import streamlit as st
import pandas as pd
import json
import re
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
import plotly.express as px
from datetime import datetime
import os
from urllib.parse import quote

# -------------------------------------------------------------------
# 1. 페이지 기본 설정
# -------------------------------------------------------------------
st.set_page_config(page_title="최신 뉴스 검색 및 저장 앱", page_icon="📰", layout="wide")
# --- 1. 설정 및 보안 키 로드 ---
st.set_page_config(page_title="구글 vs 네이버 뉴스 비교", layout="wide")

# -------------------------------------------------------------------
# 2. 비밀 키(Secrets) 불러오기 및 초기화
# -------------------------------------------------------------------
# Streamlit Cloud의 Secrets(또는 로컬의 .streamlit/secrets.toml)에서 키를 읽어옵니다.
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# Secrets 로드 (Streamlit Cloud의 Secrets 메뉴에 입력해야 함)
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY")
NAVER_ID = st.secrets.get("NAVER_CLIENT_ID")
NAVER_SECRET = st.secrets.get("NAVER_CLIENT_SECRET")
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

# Supabase 클라이언트 연결
@st.cache_resource # 데이터베이스 연결을 매번 하지 않고 캐싱(저장)해두어 속도를 높입니다.
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
# 클라이언트 초기화
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GEMINI_KEY)

supabase = init_supabase()

# Gemini 클라이언트 연결 (API 키 명시적 전달)
client = genai.Client(api_key=GEMINI_API_KEY)
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

# -------------------------------------------------------------------
# 3. 화면 UI 구성 (3개의 탭 만들기)
# -------------------------------------------------------------------
st.title("📰 AI 최신 뉴스 검색 & 자동 저장기")
st.info("💡 안내: Gemini API 무료 티어를 사용하며, 검색된 결과는 자동으로 Supabase DB에 저장됩니다.")
# --- 3. UI 구성 ---
st.title("📰 뉴스 검색 비교 마스터: Google vs Naver")
st.info("한 번의 검색으로 구글(AI 요약)과 네이버(최신 기사) 결과를 비교하고 DB에 저장합니다.")

# 화면을 3개의 탭으로 나눕니다.
tab1, tab2, tab3 = st.tabs(["🔍 검색하기", "💾 저장된 뉴스 보기", "📊 통계 분석"])
tab1, tab2, tab3, tab4 = st.tabs(["🔍 통합 뉴스 검색", "🔵 구글 검색 기록", "🟢 네이버 검색 기록", "📊 데이터 분석"])

