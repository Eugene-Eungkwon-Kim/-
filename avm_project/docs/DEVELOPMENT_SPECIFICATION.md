# AVM 프로젝트 상세 개발 명세서

**버전:** 1.0  
**작성일:** 2026-06-15  
**상태:** 개발 중  
**완성도:** Phase 1 완료, Phase 2 진행 중

---

## 1. 프로젝트 개요

### 1.1 목표
- **주요 목표:** Data.go.kr 및 Vworld 공공데이터를 활용한 AVM(Automated Valuation Model) 개발
- **3가지 핵심 산출물:**
  1. **AVM 모델**: 머신러닝 기반 부동산 자동감정 모델 (7개 알고리즘, R² > 0.90)
  2. **부동산 평가 시스템**: FastAPI REST API 서버 (6개 엔드포인트, 7개 모델 제공)
  3. **데이터 저장소 구축**: D-드라이브 기반 표준화된 데이터 저장소 (Raw/Processed/Indexed/Cleansed)

### 1.2 기술 스택
```
언어: Python 3.11+
ML 프레임워크: scikit-learn, XGBoost, LightGBM, TensorFlow
API 서버: FastAPI + Uvicorn
DB: PostgreSQL (선택사항)
컨테이너: Docker + Cloud Run
버전 관리: Git
```

### 1.3 핵심 정책
- **데이터 저장:** D:\LG_AVM_Workspace_Data_Moved_20260604\ (LG 외장 SSD)
- **폴더 구조:** 타임스탬프 라벨링 (예: 2026-06-15_DataGovKr_Downloaded)
- **배경 실행:** LG gram 랩탑에서 Windows Task Scheduler/WSL Cron
- **토큰 최소화:** Python-first, 최소한의 설명

---

## 2. 기능 요구사항 (FRD)

### 2.1 데이터 수집 (Phase 1 - 완료)

#### 요구사항 ID: REQ-DATA-001
**기능:** Data.go.kr 부동산 실거래 정보 API 연동
- **입력:** 지역코드(LAWD_CD), 거래년월(DEAL_YMD)
- **출력:** JSON 형식 거래정보 데이터
- **API:** https://apis.data.go.kr/1613000/RealEstateTransactionService/getRealEstateTransactionList
- **필수 필드:** 거래금액, 주소, 면적, 용도, 건축년도
- **성능:** 1000건/요청, 30초 타임아웃

#### 요구사항 ID: REQ-DATA-002
**기능:** Vworld 건물정보 API 연동
- **입력:** 좌표(WGS84), 범위 검색
- **출력:** JSON 형식 건물정보
- **API:** https://api.vworld.kr/req/data (LP_PA_CBND 레이어)
- **필수 필드:** 건물명, 용도, 준공년도, 지표면적, 연면적

#### 요구사항 ID: REQ-DATA-003
**기능:** 데이터 마이그레이션
- **입력:** 로컬 아래 원본 데이터
- **출력:** D-드라이브 표준 폴더 구조
- **폴더:** Raw_Data, Processed_Data, Indexed_Data, Cleansed_Data, Archived
- **형식:** 타임스탐프 라벨링

### 2.2 데이터 처리 (Phase 1 완료)

#### 요구사항 ID: REQ-PROCESS-001
**기능:** 데이터 검증 (Debug)
- **검사항목:** 파일 무결성, JSON/CSV 형식, 스키마 검증
- **산출물:** QA_REPORT_{TIMESTAMP}.md
- **목표:** 100% 파일 유효성 검증

#### 요구사항 ID: REQ-PROCESS-002
**기능:** 데이터 인덱싱
- **인덱스 타입:** 마스터 인덱스, 검색 인덱스
- **산출물:** master_index_{TIMESTAMP}.json, search_index_{TIMESTAMP}.json
- **메타데이터:** 행 수, 컬럼 수, 통계, 데이터타입

#### 요구사항 ID: REQ-PROCESS-003
**기능:** 데이터 클렌징
- **결측치 처리:** 수치형 평균값, 범주형 최빈값 대체
- **아웃라이어 제거:** IQR 방법 (Q1-1.5×IQR ~ Q3+1.5×IQR)
- **정규화:** Min-Max 스케일링 (0-1 범위)
- **산출물:** Cleansed_Data 폴더의 정제된 CSV/JSON

### 2.3 모델 개발 (Phase 2 - 진행 중)

#### 요구사항 ID: REQ-MODEL-001
**기능:** 7개 머신러닝 모델 학습

