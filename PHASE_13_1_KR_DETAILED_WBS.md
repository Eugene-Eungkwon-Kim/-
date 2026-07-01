# Phase 13.1-KR 상세 WBS
## Work Breakdown Structure: 한국 실거래 데이터 수집 & GPU 모델 학습

**프로젝트**: Loan4U AVM Phase 13.1-KR  
**기간**: 2026-07-01 ~ 2026-07-21 (21일, 3주)  
**팀**: Claude Agent (Data/ML) + 사용자 (협력)  
**총 투입시간**: 90h (3명주)

---

## 📋 WBS 계층 구조

```
Phase 13.1-KR (0)
├─ 13.1.1 Data Ingestion (1주, 40h)
│   ├─ 13.1.1.1 data.go.kr API 연동
│   ├─ 13.1.1.2 MOLIT CSV 수집
│   ├─ 13.1.1.3 데이터 병합 & 정제
│   └─ 13.1.1.4 QA 검증
│
├─ 13.2 Feature Engineering & Preparation (주1-2, 25h)
│   ├─ 13.2.1 기본 특성 추출 (10개)
│   ├─ 13.2.2 파생 특성 생성 (35개)
│   ├─ 13.2.3 정규화 & 스케일링
│   └─ 13.2.4 Train/Test Split
│
├─ 13.3 GPU Model Training (주2, 30h)
│   ├─ 13.3.1 XGBoost 학습 (GPU)
│   ├─ 13.3.2 LightGBM 학습 (GPU)
│   ├─ 13.3.3 Gradient Boosting 학습
│   └─ 13.3.4 모델 성능 비교
│
├─ 13.4 Model Validation & Optimization (주2-3, 20h)
│   ├─ 13.4.1 Cross-validation 실행
│   ├─ 13.4.2 하이퍼파라미터 튜닝
│   ├─ 13.4.3 Feature importance 분석
│   └─ 13.4.4 최종 모델 선정
│
├─ 13.5 Model Conversion & Deployment (주3, 15h)
│   ├─ 13.5.1 ONNX 변환
│   ├─ 13.5.2 OpenVINO IR 컴파일
│   ├─ 13.5.3 NPU 배포 & 테스트
│   ├─ 13.5.4 API 서비스 구현
│   └─ 13.5.5 자동 재학습 파이프라인
│
└─ 13.6 Finalization & Documentation (주3, 5h)
    ├─ 13.6.1 성능 보고서 작성
    ├─ 13.6.2 배포 가이드 작성
    └─ 13.6.3 운영 매뉴얼 작성
```

---

## 📅 Week 1: Data Ingestion (2026-07-01 ~ 2026-07-07)

### Task 13.1.1: data.go.kr API 연동

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.1.1.1 | API Key 신청 | data.go.kr 공공데이터 포털 가입 & 승인 | 2h | - | Agent | 🟡 대기 |
| 13.1.1.2 | API 문서 학습 | RESTful API 명세 분석 (rate limit, pagination) | 3h | 13.1.1.1 | Agent | 🟡 대기 |
| 13.1.1.3 | Python 수집 모듈 | data_collector.py: 실거래/건축물/공시지가 API 호출 | 8h | 13.1.1.2 | Agent | 🟡 대기 |
| 13.1.1.4 | 부동산 실거래 수집 | 2026-04월~06월 거래정보 30K 레코드 수집 | 10h | 13.1.1.3 | Agent | 🟡 대기 |
| 13.1.1.5 | 건축물 정보 수집 | 공시지가/건축물 정보 수집 (보조 데이터) | 5h | 13.1.1.3 | Agent | 🟡 대기 |
| 13.1.1.6 | 오류 처리 & 재시도 | Rate limit, timeout, 누락된 페이지 재수집 | 3h | 13.1.1.5 | Agent | 🟡 대기 |
| **소계** | | | **31h** | | | |

**산출물**: `avm_project/data/raw/datagokr_*.csv` (30K+ 레코드)

**위험**: API 지연/오류 → 대안: CSV 배치 다운로드  
**QA 기준**: 30K 레코드 수집, 0 에러, null rate <5%

---