# ==========================================
# 탭 1: 검색하기 및 자동 저장 로직
# ==========================================
# --- [Tab 1: 통합 검색 및 비교] ---
with tab1:
    st.subheader("새로운 뉴스 검색")
    keyword = st.text_input("검색할 뉴스 키워드를 입력하세요 (예: 테슬라, 올림픽)")
    
    if st.button("뉴스 검색 및 자동 저장", type="primary"):
        if not keyword:
            st.warning("키워드를 입력해주세요!")
        else:
            with st.spinner("최신 뉴스를 검색하고 DB에 저장하는 중입니다..."):
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
                    # 1. Gemini AI에 검색 및 요약 요청
                    prompt = f"""
                    다음 키워드에 대한 가장 최신 뉴스 5건을 검색하고 요약해주세요: '{keyword}'
                    
                    [요구사항]
                    1. Google Search를 사용해 최신 정보를 가져오세요.
                    2. 각 뉴스별로 제목(title), 출처(source), 날짜(date), 원본 URL(url), 3~4문장의 요약(summary)을 작성하세요.
                    3. 응답은 반드시 아래 형태의 JSON 배열(Array)로만 출력해야 합니다.[
                        {{
                            "title": "뉴스 제목",
                            "source": "언론사 이름",
                            "news_date": "YYYY-MM-DD",
                            "url": "https://...",
                            "summary": "3~4문장의 요약 내용"
                        }}
                    ]
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-lite',
                    prompt = f"'{keyword}' 관련 최신 뉴스 5개를 찾아 [제목 / URL / 2줄 요약] 형식으로 알려줘."
                    response = genai_client.models.generate_content(
                        model='gemini-2.0-flash-lite',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[{"google_search": {}}],
                            temperature=0.2
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

                    # 2. JSON 결과 추출
                    raw_text = response.text
                    match = re.search(r'\[\s*\{.*?\}\s*\]', raw_text, re.DOTALL)
                    clean_json_str = match.group(0) if match else raw_text
                    news_data = json.loads(clean_json_str)
                    
                    # 3. 화면에 출력 및 Supabase DB에 저장
                    saved_count = 0
                    duplicate_count = 0
                    
                    st.success(f"'{keyword}'에 대한 검색이 완료되었습니다!")
                    
                    for news in news_data:
                        # 화면에 카드 형태로 보여주기
                        with st.container(border=True):
                            st.markdown(f"#### [{news.get('title')}]({news.get('url')})")
                            st.caption(f"🏢 **출처:** {news.get('source')} | 📅 **날짜:** {news.get('news_date')}")
                            st.write(news.get('summary'))
                        
                        # DB 저장을 위한 데이터 조립 (keyword 추가)
                        db_record = {
                    # 네이버 DB 저장
                    try:
                        supabase.table("naver_news_history").upsert({
                            "keyword": keyword,
                            "title": news.get("title"),
                            "source": news.get("source"),
                            "news_date": news.get("news_date"),
                            "url": news.get("url"),
                            "summary": news.get("summary")
                        }
                        
                        # DB에 저장 시도
                        try:
                            supabase.table("news_history").insert(db_record).execute()
                            saved_count += 1
                        except Exception as db_e:
                            # url이 UNIQUE이므로, 이미 존재하는 URL이면 에러가 발생합니다.
                            # 이를 이용해 중복 저장을 건너뜁니다.
                            if "duplicate key value" in str(db_e) or "23505" in str(db_e):
                                duplicate_count += 1
                            else:
                                st.error(f"DB 저장 중 에러 발생: {db_e}")
                    
                    # 저장 결과 요약 알림
                    st.toast(f"✅ 새로 저장됨: {saved_count}건 | 🔄 중복 생략됨: {duplicate_count}건")
                            "title": clean_title,
                            "pub_date": item['pubDate'],
                            "url": item['link'],
                            "description": item['description']
                        }, on_conflict="url").execute()
                    except:
                        pass
                st.success(f"네이버 뉴스 {len(naver_items)}건 저장 완료!")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
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

# ==========================================
# 탭 2: 저장된 뉴스 보기
# ==========================================
with tab2:
    st.subheader("데이터베이스에 저장된 뉴스 목록")
    
    # Supabase에서 데이터 불러오기 (최신순 정렬)
    try:
        response = supabase.table("news_history").select("*").order("created_at", desc=True).execute()
        db_data = response.data
        
        if db_data:
            df = pd.DataFrame(db_data)
            
            # 사용자 편의를 위한 키워드 검색 필터 제공
            search_term = st.text_input("목록 내 키워드 필터링 (제목, 키워드 기준)", "")
            
            if search_term:
                # 대소문자 구분 없이 필터링
                df = df[df["keyword"].str.contains(search_term, case=False, na=False) | 
                        df["title"].str.contains(search_term, case=False, na=False)]
            
            # 화면에 표(Dataframe) 형태로 보여주기
            st.dataframe(
                df[["keyword", "title", "source", "news_date", "url", "created_at"]], 
                use_container_width=True,
                hide_index=True
            )
            
            # CSV 다운로드 기능
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 현재 표의 데이터 CSV 다운로드",
                data=csv_data,
                file_name="saved_news_history.csv",
                mime="text/csv"
            )
        else:
            st.info("아직 저장된 뉴스가 없습니다. 탭 1에서 뉴스를 검색해보세요!")
            
    except Exception as e:
        st.error(f"DB 데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.subheader("🔵 구글/Gemini 검색 뉴스 내역")
    # 기존 구글 테이블명에 맞춰 호출
    show_db_data("news_history")

# ==========================================
# 탭 3: 통계 분석 (차트)
# ==========================================
with tab3:
    st.subheader("검색 통계 대시보드")
    
    if 'db_data' in locals() and db_data: # 탭 2에서 불러온 데이터가 있다면 활용
        df_stats = pd.DataFrame(db_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📌 키워드별 누적 검색 건수**")
            # 키워드별로 그룹화하여 개수 세기
            keyword_counts = df_stats['keyword'].value_counts()
            # Streamlit 내장 바 차트로 그리기
            st.bar_chart(keyword_counts)
            
        with col2:
            st.markdown("**📌 일자별 DB 저장 건수**")
            # created_at (예: 2024-05-01T12:00:00) 문자열에서 날짜(YYYY-MM-DD)만 추출
            df_stats['date_only'] = pd.to_datetime(df_stats['created_at']).dt.date
            # 일자별로 개수 세기
            date_counts = df_stats['date_only'].value_counts().sort_index()
            # Streamlit 내장 라인 차트로 그리기
            st.line_chart(date_counts)
    else:
        st.info("통계를 표시할 데이터가 부족합니다.")
    st.subheader("🟢 네이버 검색 뉴스 내역")
    show_db_data("naver_news_history")

# --- [Tab 4: 데이터 분석] ---
with tab4:
    st.subheader("📊 플랫폼별 검색 비중 분석")
    # 구글 vs 네이버 데이터 합산 비교 차트 등을 추가할 수 있습니다.
    st.write("여기에 키워드별 수집 비중 차트를 구성하세요.")
