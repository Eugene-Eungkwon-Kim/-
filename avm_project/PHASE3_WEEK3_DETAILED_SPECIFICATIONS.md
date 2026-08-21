# Phase 3 Week 3: 데이터베이스 로드 & 모델 재학습 & 클라우드 배포

**상세 명세서**

---

## 📋 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | Phase 3 Week 3 상세 명세서 |
| **작성일** | 2026-06-23 |
| **Phase** | Phase 3 (클라우드 배포 준비) |
| **Week** | Week 3 |
| **총 소요 시간** | 7-9일 |
| **총 예산** | 약 $2,000-3,000 (클라우드) |
| **상태** | 📋 준비 완료 |

---

## 🎯 Phase 3 Week 3 목표

### Primary Objectives
1. ✅ 마스터 데이터셋을 프로덕션 데이터베이스에 로드
2. ✅ 7개 ML 모델을 마스터 데이터셋으로 재학습
3. ✅ 재학습 모델 성능 검증 (R² > 0.85)
4. ✅ 클라우드 환경 선택 및 구성
5. ✅ AVM 대시보드를 클라우드에 배포
6. ✅ 프로덕션 환경 모니터링 설정

### Success Criteria
- 데이터베이스: 모든 데이터 성공적으로 로드, 0 오류
- 모델: R² score ≥ 0.85 (모든 7개 모델)
- 배포: 클라우드 환경 정상 작동, 99.5% 가용성
- 성능: API 응답 시간 < 50ms, 오류율 < 0.1%

---

## 📊 작업 구성

### 3가지 주요 트랙 (Parallel Execution)

```
┌─────────────────────────────────────────────────────────────┐
│  Track A: 데이터베이스 로드 (1-2일)                        │
├─────────────────────────────────────────────────────────────┤
│  • PostgreSQL/MySQL 데이터베이스 설정
│  • 마스터 데이터셋 로드
│  • 데이터 검증 및 인덱스 생성
│  • 백업 및 복구 테스트
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Track B: 모델 재학습 (2-3일)                              │
├─────────────────────────────────────────────────────────────┤
│  • 7개 모델 재학습 실행
│  • 하이퍼파라미터 최적화
│  • 성능 평가 및 검증
│  • 모델 아티팩트 저장
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Track C: 클라우드 배포 (2-4일)                            │
├─────────────────────────────────────────────────────────────┤
│  • 클라우드 제공자 선택
│  • 인프라 구성 (VPC, 보안 그룹 등)
│  • Docker 이미지 빌드 및 레지스트리 푸시
│  • 컨테이너 오케스트레이션
│  • 모니터링 및 알림 설정
└─────────────────────────────────────────────────────────────┘
```

---

## 📌 Track A: 데이터베이스 로드

### A.1 데이터베이스 환경 설정

#### A.1.1 데이터베이스 선택 및 설정

**요구사항:**
```
선택지:
  Option 1: PostgreSQL 14+ (권장)
    - 오픈소스
    - 확장성 우수
    - JSON 지원
    
  Option 2: MySQL 8.0+
    - 높은 성능
    - 보안 기능
    
  Option 3: Cloud SQL (Google/AWS)
    - 관리형 서비스
    - 자동 백업
```

**설정 사항:**
- 데이터베이스 인스턴스 생성
- 최소 사양: 2vCPU, 8GB RAM, 50GB SSD
- 백업 정책: 일일 자동 백업, 7일 보존
- 보안: SSL/TLS 암호화, 방화벽 설정

**예상 시간:** 2-4시간

#### A.1.2 연결 및 인증 설정

**작업 내용:**
```bash
# 데이터베이스 사용자 생성
CREATE USER avm_user WITH PASSWORD 'secure_password';
CREATE DATABASE avm_production;
GRANT ALL PRIVILEGES ON DATABASE avm_production TO avm_user;

# 연결 테스트
psql -h database_host -U avm_user -d avm_production
```

**구성 파일 준비:**
- `config/db_config.json` 생성
- 환경 변수 설정: `DB_URL`, `DB_USER`, `DB_PASSWORD`
- 시크릿 매니저 등록

