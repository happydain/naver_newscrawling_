import streamlit as st
import pandas as pd
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
import plotly.express as px
from datetime import datetime
import os
from urllib.parse import quote

# --- 1. 설정 및 보안 키 로드 ---
st.set_page_config(page_title="구글 vs 네이버 뉴스 비교", layout="wide")

# Secrets 로드 (Streamlit Cloud의 Secrets 메뉴에 입력해야 함)
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY")
NAVER_ID = st.secrets.get("NAVER_CLIENT_ID")
NAVER_SECRET = st.secrets.get("NAVER_CLIENT_SECRET")
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

# 클라이언트 초기화
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GEMINI_KEY)

# --- 2. 네이버 뉴스 검색 함수 ---
def search_naver_news(query):
    encText = quote(query)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=5&sort=sim"
    headers = {
        "X-Naver-Client-Id": NAVER_ID,
        "X-Naver-Client-Secret": NAVER_SECRET
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        st.error(f"네이버 API 오류: {response.status_code}")
        return []

# --- 3. UI 구성 ---
st.title("📰 뉴스 검색 비교 마스터: Google vs Naver")
st.info("한 번의 검색으로 구글(AI 요약)과 네이버(최신 기사) 결과를 비교하고 DB에 저장합니다.")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 통합 뉴스 검색", "🔵 구글 검색 기록", "🟢 네이버 검색 기록", "📊 데이터 분석"])

# --- [Tab 1: 통합 검색 및 비교] ---
with tab1:
    with st.container(border=True):
        keyword = st.text_input("검색어를 입력하세요", placeholder="예: 삼성전자 주가")
        search_btn = st.button("두 플랫폼 동시 검색", type="primary")

    if search_btn and keyword:
        col1, col2 = st.columns(2)

        # --- 구글(Gemini) 검색 ---
        with col1:
            st.subheader("🌐 Google Search (AI 요약)")
            with st.spinner("구글 뉴스 수집 중..."):
                try:
                    prompt = f"'{keyword}' 관련 최신 뉴스 5개를 찾아 [제목 / URL / 2줄 요약] 형식으로 알려줘."
                    response = genai_client.models.generate_content(
                        model='gemini-2.0-flash-lite',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                        )
                    )
                    st.markdown(response.text)
                    # (여기서 구글 DB 저장 로직 수행 - 기존 방식과 동일)
                except Exception as e:
                    st.error(f"구글 검색 실패: {e}")

        # --- 네이버 검색 ---
        with col2:
            st.subheader("🌿 Naver Search (최신 기사)")
            with st.spinner("네이버 뉴스 수집 중..."):
                naver_items = search_naver_news(keyword)
                for item in naver_items:
                    clean_title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
                    with st.expander(clean_title):
                        st.write(f"📅 날짜: {item['pubDate']}")
                        st.write(f"🔗 [기사 원문]({item['link']})")
                        st.write(item['description'].replace("<b>", "").replace("</b>", ""))
                    
                    # 네이버 DB 저장
                    try:
                        supabase.table("naver_news_history").upsert({
                            "keyword": keyword,
                            "title": clean_title,
                            "pub_date": item['pubDate'],
                            "url": item['link'],
                            "description": item['description']
                        }, on_conflict="url").execute()
                    except:
                        pass
                st.success(f"네이버 뉴스 {len(naver_items)}건 저장 완료!")

# --- [Tab 2 & 3: DB 조회] ---
def show_db_data(table_name):
    res = supabase.table(table_name).select("*").order("created_at", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(f"{table_name} 다운로드 (CSV)", data=csv, file_name=f"{table_name}.csv")
    else:
        st.write("저장된 데이터가 없습니다.")

with tab2:
    st.subheader("🔵 구글/Gemini 검색 뉴스 내역")
    # 기존 구글 테이블명에 맞춰 호출
    show_db_data("news_history")

with tab3:
    st.subheader("🟢 네이버 검색 뉴스 내역")
    show_db_data("naver_news_history")

# --- [Tab 4: 데이터 분석] ---
with tab4:
    st.subheader("📊 플랫폼별 검색 비중 분석")
    # 구글 vs 네이버 데이터 합산 비교 차트 등을 추가할 수 있습니다.
    st.write("여기에 키워드별 수집 비중 차트를 구성하세요.")
