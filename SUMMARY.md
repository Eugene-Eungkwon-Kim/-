# AVM Agent 프로젝트 아키텍처 요약

**프로젝트명**: rtech 기반 자동감정평가 Agent 시스템 개발  
**기간**: 2026-06-09 ~ 2026-09-09 (13주)  
**목표**: 25M+ 거래 DB + LLM 기반 자동 감정평가 시스템 완성

---

## 🎯 핵심 목표

### 데이터 규모
- **아파트**: 24,197개 단지, 10,262,142호
- **다세대/연립/오피스텔**: 전국 데이터
- **실거래가**: 25M+ 건 (공공API)
- **기존 NPL**: 2,645개 물건 (7개 금융기관)

### 시스템 기능
1. **감정평가 엔진** — 비교법 + 시점수정 기반 AVM
2. **데이터 통합** — NPL 물건 ↔ rtech 단지 자동 매핑
3. **LLM Agent** — Claude API 기반 자연어 감정평가
4. **REST API** — FastAPI 기반 마이크로서비스

---

## 🏗️ 시스템 아키텍처

### 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent (Claude API)                   │
│      자연어 해석 → Tool Use → DB 쿼리 → 감정가 설명         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   REST API Layer (FastAPI)                   │
│  /api/v2/avm/estimate  /api/v2/agent/query  /api/v2/...    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              AVM Engine (Python Business Logic)              │
│  • 비교사례 추출     • 유사도 계산     • 시점수정             │
│  • 가중평균 산출     • 신뢰도 범위     • 헤도닉 모델          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│            Unified Database Layer (PostgreSQL)               │
│  ┌──────────────┬──────────────┬──────────────┐              │
│  │ NPL 물건     │ rtech 공동주택 │ 거래 이력      │            │
│  │ 2,645개      │ 10M+ 호       │ 25M+ 건       │            │
│  └──────────────┴──────────────┴──────────────┘              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Data Ingestion Pipelines                        │
│  rtech 크롤러  │  공공API (국토부)  │  NPL 파서 (7종)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 데이터 흐름

### Phase 1 ~ 6 진행 과정

```
주차별 진행
─────────────────────────────────────────────────────────────

Week 1-2   [Phase 1] 아키텍처 설계 ✓ (완료)
           ├─ ARCHITECTURE.md 작성
           ├─ ROADMAP.md 작성
           ├─ TECHNICAL_SPEC.md 작성
           └─ 스키마 설계 완료

Week 3-5   [Phase 2] 데이터 수집
           ├─ rtech 크롤러 개발 (24,197개 단지)
           ├─ 공공API 연동 (월 25M 거래)
           ├─ 데이터 검증 및 정제
           └─ DB 적재 (SQLite → PostgreSQL 준비)

Week 6-7   [Phase 3] 데이터 통합
           ├─ 주소 정규화 및 단지 매핑
           ├─ NPL 2,645개 ↔ rtech 연결
           ├─ 비교사례 자동 추출
           └─ comparable_sales 테이블 구축

Week 8-9   [Phase 4] AVM 엔진 v2
           ├─ 비교법 고도화
           ├─ 시점수정계수 적용 (KB시세 + 지가변동)
           ├─ 신뢰도 범위 추정 (상한/점추정/하한)
           └─ API 통합

Week 10    [Phase 5] 헤도닉 회귀모델
           ├─ 특성가격모형 (Hedonic) 구현
           ├─ GBM 기반 예측
           ├─ 10만 건 이상 학습
           └─ Feature importance 분석

Week 11-13 [Phase 6] LLM Agent + 프로덕션
           ├─ Claude API 통합
           ├─ Tool Use 기반 자동화
           ├─ 자연어 쿼리 처리
           ├─ Docker 배포 준비
           └─ PostgreSQL 마이그레이션 완료
```

---

## 💾 데이터베이스 스키마 (확장)

