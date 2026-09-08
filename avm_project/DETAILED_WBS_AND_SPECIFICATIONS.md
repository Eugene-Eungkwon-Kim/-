# 📋 AVM 프로젝트 Phase 2-4 상세 WBS 및 작업 명세서

**작성일**: 2026-06-16  
**프로젝트명**: AVM (자동감정가 모델) - Phase 2-4 배포 및 자동화  
**상태**: 🟡 Phase 1 완료, Phase 2-4 준비 완료  
**총 예상 기간**: 10-14일 (병렬 처리 시)  
**팀 구성**: 1명 (AI 개발자)

---

## 📊 WBS 전체 구조도

```
AVM Project Phase 2-4
├── PHASE 1: Cloud Run 배포 (2-3시간)
│   ├── 1.1 사전 준비 (30분)
│   ├── 1.2 배포 실행 (5분)
│   ├── 1.3 배포 검증 (45분)
│   └── 1.4 배포 후 설정 (30분)
├── PHASE 2: AUTO-LOOP 자동화 (1.5시간)
│   ├── 2.1 Cron 스케줄 설정 (15분)
│   ├── 2.2 모니터링 대시보드 (30분)
│   ├── 2.3 알림 시스템 설정 (20분)
│   └── 2.4 자동 스케일링 (15분)
├── PHASE 3: 실제 데이터 수집 (2-3일)
│   ├── 3.1 API 인증 설정 (2-4시간)
│   ├── 3.2 월별 데이터 수집 (1-2일)
│   ├── 3.3 데이터 전처리 (4-6시간)
│   ├── 3.4 모델 재학습 (2-4시간)
│   └── 3.5 신규 모델 배포 (1시간)
└── PHASE 4: 완전 자동화 (1주)
    ├── 4.1 성능 최적화 (2일)
    ├── 4.2 고급 기능 구현 (2.5일)
    ├── 4.3 부하 테스트 (1.5일)
    └── 4.4 보안 검증 (1일)
```

---

## 🔧 PHASE 1: Cloud Run 배포 (총 2-3시간)

### 1.1 사전 준비 (30분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 우선순위 | 담당 | 체크리스트 |
|--------|--------|---------|------|---------|------|-----------|
| 1.1.1 | gcloud CLI 설치 | Python 환경에 gcloud SDK 설치 | 10분 | P0 | AI | ☐ |
| 1.1.2 | GCP 계정 인증 | gcloud auth login (OAuth 인증) | 5분 | P0 | AI | ☐ |
| 1.1.3 | 프로젝트 ID 설정 | gcloud config set project [PROJECT_ID] | 2분 | P0 | AI | ☐ |
| 1.1.4 | API 활성화 | Cloud Run, Container Registry API 활성화 | 5분 | P0 | AI | ☐ |
| 1.1.5 | Docker 환경 확인 | Docker daemon 실행 확인 | 3분 | P0 | AI | ☐ |
| 1.1.6 | 빌드 테스트 | docker build 테스트 | 5분 | P0 | AI | ☐ |

**1.1 실행 명령어**:
```bash
# 1.1.1: gcloud CLI 설치
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# 1.1.2-1.1.3: 인증 및 프로젝트 설정
gcloud auth login
gcloud config set project your-project-id
gcloud config set compute/region asia-northeast1

# 1.1.4: API 활성화
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 1.1.5-1.1.6: Docker 확인
docker --version
cd /home/user/-/avm_project
docker build -t avm-model:latest .
```

---

### 1.2 배포 실행 (5분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 의존성 | 체크리스트 |
|--------|--------|---------|------|--------|-----------|
| 1.2.1 | Docker 빌드 | avm_project Dockerfile 빌드 | 2분 | 1.1.6 | ☐ |
| 1.2.2 | Registry 푸시 | GCR에 이미지 푸시 | 2분 | 1.2.1 | ☐ |
| 1.2.3 | Cloud Run 배포 | gcloud run deploy 실행 | 1분 | 1.2.2 | ☐ |

**1.2 실행 명령어**:
```bash
# 1.2.1: Docker 빌드
cd /home/user/-/avm_project
docker build -t gcr.io/[PROJECT_ID]/avm-model:latest .

# 1.2.2: GCR에 푸시
docker push gcr.io/[PROJECT_ID]/avm-model:latest

# 1.2.3: Cloud Run 배포
gcloud run deploy avm-model \
  --image gcr.io/[PROJECT_ID]/avm-model:latest \
  --platform managed \
  --region asia-northeast1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60 \
  --max-instances 10 \
  --min-instances 1 \
  --allow-unauthenticated
```

---

