import streamlit as st
import requests
import sqlite3
import json
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 환경 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"
RAPID_KEY = "3846404552mshd40a37048efd7cep108802jsn513f62eb92a3"
RAPID_HOST = "naver-shopping-insights-api-unofficial.p.rapidapi.com"

st.set_page_config(layout="wide", page_title="JOA CLOUD SNIPER V187")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [정밀 엔진: 품질 판단 로직 탑재] ---
def get_naver_official(keyword, pmid, cmid):
    url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(keyword)}&display=100"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            items = res.json().get('items', [])
            for idx, item in enumerate(items):
                if str(item.get('productId')) in [str(pmid), str(cmid)]:
                    return idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
    except: pass
    return 0, "", ""

def get_catalog_rapid(cmid, pmid):
    if not cmid or str(cmid).lower() == 'none': return None
    url = f"https://{RAPID_HOST}/v1/naver/products?url={quote(f'https://msearch.shopping.naver.com/catalog/{cmid}')}"
    headers = {"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": RAPID_HOST}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            malls = data.get('malls', []) + data.get('lowPriceHighValueMalls', [])
            for idx, m in enumerate(malls):
                if str(m.get('nvMid')) == str(pmid) or str(m.get('productId')) == str(pmid):
                    return {"inner": m.get('rank') or (idx + 1), "name": m.get('productName', ''), "img": m.get('imageUrl', ''), "rev": m.get('reviewCount', 0), "pur": m.get('purchaseCnt', 0)}
    except: pass
    return None

def run_scan_v187(skw, spmid, scmid, snote, user_id):
    t_pmid, t_cmid = str(spmid).strip(), str(scmid).strip()
    db = get_db()
    
    # [금고 데이터 확인]
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    m_name, m_img, m_rev, m_pur = (meta[0], meta[1], meta[2], meta[3]) if meta else (skw, "", "0", "0")

    with st.spinner(f"🛡️ '{skw}' 데이터 자동 보호 모드 가동 중..."):
        f_rank, off_name, off_img = get_naver_official(skw, t_pmid, t_cmid)
        spy = get_catalog_rapid(t_cmid, t_pmid)

    # --- [SMART JUDGE: 데이터 품질 판단] ---
    # 1. 이름 결정: (신규 Rapid이름 vs 공식 이름 vs 기존 금고이름) 중 가장 긴 것!
    name_candidates = [off_name, m_name]
    if spy: name_candidates.append(spy['name'])
    final_name = max([c for c in name_candidates if c], key=len)

    # 2. 이미지 결정: 기존 이미지가 있으면 유지, 없으면 새로운 것 확보
    final_img = m_img if (m_img and m_img.startswith("http")) else (spy['img'] if spy and spy['img'] else off_img)

    # 3. 구매수/리뷰수 결정: 0이면 과거 데이터 사용 (차단 방어)
    if spy and int(spy['pur']) > 0:
        final_pur, final_rev, final_inner = str(spy['pur']), str(spy['rev']), spy['inner']
    else:
        final_pur, final_rev, final_inner = m_pur, m_rev, 0

    # 금고(product_meta)에 최상의 데이터 박제
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur))
    
    # 로그 기록
    rank_save = f"{f_rank}|{final_inner}"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, t_cmid, str(snote)))
    db.commit(); db.close()
    st.rerun()

# --- [UI 렌더링 영역] ---
# (기존 V186 UI 코드와 동일하되, col 개수와 이미지 출력 로직을 더 안정화함)
def get_rank_display(raw_val):
    if not raw_val or raw_val == "-" or raw_val == "0|0": return "-", ""
    parts = str(raw_val).split("|")
    main = parts[0] if parts[0] != "0" else "100위+"
    inner = parts[1] if (len(parts) > 1 and parts[1] != "0") else ""
    sub_html = f"<div style='color:#22c55e; font-weight:bold; font-size:1.1rem;'>묶음 {inner}위</div>" if inner else ""
    return f"{main}위", sub_html

st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.1rem; font-weight: 700; color: #1a202c; line-height: 1.4; }
</style>""", unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    # (로그인 코드는 이전과 동일)
    st.session_state.auth = True # 클라우드 테스트용 자동통과 (사장님은 로그인 쓰세요)

st.title(f"🚀 JOA CLOUD SNIPER V187")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 추격 시작", use_container_width=True):
        if nk and np: run_scan_v187(nk, np, nc, nn, "사장님")

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
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
            else: st.info("🖼️ 이미지 사수 중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            st.markdown(f"<div class='product-title'>{title}</div>", unsafe_allow_html=True)
            if memo_text and memo_text != "None": st.caption(f"📝 {memo_text}")
            st.caption(f"P: {mid} | C: {cmid}")
        with col4:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                hist = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND date LIKE ?", (kw, mid, f"{t}%")).fetchone()
                m_rk, _ = get_rank_display(hist[0] if hist else "-")
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{m_rk}</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col5:
            st.markdown(f"<div style='margin-top:10px;'>구매 <b>{m_buy}</b><br>리뷰 <b>{m_rev}</b></div>", unsafe_allow_html=True)
        with col6:
            m_rk, s_rk = get_rank_display(row[5])
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3rem; margin:0;'>{m_rk}</h1>{s_rk}</div>", unsafe_allow_html=True)
            if st.button("🔄", key=f"r_{row[0]}"): run_scan_v187(kw, mid, cmid, memo_text, "사장님")
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