### 신규 테이블 (rtech 통합)

```
─── 단지 정보 ─────────────────────────────────────
complexes (24,197개)
  ├─ complex_code: 단지코드 (rtech)
  ├─ complex_name: 단지명
  ├─ address: 주소 (시도/시군구/동)
  ├─ build_year: 건축년도
  ├─ total_units: 총 호수
  └─ created_at

─── 호실 정보 ─────────────────────────────────────
units (10,262,142개)
  ├─ complex_id: 단지 (FK)
  ├─ exclusive_area: 전용면적
  ├─ floor: 층수
  ├─ official_price_latest: 공시가격 (최신)
  ├─ kb_price_latest: KB시세 (최신)
  └─ parking_cnt: 주차 대수

─── 실거래 정보 ─────────────────────────────────
transactions (25M+ 건)
  ├─ complex_id: 단지
  ├─ unit_id: 호실
  ├─ contract_date: 계약일
  ├─ report_date: 신고일
  ├─ price: 거래가격
  ├─ verified: 검증 여부
  └─ is_abnormal: 이상거래 플래그

─── 공시가격 이력 ──────────────────────────────
price_history
  ├─ unit_id: 호실
  ├─ price_date: 공시 기준일 (매반기)
  ├─ official_price: 공시가격
  └─ price_per_area: 평방미터당

─── 비교사례 ──────────────────────────────────
comparable_sales
  ├─ npl_property_id: NPL 물건
  ├─ transaction_id: 비교사례 (rtech 거래)
  ├─ similarity_score: 유사도 (0~1)
  ├─ weight: 가중치
  └─ created_at
```

### 기존 테이블 (NPL) 확장

```
properties (2,645개 물건)
  └─ complex_id 추가 (FK → complexes)  [NEW]
     ↓
     comparable_sales로 비교사례 자동 연결
```

---

## 🔧 API 엔드포인트

### v2 (확장된 감정평가 API)

#### 1. AVM 감정가 추정

```http
POST /api/v2/avm/estimate
Content-Type: application/json

Request:  { "property_id": 123 }

Response:
{
  "point_estimate": 3500000,      # 점 추정가
  "lower_bound": 3200000,         # 보수적 (하한)
  "upper_bound": 3800000,         # 낙관적 (상한)
  "confidence_level": 0.85,       # 신뢰도
  "comparable_count": 8,          # 비교사례 수
  "method": "weighted_avg + time_adjustment"
}
```

#### 2. 자연어 Agent 쿼리

```http
POST /api/v2/agent/query
Content-Type: application/json

Request:  { "query": "경기도 화성시 아파트 감정가?" }

Response:
{
  "response": "화성시 봉담읍 아파트의 감정가는 약 3,500만원(상한 3,800만원, 하한 3,200만원)으로 추정됩니다. 최근 8건의 유사 거래를 바탕으로 계산했으며, 신뢰도는 85%입니다.",
  "estimated_price": 3500000,
  "confidence": 0.85
}
```

#### 3. 비교사례 조회

```http
GET /api/v2/comparable-sales?property_id=123&limit=10

Response:
{
  "sales": [
    {
      "address": "경기도 화성시 봉담읍",
      "price": 3450000,
      "date": "2026-05-15",
      "similarity": 0.92
    },
    ...
  ]
}
```

#### 4. 시장 동향 분석

```http
GET /api/v2/market-trends?sido=경기도&months=12

Response:
{
  "sido": "경기도",
  "transaction_count": 125432,
  "avg_price": 3420000,
  "price_trend": "상승 (YoY +5.2%)"
}
```

---

## 🤖 LLM Agent 특징

### Tool Use 기반 자동화

Agent가 사용 가능한 도구:

1. **search_property_by_address** — 주소로 물건 검색
2. **estimate_avm** — 감정평가가 추정
3. **find_comparable_sales** — 비교사례 조회
4. **analyze_market_trends** — 시장 동향 분석