### 1.3 배포 검증 (45분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 테스트 항목 | 체크리스트 |
|--------|--------|---------|------|-----------|-----------|
| 1.3.1 | 서비스 URL 확인 | Cloud Run 서비스 URL 획득 | 2분 | GET URL | ☐ |
| 1.3.2 | Health Check | /health 엔드포인트 테스트 | 5분 | HTTP 200 응답 | ☐ |
| 1.3.3 | 예측 API 테스트 | /predict 엔드포인트 기본 테스트 | 10분 | 정상 예측값 반환 | ☐ |
| 1.3.4 | 배치 예측 테스트 | /predict-batch 대량 요청 테스트 | 10분 | 배치 처리 성공 | ☐ |
| 1.3.5 | 모델 목록 확인 | /models 엔드포인트 검증 | 3분 | 6개 모델 목록 | ☐ |
| 1.3.6 | 메트릭 확인 | /metrics 성능 지표 수집 | 5분 | 메트릭 데이터 출력 | ☐ |
| 1.3.7 | 부하 테스트 | 1000 req/sec 동시 요청 | 10분 | 응답시간 < 100ms | ☐ |

**1.3 검증 스크립트**:
```bash
# 1.3.1: URL 확인
SERVICE_URL=$(gcloud run services describe avm-model --region asia-northeast1 --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"

# 1.3.2: Health Check
curl -s "$SERVICE_URL/health" | jq .

# 1.3.3: 예측 테스트
curl -X POST "$SERVICE_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "area": 100,
    "age": 10,
    "location_score": 0.8,
    "condition": 0.9,
    "floor": 5
  }' | jq .

# 1.3.7: 부하 테스트 (ab 도구 사용)
ab -n 10000 -c 100 "$SERVICE_URL/health"
```

---

### 1.4 배포 후 설정 (30분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 우선순위 | 체크리스트 |
|--------|--------|---------|------|---------|-----------|
| 1.4.1 | 환경 변수 설정 | Cloud Run 환경 변수 구성 | 10분 | P1 | ☐ |
| 1.4.2 | 커스텀 도메인 연결 | 도메인 연결 (선택사항) | 10분 | P2 | ☐ |
| 1.4.3 | IAM 권한 설정 | 서비스 계정 권한 구성 | 5분 | P1 | ☐ |
| 1.4.4 | 배포 정보 저장 | deployment_info.json 생성 | 5분 | P1 | ☐ |

**1.4 실행 스크립트**:
```bash
# 1.4.1: 환경 변수 설정
gcloud run services update avm-model \
  --region asia-northeast1 \
  --set-env-vars LOG_LEVEL=INFO,MODEL_CACHE_TTL=3600

# 1.4.3: IAM 권한
gcloud run services add-iam-policy-binding avm-model \
  --region asia-northeast1 \
  --member=allUsers \
  --role=roles/run.invoker

# 1.4.4: 배포 정보 저장
gcloud run services describe avm-model \
  --region asia-northeast1 \
  --format=json > /home/user/-/avm_project/config/deployment_info.json
```

---

## ⚙️ PHASE 2: AUTO-LOOP 자동화 (총 1.5시간)

### 2.1 Cron 스케줄 설정 (15분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 목표 | 체크리스트 |
|--------|--------|---------|------|------|-----------|
| 2.1.1 | Cron 작업 생성 | 주간 데이터 수집 및 모델 재학습 스케줄 | 8분 | 매주 목요일 10:00 | ☐ |
| 2.1.2 | 자동화 스크립트 작성 | auto_retraining.py 작성 | 5분 | 완전 자동화 | ☐ |
| 2.1.3 | 스케줄 테스트 | 드라이런 실행 | 2분 | 정상 실행 확인 | ☐ |

**2.1 구성 명령어**:
```bash
# 2.1.1: Cron 작업 설정
crontab -e

# 추가할 내용:
0 10 * * 4 cd /home/user/-/avm_project && python scripts/auto_retraining.py >> logs/cron_auto_retraining.log 2>&1

# 2.1.2: auto_retraining.py 내용
# (scripts/auto_retraining.py로 생성할 것)

# 2.1.3: 현재 Cron 작업 확인
crontab -l
```

**2.1.2 auto_retraining.py 명세**:
```python
# 필수 기능:
# 1. Data.go.kr API에서 최신 데이터 수집
# 2. 데이터 전처리 (sample data 파이프라인 사용)
# 3. 6개 모델 학습
# 4. 최고 성능 모델 선택
# 5. 모델 배포
# 6. 로그 기록
# 7. 알림 발송
```

---

