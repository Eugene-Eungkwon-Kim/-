# AVM Agent 시스템 기술 명세서

**프로젝트**: rtech 기반 자동감정평가 Agent  
**버전**: 1.0  
**작성일**: 2026-06-09  
**상태**: Draft

---

## 1. 시스템 요구사항

### 1.1 기능 요구사항 (FR)

#### FR1: 데이터 수집 및 관리
- [ ] rtech 24,197개 단지 마스터 수집
- [ ] 아파트/다세대/연립/오피스텔 실거래가 수집 (25M+ 건)
- [ ] 월별 자동 갱신 파이프라인
- [ ] 데이터 검증 및 정제

#### FR2: NPL-rtech 데이터 통합
- [ ] 기존 NPL 2,645개 물건 ↔ rtech 단지 매핑
- [ ] 비교사례 자동 추출 (물건당 5개 이상)
- [ ] 유사도 점수 계산

#### FR3: AVM 감정평가
- [ ] 비교법 기반 감정가 추정
- [ ] 신뢰도 범위 제시 (상한/점추정/하한)
- [ ] 시점수정계수 적용
- [ ] 근거 설명 (사용된 비교사례)

#### FR4: LLM Agent
- [ ] 자연어 질의 해석
- [ ] DB 검색 자동화
- [ ] AVM 추정 자동화
- [ ] 친화적 답변 생성

#### FR5: API 서비스
- [ ] REST API (v1 + v2)
- [ ] Swagger 문서화
- [ ] 응답 시간 < 100ms

### 1.2 비기능 요구사항 (NFR)

#### NFR1: 성능
- 데이터베이스 조회: < 50ms (인덱스 기반)
- AVM 추정: < 100ms
- Agent 응답: < 3초 (API 호출 포함)
- 동시 사용자: 100명 (초기)

#### NFR2: 가용성
- 시스템 가용성: 99.0% (한 달 기준)
- 데이터 신선도: 일 1회 갱신
- 재해복구: 6시간 내 복구

#### NFR3: 보안
- API 인증: API Key 기반
- 데이터 암호화: 전송 중(HTTPS), 저장(TBD)
- 개인정보 마스킹: 매도/매수인 식별 제거
- 감사 로그: 모든 API 호출 기록

#### NFR4: 확장성
- DB: SQLite → PostgreSQL 이관
- 아키텍처: 수평 확장 가능 구조
- 캐싱: Redis (선택사항)

---

## 2. 데이터 모델

### 2.1 Core Schema (ERD)

```
┌─────────────────────┐
│   complexes         │
├─────────────────────┤
│ id (PK)             │
│ complex_code (UK)   │
│ complex_name        │
│ address_sido        │
│ address_sigungu     │
│ build_year          │
│ total_units         │
│ source              │
│ created_at          │
│ updated_at          │
└──────┬──────────────┘
       │ 1:N
       ├─────────────────────────┐
       │                         │
       ↓                         ↓
  ┌──────────┐         ┌──────────────────┐
  │  units   │         │  transactions    │
  ├──────────┤         ├──────────────────┤
  │ id (PK)  │         │ id (PK)          │
  │ complex_ │         │ complex_id (FK)  │
  │ id (FK)  │         │ unit_id (FK)     │
  │ unit_    │         │ transaction_id   │
  │ code     │         │ contract_date    │
  │ dong     │         │ report_date      │
  │ floor    │         │ price            │
  │ exclusive│         │ verified         │
  │ _area    │         │ is_abnormal      │
  │ parking_ │         │ created_at       │
  │ cnt      │         └──────────────────┘
  └──────────┘
       │
       │ 1:N
       ↓
  ┌──────────────┐
  │ price_       │
  │ history      │
  ├──────────────┤
  │ id (PK)      │
  │ unit_id (FK) │
  │ price_date   │
  │ official_    │
  │ price        │
  └──────────────┘


┌─────────────────────────┐
│  properties (NPL)       │
├─────────────────────────┤
│ id (PK)                 │
│ deal_id (FK)            │
│ property_serial         │
│ address_sido            │
│ property_type           │
│ land_area               │
│ building_area           │
│ complex_id (FK) ←────┐  │  ← 신규 (rtech 단지 링크)
│ created_at              │
└─────────────────────────┘
       │
       │ 1:N
       ├───────────────────┐
       │                   │
       ↓                   ↓
  ┌──────────┐      ┌──────────────┐
  │appraisals│      │ auctions     │
  └──────────┘      └──────────────┘
       │
       │ 1:N
       ↓
  ┌──────────────────────┐
  │comparable_sales      │
  ├──────────────────────┤
  │ id (PK)              │
  │ npl_property_id (FK) │
  │ transaction_id (FK)  │
  │ similarity_score     │
  │ weight               │
  └──────────────────────┘
```

