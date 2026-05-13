import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote
from supabase import create_client, Client
from google import genai
from google.genai import types


# --------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="구글 vs 네이버 뉴스 비교",
    page_icon="📰",
    layout="wide"
)


# --------------------------------------------------
# 2. Secrets 로드
# --------------------------------------------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET")
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")


# --------------------------------------------------
# 3. API Key 확인
# --------------------------------------------------
required_keys = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "NAVER_CLIENT_ID": NAVER_CLIENT_ID,
    "NAVER_CLIENT_SECRET": NAVER_CLIENT_SECRET,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
}

missing_keys = [key for key, value in required_keys.items() if not value]

if missing_keys:
    st.error(f"Secrets 설정이 누락되었습니다: {', '.join(missing_keys)}")
    st.stop()


# --------------------------------------------------
# 4. 클라이언트 초기화
# --------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_resource
def init_gemini():
    return genai.Client(api_key=GEMINI_API_KEY)


supabase = init_supabase()
gemini_client = init_gemini()


# --------------------------------------------------
# 5. 네이버 뉴스 검색 함수
# --------------------------------------------------
def search_naver_news(keyword: str, display: int = 5):
    enc_text = quote(keyword)

    url = (
        "https://openapi.naver.com/v1/search/news.json"
        f"?query={enc_text}&display={display}&sort=sim"
    )

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            st.error(f"네이버 API 오류: {response.status_code}")
            return []

    except Exception as e:
        st.error(f"네이버 뉴스 검색 중 오류 발생: {e}")
        return []


