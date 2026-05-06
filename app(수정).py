import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import requests
from supabase import create_client, Client
import plotly.express as px

# 1. 페이지 및 API 설정
st.set_page_config(page_title="네이버x제미나이 뉴스 봇", layout="wide")

try:
    # 모든 키를 Secrets에서 안전하게 로드
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    NAVER_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
except KeyError as e:
    st.error(f"Secrets 설정 확인 필요: {e}")
    st.stop()

# 클라이언트 초기화
genai_client = genai.Client(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- [기능 1] 네이버 뉴스 가져오기 ---
def get_naver_news(query):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=sim"
    headers = {
        "X-Naver-Client-Id": NAVER_ID,
        "X-Naver-Client-Secret": NAVER_SECRET
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('items', [])
    return []

# --- [기능 2] DB 저장 함수 ---
def save_to_supabase(news_list, keyword):
    for item in news_list:
        try:
            supabase.table("news_history").insert({
                "keyword": keyword,
                "title": item['title'].replace("<b>", "").replace("</b>", ""), # HTML 태그 제거
                "source": item.get('source', 'Naver/Gemini'),
                "news_date": item.get('date', ''),
                "url": item['url'],
                "summary": item['summary']
            }).execute()
        except:
            continue

# --- 메인 화면 ---
st.title("📰 네이버 x Gemini 통합 뉴스 엔진")
st.caption("네이버 실시간 검색 결과와 구글 제미나이의 분석력을 결합합니다.")

tab1, tab2, tab3 = st.tabs(["🔎 통합 검색", "📂 수집 기록", "📊 데이터 통계"])

with tab1:
    keyword = st.text_input("검색어를 입력하세요", placeholder="예: 초전도체 상용화")
    
    if st.button("동시 검색 및 AI 분석 시작"):
        if keyword:
            with st.spinner('네이버 뉴스를 가져오고 Gemini가 분석 중입니다...'):
                try:
                    # 1. 네이버 뉴스 검색 결과 가져오기
                    naver_items = get_naver_news(keyword)
                    naver_context = ""
                    for i, item in enumerate(naver_items):
                        naver_context += f"[{i+1}] 제목: {item['title']}, 링크: {item['link']}\n"

                    # 2. Gemini에게 네이버 결과 요약 + 구글 추가 검색 요청 (Grounding)
                    prompt = f"""
                    다음은 네이버 뉴스 검색 결과야:
                    {naver_context}

                    이 네이버 뉴스들과 네가 Google Search로 직접 찾은 최신 정보를 결합해서 
                    '{keyword}'에 대한 핵심 뉴스 5건을 선별해줘.
                    반드시 아래 JSON 리스트 형식으로만 대답해.

                    [
                      {{
                        "title": "뉴스 제목",
                        "source": "언론사명",
                        "date": "YYYY-MM-DD",
                        "url": "해당 기사 원본 URL",
                        "summary": "3~4문장 요약"
                      }}
                    ]
                    """

                    response = genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearchRetrieval())],
                            temperature=0.1
                        ),
                        contents=prompt
                    )

                    # JSON 데이터 추출
                    res_text = response.text
                    if "```json" in res_text:
                        res_text = res_text.split("```json")[1].split("```")[0]
                    news_data = json.loads(res_text.strip())

                    # 3. 저장 및 출력
                    save_to_supabase(news_data, keyword)
                    st.success(f"네이버와 구글에서 최신 정보를 취합하여 저장했습니다!")

                    for item in news_data:
                        with st.expander(f"📌 {item['title']}", expanded=True):
                            st.write(item['summary'])
                            st.caption(f"출처: {item['source']} | [기사보기]({item['url']})")

                except Exception as e:
                    st.error(f"검색 처리 중 오류: {e}")

# (Tab 2, Tab 3는 이전과 동일한 로직을 사용하시면 됩니다)
with tab2:
    st.subheader("데이터베이스 조회")
    try:
        history = supabase.table("news_history").select("*").order("created_at", desc=True).execute()
        if history.data:
            df = pd.DataFrame(history.data)
            st.dataframe(df[['keyword', 'title', 'source', 'news_date', 'url']], use_container_width=True)
        else:
            st.write("데이터가 없습니다.")
    except Exception as e:
        st.error(f"DB 로드 실패: {e}")

with tab3:
    st.subheader("통계 차트")
    try:
        all_data = supabase.table("news_history").select("keyword").execute()
        if all_data.data:
            df_stat = pd.DataFrame(all_data.data)
            fig = px.pie(df_stat, names='keyword', title="검색 키워드 분포")
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.write("통계 데이터가 부족합니다.")