**예상 시간:** 1-2시간

---

### A.2 마스터 데이터셋 로드

#### A.2.1 스키마 생성

**테이블 정의:**

```sql
-- 부동산 마스터 테이블
CREATE TABLE master_real_estate (
    id SERIAL PRIMARY KEY,
    
    -- 기본 정보
    property_id VARCHAR(50) UNIQUE NOT NULL,
    property_type VARCHAR(50),
    region VARCHAR(100),
    district VARCHAR(100),
    
    -- 물리적 특성
    area_sqm DECIMAL(10, 2),
    year_built INTEGER,
    rooms INTEGER,
    bathrooms INTEGER,
    parking INTEGER,
    floor INTEGER,
    total_floor INTEGER,
    condition INTEGER,
    
    -- 가격 정보
    appraised_price DECIMAL(15, 2),
    original_price DECIMAL(15, 2),
    market_price DECIMAL(15, 2),
    outstanding_debt DECIMAL(15, 2),
    price_per_sqm DECIMAL(10, 2),
    price_variance DECIMAL(5, 2),
    
    -- 대출 정보
    loan_term_months INTEGER,
    ltv DECIMAL(3, 2),
    interest_rate DECIMAL(5, 3),
    debt_to_price_ratio DECIMAL(3, 2),
    
    -- 시장 정보
    transaction_count_1y INTEGER,
    days_on_market INTEGER,
    market_trend DECIMAL(5, 2),
    appraisal_rounds INTEGER,
    age_years INTEGER,
    
    -- 관리 정보
    data_source VARCHAR(50),
    integration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 인덱스
    INDEX idx_property_type (property_type),
    INDEX idx_region (region),
    INDEX idx_year_built (year_built),
    INDEX idx_price (market_price),
    INDEX idx_created_at (created_at)
);

-- NPL 마스터 테이블
CREATE TABLE master_npl (
    id SERIAL PRIMARY KEY,
    
    -- 기본 정보
    property_id VARCHAR(50) UNIQUE NOT NULL,
    property_type VARCHAR(50),
    region VARCHAR(100),
    district VARCHAR(100),
    
    -- NPL 상태
    npl_stage VARCHAR(50),
    loan_status VARCHAR(50),
    default_date DATE,
    days_delinquent INTEGER,
    
    -- 부동산 정보
    area_sqm DECIMAL(10, 2),
    year_built INTEGER,
    condition INTEGER,
    
    -- 금융 정보
    original_loan_amount DECIMAL(15, 2),
    current_outstanding DECIMAL(15, 2),
    estimated_market_value DECIMAL(15, 2),
    recovery_rate DECIMAL(5, 2),
    
    -- 거래 이력
    price_history JSON,
    transaction_history JSON,
    
    -- 관리 정보
    data_source VARCHAR(50),
    integration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_npl_stage (npl_stage),
    INDEX idx_region (region),
    INDEX idx_default_date (default_date)
);
```

**예상 시간:** 2-3시간

#### A.2.2 데이터 로드

**로드 방법:**

```bash
# Python을 이용한 로드
python scripts/load_to_database.py \
  --input output/master_real_estate_20260623_084912.csv \
  --table master_real_estate \
  --batch_size 1000 \
  --verify
```

**SQL 직접 로드:**

```sql
-- CSV 파일로부터 직접 로드
COPY master_real_estate FROM '/path/to/master_real_estate_20260623_084912.csv'
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

COPY master_npl FROM '/path/to/master_npl_20260623_084912.csv'
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
```

**검증:**

```sql
-- 로드 확인
SELECT COUNT(*) as real_estate_count FROM master_real_estate;  -- Expected: 13,000
SELECT COUNT(*) as npl_count FROM master_npl;                  -- Expected: 500

-- 데이터 품질 확인
SELECT 
  COUNT(*) as total_rows,
  COUNT(DISTINCT property_id) as unique_properties,
  MIN(market_price) as min_price,
  MAX(market_price) as max_price,
  AVG(market_price) as avg_price
FROM master_real_estate;
```

**예상 시간:** 2-4시간

