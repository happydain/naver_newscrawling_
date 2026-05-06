import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
from supabase import create_client, Client
import plotly.express as px

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="AI 뉴스 큐레이션", layout="wide")

# 2. Secrets에서 API 키 가져오기
# Streamlit Cloud의 Settings -> Secrets에 설정되어 있어야 합니다.
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("Secrets 설정이 누락되었습니다. GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY를 확인해주세요.")
    st.stop()

# 3. 클라이언트 초기화
genai_client = genai.Client(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 헬퍼 함수: DB 저장 ---
def save_to_supabase(news_list, keyword):
    for item in news_list:
        try:
            # url이 고유값(UNIQUE)이므로 중복 저장 시 에러가 나며 자동 스킵됩니다.
            supabase.table("news_history").insert({
                "keyword": keyword,
                "title": item.get('title', '제목 없음'),
                "source": item.get('source', '출처 미상'),
                "news_date": item.get('date', ''),
                "url": item.get('url', ''),
                "summary": item.get('summary', '')
            }).execute()
        except Exception:
            continue # 중복 데이터 에러 발생 시 무시하고 다음으로 진행

# --- 메인 UI ---
st.title("🚀 Gemini 실시간 뉴스 검색 시스템")
st.info("💡 Gemini 2.0 Flash 모델을 사용하여 구글 실시간 검색을 수행합니다. (무료 티어: 분당 15회)")

tab1, tab2, tab3 = st.tabs(["🔎 실시간 뉴스 검색", "📂 수집 기록 보기", "📊 데이터 통계"])

# --- Tab 1: 실시간 뉴스 검색 ---
with tab1:
    col1, col2 = st.columns([4, 1])
    with col1:
        keyword = st.text_input("검색어를 입력하세요", placeholder="예: 삼성전자 엔비디아 협력 최신 뉴스")
    with col2:
        st.write(" ") # 간격 맞춤
        search_btn = st.button("검색 및 저장", use_container_width=True)

    if search_btn and keyword:
        with st.spinner('구글 검색을 통해 최신 정보를 분석 중...'):
            try:
                # 1. Gemini Search Grounding 호출 (최신 정보 검색 강제)
                # 검색 기능을 쓸 때는 JSON 모드 옵션을 동시에 쓸 수 없어 프롬프트로 제어합니다.
                prompt = f"""
                Google Search를 사용하여 '{keyword}'에 대한 아주 최신 뉴스 5건을 찾아줘.
                결과는 반드시 아래 JSON 형식을 지켜서 응답하고, 다른 설명은 하지마.
                
                형식:
                [
                  {{
                    "title": "뉴스 제목",
                    "source": "언론사명",
                    "date": "날짜(YYYY-MM-DD)",
                    "url": "원본 기사 URL",
                    "summary": "3~4문장으로 핵심 내용 요약"
                  }}
                ]
                """
                
                response = genai_client.models.generate_content(
                    model="gemini-2.0-flash", # 검색 능력이 더 좋은 일반 Flash 모델 권장
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearchRetrieval())],
                        temperature=0
                    ),
                    contents=prompt
                )

                # 2. JSON 파싱 (마크다운 코드 블록 제거)
                res_text = response.text
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0]
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0]
                
                news_data = json.loads(res_text.strip())
                
                # 3. 화면 출력 및 DB 저장
                if news_data:
                    save_to_supabase(news_data, keyword)
                    st.success(f"'{keyword}' 관련 최신 뉴스 5건을 성공적으로 저장했습니다.")
                    
                    for item in news_data:
                        with st.container():
                            st.markdown(f"#### [{item['title']}]({item['url']})")
                            c1, c2 = st.columns([1, 5])
                            c1.caption(f"📅 {item['date']}\n\n🏢 {item['source']}")
                            c2.write(item['summary'])
                            st.divider()
                else:
                    st.warning("뉴스 검색 결과를 가져오지 못했습니다.")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# --- Tab 2: 수집 기록 보기 ---
with tab2:
    st.subheader("데이터베이스 조회")
    db_search = st.text_input("DB 내 키워드 검색 (엔터)")
    
    try:
        query = supabase.table("news_history").select("*").order("created_at", desc=True)
        if db_search:
            query = query.ilike("keyword", f"%{db_search}%")
        
        history = query.execute()
        
        if history.data:
            df = pd.DataFrame(history.data)
            # 깔끔한 표로 보여주기
            st.dataframe(df[['keyword', 'title', 'source', 'news_date', 'created_at']], use_container_width=True)
            
            # CSV 다운로드 기능
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 전체 기록 CSV 다운로드", data=csv, file_name="news_history.csv", mime="text/csv")
        else:
            st.write("저장된 데이터가 없습니다.")
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

# --- Tab 3: 데이터 통계 ---
with tab3:
    st.subheader("수집 통계 대시보드")
    try:
        all_res = supabase.table("news_history").select("keyword, created_at").execute()
        if all_res.data:
            df_all = pd.DataFrame(all_res.data)
            df_all['created_at'] = pd.to_datetime(df_all['created_at']).dt.date
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("📊 키워드별 뉴스 점유율")
                fig1 = px.pie(df_all, names='keyword', hole=0.3)
                st.plotly_chart(fig1, use_container_width=True)
            with col_b:
                st.write("📈 일자별 수집 트렌드")
                date_counts = df_all.groupby('created_at').size().reset_index(name='count')
                fig2 = px.line(date_counts, x='created_at', y='count', markers=True)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("통계를 낼 데이터가 없습니다.")
    except Exception as e:
        st.error(f"통계 데이터를 불러오지 못했습니다: {e}")
