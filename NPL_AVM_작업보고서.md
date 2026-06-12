# NPL AVM 프로젝트 정리 및 버그 수정 보고서

**작업일**: 2026-06-12  
**브랜치**: `claude/code-session-connection-ml8t7v`  
**저장소**: `eugene-eungkwon-kim/-` → `npl_avm/` 서브디렉토리

---

## 1. 프로젝트 개요

NPL(부실채권) 담보자산 자동평가 시스템 (AVM, Automated Valuation Model)  
FastAPI + SQLAlchemy + SQLite 기반 REST API 서버

---

## 2. 작업 전 문제 목록

### 🔴 즉시 수정 필요 (Critical)

| # | 파일 | 문제 |
|---|------|------|
| 1 | 프로젝트 루트 | AI 에이전트 산출 마크다운 **140개** — 운영과 무관한 파일로 프로젝트 파악 불가 |
| 2 | `app/main.py` | `allow_origins=["*"]` + `allow_credentials=True` 조합 → 브라우저 CORS 차단 (RFC 위반) |
| 3 | `app/main.py` | `@app.on_event("startup")` — FastAPI에서 deprecated 경고 |
| 4 | `app/avm/engine_optimized.py` | `main.py`에서 import 안 됨 + 런타임 크래시 3개:<br>• `ComparableSale.transaction_date` (실제 필드명: `trade_date`)<br>• `ComparableSale.join(Property)` (FK 관계 없음)<br>• `class OptimizedAVMEngine(AVMEngine)` (AVMEngine 클래스 미존재) |
| 5 | `app/api/monitoring_routes.py` | `routes_monitoring.py`와 동일 역할인데 둘 다 존재, `main.py`는 `routes_monitoring`만 사용 |
| 6 | `app/utils/cache_manager.py` | 모듈 임포트 시 Redis 연결 시도 (사이드이펙트) — Redis 없으면 앱 시작 지연. L1Cache는 항상 `None` 반환. Dead code |
| 7 | `app/utils/query_optimizer.py` | `engine_optimized.py`에서만 사용 — Dead code |
| 8 | `app/db/database.py` | `DATABASE_URL` 하드코딩: `"sqlite:///D:/NPL전례/avm_project/data/npl_avm.db"` (Windows 절대경로) |
| 9 | `.env` / `.env.example` | 동일한 Windows 절대경로, 불필요한 `ANTHROPIC_API_KEY` / `KAKAO_REST_API_KEY` |

### 🟡 버그 수정 필요 (Bug)

| # | 파일 | 문제 |
|---|------|------|
| 10 | `app/api/routes.py` `auction_stats()` | `Appraisal` 조인 시 최신 감정평가 미필터 → 동일 물건 중복 집계로 낙찰가율 왜곡 |
| 11 | `app/api/routes_export.py` | 존재하지 않는 필드 다수 참조:<br>• `Appraisal.appraisal_value` → 실제: `total_value`<br>• `Appraisal.deal_id` → 미존재<br>• `Deal.auction_id` → 미존재<br>• `Auction.hammer_rate` → 미존재 (계산값)<br>• `ComparableSale.property_id` → 미존재<br>• `ComparableSale.transaction_date` → 실제: `trade_date` |
| 12 | `app/models/report_models.py` | 독립 `Base = declarative_base()` 사용 → `init_db()`에서 테이블 미생성 |
| 13 | `requirements.txt` | 미사용 패키지 포함: `anthropic`, `psycopg2-binary`, `geopy`<br>`redis` 누락 (cache_manager.py가 사용) |

### 🟢 개선 필요 (Enhancement)

| # | 파일 | 문제 |
|---|------|------|
| 14 | `app/avm/engine.py` | AVM 추정 로직이 **비교사례 감정가 단순 평균** — 면적 보정 없음, 단가 개념 없음 |
| 15 | `app/avm/engine.py` | 신뢰도(confidence)가 비교사례 수만으로 결정 — 값 분산 미반영 |
| 16 | `app/monitoring/metrics.py` | MetricsCollector 구현은 있으나 실제 HTTP 요청과 연결 안 됨 → 항상 빈 데이터 |
| 17 | `app/avm/engine.py` `auction_stats()` | 낙찰가율 avg만 반환 — min/max 없음 |

---

## 3. 수행한 작업

### Phase 1 — 파일 정리 (Cleanup)

**삭제된 파일/디렉토리:**