### Task 13.1.2: MOLIT CSV 수집

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.1.2.1 | MOLIT 시스템 접근 | 부동산거래공개시스템 회원가입 & CSV 다운로드 경로 확인 | 2h | - | 사용자 | 🟡 협력 필요 |
| 13.1.2.2 | 지역별 CSV 다운로드 | 서울, 경기, 인천 (3개월 × 3개 지역) | 5h | 13.1.2.1 | Agent | 🟡 대기 |
| 13.1.2.3 | CSV 파싱 모듈 | 인코딩(EUC-KR) 변환, 스키마 검증 | 4h | 13.1.2.2 | Agent | 🟡 대기 |
| 13.1.2.4 | 병렬 다운로드 | 3개 지역 동시 다운로드 (30분 → 10분) | 3h | 13.1.2.3 | Agent | 🟡 대기 |
| **소계** | | | **14h** | | | |

**산출물**: `avm_project/data/raw/molit_*.csv` (20K+ 레코드)

**의존성**: 사용자의 MOLIT 접근 권한 필요  
**QA 기준**: 20K+ 레코드, EUC-KR 정상 변환, 지역별 균형 분포

---

### Task 13.1.3: 데이터 병합 & 정제

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.1.3.1 | 스키마 통일 | data.go.kr + MOLIT 컬럼 매핑 (거래가 → 거래금액) | 2h | 13.1.1.6, 13.1.2.4 | Agent | 🟡 대기 |
| 13.1.3.2 | 데이터 병합 | Concatenate (vertical merge) 50K 레코드 생성 | 2h | 13.1.3.1 | Agent | 🟡 대기 |
| 13.1.3.3 | 중복 제거 | (거래일, 주소, 거래가) 기반 중복 제거 | 3h | 13.1.3.2 | Agent | 🟡 대기 |
| 13.1.3.4 | 결측값 처리 | KNN imputation (위도/경도), 카테고리 fill_forward | 4h | 13.1.3.3 | Agent | 🟡 대기 |
| 13.1.3.5 | 이상치 제거 | 3-시그마 필터링 (거래가: 2억~20억) | 3h | 13.1.3.4 | Agent | 🟡 대기 |
| 13.1.3.6 | Parquet 저장 | 정제된 50K 레코드 → parquet (압축) | 1h | 13.1.3.5 | Agent | 🟡 대기 |
| **소계** | | | **15h** | | | |

**산출물**: `avm_project/data/processed/kr_validated.parquet` (50K 레코드)

**QA 기준**: 50K 레코드, null rate <2%, outlier rate <3%

---

### Task 13.1.4: QA & 검증

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.1.4.1 | 데이터 프로파일링 | 통계 분석 (min, max, mean, std) & 시각화 | 3h | 13.1.3.6 | Agent | 🟡 대기 |
| 13.1.4.2 | 이상 탐지 | 지오코딩 검증 (서울 범위 내 위도/경도) | 2h | 13.1.4.1 | Agent | 🟡 대기 |
| 13.1.4.3 | 데이터 품질 보고 | Completeness, Accuracy, Consistency 지표 산출 | 2h | 13.1.4.2 | Agent | 🟡 대기 |
| **소계** | | | **7h** | | | |

**산출물**: `docs/phase13_kr_data_quality_report.md`

**승인 기준**: 
- ✅ Completeness >95% (null rate <5%)
- ✅ Accuracy >98% (지오코딩 성공)
- ✅ 50K 레코드 확인
- ✅ 사용자 승인

**Week 1 Total**: **67h** → **축약 목표 40h** (병렬화)

---

## 📅 Week 2: Feature Engineering & GPU Training (2026-07-08 ~ 2026-07-14)

### Task 13.2: Feature Engineering

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.2.1 | Base 10 features | 평면적, 건축년도, 층, 지하철거리, 학교거리 등 | 3h | 13.1.4.3 | Agent | 🟡 대기 |
| 13.2.2 | Temporal features | 거래년도, 월, 분기, 건물나이 | 2h | 13.2.1 | Agent | 🟡 대기 |
| 13.2.3 | Location features | 지역 클러스터 (K-means), 거리 인코딩 | 4h | 13.2.2 | Agent | 🟡 대기 |
| 13.2.4 | Market features | 지역별 월평균가, 가격추이, 물량 | 3h | 13.2.3 | Agent | 🟡 대기 |
| 13.2.5 | Categorical encoding | One-hot (용도), target encoding (법정동) | 3h | 13.2.4 | Agent | 🟡 대기 |
| 13.2.6 | Interaction features | 면적×나이, 나이², 면적×위도 등 | 3h | 13.2.5 | Agent | 🟡 대기 |
| 13.2.7 | Normalization | StandardScaler (train fit, test transform) | 2h | 13.2.6 | Agent | 🟡 대기 |
| 13.2.8 | Train/Test split | 80/20 temporal split (시간순) | 1h | 13.2.7 | Agent | 🟡 대기 |
| **소계** | | **45 features** | **21h** | | | |

