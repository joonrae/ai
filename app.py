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

st.set_page_config(layout="wide", page_title="JOA DB REPAIR V198")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    # 테이블 생성
    conn.execute("CREATE TABLE IF NOT EXISTS product_meta (p_mid TEXT PRIMARY KEY, name TEXT, img TEXT, reviews TEXT, purchase TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, keyword TEXT, p_mid TEXT, rank TEXT, name TEXT, price TEXT, mall TEXT, reviews TEXT, purchase TEXT, cat_mid TEXT, note TEXT)")
    
    # [핵심] 기존 DB에 'note' 컬럼이 없는 경우를 대비한 수리 코드
    try:
        conn.execute("ALTER TABLE product_meta ADD COLUMN note TEXT")
    except:
        pass # 이미 컬럼이 있으면 무시
    
    conn.commit()
    return conn

# --- [정밀 추격 엔진] ---
def run_scan_v198(skw, spmid, scmid, snote):
    t_pmid = str(spmid).strip()
    db = get_db()
    
    # 기존 데이터 로드
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (t_pmid,)).fetchone()
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (skw, "", "0", "0", snote)

    with st.spinner(f"🛡️ '{skw}' 데이터 사수 중..."):
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

    # 이름 사수 (길이 비교)
    final_name = off_name if len(off_name) > len(m_name) else m_name
    final_img = m_img if (m_img and m_img.startswith("http")) else off_img
    
    # 메모 업데이트
    final_note = snote if snote else m_note

    # 금고 업데이트 (구매/리뷰는 기존꺼 유지)
    db.execute("INSERT OR REPLACE INTO product_meta VALUES (?,?,?,?,?,?)", (t_pmid, final_name, final_img, m_rev, m_pur, final_note))
    
    rank_save = f"{f_rank}|0"
    save_data = f"{final_img}||0||{final_name}||{final_name}"
    db.execute("INSERT INTO logs (user_id, date, keyword, p_mid, rank, name, price, mall, reviews, purchase, cat_mid, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("사장님", datetime.now().strftime("%Y-%m-%d %H:%M"), skw, t_pmid, rank_save, save_data, "0", "피크스페이스", m_rev, m_pur, scmid, final_note))
    db.commit(); db.close(); st.rerun()

# --- [UI 렌더링] ---
st.markdown("""<style>
    .product-box { border: 2px solid #edf2f7; border-radius: 15px; padding: 25px; background: white; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.01); }
</style>""", unsafe_allow_html=True)

st.title("🛡️ JOA DATA KEEPER V198")

# 신규 등록
with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.2])
    nk, np, nc, nn = c1.text_input("키워드"), c2.text_input("P-MID"), c3.text_input("C-MID"), c4.text_input("메모")
    if c5.button("🚀 신규 등록/조회", key="main_btn"):
        if nk and np: run_scan_v198(nk, np, nc, nn)

st.divider()

db = get_db()
# P-MID 기준으로 단일화
items = db.execute("SELECT keyword, p_mid, MAX(id) FROM logs GROUP BY p_mid ORDER BY MAX(id) DESC").fetchall()

for idx, (kw, mid, _) in enumerate(items):
    meta = db.execute("SELECT name, img, reviews, purchase, note FROM product_meta WHERE p_mid=?", (mid,)).fetchone()
    row = db.execute("SELECT rank, cat_mid FROM logs WHERE p_mid=? ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
    
    if not row: continue
    m_name, m_img, m_rev, m_pur, m_note = meta if meta else (kw, "", "0", "0", "")
    m_rk = str(row[0]).split("|")[0] if "|" in str(row[0]) else row[0]

    with st.container():
        st.markdown('<div class="product-box">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([0.5, 5.0, 5.0, 1.8, 2.5])
        with col1: st.subheader(idx + 1)
        with col2:
            st.markdown(f"### 🔍 {kw}")
            edit_name = st.text_area("📄 상품명(수정가능)", value=m_name, key=f"t_{mid}", height=65)
            edit_note = st.text_input("📝 메모", value=m_note if m_note else "", key=f"n_{mid}")
            if edit_name != m_name or edit_note != m_note:
                db_u = get_db(); db_u.execute("UPDATE product_meta SET name=?, note=? WHERE p_mid=?", (edit_name, edit_note, mid)); db_u.commit(); db_u.close(); st.rerun()
            st.caption(f"MID: {mid} | C: {row[1]}")
        with col3:
            h_html = "<div style='display:flex; gap:3px;'>"
            for d in range(8):
                t = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                h_rank = db.execute("SELECT rank FROM logs WHERE p_mid=? AND date LIKE ?", (mid, f"{t}%")).fetchone()
                rk = str(h_rank[0]).split("|")[0] if h_rank and "|" in str(h_rank[0]) else "-"
                h_html += f"<div style='flex:1; border:1px solid #e2e8f0; padding:5px; text-align:center; background:#f8f9fa; border-radius:8px;'><div style='font-size:0.6rem; color:#a0aec0;'>{t[5:]}</div><div style='font-size:0.8rem; font-weight:bold;'>{rk if rk != '0' else '100+'}위</div></div>"
            st.markdown(h_html + "</div>", unsafe_allow_html=True)
        with col4:
            edit_pur = st.text_input("구매", value=m_pur, key=f"p_{mid}")
            edit_rev = st.text_input("리뷰", value=m_rev, key=f"r_{mid}")
            if edit_pur != m_pur or edit_rev != m_rev:
                db_u = get_db(); db_u.execute("UPDATE product_meta SET purchase=?, reviews=? WHERE p_mid=?", (edit_pur, edit_rev, mid)); db_u.commit(); db_u.close(); st.rerun()
        with col5:
            st.markdown(f"<div style='text-align:center;'><h1 style='font-size:3.5rem; margin:0;'>{m_rk if m_rk != '0' else '100+'}위</h1></div>", unsafe_allow_html=True)
            if st.button("🔄 순위 갱신", key=f"btn_{mid}"):
                run_scan_v198(kw, mid, row[1], edit_note)
        st.markdown('</div>', unsafe_allow_html=True)
db.close()