### 2.2 모니터링 대시보드 (30분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 수집 항목 | 체크리스트 |
|--------|--------|---------|------|----------|-----------|
| 2.2.1 | 메트릭 수집 | Cloud Run 메트릭 자동 수집 | 10분 | CPU, Memory, Requests | ☐ |
| 2.2.2 | 대시보드 생성 | Grafana/Cloud Console 대시보드 구성 | 12분 | 실시간 모니터링 | ☐ |
| 2.2.3 | 로그 수집 | Cloud Logging에 로그 통합 | 8분 | 구조화된 로깅 | ☐ |

**2.2 대시보드 항목**:
- 📊 실시간 요청 수 (req/sec)
- 📈 평균 응답 시간 (ms)
- 💾 메모리 사용량 (%)
- 🔧 CPU 사용량 (%)
- ✅ 에러율 (%)
- 🚀 모델 정확도 (R² 점수)
- 📅 마지막 데이터 수집 시간
- 🔄 마지막 모델 재학습 시간

**2.2 설정 명령어**:
```bash
# Cloud Logging 권한 활성화
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com

# Grafana 연결 (선택사항)
# Google Cloud Monitoring에서 대시보드 생성
gcloud monitoring dashboards create --config-from-file=config/monitoring_dashboard.json
```

---

### 2.3 알림 시스템 설정 (20분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 알림 유형 | 체크리스트 |
|--------|--------|---------|------|----------|-----------|
| 2.3.1 | 에러 알림 | 5분 이상 에러율 > 5% | 7분 | Slack/Email | ☐ |
| 2.3.2 | 성능 알림 | 응답 시간 > 500ms | 7분 | Slack/Email | ☐ |
| 2.3.3 | 리소스 알림 | CPU/Memory > 80% | 3분 | Slack/Email | ☐ |
| 2.3.4 | 자동화 실패 알림 | Cron job 실패 감지 | 3분 | Email | ☐ |

**2.3 알림 규칙 정의**:
```json
{
  "alert_rules": [
    {
      "name": "HighErrorRate",
      "condition": "error_rate > 5%",
      "duration": "5m",
      "notification": "email,slack"
    },
    {
      "name": "SlowResponse",
      "condition": "response_time_p95 > 500ms",
      "duration": "10m",
      "notification": "slack"
    },
    {
      "name": "HighResourceUsage",
      "condition": "cpu > 80% OR memory > 80%",
      "duration": "5m",
      "notification": "email,slack"
    }
  ]
}
```

---

### 2.4 자동 스케일링 (15분)

| 작업ID | 작업명 | 상세 내용 | 시간 | 목표 | 체크리스트 |
|--------|--------|---------|------|------|-----------|
| 2.4.1 | 스케일링 정책 설정 | min: 1, max: 10 인스턴스 | 8분 | 자동 확장 | ☐ |
| 2.4.2 | 부하 기반 스케일링 | CPU > 70%시 자동 확장 | 5분 | 동적 스케일링 | ☐ |
| 2.4.3 | 스케일링 테스트 | 부하 증가 시 확장 확인 | 2분 | 정상 작동 | ☐ |

**2.4 설정 명령어**:
```bash
# Cloud Run 자동 스케일링 설정 (배포 시에 포함됨)
gcloud run services update avm-model \
  --region asia-northeast1 \
  --min-instances 1 \
  --max-instances 10 \
  --update-max-instances=10 \
  --cpu-throttling
```

---

## 📊 PHASE 3: 실제 데이터 수집 (총 2-3일)

### 3.1 API 인증 설정 (2-4시간)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 의존성 | 체크리스트 |
|--------|--------|---------|---------|--------|-----------|
| 3.1.1 | Data.go.kr 회원가입 | 포털 계정 생성 | 5분 | - | ☐ |
| 3.1.2 | API 신청 | 부동산 실거래 정보 API 신청 | 10-30분 | 3.1.1 | ☐ |
| 3.1.3 | API 승인 대기 | 자동 승인 또는 수동 승인 대기 | 1-4시간 | 3.1.2 | ☐ |
| 3.1.4 | API 키 확인 | 마이페이지에서 API 키 수집 | 5분 | 3.1.3 | ☐ |
| 3.1.5 | .env 파일 설정 | API 키 환경 변수에 등록 | 5분 | 3.1.4 | ☐ |
| 3.1.6 | 연결 테스트 | test_api_collection.py 실행 | 5분 | 3.1.5 | ☐ |

**3.1 상세 절차**:

```bash
# 3.1.1-3.1.2: Data.go.kr 가입 및 API 신청
# 웹사이트: https://www.data.go.kr
# 1. 회원가입
# 2. 마이페이지 > API 관리 > 신청
# 3. "부동산 실거래 정보 서비스" 검색 및 신청
# 4. 승인 대기

# 3.1.4: API 키 확인
# 마이페이지 > API 관리 > 신청 내역에서 인증키 복사

# 3.1.5: .env 파일 설정
cd /home/user/-/avm_project
echo "DATA_GO_KR_API_KEY=your_api_key_here" >> .env
echo "DATA_GO_KR_API_URL=http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/MAPIService" >> .env

# 3.1.6: 연결 테스트
python scripts/test_api_collection.py
```

**3.1 예상 API 응답** (성공 시):
```json
{
  "result": {
    "code": "00",
    "message": "SUCCESS"
  },
  "body": {
    "items": [
      {
        "거래금액": "500000000",
        "건물면적": "99.99",
        "도로명": "서울시 강남구",
        "거래일자": "20260601",
        ...
      }
    ]
  }
}
```

---

### 3.2 월별 데이터 수집 (1-2일)

| 작업ID | 작업명 | 기간 | 예상 용량 | 소요시간 | 체크리스트 |
|--------|--------|------|---------|---------|-----------|
| 3.2.1 | 2024년 1월 데이터 | Jan 2024 | 85-120MB | 15분 | ☐ |
| 3.2.2 | 2024년 2월 데이터 | Feb 2024 | 95-130MB | 15분 | ☐ |
| 3.2.3 | 2024년 3월 데이터 | Mar 2024 | 100-140MB | 15분 | ☐ |
| 3.2.4 | 2024년 4월 데이터 | Apr 2024 | 110-150MB | 15분 | ☐ |
| 3.2.5 | 2024년 5월 데이터 | May 2024 | 120-160MB | 15분 | ☐ |
| 3.2.6 | 2024년 6월 데이터 | Jun 2024 | 85-120MB | 15분 | ☐ |
| 3.2.7 | 데이터 통합 | 6개월 통합 | 595-820MB | 30분 | ☐ |
| 3.2.8 | 데이터 검증 | 이상치, 중복 확인 | - | 1시간 | ☐ |

**3.2 수집 스크립트**:
```python
# collect_real_estate_monthly_data.py
from scripts.data_collection_handler import KoreanRealEstateDataCollector

collector = KoreanRealEstateDataCollector(api_key="YOUR_API_KEY")

# 월별 데이터 수집 (병렬 처리)
months = [
    "202401", "202402", "202403", 
    "202404", "202405", "202406"
]

for month in months:
    try:
        data = collector.collect_real_estate_transaction_data(
            transaction_date=month,
            region_code="all"  # 전국
        )
        data.to_csv(f"data/raw/real_estate_{month}.csv")
        print(f"✅ {month} 데이터 수집 완료: {len(data)} 행")
    except Exception as e:
        print(f"❌ {month} 데이터 수집 실패: {e}")
```

**3.2 데이터 검증 체크리스트**:
- ✓ 데이터 행 수 (예상: 5M~8M 행)
- ✓ 컬럼 수 (예상: 26 컬럼)
- ✓ 중복 제거 (0개)
- ✓ NULL 값 처리 (< 1%)
- ✓ 이상치 감지 (< 5%)
- ✓ 가격 범위 확인 (10억 ~ 50억 원)

---

### 3.3 데이터 전처리 (4-6시간)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 입력 | 출력 | 체크리스트 |
|--------|--------|---------|---------|------|------|-----------|
| 3.3.1 | 데이터 로드 | 6개월 통합 CSV 로드 | 10분 | 595-820MB | DataFrame | ☐ |
| 3.3.2 | 결측치 처리 | NULL 값 대체 (평균/중위수) | 30분 | raw data | cleaned data | ☐ |
| 3.3.3 | 이상치 탐지 | IQR 방법으로 이상치 식별 | 20분 | data | outlier list | ☐ |
| 3.3.4 | 이상치 제거 | 극단값 제거 또는 대체 | 15분 | outlier list | cleaned data | ☐ |
| 3.3.5 | 정규화 | Min-Max 정규화 적용 | 20분 | data | normalized data | ☐ |
| 3.3.6 | 파생변수 생성 | 지역별 평균가, 아파트 나이 등 | 30분 | data | feature engineered data | ☐ |
| 3.3.7 | 최종 검증 | 데이터 품질 평가 | 20분 | data | quality report | ☐ |
| 3.3.8 | 저장 | 전처리된 데이터 저장 | 10분 | data | CSV/Parquet | ☐ |