#### A.2.3 성능 최적화

**인덱스 생성:**

```sql
-- 자주 사용되는 칼럼 인덱스
CREATE INDEX idx_region_property_type ON master_real_estate(region, property_type);
CREATE INDEX idx_price_range ON master_real_estate(market_price);
CREATE INDEX idx_year_built_condition ON master_real_estate(year_built, condition);

-- 복합 인덱스 (검색 최적화)
CREATE INDEX idx_search ON master_real_estate(region, year_built, area_sqm);
```

**통계 분석:**

```sql
-- 테이블 통계 업데이트
ANALYZE master_real_estate;
ANALYZE master_npl;

-- 쿼리 플랜 확인
EXPLAIN ANALYZE SELECT * FROM master_real_estate WHERE region = 'Seoul';
```

**예상 시간:** 1-2시간

#### A.2.4 백업 및 복구 테스트

**백업 생성:**

```bash
# 전체 데이터베이스 백업
pg_dump -h localhost -U avm_user avm_production \
  | gzip > backup_20260623.sql.gz

# 특정 테이블만 백업
pg_dump -h localhost -U avm_user -t master_real_estate avm_production \
  > backup_real_estate.sql
```

**복구 테스트:**

```bash
# 복구 테스트 (별도 테스트 DB)
createdb avm_test
gunzip -c backup_20260623.sql.gz | psql -U avm_user avm_test

# 복구된 데이터 검증
psql -U avm_user avm_test -c "SELECT COUNT(*) FROM master_real_estate;"
```

**예상 시간:** 1-2시간

---

## 📌 Track B: 모델 재학습

### B.1 재학습 환경 준비

#### B.1.1 데이터 로드 및 전처리

**작업 내용:**

```python
# 1. 데이터베이스에서 데이터 로드
df_real_estate = pd.read_sql(
    "SELECT * FROM master_real_estate",
    connection_string
)

# 2. 데이터 전처리
from scripts.data_preprocessing import DataPreprocessor

preprocessor = DataPreprocessor()
df_processed = preprocessor.load_data_from_db(connection_string)
df_processed = preprocessor.explore_data(df_processed)
df_processed = preprocessor.handle_missing_values(df_processed)
df_processed = preprocessor.detect_outliers(df_processed)
df_processed = preprocessor.normalize_data(df_processed)
df_processed = preprocessor.feature_engineering(df_processed)

# 3. 전처리 결과 저장
preprocessor.save_processed_data(df_processed, 
    'output/processed_master_real_estate_20260623.csv')
```

**검증:**
- 데이터 형태: (13,000, 30+) 확인
- 결측치: 0 확인
- 이상치: 문서화
- 통계: 분포 확인

**예상 시간:** 2-4시간

#### B.1.2 데이터 분할

**Train/Validation/Test 분할:**

```python
from sklearn.model_selection import train_test_split

# 70% 학습, 15% 검증, 15% 테스트
train, temp = train_test_split(df_processed, test_size=0.3, random_state=42)
val, test = train_test_split(temp, test_size=0.5, random_state=42)

print(f"Train: {len(train)} ({len(train)/len(df_processed)*100:.1f}%)")
print(f"Val: {len(val)} ({len(val)/len(df_processed)*100:.1f}%)")
print(f"Test: {len(test)} ({len(test)/len(df_processed)*100:.1f}%)")

# 저장
train.to_csv('data/train_set_20260623.csv', index=False)
val.to_csv('data/val_set_20260623.csv', index=False)
test.to_csv('data/test_set_20260623.csv', index=False)
```

**예상 시간:** 30분

---

### B.2 모델 재학습

#### B.2.1 학습 구성

**7개 모델 재학습:**

| # | 모델 | 학습 시간 | 예상 R² |
|---|------|---------|--------|
| 1 | Linear Regression | 10초 | 0.75 |
| 2 | Decision Tree | 1분 | 0.78 |
| 3 | Random Forest | 5분 | 0.82 |
| 4 | Gradient Boosting | 8분 | 0.84 |
| 5 | XGBoost | 10분 | 0.86 |
| 6 | LightGBM | 8분 | 0.87 |
| 7 | Ensemble | 5분 | 0.88 |
| | **총 합계** | **37분** | - |

