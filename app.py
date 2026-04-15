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

st.set_page_config(layout="wide", page_title="JOA MASTER V206")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    return conn

# --- [V206: 과거 데이터 강제 소환 엔진] ---
def run_scan_v206(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # [방패] 장부 전체에서 '역대 최고 데이터'를 찾아옵니다.
    # 이름이 가장 길고, 구매수가 가장 높았던 기록을 최우선으로 가져옵니다.
    prev = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC, id DESC 
        LIMIT 1
    """, (t_pmid,)).fetchone()
    
    m_img = prev[0].split("||")[0] if prev and "||" in str(prev[0]) else ""
    m_name = prev[0].split("||")[2] if prev and "||" in str(prev[0]) else skw
    m_rev = str(prev[1]) if prev else "0"
    m_pur = str(prev[2]) if prev else "0"

    with st.spinner(f"🚀 '{skw}' 순위 업데이트 중..."):
        # 순위만 새로 가져옵니다 (차단 안 됨)
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

    # 데이터 판정: 새로 가져온 게 나쁘면 과거 데이터를 씁니다.
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 저장 (로그에 기록하지만, 화면에는 항상 '최고치'만 띄울 겁니다)
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🛡️ JOA DATA SHIELD V206")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 조회/등록", key="main_btn"):
        if nk and np: run_scan_v206(nk, np, nc, nn)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # [핵심] 화면 표시용 데이터를 찾을 때 '역대 최고치'를 직접 쿼리합니다.
    best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC, id DESC 
        LIMIT 1
    """, (mid,)).fetchone()
    
    # 순위는 가장 최근 것
    curr = db.execute("SELECT rank, cat_mid FROM logs WHERE keyword=? AND p_mid=? AND note=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    
    if not curr or not best: continue
    
    parts = str(best[0]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rk = str(curr[0]).split("|")[0] if "|" in str(curr[0]) else curr[0]

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"**{title}**") # 역대 가장 길었던 이름 자동 노출
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid} | C: {curr[1]}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ?", (kw, mid, m_val, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.write(f"구매 **{best[2]}**") # 역대 가장 높았던 구매수 자동 노출
            st.write(f"리뷰 **{best[1]}**") # 역대 가장 높았던 리뷰수 자동 노출
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_scan_v206(kw, mid, curr[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
