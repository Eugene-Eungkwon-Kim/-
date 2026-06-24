# AVM 프로젝트 WBS (Work Breakdown Structure)
## 2026-06-24

---

## 프로젝트 구조

```
AVM 프로젝트 (35% → 100%)
│
├─ Phase 3: 운영 데이터 통합 (Week 1-5)
│   ├─ Task 3.1: 데이터 분석 및 스키마 설계
│   ├─ Task 3.2: 데이터 추출 및 정제
│   ├─ Task 3.3: 운영 마스터 데이터셋 생성
│   └─ Task 3.4: 모델 재학습 및 검증
│
└─ Phase 4: 클라우드 배포 (Week 1-6)
    ├─ Task 4.1: 클라우드 인프라 설계 및 구성
    ├─ Task 4.2: FastAPI 서빙 레이어 개발
    ├─ Task 4.3: 모니터링 및 최적화
    └─ Task 4.4: Go-Live 및 운영 인수인계
```

---

## Phase 3: 운영 데이터 통합

### Task 3.1: 데이터 분석 및 스키마 설계

#### 3.1.1 LG 외장하드 데이터 분석
```
ID: 3.1.1
담당: 데이터 분석가
기간: 3일 (2026-06-24 ~ 2026-06-26)
선행작업: 없음

세부 작업:
├─ 3.1.1.1: 디렉토리 구조 파악 (1일)
│   ├─ 파일 목록 작성
│   ├─ 파일 크기 정산
│   └─ 데이터 형식 분류
│
├─ 3.1.1.2: Database 파일 분석 (1일)
│   ├─ real_estate_transactions.db 분석
│   ├─ building_registry.db 분석
│   ├─ loan_portfolio.db 분석
│   └─ 테이블 관계 파악
│
└─ 3.1.1.3: Manifest 파일 검토 (1일)
    ├─ data_catalog.json 검토
    ├─ schema_definition.json 검토
    └─ 메타데이터 정리

산출물:
├─ DATA_STRUCTURE_ANALYSIS.md (10-15 페이지)
├─ TABLE_RELATIONSHIPS.json
└─ METADATA_SUMMARY.xlsx
```

#### 3.1.2 스키마 매핑 및 설계
```
ID: 3.1.2
담당: 데이터 엔지니어
기간: 3일 (2026-06-27 ~ 2026-06-30)
선행작업: 3.1.1 완료

세부 작업:
├─ 3.1.2.1: 스키마 매핑 (1.5일)
│   ├─ 원본 컬럼 → 통합 컬럼 매핑
│   ├─ 데이터 타입 표준화
│   └─ NULL 값 처리 규칙 정의
│
├─ 3.1.2.2: 통합 스키마 설계 (1일)
│   ├─ 19개 통합 컬럼 정의
│   ├─ 파생 변수 계산 규칙
│   └─ 인덱스 전략 수립
│
└─ 3.1.2.3: 검증 규칙 정의 (0.5일)
    ├─ 범위 검증 규칙
    ├─ 논리 검증 규칙
    └─ 중복 검증 규칙

산출물:
├─ SCHEMA_MAPPING_DOCUMENT.md (15-20 페이지)
├─ UNIFIED_SCHEMA.json
├─ VALIDATION_RULES.json
└─ DATA_QUALITY_CRITERIA.xlsx
```

---

### Task 3.2: 데이터 추출 및 정제

