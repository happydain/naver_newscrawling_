# 📰 AI News Dashboard  
> Google Gemini AI + Naver Open API + Supabase 기반 통합 뉴스 검색 및 분석 플랫폼

---

## 📌 프로젝트 소개

AI 기반 최신 뉴스 검색과 포털 뉴스 검색을 하나의 대시보드에서 통합 제공하는 Streamlit 애플리케이션입니다.

사용자는 하나의 키워드만 입력하면:

- Google Gemini AI 기반 최신 뉴스 요약
- Naver 최신 뉴스 기사 검색
- 검색 결과 자동 저장
- 검색 통계 및 데이터 분석

까지 한 번에 수행할 수 있습니다.

---

# ✨ 주요 기능

## 🔍 통합 뉴스 검색
- Gemini AI 기반 최신 뉴스 검색 및 요약
- Naver Open API 기반 최신 기사 조회
- 두 플랫폼 결과 동시 비교

---

## 💾 자동 DB 저장
- Supabase 연동
- 검색 결과 자동 저장
- URL 기준 중복 제거 처리

---

## 📊 데이터 분석
- 키워드별 검색 빈도
- 날짜별 저장 추이
- 플랫폼별 데이터 비교

---

## 📥 데이터 다운로드
- CSV 다운로드 지원
- 저장 데이터 필터링 가능

---

# 🖥️ 화면 구성

| 탭 | 기능 |
|---|---|
| 🔍 통합 뉴스 검색 | Google + Naver 뉴스 검색 |
| 🔵 구글 검색 기록 | Gemini 검색 저장 내역 |
| 🟢 네이버 검색 기록 | Naver 저장 내역 |
| 📊 데이터 분석 | 검색 통계 및 시각화 |

---

# 🏗️ 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Streamlit |
| AI Engine | Google Gemini API |
| News API | Naver Search API |
| Database | Supabase |
| Data Processing | Pandas |
| Visualization | Plotly |
| Language | Python |

---

# 📂 프로젝트 구조

```bash
.
├── app.py
├── requirements.txt
├── README.md
└── .streamlit
    └── secrets.toml
```

---

# ⚙️ 설치 방법

## 1️⃣ 저장소 Clone

```bash
git clone https://github.com/your-id/ai-news-dashboard.git

cd ai-news-dashboard
```

---

## 2️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

---

# 🔐 환경 변수 설정

`.streamlit/secrets.toml`

```toml
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

NAVER_CLIENT_ID="YOUR_NAVER_CLIENT_ID"
NAVER_CLIENT_SECRET="YOUR_NAVER_CLIENT_SECRET"

SUPABASE_URL="YOUR_SUPABASE_URL"
SUPABASE_KEY="YOUR_SUPABASE_KEY"
```

---

# 🗄️ Supabase 테이블 생성

## Google 뉴스 테이블

```sql
create table news_history (
    id bigint generated always as identity primary key,
    keyword text,
    title text,
    source text,
    news_date text,
    url text unique,
    summary text,
    created_at timestamp default now()
);
```

---

## Naver 뉴스 테이블

```sql
create table naver_news_history (
    id bigint generated always as identity primary key,
    keyword text,
    title text,
    pub_date text,
    url text unique,
    description text,
    created_at timestamp default now()
);
```

---

# ▶️ 실행 방법

```bash
streamlit run app.py
```

---

# 🧠 Google Gemini AI 검색 구조

Gemini의 `Google Search Retrieval` 기능을 사용하여 최신 뉴스 정보를 수집합니다.

```python
response = genai_client.models.generate_content(
    model='gemini-2.0-flash-lite',
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search_retrieval=types.GoogleSearchRetrieval()
            )
        ]
    )
)
```

---

# 🌿 Naver 뉴스 검색 구조

```python
url = "https://openapi.naver.com/v1/search/news.json"
```

수집 데이터:
- 기사 제목
- 발행일
- 기사 링크
- 기사 설명

---

# 📈 데이터 분석 기능

### 제공 분석
- 키워드별 검색량
- 날짜별 저장 추이
- 플랫폼별 데이터 비교

### 향후 확장 예정
- 감성 분석
- 워드클라우드
- 뉴스 카테고리 분류
- 트렌드 예측

---

# 🚀 Streamlit Cloud 배포

## 1. GitHub 업로드
## 2. Streamlit Cloud 연결
## 3. Secrets 등록
## 4. Deploy

---

# 📦 requirements.txt

```txt
streamlit
pandas
requests
plotly
supabase
google-genai
```

---

# ⚠️ 주의사항

## Gemini API
- 무료 티어 사용 시 호출 제한 존재

## Naver API
- 일일 요청 제한 존재

## Supabase
- 운영 시 Row Level Security(RLS) 설정 권장

---

# 📌 향후 개선 방향

- 뉴스 중복 제거 로직 고도화
- AI 뉴스 추천 기능
- 사용자 맞춤 뉴스 큐레이션
- 실시간 뉴스 스트리밍
- 대시보드 UI 개선

---

# 📜 License

MIT License

---

# 👨‍💻 Author

AI News Dashboard Project  
Built with Python, Streamlit, Gemini AI, Supabase 🚀
