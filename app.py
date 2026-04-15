import streamlit as st
import requests
import sqlite3
import json
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 환경 설정
DB_PATH = 'joa_final_v12.db'

# ==========================================
# VERSION: V183-CLOUD-FIX (UI 기둥 수선 완료)
# ==========================================

NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA CLOUD SNIPER V183")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, 
            rank TEXT, name TEXT, price TEXT, mall TEXT, 
            reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT
        )
    """)
    return conn

# --- [로그인 시스템] ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center; margin-top:50px;'>☁️ JOA CLOUD SNIPER</h1>", unsafe_allow_html=True)
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login"):
            u = st.text_input("아이디").strip()
            p = st.text_input("비밀번호", type="password")
            if st.form_submit_button("접속"):
                db = get_db()
                r = db.execute("SELECT username FROM users WHERE username=? AND password=?", (u, p)).fetchone()
                db.close()
                if r:
                    st.session_state.auth, st.session_state.user = True, r[0]
                    st.rerun()
                else:
                    st.error("아이디/비번을 확인하세요. (DB 파일이 잘 올라갔는지 확인!)")
    st.stop()

# --- [기능] 클라우드 정찰 엔진 ---
def run_scan_v183(skw, spmid, scmid, snote, user_id):
    t_pmid, t_cmid = str(spmid).strip(), str(scmid).strip()
    url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    
    with st.spinner(f"🚀 클라우드 엔진이 '{skw}' 추격 중..."):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            f_rank, off_name = 0, skw
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, t_cmid]:
                        f_rank = idx + 1
                        off_name = re.sub('<[^>]*>', '', item.get('title', ''))
                        break
            
            db = get_db()
            rank_save = f"{f_rank}|0"
            save_data = f"||0||{off_name}||{off_name}"
            db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", "0", "0", t_cmid, str(snote)))
            db.commit(); db.close()
            st.rerun()
        except Exception as e:
            st.error(f"스캔 오류: {e}")

# --- [UI 렌더링] ---
def get_rank_display(raw_val):
    if not raw_val or raw_val == "-" or raw_val == "0|0": return "-", ""
    parts = str(raw_val).split("|")
    main = parts[0] if parts[0] != "0" else "100위+"
    return f"{main}위", ""

st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.15rem; font-weight: 700; color: #1a202c; line-height: 1.5; }
</style>""", unsafe_allow_html=True)

st.title(f"🚀 JOA CLOUD SNIPER - {st.session_state.user}님")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 순위 추격", use_container_width=True):
        if nk and np: run_scan_v183(nk, np, nc, nn, st.session_state.user)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs WHERE user_id=? GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC", (st.session_state.user,)).fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) AND user_id=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val, st.session_state.user)).fetchone()
    if not row: continue
    parts = str(row[6]).split("||")
    title = parts[2] if len(parts)>2 else kw
    m_rev, m_buy, cmid, memo_text = str(row[9]), str(row[10]), row[11], row[12]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        # 기둥을 6개로 정확하게 정의합니다.
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 4.2, 5.0, 1.8, 1.5, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"<div class='product-title'>{title}</div>", unsafe_allow_html=True)
            if memo_text and memo_text != "None": st.markdown(f"<div style='color:#3182ce;'>📝 {memo_text}</div>", unsafe_allow_html=True)
            st.caption(f"P: {mid} | C: {cmid if cmid else '-'}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                hist = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ? ORDER BY id DESC LIMIT 1", (kw, mid, memo_text, f"{t}%")).fetchone()
                m_rk, _ = get_rank_display(hist[0] if hist else "-")
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{m_rk}</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='margin-top:10px;'>구매 <b>{m_buy}</b><br>리뷰 <b>{m_rev}</b></div>", unsafe_allow_html=True)
        with col5:
            # 🔄 버튼 영역
            if st.button("🔄", key=f"r_{row[0]}"): 
                run_scan_v183(kw, mid, cmid, memo_text, st.session_state.user)
        with col6:
            # 순위 표시 및 🗑️ 버튼 영역
            m_rk, _ = get_rank_display(row[5])
            sc1, sc2 = st.columns([3, 1])
            sc1.markdown(f"<h1 style='font-size:2.5rem; margin:0; text-align:right;'>{m_rk}</h1>", unsafe_allow_html=True)
            if sc2.button("🗑️", key=f"d_{row[0]}"):
                db_del = get_db()
                db_del.execute("DELETE FROM logs WHERE keyword=? AND p_mid=? AND note=? AND user_id=?", (kw, mid, memo_text, st.session_state.user))
                db_del.commit(); db_del.close()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