### 2.2 테이블 명세

#### complexes (단지 마스터)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INTEGER | PK | 단지 ID |
| complex_code | VARCHAR(20) | UK, NN | rtech 단지코드 |
| complex_name | VARCHAR(200) | NN | 단지명 |
| address_sido | VARCHAR(30) | INDEX | 시도 |
| address_sigungu | VARCHAR(50) | INDEX | 시군구 |
| address_dong | VARCHAR(50) | | 동 |
| address_jibun | VARCHAR(100) | | 지번 |
| address_roadname | VARCHAR(100) | INDEX | 도로명 |
| build_year | INTEGER | | 건축년도 |
| total_units | INTEGER | | 총 호수 |
| total_area | FLOAT | | 단지 총 면적 |
| source | VARCHAR(20) | | 데이터 출처 (rtech, api) |
| last_updated | DATETIME | | 마지막 갱신 시각 |
| created_at | DATETIME | | 생성 시각 |

**인덱스**:
```sql
CREATE INDEX idx_complex_code ON complexes(complex_code);
CREATE INDEX idx_complex_address ON complexes(address_sido, address_sigungu);
CREATE INDEX idx_complex_roadname ON complexes(address_roadname);
```

#### units (호실)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INTEGER | PK | 호실 ID |
| complex_id | INTEGER | FK, NN | 단지 ID |
| unit_code | VARCHAR(50) | UK | 호실 고유코드 (단지코드-동-호) |
| dong | VARCHAR(20) | | 동 |
| floor | INTEGER | | 층 |
| unit_num | VARCHAR(20) | | 호수 |
| exclusive_area | FLOAT | NN | 전용면적 (㎡) |
| supply_area | FLOAT | | 공급면적 (㎡) |
| parking_cnt | INTEGER | | 주차 대수 |
| official_price_latest | NUMERIC(20,0) | | 최신 공시가격 |
| kb_price_latest | NUMERIC(20,0) | | 최신 KB 시세 |
| created_at | DATETIME | | 생성 시각 |
| updated_at | DATETIME | | 갱신 시각 |

**인덱스**:
```sql
CREATE INDEX idx_unit_complex ON units(complex_id);
CREATE INDEX idx_unit_code ON units(unit_code);
CREATE INDEX idx_unit_area ON units(exclusive_area);
```

#### transactions (실거래)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INTEGER | PK | 거래 ID |
| complex_id | INTEGER | FK, NN | 단지 ID |
| unit_id | INTEGER | FK | 호실 ID |
| transaction_id | VARCHAR(50) | UK | API 거래ID |
| contract_date | DATE | | 계약일 |
| report_date | DATE | NN, INDEX | 신고일 |
| price | NUMERIC(20,0) | NN | 거래가격 (원) |
| price_per_area | NUMERIC(15,2) | | 평방미터당 가격 |
| seller | VARCHAR(100) | | 매도인 (마스킹됨) |
| buyer | VARCHAR(100) | | 매수인 (마스킹됨) |
| verified | BOOLEAN | DEFAULT FALSE | 검증 완료 여부 |
| is_abnormal | BOOLEAN | DEFAULT FALSE | 이상거래 플래그 |
| created_at | DATETIME | | 생성 시각 |