#### B.2.2 학습 스크립트

```python
#!/usr/bin/env python3
"""
모델 재학습 스크립트
"""

from scripts.model_development import AVMModelDeveloper
import pandas as pd
from datetime import datetime

# 데이터 로드
train = pd.read_csv('data/train_set_20260623.csv')
val = pd.read_csv('data/val_set_20260623.csv')
test = pd.read_csv('data/test_set_20260623.csv')

# 모델 개발자 초기화
developer = AVMModelDeveloper(
    output_dir='models/retrained_20260623',
    random_state=42
)

# 모델 목록
models_to_train = [
    'linear_regression',
    'decision_tree',
    'random_forest',
    'gradient_boosting',
    'xgboost',
    'lightgbm',
    'ensemble'
]

print("=" * 80)
print("🚀 모델 재학습 시작")
print("=" * 80)
print(f"시작 시간: {datetime.now().isoformat()}")
print(f"학습 데이터: {len(train)} 샘플")
print(f"검증 데이터: {len(val)} 샘플")
print(f"테스트 데이터: {len(test)} 샘플")
print()

results = {}

for model_name in models_to_train:
    print(f"\n🔄 학습 중: {model_name}")
    print("-" * 80)
    
    try:
        # 모델 학습
        model = developer.train_model(
            model_name=model_name,
            train_data=train,
            val_data=val,
            hyperparameter_tuning=True,
            n_trials=20
        )
        
        # 모델 평가
        eval_results = developer.evaluate_model(
            model=model,
            test_data=test
        )
        
        results[model_name] = {
            'status': 'SUCCESS',
            'r2_score': eval_results['r2_score'],
            'rmse': eval_results['rmse'],
            'mae': eval_results['mae'],
            'mape': eval_results['mape']
        }
        
        print(f"✅ {model_name}")
        print(f"   R² Score: {eval_results['r2_score']:.4f}")
        print(f"   RMSE: {eval_results['rmse']:.2f}")
        print(f"   MAE: {eval_results['mae']:.2f}")
        
        # 모델 저장
        developer.save_model(
            model=model,
            model_name=model_name,
            version='20260623'
        )
        
    except Exception as e:
        results[model_name] = {
            'status': 'FAILED',
            'error': str(e)
        }
        print(f"❌ {model_name}: {str(e)}")

# 결과 요약
print("\n" + "=" * 80)
print("📊 재학습 결과 요약")
print("=" * 80)

success_count = sum(1 for r in results.values() if r['status'] == 'SUCCESS')
print(f"\n✅ 성공: {success_count}/{len(results)}")

for model_name, result in results.items():
    if result['status'] == 'SUCCESS':
        print(f"\n{model_name}:")
        print(f"  R² Score: {result['r2_score']:.4f} " 
              f"({'✅ PASS' if result['r2_score'] >= 0.85 else '⚠️ CHECK'})")
        print(f"  RMSE: {result['rmse']:.2f}")
        print(f"  MAE: {result['mae']:.2f}")
    else:
        print(f"\n{model_name}: ❌ {result['error']}")

print(f"\n완료 시간: {datetime.now().isoformat()}")
print("=" * 80)
```

**예상 시간:** 45분 ~ 1시간

#### B.2.3 성능 평가

**평가 지표:**

```
모델 성능 평가:

1. R² Score (결정 계수)
   - 범위: 0 ~ 1
   - 기준: ≥ 0.85
   - 의미: 예측 변동성의 85% 이상 설명

2. RMSE (평균 제곱근 오차)
   - 범위: 0 ~ ∞
   - 낮을수록 좋음
   - 의미: 평균 예측 오차

3. MAE (평균 절대 오차)
   - 범위: 0 ~ ∞
   - 낮을수록 좋음
   - 의미: 평균 절대 예측 오차

4. MAPE (평균 절대 백분율 오차)
   - 범위: 0% ~ ∞%
   - 기준: < 10%
   - 의미: 평균 오류율

5. Cross-Validation Score
   - 기준: Mean CV Score ≥ 0.83
   - 의미: 모델 안정성
```