#### 3.2.1 데이터 추출 파이프라인 개발
```
ID: 3.2.1
담당: 데이터 엔지니어
기간: 4일 (2026-07-01 ~ 2026-07-04)
선행작업: 3.1.2 완료

세부 작업:
├─ 3.2.1.1: DB 추출 스크립트 개발 (2일)
│   ├─ extract_real_estate_db.py
│   ├─ extract_building_registry_db.py
│   ├─ extract_loan_portfolio_db.py
│   ├─ 에러 처리 로직
│   └─ 로깅 구현
│
├─ 3.2.1.2: CSV 로드 스크립트 (1일)
│   ├─ load_csv_data.py
│   ├─ 인코딩 처리
│   ├─ 형식 변환
│   └─ 에러 핸들링
│
└─ 3.2.1.3: 데이터 통합 및 검증 (1일)
    ├─ merge_datasets.py
    ├─ 충돌 해결
    ├─ 기본 검증
    └─ 통합 보고서 생성

산출물:
├─ extract_*.py (3개 파일)
├─ load_csv_data.py
├─ merge_datasets.py
├─ EXTRACTION_LOG.json
└─ RAW_DATA_SUMMARY.xlsx
```

#### 3.2.2 데이터 정제 및 검증
```
ID: 3.2.2
담당: 데이터 품질 엔지니어
기간: 3일 (2026-07-05 ~ 2026-07-07)
선행작업: 3.2.1 완료

세부 작업:
├─ 3.2.2.1: 결측치 처리 (1일)
│   ├─ 결측 패턴 분석
│   ├─ 대체 값 결정
│   ├─ handle_missing_values.py
│   └─ 처리 통계 기록
│
├─ 3.2.2.2: 아웃라이어 탐지 (1일)
│   ├─ IQR 방법 적용
│   ├─ Z-score 계산
│   ├─ detect_outliers.py
│   └─ 비이상 값 확인
│
└─ 3.2.2.3: 검증 규칙 적용 (1일)
    ├─ VALIDATION_RULES.json 적용
    ├─ validate_data.py
    ├─ 실패 건 분류
    └─ 정제 보고서 작성

산출물:
├─ handle_missing_values.py
├─ detect_outliers.py
├─ validate_data.py
├─ cleaned_real_estate_operational.csv
└─ DATA_CLEANING_REPORT.md (10 페이지)
```

---

### Task 3.3: 운영 마스터 데이터셋 생성

#### 3.3.1 마스터 데이터셋 생성
```
ID: 3.3.1
담당: 데이터 엔지니어
기간: 3일 (2026-07-08 ~ 2026-07-10)
선행작업: 3.2.2 완료

세부 작업:
├─ 3.3.1.1: 데이터 통합 (1일)
│   ├─ 모든 정제 데이터 병합
│   ├─ merge_cleaned_data.py
│   ├─ 중복 제거
│   └─ 정렬 및 인덱싱
│
├─ 3.3.1.2: 파생 변수 생성 (1day)
│   ├─ price_per_sqm 계산
│   ├─ age_years 계산
│   ├─ debt_to_price_ratio 계산
│   ├─ 추가 13개 파생 변수
│   └─ create_derived_features.py
│
└─ 3.3.1.3: 최종 검증 (1일)
    ├─ 완정성 검증 (≥95%)
    ├─ 통계 검증
    ├─ 비즈니스 로직 검증
    └─ 검증 보고서 작성

산출물:
├─ merge_cleaned_data.py
├─ create_derived_features.py
├─ master_real_estate_operational_20260710.csv (500MB+)
└─ MASTER_DATA_VALIDATION.md
```

#### 3.3.2 데이터 품질 보고서
```
ID: 3.3.2
담당: 데이터 분석가
기간: 2일 (2026-07-11 ~ 2026-07-12)
선행작업: 3.3.1 완료

세부 작업:
├─ 3.3.2.1: 통계 분석 (1일)
│   ├─ 행/열 수 정산
│   ├─ 메모리 사용량 계산
│   ├─ 컬럼별 통계 (min/max/mean/std)
│   ├─ 결측치 비율
│   └─ create_statistics_report.py
│
└─ 3.3.2.2: 품질 평가 (1일)
    ├─ 완정성 평가
    ├─ 정확성 평가
    ├─ 일관성 평가
    ├─ GO/NO-GO 판단
    └─ 보고서 작성

산출물:
├─ create_statistics_report.py
├─ OPERATIONAL_DATA_QUALITY_REPORT.md (15 페이지)
└─ DATA_QUALITY_METRICS.xlsx
```

