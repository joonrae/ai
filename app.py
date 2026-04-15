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

st.set_page_config(layout="wide", page_title="JOA DATA RECOVERY V208")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- [V208: 과거 데이터 강제 소환 및 고정 엔진] ---
def run_recovery_scan_v208(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 🔍 [핵심] 장부 전체를 뒤져서 '역대 가장 길었던 이름'과 '가장 높았던 구매/리뷰'를 찾아옵니다.
    best_record = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1
    """, (t_pmid,)).fetchone()
    
    m_img = best_record[0].split("||")[0] if best_record and "||" in str(best_record[0]) else ""
    m_name = best_record[0].split("||")[2] if best_record and "||" in str(best_record[0]) else skw
    m_rev = str(best_record[1]) if best_record else "0"
    m_pur = str(best_record[2]) if best_record else "0"

    with st.spinner(f"🛡️ '{skw}' 순위 갱신 및 데이터 복구 중..."):
        # 순위만 새로 가져옵니다.
        f_rank = 0
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        f_rank = idx + 1
                        break
        except: pass

    # 기록 저장 (화면에는 항상 위의 m_name, m_pur 같은 '최고 기록'만 나옵니다)
    rank_save = f"{f_rank}|0"
    save_data = f"{m_img}||0||{m_name}||{m_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI 화면] ---
st.title("🛡️ JOA 데이터 복구 시스템 V208")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규추가/복구", key="main_btn"):
        if nk and np: run_recovery_scan_v208(nk, np, nc, nn)

st.divider()

db = get_db()
# 등록된 순서대로 정렬 (ASC)
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # [화면 표시] 무조건 장부 내 '역대 최고치'만 가져와서 보여줍니다.
    best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? 
        ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1
    """, (mid,)).fetchone()
    
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
            st.markdown(f"**{title}**") # 역대 최고로 길었던 이름 강제 출력
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"MID: {mid}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ?", (kw, mid, m_val, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.write(f"구매 **{best[2]}**") # 역대 최고 구매수 강제 출력
            st.write(f"리뷰 **{best[1]}**") # 역대 최고 리뷰수 강제 출력
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 순위갱신", key=f"btn_{mid}_{idx}"):
                run_recovery_scan_v208(kw, mid, curr[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