# --------------------------------------------------
# 6. Gemini 뉴스 검색 함수
# --------------------------------------------------
def search_google_news_with_gemini(keyword: str):
    prompt = f"""
'{keyword}' 관련 최신 뉴스 5개를 찾아주세요.

다음 형식으로 정리해주세요.

각 뉴스마다:
1. 제목
2. 출처
3. 날짜
4. URL
5. 2~3문장 요약

마크다운 형식으로 보기 좋게 출력해주세요.
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search_retrieval=types.GoogleSearchRetrieval()
                    )
                ]
            ),
        )

        return response.text

    except Exception as e:
        st.error(f"Gemini 검색 실패: {e}")
        return None


# --------------------------------------------------
# 7. 네이버 뉴스 저장 함수
# --------------------------------------------------
def save_naver_news(keyword: str, items: list):
    saved_count = 0

    for item in items:
        clean_title = (
            item.get("title", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("&quot;", '"')
        )

        clean_description = (
            item.get("description", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("&quot;", '"')
        )

        record = {
            "keyword": keyword,
            "title": clean_title,
            "pub_date": item.get("pubDate"),
            "url": item.get("link"),
            "description": clean_description,
        }

        try:
            supabase.table("naver_news_history").upsert(
                record,
                on_conflict="url"
            ).execute()
            saved_count += 1

        except Exception as e:
            st.warning(f"네이버 뉴스 저장 실패: {clean_title}")
            st.caption(str(e))

    return saved_count


# --------------------------------------------------
# 8. Google/Gemini 검색 기록 저장 함수
# --------------------------------------------------
def save_google_search_result(keyword: str, result_text: str):
    record = {
        "keyword": keyword,
        "title": f"{keyword} Gemini 검색 결과",
        "source": "Google Gemini",
        "news_date": None,
        "url": f"gemini-search-{keyword}",
        "summary": result_text,
    }

    try:
        supabase.table("news_history").upsert(
            record,
            on_conflict="url"
        ).execute()
        return True

    except Exception as e:
        st.warning("Gemini 검색 결과 저장 실패")
        st.caption(str(e))
        return False


# --------------------------------------------------
# 9. DB 조회 함수
# --------------------------------------------------
def show_db_data(table_name: str):
    try:
        response = (
            supabase
            .table(table_name)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        df = pd.DataFrame(response.data)

        if df.empty:
            st.info("저장된 데이터가 없습니다.")
            return df

        search_term = st.text_input(
            f"{table_name} 내 검색어 필터",
            key=f"filter_{table_name}"
        )

        if search_term:
            filter_columns = [col for col in ["keyword", "title", "summary", "description"] if col in df.columns]

            condition = False
            for col in filter_columns:
                condition = condition | df[col].astype(str).str.contains(
                    search_term,
                    case=False,
                    na=False
                )

            df = df[condition]

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            label=f"📥 {table_name} CSV 다운로드",
            data=csv,
            file_name=f"{table_name}.csv",
            mime="text/csv"
        )

        return df

    except Exception as e:
        st.error(f"{table_name} 데이터를 불러오는 중 오류 발생: {e}")
        return pd.DataFrame()


# --------------------------------------------------
# 10. 앱 UI
# --------------------------------------------------
st.title("📰 뉴스 검색 비교 마스터: Google vs Naver")
st.info("하나의 키워드로 Google Gemini AI 요약 뉴스와 Naver 최신 뉴스를 비교하고 Supabase에 저장합니다.")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 통합 뉴스 검색",
    "🔵 구글 검색 기록",
    "🟢 네이버 검색 기록",
    "📊 데이터 분석"
])


# --------------------------------------------------
# Tab 1. 통합 뉴스 검색
# --------------------------------------------------
with tab1:
    st.subheader("🔍 통합 뉴스 검색")

    with st.container(border=True):
        keyword = st.text_input(
            "검색어를 입력하세요",
            placeholder="예: 삼성전자 주가, AI 반도체, 테슬라"
        )

        search_btn = st.button("두 플랫폼 동시 검색", type="primary")

    if search_btn:
        if not keyword:
            st.warning("검색어를 입력해주세요.")
        else:
            col1, col2 = st.columns(2)

            # Google / Gemini 검색
            with col1:
                st.subheader("🌐 Google Search with Gemini")

                with st.spinner("Gemini가 최신 뉴스를 검색하고 요약 중입니다..."):
                    google_result = search_google_news_with_gemini(keyword)

                if google_result:
                    st.markdown(google_result)

                    saved = save_google_search_result(keyword, google_result)

                    if saved:
                        st.success("Google/Gemini 검색 결과가 저장되었습니다.")

            # Naver 검색
            with col2:
                st.subheader("🌿 Naver Search")

                with st.spinner("네이버 뉴스를 검색 중입니다..."):
                    naver_items = search_naver_news(keyword)

                if naver_items:
                    saved_count = save_naver_news(keyword, naver_items)

                    for item in naver_items:
                        clean_title = (
                            item.get("title", "")
                            .replace("<b>", "")
                            .replace("</b>", "")
                            .replace("&quot;", '"')
                        )

                        clean_description = (
                            item.get("description", "")
                            .replace("<b>", "")
                            .replace("</b>", "")
                            .replace("&quot;", '"')
                        )

                        with st.expander(clean_title):
                            st.write(f"📅 날짜: {item.get('pubDate')}")
                            st.write(f"🔗 [기사 원문]({item.get('link')})")
                            st.write(clean_description)

                    st.success(f"네이버 뉴스 {saved_count}건 저장 완료")
                else:
                    st.info("네이버 검색 결과가 없습니다.")


# --------------------------------------------------
# Tab 2. Google 검색 기록
# --------------------------------------------------
with tab2:
    st.subheader("🔵 구글/Gemini 검색 뉴스 내역")
    google_df = show_db_data("news_history")


# --------------------------------------------------
# Tab 3. Naver 검색 기록
# --------------------------------------------------
with tab3:
    st.subheader("🟢 네이버 검색 뉴스 내역")
    naver_df = show_db_data("naver_news_history")


# --------------------------------------------------
# Tab 4. 데이터 분석
# --------------------------------------------------
with tab4:
    st.subheader("📊 데이터 분석")

    try:
        google_res = (
            supabase
            .table("news_history")
            .select("*")
            .execute()
        )

        naver_res = (
            supabase
            .table("naver_news_history")
            .select("*")
            .execute()
        )

        google_df = pd.DataFrame(google_res.data)
        naver_df = pd.DataFrame(naver_res.data)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔵 Google/Gemini 키워드별 저장 건수")

            if not google_df.empty and "keyword" in google_df.columns:
                google_keyword_counts = google_df["keyword"].value_counts()
                st.bar_chart(google_keyword_counts)
            else:
                st.info("Google/Gemini 데이터가 없습니다.")

        with col2:
            st.markdown("### 🟢 Naver 키워드별 저장 건수")

            if not naver_df.empty and "keyword" in naver_df.columns:
                naver_keyword_counts = naver_df["keyword"].value_counts()
                st.bar_chart(naver_keyword_counts)
            else:
                st.info("Naver 데이터가 없습니다.")

        st.markdown("### 📌 플랫폼별 저장 건수 비교")

        platform_counts = pd.DataFrame({
            "platform": ["Google/Gemini", "Naver"],
            "count": [len(google_df), len(naver_df)]
        })

        st.dataframe(platform_counts, use_container_width=True, hide_index=True)
        st.bar_chart(platform_counts.set_index("platform"))

    except Exception as e:
        st.error(f"데이터 분석 중 오류 발생: {e}")