---

### Task 3.4: 모델 재학습 및 검증

#### 3.4.1 모델 재학습
```
ID: 3.4.1
담당: ML 엔지니어
기간: 5일 (2026-07-15 ~ 2026-07-19)
선행작업: 3.3.2 완료

세부 작업:
├─ 3.4.1.1: 데이터 전처리 (1일)
│   ├─ 정규화/표준화
│   ├─ 특성 공학 (19개 특성)
│   ├─ Train/Test 분할 (80/20, 5-fold CV)
│   └─ preprocess_training_data.py
│
├─ 3.4.1.2: 모델 재학습 (2일)
│   ├─ XGBoost: train_xgboost_operational.py
│   ├─ Random Forest: train_rf_operational.py
│   ├─ Gradient Boosting: train_gb_operational.py
│   ├─ LightGBM: train_lgbm_operational.py
│   ├─ Decision Tree: train_dt_operational.py
│   ├─ Linear Regression: train_lr_operational.py
│   ├─ Voting Ensemble: train_ensemble_operational.py
│   └─ 병렬 학습 (모든 모델 동시 실행)
│
└─ 3.4.1.3: 하이퍼파라미터 튜닝 (2일)
    ├─ GridSearchCV 적용
    ├─ 최적 파라미터 탐색
    ├─ 모델 저장 (/models/operational/)
    └─ tune_hyperparameters.py

산출물:
├─ 7개 학습 스크립트
├─ preprocess_training_data.py
├─ tune_hyperparameters.py
├─ /models/operational/ (7개 모델)
└─ TRAINING_LOG.json
```

#### 3.4.2 성능 검증
```
ID: 3.4.2
담당: 데이터 과학자
기간: 4일 (2026-07-20 ~ 2026-07-23)
선행작업: 3.4.1 완료

세부 작업:
├─ 3.4.2.1: 성능 평가 (1.5일)
│   ├─ R² 점수 계산
│   ├─ RMSE, MAE, MAPE 계산
│   ├─ 모델별 비교 분석
│   └─ evaluate_model_performance.py
│
├─ 3.4.2.2: 괴리율 검증 (1.5일)
│   ├─ 예측가 vs 실제 거래가 비교
│   ├─ 절대/상대 오차 계산
│   ├─ ±3%, ±5%, ±10% 달성율
│   └─ calculate_discrepancy_rate.py
│
└─ 3.4.2.3: 최종 보고서 (1일)
    ├─ PoC vs 운영 성능 비교
    ├─ 성능 차이 원인 분석
    ├─ 모델 선정 추천
    └─ 최종 보고서 작성

산출물:
├─ evaluate_model_performance.py
├─ calculate_discrepancy_rate.py
├─ OPERATIONAL_MODEL_VALIDATION_REPORT.md (20 페이지)
└─ MODEL_PERFORMANCE_COMPARISON.xlsx
```

#### 3.4.3 자동화 재구성
```
ID: 3.4.3
담당: DevOps 엔지니어
기간: 3일 (2026-07-24 ~ 2026-07-26)
선행작업: 3.4.2 완료

세부 작업:
├─ 3.4.3.1: 데이터 수집 자동화 (1day)
│   ├─ sync_from_lg_drive.py
│   ├─ monthly_data_split.py
│   ├─ Cron 설정 (목요일 10:00)
│   └─ 로깅 구현
│
├─ 3.4.3.2: 모델 재학습 자동화 (1day)
│   ├─ operational_model_retrain.py
│   ├─ 월 1회 자동화 (월요일 11:00)
│   ├─ 성능 모니터링
│   └─ 모델 버전 관리
│
└─ 3.4.3.3: 운영 모니터링 강화 (1day)
    ├─ performance_monitoring.py
    ├─ alert_system.py
    ├─ 실시간 추적 설정
    └─ 알림 규칙 정의

산출물:
├─ sync_from_lg_drive.py
├─ monthly_data_split.py
├─ operational_model_retrain.py
├─ performance_monitoring.py
└─ alert_system.py
```

