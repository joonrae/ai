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

st.set_page_config(layout="wide", page_title="JOA RESCUE FORCE V215")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- [V215: 과거 데이터 강제 인양 엔진] ---
def run_rescue_scan_v215(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 🔍 1. 장부에서 이 상품의 '역대 가장 긴 이름'과 '최고 수치'를 강제로 긁어모읍니다.
    # 0이 아닌 구매수와 가장 긴 이름을 찾기 위해 쿼리를 더 공격적으로 짭니다.
    best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? AND name LIKE '%||%'
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1
    """, (t_pmid,)).fetchone()
    
    # 예외 처리: 만약 || 형식이 없으면 그냥 가장 긴거라도 가져옴
    if not best:
        best = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (t_pmid,)).fetchone()

    m_img = best[0].split("||")[0] if best and "||" in str(best[0]) else ""
    m_name = best[0].split("||")[2] if best and "||" in str(best[0]) else skw
    m_rev = str(best[1]) if best else "0"
    m_pur = str(best[2]) if best else "0"

    with st.spinner(f"🛡️ '{skw}' 데이터 인양 및 순위 갱신 중..."):
        # 순위만 새로 가져옵니다. (차단 안됨)
        f_rank, off_img = 0, ""
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        f_rank, off_img = idx + 1, item.get('image', '')
                        break
        except: pass

    # 결정: 네이버가 0을 주든 짧은 이름을 주든, 무조건 '우리가 찾은 최고 기록'을 저장함
    final_img = off_img if off_img else m_img
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{m_name}||{m_name}" # 긴 이름 박제
    
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🛡️ JOA 데이터 구출 작전 V215")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 즉시 구출", key="main_btn"):
        if nk and np: run_rescue_scan_v215(nk, np, nc, nn)

st.divider()

db = get_db()
# 등록 순서대로 아래로 차곡차곡 (ASC)
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # 화면 표시 시에도 실시간으로 이 MID의 '역대 최고 기록'을 다시 불러와서 보여줍니다. (오염 방지)
    best_record = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1
    """, (mid,)).fetchone()
    
    curr_rank = db.execute("SELECT rank, cat_mid, id FROM logs WHERE keyword=? AND p_mid=? AND note=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    if not curr_rank or not best_record: continue
    
    parts = str(best_record[0]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rk = str(curr_rank[0]).split("|")[0] if "|" in str(curr_rank[0]) else curr_rank[0]

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 2.0, 7.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            if img: st.image(img, width=130)
            else: st.info("🖼️ 복구중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"**{title}**") # 강제 구출된 이름
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid} | C: {curr_rank[1]}")
        with col4:
            st.write(f"구매 **{best_record[2]}**") # 강제 구출된 구매수
            st.write(f"리뷰 **{best_record[1]}**") # 강제 구출된 리뷰수
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 순환업데이트", key=f"btn_{mid}_{idx}_{curr_rank[2]}"):
                run_rescue_scan_v215(kw, mid, curr_rank[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
