# AI-Powered Smart Web Crawler

MCP(Model Context Protocol) 기반 지능형 웹 크롤링 시스템으로, 4개의 다중 크롤링 엔진을 활용하여 다양한 사이트에 적응적으로 대응하는 스마트 크롤러입니다.

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+ (권장: Python 3.9+)
- Node.js 18+ (프론트엔드 사용 시)
- OpenAI API 키 (필수)

### 1️⃣ 프로젝트 클론 및 디렉토리 이동
```bash
git clone <repository-url>
cd ai-crawler
```

### 2️⃣ Python 의존성 설치
```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 백엔드 + MCP 서버 의존성 설치 (52개 패키지)
pip install -r requirements.txt

# 플레이라이트 브라우저 설치 (필수)
playwright install
```

### 3️⃣ 환경변수 설정
```bash
# 환경 설정 파일 복사
cp env.example .env

# .env 파일을 열어서 최소한 OpenAI API 키 설정 (필수)
# OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 4️⃣ 백엔드 서버 실행 (단일 명령어)
```bash
cd backend
python main.py
```
**🎯 서버가 http://localhost:8001 에서 실행됩니다**

### 5️⃣ API 테스트 (즉시 사용 가능)
```bash
# 헬스체크
curl http://localhost:8001/health

# 크롤링 테스트
curl -X POST "http://localhost:8001/api/v1/crawl/unified" \
  -H "Content-Type: application/json" \
  -d '{"text": "https://example.com"}'

# API 문서 확인: http://localhost:8001/docs
```

### 6️⃣ 프론트엔드 실행 (선택사항)
```bash
# 새 터미널에서
cd frontend
npm install
npm run dev