#### 3.4.4 운영 준비도 검토
```
ID: 3.4.4
담당: 프로젝트 매니저
기간: 2일 (2026-07-27 ~ 2026-07-28)
선행작업: 3.4.3 완료

세부 작업:
├─ 3.4.4.1: GO/NO-GO 게이트 검토 (1day)
│   ├─ 데이터 품질 확인
│   ├─ 모델 성능 확인
│   ├─ 자동화 준비 확인
│   └─ 배포 준비 확인
│
└─ 3.4.4.2: 최종 승인 (1day)
    ├─ 경영진 검토
    ├─ Phase 4 승인
    └─ 리소스 할당

산출물:
├─ GO_NO_GO_GATE_REVIEW.md
└─ PHASE_3_COMPLETION_REPORT.md
```

---

## Phase 4: 클라우드 배포

### Task 4.1: 클라우드 인프라 설계 및 구성

#### 4.1.1 아키텍처 설계
```
ID: 4.1.1
담당: 클라우드 아키텍트
기간: 3일 (2026-08-01 ~ 2026-08-03)
선행작업: 3.4.4 완료

세부 작업:
├─ 4.1.1.1: 플랫폼 평가 (1day)
│   ├─ AWS 평가
│   ├─ GCP 평가
│   ├─ Azure 평가
│   └─ 선택 및 권장사항
│
├─ 4.1.1.2: 아키텍처 설계 (1day)
│   ├─ VPC 구성 (3-tier)
│   ├─ RDS (PostgreSQL)
│   ├─ Lambda/ECS
│   ├─ S3 저장소
│   └─ CloudWatch 모니터링
│
└─ 4.1.1.3: 비용 추정 (1day)
    ├─ 월별 비용 계산
    ├─ 연간 비용 예상
    └─ 최적화 안내

산출물:
├─ CLOUD_ARCHITECTURE_DESIGN.md (20 페이지)
├─ ARCHITECTURE_DIAGRAM.png
├─ AWS_COST_ESTIMATE.xlsx
└─ PLATFORM_COMPARISON.xlsx
```

#### 4.1.2 인프라 구성
```
ID: 4.1.2
담당: 인프라 엔지니어
기간: 5일 (2026-08-04 ~ 2026-08-08)
선행작업: 4.1.1 완료

세부 작업:
├─ 4.1.2.1: IaC 작성 (2days)
│   ├─ Terraform 스크립트 작성
│   ├─ VPC 정의
│   ├─ RDS 정의
│   ├─ Lambda/ECS 정의
│   ├─ IAM 역할 정의
│   └─ 환경 변수 설정
│
├─ 4.1.2.2: 환경 구성 (1.5day)
│   ├─ Dev 환경 구성
│   ├─ Staging 환경 구성
│   ├─ Production 환경 구성
│   └─ 환경별 설정 파일
│
└─ 4.1.2.3: 배포 파이프라인 (1.5day)
    ├─ GitHub Actions 설정
    ├─ CI/CD 파이프라인
    ├─ 자동 테스트 연동
    └─ 자동 배포 설정

산출물:
├─ terraform/*.tf (VPC, RDS, Lambda, IAM)
├─ .github/workflows/*.yml (CI/CD)
├─ .env.dev, .env.staging, .env.prod
└─ DEPLOYMENT_GUIDE.md
```

