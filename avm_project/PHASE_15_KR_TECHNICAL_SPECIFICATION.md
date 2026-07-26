# Phase 15.KR - 서버 배포 기술 명세서

**버전**: 1.0  
**작성일**: 2026-07-22  
**상태**: 기술 명세 완성  
**목표 기간**: 2026-08-16 ~ 2026-08-31  
**우선순위**: 최우선 (한국 국내 개발)

---

## 📋 목차

1. [개요](#개요)
2. [기술 요구사항](#기술-요구사항)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [API 명세](#api-명세)
5. [데이터베이스 설계](#데이터베이스-설계)
6. [캐싱 전략](#캐싱-전략)
7. [Docker 구성](#docker-구성)
8. [모니터링 및 로깅](#모니터링-및-로깅)
9. [배포 절차](#배포-절차)
10. [성능 요구사항](#성능-요구사항)
11. [보안 명세](#보안-명세)
12. [테스트 명세](#테스트-명세)

---

## 개요

### 목표
- 고가용성 Python FastAPI 서버 구축
- PostgreSQL 기반 데이터 저장소
- Redis 캐싱으로 응답 시간 최소화
- 100ms 이내 예측 응답 시간
- 99.9% 가용성 (SLA)
- 1,000+ QPS 처리 능력

### 범위
- FastAPI 애플리케이션 개발
- PostgreSQL 데이터베이스 설계
- Redis 캐시 계층
- Docker 컨테이너화
- 모니터링 스택 (Prometheus + Grafana)
- 로깅 시스템 (ELK Stack)
- 배포 자동화 (GitHub Actions)

### 출력물
```
phase15_kr_server/
├── app/
│   ├── main.py (300 lines)
│   ├── models.py (150 lines)
│   ├── schemas.py (100 lines)
│   ├── routers/
│   │   ├── predictions.py (200 lines)
│   │   ├── models.py (150 lines)
│   │   └── health.py (80 lines)
│   └── services/
│       ├── prediction_service.py (250 lines)
│       ├── cache_service.py (180 lines)
│       └── model_loader.py (120 lines)
├── db/
│   ├── models.py (200 lines)
│   ├── schemas.py (150 lines)
│   └── migrations/ (Alembic)
├── config/
│   └── settings.py (200 lines)
├── tests/
│   ├── test_predictions.py (300 lines)
│   ├── test_cache.py (200 lines)
│   └── test_database.py (250 lines)
├── docker/
│   ├── Dockerfile (50 lines)
│   └── docker-compose.yml (100 lines)
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
├── scripts/
│   ├── init_db.py
│   ├── load_models.py
│   └── backup_db.py
└── requirements.txt
```

---

## 기술 요구사항

### 서버 사양
- **CPU**: 4-8 cores
- **메모리**: 16-32GB RAM
- **스토리지**: SSD 200GB (models + data)
- **네트워크**: 1Gbps 이상

### 소프트웨어 스택
| 계층 | 기술 | 버전 |
|------|------|------|
| 런타임 | Python | 3.11+ |
| 웹프레임워크 | FastAPI | 0.104+ |
| 비동기 서버 | Uvicorn | 0.24+ |
| ORM | SQLAlchemy | 2.0+ |
| DB | PostgreSQL | 15+ |
| 캐시 | Redis | 7.0+ |
| 모니터링 | Prometheus | 2.40+ |
| 시각화 | Grafana | 10.0+ |
| 컨테이너 | Docker | 24.0+ |
| 오케스트레이션 | Kubernetes | 1.27+ |

### 의존성
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
alembic==1.13.1
prometheus-client==0.19.0
python-multipart==0.0.6
aioredis==2.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

---

## 시스템 아키텍처

### 고수준 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                    클라이언트 레이어                           │
│   (모바일앱, 웹앱, 외부시스템)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│                   로드 밸런서 (Nginx/AWS ALB)                 │
│              (SSL/TLS, Rate Limiting, CORS)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼─────┐ ┌─────▼──────┐ ┌────▼──────────┐
│ FastAPI     │ │ FastAPI    │ │ FastAPI      │
│ Instance 1  │ │ Instance 2 │ │ Instance N   │
│ (Uvicorn)   │ │ (Uvicorn)  │ │ (Uvicorn)    │
└─────┬───────┘ └─────┬──────┘ └────┬──────────┘
      │               │             │
      │   ┌───────────┼──────────────┘
      │   │
      │   ├─────────────────────────────────┐
      │   │                                 │
┌─────▼───▼──────┐             ┌────────────▼────────┐
│  Redis Cache   │             │  PostgreSQL DB      │
│  (6GB, TTL)    │             │  (Primary + Replica)│
└────────────────┘             └─────────────────────┘
      ▲
      │ (Model Loading)
┌─────┴──────────────────────────────┐
│  Model Storage (NFS/S3)             │
│  - KR_nationwide_v1.0.pkl           │
│  - KR_nationwide_v1.0_int8.bin      │
│  - KR_seoul_*.pkl, .bin             │
│  - ... (5개 지역)                    │
└────────────────────────────────────┘
```

### 요청 흐름
```
1. Client Request (HTTP POST /predict)
   ↓
2. Load Balancer (Rate Limiting, SSL/TLS)
   ↓
3. FastAPI (Request Validation)
   ↓
4. Cache Check (Redis)
   ├─ HIT: Return cached result (2ms)
   └─ MISS: Continue to step 5
   ↓
5. Feature Engineering (Feature Service)
   ↓
6. Model Selection (Regional/Nationwide)
   ↓
7. Prediction (Model Inference)
   ├─ Quantized Model: 5-10ms
   └─ Full Model: 50ms
   ↓
8. Database Logging (Async)
   ├─ Prediction record
   ├─ User feedback
   └─ Performance metrics
   ↓
9. Cache Write (Redis, TTL: 24h)
   ↓
10. Response (JSON)
```

---

## API 명세

### 기본 설정
```
Base URL: https://api.loan4u-kr.com/v1
API Version: 1.0
Response Format: JSON
Authentication: JWT Bearer Token
Rate Limit: 1,000 req/min per token
```

### 1. 예측 API (Nationwide)

**엔드포인트**: `POST /predict/nationwide`

**요청**:
```json
{
  "property_type": "apartment",
  "area_sqm": 84.5,
  "building_year": 2015,
  "floor": 15,
  "total_floors": 30,
  "has_parking": true,
  "distance_to_station_km": 0.5,
  "interest_rate": 5.2,
  "loan_term_years": 30,
  "down_payment_pct": 20,
  "user_id": "user_12345"
}
```

**응답** (성공):
```json
{
  "request_id": "req_20260722_001",
  "status": "success",
  "prediction": {
    "estimated_price": 450000000,
    "price_range": {
      "min": 425000000,
      "max": 475000000
    },
    "confidence": 0.92,
    "confidence_level": "High",
    "mape": 0.087,
    "model_version": "v1.0"
  },
  "market_analysis": {
    "market_trend": "upward",
    "trend_pct": 3.5,
    "comparable_properties": 245,
    "avg_price_sqm": 5312000
  },
  "timestamp": "2026-07-22T14:30:00Z",
  "processing_time_ms": 45
}
```

**응답** (에러):
```json
{
  "request_id": "req_20260722_001",
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "area_sqm must be between 20 and 300",
    "field": "area_sqm"
  },
  "timestamp": "2026-07-22T14:30:00Z"
}
```

**상태 코드**:
| 코드 | 의미 | 처리 |
|------|------|------|
| 200 | 성공 | 결과 반환 |
| 400 | 유효하지 않은 입력 | 클라이언트 수정 필요 |
| 401 | 인증 실패 | Token 갱신 |
| 429 | Rate limit | Retry-After 대기 |
| 500 | 서버 에러 | 재시도 (지수 백오프) |
| 503 | 서비스 불가 | 대기 후 재시도 |

### 2. 예측 API (지역별)

**엔드포인트**: `POST /predict/regional`

**요청**:
```json
{
  "region": "seoul",
  "property_type": "apartment",
  "area_sqm": 84.5,
  "building_year": 2015,
  "floor": 15,
  "total_floors": 30,
  "has_parking": true,
  "distance_to_station_km": 0.5,
  "interest_rate": 5.2,
  "loan_term_years": 30,
  "down_payment_pct": 20,
  "user_id": "user_12345"
}
```

**지역 코드**:
```python
REGIONS = {
    'seoul': 'KR_seoul_v1.0',
    'busan': 'KR_busan_v1.0',
    'gyeonggi': 'KR_gyeonggi_v1.0',
    'daegu': 'KR_daegu_v1.0',
    'incheon': 'KR_incheon_v1.0',
}
```

**응답** (동일하게 성공/실패):
```json
{
  "request_id": "req_20260722_001",
  "status": "success",
  "prediction": {
    "estimated_price": 480000000,
    "price_range": {
      "min": 465000000,
      "max": 495000000
    },
    "confidence": 0.94,
    "confidence_level": "High",
    "mape": 0.074,
    "model_version": "v1.0",
    "region": "seoul"
  },
  "market_analysis": {
    "market_trend": "upward",
    "trend_pct": 4.2,
    "comparable_properties": 512,
    "avg_price_sqm": 5680000,
    "gangnam_premium": 1.15
  },
  "timestamp": "2026-07-22T14:30:00Z",
  "processing_time_ms": 8
}
```

### 3. 모델 정보 API

**엔드포인트**: `GET /models/info`

**응답**:
```json
{
  "status": "success",
  "models": [
    {
      "model_id": "KR_nationwide_v1.0",
      "region": "nationwide",
      "version": "v1.0",
      "trained_date": "2026-07-22T00:00:00Z",
      "performance": {
        "mape": 0.8361,
        "r2": 0.404,
        "n_samples": 4900
      },
      "status": "production",
      "size_mb": 75
    },
    {
      "model_id": "KR_seoul_v1.0",
      "region": "seoul",
      "version": "v1.0",
      "trained_date": "2026-07-22T00:00:00Z",
      "performance": {
        "mape": 0.0937,
        "r2": 0.944,
        "n_samples": 980
      },
      "status": "production",
      "size_mb": 55
    }
  ],
  "timestamp": "2026-07-22T14:30:00Z"
}
```

### 4. 헬스 체크 API

**엔드포인트**: `GET /health`

**응답** (정상):
```json
{
  "status": "healthy",
  "timestamp": "2026-07-22T14:30:00Z",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "models": "ok",
    "disk_space_gb": 185.5
  },
  "uptime_hours": 720.5
}
```

**응답** (문제):
```json
{
  "status": "degraded",
  "timestamp": "2026-07-22T14:30:00Z",
  "checks": {
    "database": "ok",
    "cache": "degraded",
    "models": "ok",
    "disk_space_gb": 25.3
  },
  "warnings": ["Cache response time > 100ms", "Low disk space"]
}
```

### 5. 메트릭 API

**엔드포인트**: `GET /metrics`

**형식**: Prometheus 텍스트 형식

```
# HELP predictions_total Total number of predictions
predictions_total{region="seoul"} 15342
predictions_total{region="busan"} 8923
predictions_total{region="nationwide"} 2145

# HELP prediction_latency_ms Prediction latency in milliseconds
prediction_latency_ms{percentile="p50"} 12
prediction_latency_ms{percentile="p95"} 45
prediction_latency_ms{percentile="p99"} 85

# HELP cache_hit_rate Cache hit ratio
cache_hit_rate 0.76

# HELP models_loaded_count Number of loaded models
models_loaded_count 6
```

---

## 데이터베이스 설계

### PostgreSQL 스키마

#### 1. predictions 테이블
```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 요청 정보
    request_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 입력 데이터
    property_type VARCHAR(20) NOT NULL,
    region VARCHAR(20) NOT NULL,
    area_sqm NUMERIC(8, 2) NOT NULL,
    building_year INTEGER NOT NULL,
    floor INTEGER NOT NULL,
    total_floors INTEGER NOT NULL,
    has_parking BOOLEAN,
    distance_to_station_km NUMERIC(6, 2),
    interest_rate NUMERIC(5, 2),
    loan_term_years INTEGER,
    down_payment_pct NUMERIC(5, 2),
    
    -- 예측 결과
    estimated_price BIGINT NOT NULL,
    price_min BIGINT NOT NULL,
    price_max BIGINT NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL,
    mape NUMERIC(5, 4),
    model_version VARCHAR(20) NOT NULL,
    processing_time_ms INTEGER,
    
    -- 캐시
    cached BOOLEAN DEFAULT FALSE,
    cache_hit_time TIMESTAMP WITH TIME ZONE,
    
    -- 인덱스
    CONSTRAINT area_sqm_valid CHECK (area_sqm > 0),
    CONSTRAINT building_year_valid CHECK (building_year >= 1900)
);

CREATE INDEX idx_predictions_user_id ON predictions(user_id);
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp DESC);
CREATE INDEX idx_predictions_region ON predictions(region);
CREATE INDEX idx_predictions_request_id ON predictions(request_id);
```

#### 2. model_versions 테이블
```sql
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    model_id VARCHAR(50) NOT NULL UNIQUE,
    region VARCHAR(20) NOT NULL,
    version VARCHAR(10) NOT NULL,
    
    -- 메타데이터
    trained_date TIMESTAMP WITH TIME ZONE NOT NULL,
    training_samples INTEGER NOT NULL,
    
    -- 성능 메트릭
    mape NUMERIC(5, 4) NOT NULL,
    r2 NUMERIC(5, 4) NOT NULL,
    
    -- 파일 정보
    file_path VARCHAR(500) NOT NULL,
    file_size_mb INTEGER NOT NULL,
    file_hash VARCHAR(64),
    
    -- 상태
    status VARCHAR(20) NOT NULL DEFAULT 'training',
    is_active BOOLEAN DEFAULT FALSE,
    deployment_date TIMESTAMP WITH TIME ZONE,
    
    -- 추적
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_model_versions_active ON model_versions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_model_versions_region ON model_versions(region);
```

#### 3. user_feedback 테이블
```sql
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    prediction_id UUID NOT NULL REFERENCES predictions(id),
    user_id VARCHAR(100) NOT NULL,
    
    -- 피드백
    feedback_type VARCHAR(20) NOT NULL,  -- 'accurate', 'low', 'high', 'other'
    actual_price BIGINT,
    notes TEXT,
    
    -- 추적
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_feedback_prediction_id ON user_feedback(prediction_id);
CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);
```

#### 4. performance_metrics 테이블
```sql
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 시간 정보
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    hour TIMESTAMP NOT NULL,
    
    -- 집계 메트릭
    total_predictions INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms NUMERIC(8, 2),
    p95_latency_ms NUMERIC(8, 2),
    p99_latency_ms NUMERIC(8, 2),
    cache_hit_rate NUMERIC(3, 2),
    error_rate NUMERIC(5, 4),
    
    -- 지역별
    region VARCHAR(20),
    model_id VARCHAR(50),
    
    -- 평균 신뢰도
    avg_confidence NUMERIC(3, 2)
);

CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp DESC);
CREATE INDEX idx_performance_metrics_hour ON performance_metrics(hour);
CREATE INDEX idx_performance_metrics_region ON performance_metrics(region);
```

#### 5. api_keys 테이블
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(100) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100),
    
    -- 제한
    rate_limit_per_min INTEGER DEFAULT 1000,
    daily_limit INTEGER DEFAULT 50000,
    
    -- 추적
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(user_id, name)
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id) WHERE is_active = TRUE;
```

### 데이터베이스 초기화
```python
# scripts/init_db.py
from sqlalchemy import create_engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

def init_database(database_url: str):
    """데이터베이스 초기화"""
    engine = create_engine(database_url)
    
    with engine.begin() as connection:
        # Alembic 마이그레이션 실행
        migration_context = MigrationContext.configure(connection)
        operations = Operations(migration_context)
        
        # 최신 버전으로 마이그레이션
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        
        for rev in script.walk_revisions(head=None):
            operations.upgrade(rev.revision)
    
    print("✅ Database initialized successfully")
```

---

## 캐싱 전략

### Redis 구성
```python
# app/services/cache_service.py

import redis
import json
from datetime import timedelta
from typing import Optional, Any

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.namespace = "loan4u"
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """캐시 키 생성"""
        return f"{self.namespace}:{prefix}:{identifier}"
    
    async def get_prediction_cache(
        self, 
        prediction_hash: str
    ) -> Optional[dict]:
        """예측 결과 캐시 조회"""
        key = self._make_key("prediction", prediction_hash)
        
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def set_prediction_cache(
        self,
        prediction_hash: str,
        result: dict,
        ttl_hours: int = 24
    ) -> bool:
        """예측 결과 캐시 저장"""
        key = self._make_key("prediction", prediction_hash)
        ttl = timedelta(hours=ttl_hours)
        
        self.redis.setex(
            key,
            ttl,
            json.dumps(result)
        )
        return True
    
    async def get_model(self, model_id: str) -> Optional[Any]:
        """모델 객체 캐시 조회 (바이너리)"""
        key = self._make_key("model", model_id)
        return self.redis.get(key)
    
    async def set_model(
        self,
        model_id: str,
        model_data: bytes,
        ttl_hours: int = 720  # 30 days
    ) -> bool:
        """모델 객체 캐시 저장"""
        key = self._make_key("model", model_id)
        ttl = timedelta(hours=ttl_hours)
        
        self.redis.setex(key, ttl, model_data)
        return True
    
    async def increment_counter(
        self,
        counter_name: str,
        increment: int = 1
    ) -> int:
        """카운터 증가"""
        key = self._make_key("counter", counter_name)
        return self.redis.incrby(key, increment)
    
    async def get_counter(self, counter_name: str) -> int:
        """카운터 값 조회"""
        key = self._make_key("counter", counter_name)
        value = self.redis.get(key)
        return int(value) if value else 0
    
    async def clear_cache(self, prefix: str) -> int:
        """캐시 초기화"""
        pattern = f"{self.namespace}:{prefix}:*"
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
    
    async def get_cache_stats(self) -> dict:
        """캐시 통계"""
        info = self.redis.info()
        return {
            "used_memory_mb": info.get("used_memory_mb", 0),
            "evicted_keys": info.get("evicted_keys", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / (
                info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)
            )
        }

# 캐시 키 구조
"""
loan4u:prediction:{hash}
  - SHA256({property_type}_{area_sqm}_{building_year}_{region})
  - TTL: 24시간
  - 크기: ~500 bytes

loan4u:model:{model_id}
  - 로드된 모델 객체 (메모리 효율)
  - TTL: 30일
  - 크기: 50-75MB

loan4u:counter:predictions_total
  - 전체 예측 수
  - 1시간마다 리셋

loan4u:counter:cache_hits
  - 캐시 히트 수
  - 1시간마다 리셋
"""
```

### 캐시 전략
| 항목 | TTL | 크기 | 우선순위 | 정책 |
|------|-----|------|---------|------|
| 예측 결과 | 24시간 | 500B | 높음 | LRU |
| 모델 객체 | 30일 | 50-75MB | 높음 | 수동 갱신 |
| 성능 메트릭 | 1시간 | 1KB | 중간 | TTL 만료 |
| 사용자 세션 | 7일 | 100B | 낮음 | LRU |

---

## Docker 구성

### Dockerfile
```dockerfile
# stage 1: builder
FROM python:3.11-slim as builder

WORKDIR /build

# 의존성 설치
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# stage 2: runtime
FROM python:3.11-slim

WORKDIR /app

# 보안: 비루트 사용자
RUN useradd -m -u 1000 appuser

# 빌더에서 의존성 복사
COPY --from=builder /root/.local /home/appuser/.local

# 애플리케이션 코드
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser db/ ./db/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser alembic.ini .

# 환경 설정
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER appuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  # FastAPI 애플리케이션 (3개 인스턴스)
  api-1:
    build: .
    container_name: loan4u_api_1
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://loan4u:password@postgres:5432/loan4u_kr
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - loan4u_network
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  api-2:
    build: .
    container_name: loan4u_api_2
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=postgresql://loan4u:password@postgres:5432/loan4u_kr
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - loan4u_network
    restart: always

  api-3:
    build: .
    container_name: loan4u_api_3
    ports:
      - "8003:8000"
    environment:
      - DATABASE_URL=postgresql://loan4u:password@postgres:5432/loan4u_kr
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - loan4u_network
    restart: always

  # PostgreSQL 데이터베이스
  postgres:
    image: postgres:15-alpine
    container_name: loan4u_postgres
    environment:
      - POSTGRES_DB=loan4u_kr
      - POSTGRES_USER=loan4u
      - POSTGRES_PASSWORD=secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init_scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - loan4u_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U loan4u"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  # Redis 캐시
  redis:
    image: redis:7-alpine
    container_name: loan4u_redis
    command: redis-server --maxmemory 6gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - loan4u_network
    restart: always

  # Nginx 로드 밸런서
  nginx:
    image: nginx:alpine
    container_name: loan4u_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api-1
      - api-2
      - api-3
    networks:
      - loan4u_network
    restart: always

  # Prometheus 모니터링
  prometheus:
    image: prom/prometheus:latest
    container_name: loan4u_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - loan4u_network
    restart: always

  # Grafana 대시보드
  grafana:
    image: grafana/grafana:latest
    container_name: loan4u_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    depends_on:
      - prometheus
    networks:
      - loan4u_network
    restart: always

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  loan4u_network:
    driver: bridge
```

---

## 모니터링 및 로깅

### Prometheus 메트릭

```python
# app/services/metrics_service.py

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict

class MetricsService:
    # 카운터
    predictions_total = Counter(
        'predictions_total',
        'Total number of predictions',
        ['region', 'model_version']
    )
    
    prediction_errors_total = Counter(
        'prediction_errors_total',
        'Total prediction errors',
        ['region', 'error_type']
    )
    
    # 히스토그램
    prediction_latency_ms = Histogram(
        'prediction_latency_ms',
        'Prediction latency in milliseconds',
        ['region'],
        buckets=(5, 10, 25, 50, 100, 250, 500, 1000)
    )
    
    db_query_latency_ms = Histogram(
        'db_query_latency_ms',
        'Database query latency',
        ['query_type'],
        buckets=(1, 5, 10, 50, 100, 250)
    )
    
    # 게이지
    cache_size_bytes = Gauge(
        'cache_size_bytes',
        'Cache memory usage'
    )
    
    models_loaded = Gauge(
        'models_loaded_count',
        'Number of loaded models',
        ['region']
    )
    
    cache_hit_rate = Gauge(
        'cache_hit_rate',
        'Cache hit rate'
    )
    
    active_connections = Gauge(
        'active_connections',
        'Active database connections'
    )

    @staticmethod
    def record_prediction(region: str, model_version: str):
        """예측 기록"""
        MetricsService.predictions_total.labels(
            region=region,
            model_version=model_version
        ).inc()
    
    @staticmethod
    def record_error(region: str, error_type: str):
        """에러 기록"""
        MetricsService.prediction_errors_total.labels(
            region=region,
            error_type=error_type
        ).inc()
```

### Prometheus 설정
```yaml
# monitoring/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['api-1:8000', 'api-2:8000', 'api-3:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'rules.yml'
```

### Grafana 대시보드
```json
{
  "dashboard": {
    "title": "Loan4U Korea API Monitoring",
    "panels": [
      {
        "title": "Predictions Per Minute",
        "targets": [
          {
            "expr": "rate(predictions_total[1m])"
          }
        ]
      },
      {
        "title": "Average Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, prediction_latency_ms)"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "cache_hit_rate"
          }
        ]
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "active_connections"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(prediction_errors_total[5m])"
          }
        ]
      }
    ]
  }
}
```

---

## 배포 절차

### 1. 사전 준비 (준비 단계)

```bash
#!/bin/bash
# scripts/pre_deployment_check.sh

set -e

echo "🔍 Pre-deployment checks..."

# 1. 환경 변수 확인
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "API_KEY_SECRET"
    "JWT_SECRET"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

# 2. 데이터베이스 연결 확인
echo "Testing database connection..."
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('✅ Database connection OK')
"

# 3. Redis 연결 확인
echo "Testing Redis connection..."
python -c "
import redis
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()
print('✅ Redis connection OK')
"

# 4. 모델 파일 확인
echo "Checking model files..."
models_dir="output/models/korea"
required_models=("KR_nationwide_v1.0.pkl" "KR_seoul_v1.0.pkl")

for model in "${required_models[@]}"; do
    if [ ! -f "$models_dir/$model" ]; then
        echo "❌ Missing model: $model"
        exit 1
    fi
done
echo "✅ All models present"

echo "✅ All pre-deployment checks passed"
```

### 2. 배포 (배포 단계)

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

DEPLOYMENT_ENV=$1
DOCKER_REGISTRY="registry.example.com"
APP_VERSION="1.0.0"

if [ -z "$DEPLOYMENT_ENV" ]; then
    echo "Usage: ./deploy.sh [staging|production]"
    exit 1
fi

echo "🚀 Deploying to $DEPLOYMENT_ENV..."

# 1. Docker 이미지 빌드
echo "📦 Building Docker image..."
docker build -t "$DOCKER_REGISTRY/loan4u-api:$APP_VERSION" .
docker push "$DOCKER_REGISTRY/loan4u-api:$APP_VERSION"

# 2. Kubernetes 배포
echo "🌐 Deploying to Kubernetes..."
kubectl set image deployment/loan4u-api \
  loan4u-api="$DOCKER_REGISTRY/loan4u-api:$APP_VERSION" \
  -n loan4u-$DEPLOYMENT_ENV

# 3. 배포 대기
echo "⏳ Waiting for deployment..."
kubectl rollout status deployment/loan4u-api -n loan4u-$DEPLOYMENT_ENV

# 4. 헬스체크
echo "🏥 Running health checks..."
kubectl run health-check-pod \
  --image=curlimages/curl:latest \
  --rm -i --restart=Never \
  -- curl -f http://loan4u-api:8000/health

echo "✅ Deployment successful"
```

### 3. 배포 후 검증 (검증 단계)

```python
# scripts/post_deployment_test.py

import requests
import time
from typing import List

def run_post_deployment_tests(api_url: str, timeout: int = 300) -> bool:
    """배포 후 검증"""
    
    print("🧪 Running post-deployment tests...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 1. 헬스체크
            response = requests.get(f"{api_url}/health", timeout=5)
            assert response.status_code == 200
            print("✅ Health check passed")
            
            # 2. 모델 정보 확인
            response = requests.get(f"{api_url}/models/info", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert len(data['models']) >= 6
            print(f"✅ Models loaded: {len(data['models'])}")
            
            # 3. 예측 테스트
            payload = {
                "property_type": "apartment",
                "area_sqm": 84.5,
                "building_year": 2015,
                "floor": 15,
                "total_floors": 30,
                "has_parking": True,
                "distance_to_station_km": 0.5
            }
            response = requests.post(
                f"{api_url}/predict/nationwide",
                json=payload,
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert 'prediction' in data
            assert data['prediction']['estimated_price'] > 0
            print("✅ Prediction test passed")
            
            # 4. 성능 테스트
            latencies = []
            for _ in range(10):
                start = time.time()
                requests.post(f"{api_url}/predict/nationwide", json=payload)
                latencies.append((time.time() - start) * 1000)
            
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[9]
            
            assert avg_latency < 100, f"Average latency too high: {avg_latency:.0f}ms"
            assert p95_latency < 200, f"P95 latency too high: {p95_latency:.0f}ms"
            print(f"✅ Performance OK (avg: {avg_latency:.0f}ms, p95: {p95_latency:.0f}ms)")
            
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                print(f"❌ Tests failed after {timeout}s: {e}")
                return False
            print(f"⏳ Retrying in 10s... ({elapsed:.0f}s elapsed)")
            time.sleep(10)
    
    return False
```

### 4. 배포 자동화 (GitHub Actions)

```yaml
# .github/workflows/deploy_server.yml

name: Deploy Server

on:
  push:
    branches: [main]
    paths:
      - 'phase15_kr_server/**'
      - '.github/workflows/deploy_server.yml'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Pre-deployment checks
        run: bash scripts/pre_deployment_check.sh

      - name: Build and push Docker image
        run: |
          docker login -u ${{ secrets.DOCKER_USERNAME }} -p ${{ secrets.DOCKER_PASSWORD }}
          docker build -t loan4u-api:${{ github.sha }} .
          docker push loan4u-api:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: bash scripts/deploy.sh production

      - name: Post-deployment tests
        run: python scripts/post_deployment_test.py https://api.loan4u-kr.com
```

---

## 성능 요구사항

### SLA (Service Level Agreement)

| 메트릭 | 목표 | 측정 방법 |
|--------|------|---------|
| 가용성 | 99.9% (36분/월) | 분당 헬스체크 |
| 응답 시간 (P50) | <20ms | 요청 로그 |
| 응답 시간 (P95) | <50ms | 요청 로그 |
| 응답 시간 (P99) | <100ms | 요청 로그 |
| 처리량 | 1,000+ QPS | Prometheus |
| 캐시 히트율 | >75% | Redis 통계 |

### 부하 테스트

```python
# scripts/load_test.py

import concurrent.futures
import requests
import time
import statistics
from typing import List

def load_test(
    api_url: str,
    duration_seconds: int = 60,
    concurrent_users: int = 100,
    rps_target: int = 1000
) -> dict:
    """부하 테스트"""
    
    print(f"🧪 Load test: {concurrent_users} users, {rps_target} RPS target")
    
    latencies: List[float] = []
    errors = 0
    success = 0
    
    payload = {
        "property_type": "apartment",
        "area_sqm": 84.5,
        "building_year": 2015,
        "floor": 15,
        "total_floors": 30,
        "has_parking": True,
        "distance_to_station_km": 0.5
    }
    
    start_time = time.time()
    
    def make_request():
        try:
            start = time.time()
            response = requests.post(
                f"{api_url}/predict/nationwide",
                json=payload,
                timeout=10
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return ('success', latency)
            else:
                return ('error', latency)
        except Exception as e:
            return ('error', -1)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        
        while time.time() - start_time < duration_seconds:
            for _ in range(min(10, concurrent_users)):
                future = executor.submit(make_request)
                futures.append(future)
            
            # 결과 수집
            for future in concurrent.futures.as_completed(futures):
                result_type, latency = future.result()
                
                if result_type == 'success':
                    success += 1
                    latencies.append(latency)
                else:
                    errors += 1
            
            futures = []
    
    # 결과 분석
    results = {
        'total_requests': success + errors,
        'successful': success,
        'failed': errors,
        'error_rate': errors / (success + errors) if success + errors > 0 else 0,
        'latency_p50': statistics.median(latencies) if latencies else 0,
        'latency_p95': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        'latency_p99': sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
        'latency_avg': statistics.mean(latencies) if latencies else 0,
        'duration_seconds': time.time() - start_time,
        'rps': success / (time.time() - start_time),
    }
    
    print("\n📊 Load test results:")
    print(f"  Total requests: {results['total_requests']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']} ({results['error_rate']*100:.2f}%)")
    print(f"  P50 latency: {results['latency_p50']:.0f}ms")
    print(f"  P95 latency: {results['latency_p95']:.0f}ms")
    print(f"  P99 latency: {results['latency_p99']:.0f}ms")
    print(f"  RPS: {results['rps']:.0f}")
    
    return results
```

---

## 보안 명세

### 인증 및 인가

```python
# app/security/auth.py

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

class TokenData(BaseModel):
    user_id: str
    scopes: list[str] = []

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    user_id: str,
    expires_delta: timedelta = None
) -> str:
    """JWT 토큰 생성"""
    
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": user_id, "exp": expire}
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return encoded_jwt

async def verify_token(token: str) -> TokenData:
    """토큰 검증"""
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token")
        return TokenData(user_id=user_id)
    except JWTError:
        raise ValueError("Invalid token")

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)
```

### Rate Limiting

```python
# app/middleware/rate_limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@app.get("/predict/nationwide")
@limiter.limit("100/minute")
async def predict_nationwide(request: Request):
    """100 요청/분 제한"""
    pass
```

### CORS 설정

```python
# app/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://loan4u.com", "https://app.loan4u.com"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 데이터 암호화

```python
# app/security/encryption.py

from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt_user_id(self, user_id: str) -> str:
        """사용자 ID 암호화"""
        return self.cipher.encrypt(user_id.encode()).decode()
    
    def decrypt_user_id(self, encrypted: str) -> str:
        """사용자 ID 복호화"""
        return self.cipher.decrypt(encrypted.encode()).decode()
```

---

## 테스트 명세

### 통합 테스트

```python
# tests/test_predictions.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPredictions:
    def test_predict_nationwide_success(self):
        """nationwide 예측 성공"""
        payload = {
            "property_type": "apartment",
            "area_sqm": 84.5,
            "building_year": 2015,
            "floor": 15,
            "total_floors": 30,
            "has_parking": True,
            "distance_to_station_km": 0.5
        }
        
        response = client.post("/predict/nationwide", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert data["prediction"]["estimated_price"] > 0
        assert data["prediction"]["confidence"] > 0.5
    
    def test_predict_regional_success(self):
        """regional 예측 성공"""
        payload = {
            "region": "seoul",
            "property_type": "apartment",
            "area_sqm": 84.5,
            "building_year": 2015,
            "floor": 15,
            "total_floors": 30,
            "has_parking": True,
            "distance_to_station_km": 0.5
        }
        
        response = client.post("/predict/regional", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"]["region"] == "seoul"
    
    def test_predict_invalid_input(self):
        """유효하지 않은 입력 처리"""
        payload = {
            "property_type": "apartment",
            "area_sqm": -10,  # Invalid
        }
        
        response = client.post("/predict/nationwide", json=payload)
        
        assert response.status_code == 400
        assert "error" in response.json()
    
    def test_cache_hit(self):
        """캐시 히트 확인"""
        payload = {
            "property_type": "apartment",
            "area_sqm": 84.5,
            "building_year": 2015,
            "floor": 15,
            "total_floors": 30,
            "has_parking": True,
            "distance_to_station_km": 0.5
        }
        
        # 첫 번째 요청
        response1 = client.post("/predict/nationwide", json=payload)
        time1 = response1.json()["processing_time_ms"]
        
        # 두 번째 요청 (캐시 히트)
        response2 = client.post("/predict/nationwide", json=payload)
        time2 = response2.json()["processing_time_ms"]
        
        # 캐시 히트 응답이 더 빨라야 함
        assert time2 < time1 * 0.5

class TestDatabase:
    def test_prediction_logging(self):
        """예측 기록 저장"""
        payload = {...}
        response = client.post("/predict/nationwide", json=payload)
        
        # 데이터베이스에서 확인
        # (생략)

class TestCache:
    def test_cache_operations(self):
        """캐시 작업 확인"""
        # (생략)
```

### 성능 테스트 체크리스트

- [ ] P50 응답시간 < 20ms
- [ ] P95 응답시간 < 50ms
- [ ] P99 응답시간 < 100ms
- [ ] 캐시 히트율 > 75%
- [ ] 에러율 < 0.1%
- [ ] 1,000 QPS 이상 처리 가능

---

## 배포 체크리스트

### 인프라 준비
- [ ] 서버 프로비저닝 (4-8 cores, 16-32GB RAM, 200GB SSD)
- [ ] PostgreSQL 15+ 설치 및 설정
- [ ] Redis 7.0+ 설치 및 설정
- [ ] Kubernetes 클러스터 준비
- [ ] SSL/TLS 인증서 설정

### 애플리케이션
- [ ] FastAPI 서버 코드 완성
- [ ] 모든 의존성 설치
- [ ] 환경 변수 설정
- [ ] 데이터베이스 마이그레이션
- [ ] 모델 파일 로드
- [ ] 보안 설정 (JWT, CORS, Rate limiting)

### 모니터링
- [ ] Prometheus 설정
- [ ] Grafana 대시보드 구성
- [ ] 알림 규칙 설정
- [ ] 로그 수집 설정

### 테스트
- [ ] 단위 테스트 (100% 통과)
- [ ] 통합 테스트 (100% 통과)
- [ ] 부하 테스트 (1,000 QPS)
- [ ] 성능 테스트 (P99 < 100ms)

### 배포
- [ ] 사전 검사 스크립트 실행
- [ ] Docker 이미지 빌드 및 푸시
- [ ] Kubernetes 배포
- [ ] 헬스체크 확인
- [ ] 배포 후 테스트 실행

### 운영
- [ ] 모니터링 대시보드 확인
- [ ] 알림 채널 설정 (Slack, Email, PagerDuty)
- [ ] 백업 정책 수립
- [ ] 재해 복구 계획 준비
- [ ] 로그 기간 설정 (90일 이상 보관)

---

## 다음 단계

### Phase 15.1.KR - Advanced Features
- Batch prediction API
- Async processing
- WebSocket 실시간 업데이트
- 예정: 2주

### Phase 15.2.KR - Security Hardening
- OAuth 2.0 / OpenID Connect
- API 키 로테이션
- 감사 로깅
- 예정: 1주

### Phase 15.3.KR - Optimization
- GraphQL API (선택적)
- gRPC 고성능 서버
- 데이터베이스 샤딩
- 예정: 2주

---

## 참고자료

- FastAPI 공식 문서: https://fastapi.tiangolo.com
- PostgreSQL 공식 문서: https://www.postgresql.org/docs
- Redis 공식 문서: https://redis.io/docs
- Kubernetes 공식 문서: https://kubernetes.io/docs
- Prometheus 공식 문서: https://prometheus.io/docs
- Grafana 공식 문서: https://grafana.com/docs

---

## 완료 기준

- [x] 시스템 아키텍처 설계
- [x] API 명세 작성
- [x] 데이터베이스 스키마 설계
- [x] 캐싱 전략 수립
- [x] Docker 구성 완성
- [x] 모니터링 설정
- [x] 배포 절차 문서화
- [x] 성능 요구사항 정의
- [x] 보안 명세 작성
- [x] 테스트 명세 작성
- [ ] 구현 시작 (다음 단계)
- [ ] 테스트 완료
- [ ] 배포 (프로덕션)

---

## 성공 메트릭

| 메트릭 | 목표 | 측정 시기 |
|--------|------|---------|
| 가용성 | 99.9% | 배포 후 1개월 |
| P95 응답시간 | <50ms | 배포 후 1주 |
| 캐시 히트율 | >75% | 배포 후 1주 |
| 에러율 | <0.1% | 실시간 |
| 사용자 만족도 | >4.5/5 | 배포 후 1개월 |

---

**Phase 15.KR 상태**: 🔄 **기술 명세 완성 → 구현 준비**

**다음 단계**: Phase 15.KR 구현 시작 (FastAPI 서버, PostgreSQL, Redis, Docker)

---

*작성일: 2026-07-22*
*관리자: Loan4U AVM 개발팀*
*우선순위: 최우선 (한국 국내 개발)*