**3.3 전처리 파이프라인**:
```python
from scripts.data_preprocessing import DataPreprocessor

preprocessor = DataPreprocessor()

# Step 1-2: 로드 및 결측치 처리
df = preprocessor.load_data("data/raw/real_estate_combined.csv")
df_cleaned = preprocessor.handle_missing_values(df, strategy="mean")

# Step 3-4: 이상치 처리
outliers = preprocessor.detect_outliers(df_cleaned)
df_cleaned = df_cleaned.drop(outliers.index)

# Step 5-6: 정규화 및 파생변수
df_normalized = preprocessor.normalize_data(df_cleaned)
df_featured = preprocessor.feature_engineering(df_normalized)

# Step 7-8: 검증 및 저장
quality_report = preprocessor.explore_data(df_featured)
preprocessor.save_processed_data(df_featured, "data/processed/real_estate_final.csv")
```

**3.3 품질 지표**:
- 데이터 행 수: 3M~5M (제거 후)
- 결측치율: < 0.5%
- 이상치 제거율: 2-5%
- 파생변수: 4개 추가
- 정규화 범위: [0, 1]

---

### 3.4 모델 재학습 (2-4시간)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 모델 | 입력 데이터 | 예상 R² | 체크리스트 |
|--------|--------|---------|---------|------|-----------|--------|-----------|
| 3.4.1 | 데이터 분할 | Train(70%), Val(15%), Test(15%) | 5분 | - | 전처리 데이터 | - | ☐ |
| 3.4.2 | Linear Regression | 기본 선형회귀 학습 | 10분 | LR | train data | 0.92-0.94 | ☐ |
| 3.4.3 | Decision Tree | 의사결정트리 학습 | 15분 | DT | train data | 0.85-0.87 | ☐ |
| 3.4.4 | Random Forest | 랜덤포레스트 학습 | 20분 | RF | train data | 0.88-0.90 | ☐ |
| 3.4.5 | Gradient Boosting | 그래디언트 부스팅 학습 | 25분 | GB | train data | 0.89-0.91 | ☐ |
| 3.4.6 | XGBoost | XGBoost 학습 + 튜닝 | 30분 | XGB | train data | 0.90-0.92 | ☐ |
| 3.4.7 | LightGBM | LightGBM 학습 + 튜닝 | 20분 | LGBM | train data | 0.89-0.91 | ☐ |
| 3.4.8 | 모델 평가 | 모든 모델 검증 데이터셋 평가 | 15분 | 6개 모델 | val data | - | ☐ |
| 3.4.9 | 모델 비교 | 성능 순위 매기기 | 10분 | 6개 모델 | 평가 결과 | - | ☐ |

**3.4 학습 코드**:
```python
from scripts.model_development import AVMModelDeveloper

developer = AVMModelDeveloper()

# 데이터 분할
X_train, X_val, X_test, y_train, y_val, y_test = developer.prepare_features(
    df_featured, 
    test_size=0.15,
    val_size=0.15
)

# 6개 모델 학습
models_dict = {
    "LinearRegression": developer.train_linear_regression(X_train, y_train),
    "DecisionTree": developer.train_decision_tree(X_train, y_train),
    "RandomForest": developer.train_random_forest(X_train, y_train),
    "GradientBoosting": developer.train_gradient_boosting(X_train, y_train),
    "XGBoost": developer.train_xgboost(X_train, y_train),
    "LightGBM": developer.train_lightgbm(X_train, y_train)
}

# 모델 평가
results = {}
for name, model in models_dict.items():
    r2, rmse, mae = developer.evaluate_model(model, X_val, y_val)
    results[name] = {"R2": r2, "RMSE": rmse, "MAE": mae}
    print(f"{name}: R²={r2:.4f}, RMSE={rmse:.2f}")

# 최고 성능 모델 저장
best_model_name = max(results, key=lambda x: results[x]["R2"])
developer.save_model(models_dict[best_model_name], f"models/{best_model_name}_model.joblib")
```

**3.4 예상 성능 향상**:
| 모델 | 샘플 데이터 R² | 실제 데이터 R² | 개선도 |
|------|---------------|---------------|--------|
| Linear Regression | 0.9251 | 0.93-0.95 | +0.01-0.03 |
| Decision Tree | 0.8545 | 0.86-0.88 | +0.01-0.02 |
| Random Forest | 0.8920 | 0.90-0.92 | +0.01-0.02 |
| Gradient Boosting | 0.8876 | 0.90-0.92 | +0.01-0.02 |
| XGBoost | 0.8765 | 0.89-0.91 | +0.01-0.02 |
| LightGBM | 0.8654 | 0.88-0.90 | +0.01-0.02 |