#### 4.1.3 데이터베이스 마이그레이션
```
ID: 4.1.3
담당: 데이터 엔지니어
기간: 3일 (2026-08-09 ~ 2026-08-11)
선행작업: 4.1.2 완료

세부 작업:
├─ 4.1.3.1: RDS 스키마 생성 (1day)
│   ├─ 마스터 테이블 정의
│   ├─ 인덱스 설정
│   ├─ 파티셔닝 계획
│   └─ create_rds_schema.sql
│
├─ 4.1.3.2: 데이터 로드 (1day)
│   ├─ CSV → RDS 로드
│   ├─ 데이터 검증
│   ├─ load_data_to_rds.py
│   └─ 통계 기록
│
└─ 4.1.3.3: 백업 설정 (1day)
    ├─ 자동 백업 정책
    ├─ 재해복구 계획
    ├─ RTO/RPO 설정
    └─ 백업 테스트

산출물:
├─ create_rds_schema.sql
├─ load_data_to_rds.py
├─ DATABASE_MIGRATION_REPORT.md
└─ BACKUP_STRATEGY.md
```

---

### Task 4.2: FastAPI 서빙 레이어 개발

#### 4.2.1 FastAPI 개발
```
ID: 4.2.1
담당: 백엔드 엔지니어
기간: 5일 (2026-08-15 ~ 2026-08-19)
선행작업: 4.1.2 완료

세부 작업:
├─ 4.2.1.1: 애플리케이션 구조 (1day)
│   ├─ app.py 메인 애플리케이션
│   ├─ models.py (Pydantic 모델)
│   ├─ services.py (비즈니스 로직)
│   ├─ db.py (DB 연결)
│   └─ utils.py (유틸리티)
│
├─ 4.2.1.2: API 엔드포인트 (2days)
│   ├─ POST /api/v1/predict
│   ├─ GET /api/v1/model/info
│   ├─ GET /api/v1/health
│   ├─ POST /api/v1/batch-predict
│   └─ GET /api/v1/prediction-history
│
├─ 4.2.1.3: 입력 검증 (1day)
│   ├─ Pydantic 모델 정의
│   ├─ 범위 검증
│   └─ 타입 검증
│
└─ 4.2.1.4: 예측 로직 (1day)
    ├─ 모델 로드
    ├─ 전처리
    ├─ 예측 생성
    ├─ 신뢰도 계산
    └─ 응답 포맷팅

산출물:
├─ avm_prediction_service/
│   ├─ app.py
│   ├─ models.py
│   ├─ services.py
│   ├─ db.py
│   └─ utils.py
├─ tests/ (단위 테스트)
└─ API_SPECIFICATION.md
```

#### 4.2.2 Docker 컨테이너화
```
ID: 4.2.2
담당: DevOps 엔지니어
기간: 2일 (2026-08-20 ~ 2026-08-21)
선행작업: 4.2.1 완료

세부 작업:
├─ 4.2.2.1: Dockerfile 작성 (1day)
│   ├─ Python 3.11 베이스
│   ├─ 의존성 설치
│   ├─ 모델 파일 포함
│   ├─ 헬스체크 설정
│   └─ 포트 노출
│
└─ 4.2.2.2: ECR 푸시 (1day)
    ├─ Docker 빌드
    ├─ AWS ECR 연결
    ├─ 이미지 푸시
    └─ 태깅 및 버전 관리

산출물:
├─ Dockerfile
├─ .dockerignore
├─ docker-compose.yml
└─ ECR_SETUP.md
```

#### 4.2.3 ECS/Lambda 배포
```
ID: 4.2.3
담당: 인프라 엔지니어
기간: 3일 (2026-08-22 ~ 2026-08-24)
선행작업: 4.2.2 완료

세부 작업:
├─ 4.2.3.1: ECS 클러스터 구성 (1.5day)
│   ├─ 작업 정의 생성
│   ├─ 서비스 정의
│   ├─ 로드 밸런싱
│   └─ Auto-scaling 규칙
│
├─ 4.2.3.2: API Gateway 설정 (1day)
│   ├─ /api/v1/* 라우팅
│   ├─ API Key 인증
│   ├─ Rate limiting
│   └─ CORS 설정
│
└─ 4.2.3.3: 배포 실행 (0.5day)
    ├─ Dev 환경 배포
    ├─ Staging 환경 배포
    └─ Production 환경 배포

산출물:
├─ ecs-task-definition.json
├─ ecs-service-definition.json
├─ api-gateway-config.yml
└─ DEPLOYMENT_STEPS.md
```