**산출물**: 
- `avm_project/data/processed/kr_features_45.pkl` (50K×45)
- `avm_project/data/processed/kr_target.pkl` (50K)
- `avm_project/data/processed/train_indices.pkl` (40K)
- `avm_project/data/processed/test_indices.pkl` (10K)

---

### Task 13.3: GPU Model Training

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.3.1 | XGBoost 학습 | GPU (tree_method=gpu_hist) - 50K 레코드 | 15h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.1a | - XGBoost 설정 | 하이퍼파라미터 (max_depth=8, lr=0.05) | 2h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.1b | - 학습 실행 | 15분 예상 (DMatrix 생성, train 루프) | 8h | 13.3.1a | Agent | 🟡 대기 |
| 13.3.1c | - 검증 & 저장 | R², MAPE 계산, 모델 저장 (JSON) | 5h | 13.3.1b | Agent | 🟡 대기 |
| 13.3.2 | LightGBM 학습 | GPU (device_type=gpu) - 빠른 학습 | 12h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.2a | - LightGBM 설정 | 하이퍼파라미터 (num_leaves=31, lr=0.05) | 2h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.2b | - 학습 실행 | 8분 예상 (빠른 학습) | 5h | 13.3.2a | Agent | 🟡 대기 |
| 13.3.2c | - 검증 & 저장 | R², MAPE 계산, 모델 저장 (.txt) | 5h | 13.3.2b | Agent | 🟡 대기 |
| 13.3.3 | Gradient Boosting 학습 | CPU fallback (sklearn) | 10h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.3a | - GB 설정 | 하이퍼파라미터 (n_estimators=500, lr=0.05) | 1h | 13.2.8 | Agent | 🟡 대기 |
| 13.3.3b | - 학습 실행 | 30분 예상 (CPU) | 7h | 13.3.3a | Agent | 🟡 대기 |
| 13.3.3c | - 검증 & 저장 | R², MAPE 계산, joblib 저장 | 2h | 13.3.3b | Agent | 🟡 대기 |
| 13.3.4 | 모델 성능 비교 | 3개 모델 평가표, 최적 모델 선정 | 3h | 13.3.1c, 13.3.2c, 13.3.3c | Agent | 🟡 대기 |
| **소계** | | **3 models trained** | **40h** | | | |

**산출물**:
- `avm_project/models/phase13_kr/xgboost_kr.json` (100 MB)
- `avm_project/models/phase13_kr/lightgbm_kr.txt` (80 MB)
- `avm_project/models/phase13_kr/gradient_boosting_kr.pkl` (150 MB)
- `models_comparison.csv` (성능표)

**성능 기준** (최소):
- ✅ R² > 0.84
- ✅ MAPE < 10.5%
- ✅ RMSE < 200만원

**병렬화 가능**: XGBoost + LightGBM 동시 학습 → 40h → 25h 단축

---

### Task 13.4: Model Validation & Optimization (주2-3)

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.4.1 | Cross-validation | 5-fold CV (각 fold별 R², MAPE 기록) | 5h | 13.3.4 | Agent | 🟡 대기 |
| 13.4.2 | 하이퍼파라미터 튜닝 | GridSearch/RandomSearch (depth, lr, leaves) | 8h | 13.4.1 | Agent | 🟡 대기 |
| 13.4.2a | - XGBoost 튜닝 | max_depth: 6-10, lr: 0.01-0.1 | 4h | 13.4.1 | Agent | 🟡 대기 |
| 13.4.2b | - LightGBM 튜닝 | num_leaves: 20-50, lr: 0.01-0.1 | 4h | 13.4.1 | Agent | 🟡 대기 |
| 13.4.3 | Feature importance | 상위 10개 feature 추출 & 시각화 | 3h | 13.4.2 | Agent | 🟡 대기 |
| 13.4.4 | 최종 모델 선정 | R² 최고 모델 결정 (LightGBM likely) | 2h | 13.4.3 | Agent | 🟡 대기 |
| 13.4.5 | 성능 보고서 | 상세 검증 리포트 작성 | 2h | 13.4.4 | Agent | 🟡 대기 |
| **소계** | | **Best model selected** | **20h** | | | |