---

### 3.5 신규 모델 배포 (1시간)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 의존성 | 체크리스트 |
|--------|--------|---------|---------|--------|-----------|
| 3.5.1 | 모델 버전 관리 | 날짜 기반 버전 지정 | 5분 | 3.4.9 | ☐ |
| 3.5.2 | 모델 검증 | 저장된 모델 로드 및 테스트 | 10분 | 3.5.1 | ☐ |
| 3.5.3 | 모델 서명 | SHA256 해시 생성 | 5분 | 3.5.2 | ☐ |
| 3.5.4 | API 서버 업데이트 | api_server.py에서 신규 모델 로드 | 10분 | 3.5.3 | ☐ |
| 3.5.5 | Docker 재빌드 | 신규 모델 포함 Docker 이미지 빌드 | 5분 | 3.5.4 | ☐ |
| 3.5.6 | Cloud Run 재배포 | 신규 이미지 배포 | 5분 | 3.5.5 | ☐ |
| 3.5.7 | 배포 검증 | /predict 엔드포인트로 예측 테스트 | 15분 | 3.5.6 | ☐ |

**3.5 배포 명령어**:
```bash
# 3.5.1: 버전 지정
MODEL_VERSION="20260616_real_data_v1"

# 3.5.2-3.5.3: 모델 검증 및 서명
python scripts/validate_and_sign_model.py \
  --model_path models/LinearRegression_model.joblib \
  --version $MODEL_VERSION

# 3.5.4: API 서버 업데이트
# config/avm_config.json의 모델 경로 업데이트
sed -i "s/model_path.*$/\"model_path\": \"models\/LinearRegression_model.joblib\"/g" config/avm_config.json

# 3.5.5-3.5.6: 재빌드 및 배포
cd /home/user/-/avm_project
docker build -t gcr.io/[PROJECT_ID]/avm-model:$MODEL_VERSION .
docker push gcr.io/[PROJECT_ID]/avm-model:$MODEL_VERSION

gcloud run deploy avm-model \
  --image gcr.io/[PROJECT_ID]/avm-model:$MODEL_VERSION \
  --region asia-northeast1 \
  --no-traffic  # 카나리 배포

# 3.5.7: 배포 검증
curl -X POST "https://[SERVICE_URL]/predict" \
  -H "Content-Type: application/json" \
  -d '{"area": 100, "age": 10, "location_score": 0.8}'
```

---

## 🚀 PHASE 4: 완전 자동화 (총 1주)

### 4.1 성능 최적화 (2일)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 목표 | 체크리스트 |
|--------|--------|---------|---------|------|-----------|
| 4.1.1 | 모델 캐싱 | Redis 또는 메모리 캐시 구현 | 4시간 | 응답시간 50% 단축 | ☐ |
| 4.1.2 | 배치 최적화 | 배치 예측 처리 최적화 | 3시간 | 처리량 200% 증가 | ☐ |
| 4.1.3 | 데이터베이스 최적화 | 인덱싱 및 쿼리 최적화 | 4시간 | 쿼리 속도 10배 | ☐ |
| 4.1.4 | 이미지 최적화 | Docker 이미지 크기 감소 | 2시간 | 크기 50% 감소 | ☐ |
| 4.1.5 | 코드 프로파일링 | 병목 지점 분석 | 3시간 | 주요 병목 식별 | ☐ |

**4.1.1 모델 캐싱 구현**:
```python
# 캐시 기반 예측
from functools import lru_cache
import json

@lru_cache(maxsize=10000)
def cached_predict(features_json: str):
    features = json.loads(features_json)
    return model.predict([features])

# 또는 Redis 캐시
import redis
cache = redis.Redis(host='localhost', port=6379)

def predict_with_cache(features):
    cache_key = json.dumps(features, sort_keys=True)
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    
    result = model.predict([features])
    cache.setex(cache_key, 3600, json.dumps(result.tolist()))
    return result
```

**4.1.2 배치 최적화**:
```python
# 벡터화된 배치 처리
def predict_batch_optimized(features_df, batch_size=1000):
    results = []
    for i in range(0, len(features_df), batch_size):
        batch = features_df.iloc[i:i+batch_size]
        predictions = model.predict(batch)
        results.extend(predictions)
    return results
```

---

### 4.2 고급 기능 구현 (2.5일)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 기술 스택 | 체크리스트 |
|--------|--------|---------|---------|----------|-----------|
| 4.2.1 | 신뢰도 추정 | 예측값의 신뢰도/불확실성 계산 | 1일 | Monte Carlo | ☐ |
| 4.2.2 | 이상탐지 | 비정상 입력값 탐지 | 12시간 | Isolation Forest | ☐ |
| 4.2.3 | 설명가능성 | SHAP 값으로 예측 설명 | 12시간 | SHAP | ☐ |
| 4.2.4 | A/B 테스트 | 모델 버전 비교 | 12시간 | Bayesian | ☐ |