**재학습 목표:**

| 모델 | 이전 R² | 목표 R² | 개선율 |
|------|--------|--------|--------|
| Linear Regression | 0.72 | 0.75 | +4% |
| Decision Tree | 0.76 | 0.78 | +3% |
| Random Forest | 0.81 | 0.82 | +1% |
| Gradient Boosting | 0.83 | 0.84 | +1% |
| XGBoost | 0.85 | 0.86 | +1% |
| LightGBM | 0.86 | 0.87 | +1% |
| Ensemble | 0.87 | 0.88 | +1% |

**예상 시간:** 2-4시간

#### B.2.4 모델 검증 및 저장

**검증:**

```python
# 새 모델 vs 기존 모델 비교
comparison = compare_models(
    old_models_dir='models/production',
    new_models_dir='models/retrained_20260623',
    test_data=test
)

print("모델 성능 비교:")
print(comparison.to_string())

# 모든 새 모델이 기존 모델보다 성능 우수한지 확인
assert (comparison['new_r2'] > comparison['old_r2']).all(), \
    "새 모델 성능이 기존 모델보다 낮습니다"
```

**저장:**

```bash
# 재학습된 모델 저장
mv models/retrained_20260623/* models/production/

# 버전 관리
git add models/production/
git commit -m "Update ML models with master dataset training

- All 7 models retrained with master_real_estate dataset
- R² scores improved across all models
- Ensemble model: R² = 0.88
- Models saved with timestamp 20260623"
```

**예상 시간:** 1-2시간

---

## 📌 Track C: 클라우드 배포

### C.1 클라우드 제공자 선택 및 환경 구성

#### C.1.1 클라우드 제공자 선택

**선택지 분석:**

```
Option 1: Google Cloud Run (권장) ⭐
  ✅ 장점:
     - 서버리스 (비용 효율적)
     - 자동 스케일링
     - 빠른 배포
     - Firebase 통합
  
  ❌ 단점:
     - 콜드 스타트 시간 (3-5초)
  
  💰 예상 비용: $100-200/월
  
  🎯 권장: 중소 규모 프로젝트

Option 2: AWS ECS on Fargate
  ✅ 장점:
     - 관리형 컨테이너 서비스
     - 탄력적 스케일링
     - 높은 성능
  
  ❌ 단점:
     - 설정 복잡도
  
  💰 예상 비용: $200-400/월
  
  🎯 권장: 대규모 프로젝트

Option 3: Kubernetes (GKE/EKS)
  ✅ 장점:
     - 높은 제어 능력
     - 복잡한 오케스트레이션
     - 멀티 리전 배포
  
  ❌ 단점:
     - 운영 복잡도 높음
  
  💰 예상 비용: $300-500/월
  
  🎯 권장: 엔터프라이즈급
```

**권장: Google Cloud Run**

#### C.1.2 클라우드 계정 및 프로젝트 설정

**Google Cloud 설정:**

```bash
# 1. gcloud CLI 설치
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# 2. 프로젝트 생성
gcloud projects create avm-dashboard-prod --name "AVM Dashboard Production"

# 3. 프로젝트 설정
PROJECT_ID="avm-dashboard-prod"
gcloud config set project $PROJECT_ID

# 4. 필요한 API 활성화
gcloud services enable \
  run.googleapis.com \
  compute.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  sql-component.googleapis.com \
  cloudkms.googleapis.com

# 5. 서비스 계정 생성
gcloud iam service-accounts create avm-dashboard-sa \
  --display-name="AVM Dashboard Service Account"

# 6. 권한 할당
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:avm-dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

**예상 시간:** 30분 ~ 1시간

#### C.1.3 데이터베이스 클라우드 마이그레이션

**옵션:**

```
Option A: Cloud SQL (권장)
  - 관리형 PostgreSQL/MySQL
  - 자동 백업
  - 보안 기능 내장
  
Option B: 로컬 데이터베이스 유지
  - 비용 절감
  - 낮은 레이턴시
  - 수동 관리