**인덱스**:
```sql
CREATE INDEX idx_transaction_complex ON transactions(complex_id);
CREATE INDEX idx_transaction_date ON transactions(report_date);
CREATE INDEX idx_transaction_price ON transactions(price);
```

#### price_history (공시가격 이력)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INTEGER | PK | 이력 ID |
| unit_id | INTEGER | FK, NN | 호실 ID |
| price_date | DATE | NN | 공시 기준일 |
| official_price | NUMERIC(20,0) | NN | 공시가격 |
| price_per_area | NUMERIC(15,2) | | 평방미터당 |

**Unique**: (unit_id, price_date)

#### comparable_sales (비교사례)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INTEGER | PK | 비교사례 ID |
| npl_property_id | INTEGER | FK, NN | NPL 물건 ID |
| transaction_id | INTEGER | FK, NN | 거래 ID |
| similarity_score | FLOAT | | 종합 유사도 (0~1) |
| area_similarity | FLOAT | | 면적 유사도 |
| location_similarity | FLOAT | | 입지 유사도 |
| vintage_similarity | FLOAT | | 연식 유사도 |
| weight | FLOAT | | 최종 가중치 |
| created_at | DATETIME | | 생성 시각 |

---

## 3. API 명세

### 3.1 REST API Endpoints

#### 3.1.1 감정평가 추정 (AVM)

```http
POST /api/v2/avm/estimate
Content-Type: application/json

{
  "property_id": 123
}

HTTP/1.1 200 OK
Content-Type: application/json

{
  "property_id": 123,
  "point_estimate": 3500000,
  "lower_bound": 3200000,
  "upper_bound": 3800000,
  "confidence_level": 0.85,
  "comparable_count": 8,
  "comparable_details": [
    {
      "transaction_id": 1001,
      "price": 3450000,
      "address": "경기도 화성시 봉담읍",
      "date": "2026-05-15",
      "similarity": 0.92,
      "weight": 0.25
    }
  ],
  "method": "weighted_avg + time_adjustment",
  "estimated_at": "2026-06-09T12:34:56Z"
}
```

**응답 코드**:
- 200: 성공
- 400: 비교사례 부족
- 404: 물건 없음
- 500: 서버 오류

#### 3.1.2 자연어 Agent 쿼리

```http
POST /api/v2/agent/query
Content-Type: application/json

{
  "query": "경기도 화성시 아파트 감정가 추정해줄래?"
}

HTTP/1.1 200 OK
Content-Type: application/json

{
  "response": "화성시 봉담읍 아파트의 감정가는 약 3,500만원(상한 3,800만원, 하한 3,200만원) 정도로 추정됩니다. 이는 최근 8건의 주변 거래사례를 바탕으로 계산한 결과입니다.",
  "timestamp": "2026-06-09T12:34:56Z"
}
```

#### 3.1.3 비교사례 조회

```http
GET /api/v2/comparable-sales?property_id=123&limit=10

HTTP/1.1 200 OK

{
  "property_id": 123,
  "comparable_count": 8,
  "sales": [
    {
      "transaction_id": 1001,
      "complex_name": "봉담 아파트",
      "address": "경기도 화성시 봉담읍",
      "price": 3450000,
      "area": 84.92,
      "price_per_area": 40621,
      "report_date": "2026-05-15",
      "similarity": 0.92
    }
  ]
}
```

#### 3.1.4 시장 동향 분석

```http
GET /api/v2/market-trends?sido=경기도&months=12

HTTP/1.1 200 OK

{
  "sido": "경기도",
  "period_months": 12,
  "transaction_count": 125432,
  "avg_price": 3420000,
  "price_trend": "상승",
  "yoy_change_percent": 5.2,
  "top_districts": [
    {
      "sigungu": "화성시",
      "transaction_count": 12543,
      "avg_price": 3500000
    }
  ]
}
```