#### 4.2.4 성능 테스트
```
ID: 4.2.4
담당: QA 엔지니어
기간: 2일 (2026-08-25 ~ 2026-08-26)
선행작업: 4.2.3 완료

세부 작업:
├─ 4.2.4.1: 단위 테스트 (0.5day)
│   ├─ 입력 검증 테스트
│   ├─ 모델 로드 테스트
│   ├─ 예측 로직 테스트
│   └─ 에러 처리 테스트
│
├─ 4.2.4.2: 통합 테스트 (0.5day)
│   ├─ API 엔드포인트 테스트
│   ├─ DB 연결 테스트
│   └─ 캐싱 테스트
│
└─ 4.2.4.3: 부하 테스트 (1day)
    ├─ 1,000 concurrent users
    ├─ 응답 시간 측정
    ├─ 처리량 측정
    └─ 에러율 측정

산출물:
├─ tests/*.py (테스트 코드)
├─ PERFORMANCE_TEST_REPORT.md
└─ LOAD_TEST_RESULTS.xlsx
```

---

### Task 4.3: 모니터링 및 최적화

#### 4.3.1 모니터링 설정
```
ID: 4.3.1
담당: DevOps 엔지니어
기간: 3일 (2026-08-29 ~ 2026-08-31)
선행작업: 4.2.4 완료

세부 작업:
├─ 4.3.1.1: CloudWatch 설정 (1.5day)
│   ├─ API 응답 시간 추적
│   ├─ 에러율 모니터링
│   ├─ 리소스 사용률
│   ├─ 데이터베이스 성능
│   └─ 커스텀 메트릭
│
├─ 4.3.1.2: 로깅 설정 (1day)
│   ├─ 요청/응답 로깅
│   ├─ 예측 결과 로깅
│   ├─ 에러 로깅
│   ├─ 감사 로그 (audit trail)
│   └─ 로그 저장 (S3)
│
└─ 4.3.1.3: 알림 규칙 (0.5day)
    ├─ 응답 시간 (>1초)
    ├─ 에러율 (>1%)
    ├─ 모델 성능 저하
    └─ 리소스 부족

산출물:
├─ cloudwatch-monitoring.tf
├─ logging-configuration.yaml
├─ alert-rules.json
└─ MONITORING_GUIDE.md
```

#### 4.3.2 성능 최적화
```
ID: 4.3.2
담당: 성능 엔지니어
기간: 3일 (2026-09-01 ~ 2026-09-03)
선행작업: 4.3.1 완료

세부 작업:
├─ 4.3.2.1: 캐싱 전략 (1day)
│   ├─ 모델 캐싱
│   ├─ 결과 캐싱
│   ├─ Redis 도입
│   └─ 캐시 무효화 규칙
│
├─ 4.3.2.2: DB 최적화 (1day)
│   ├─ 쿼리 최적화
│   ├─ 인덱스 추가
│   ├─ 연결 풀링
│   └─ 성능 모니터링
│
└─ 4.3.2.3: API 최적화 (1day)
    ├─ 배치 예측 지원
    ├─ 비동기 처리
    ├─ 결과 압축
    └─ 성능 개선 측정

산출물:
├─ caching-strategy.py
├─ db-optimization.sql
├─ api-optimization.py
└─ PERFORMANCE_OPTIMIZATION_REPORT.md
```