**산출물**: 
- `docs/phase13_kr_model_validation_report.md`
- `best_model_path`: `models/phase13_kr/lightgbm_kr.txt`

**승인 기준**: R² ≥ 0.84, MAPE ≤ 10.5%

---

## 📅 Week 3: Deployment & Finalization (2026-07-15 ~ 2026-07-21)

### Task 13.5: Model Conversion & Deployment

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.5.1 | ONNX 변환 | Best model → ONNX format (scikit-learn용) | 2h | 13.4.4 | Agent | 🟡 대기 |
| 13.5.2 | OpenVINO 컴파일 | ONNX → OpenVINO IR (XML + BIN) | 2h | 13.5.1 | Agent | 🟡 대기 |
| 13.5.2a | - FP32 컴파일 | 전체 정밀도 (100 MB 모델) | 1h | 13.5.1 | Agent | 🟡 대기 |
| 13.5.2b | - INT8 양자화 | 정수 양자화 (10-20 MB, 최소 손실) | 1h | 13.5.1 | Agent | 🟡 대기 |
| 13.5.3 | NPU 배포 | OpenVINO runtime 초기화, 하드웨어 테스트 | 3h | 13.5.2b | Agent | 🟡 대기 |
| 13.5.3a | - NPU 감지 | 온보드 NPU 드라이버 확인 | 1h | 13.5.2b | Agent | 🟡 대기 |
| 13.5.3b | - 추론 테스트 | 단일 & 배치 추론, 지연시간 측정 | 2h | 13.5.3a | Agent | 🟡 대기 |
| 13.5.4 | API 서비스 구현 | FastAPI (POST /valuate, GET /health) | 5h | 13.5.3b | Agent | 🟡 대기 |
| 13.5.4a | - API 엔드포인트 | /valuate (단일), /valuate-batch | 3h | 13.5.3b | Agent | 🟡 대기 |
| 13.5.4b | - 문서화 | OpenAPI/Swagger 자동 문서 | 1h | 13.5.4a | Agent | 🟡 대기 |
| 13.5.4c | - 보안 (API Key) | X-API-Key 헤더 검증 | 1h | 13.5.4a | Agent | 🟡 대기 |
| 13.5.5 | 자동 재학습 파이프라인 | APScheduler (월 1회, 1일 2AM) | 3h | 13.5.4c | Agent | 🟡 대기 |
| 13.5.5a | - Scheduler 구성 | Cron 설정, 데이터 수집 자동화 | 1h | 13.5.4c | Agent | 🟡 대기 |
| 13.5.5b | - 성능 비교 & 배포 | 새 모델 vs 기존 모델, 자동 배포 | 1h | 13.5.5a | Agent | 🟡 대기 |
| 13.5.5c | - 알림 시스템 | Slack/Email 알림 (배포 완료/실패) | 1h | 13.5.5b | Agent | 🟡 대기 |
| **소계** | | **Production ready** | **15h** | | | |

**산출물**:
- `avm_project/models/phase13_kr/model_kr.xml` (1-2 MB)
- `avm_project/models/phase13_kr/model_kr.bin` (10-15 MB, INT8)
- `avm_project/scripts/phase13_api_service.py` (FastAPI app)
- `avm_project/scripts/phase13_auto_retrain.py` (Scheduler)

**성능 기준**:
- ✅ NPU 추론 <1ms
- ✅ API 처리량 1000+ req/sec
- ✅ 모든 엔드포인트 통과

---

### Task 13.6: Documentation & Finalization

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.6.1 | 성능 보고서 | 최종 R², MAPE, 비용 요약 | 2h | 13.5.5c | Agent | 🟡 대기 |
| 13.6.2 | 배포 가이드 | 단계별 배포 절차, 롤백 계획 | 2h | 13.5.5c | Agent | 🟡 대기 |
| 13.6.3 | 운영 매뉴얼 | API 사용법, 모니터링, troubleshooting | 1h | 13.5.5c | Agent | 🟡 대기 |
| **소계** | | **Complete documentation** | **5h** | | | |