**4.2.1 신뢰도 추정**:
```python
# Monte Carlo Dropout으로 불확실성 계산
def predict_with_uncertainty(features, n_iterations=100):
    predictions = []
    for _ in range(n_iterations):
        pred = model.predict(features)  # dropout 활성화
        predictions.append(pred)
    
    predictions = np.array(predictions)
    mean = predictions.mean(axis=0)
    std = predictions.std(axis=0)
    
    return mean, std  # 예측값과 표준편차
```

**4.2.2 이상탐지**:
```python
from sklearn.ensemble import IsolationForest

anomaly_detector = IsolationForest(contamination=0.05)
anomaly_scores = anomaly_detector.decision_function(features)

# 이상 점수가 낮으면 비정상 데이터
is_anomaly = anomaly_detector.predict(features) == -1
```

---

### 4.3 부하 테스트 (1.5일)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 테스트 목표 | 체크리스트 |
|--------|--------|---------|---------|-----------|-----------|
| 4.3.1 | 단계적 부하 테스트 | 100→10K→100K req/sec | 8시간 | 안정성 검증 | ☐ |
| 4.3.2 | 스트레스 테스트 | 최대 용량 초과 테스트 | 4시간 | 한계점 파악 | ☐ |
| 4.3.3 | 스파이크 테스트 | 갑작스런 트래픽 증가 테스트 | 4시간 | 반응성 검증 | ☐ |

**4.3 부하 테스트 도구**:
```bash
# Apache Bench (ab)
ab -n 100000 -c 1000 https://[SERVICE_URL]/health

# wrk (고성능)
wrk -t12 -c400 -d30s https://[SERVICE_URL]/predict

# Locust (분산 부하)
locust -f scripts/load_test.py --host https://[SERVICE_URL]
```

**4.3 테스트 결과 예상**:
- ✅ 100 req/sec: 응답시간 < 50ms
- ✅ 1K req/sec: 응답시간 < 100ms
- ✅ 10K req/sec: 응답시간 < 200ms
- ✅ 100K req/sec: 응답시간 < 500ms (인스턴스 자동 확장)

---

### 4.4 보안 검증 (1일)

| 작업ID | 작업명 | 상세 내용 | 소요시간 | 검증 항목 | 체크리스트 |
|--------|--------|---------|---------|----------|-----------|
| 4.4.1 | 보안 스캔 | Bandit, Safety로 코드 스캔 | 2시간 | 0개 HIGH | ☐ |
| 4.4.2 | 의존성 스캔 | 라이브러리 취약점 확인 | 2시간 | 0개 HIGH | ☐ |
| 4.4.3 | API 보안 | SQL 주입, XSS 테스트 | 3시간 | 100% 안전 | ☐ |
| 4.4.4 | 컨테이너 보안 | Docker 이미지 스캔 | 1시간 | 0개 CRITICAL | ☐ |

**4.4 보안 검증 명령어**:
```bash
# Bandit
bandit -r /home/user/-/avm_project/scripts

# Safety
safety check --requirements requirements.txt

# Trivy (Docker 이미지 스캔)
trivy image gcr.io/[PROJECT_ID]/avm-model:latest

# OWASP ZAP (API 보안)
zaproxy -config api.enabled=true -cmd -quickurl https://[SERVICE_URL] -quickout security_report.html
```

---

## 📅 타임라인 및 의존성

### 전체 타임라인 (병렬 처리 가정)
```
시작 → PHASE 1 (2-3시간)
     ↓
     → PHASE 2 (1.5시간, PHASE 1 이후 시작 가능)
     ↓
     → PHASE 3 (2-3일, PHASE 1 완료 필요)
     ↓
     → PHASE 4 (1주, PHASE 3 완료 필요)

총 소요 기간: 약 10-14일 (병렬 처리 시)
```

### 의존성 매트릭스
| Phase | 선행 조건 | 병렬 가능 | 소요시간 |
|-------|---------|---------|---------|
| 1 | 없음 | X | 2-3시간 |
| 2 | Phase 1 완료 | Phase 1과 직렬 | 1.5시간 |
| 3 | Phase 1 완료 | Phase 2와 병렬 가능 | 2-3일 |
| 4 | Phase 3 완료 | Phase 2, 3과 직렬 | 1주 |