#### 4.3.3 운영 문서화
```
ID: 4.3.3
담당: 기술 문서 작성자
기간: 3일 (2026-09-04 ~ 2026-09-06)
선행작업: 4.3.2 완료

세부 작업:
├─ 4.3.3.1: 운영 매뉴얼 (1.5day)
│   ├─ 시스템 구조 설명
│   ├─ 장애 대응 절차
│   ├─ 성능 튜닝 가이드
│   ├─ 일일 점검 체크리스트
│   └─ 응급 대응 절차
│
├─ 4.3.3.2: API 문서 (1day)
│   ├─ Swagger/OpenAPI 정의
│   ├─ 사용 예제
│   ├─ 에러 코드 문서
│   └─ 응답 예제
│
└─ 4.3.3.3: 운영 가이드 (0.5day)
    ├─ 메트릭 설명
    ├─ 알림 해석
    ├─ 조치 방법
    └─ 에스컬레이션 절차

산출물:
├─ OPERATIONS_MANUAL.md (50+ 페이지)
├─ API_DOCUMENTATION.md
├─ TROUBLESHOOTING_GUIDE.md
├─ DAILY_CHECKLIST.xlsx
└─ swagger.yaml
```

#### 4.3.4 Go-Live 및 최종 검증
```
ID: 4.3.4
담당: 프로젝트 매니저
기간: 7일 (2026-09-08 ~ 2026-09-15)
선행작업: 4.3.3 완료

세부 작업:
├─ 4.3.4.1: SLA 검증 (2days)
│   ├─ 응답시간 <500ms ✓
│   ├─ 동시성 1,000+ req/sec ✓
│   ├─ 가용성 99.9% ✓
│   ├─ 정확성 R² ≥ 0.85 ✓
│   └─ 검증 보고서
│
├─ 4.3.4.2: 보안 검증 (1day)
│   ├─ API 인증 확인
│   ├─ 데이터 암호화 확인
│   ├─ 감사 로그 확인
│   └─ 보안 테스트
│
├─ 4.3.4.3: 사용자 수락 테스트 (2days)
│   ├─ 실제 사용 시나리오
│   ├─ 비즈니스 요구사항 확인
│   ├─ 최종 승인
│   └─ UAT 보고서
│
└─ 4.3.4.4: Go-Live (2days)
    ├─ 프로덕션 배포
    ├─ 트래픽 전환
    ├─ 모니터링 시작
    ├─ 지원 팀 교육
    └─ 인수인계 완료

산출물:
├─ SLA_VERIFICATION_REPORT.md
├─ SECURITY_AUDIT_REPORT.md
├─ UAT_REPORT.md
├─ GO_LIVE_CHECKLIST.xlsx
└─ HANDOVER_DOCUMENTATION.md
```

---

## 요약

### 전체 작업량

```
Phase 3: 운영 데이터 통합
├─ Task 3.1: 6일 (6명)
├─ Task 3.2: 7일 (4명)
├─ Task 3.3: 5일 (3명)
└─ Task 3.4: 14일 (5명)
소계: 5주, 최대 5명 병렬

Phase 4: 클라우드 배포
├─ Task 4.1: 8일 (3명)
├─ Task 4.2: 12일 (4명)
├─ Task 4.3: 13일 (4명)
└─ Task 4.4: 7일 (3명)
소계: 6주, 최대 4명 병렬

전체: 11주, 평균 4-5명
```

### 주요 마일스톤

```
2026-07-07: Phase 3.2 완료 (데이터 정제)
2026-07-14: Phase 3.3 완료 (마스터 데이터)
2026-07-28: Phase 3.4 완료 (모델 검증 & Phase 4 승인)
2026-08-14: Phase 4.1 완료 (인프라 구성)
2026-08-26: Phase 4.2 완료 (API 배포)
2026-09-06: Phase 4.3 완료 (모니터링 설정)
2026-09-15: Go-Live & 인수인계 완료
```

---

**작성 일자**: 2026-06-24  
**버전**: v1.0  
**상태**: 검토 대기