```
루트 *.md (140개)          AI_AGENT_*.md, FINAL_*.md, PHASE*.md,
                           SPECIFICATION_*.md, WBS_*.md, REVIEW_*.md 등

app/avm/engine_optimized.py    런타임 크래시 dead code
app/api/monitoring_routes.py   routes_monitoring.py 중복
app/utils/cache_manager.py     Redis 미설치 사이드이펙트 dead code
app/utils/query_optimizer.py   dead code

results/*.md (9개)         마크다운 보고서 (CSV/JSON/txt 데이터는 유지)
execution_logs/*.md (2개)  마크다운 로그 (.log 파일은 유지)

NPL_AVM_SYSTEM_HERMÈS_TRAINING.zip  중첩 zip
server.log / server_err.log         로그 파일
phase5_2_day1_execution.py          임시 실행 스크립트
deploy_phase2_auto.py               임시 배포 스크립트
verify_deployment.py                임시 검증 스크립트
backups/                            DB 백업 (소스코드 repo 불필요)
__pycache__/ 전체, *.pyc            Python 캐시
.pytest_cache/                      테스트 캐시
```

**git에서 제외된 대용량 바이너리 (`.gitignore` 추가):**

```
data/*.db          npl_avm.db (1.8MB)
data/*.duckdb      rtms_*.duckdb (780KB~2.1MB)
models/*.pkl       7개 모델 파일 (176KB~432KB)
.env               환경변수 (보안)
```

---

### Phase 2 — 보안 수정

**`app/main.py`**

```python
# Before (브라우저 차단)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,   # ← RFC 위반: wildcard + credentials 조합 불가
    allow_methods=["*"],
    allow_headers=["*"],
)

# After
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # ✅ 수정
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**`.env` / `.env.example`**

```
# Before
DATABASE_URL=sqlite:///D:/NPL전례/avm_project/data/npl_avm.db
ANTHROPIC_API_KEY=sk-ant-your_key_here
KAKAO_REST_API_KEY=YOUR_KAKAO_KEY_HERE

# After
DATABASE_URL=sqlite:///data/npl_avm.db
KOREA_API_KEY=your_api_key_here
```

---

### Phase 3 — 버그 수정

#### 3-1. `app/db/database.py` — 하드코딩 경로 수정

```python
# Before
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///D:/NPL전례/avm_project/data/npl_avm.db")

# After
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/npl_avm.db")
```

#### 3-2. `app/main.py` — deprecated API 교체

```python
# Before
@app.on_event("startup")
def startup():
    init_db()

# After
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(..., lifespan=lifespan)
```

#### 3-3. `app/avm/engine.py` — `auction_stats()` 중복 감정평가 N+1 수정

```python
# Before: 감정평가 전체 조인 → 동일 물건 중복 집계
.join(Appraisal, Appraisal.property_id == Property.id)

# After: 최신 감정평가만 서브쿼리로 필터
latest_appr = (
    db.query(Appraisal.property_id, func.max(Appraisal.appraisal_date).label("max_date"))
    .group_by(Appraisal.property_id)
    .subquery()
)
.join(latest_appr, latest_appr.c.property_id == Property.id)
.join(Appraisal, and_(
    Appraisal.property_id == Property.id,
    Appraisal.appraisal_date == latest_appr.c.max_date,
))
```

#### 3-4. `app/api/routes_export.py` — 잘못된 필드 참조 전면 수정

```python
# Before (존재하지 않는 필드)
appraisal.appraisal_value     → appraisal.total_value
Deal.id == Appraisal.deal_id  → Deal.id == Property.deal_id
Auction.id == Deal.auction_id → Auction.property_id == Property.id
auction.hammer_rate           → 직접 계산 (hammer/appr_val)
ComparableSale.property_id    → subject_property_serial
c.transaction_date            → c.trade_date
c.transaction_price           → c.trade_amount
c.address                     → c.address_full
```

또한 내보내기 포맷을 현실적으로 단순화:  
`csv | excel | json | parquet | hdf5 | sqlite` → `csv | excel | json`

#### 3-5. `app/models/report_models.py` — 독립 Base → 공유 Base 통합

```python
# Before: 독립 Base → init_db()에서 테이블 생성 안 됨
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# After: 메인 Base와 통합 → init_db() 시 자동 생성
from app.db.models import Base
```

#### 3-6. `requirements.txt` — 미사용 패키지 정리

```
제거: anthropic>=0.40.0    (LLM 에이전트 코드 미구현)
제거: psycopg2-binary      (SQLite 사용 중, PostgreSQL 미이관)
제거: geopy                (주소 정규화 코드 미사용)
```

---

### Phase 4 — 기능 개선

#### 4-1. AVM 추정 엔진 개선 (`app/avm/engine.py`)

**Before: 단순 평균**
```python
avg_val = int(sum(values) / len(values))
# → 면적 차이 무시, 단가 개념 없음
```

**After: 면적 유사도 가중 단가(원/㎡) 추정**
```python
def _weighted_estimate(comps, target_building_area):
    for comp in comps:
        unit_price = comp.appraisal_value / comp.building_area  # 원/㎡
        area_ratio = min(target, comp.area) / max(target, comp.area)  # 유사도
        weighted_sum += unit_price * area_ratio
        weight_total += area_ratio
    avg_unit_price = weighted_sum / weight_total
    return int(avg_unit_price * target_building_area), int(avg_unit_price)