### 3.2 인증 (API Key)

모든 API 엔드포인트는 API Key 필요:

```http
GET /api/v2/avm/estimate?property_id=123
Authorization: Bearer YOUR_API_KEY

또는

GET /api/v2/avm/estimate?property_id=123&api_key=YOUR_API_KEY
```

---

## 4. 구현 세부사항

### 4.1 Dataclass 정의

```python
# app/schemas/

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

@dataclass
class ComplexMeta:
    """단지 메타정보"""
    complex_code: str
    complex_name: str
    address_sido: str
    address_sigungu: str
    address_dong: Optional[str]
    build_year: Optional[int]
    total_units: Optional[int]
    source: str = "rtech"

@dataclass
class UnitInfo:
    """호실 정보"""
    complex_id: int
    unit_code: str
    dong: str
    floor: int
    exclusive_area: float
    parking_cnt: int = 1

@dataclass
class TransactionRecord:
    """거래 기록"""
    complex_id: int
    unit_id: Optional[int]
    contract_date: date
    report_date: date
    price: int
    verified: bool = False

@dataclass
class AVMEstimate:
    """감정가 추정 결과"""
    property_id: int
    point_estimate: int
    lower_bound: int
    upper_bound: int
    confidence_level: float
    comparable_count: int
    method: str
    estimated_at: datetime
```

### 4.2 AVM 엔진 알고리즘

#### 4.2.1 비교사례 선정

```python
# Pseudocode

function select_comparables(target_property):
    comparables = []
    
    # 1. 같은 단지 거래 (최근 12개월)
    same_complex = query_transactions(
        complex_id = target_property.complex_id,
        report_date >= TODAY - 365days
    )
    comparables.extend(same_complex, weight=0.95)
    
    # 2. 근처 단지 거래 (거리 < 2km)
    nearby_units = query_units(
        distance < 2km,
        area_similarity > 0.7
    )
    nearby_trans = query_transactions(
        unit_id in nearby_units,
        report_date >= TODAY - 365days
    )
    comparables.extend(nearby_trans, weight=0.7)
    
    # 3. 이상거래 제거
    comparables = remove_outliers(comparables, iqr_multiplier=1.5)
    
    return comparables
```

#### 4.2.2 시점수정계수

```python
# 계산 식

time_adjustment = 0.8 * kb_rate + 0.2 * land_rate

where:
  kb_rate = (KB_current - KB_transaction_date) / KB_transaction_date
  land_rate = (Land_current - Land_transaction_date) / Land_transaction_date
  
# 예시
transaction_date = 2026-01-15
current_date = 2026-06-09
kb_rate = 0.025  # 2.5% 상승
land_rate = 0.010  # 1.0% 상승
time_adjustment = 0.8 * 0.025 + 0.2 * 0.010 = 0.022 (2.2%)

adjusted_price = 3400000 * (1 + 0.022) = 3474800
```

#### 4.2.3 가중평균 계산

```python
# 가중치 결정

weight_i = similarity_score_i / sum(similarity_scores)

# 예시 (3개 비교사례)
similarity = [0.92, 0.85, 0.78]
sum = 2.55
weights = [0.92/2.55, 0.85/2.55, 0.78/2.55]
        = [0.361, 0.333, 0.306]

adjusted_prices = [3450000, 3400000, 3350000]
point_estimate = 3450000*0.361 + 3400000*0.333 + 3350000*0.306
               = 1245450 + 1132200 + 1025100
               = 3402750
```

#### 4.2.4 신뢰도 범위

```python
# 통계적 신뢰 구간

std_dev = sqrt(sum((price_i - mean)^2) / n)
z_score = 1.96  # 95% 신뢰도

lower_bound = point_estimate - z_score * (std_dev / sqrt(n))
upper_bound = point_estimate + z_score * (std_dev / sqrt(n))

# 예시
point_estimate = 3402750
std_dev = 45000
n = 3
margin_of_error = 1.96 * 45000 / sqrt(3) = 51000

lower_bound = 3402750 - 51000 = 3351750
upper_bound = 3402750 + 51000 = 3453750
```