```

**Cloud SQL 설정 (선택 시):**

```bash
# Cloud SQL 인스턴스 생성
gcloud sql instances create avm-database \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=asia-northeast1 \
  --backup-start-time=03:00 \
  --enable-bin-log

# 데이터베이스 생성
gcloud sql databases create avm_production \
  --instance=avm-database

# 사용자 생성
gcloud sql users create avm_user \
  --instance=avm-database \
  --password=secure_password

# 데이터 마이그레이션
gcloud sql import sql avm-database \
  gs://my-bucket/backup.sql \
  --database=avm_production
```

**예상 시간:** 2-4시간

---

### C.2 Docker 컨테이너화

#### C.2.1 Dockerfile 최적화

**현재 Dockerfile 검토:**

```dockerfile
# 멀티스테이지 빌드 구성 확인
FROM python:3.11-slim AS builder

# 1. 백엔드 의존성 설치
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Node.js 설치 (프론트엔드)
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# 3. 최종 이미지
FROM python:3.11-slim

WORKDIR /app

# 의존성 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 빌드된 프론트엔드 복사
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# 애플리케이션 코드 복사
COPY backend/ ./backend/
COPY config/ ./config/
COPY scripts/ ./scripts/

# 포트 노출
EXPOSE 8000 3000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 시작 스크립트
CMD ["python", "backend/main.py"]
```

**최적화 사항:**
- 멀티스테이지 빌드 (이미지 크기 감소)
- 캐시 레이어 최적화
- 헬스체크 추가
- 불필요한 파일 제외 (.dockerignore)

**예상 시간:** 1-2시간

#### C.2.2 .dockerignore 파일 생성

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
.npm
npm-debug.log

# 개발 환경
.git/
.gitignore
.env.local
.env.*.local
.vscode/
.idea/
*.swp
*.swo

# 테스트
.pytest_cache/
.coverage
htmlcov/

# 시스템
.DS_Store
.DS_Store?
._*
.Spotlight-V100

# 임시 파일
*.tmp
*.log
temp/
tmp/

# 문서
docs/
*.md
README.md
LICENSE

# 데이터
data/raw/
data/sample/
*.csv
```

**예상 시간:** 30분

#### C.2.3 Docker 이미지 빌드 및 테스트

```bash
# 1. 이미지 빌드
docker build -t avm-dashboard:latest -t avm-dashboard:v2.0 .

# 2. 이미지 검증
docker inspect avm-dashboard:v2.0

# 3. 로컬 테스트
docker run -p 8000:8000 -p 3000:3000 \
  -e FASTAPI_ENV=production \
  -e DB_URL="postgresql://localhost/avm_production" \
  avm-dashboard:v2.0

# 4. 헬스체크
curl http://localhost:8000/health
curl http://localhost:3000

# 5. 이미지 크기 확인
docker images avm-dashboard:v2.0
# 예상: 800-1200 MB (최적화 후)
```

**예상 시간:** 30분 ~ 1시간

---

### C.3 컨테이너 레지스트리에 푸시

#### C.3.1 Google Container Registry (GCR) 설정

```bash
# 1. 컨테이너 레지스트리 인증
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# 2. 이미지 태그 설정
docker tag avm-dashboard:v2.0 \
  asia-northeast1-docker.pkg.dev/avm-dashboard-prod/avm-dashboard/app:v2.0

docker tag avm-dashboard:v2.0 \
  asia-northeast1-docker.pkg.dev/avm-dashboard-prod/avm-dashboard/app:latest

# 3. 이미지 푸시
docker push asia-northeast1-docker.pkg.dev/avm-dashboard-prod/avm-dashboard/app:v2.0
docker push asia-northeast1-docker.pkg.dev/avm-dashboard-prod/avm-dashboard/app:latest

# 4. 푸시 확인
gcloud container images list
```

**예상 시간:** 5-15분 (네트워크 속도에 따라)

---

### C.4 클라우드 배포

#### C.4.1 Google Cloud Run 배포