```

응답에 `unit_price_per_sqm` 필드 추가.

**신뢰도 개선:**
```python
# Before: 비교사례 수만으로 판단
confidence = "HIGH" if n >= 5 else ("MEDIUM" if n >= 2 else "LOW")

# After: 비교사례 수 + 단가 변동계수(CV) 복합 판단
cv = std / mean  # 단가 변동계수
if n >= 5 and cv < 0.15: return "HIGH"   # 많고 일관됨
if n >= 3 and cv < 0.30: return "MEDIUM" # 적당하거나 다소 분산됨
return "LOW"
```

#### 4-2. `auction_stats()` 반환값 확장

```python
# Before: avg만 반환
{"result": ..., "count": ..., "avg_hammer_rate": ...}

# After: min/max 추가
{"result": ..., "count": ..., "avg_hammer_rate": ..., "min_hammer_rate": ..., "max_hammer_rate": ...}
```

#### 4-3. HTTP 메트릭 미들웨어 연결 (`app/main.py`)

```python
# Before: MetricsCollector 구현은 있으나 연결 안 됨 → 항상 빈 데이터

# After: 모든 HTTP 요청 자동 기록
@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = (time.monotonic() - start) * 1000
    metrics_collector.record_request(
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response
```

---

## 4. 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `app/main.py` | CORS 수정, lifespan 교체, 메트릭 미들웨어 추가 |
| `app/avm/engine.py` | 가중 단가 추정, 신뢰도 개선, auction_stats 수정 |
| `app/api/routes.py` | `AVMResponse`에 `unit_price_per_sqm` 추가 |
| `app/api/routes_export.py` | 잘못된 필드 참조 전면 수정, 포맷 단순화 |
| `app/db/database.py` | 하드코딩 경로 → 환경변수 기본값 수정 |
| `app/models/report_models.py` | 독립 Base → 공유 Base 통합 |
| `requirements.txt` | 미사용 패키지 제거 |
| `.env` / `.env.example` | Windows 경로, 불필요 키 제거 |
| `npl_avm/.gitignore` | DB/모델 바이너리, .env 제외 규칙 추가 |

| 파일 | 작업 |
|------|------|
| `app/avm/engine_optimized.py` | 삭제 (dead code + 런타임 크래시) |
| `app/api/monitoring_routes.py` | 삭제 (중복) |
| `app/utils/cache_manager.py` | 삭제 (dead code + 임포트 사이드이펙트) |
| `app/utils/query_optimizer.py` | 삭제 (dead code) |
| 루트 `*.md` 140개 | 삭제 |
| `results/*.md` 9개 | 삭제 |
| `execution_logs/*.md` 2개 | 삭제 |
| `backups/`, `__pycache__/` 등 | 삭제 |

---

## 5. 향후 권고사항

### 단기 (1~2주)
- **ML 모델 통합**: `final_calibrated_pipeline.pkl` (MAPE 15%)의 feature engineering 파이프라인을 API 입력값에 맞게 재구성 후 연결 고려
- **테스트 코드**: `tests/test_phase3_comprehensive.py` 외 핵심 API 엔드포인트 단위테스트 추가
- **alembic 마이그레이션**: 현재 `init_db()`로 테이블 생성 — alembic으로 스키마 버전 관리

### 중기 (1~2개월)
- **PostgreSQL 이관**: `psycopg2` 재추가, alembic 마이그레이션으로 전환
- **K8s/Prometheus**: SQLite → PostgreSQL 전환 후 의미 있음
- **인증**: 현재 API 인증 없음 — 내부망이 아니라면 API Key 또는 JWT 추가 필요

---

*작성: Claude Code (claude-sonnet-4-6)*
