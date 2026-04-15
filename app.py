import streamlit as st
import requests
import sqlite3
import json
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 환경 경로 설정 (깃허브 루트 경로)
DB_PATH = 'joa_final_v12.db'

# ==========================================
# VERSION: V181-CLOUD-START (클라우드 이사 전용)
# ==========================================

NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA CLOUD SNIPER")

def get_db():
    # 클라우드에서는 파일 권한이 더 자유롭습니다.
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- [로그인 시스템] ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center;'>☁️ JOA CLOUD SNIPER</h1>", unsafe_allow_html=True)
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login"):
            u = st.text_input("아이디").strip()
            p = st.text_input("비밀번호", type="password")
            if st.form_submit_button("접속"):
                db = get_db()
                r = db.execute("SELECT username FROM users WHERE username=? AND password=?", (u, p)).fetchone()
                if r:
                    st.session_state.auth, st.session_state.user = True, r[0]
                    db.close(); st.rerun()
                else:
                    st.error("계정 정보를 확인해주세요. (DB 파일이 잘 올라갔는지 확인!)")
    st.stop()

# --- [클라우드 파워 추격 엔진] ---
def run_scan_cloud(skw, spmid, scmid, snote, user_id):
    t_pmid, t_cmid = str(spmid).strip(), str(scmid).strip()
    
    # 클라우드 아이피의 힘을 빌려 정밀 스캔
    url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    
    with st.spinner("🚀 클라우드 엔진 가동 중..."):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            f_rank = 0
            off_name = skw
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, t_cmid]:
                        f_rank = idx + 1
                        off_name = re.sub('<[^>]*>', '', item.get('title', ''))
                        break
            
            # DB 업데이트
            db = get_db()
            rank_save = f"{f_rank}|0" # 카탈로그 순위는 추후 보강
            save_data = f"||0||{off_name}||{off_name}"
            db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", "0", "0", t_cmid, str(snote)))
            db.commit(); db.close()
            st.rerun()
        except Exception as e:
            st.error(f"스캔 중 오류: {e}")

# (이하 리스트 출력 UI 코드는 사장님이 쓰시던 것과 동일하게 붙여넣으시면 됩니다!)