```bash
# 환경 변수 설정
export PROJECT_ID="avm-dashboard-prod"
export REGION="asia-northeast1"
export SERVICE_NAME="avm-dashboard"
export IMAGE_URL="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/avm-dashboard/app:v2.0"

# Cloud Run 배포
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_URL \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --concurrency=50 \
  --max-instances=10 \
  --min-instances=1 \
  --set-env-vars="\
    FASTAPI_ENV=production,\
    DB_URL=$DB_URL,\
    DB_USER=$DB_USER,\
    DB_PASSWORD=$DB_PASSWORD,\
    SECRET_KEY=$SECRET_KEY,\
    CORS_ORIGINS=https://avm-dashboard.example.com,\
    MONITORING_ENABLED=true" \
  --service-account=avm-dashboard-sa@${PROJECT_ID}.iam.gserviceaccount.com

# 배포 상태 확인
gcloud run services describe $SERVICE_NAME --region=$REGION
```

**배포 옵션:**
- Memory: 2GB (권장)
- CPU: 2개 (권장)
- 동시 요청: 50개
- 최대 인스턴스: 10개
- 최소 인스턴스: 1개 (콜드 스타트 방지)

**예상 시간:** 10-15분

#### C.4.2 커스텀 도메인 설정 (선택)

```bash
# Cloud Run 서비스에 커스텀 도메인 매핑
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=avm-dashboard.example.com \
  --region=$REGION

# DNS 레코드 업데이트 (DNS 제공자에서)
# CNAME: avm-dashboard.example.com → (Cloud Run URL)
```

**예상 시간:** 30분 (DNS 전파 포함)

---

### C.5 배포 후 검증

#### C.5.1 헬스체크

```bash
# 1. API 헬스체크
curl https://avm-dashboard-${PROJECT_ID}.run.app/health

# 2. API 문서
curl https://avm-dashboard-${PROJECT_ID}.run.app/docs

# 3. 대시보드 로드
curl https://avm-dashboard-${PROJECT_ID}.run.app/

# 4. 모델 정보 확인
curl https://avm-dashboard-${PROJECT_ID}.run.app/models

# 예상 응답:
# {
#   "status": "healthy",
#   "timestamp": "2026-06-23T...",
#   "version": "2.0.0",
#   "models": 7,
#   "models_ready": true
# }
```

**예상 시간:** 10분

#### C.5.2 성능 테스트

```bash
# 부하 테스트
ab -n 100 -c 10 https://avm-dashboard-${PROJECT_ID}.run.app/health

# 결과 확인 항목:
# - 평균 응답 시간 < 50ms
# - 성공률 100%
# - 에러율 0%

# 모델 예측 테스트
curl -X POST https://avm-dashboard-${PROJECT_ID}.run.app/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "area_sqm": 150,
    "year_built": 2005,
    "rooms": 3,
    "bathrooms": 2,
    ...
  }'
```

**예상 시간:** 20분

#### C.5.3 모니터링 설정

```bash
# Cloud Logging 활성화
gcloud logging sinks create avm-logs \
  logging.googleapis.com/projects/avm-dashboard-prod/logs/avm-dashboard \
  --log-filter='resource.type="cloud_run_revision"'

# Cloud Monitoring 대시보드 생성
gcloud monitoring dashboards create --config-from-file=dashboard.yaml

# 알림 정책 설정
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="AVM Dashboard Alerts" \
  --condition-display-name="High Error Rate" \
  --condition-threshold-value=0.01
```

**예상 시간:** 1-2시간

---

## 📊 타임라인 및 의존성

### 작업 흐름도

```
Day 1-2: Track A (데이터베이스 로드)
  A.1 환경 설정 (2-4h)
  │
  └─→ A.2 데이터 로드 (2-4h)
       │
       └─→ A.3 성능 최적화 (1-2h)
            │
            └─→ A.4 백업 테스트 (1-2h) ✅

Day 2-3: Track B (모델 재학습) [A.4 후 시작]
  B.1 환경 준비 (2-4h)
  │
  ├─→ B.2 재학습 (45m - 1h)
  │
  ├─→ B.3 성능 평가 (2-4h)
  │
  └─→ B.4 모델 저장 (1-2h) ✅

Day 3-4: Track C (클라우드 배포) [B.4 후 시작]
  C.1 클라우드 환경 (2-4h)
  │
  ├─→ C.2 Docker 컨테이너 (1-2h)
  │
  ├─→ C.3 레지스트리 푸시 (5-15m)
  │
  ├─→ C.4 클라우드 배포 (10-15m)
  │
  └─→ C.5 배포 후 검증 (20m) ✅
```