### 예시 대화

```
사용자: "경기도 화성시 아파트 감정가 알려줄래?"

Agent 처리:
  1. Tool: search_property_by_address(address="경기도 화성시")
     ↓ 결과: 화성시 내 물건 5개 검색
  
  2. Tool: estimate_avm(property_id=123)
     ↓ 결과: 감정가 3,500만원 (범위 3,200~3,800)
  
  3. Tool: find_comparable_sales(property_id=123)
     ↓ 결과: 비교사례 8건 조회
  
  4. 최종 답변 생성 (자연어)

응답: "화성시 봉담읍의 아파트는 약 3,500만원으로 추정됩니다. 
      최근 8건의 인접 거래를 바탕으로 계산했으며, 
      상한은 3,800만원, 하한은 3,200만원입니다."
```

---

## 📈 AVM 감정평가 로직

### 단계별 처리

```
[1] 비교사례 추출
    ├─ 같은 단지 거래 (weight=0.95)
    ├─ 근처 단지 거래 (거리<2km, weight=0.70)
    ├─ 면적 유사도 필터링 (>70%)
    └─ 이상거래 제거 (IQR 방법)

[2] 시점수정계수 계산
    └─ adjustment = 0.8 × KB시세변화 + 0.2 × 지가변동
       예: 2026-01 거래 → 2026-06 현재: +2.2% 보정

[3] 거래가 조정
    └─ adjusted_price = comparable_price × (1 + adjustment)

[4] 가중평균
    ├─ weight_i = similarity_i / sum(similarities)
    └─ point_estimate = Σ(price_i × weight_i)

[5] 신뢰도 범위 (95% 신뢰도)
    ├─ std_dev = 표준편차
    ├─ margin_of_error = 1.96 × std_dev / √n
    ├─ lower_bound = point_estimate - margin
    └─ upper_bound = point_estimate + margin
```

### 정확도 목표

| 지표 | 목표 | 검증 방법 |
|------|------|---------|
| **MAPE** | < 10% | 실제 낙찰가와 비교 |
| **적중률** | 예정 범위 내: > 85% | 신뢰도 범위 검증 |
| **비교사례** | 물건당 최소 5개 | 추출 로직 테스트 |

---

## 🚀 기술 스택

### 현재
```
Python 3.12
FastAPI 0.100+
SQLAlchemy 2.0
SQLite (개발)
```

### 추가 (Phase 2~6)
```
# 데이터 수집
aiohttp, beautifulsoup4, selenium

# 공공API
requests, pandas

# 지리 정보
geopy, shapely

# ML
scikit-learn, numpy

# LLM
anthropic (Claude API)

# DB
PostgreSQL, psycopg2, alembic

# 모니터링
prometheus-client
```

---

## 📋 체크리스트

### 즉시 시작 항목
- [ ] 아키텍처 리뷰 회의 (이해관계자 검토)
- [ ] API 키 신청 시작
  - [ ] data.go.kr (국토부 실거래API)
  - [ ] Kakao Map API
  - [ ] Anthropic API Key 확인
- [ ] 개발 환경 구성
  - [ ] PostgreSQL 설치
  - [ ] 비용 예상 계산 (Claude API)

### Phase 2 준비 항목
- [ ] rtech 크롤러 프로토타입 개발
- [ ] DB 스키마 마이그레이션 스크립트
- [ ] 데이터 검증 규칙 정의

### 위험 요소
| 위험 | 대응 |
|------|------|
| rtech 크롤링 차단 | 공공API 우선 추진 |
| API 데이터 품질 | 수동 검증 + 이상치 제거 |
| 주소 매핑 실패 | 지오코딩 + 지오해싱 병행 |
| Claude API 비용 | Rate limiting + 캐싱 |

---

## 📚 핵심 문서

