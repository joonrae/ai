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

st.set_page_config(layout="wide", page_title="JOA ULTRA STABLE V197")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    # 금고(product_meta)에 메모(note) 필드 추가하여 고정
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT, note TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    conn.commit()
    return conn

# --- [정밀 추격 엔진: V197 지능형 사수] ---
def run_scan_v197(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 1. 기존 데이터 확보
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (skw, "", "0", "0", snote)

    with st.spinner(f"🛡️ '{skw}' 데이터 철통 보호 중..."):
        # 공식 API 스캔 (순위용)
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

    # 2. 데이터 품질 판단 (V152식 길이 비교 유지)
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 구매/리뷰: 0이 들어오면 기존 데이터 유지 (금고 보호)
    final_pur, final_rev = m_pur, m_rev
    
    # 메모 업데이트: 새로 적은 메모가 있으면 그걸로 고정
    final_note = snote if snote else m_note

    # 금고 업데이트
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?,?)", (t_pmid, final_name, final_img, final_rev, final_pur, final_note))
    
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", final_rev, final_pur, scmid, final_note))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .product-title { font-size: 1.1rem; font-weight: 700; color: #1a202c; line-height: 1.4; }
</style>""", unsafe_allow_html=True)

st.title("🛡️ JOA ULTRA STABLE V197")

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모(신규 등록시)")
    if c5.button("🚀 새 상품 등록", key="main_btn"):
        if nk and np: run_scan_v197(nk, np, nc, nn)

st.divider()

db = get_db()
# [중요] 리스트 출력을 P-MID 기준으로 단일화하여 메모 수정시 사라짐 방지
items = db.execute("SELECT keyword, p_mid, MAX(id) FROM logs GROUP BY p_mid ORDER BY MAX(id) DESC").fetchall()

for idx, (kw, mid, _) in enumerate(items):
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT rank, date, cat_mid FROM logs WHERE p_mid=? ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
    
    if not row: continue
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (kw, "", "0", "0", "")
    m_rk = str(row[0]).split("|")[0] if "|" in str(row[0]) else row[0]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            # [수정] 상품명 직접 편집 가능 (한 번 수정하면 절대 안 변함)
            edit_name = st.text_area("📄 상품명 마스터", value=m_name, key=f"t_{mid}", height=65)
            # [수정] 메모 상시 노출 및 수정 가능
            edit_note = st.text_input("📝 메모", value=m_note if m_note else "", key=f"n_{mid}")
            if edit_name != m_name or edit_note != m_note:
                db_u = get_db(); db_u.execute("UPDATE product_meta SET name=?, note=? WHERE p_mid=?", (edit_name, edit_note, mid)); db_u.commit(); db_u.close(); st.rerun()
            st.caption(f"MID: {mid} | C: {row[2]}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE p_mid=? AND date LIKE ?", (mid, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            # [수정] 구매/리뷰 직접 입력 가능 (0점 방지)
            edit_pur = st.text_input("구매", value=m_pur, key=f"p_{mid}")
            edit_rev = st.text_input("리뷰", value=m_rev, key=f"r_{mid}")
            if edit_pur != m_pur or edit_rev != m_rev:
                db_u = get_db(); db_u.execute("UPDATE product_meta SET purchase=?, reviews=? WHERE p_mid=?", (edit_pur, edit_rev, mid)); db_u.commit(); db_u.close(); st.rerun()
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 순위 갱신", key=f"btn_{mid}"):
                run_scan_v197(kw, mid, row[2], edit_note)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