# 프론트엔드: http://localhost:3000
```

### 🎉 즉시 사용 가능!
- **API 서버**: http://localhost:8001
- **API 문서**: http://localhost:8001/docs  
- **웹 UI**: http://localhost:3000 (프론트엔드 실행 시)

---

## 🚀 주요 특징

- **🧠 MCP 표준 기반 AI 분석**: OpenAI MCP 표준을 준수하는 지능형 사이트 분석 시스템
- **⚡ 4개 크롤링 엔진**: Firecrawl, Crawl4AI, Playwright, Requests - 각각의 장점 활용
- **🎯 자연어 처리**: "네이버 뉴스 제목만 추출해줘" 형태의 자연어 입력 지원
- **🔄 자동 폴백 시스템**: 한 엔진이 실패하면 자동으로 다음 엔진으로 전환
- **📊 다층 품질 관리**: 크롤링 결과를 0-100점으로 정량 평가 및 실시간 검증
- **🌐 실시간 WebSocket**: 진행 상황을 실시간으로 모니터링
- **📦 병렬 대량 처리**: 최대 5개 URL 동시 병렬 처리
- **🧹 고급 텍스트 후처리**: AI 기반 불필요 요소 제거 및 구조화
- **💬 채팅 기반 UI**: React 19 + Next.js 15 기반 직관적 대화형 인터페이스

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │◄──►│   Backend        │◄──►│  MCP Server     │
│   (Next.js 15)  │    │   (FastAPI)      │    │  (AI Analysis)  │
│   - 채팅 UI     │    │   - REST API     │    │   - SiteAnalyzer│
│   - 실시간 추적  │    │   - WebSocket    │    │   - StructureDetector│
│   - 결과 표시    │    │   - 엔진 관리     │    │   - QualityValidator│
│   - React 19    │    │   - 자연어 파싱   │    │   - ContentExtractor│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │          ┌───────────────────────┐            │
         │          │  MultiEngineCrawler   │            │
         │          │  ┌─────────────────┐  │            │
         │          │  │ 1. Firecrawl    │  │◄───────────┤
         │          │  │ 2. Crawl4AI     │  │            │
         │          │  │ 3. Playwright   │  │            │
         │          │  │ 4. Requests     │  │            │
         │          │  └─────────────────┘  │            │
         │          └───────────────────────┘            │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  결과 다운로드    │    │  JSON 파일 저장   │    │  텍스트 후처리    │
│  (여러 포맷)     │    │  (results/)      │    │  (품질 향상)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔍 지능형 분석 시스템

### MCP 도구별 분석 기능
- **SiteAnalyzer**: SPA/SSR/Static 판별, JavaScript 복잡도 분석, 안티봇 시스템 감지
- **StructureDetector**: 콘텐츠 구조 패턴 분석, 계층구조 식별
- **CrawlerSelector**: 최적 크롤러 선택 및 엔진별 설정 최적화
- **QualityValidator**: 실시간 품질 검증 및 재시도 필요성 판단
- **ContentExtractor**: 선택적 콘텐츠 추출 (제목, 가격, 본문, 리뷰 등)

### 자동 크롤링 전략
```python
crawler_strategies = {
    "complex_spa": {
        "primary": "crawl4ai",      # AI 기반 SPA 크롤링
        "fallback": ["firecrawl", "playwright", "requests"],
        "characteristics": ["React/Vue", "무한스크롤", "복잡한 JS"]
    },
    "anti_bot_heavy": {
        "primary": "playwright",    # 브라우저 우회
        "fallback": ["firecrawl", "crawl4ai", "requests"],
        "characteristics": ["Cloudflare", "reCAPTCHA", "강한 봇 차단"]
    },
    "ai_analysis_needed": {
        "primary": "crawl4ai",      # LLM 추출 전략
        "fallback": ["firecrawl", "playwright", "requests"],
        "characteristics": ["복잡한 구조", "의미적 추출", "AI 분류 필요"]
    },
    "simple_static": {
        "primary": "requests",      # 빠른 처리
        "fallback": ["crawl4ai", "firecrawl", "playwright"],
        "characteristics": ["정적 HTML", "빠른 처리", "단순 구조"]
    }
}
```

## 📋 지원하는 사이트 유형

### 🎯 지능형 엔진 선택 전략
- **복잡한 SPA**: React, Vue.js → **Crawl4AI** (AI 기반 추출)
- **안티봇 사이트**: Cloudflare, reCAPTCHA → **Playwright** (브라우저 우회)
- **AI 분석 필요**: 쇼핑몰, 복잡한 구조 → **Crawl4AI** (LLM 기반 추출)
- **표준 동적 사이트**: 로그인 필요, 세밀한 제어 → **Playwright** (브라우저 자동화)
- **정적 사이트**: 빠른 처리 → **Requests** (HTTP 직접 요청)

## 💬 자연어 크롤링 기능

### 지원하는 입력 형태
```bash
# 1. URL만 입력 (단일 크롤링)
"https://naver.com"

# 2. 자연어 + URL (선택적 추출)
"https://shopping.naver.com 에서 가격만 추출해줘"
"네이버 뉴스 제목만 가져와줘: https://news.naver.com"

# 3. 다중 URL (멀티 크롤링)
"https://site1.com https://site2.com https://site3.com"

# 4. 도메인만 입력 (자동 프로토콜 추가)
"www.naver.com"
```

### 타겟 콘텐츠 자동 감지
- **제목**: "제목", "타이틀", "title", "헤드라인"
- **가격**: "가격", "price", "비용", "금액", "요금"
- **본문**: "본문", "내용", "content", "글", "article"
- **리뷰**: "리뷰", "review", "후기", "평가", "댓글"
- **요약**: "요약", "summary", "개요", "핵심", "정리"

## 🛠️ 상세 설치 가이드

> 📖 **빠른 시작**: 위의 [Quick Start Guide](#-quick-start-guide)를 먼저 확인하세요!

### 고급 설정 옵션

#### 🔧 플레이라이트 추가 설정
```bash
# 특정 브라우저만 설치 (공간 절약)
playwright install chromium  # Chrome/Edge만
playwright install firefox   # Firefox만
playwright install webkit    # Safari만
```

#### 🐳 Docker 실행 (선택사항)
```bash
# 도커 이미지 빌드 및 실행
docker build -t ai-crawler .
docker run -p 8001:8001 --env-file .env ai-crawler
```

#### 🔐 환경변수 상세 설정
```bash
# .env 파일의 선택적 설정들
MAX_CONCURRENT_CRAWLS=5      # 동시 크롤링 수 제한
DEFAULT_TIMEOUT=30           # 기본 타임아웃 (초)
RESULTS_DIR=./results        # 결과 저장 디렉토리
CACHE_DIR=./cache           # 캐시 디렉토리
DEBUG=true                  # 디버그 모드
```

### 접근 URL
- **백엔드 API**: `http://localhost:8001`
- **API 문서**: `http://localhost:8001/docs`
- **프론트엔드 UI**: `http://localhost:3000`
- **WebSocket**: `ws://localhost:8001/ws/{connection_id}`
- **헬스체크**: `http://localhost:8001/health`

