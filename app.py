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
# VERSION: V185-FORCE-INJECTION (데이터 강제 주입 및 진단)
# ==========================================

NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"
RAPID_KEY = "3846404552mshd40a37048efd7cep108802jsn513f62eb92a3"
RAPID_HOST = "naver-shopping-insights-api-unofficial.p.rapidapi.com"

st.set_page_config(layout="wide", page_title="JOA CLOUD SNIPER V185")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [로그인 시스템] ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center; margin-top:50px;'>🛡️ JOA CLOUD SNIPER V185</h1>", unsafe_allow_html=True)
    _, l_col, _ = st.columns([1, 1, 1])
    with l_col:
        with st.form("login"):
            u, p = st.text_input("아이디").strip(), st.text_input("비밀번호", type="password")
            if st.form_submit_button("접속"):
                db = get_db(); r = db.execute("SELECT username FROM users WHERE username=? AND password=?", (u, p)).fetchone(); db.close()
                if not r: # 계정 없으면 자동 생성
                    db = get_db(); db.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (u, p)); db.commit(); db.close()
                st.session_state.auth, st.session_state.user = True, u; st.rerun()
    st.stop()

# --- [정밀 추격 엔진] ---
def get_main_rank(keyword, pmid, cmid):
    url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(keyword)}&display=100"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            items = res.json().get('items', [])
            for idx, item in enumerate(items):
                if str(item.get('productId')) in [str(pmid), str(cmid)]:
                    return idx + 1, re.sub('<[^>]*>', '', item.get('title', ''))
    except: pass
    return 0, ""

def get_catalog_rapid_spy(cmid, pmid):
    if not cmid or str(cmid).lower() == 'none': return None, "NO_CMID"
    # RapidAPI URL 구조 최적화
    url = f"https://{RAPID_HOST}/v1/naver/products?url={quote(f'https://msearch.shopping.naver.com/catalog/{cmid}')}"
    headers = {"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": RAPID_HOST}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            malls = data.get('malls', []) + data.get('lowPriceHighValueMalls', [])
            for idx, m in enumerate(malls):
                if str(m.get('nvMid')) == str(pmid) or str(m.get('productId')) == str(pmid):
                    return {"inner": m.get('rank') or (idx + 1), "name": m.get('productName', ''), "img": m.get('imageUrl', ''), "rev": m.get('reviewCount', 0), "pur": m.get('purchaseCnt', 0)}, "SUCCESS"
            return None, "MID_NOT_FOUND"
        return None, f"HTTP_{res.status_code}"
    except Exception as e: return None, str(e)

def run_scan_v185(skw, spmid, scmid, snote, user_id):
    t_pmid, t_cmid = str(spmid).strip(), str(scmid).strip()
    db = get_db()
    
    # 1. 금고 데이터 로드
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    m_name, m_img, m_rev, m_pur = (meta[0], meta[1], meta[2], meta[3]) if meta else (skw, "", "0", "0")

    # 2. [특별 로직] !fix 명령어가 메모에 있으면 강제 주입
    if snote.startswith("!fix"):
        fixed_name = snote.replace("!fix", "").strip()
        # 임시 이미지 주소 (사장님이 나중에 바꾸실 수 있음)
        m_name, m_rev, m_pur = fixed_name, "601", "1" 
        db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, m_name, m_img, m_rev, m_pur))
        db.commit()

    with st.spinner(f"🔍 '{skw}' 정밀 분석 중..."):
        f_rank, off_name = get_main_rank(skw, t_pmid, t_cmid)
        spy, status = get_catalog_rapid_spy(t_cmid, t_pmid)

    # 3. 데이터 판정
    if spy and int(spy['pur']) > 0:
        final_name = spy['name'] if len(spy['name']) > len(m_name) else m_name
        final_img, final_rev, final_pur, final_inner = spy['img'], str(spy['rev']), str(spy['pur']), spy['inner']
        db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur))
    else:
        # 실패 시 금고 유지
        final_name = m_name if len(m_name) > len(off_name) else (off_name or skw)
        final_img, final_rev, final_pur, final_inner = m_img, m_rev, m_pur, 0
        if status != "SUCCESS": st.toast(f"ℹ️ 카탈로그 정찰 결과: {status}")

    # 4. 로그 저장
    rank_save = f"{f_rank}|{final_inner}"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, t_cmid, str(snote)))
    db.commit(); db.close()
    st.rerun()

# --- [UI 렌더링 영역] ---
def get_rank_display(raw_val):
    if not raw_val or raw_val == "-" or raw_val == "0|0": return "-", ""
    parts = str(raw_val).split("|")
    main = parts[0] if parts[0] != "0" else "100위+"
    inner = parts[1] if (len(parts) > 1 and parts[1] != "0") else ""
    sub_html = f"<div style='color:#22c55e; font-weight:bold; font-size:1.1rem;'>묶음 {inner}위</div>" if inner else ""
    return f"{main}위", sub_html

st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.1rem; font-weight: 700; color: #1a202c; line-height: 1.5; }
</style>""", unsafe_allow_html=True)

st.title(f"🚀 JOA CLOUD SNIPER V185 - {st.session_state.user}님")

with st.container():
    st.info("💡 팁: 상품명이 계속 짧게 나오면 메모란에 `!fix 상품명`을 입력하고 새로고침 하세요.")
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 추격 시작", use_container_width=True):
        if nk and np: run_scan_v185(nk, np, nc, nn, st.session_state.user)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs WHERE user_id=? GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC", (st.session_state.user,)).fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) AND user_id=? ORDER BY id DESC LIMIT 1", (kw, mid, m_val, st.session_state.user)).fetchone()
    if not row: continue
    parts = str(row[6]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rev, m_buy, cmid, memo_text = str(row[9]), str(row[10]), row[11], row[12]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 1.8, 4.2, 5.0, 1.8, 2.8])
        with col1: st.subheader(idx + 1)
        with col2:
            if img.startswith("http"): st.image(img, width=140)
            else: st.write("🖼️ 이미지 사수 중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"<div class='product-title'>{title}</div>", unsafe_allow_html=True)
            if memo_text and memo_text != "None": st.markdown(f"<div style='color:#3182ce; font-weight:bold;'>📝 {memo_text}</div>", unsafe_allow_html=True)
            st.caption(f"P: {mid} | C: {cmid if cmid else '-'}")
        with col4:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                hist = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ? ORDER BY id DESC LIMIT 1", (kw, mid, memo_text, f"{t}%")).fetchone()
                m_rk, _ = get_rank_display(hist[0] if hist else "-")
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{m_rk}</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col5:
            st.markdown(f"<div style='margin-top:10px;'>구매 <b>{m_buy}</b><br>리뷰 <b>{m_rev}</b></div>", unsafe_allow_html=True)
        with col6:
            m_rk, s_rk = get_rank_display(row[5])
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3rem; margin:0;'>{m_rk}</h1>{s_rk}</div>", unsafe_allow_html=True)
            bc = st.columns(2)
            if bc[0].button("🔄", key=f"r_{row[0]}"): run_scan_v185(kw, mid, cmid, memo_text, st.session_state.user)
            if bc[1].button("🗑️", key=f"d_{row[0]}"):
                db_del = get_db()
                db_del.execute("DELETE FROM logs WHERE keyword=? AND p_mid=? AND note=? AND user_id=?", (kw, mid, memo_text, st.session_state.user))
                db_del.commit(); db_del.close(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
