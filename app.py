import streamlit as st
import requests
import sqlite3
import re
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA ORIGIN V207")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    return conn

# --- [V207: 사장님이 찾으시는 그 오리지널 방어 엔진] ---
def run_scan_v207(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 1. 기존 장부에서 '가장 최근에 저장된 정상 데이터'를 먼저 불러옵니다.
    prev = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? ORDER BY id DESC LIMIT 1
    """, (t_pmid,)).fetchone()
    
    # [방패 설정]
    # 기존에 데이터가 있었다면 일단 그걸 기본값으로 잡습니다.
    m_img = prev[0].split("||")[0] if prev and "||" in str(prev[0]) else ""
    m_name = prev[0].split("||")[2] if prev and "||" in str(prev[0]) else skw
    m_rev = str(prev[1]) if prev else "0"
    m_pur = str(prev[2]) if prev else "0"

    with st.spinner(f"🚀 '{skw}' 순위 업데이트 및 데이터 보호 중..."):
        # 2. 순위 및 이름 가져오기 (공식 API)
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

    # --- [핵심 로직: 사장님이 말씀하신 그 방식] ---
    # 신규 이름이 기존보다 짧으면 덮어쓰지 않습니다.
    final_name = off_name if len(off_name) > len(m_name) else m_name
    
    # 이미지가 깨져서 오면 기존 이미지를 씁니다.
    final_img = off_img if off_img and off_img.startswith("http") else m_img
    
    # [중요] 신규 데이터가 없거나 0이면, 기존의 구매/리뷰 숫자를 그대로 유지합니다.
    # 이것이 사장님이 말씀하신 "잘 되던 시절"의 비결입니다.
    final_pur, final_rev = m_pur, m_rev

    # 기록 저장
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🚀 JOA ORIGIN V207 (데이터 사수형)")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 즉시 조회", key="main_btn"):
        if nk and np: run_scan_v207(nk, np, nc, nn)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    if not row: continue
    
    parts = str(row[6]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rk = str(row[5]).split("|")[0] if "|" in str(row[5]) else row[5]

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"**{title}**") # 지켜낸 긴 이름
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid} | C: {row[11]}")
        with col4:
            st.write(f"구매 **{row[10]}**") # 지켜낸 구매수
            st.write(f"리뷰 **{row[9]}**") # 지켜낸 리뷰수
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_scan_v207(kw, mid, row[11], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