## 🎯 사용 방법

### 📖 API 문서
서버 실행 후 자동 생성된 API 문서를 확인하세요:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### 1. 통합 크롤링 API (권장)

```bash
# 자연어 입력으로 모든 형태 처리
curl -X POST "http://localhost:8001/api/v1/crawl/unified" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "https://help.kt.com 에서 제목만 추출해줘",
    "timeout": 30,
    "clean_text": true,
    "engine": "crawl4ai"
  }'
```

### 2. 단일 URL 크롤링

```bash
curl -X POST "http://localhost:8001/api/v1/crawl/single" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://help.kt.com/main.jsp",
    "timeout": 30,
    "clean_text": true
  }'
```

### 3. 선택적 콘텐츠 추출

```bash
curl -X POST "http://localhost:8001/api/v1/crawl/smart" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "https://shopping.naver.com 가격 정보만 가져와줘",
    "timeout": 30,
    "clean_text": true
  }'
```

### 4. 특정 엔진 강제 지정

```bash
curl -X POST "http://localhost:8001/api/v1/crawl/single" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "engine": "firecrawl",
    "timeout": 45,
    "anti_bot_mode": true
  }'
```

### 5. 대량 URL 크롤링 (백그라운드)

```bash
curl -X POST "http://localhost:8001/api/v1/crawl/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com",
      "https://httpbin.org/html", 
      "https://jsonplaceholder.typicode.com"
    ],
    "max_concurrent": 5,
    "clean_text": true
  }'
```

### 6. 작업 상태 및 결과 확인

```bash
# 활성 작업 목록
curl "http://localhost:8001/api/v1/jobs/active"

# 작업 상태 확인
curl "http://localhost:8001/api/v1/jobs/{job_id}/status"

# 결과 다운로드
curl "http://localhost:8001/api/v1/jobs/{job_id}/download" -o results.json

# 결과 미리보기
curl "http://localhost:8001/api/v1/jobs/{job_id}/results"

# 엔진 상태 확인
curl "http://localhost:8001/api/v1/engines/status"
```

## 📊 크롤링 결과 형식 (RAG 최적화)

```json
{
  "url": "https://help.kt.com/main.jsp",
  "title": "고객지원",
  "text": "## 가장 궁금해 하시는 메뉴를 모았어요.\n- 가까운 대리점 찾기\n- 인터넷 속도측정\n- 고객센터안내\n...",
  "hierarchy": {
    "depth1": "고객지원",
    "depth2": {
      "요금서비스": ["요금명세서 확인", "요금 즉시납부", "납부확인서 출력"],
      "조회서비스": ["가입정보 인쇄/발송", "통화내역 조회", "명의변경"],
      "신청서비스": ["요금제 변경", "휴대폰 분실신청", "휴대폰 일시정지"]
    },
    "depth3": {
      "고객센터": ["모바일 문의", "인터넷/TV/전화 문의", "Shop 고객센터"]
    }
  },
  "metadata": {
    "crawler_used": "firecrawl",
    "processing_time": "3.2s",
    "quality_score": 87.5,
    "extraction_confidence": 0.95,
    "content_quality": "high",
    "strategy_used": "complex_spa",
    "text_reduction_ratio": 0.75,
    "intent_confidence": 0.9,
    "mcp_analysis_used": true
  },
  "status": "complete",
  "timestamp": "2024-01-01T12:00:00Z",
  "error": null
}
```

## 🔧 크롤링 엔진별 특성