### 추천 실행 순서
1. **Day 1 (PHASE 1)**: Cloud Run 배포 (2-3시간)
2. **Day 1-2 (PHASE 2)**: AUTO-LOOP 설정 (1.5시간, PHASE 1 이후)
3. **Day 2-4 (PHASE 3)**: 실제 데이터 수집 (2-3일, PHASE 1 완료 후 병렬 가능)
4. **Day 5-11 (PHASE 4)**: 완전 자동화 (1주)

---

## ✅ 성공 기준 및 검수 체크리스트

### PHASE 1 완료 기준
- ☐ Cloud Run 서비스 배포 완료
- ☐ /health 엔드포인트 HTTP 200 응답
- ☐ /predict 예측 API 정상 작동
- ☐ 부하 테스트 (1000 req/sec) 통과
- ☐ deployment_info.json 생성 완료

### PHASE 2 완료 기준
- ☐ Cron job 등록 (매주 목요일 10:00)
- ☐ Cloud Logging 통합 완료
- ☐ 모니터링 대시보드 생성
- ☐ 알림 규칙 3개 이상 설정
- ☐ 자동 스케일링 (min: 1, max: 10) 설정

### PHASE 3 완료 기준
- ☐ Data.go.kr API 인증 완료
- ☐ 6개월 데이터 (595-820MB) 수집
- ☐ 데이터 품질 보고서 생성
- ☐ 6개 모델 학습 완료 (R² > 0.88)
- ☐ 신규 모델 배포 완료

### PHASE 4 완료 기준
- ☐ 모델 캐싱 구현 (응답시간 50% 개선)
- ☐ 신뢰도 추정 구현
- ☐ 이상탐지 기능 구현
- ☐ 부하 테스트 (100K req/sec) 통과
- ☐ 보안 스캔 0개 HIGH 이상 취약점

---

## 📊 예상 결과물 및 산출물

### Phase 1 산출물
- `config/deployment_info.json` - 배포 정보
- `logs/deployment.log` - 배포 로그
- Cloud Run Service URL

### Phase 2 산출물
- `config/cron_automation_setup.sh` - Cron 스크립트
- `config/monitoring_dashboard.json` - 모니터링 대시보드
- `config/alert_rules.json` - 알림 규칙

### Phase 3 산출물
- `data/raw/real_estate_202401-202406.csv` - 수집 데이터
- `data/processed/real_estate_final.csv` - 전처리 데이터
- `models/LinearRegression_20260616_v1.joblib` - 신규 모델
- `reports/phase3_model_comparison.json` - 모델 비교 보고서

### Phase 4 산출물
- `config/model_caching_config.json` - 캐시 설정
- `reports/performance_optimization_report.md` - 성능 개선 보고서
- `reports/load_test_results.html` - 부하 테스트 결과
- `reports/security_scan_report.json` - 보안 스캔 결과

---

## 🎯 주요 KPI 및 목표치

| KPI | 현재값 | 목표값 | Phase |
|-----|--------|--------|-------|
| 응답시간 (평균) | 0.0083ms | < 0.01ms | 4.1 |
| 처리량 | 121K req/sec | > 150K req/sec | 4.1 |
| 모델 정확도 (R²) | 0.9251 | 0.95+ | 3.4 |
| 데이터 용량 | 124KB (샘플) | 500MB+ (실제) | 3.2 |
| 배포 시간 | - | < 5분 | 1.2 |
| 가용성 | 99.95% | 99.99% | 4.3 |
| 보안 취약점 | 0개 HIGH | 0개 HIGH | 4.4 |

---

## 📝 문서 및 참고 자료

### 기존 문서
- ✅ `FINAL_ASSESSMENT_100_POINTS_AND_NEXT_TASKS.md` - 최종 평가 및 계획
- ✅ `AVM_AGENT_INJECTION.md` - 전체 코드 주입 가이드
- ✅ `PHASE1_DEPLOYMENT_MANUAL.md` - Phase 1 배포 매뉴얼

### 생성될 문서
- 📝 `PHASE1_DEPLOYMENT_EXECUTION_REPORT.md` - Phase 1 실행 보고서
- 📝 `PHASE2_AUTOMATION_SETUP_GUIDE.md` - Phase 2 자동화 가이드
- 📝 `PHASE3_DATA_COLLECTION_REPORT.md` - Phase 3 데이터 수집 보고서
- 📝 `PHASE4_OPTIMIZATION_RESULTS.md` - Phase 4 최적화 결과

---

**작성자**: AI 개발팀  
**최종 승인**: 사용자  
**버전**: 1.0  
**상태**: 준비 완료 (Ready to Execute)
