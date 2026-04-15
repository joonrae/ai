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
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"
RAPID_KEY = "3846404552mshd40a37048efd7cep108802jsn513f62eb92a3"
RAPID_HOST = "naver-shopping-insights-api-unofficial.p.rapidapi.com"

st.set_page_config(layout="wide", page_title="JOA CLOUD SNIPER V192")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [정밀 추격 엔진: 데이터 사수형] ---
def run_auto_scan_v192(skw, spmid, scmid, snote, user_id):
    t_pmid, t_cmid = str(spmid).strip(), str(scmid).strip()
    db = get_db()
    
    # [1] 기존 데이터 확보 (금고 + 로그 뒤지기)
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    best_log = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (t_pmid,)).fetchone()
    
    m_name = best_log[0].split("||")[2] if best_log and "||" in str(best_log[0]) else (meta[0] if meta else skw)
    m_img, m_rev, m_pur = (meta[1], meta[2], meta[3]) if meta else ("", "0", "0")

    with st.spinner(f"🛡️ '{skw}' 데이터 복구 및 추격 중..."):
        # 공식 API (순위 전용)
        f_rank, off_name, off_img = 0, skw, ""
        try:
            url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, t_cmid]:
                        f_rank, off_name, off_img = idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
                        break
        except: pass

        # RapidAPI (상세 정보용)
        spy = None
        try:
            r_url = f"https://{RAPID_HOST}/v1/naver/products?url={quote(f'https://msearch.shopping.naver.com/catalog/{t_cmid}')}"
            r_headers = {"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": RAPID_HOST}
            r_res = requests.get(r_url, headers=r_headers, timeout=15)
            if r_res.status_code == 200:
                data = r_res.json()
                malls = data.get('malls', []) + data.get('lowPriceHighValueMalls', [])
                for idx, m in enumerate(malls):
                    if str(m.get('nvMid') or m.get('productId')) == t_pmid:
                        spy = {"inner": m.get('rank') or (idx + 1), "name": m.get('productName', ''), "img": m.get('imageUrl', ''), "rev": m.get('reviewCount', 0), "pur": m.get('purchaseCnt', 0)}
                        break
        except: pass

    # --- [데이터 품질 판단] ---
    # 이번에 가져온 이름이 기존 금고보다 길다면 업데이트, 아니면 유지
    final_name = max([m_name, off_name, (spy['name'] if spy else "")], key=len)
    final_img = m_img if (m_img and m_img.startswith("http")) else (spy['img'] if spy and spy['img'] else off_img)
    
    # 구매/리뷰 수: 0이면 절대 저장하지 않고 기존 '최고치' 유지
    if spy and int(spy['pur']) > 0:
        final_pur, final_rev, final_inner = str(spy['pur']), str(spy['rev']), spy['inner']
    else:
        final_pur, final_rev, final_inner = m_pur, m_rev, 0

    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur))
    rank_save = f"{f_rank}|{final_inner}"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, t_cmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링 영역] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.15rem; font-weight: 700; color: #1a202c; line-height: 1.4; margin-bottom: 8px; }
</style>""", unsafe_allow_html=True)

st.title("🚀 JOA CLOUD SNIPER V192")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 추격 시작", key="main_btn"):
        if nk and np: run_auto_scan_v192(nk, np, nc, nn, "사장님")

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # [핵심] 화면에는 무조건 금고(meta)의 '검증된' 데이터만 뿌립니다.
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    # 로그는 날짜별 순위 그래프용으로만 사용
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? ORDER BY id DESC LIMIT 1", (kw, mid)).fetchone()
    
    if not row: continue
    
    # 금고가 비어있으면(신규) 로그에서라도 찾아내기
    if not meta:
        best_in_log = db.execute("SELECT name, reviews, purchase FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (mid,)).fetchone()
        if best_in_log:
            n = best_log_name = best_in_log[0].split("||")[2] if "||" in str(best_in_log[0]) else best_in_log[0]
            db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (mid, n, "", str(best_in_log[1]), str(best_in_log[2])))
            db.commit()
            meta = (n, "", str(best_in_log[1]), str(best_in_log[2]))
        else:
            meta = (kw, "", "0", "0")

    m_name, m_img, m_rev, m_pur = meta
    m_rk = str(row[5]).split("|")[0] if "|" in str(row[5]) else row[5]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 1.8, 4.2, 5.0, 1.8, 2.8])
        with col1: st.subheader(idx + 1)
        with col2:
            if m_img.startswith("http"): st.image(m_img, width=140)
            else: st.info("🖼️ 사수 중")
        with col3:
            st.markdown(f"### 🔍 {kw}")
            # [진짜 긴 이름 노출]
            st.markdown(f"<div class='product-title'>{m_name}</div>", unsafe_allow_html=True)
            if m_val and m_val != "None": st.caption(f"📝 {m_val}")
            st.caption(f"P: {mid} | C: {row[11]}")
        with col4:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE keyword=? AND p_mid=? AND date LIKE ?", (kw, mid, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col5:
            # [진짜 높은 수치 노출]
            st.markdown(f"<div style='margin-top:10px;'>구매 <b>{m_pur}</b><br>리뷰 <b>{m_rev}</b></div>", unsafe_allow_html=True)
        with col6:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 업데이트", key=f"btn_{mid}_{idx}"):
                run_auto_scan_v192(kw, mid, row[11], m_val, "사장님")
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