---

## 5. 성능 최적화

### 5.1 데이터베이스 최적화

**쿼리 최적화**:

```sql
-- 최적화 전 (느림)
SELECT * FROM transactions t
WHERE t.complex_id IN (SELECT id FROM complexes WHERE address_sigungu = '화성시')
  AND t.report_date >= DATE_SUB(NOW(), INTERVAL 365 DAY);

-- 최적화 후 (빠름 - 인덱스 활용)
SELECT t.* FROM transactions t
JOIN complexes c ON t.complex_id = c.id
WHERE c.address_sigungu = '화성시'
  AND t.report_date >= DATE_SUB(NOW(), INTERVAL 365 DAY);

-- 인덱스 활용 확인
EXPLAIN SELECT ...;
```

### 5.2 캐싱 전략

```python
# Redis 캐싱 (선택사항)

from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def get_complex_cached(complex_id: int) -> Complex:
    cache_key = f"complex:{complex_id}"
    
    # 1. Cache hit
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. Cache miss
    complex_obj = db.query(Complex).filter_by(id=complex_id).first()
    
    # 3. Cache set (TTL: 1 hour)
    redis_client.setex(cache_key, 3600, json.dumps(complex_obj))
    
    return complex_obj
```

### 5.3 N+1 쿼리 방지

```python
# 나쁜 예 (N+1 쿼리)
complexes = db.query(Complex).limit(100).all()
for complex in complexes:
    units_count = db.query(Unit).filter_by(complex_id=complex.id).count()  # 100번 쿼리!

# 좋은 예 (1 쿼리)
from sqlalchemy.orm import joinedload
complexes = db.query(Complex).options(
    joinedload(Complex.units)
).limit(100).all()
```

---

## 6. 보안

### 6.1 API 인증

```python
# FastAPI Security

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="Authorization")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key.startswith("Bearer "):
        raise HTTPException(status_code=401)
    
    token = api_key[7:]  # "Bearer " 제거
    
    # DB에서 토큰 검증
    if not is_valid_token(token):
        raise HTTPException(status_code=403)
    
    return token
```

### 6.2 개인정보 마스킹

```python
# 거래 당사자 정보 마스킹

def mask_personal_info(name: str) -> str:
    """
    "홍길동" → "홍○○"
    "ACME Corp" → "ACME C***"
    """
    if len(name) <= 2:
        return "*" * len(name)
    
    if name.endswith("Corp") or name.endswith("Co."):
        # 회사명
        masked = name[:-4] + "****"
    else:
        # 개인명 (처음 글자 + 나머지 마스크)
        masked = name[0] + "○" * (len(name) - 1)
    
    return masked
```

### 6.3 감사 로그

```python
# 모든 API 호출 기록

from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    api_key = Column(String(50))
    endpoint = Column(String(200))
    method = Column(String(10))
    status_code = Column(Integer)
    request_body = Column(Text)
    response_body = Column(Text)
    execution_time_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Middleware 추가
@app.middleware("http")
async def log_api_call(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    execution_time = (time.time() - start_time) * 1000
    
    # Log
    audit_log = AuditLog(
        api_key=request.headers.get("Authorization"),
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        execution_time_ms=int(execution_time)
    )
    db.add(audit_log)
    db.commit()
    
    return response
```

---

## 7. 테스트 계획

### 7.1 단위 테스트 (Unit Tests)