| 모델 | 알고리즘 | 목표 R² | 교차검증 |
|------|---------|--------|--------|
| M1 | Linear Regression | > 0.80 | 5-Fold |
| M2 | Decision Tree | > 0.85 | 5-Fold |
| M3 | Random Forest | > 0.90 | 5-Fold |
| M4 | Gradient Boosting | > 0.90 | 5-Fold |
| M5 | XGBoost | > 0.92 | 5-Fold |
| M6 | LightGBM | > 0.92 | 5-Fold |
| M7 | Neural Network | > 0.90 | 5-Fold |

#### 요구사항 ID: REQ-MODEL-002
**기능:** 하이퍼파라미터 최적화
- **방법:** GridSearchCV, 5-Fold 교차검증
- **출력:** 
  - hyperparameter_tuning_results.json (최적 파라미터)
  - model_comparison_tuned.csv (성능 비교)
  - models/*_tuned.pkl (튜닝된 모델)
- **실행 시간:** 10분 이내 (병렬 처리 지원)

#### 요구사항 ID: REQ-MODEL-003
**기능:** 모델 평가
- **지표:** R², RMSE, MAE, MAPE
- **검증:** 학습/검증/테스트 셋 분리 (60/20/20)
- **산출물:** evaluation_report.json

### 2.4 API 서버 (Phase 2 진행 중)

#### 요구사항 ID: REQ-API-001
**기능:** FastAPI 기반 REST API 서버

| 엔드포인트 | 메서드 | 기능 |
|-----------|--------|------|
| /predict | POST | 단일 예측 |
| /predict-batch | POST | 배치 예측 |
| /model-info | GET | 모델 정보 조회 |
| /model-list | GET | 전체 모델 목록 |
| /health | GET | 헬스 체크 |
| /docs | GET | Swagger UI |

#### 요구사항 ID: REQ-API-002
**기능:** 모델 서빙
- **모델 수:** 7개 모델 동시 서빙
- **포트:** 8000
- **문서화:** Swagger UI 자동 생성
- **응답 형식:** JSON with metadata

#### 요구사항 ID: REQ-API-003
**기능:** Docker 컨테이너화
- **기본 이미지:** Python 3.11-slim
- **보안:** 헬스 체크, 리소스 제한
- **배포:** Cloud Run 호환

### 2.5 배포 (Phase 2-3)

#### 요구사항 ID: REQ-DEPLOY-001
**기능:** Cloud Run 배포
- **프로젝트:** GCP 프로젝트 생성
- **빌드:** Docker 이미지 빌드
- **푸시:** Container Registry로 푸시
- **배포:** Cloud Run 서비스 배포
- **도메인:** 자동 할당 (https://avm-api-xxxxx.run.app)

#### 요구사항 ID: REQ-DEPLOY-002
**기능:** 자동화 및 모니터링
- **자동 실행:** Windows Task Scheduler / WSL Cron
- **빈도:** 주간 (목요일 10:00)
- **모니터링:** 실시간 로깅 및 리포트

---

## 3. 비기능 요구사항 (NFR)

### 3.1 성능
- **API 응답 시간:** < 500ms (단일 예측)
- **배치 처리:** 1000건/초
- **메모리 사용:** < 2GB (단일 컨테이너)
- **모델 로드 시간:** < 5초

### 3.2 신뢰성
- **가용성:** 99.5% (Cloud Run)
- **데이터 무결성:** MD5/SHA256 체크섬
- **실패 복구:** 자동 재시작

### 3.3 보안
- **API 인증:** API Key (선택사항)
- **데이터 암호화:** HTTPS (Cloud Run)
- **민감정보:** API 키를 환경변수로 관리

### 3.4 확장성
- **수평 확장:** Cloud Run auto-scaling (0-100 인스턴스)
- **모델 추가:** 신규 모델 .pkl 파일 추가만으로 자동 로드

### 3.5 유지보수성
- **코드 품질:** PEP 8 준수
- **로깅:** 구조화된 로깅 (JSON)
- **문서화:** 모든 함수에 docstring

---

## 4. 기술 설계 (TDD)

### 4.1 데이터 아키텍처
```
D:\LG_AVM_Workspace_Data_Moved_20260604\
├── 2026-06-15_DataGovKr_Downloaded/      # API 다운로드
│   ├── real_estate_202406.json
│   └── manifest_2026-06-15.json
├── 2026-06-15_Vworld_Downloaded/         # API 다운로드
│   ├── vworld_building_info.json
│   └── manifest_2026-06-15.json
├── Migration_2026-06-15/                 # 마이그레이션
│   ├── real_estate_202406.json
│   └── vworld_building_info.json
├── Raw_Data/                             # 원본 데이터
├── Processed_Data/                       # 처리된 데이터
├── Indexed_Data/                         # 인덱스
│   ├── master_index_2026-06-15.json
│   └── search_index_2026-06-15.json
├── Cleansed_Data/                        # 정제 데이터
└── Archived/                             # 아카이브
```

### 4.2 모델 아키텍처
```
Input Data (30 features)
    ↓
[7 Parallel Models]
├─ Linear Regression
├─ Decision Tree
├─ Random Forest
├─ Gradient Boosting
├─ XGBoost
├─ LightGBM
└─ Neural Network
    ↓
Ensemble/Voting
    ↓
Output (가격 예측)
```

### 4.3 API 아키텍처
```
FastAPI Server (uvicorn)
├─ /predict (Single Prediction)
├─ /predict-batch (Batch Prediction)
├─ /model-info (Model Metadata)
├─ /model-list (Available Models)
├─ /health (Health Check)
└─ /docs (Swagger UI)
    ↓
Model Inference Engine
├─ Model Loader (lazy loading)
├─ Feature Engineering
├─ Prediction Pipeline
└─ Response Formatter
```

---

## 5. 모듈 설계

### 5.1 데이터 수집 (download_data.py)
```python
DataDownloader
├─ download_datagovkr()      # Data.go.kr API
├─ download_vworld()         # Vworld API
├─ create_labeled_folder()   # 폴더 생성
├─ create_manifest()         # 메타데이터
└─ run()                      # 통합 실행
```

### 5.2 데이터 마이그레이션 (migrate_data.py)
```python
DataMigrator
├─ migrate_from_local()      # 로컬 → D-드라이브
├─ create_structure()        # 표준 폴더 구조
└─ run()                      # 통합 실행
```

### 5.3 데이터 검증 (debug_data.py)
```python
DataDebugger
├─ validate_json_files()     # JSON 검증
├─ validate_csv_files()      # CSV 검증
├─ check_manifest()          # 메타데이터 검증
├─ generate_qa_report()      # QA 리포트
└─ run()                      # 통합 실행
```

### 5.4 데이터 인덱싱 (index_data.py)
```python
DataIndexer
├─ create_csv_index()        # CSV 인덱싱
├─ create_json_index()       # JSON 인덱싱
├─ create_master_index()     # 마스터 인덱스
├─ create_search_index()     # 검색 인덱스
├─ generate_index_report()   # 리포트
└─ run()                      # 통합 실행
```

### 5.5 데이터 클렌징 (cleanse_data.py)
```python
DataCleaner
├─ handle_missing_values()   # 결측치 처리
├─ remove_outliers()         # 아웃라이어 제거
├─ normalize_data()          # 정규화
├─ cleanse_csv_files()       # CSV 클렌징
├─ generate_cleansing_report() # 리포트
└─ run()                      # 통합 실행
```

### 5.6 파이프라인 오케스트레이션 (main_pipeline.py)
```python
PipelineOrchestrator
├─ run_script()              # 개별 스크립트 실행
├─ generate_summary()        # 실행 요약
└─ run()                      # 전체 워크플로우
```

### 5.7 모델 개발 (model_development.py - 기존)
```python
AVMModelDeveloper
├─ train_linear_regression() 
├─ train_decision_tree()
├─ train_random_forest()
├─ train_gradient_boosting()
├─ evaluate_model()
├─ hyperparameter_tuning()
└─ save_model()
```

### 5.8 API 서버 (api_server.py - 기존)
```python
FastAPI App
├─ @app.post("/predict")
├─ @app.post("/predict-batch")
├─ @app.get("/model-info")
├─ @app.get("/model-list")
├─ @app.get("/health")
└─ /docs (Swagger UI)
```

---

## 6. 데이터 사양

### 6.1 입력 데이터 (Feature Set)
| 번호 | 필드명 | 타입 | 설명 | 출처 |
|------|--------|------|------|------|
| 1 | 거래금액 | float | 부동산 거래가 (단위: 만원) | Data.go.kr |
| 2 | 주소 | str | 부동산 위치 | Data.go.kr |
| 3 | 면적 | float | 건물 면적 (m²) | Data.go.kr/Vworld |
| 4 | 용도 | str | 건물 용도 코드 | Data.go.kr/Vworld |
| 5 | 건축년도 | int | 건축 연도 | Data.go.kr/Vworld |
| 6-26 | ... | ... | ... | ... |
| 27 | 수익성지수 | float | 파생변수: ROI 지표 | 계산 |
| 28 | 위치점수 | float | 파생변수: 거리 기반 | 계산 |
| 29 | 수요지수 | float | 파생변수: 거래량 기반 | 계산 |
| 30 | 시장지수 | float | 파생변수: 시계열 추세 | 계산 |

### 6.2 출력 데이터 (Prediction)
```json
{
  "predicted_price": 450000,
  "confidence": 0.92,
  "model": "xgboost_tuned",
  "timestamp": "2026-06-15T12:30:45Z",
  "features_used": 30,
  "processing_time_ms": 45
}
```

---

## 7. 테스트 전략

### 7.1 단위 테스트 (Unit Test)
- **범위:** 각 모듈의 개별 함수
- **커버리지:** 80% 이상
- **도구:** pytest

### 7.2 통합 테스트 (Integration Test)
- **범위:** ETL 파이프라인 전체
- **테스트:** download → migrate → debug → index → cleanse
- **검증:** 각 단계 출력 파일 생성 확인

### 7.3 성능 테스트 (Performance Test)
- **모델 로드:** < 5초
- **API 응답:** < 500ms
- **배치 처리:** 1000건/초

### 7.4 데이터 검증 테스트 (Data Validation)
- **스키마 검증:** 모든 필드 타입 확인
- **범위 검증:** 값의 합리성 확인
- **무결성:** 중복 레코드 확인

---

## 8. 배포 전략

### 8.1 로컬 개발 환경
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/main_pipeline.py
python scripts/api_server.py
```

### 8.2 Docker 배포
```bash
docker build -t avm-api:latest .
docker-compose up -d
```

### 8.3 Cloud Run 배포
```bash
export PROJECT_ID="avm-api-prod"
gcloud builds submit --tag gcr.io/$PROJECT_ID/avm-api:latest
gcloud run deploy avm-api \
  --image gcr.io/$PROJECT_ID/avm-api:latest \
  --platform managed \
  --region us-central1
```

---

## 9. 위험 및 대응방안

| 위험 | 영향 | 확률 | 대응방안 |
|------|------|------|---------|
| API 키 만료/거부 | 데이터 수집 불가 | 중 | 백업 API 키 준비, 대체 데이터소스 |
| D-드라이브 용량 부족 | 데이터 저장 실패 | 낮음 | 압축, 아카이브 자동화 |
| 모델 성능 미달 | 예측 정확도 낮음 | 중 | 특성 엔지니어링, 데이터 증강 |
| 서버 다운 | 서비스 중단 | 낮음 | 자동 재시작, 모니터링 알림 |

---

## 10. 성공 기준 (Definition of Done)

### 10.1 코드 관점
- [ ] PEP 8 준수 (pylint score > 8.0)
- [ ] 단위 테스트 커버리지 ≥ 80%
- [ ] 모든 함수에 docstring 작성
- [ ] 에러 핸들링 완벽
- [ ] 보안 취약점 없음

### 10.2 기능 관점
- [ ] 모든 요구사항 구현 완료
- [ ] 통합 테스트 통과
- [ ] 성능 목표 달성 (R² > 0.90)
- [ ] API 문서 자동 생성

### 10.3 데이터 관점
- [ ] 원본 데이터 검증 100%
- [ ] 클렌징 완료 (결측치 0%)
- [ ] 인덱싱 완료 (검색 가능)
- [ ] 메타데이터 일관성 검증

### 10.4 배포 관점
- [ ] Docker 이미지 빌드 성공
- [ ] Cloud Run 배포 성공
- [ ] 자동화 스크립트 실행 성공
- [ ] 모니터링/로깅 설정 완료

---

## 11. 체크리스트

### Phase 1 (완료)
- [x] ETL 파이프라인 스크립트 작성 (6개)
- [x] API 키 확보 및 검증
- [x] D-드라이브 경로 설정
- [x] 샘플 데이터 생성
- [x] 파이프라인 로컬 테스트

### Phase 2 (진행 중)
- [x] 하이퍼파라미터 튜닝 스크립트
- [x] FastAPI 서버 구현
- [x] Docker 이미지 준비
- [ ] 모델 최적화 완료 (OPTION 2)
- [ ] API 테스트 및 검증

### Phase 3 (예정)
- [ ] GCP 프로젝트 생성
- [ ] Cloud Run 배포
- [ ] 실제 데이터 수집
- [ ] 모델 재학습

### Phase 4 (예정)
- [ ] 자동화 스크립트 설정
- [ ] 모니터링 대시보드
- [ ] 정기 유지보수 계획

---

**문서 버전:** 1.0  
**최종 업데이트:** 2026-06-15  
**다음 검토:** Phase 2 완료 후
