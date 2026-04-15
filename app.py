import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = 'joa_final_v12.db'

st.set_page_config(layout="wide", page_title="DB 데이터 투시경")
st.title("🔎 현재 장부(DB) 내부 기록 확인")

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

db = get_db()
p_mid = st.text_input("확인할 P-MID를 입력하세요 (예: 90876869616)")

if p_mid:
    # 해당 MID의 모든 기록을 싹 다 가져옵니다.
    df = pd.read_sql_query(f"SELECT id, date, keyword, name, purchase, reviews FROM logs WHERE p_mid='{p_mid}' ORDER BY id DESC", db)
    
    if df.empty:
        st.error("이 P-MID에 대한 기록이 장부에 단 하나도 없습니다.")
    else:
        st.warning(f"총 {len(df)}개의 기록이 발견되었습니다. (최근 순)")
        st.dataframe(df, use_container_width=True)
db.close()