**산출물**:
- `docs/PHASE_13_1_KR_FINAL_REPORT.md`
- `docs/PHASE_13_1_KR_DEPLOYMENT_GUIDE.md`
- `docs/PHASE_13_1_KR_OPERATIONS_MANUAL.md`

---

## ⏱️ 전체 일정 요약 (Gantt View)

```
Week 1 (Jul 1-7):  Data Ingestion ████████ [67h target → 40h actual]
Week 2 (Jul 8-14): Feature Eng + GPU Training ██████████ [61h target → 50h actual]
Week 3 (Jul 15-21): Deployment + Finalization ███████ [20h target → 20h actual]

Total: 148h planned → 110h optimized (병렬화)

Milestones:
├─ Jul 3: data.go.kr API 연동 ✅
├─ Jul 5: 50K 데이터셋 준비 ✅
├─ Jul 10: R² >0.84 모델 달성 ✅
├─ Jul 15: NPU 배포 완료 ✅
└─ Jul 21: 자동 재학습 파이프라인 운영 ✅
```

---

## 👥 역할 분담 (RACI Matrix)

| Task | Claude Agent | 사용자 | QA | 상태 |
|------|-------------|--------|-----|------|
| 13.1.1 (data.go.kr API) | **Accountable** | Approves | Validates | 🟡 Waiting for approval |
| 13.1.2 (MOLIT CSV) | Responsible | **Accountable** (access) | Validates | 🟡 Needs user action |
| 13.1.3 (Data merge) | **Accountable** | Approves | Validates | 🟡 Ready to start |
| 13.2 (Feature Eng) | **Accountable** | Consults | Validates | 🟡 Ready to start |
| 13.3 (GPU Training) | **Accountable** | Monitors | Validates | 🟡 Ready to start |
| 13.4 (Validation) | **Accountable** | Approves | **QA Lead** | 🟡 Ready to start |
| 13.5 (Deployment) | **Accountable** | Monitors | Validates | 🟡 Ready to start |
| 13.6 (Documentation) | **Accountable** | Reviews | **QA Lead** | 🟡 Ready to start |

**Legend**: R=Responsible, A=Accountable, C=Consulted, I=Informed

---

## 🎯 의존성 그래프 (Dependencies)

```
Start
  │
  ├─ 13.1.1 (data.go.kr) ──┐
  │                        ├─→ 13.1.3 (Merge) ──→ 13.1.4 (QA) ──┐
  └─ 13.1.2 (MOLIT CSV) ───┘                                  │
                                                               ├─→ 13.2 (Features) ──┐
  End (Previous phases)                                        │                     ├─→ 13.3 (Train) ──→ 13.4 (Val) ──→ 13.5 (Deploy) ──→ 13.6 (Doc) → End
                                                               └────────────────────┘
                                                               [병렬 가능]

Critical Path: data.go.kr → Merge → QA → Features → Train(30h) → Val → Deploy
→ Duration: 75 working hours (3 weeks continuous, 1 FTE)
```

---

## 📊 리소스 배분 (Resource Allocation)

### 인력 투입 (90h total)

```
Week 1: 40h (Data Ingestion)
├─ data.go.kr API 연동: 20h
├─ MOLIT CSV 수집: 10h (사용자 협력 2h)
└─ 정제 & QA: 10h

Week 2: 45h (Features + Training)
├─ Feature Engineering: 20h
├─ GPU Training: 25h (병렬)

Week 3: 15h (Deployment + Docs)
├─ Model conversion & NPU: 10h
├─ API & Automation: 4h
└─ Documentation: 5h → 3h (병렬)

Total: 90h (1명주 × 3 = 90h)
```

### 인프라 비용 (선택사항)

| 항목 | 수량 | 비용 | 비고 |
|------|------|------|------|
| GPU (RTX 5050) | 로컬 | $0 | 사용 중 |
| Cloud GPU (대체) | 21일 | $150-200 | 로컬 불가 시 |
| data.go.kr API (upgrade) | 선택사항 | $50/month | 1000→무제한 req/day |
| Storage | <100 MB | $0 | 무료 |
| **Total** | | **$0-200** | |

---

## ✅ 성공 기준 (Acceptance Criteria)

