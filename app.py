import streamlit as st
import requests
import sqlite3
import re
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 환경 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"
RAPID_KEY = "3846404552mshd40a37048efd7cep108802jsn513f62eb92a3"
RAPID_HOST = "naver-shopping-insights-api-unofficial.p.rapidapi.com"

st.set_page_config(layout="wide", page_title="JOA TOTAL LOCK V203")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    return conn

# --- [V203: P-MID 이름 사수 + C-MID 순위 추격 엔진] ---
def run_scan_v203(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    t_cmid = str(scmid).strip() if scmid and str(scmid).lower() != 'none' else ""
    db = get_db()
    
    # [방패] P-MID 기준으로 '역대 가장 길었던 이름' 찾기 (사장님의 핵심 요구사항)
    # logs 테이블에서 이 P-MID를 가진 기록 중 이름(name)의 3번째 칸(진짜 이름)이 가장 긴 걸 찾습니다.
    prev_best = db.execute("""
        SELECT name, reviews, purchase FROM logs 
        WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1
    """, (t_pmid,)).fetchone()
    
    m_img = prev_best[0].split("||")[0] if prev_best and "||" in str(prev_best[0]) else ""
    m_name = prev_best[0].split("||")[2] if prev_best and "||" in str(prev_best[0]) else skw
    m_rev = str(prev_best[1]) if prev_best else "0"
    m_pur = str(prev_best[2]) if prev_best else "0"

    with st.spinner(f"🚀 '{skw}' 데이터 사수 및 순위 추격 중..."):
        # 1. 메인 순위 추격 (C-MID가 있다면 C-MID를 우선으로 찾음)
        f_rank, off_name, off_img = 0, skw, ""
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    # P-MID나 C-MID 둘 중 하나라도 맞으면 내 상품으로 간주
                    if str(item.get('productId')) == t_pmid or str(item.get('productId')) == t_cmid:
                        f_rank, off_name, off_img = idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
                        break
        except: pass

        # 2. 상세 데이터 (RapidAPI)
        r_pur, r_rev, r_name, r_img, r_inner = "0", "0", "", "", 0
        if t_cmid:
            try:
                r_url = f"https://{RAPID_HOST}/v1/naver/products?url={quote(f'https://msearch.shopping.naver.com/catalog/{t_cmid}')}"
                r_headers = {"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": RAPID_HOST}
                r_res = requests.get(r_url, headers=r_headers, timeout=15)
                if r_res.status_code == 200:
                    data = r_res.json()
                    malls = data.get('malls', []) + data.get('lowPriceHighValueMalls', [])
                    for idx, m in enumerate(malls):
                        if str(m.get('nvMid') or m.get('productId')) == t_pmid:
                            r_name, r_img, r_rev, r_pur, r_inner = m.get('productName', ''), m.get('imageUrl', ''), str(m.get('reviewCount', 0)), str(m.get('purchaseCnt', 0)), (m.get('rank') or idx+1)
                            break
            except: pass

    # --- [최종 판단: V203 절대 길이 원칙] ---
    # 신규로 가져온 이름들(r_name, off_name)과 기존 금고 이름(m_name) 중 가장 긴 것 선택!
    final_name = max([r_name, off_name, m_name], key=len)
    final_img = r_img if r_img else (off_img if off_img else m_img)
    final_pur = r_pur if int(re.sub(r'[^0-9]', '', r_pur)) > 0 else m_pur
    final_rev = r_rev if int(re.sub(r'[^0-9]', '', r_rev)) > 0 else m_rev

    # 로그 저장
    rank_save = f"{f_rank}|{r_inner}"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, t_cmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI] ---
st.title("🛡️ JOA TOTAL LOCK V203")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규조회", key="main_btn"):
        if nk and np: run_scan_v203(nk, np, nc, nn)

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? AND (note=? OR note IS NULL) ORDER BY id DESC LIMIT 1", (kw, mid, m_val)).fetchone()
    if not row: continue
    
    parts = str(row[6]).split("||")
    img, title = (parts[0] if len(parts)>0 else ""), (parts[2] if len(parts)>2 else kw)
    m_rk = str(row[5]).split("|")[0] if "|" in str(row[5]) else row[5]
    s_rk = str(row[5]).split("|")[1] if "|" in str(row[5]) and str(row[5]).split("|")[1] != "0" else ""

    with st.container():
        st.markdown(f'<div style="border:1px solid #edf2f7; border-radius:15px; padding:20px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            # [P-MID 기반 최장 이름 노출]
            st.markdown(f"**{title}**")
            if m_val: st.info(f"📝 {m_val}")
            st.caption(f"P-MID: {mid} | C-MID: {row[11]}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND note=? AND date LIKE ?", (kw, mid, m_val, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            st.write(f"구매 {row[10]}")
            st.write(f"리뷰 {row[9]}")
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1>", unsafe_allow_html=True)
            if s_rk: st.markdown(f"<div style='text-align:center; color:green; font-weight:bold;'>묶음 {s_rk}위</div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_scan_v203(kw, mid, row[11], m_val)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