```python
# tests/test_avm_engine.py

import pytest

class TestAVMEngine:
    
    @pytest.fixture
    def engine(self, db_session):
        return AVMEngineV2(db_session)
    
    @pytest.fixture
    def sample_property(self, db_session):
        # Mock property
        return Property(...)
    
    def test_estimate_basic(self, engine, sample_property):
        """기본 추정 테스트"""
        result = engine.estimate(sample_property)
        
        assert result.point_estimate > 0
        assert result.lower_bound < result.point_estimate
        assert result.upper_bound > result.point_estimate
    
    def test_time_adjustment(self, engine):
        """시점수정계수 테스트"""
        adjustment = engine._calc_time_adjustment(
            date(2026, 1, 15),
            "경기도"
        )
        
        assert -0.1 < adjustment < 0.1  # ±10% 범위
    
    def test_outlier_removal(self, engine):
        """이상치 제거 테스트"""
        prices = [3000000, 3500000, 3400000, 100000000]  # 마지막은 이상치
        filtered = engine._remove_outliers(prices)
        
        assert len(filtered) == 3
        assert 100000000 not in filtered
```

### 7.2 통합 테스트 (Integration Tests)

```python
# tests/test_api_integration.py

import pytest
from fastapi.testclient import TestClient

client = TestClient(app)

class TestAPIIntegration:
    
    def test_avm_endpoint(self):
        """AVM API 테스트"""
        response = client.post(
            "/api/v2/avm/estimate",
            json={"property_id": 1},
            headers={"Authorization": "Bearer TEST_TOKEN"}
        )
        
        assert response.status_code == 200
        assert "point_estimate" in response.json()
    
    def test_agent_query(self):
        """Agent API 테스트"""
        response = client.post(
            "/api/v2/agent/query",
            json={"query": "경기도 화성시 아파트 감정가?"},
            headers={"Authorization": "Bearer TEST_TOKEN"}
        )
        
        assert response.status_code == 200
        assert "response" in response.json()
```

### 7.3 성능 테스트 (Performance Tests)

```bash
# Apache JMeter 또는 Locust

# Locust 사용 예시
locust -f locustfile.py --host=http://localhost:8000

# 목표
# - 응답 시간 p95: < 100ms
# - 동시 사용자 100명에서 에러율: < 0.1%
```

---

## 8. 배포 및 운영

### 8.1 Docker 배포

```dockerfile
# Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드
COPY . .

# Port
EXPOSE 8000

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  avm-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/avm_db
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: avm_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 8.2 모니터링

```python
# Prometheus 메트릭

from prometheus_client import Counter, Histogram

# Metrics
api_calls = Counter('api_calls_total', 'Total API calls', ['endpoint', 'method', 'status'])
api_latency = Histogram('api_latency_seconds', 'API latency', ['endpoint'])
avm_estimates = Counter('avm_estimates_total', 'Total AVM estimates')

# 사용
@app.get("/api/v2/avm/estimate")
async def estimate_avm(...):
    with api_latency.labels(endpoint="/avm/estimate").time():
        result = engine.estimate(...)
        api_calls.labels(endpoint="/avm/estimate", method="GET", status=200).inc()
        avm_estimates.inc()
```

### 8.3 로깅

```python
# Logging 설정

import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("avm")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    "logs/avm.log",
    maxBytes=10485760,  # 10MB
    backupCount=10
)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 사용
logger.info(f"AVM estimation for property {property_id}: {point_estimate}")
```

---

## 부록: 용어정의

| 용어 | 정의 |
|------|------|
| **AVM** | 자동감정평가모델 (Automated Valuation Model) |
| **비교법** | 유사한 거래사례를 이용한 감정평가 방법 |
| **시점수정** | 거래 시점과 현재 시점의 시장 변화를 반영 |
| **NPL** | 부실채권 (Non-Performing Loan) |
| **공시가격** | 정부에서 공식 공표한 부동산 가격 |
| **KB시세** | KB 부동산에서 공표하는 시장 시세 |
| **지가변동률** | 공시지가의 변화율 |
| **헤도닉모델** | 상품의 특성과 가격의 관계를 분석하는 모형 |
| **IQR** | 사분위수 범위 (Interquartile Range) |
| **유사도** | 대상 물건과 비교사례의 유사 정도 (0~1) |

---

**작성일**: 2026-06-09  
**최종 수정**: -  
**상태**: Draft (검토 대기)