### 1. **Firecrawl Engine** 🔥
- **장점**: 프리미엄 품질, 안티봇 우회, JavaScript 렌더링
- **최적**: SPA, 복잡한 사이트, 무료 스크롤
- **제한**: API 요금제 필요
- **설정**: 마크다운/HTML 추출, 스크린샷 옵션

### 2. **Crawl4AI Engine** 🧠  
- **장점**: AI 기반 추출, LLM 전략, 의미적 분류
- **최적**: 구조화된 데이터 추출, 쇼핑몰, 뉴스
- **특징**: OpenAI/Anthropic LLM 활용
- **설정**: 추출 전략, 청킹 전략, CSS 셀렉터

### 3. **Playwright Engine** 🎭
- **장점**: 실제 브라우저, 정밀 제어, 강력한 우회
- **최적**: 로그인 필요, 복잡한 동적 사이트
- **기능**: 스크린샷, 무한스크롤, 사용자 인터랙션
- **설정**: 뷰포트, 헤더, 대기 조건

### 4. **Requests Engine** ⚡
- **장점**: 빠른 속도, 가벼움, 높은 처리량
- **최적**: 정적 HTML, API 엔드포인트
- **특징**: HTTP 직접 요청, 최소 오버헤드
- **설정**: 헤더, 타임아웃, 재시도 로직

## 🧹 고급 텍스트 후처리

### 정제 기능
- **JavaScript 링크 제거**: `[텍스트](javascript:...)` → `텍스트`
- **UI 요소 제거**: 아이콘, 버튼, 바로가기, 새창열림 등
- **마크다운 정리**: 중복 헤더, 불필요한 구분선 정리
- **공백 최적화**: 연속 공백/개행을 적절히 정리
- **문장 구조 개선**: 의미없는 단독 문자, 짧은 리스트 제거

### 품질 점수 계산
```python
quality_score = (
    length_ratio * 0.4 +        # 내용 보존도
    markdown_reduction * 0.3 +   # 마크다운 정리도
    ui_reduction * 0.3          # UI 요소 제거도
)
```

## 🔄 WebSocket 실시간 추적

### 지원하는 이벤트
- **진행률 업데이트**: 크롤링 단계별 실시간 진행률
- **크롤링 완료**: 성공/실패 상태 및 결과 데이터
- **에러 알림**: 실시간 오류 정보 및 해결 방안
- **벌크 진행률**: 다중 URL 처리 시 개별 URL별 상태