### Phase 13.1.1 (Data Ingestion)
- [ ] 50K 레코드 수집 확인
- [ ] data.go.kr + MOLIT 통합 완료
- [ ] 데이터 품질 (null rate <2%, outlier <3%)
- [ ] CSV/Parquet 저장 완료

### Phase 13.2 (Feature Engineering)
- [ ] 45개 특성 생성 완료
- [ ] 정규화 완료
- [ ] Train/Test split 완료 (80/20, 40K/10K)

### Phase 13.3 (GPU Training)
- [ ] 3개 모델 학습 완료 (XGBoost, LightGBM, GB)
- [ ] 각 모델 저장 확인

### Phase 13.4 (Validation)
- [ ] **R² > 0.84** ✅
- [ ] **MAPE < 10.5%** ✅
- [ ] 5-fold CV 완료
- [ ] Feature importance top 10 추출

### Phase 13.5 (Deployment)
- [ ] ONNX 변환 완료
- [ ] OpenVINO IR 컴파일 완료 (INT8)
- [ ] **NPU 추론 <1ms** ✅
- [ ] API 서비스 구동 (1000+ req/sec)
- [ ] 자동 재학습 스케줄러 활성화

### Phase 13.6 (Documentation)
- [ ] 최종 성능 보고서
- [ ] 배포 가이드
- [ ] 운영 매뉴얼

---

## 🚨 위험 & 대응 (Risk Management)

| 위험 | 확률 | 영향 | 대응 | Owner |
|------|------|------|------|-------|
| data.go.kr API 지연 (rate limit) | 30% | 1주 | CSV 배치 다운로드 병렬 진행 | Agent |
| MOLIT 접근 불가 | 10% | 1주 | 공개 데이터만 사용 (data.go.kr) | 사용자 |
| GPU 메모리 부족 | 20% | 2-3일 | 배치 학습 (1K/batch), feature 축소 | Agent |
| 모델 성능 미달 (R² <0.80) | 15% | 3-5일 | Hyperparameter tuning, feature engineering | Agent |
| 일정 지연 | 40% | 3-7일 | 병렬화, 자동화 강화, 리소스 추가 | Agent + User |

---

## 📋 주간 체크리스트 (Weekly Checklist)

### Week 1 Checkpoint (Jul 7)
```
Data Ingestion:
- [ ] 30K+ data.go.kr 레코드 수집
- [ ] 20K+ MOLIT CSV 다운로드
- [ ] 50K 통합 데이터셋 검증
- [ ] Parquet 저장 완료
- [ ] 사용자 승인
```

### Week 2 Checkpoint (Jul 14)
```
Training:
- [ ] 45 features 생성 완료
- [ ] 3개 모델 학습 완료
- [ ] XGBoost: R² > 0.84 확인
- [ ] LightGBM: R² > 0.85 확인
- [ ] Best model 선정 (권장: LightGBM)
```

### Week 3 Checkpoint (Jul 21)
```
Deployment:
- [ ] ONNX + OpenVINO IR 변환 완료
- [ ] NPU 추론 <1ms 확인
- [ ] API 서비스 구동 (1000+ req/sec)
- [ ] 자동 재학습 스케줄러 활성화
- [ ] 모든 문서 완성 & 승인
- [ ] Go-Live 준비 완료 ✅
```

---

## 📞 연락처 & 에스컬레이션

**주간 진행상황 보고**: 매주 월요일 10:00 KST  
**긴급 이슈**: 즉시 보고 (Slack/Email)  
**승인자**: eugene1108@gmail.com  

**이슈 에스컬레이션**:
1. **Yellow Flag** (소폭 지연, 1-2일): Agent 자체 해결
2. **Red Flag** (주요 지연, 3일+): 사용자 알림 + 계획 수정
3. **Critical** (일정 무너짐, >1주): 사용자 + 리소스 재배분

---

**문서 버전**: 1.0  
**작성일**: 2026-07-01  
**최종 검토**: TBD (사용자 승인 대기)  
**다음 검토**: 2026-07-07 (Week 1 완료 후)

**승인 기록**:
- [ ] 데이터 수집 소스 확정
- [ ] 50K 레코드 규모 수락
- [ ] 3주 일정 확정
- [ ] 리소스 배분 승인
- [ ] GPU/NPU 인프라 준비 완료

---

**Last Updated**: 2026-07-01  
**Author**: Claude Agent (claude-opus-4-8)  
**Status**: 🟡 Ready for Approval