| 문서 | 목적 | 분량 |
|------|------|------|
| **ARCHITECTURE.md** | 전체 시스템 설계 | 14개 섹션 |
| **ROADMAP.md** | 주차별 상세 계획 | 13주 × 일일 태스크 |
| **TECHNICAL_SPEC.md** | 기술 명세 (스키마, API, 알고리즘) | API, DB, 보안 |
| **SUMMARY.md** (본 문서) | 아키텍처 개요 | 1장 (인쇄용) |

---

## 💡 성공 지표

### 데이터 적재
- ✓ rtech 단지 마스터: 24,197개
- ✓ 호실 정보: 10M+ 개
- ✓ 실거래 거래: 25M+ 건
- ✓ NPL 물건 매핑: 2,100개 (80%)

### 시스템 성능
- API 응답: < 100ms
- Agent 응답: < 3초
- 가용성: 99.0%
- 동시 사용자: 100명

### AVM 정확도
- MAPE: < 10%
- 범위 적중률: > 85%
- 비교사례: 물건당 평균 5개 이상

### Agent 품질
- 자연어 해석율: > 95%
- 오류 응답: < 2%
- 사용자 만족도: 4/5 이상

---

## 🔗 참고 자료

### 외부 API 문서
- [data.go.kr — 국토부 실거래가](https://www.data.go.kr/)
- [Kakao Map API](https://apis.map.kakao.com/)
- [Anthropic API — Claude](https://docs.anthropic.com/)

### 관련 논문/자료
- Rosen, S. (1974). "Hedonic Prices and Implicit Markets"
- 한국부동산원 — 주택시장 지표
- KB국민은행 — 부동산 시세 정보

---

## 👥 연락 및 질문

**프로젝트 리더**: [이름]  
**기술 담당**: [담당자]  
**일정 문의**: 주간 회의 (목요일 10:00)

**질문 또는 피드백**: 
1. GitHub Issues (기술)
2. 주간 회의 (일정/방향)
3. Email (긴급)

---

## 📅 마일스톤

| 마일스톤 | 목표 | 예상 일자 |
|---------|------|---------|
| **M1** | Phase 2 완료 (25M 거래 적재) | 2026-07-05 |
| **M2** | Phase 3 완료 (NPL-rtech 매핑) | 2026-07-20 |
| **M3** | Phase 4 완료 (AVM v2 API) | 2026-08-03 |
| **M4** | Phase 5 완료 (헤도닉 모델) | 2026-08-17 |
| **M5** | Phase 6 완료 (LLM Agent 배포) | 2026-09-07 |

---

**문서 작성**: 2026-06-09  
**최종 수정**: -  
**상태**: ✓ Complete (검토 대기)

---

## 부록: 빠른 시작 가이드

### 1단계: 개발 환경 설정
```bash
# 저장소 클론
cd D:\NPL전례\avm_project

# 의존성 설치
pip install -r requirements.txt

# PostgreSQL 준비
# (Docker 사용 권장)
docker-compose up -d db

# 환경변수 설정
cp .env.example .env
# .env 파일에서 API 키 입력
```

### 2단계: DB 마이그레이션 (Phase 2 시작 시)
```bash
# 신 스키마 생성
alembic upgrade head

# 기존 NPL 데이터 검증
python scripts/validate_npl_data.py
```

### 3단계: 첫 API 테스트 (Phase 4 이후)
```bash
# 서버 실행
uvicorn app.main:app --reload --port 8000

# Swagger 문서
http://localhost:8000/docs

# 샘플 요청
curl -X POST http://localhost:8000/api/v2/avm/estimate \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1}'
```

### 4단계: Agent 테스트 (Phase 6)
```bash
# Agent API 테스트
curl -X POST http://localhost:8000/api/v2/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "경기도 화성시 아파트 감정가?"}'
```

---

**더 자세한 내용은 ARCHITECTURE.md, ROADMAP.md, TECHNICAL_SPEC.md를 참고하세요.**