### 연결 방법
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/your-job-id');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress, '%');
};
```

## 📈 성능 최적화

### 병렬 처리
- **최대 동시 크롤링**: 5개 URL
- **지수 백오프**: 실패 시 재시도 간격 자동 조절
- **영구 에러 감지**: 404, DNS 오류 등 재시도 불가 에러 식별

### 메모리 관리
- **스트리밍 결과**: 대용량 데이터 점진적 전송
- **캐시 활용**: 중복 요청 방지
- **리소스 정리**: 브라우저, 연결 자동 해제

## 🚨 에러 처리 및 복구

### 자동 복구 시스템
```python
# 재시도하지 않을 영구적 에러들
permanent_errors = [
    "404", "not found",           # HTTP 404
    "403", "forbidden",           # 접근 금지
    "dns", "name resolution",     # DNS 오류
    "connection refused",         # 연결 거부
    "invalid url",               # 잘못된 URL
    "ssl certificate"            # SSL 인증서 오류
]
```

### 품질 보장 시스템
- **MCP 품질 검증**: 실시간 결과 검증 및 재시도 판단
- **다층 품질 체크**: 콘텐츠 밀도, 구조적 완성도, 정제 효과
- **자동 폴백**: 품질 기준 미달 시 다른 엔진으로 자동 전환

## 🔒 보안 및 제한사항

### 보안 기능
- **User-Agent 로테이션**: 다양한 브라우저 에이전트 사용
- **요청 속도 제한**: 서버 부하 방지
- **SSL 검증**: 보안 연결 강제
- **입력 검증**: 악성 URL 및 입력 필터링

### 사용 제한
- **동시 연결**: WebSocket 연결 수 제한
- **파일 크기**: 결과 파일 크기 제한
- **API 요율**: 엔진별 API 호출 한도 관리

## 📁 프로젝트 구조

```
ai-crawler/
├── backend/                    # FastAPI 백엔드 서버
│   ├── app/
│   │   ├── api/               # REST API 라우터
│   │   │   ├── routes.py      # 메인 API 엔드포인트 (1140 라인)
│   │   │   └── websocket.py   # WebSocket 핸들러
│   │   ├── crawlers/          # 크롤링 엔진들
│   │   │   ├── multi_engine.py    # 멀티 엔진 관리자 (470 라인)
│   │   │   ├── firecrawl_engine.py    # Firecrawl 엔진
│   │   │   ├── crawl4ai_engine.py     # Crawl4AI 엔진
│   │   │   ├── playwright_engine.py   # Playwright 엔진
│   │   │   ├── requests_engine.py     # Requests 엔진
│   │   │   └── base.py            # 베이스 크롤러 클래스
│   │   ├── mcp/               # MCP 클라이언트
│   │   │   ├── client.py      # MCP 통신 클라이언트
│   │   │   ├── tools.py       # 도구 관리자
│   │   │   └── strategies.py  # 전략 관리자
│   │   └── utils/             # 유틸리티
│   │       ├── natural_language_parser.py  # 자연어 파싱 (327 라인)
│   │       └── text_processor.py          # 텍스트 후처리 (259 라인)
│   └── main.py                # FastAPI 앱 진입점
├── frontend/                   # Next.js 15 + React 19 프론트엔드
│   └── src/
│       ├── app/
│       │   ├── page.tsx       # 메인 페이지 (444 라인)
│       │   └── layout.tsx     # 레이아웃
│       ├── components/        # 리액트 컴포넌트들
│       │   ├── chat/          # 채팅 UI 컴포넌트
│       │   ├── results/       # 결과 표시 컴포넌트
│       │   └── download/      # 다운로드 컴포넌트
│       ├── hooks/             # 리액트 훅들 (WebSocket 등)
│       ├── types/             # TypeScript 타입 정의
│       └── utils/             # 프론트엔드 유틸리티
├── mcp-server/                 # MCP 표준 서버
│   ├── server.py              # MCP 서버 메인 파일 (212 라인)
│   └── tools/                 # MCP 도구들
│       ├── site_analyzer.py       # 사이트 분석 (314 라인)
│       ├── crawler_selector.py    # 크롤러 선택 (407 라인)
│       ├── structure_detector.py  # 구조 감지 (417 라인)
│       ├── quality_validator.py   # 품질 검증 (535 라인)
│       └── content_extractor.py   # 콘텐츠 추출 (616 라인)
├── requirements.txt            # Python 의존성 (52개 패키지)
├── env.example                # 환경변수 예시
└── README.md                  # 프로젝트 문서
```

## 🔍 개발자 정보

### 코드 통계
- **총 Python 코드**: ~7,000+ 라인
- **총 TypeScript/React 코드**: ~1,500+ 라인
- **주요 의존성**: FastAPI, Next.js, MCP, OpenAI, Anthropic
- **지원 포맷**: JSON, Markdown, HTML, Plain Text

### 확장성
- **모듈화 설계**: 플러그인 방식으로 새로운 엔진 추가 가능
- **MCP 표준**: 다른 AI 도구들과 호환
- **비동기 처리**: 고성능 동시 처리 지원
- **타입 안전성**: TypeScript 기반 타입 안전성

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 💡 향후 계획

- [ ] **추가 엔진 지원**: Selenium, Scraping Bee 등
- [ ] **AI 모델 업그레이드**: GPT-4, Claude-3 통합
- [ ] **성능 모니터링**: 메트릭 수집 및 대시보드
- [ ] **분산 처리**: Redis 기반 작업 큐
- [ ] **커스텀 추출기**: 사용자 정의 추출 규칙
- [ ] **API 버전 관리**: v2 API 준비

---
**AI-Powered Smart Web Crawler** - MCP 표준 기반 차세대 지능형 크롤링 시스템 