import streamlit as st
import requests
import sqlite3
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote

# [1] 클라우드 환경 설정
DB_PATH = 'joa_final_v12.db'
NAVER_CLIENT_ID = "alIoLSc1k8jVcgeZZ8Ab"
NAVER_CLIENT_SECRET = "DzhNvk3yi3"

st.set_page_config(layout="wide", page_title="JOA IRON SHIELD V193")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    # 금고(product_meta) 테이블: 여기가 사장님의 진짜 데이터를 지키는 곳입니다.
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [정밀 추격 엔진: 고집불통 모드] ---
def run_iron_scan_v193(skw, spmid, scmid, snote, user_id):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 1. 금고에서 '가장 완벽했던 데이터'를 미리 꺼내둡니다.
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    # 로그 전체를 뒤져서 역사상 가장 길었던 이름을 찾아둡니다.
    best_log = db.execute("SELECT name FROM logs WHERE p_mid=? ORDER BY length(name) DESC LIMIT 1", (t_pmid,)).fetchone()
    
    m_name = (best_log[0].split("||")[2] if best_log and "||" in str(best_log[0]) else (meta[0] if meta else skw))
    m_img, m_rev, m_pur = (meta[1], meta[2], meta[3]) if meta else ("", "0", "0")

    with st.spinner(f"🛡️ '{skw}' 데이터 철통 보호 중..."):
        # 공식 API 스캔 (순위 16위는 여기서 정확히 나옵니다)
        url = f"https://openapi.naver.com/v1/search/shop.json?query={quote(skw)}&display=100"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        f_rank, off_name, off_img = 0, skw, ""
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                items = res.json().get('items', [])
                for idx, item in enumerate(items):
                    if str(item.get('productId')) in [t_pmid, str(scmid)]:
                        f_rank, off_name, off_img = idx + 1, re.sub('<[^>]*>', '', item.get('title', '')), item.get('image', '')
                        break
        except: pass

    # --- [SMART JUDGE: 멍청한 업데이트 거부] ---
    # 이름: 가져온 이름이 기존보다 짧으면 무조건 기존 거 유지!
    final_name = off_name if len(off_name) > len(m_name) else m_name
    # 이미지: 한 번이라도 있었으면 절대 잃지 않음!
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    # 구매/리뷰: 이번 스캔 결과는 무조건 0이라고 가정하고, 금고의 데이터만 노출!
    final_pur, final_rev = m_pur, m_rev

    # 금고 업데이트 (순위는 매번 바뀌어도 정보는 최고치 유지)
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur))
    
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, scmid, str(snote)))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.15rem; font-weight: 700; color: #1a202c; line-height: 1.4; margin-bottom: 8px; }
</style>""", unsafe_allow_html=True)

st.title("🛡️ JOA IRON SHIELD V193 (데이터 고정형)")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 업데이트", key="main_btn"):
        if nk and np: run_iron_scan_v193(nk, np, nc, nn, "사장님")

st.divider()

db = get_db()
items = db.execute("SELECT keyword, p_mid, note, MIN(id) FROM logs GROUP BY keyword, p_mid, note ORDER BY MIN(id) ASC").fetchall()

for idx, (kw, mid, m_val, _) in enumerate(items):
    # [핵심] 화면에는 무조건 금고(meta)의 '가장 완벽한 데이터'만 뿌립니다.
    meta = db.execute("SELECT name, img, reviews, purchase FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT * FROM logs WHERE keyword=? AND p_mid=? ORDER BY id DESC LIMIT 1", (kw, mid)).fetchone()
    
    if not row: continue
    
    m_name, m_img, m_rev, m_pur = meta if meta else (kw, "", "0", "0")
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
            # [진짜 긴 이름 강제 노출]
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
            # [진짜 데이터 강제 노출]
            st.markdown(f"<div style='margin-top:10px;'>구매 <b>{m_pur}</b><br>리뷰 <b>{m_rev}</b></div>", unsafe_allow_html=True)
        with col6:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 즉시 업데이트", key=f"btn_{mid}_{idx}"):
                run_iron_scan_v193(kw, mid, row[11], m_val, "사장님")
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
