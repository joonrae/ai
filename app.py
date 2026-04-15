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

st.set_page_config(layout="wide", page_title="JOA TIME-MACHINE V199")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT, note TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    # DB 수리 (note 컬럼 누락 대비)
    try: conn.execute("ALTER TABLE product_meta ADD COLUMN note TEXT")
    except: pass
    conn.commit()
    return conn

# --- [V152 스타일: 자동 사수형 스캔 엔진] ---
def run_scan_v199(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # [1] 기존 데이터 확보 (금고 뒤지기)
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (skw, "", "0", "0", snote)

    with st.spinner(f"🚀 '{skw}' 자동 사수 중..."):
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

    # [V152 엔진 복구] 이름이 기존보다 짧으면 무조건 긴 이름 유지
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 메모는 새로 적은 게 있으면 업데이트, 없으면 유지
    final_note = snote if snote else m_note

    # 금고 업데이트 (구매/리뷰는 기존 최고치 유지)
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?,?)", (t_pmid, final_name, final_img, m_rev, m_pur, final_note))
    
    # 로그 기록 (신규 추가 시 리스트 노출을 위해 반드시 기록)
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, final_note))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 15px; }
    .product-title { font-size: 1.1rem; font-weight: 700; color: #1a202c; line-height: 1.4; }
</style>""", unsafe_allow_html=True)

st.title("🚀 JOA AUTO MASTER V199")

# [신규 추가부] 여기서 등록하면 즉시 아래 리스트에 뜹니다!
with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규 상품 추가", key="main_btn"):
        if nk and np: run_scan_v199(nk, np, nc, nn)

st.divider()

db = get_db()
# [신규 상품 추가 해결] logs와 product_meta를 JOIN하여 데이터가 없어도 무조건 리스트에 노출
items = db.execute("""
    SELECT l.keyword, l.p_mid, l.cat_mid, l.note, MAX(l.id) 
    FROM logs l 
    GROUP BY l.p_mid 
    ORDER BY MAX(l.id) DESC
""").fetchall()

for idx, (kw, mid, cmid, l_note, _) in enumerate(items):
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT rank FROM logs WHERE p_mid=? ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
    
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (kw, "", "0", "0", l_note)
    m_rk = str(row[0]).split("|")[0] if row and "|" in str(row[0]) else "0"

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            # 상품명은 이제 자동으로 긴 것만 보여줍니다. (필요시에만 수동 수정)
            st.markdown(f"<div class='product-title'>{m_name}</div>", unsafe_allow_html=True)
            if m_note: st.info(f"📝 {m_note}")
            st.caption(f"MID: {mid} | C: {cmid}")
        with col3:
            # 8일간 순위 그래프
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE p_mid=? AND date LIKE ?", (mid, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.write(f"구매 {m_pur}")
            st.write(f"리뷰 {m_rev}")
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_scan_v199(kw, mid, cmid, m_note)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
