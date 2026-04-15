import streamlit as st
import requests
import sqlite3
import re
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 환경 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA ULTRA MASTER V200")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT, note TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    try: conn.execute("ALTER TABLE product_meta ADD COLUMN note TEXT")
    except: pass
    conn.commit()
    return conn

# --- [V200: 딥 리커버리 엔진] ---
def run_scan_v200(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 1. 금고 및 과거 로그에서 '역대 최고 데이터' 탐색
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    # [핵심] 로그 전체에서 가장 긴 이름과 가장 높은 수치를 찾습니다.
    best_log = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC 
        LIMIT 1
    """, (t_pmid,)).fetchone()
    
    m_name = (best_log[0].split("||")[2] if best_log and "||" in str(best_log[0]) else (meta[0] if meta else skw))
    m_img, m_rev, m_pur = (meta[1], meta[2], meta[3]) if meta else ("", "0", "0")
    if best_log:
        m_rev = str(max(int(re.sub(r'[^0-9]', '', str(m_rev))), int(re.sub(r'[^0-9]', '', str(best_log[1])))))
        m_pur = str(max(int(re.sub(r'[^0-9]', '', str(m_pur))), int(re.sub(r'[^0-9]', '', str(best_log[2])))))

    with st.spinner(f"🛡️ '{skw}' 데이터 복구 중..."):
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        f_rank, off_name, off_img = 0, skw, ""
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        f_rank, off_name, off_img = idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
                        break
        except: pass

    # 데이터 비교 사수: 새로 가져온 게 기존보다 짧거나 0이면 업데이트 거부
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 금고 업데이트
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?,?)", (t_pmid, final_name, final_img, m_rev, m_pur, snote))
    
    # 로그 기록 (신규 추가 시 누락 방지를 위해 상세 정보 포함 저장)
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🛡️ JOA AUTO MASTER V200")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규 상품 추가", key="main_btn"):
        if nk and np: run_scan_v200(nk, np, nc, nn)

st.divider()

db = get_db()
# [중요] 중복 등록 허용: 키워드와 MID가 다르면 별도로 노출
items = db.execute("""
    SELECT keyword, p_mid, note, MAX(id) 
    FROM logs 
    GROUP BY keyword, p_mid, note 
    ORDER BY MAX(id) DESC
""").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT rank, cat_mid FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    
    if not row: continue
    m_name, m_img, m_rev, m_pur = meta if meta else (kw, "", "0", "0")
    m_rk = str(row[0]).split("|")[0] if "|" in str(row[0]) else row[0]

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"**{m_name}**")
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid} | C: {row[1]}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ?", (kw, mid, m_val, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.write(f"구매 {m_pur}")
            st.write(f"리뷰 {m_rev}")
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_auto_scan_v200(kw, mid, row[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
