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

st.set_page_config(layout="wide", page_title="JOA INJECTOR V216")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- [V216: 데이터 강제 주입 및 순위 추격 엔진] ---
def run_scan_v216(skw, spmid, scmid, snote, force_data=None):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    if force_data:
        # 사장님이 수동으로 주입한 데이터가 있으면 그걸로 즉시 박제
        f_name, f_pur, f_rev = force_data['name'], force_data['purchase'], force_data['reviews']
        f_rank = force_data.get('rank', '0')
    else:
        # 일반 스캔 시: 장부 내 최고 기록 탐색
        best = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1", (t_pmid,)).fetchone()
        f_name = best[0].split("||")[2] if best and "||" in str(best[0]) else skw
        f_pur = str(best[2]) if best else "0"
        f_rev = str(best[1]) if best else "0"

    with st.spinner(f"🚀 '{skw}' 순위 갱신 중..."):
        # 순위만 새로 가져옵니다.
        new_rank = "0"
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        new_rank = str(idx + 1)
                        break
        except: pass

    # 기록 저장 (이미지가 없으면 샘플 이미지로 대체)
    save_data = f"https://via.placeholder.com/150||0||{f_name}||{f_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, f"{new_rank}|0", save_data, "0", "피크스페이스", f_rev, f_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("💉 JOA 데이터 강제 주입기 V216")
st.info("💡 데이터가 0으로 나오면 아래 '강제 데이터 주입' 칸에 한 번만 입력하세요. 그 뒤론 영구 고정됩니다.")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규 등록", key="main_btn"):
        if nk and np: run_scan_v208(nk, np, nc, nn) # 기본 스캔

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    best = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC, CAST(purchase AS INTEGER) DESC LIMIT 1", (mid,)).fetchone()
    curr = db.execute("SELECT rank, cat_mid, id FROM logs WHERE keyword=? AND p_mid=? AND note=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    
    if not curr or not best: continue
    title = str(best[0]).split("||")[2] if "||" in str(best[0]) else kw
    m_rk = str(curr[0]).split("|")[0] if "|" in str(curr[0]) else curr[0]

    with st.container():
        st.markdown(f'<div style="border:2px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:15px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([0.5, 6.0, 3.0, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw} <small>(MID: {mid})</small>", unsafe_allow_html=True)
            st.markdown(f"**현상태:** {title} / 구매 {best[2]} / 리뷰 {best[1]}")
            
            # --- [강제 주입 폼] ---
            with st.expander("💉 이 상품 데이터 강제 주입 (수정하기)"):
                in_name = st.text_input("수정할 긴 상품명", value=title, key=f"in_{mid}")
                in_pur = st.text_input("수정할 구매수", value=best[2], key=f"ip_{mid}")
                in_rev = st.text_input("수정할 리뷰수", value=best[1], key=f"ir_{mid}")
                if st.button("✅ 데이터 박제하기", key=f"save_{mid}"):
                    run_scan_v216(kw, mid, curr[1], m_val, force_data={'name': in_name, 'purchase': in_pur, 'reviews': in_rev})
        
        with col3:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
        with col4:
            if st.button("🔄 순위만 갱신", key=f"up_{mid}_{idx}"):
                run_scan_v216(kw, mid, curr[1], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
