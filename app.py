import streamlit as st
import sqlite3
import requests
import re
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 기본 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA DATA SENSING V213")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- [V213: 정밀 데이터 복구 및 추격 엔진] ---
def run_final_scan_v213(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 🔍 [수정] 장부에서 데이터를 찾는 로직을 훨씬 더 넓게 잡습니다.
    # length(name) 뿐만 아니라 '||' 구분자가 있는 진짜 상품명을 정확히 타겟팅합니다.
    best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? AND name LIKE '%||%'
        ORDER BY length(name) DESC LIMIT 1
    """, (t_pmid,)).fetchone()
    
    # 만약 위 조건으로 못찾으면 그냥 가장 긴거라도 가져옵니다.
    if not best:
        best = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (t_pmid,)).fetchone()

    m_img = best[0].split("||")[0] if best and "||" in str(best[0]) else ""
    m_name = best[0].split("||")[2] if best and "||" in str(best[0]) else skw
    m_rev = str(best[1]) if best else "0"
    m_pur = str(best[2]) if best else "0"

    with st.spinner(f"🛡️ '{skw}' 데이터 정밀 복구 중..."):
        f_rank, off_name, off_img = 0, skw, ""
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        f_rank, off_name, off_img = idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
                        break
        except: pass

    # [보정] 네이버 이름이 기존 장부 이름보다 길면 업데이트, 아니면 장부 이름 고정
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = off_img if (off_img and off_img.startswith("http")) else m_img
    
    # 기록 저장
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🛡️ JOA 데이터 정밀 복구 V213")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 정밀 추격/복구", key="main_btn"):
        if nk and np: run_final_scan_v213(nk, np, nc, nn)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # 화면 표시용 데이터도 '정밀'하게 역대 최고치를 가져옵니다.
    best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? AND name LIKE '%||%'
        ORDER BY length(name) DESC LIMIT 1
    """, (mid,)).fetchone()
    
    if not best:
        best = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (mid,)).fetchone()

    curr = db.execute("SELECT rank, cat_mid, id FROM logs WHERE keyword=? AND p_mid=? AND note=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    if not curr or not best: continue
    
    parts = str(best[0]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rk = str(curr[0]).split("|")[0] if "|" in str(curr[0]) else curr[0]

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 2.0, 7.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            if img: st.image(img, width=130)
            else: st.info("🖼️ 수색중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            # [결과] 무조건 가장 길었던 황금기 이름 노출
            st.markdown(f"**{title}**")
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid} | C: {curr[1]}")
        with col4:
            st.write(f"구매 **{best[2]}**")
            st.write(f"리뷰 **{best[1]}**")
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 순위갱신", key=f"btn_{mid}_{idx}_{curr[2]}"):
                run_final_scan_v213(kw, mid, curr[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