### 병렬 처리 전략

**권장 실행 계획:**

1. **Day 1-2**: Track A 실행 (Database Setup)
2. **Day 2-3**: Track B 실행 (Model Retraining)
   - A.4 완료 후 시작 가능
   - 필수 의존성: A.2 (데이터 로드)
3. **Day 3-4**: Track C 실행 (Cloud Deployment)
   - B.4 완료 후 시작 가능
   - Track A/B와 독립적

---

## 💰 비용 추정

### 인프라 비용 (월별)

```
Google Cloud Run:
  ├─ CPU: $0.00002400/vCPU-second
  ├─ Memory: $0.00000250/GB-second
  ├─ 요청: $0.40/100만 요청
  └─ 월 예상: $100-200

Cloud SQL:
  ├─ db-f1-micro: $9/월
  ├─ 스토리지 10GB: $1.70/월
  ├─ 백업: 포함
  └─ 월 예상: $50-80

Cloud Storage (백업):
  ├─ 스토리지: $0.02/GB-월
  ├─ 예상 크기: 50GB
  └─ 월 예상: $1-2

합계: $150-280/월 (소규모 운영 기준)
```

### 개발 비용 (일회성)

```
인력 (3명, 10일):
  ├─ 데이터베이스 엔지니어: $200/일
  ├─ ML 엔지니어: $250/일
  ├─ DevOps 엔지니어: $200/일
  └─ 합계: $15,000

도구 및 서비스:
  ├─ 클라우드 초기화: 무료
  ├─ 모니터링: $100
  └─ 합계: $100

전체 개발 비용: $15,100
```

---

## ✅ 최종 체크리스트

### Phase 3 Week 3 완료 기준

#### Database Track (Track A)
- [ ] PostgreSQL/MySQL 데이터베이스 설정
- [ ] 마스터 데이터셋 로드 (13,500 행)
- [ ] 데이터 검증 완료 (0 오류)
- [ ] 인덱스 생성 및 최적화
- [ ] 백업 및 복구 테스트 통과

#### Model Retraining Track (Track B)
- [ ] 7개 모델 재학습 완료
- [ ] 모든 모델 R² ≥ 0.85 달성
- [ ] 성능 개선 확인
- [ ] 모델 아티팩트 저장
- [ ] Git에 커밋

#### Cloud Deployment Track (Track C)
- [ ] 클라우드 제공자 선택 및 계정 설정
- [ ] Docker 이미지 빌드 및 테스트
- [ ] 컨테이너 레지스트리에 푸시
- [ ] Cloud Run/ECS 배포 완료
- [ ] 헬스체크 통과
- [ ] 성능 테스트 통과 (< 50ms)
- [ ] 모니터링 및 알림 설정

#### Final Verification
- [ ] 모든 3개 Track 완료
- [ ] 대시보드 정상 작동
- [ ] API 모든 엔드포인트 정상
- [ ] WebSocket 연결 안정
- [ ] 프로덕션 모니터링 활성화
- [ ] 백업 및 복구 계획 수립

---

## 📞 연락처 및 지원

### 담당팀
- **Database Team**: 데이터베이스 로드 및 관리
- **ML Team**: 모델 재학습 및 성능 평가
- **DevOps/Cloud Team**: 클라우드 배포 및 운영

### 에스컬레이션
- Level 1: 팀 내 기술 리드
- Level 2: 프로젝트 매니저
- Level 3: CTO/기술 이사

---

**문서 작성일:** 2026-06-23  
**최종 검토:** Phase 3 Week 2 완료  
**상태:** ✅ 실행 준비 완료

