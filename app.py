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

st.set_page_config(layout="wide", page_title="JOA LEGACY SHIELD V196")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [정밀 추격 엔진: V152식 보존 로직 탑재] ---
def run_scan_v196(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # [방패 1] 기존 금고 데이터 확보
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    # [방패 2] 역대 로그 중 가장 길었던 이름 확보 (V152 핵심 로직)
    best_log = db.execute("SELECT name FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (t_pmid,)).fetchone()
    
    m_name = (best_log[0].split("||")[2] if best_log and "||" in str(best_log[0]) else (meta[0] if meta else skw))
    m_img, m_rev, m_pur = (meta[1], meta[2], meta[3]) if meta else ("", "0", "0")

    with st.spinner(f"🛡️ '{skw}' 데이터 사수 중..."):
        # 공식 API 스캔 (순위용)
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

    # --- [SMART JUDGE: V152식 비교] ---
    # 1. 이름 사수: 새로 가져온 이름이 기존보다 짧으면 무조건 기존 긴 이름 선택
    final_name = off_name if len(off_name) > len(m_name) else m_name
    
    # 2. 이미지 사수: 기존 주소가 있으면 유지
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 3. 구매/리뷰 사수: 일단 금고 데이터 유지 (추후 차단 풀리면 업데이트 되도록 설계)
    final_pur, final_rev = m_pur, m_rev

    # 금고 업데이트
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur))
    
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.15rem; font-weight: 700; color: #1a202c; line-height: 1.4; margin-bottom: 8px; }
</style>""", unsafe_allow_html=True)

st.title("🛡️ JOA LEGACY SHIELD V196")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 업데이트", key="main_btn"):
        if nk and np: run_scan_v196(nk, np, nc, nn)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? ORDER BY id DESC LIMIT 1", (kw, mid)).fetchone()
    
    if not row: continue
    m_name, m_img, m_rev, m_pur = meta if meta else (kw, "", "0", "0")
    m_rk = str(row[5]).split("|")[0] if "|" in str(row[5]) else row[5]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 1.8, 4.2, 5.0, 1.8, 2.8])
        with col1: st.subheader(idx + 1)
        with col2:
            if m_img.startswith("http"): st.image(m_img, width=140)
            else: st.info("🖼️ 사수 중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            # 사장님이 편집 가능하게 한 번 더 열어둠 (마지막 수단)
            new_title = st.text_area("📄 상품명 마스터", value=m_name, key=f"t_{mid}_{idx}", height=70)
            if new_title != m_name:
                db_u = get_db(); db_u.execute("UPDATE product_meta SET name=? WHERE p_mid=?", (new_title, mid)); db_u.commit(); db_u.close(); st.rerun()
            st.caption(f"P: {mid} | C: {row[11]}")
        with col4:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND date LIKE ?", (kw, mid, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col5:
            st.write(f"구매 {m_pur}")
            st.write(f"리뷰 {m_rev}")
        with col6:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 즉시 업데이트", key=f"btn_{mid}_{idx}"):
                run_scan_v196(kw, mid, row[11], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
