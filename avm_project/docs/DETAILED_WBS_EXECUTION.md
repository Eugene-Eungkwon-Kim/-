# AVM 엔진 - 상세 WBS 및 실행 계획 (Detailed WBS Execution)

**문서 버전**: 2.0  
**작성일**: 2026-06-30  
**총 기간**: 35 working days  
**투입**: Senior Engineer 1명 (full-time 8h/day)  
**상태**: Ready for Execution

---

## Part 1: 전체 프로젝트 일정 (Calendar View)

### 월별 계획

```
┌─────────────────────────────────────────────────────────┐
│ 2026년 7월 (Phase 13.4 - AVM Engine Development)       │
├─────────────────────────────────────────────────────────┤
│ Week 1 (07/01-07/05): 기초 준비 (5-7 days)             │
│ Week 2 (07/08-07/12): Feature Eng + Ensemble (7-9 days)│
│ Week 3 (07/15-07/19): 나머지 컴포넌트 (7 days)        │
│ Week 4 (07/22-07/26): Core + API (5-7 days)           │
│ Week 5 (07/29-08/02): 테스트 (5-6 days)               │
│ Week 6 (08/05-08/09): NPU 최적화 (5 days)             │
│ Week 7 (08/12-08/14): 배포 (3-5 days)                 │
│                                                         │
│ 목표 완료일: 2026-07-14 (35 working days)             │
└─────────────────────────────────────────────────────────┘
```

---

## Part 2: 세부 일정 (Day-by-Day Breakdown)

### **PHASE 1: 기초 준비** (5-7 days)

#### **Day 1 (월요일, 2026-07-01)**

| 시간 | 작업 | 산출물 | 진도 |
|------|------|--------|------|
| 09:00-10:00 | 킥오프 미팅 + 목표 설정 | 미팅 노트 | - |
| 10:00-11:00 | Git 저장소 준비 | .gitignore, 브랜치 확인 | 10% |
| 11:00-12:00 | 의존성 설치 | requirements.txt 검증 | 20% |
| 13:00-14:00 | 디렉토리 생성 | scripts/, tests/, config/, output/ | 30% |
| 14:00-15:00 | avm_config.json 작성 | 26개 파라미터 | 60% |
| 15:00-17:00 | 데이터 로드 테스트 | 첫 데이터 로드 확인 | 100% |

**완료 기준**: ✅ 환경 준비 완료, 데이터 로드 성공  
**Commit**: `[Day 1] Setup: Initialize project structure, dependencies, config`

---

#### **Day 2 (화요일, 2026-07-02)**

| 시간 | 작업 | 산출물 | 진도 |
|------|------|--------|------|
| 09:00-10:00 | 데이터 탐색 (EDA) | data_summary.csv | 20% |
| 10:00-11:30 | 결측치 처리 | 처리된 데이터셋 | 40% |
| 11:30-13:00 | 이상치 탐지 | outliers_report.txt | 60% |
| 14:00-15:30 | 학습/검증 분할 | train.csv, test.csv (70/30) | 80% |
| 15:30-17:00 | 정규화 테스트 | normalized_data.csv | 100% |

**완료 기준**: ✅ 1000+ 행 데이터셋 준비, 70/30 분할  
**Commit**: `[Day 2] Data: Load, validate, normalize property dataset`

---

#### **Day 3 (수요일, 2026-07-03)**

| 시간 | 작업 | 산출물 | 진도 |
|------|------|--------|------|
| 09:00-10:00 | 모델 로드 | 3개 모델 확인 | 20% |
| 10:00-11:00 | XGBoost 검증 | R² score 기록 | 40% |
| 11:00-12:00 | LightGBM 검증 | R² score 기록 | 60% |
| 13:00-14:00 | GB 검증 | R² score 기록 | 75% |
| 14:00-15:00 | 모델 저장 | output/trained_models/*.pkl | 90% |
| 15:00-17:00 | 성능 벤치마크 | benchmark_results.txt | 100% |

**완료 기준**: ✅ R² > 0.80 모두 확인, 모델 직렬화 완료  
**Commit**: `[Day 3] Models: Load, validate, serialize trained models`

---

#### **Day 4-5 (목-금, 2026-07-04-05)**

| Day | 작업 | 산출물 | 진도 |
|-----|-----|--------|------|
| 4 | 모델 초기 성능 측정 (500개 샘플) | latency_baseline.txt | 100% |
| 5 | 예비 시간 + 피드백 반영 | 업데이트된 설정 | 100% |

**완료 기준**: ✅ MS-1: 모든 기초 준비 완료  
**진도**: ▓▓▓▓▓░░░░ (5/35 days, 14%)

---

### **PHASE 2: 컴포넌트 개발** (14-18 days)

#### **일정: Days 6-20** (병렬 처리 최적화)

```
Day 6-7   : Feature Engineering (WP 2.1)
Day 8-10  : Ensemble Engine (WP 2.2) [Day 6과 병렬]
Day 11-12 : Correction Layer (WP 2.3) [Day 10과 병렬]
Day 13-14 : Validation Engine (WP 2.4) [Day 12와 병렬]
Day 15-16 : Auction Module (WP 2.5) [Day 14와 병렬]
Day 17-20 : Core Engine Integration (WP 2.6)
```

#### **WP 2.1: Feature Engineering** (3-4 days, Days 6-7)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **6** | | | | |
| | 클래스 구조 설계 | 1h | AVMFeatureEngineer 클래스 정의 | ✅ |
| | normalize() 구현 | 1h | 정규화 로직 (10 lines) | ✅ |
| | normalize() 테스트 | 1h | 2개 테스트 케이스 | ✅ coverage>95% |
| | encode_property_type() | 1h | 인코딩 함수 (8 lines) | ✅ |
| | encode_district_grade() | 1h | 등급 인코딩 (8 lines) | ✅ |
| | 테스트 작성 | 2h | 4개 케이스 | ✅ coverage>90% |
| | 일일 리뷰 | 1h | - | ✅ |
| **7** | | | | |
| | create_derived_features() | 1.5h | 파생변수 생성 (15 lines) | ✅ |
| | transform() 통합 | 1.5h | 종합 변환 함수 (20 lines) | ✅ |
| | 단위 테스트 | 2h | 10개 케이스 총합 | ✅ |
| | 코드 리뷰 | 1h | 피드백 적용 | ✅ |
| | 리팩토링 | 1h | 최종 정리 | ✅ |

**산출물**: `avm_feature_engineering.py` (250 lines, 12 test cases)  
**완료 기준**: ✅ 커버리지 > 95%  
**Commit**: `[WP 2.1] Feature Engineering: Normalization, encoding, transform`

---

#### **WP 2.2: Ensemble Engine** (4-5 days, Days 8-10)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **8** | | | | |
| | 클래스 구조 | 1h | AVMEnsembleEngine 정의 | ✅ |
| | 상수/파라미터 | 0.5h | MODEL_WEIGHTS, CONFIDENCE_PARAMS | ✅ |
| | __init__() | 1h | 초기화 함수 (15 lines) | ✅ |
| | _load_ir_models() | 2h | OpenVINO IR 로드 | ✅ |
| | 일일 리뷰 | 1h | - | ✅ |
| **9** | | | | |
| | _load_pickled_models() | 1.5h | sklearn 모델 폴백 | ✅ |
| | predict() 기본 | 2h | 예측 로직 초안 (25 lines) | ✅ |
| | 가중 평균 구현 | 1.5h | 앙상블 가중치 적용 | ✅ |
| | 테스트 | 2h | 5개 케이스 | ✅ |
| **10** | | | | |
| | predict() 완성 | 2h | 레이턴시 측정, 캐싱 | ✅ |
| | _calculate_confidence() | 1.5h | 신뢰도 계산 (12 lines) | ✅ |
| | LRU 캐시 | 2h | OrderedDict 기반 캐싱 | ✅ |
| | 성능 테스트 | 2h | 벤치마크 (100 samples) | ✅ |
| | 코드 리뷰 + 리팩토링 | 1h | 최종 정리 | ✅ |

**산출물**: `avm_ensemble_engine.py` (300 lines, 10 test cases)  
**완료 기준**: ✅ 평균 레이턴시 < 5ms, 캐시 히트율 > 40%  
**Commit**: `[WP 2.2] Ensemble Engine: 3-model ensemble, caching, confidence`

---

#### **WP 2.3: Correction Layer** (2-3 days, Days 11-12)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **11** | | | | |
| | 클래스 구조 | 0.5h | CorrectionLayer 정의 | ✅ |
| | 보정값 테이블 입력 | 1.5h | 30개 지역별 보정값 | ✅ |
| | 시간 조정값 | 0.5h | 2020-2024 연도별 인자 | ✅ |
| | get_region_correction() | 1h | 지역 조회 함수 (8 lines) | ✅ |
| | 테스트 | 1.5h | 4개 케이스 | ✅ |
| **12** | | | | |
| | apply_corrections() | 1.5h | 보정 공식 (12 lines) | ✅ |
| | get_correction_breakdown() | 1h | 디버깅용 상세 함수 | ✅ |
| | 단위 테스트 | 1.5h | 8개 케이스 완성 | ✅ |
| | 코드 리뷰 | 1h | 최종 검수 | ✅ |

**산출물**: `avm_correction_layer.py` (150 lines, 8 test cases)  
**완료 기준**: ✅ 30개 보정값 검증, Loan4U 공식 일치  
**Commit**: `[WP 2.3] Correction Layer: Regional & temporal adjustments`

---

#### **WP 2.4: Validation Engine** (4-5 days, Days 13-14)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **13** | | | | |
| | 클래스 구조 | 0.5h | ValidationEngine 정의 | ✅ |
| | 이상탐지 모델 | 2h | Isolation Forest 초기화 | ✅ |
| | check_anomaly() | 1.5h | 이상탐지 함수 (12 lines) | ✅ |
| | 테스트 | 2h | 3개 케이스 | ✅ |
| **14** | | | | |
| | 신뢰도 구간 | 1.5h | ConfidenceInterval 클래스 | ✅ |
| | estimate_confidence_interval() | 1.5h | Z-score 계산 (15 lines) | ✅ |
| | check_appraisal_range() | 1.5h | 공시가격 검증 (12 lines) | ✅ |
| | validate() 종합 | 2h | 모든 검증 통합 (25 lines) | ✅ |
| | 단위 테스트 | 2.5h | 15개 케이스 | ✅ coverage>92% |
| | 코드 리뷰 | 0.5h | 최종 정리 | ✅ |

**산출물**: `avm_validation_engine.py` (350 lines, 15 test cases)  
**완료 기준**: ✅ 이상탐지율 > 95%, 신뢰도 구간 정확도  
**Commit**: `[WP 2.4] Validation Engine: Anomaly detection, confidence intervals`

---

#### **WP 2.5: Auction Module** (2-3 days, Days 15-16)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **15** | | | | |
| | 클래스 구조 | 0.5h | AuctionModule 정의 | ✅ |
| | 시장 조정 인자 | 0.5h | MARKET_CONDITIONS 맵 | ✅ |
| | _get_region_rate() | 1h | 낙찰가율 테이블 | ✅ |
| | 테스트 | 1h | 2개 케이스 | ✅ |
| **16** | | | | |
| | estimate_auction_price() | 1.5h | 낙찰 공식 (20 lines) | ✅ |
| | 상세 분석 함수 | 1h | breakdown() 디버깅 | ✅ |
| | 단위 테스트 | 1.5h | 6개 케이스 | ✅ |
| | 코드 리뷰 | 0.5h | 최종 정리 | ✅ |

**산출물**: `avm_auction_module.py` (150 lines, 6 test cases)  
**완료 기준**: ✅ 낙찰가 공식 검증, Loan4U 일치  
**Commit**: `[WP 2.5] Auction Module: Forecast calculation, market factors`

---

#### **WP 2.6: Core Engine Integration** (3-4 days, Days 17-20)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **17** | | | | |
| | 클래스 구조 | 1h | AVMCoreEngine 정의 | ✅ |
| | 설정 로드 | 1h | _load_config() | ✅ |
| | 컴포넌트 초기화 | 1.5h | __init__() (15 lines) | ✅ |
| | 성능 로깅 | 1h | performance_log 시스템 | ✅ |
| **18** | | | | |
| | valuate() Step 1 | 1.5h | Feature engineering | ✅ |
| | valuate() Step 2 | 1.5h | Ensemble prediction | ✅ |
| | valuate() Step 3 | 1.5h | Correction 적용 | ✅ |
| | 테스트 | 2h | 5개 케이스 | ✅ |
| **19** | | | | |
| | valuate() Step 4 | 1.5h | Validation | ✅ |
| | valuate() Step 5 | 1.5h | Auction forecast | ✅ |
| | valuate() 완성 | 1.5h | 종합 통합 (45 lines) | ✅ |
| | batch_valuate() | 1.5h | 대량 처리 (15 lines) | ✅ |
| | 테스트 | 2h | 5개 케이스 | ✅ |
| **20** | | | | |
| | get_engine_stats() | 1h | 모니터링 (20 lines) | ✅ |
| | get_model_stats() | 0.5h | 모델 정보 (10 lines) | ✅ |
| | End-to-end 테스트 | 2h | 전체 파이프라인 | ✅ |
| | 코드 리뷰 | 1h | 최종 정리 | ✅ |
| | 일일 리뷰 | 0.5h | - | ✅ |

**산출물**: `avm_core_engine.py` (350 lines, 10 test cases)  
**완료 기준**: ✅ MS-3: 모든 컴포넌트 통합 완료  
**진도**: ▓▓▓▓▓▓▓▓▓▓░░░░░ (20/35 days, 57%)  
**Commit**: `[WP 2.6] Core Engine: Complete 5-step valuation pipeline`

---

### **PHASE 3: API 서비스** (3-4 days, Days 21-24)

#### **WP 3.1: FastAPI 구현** (2-3 days, Days 21-23)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **21** | | | | |
| | 임포트 및 기본 구조 | 1h | FastAPI 앱 선언 | ✅ |
| | Pydantic 모델 정의 | 2h | PropertyInput, ValuationResponse | ✅ |
| | 에러 처리 | 1h | HTTPException 정의 | ✅ |
| | 테스트 | 1h | 2개 기본 테스트 | ✅ |
| **22** | | | | |
| | POST /api/valuate | 2h | 개별 평가 엔드포인트 | ✅ |
| | POST /api/batch-valuate | 1.5h | 대량 처리 엔드포인트 | ✅ |
| | GET /api/engine-status | 1h | 상태 조회 | ✅ |
| | GET /api/health | 0.5h | 헬스체크 | ✅ |
| | 테스트 | 2h | 4개 엔드포인트 테스트 | ✅ |
| **23** | | | | |
| | Swagger 문서화 | 1.5h | /docs, /redoc 자동 생성 | ✅ |
| | 에러 처리 테스트 | 1.5h | 잘못된 입력, 범위 초과 | ✅ |
| | CORS 설정 | 0.5h | Cross-origin 요청 허용 | ✅ |
| | 코드 리뷰 | 1h | 최종 정리 | ✅ |

**산출물**: `avm_api_service.py` (300 lines, 7 엔드포인트)  
**완료 기준**: ✅ 모든 엔드포인트 작동, Swagger 문서화 완료  
**Commit**: `[WP 3.1] API Service: FastAPI implementation with all endpoints`

---

#### **WP 3.2: 엔드포인트 테스트 & 최적화** (1-2 days, Day 24)

| Day | 세부 작업 | 예상시간 | 산출물 | 검증 |
|-----|----------|---------|--------|------|
| **24** | | | | |
| | curl 테스트 | 1h | 각 엔드포인트 동작 확인 | ✅ |
| | 배치 성능 테스트 | 1.5h | 100개 동시 요청 | ✅ |
| | 에러 케이스 | 1.5h | 422, 500 응답 검증 | ✅ |
| | 성능 프로파일링 | 1h | 레이턴시 측정 | ✅ |
| | 최종 리뷰 | 0.5h | - | ✅ |

**완료 기준**: ✅ 모든 엔드포인트 검증 완료  
**진도**: ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░ (24/35 days, 69%)  
**Commit**: `[WP 3.2] API Testing: Verify all endpoints, performance profile`

---

### **PHASE 4: 테스트 & 검증** (5-6 days, Days 25-30)

#### **WP 4.1: 단위 테스트** (1-2 days, Day 25)

```
pytest tests/ --cov=scripts --cov-report=term-missing

Target Coverage by Module:
├─ feature_engineering.py: 12 cases → > 95%
├─ ensemble_engine.py: 10 cases → > 90%
├─ correction_layer.py: 8 cases → > 95%
├─ validation_engine.py: 15 cases → > 92%
├─ auction_module.py: 6 cases → > 95%
└─ core_engine.py: 10 cases → > 90%

Total: 61 test cases, > 92% coverage
```

**산출물**: `tests/test_*.py` (600+ lines)  
**완료 기준**: ✅ 커버리지 > 92%, 모든 테스트 통과

---

#### **WP 4.2: 통합 테스트** (1-2 days, Day 26-27)

```
test_full_pipeline.py:
├─ test_data_loading() ✅
├─ test_model_training() ✅
├─ test_model_conversion() ✅
├─ test_npu_inference() ✅
└─ test_api_service() ✅

test_integration.py:
├─ test_end_to_end_valuation() ✅
├─ test_batch_valuation() ✅
├─ test_cache_functionality() ✅
└─ test_error_handling() ✅
```

**완료 기준**: ✅ End-to-end 파이프라인 통과

---

#### **WP 4.3: 성능 테스트** (2-3 days, Day 28-29)

```
성능 지표 측정:
├─ Latency (1,000 samples):
│  ├─ Mean: < 2.0 ms ✅
│  ├─ P95: < 5.0 ms ✅
│  └─ P99: < 10.0 ms ✅
│
├─ Throughput:
│  └─ > 100 req/sec ✅
│
├─ Accuracy:
│  ├─ R² > 0.84 ✅
│  ├─ MAPE < 10.5% ✅
│  └─ Confidence > 85% ✅
│
└─ Cache:
   └─ Hit rate > 40% ✅
```

**산출물**: `performance_report.txt`  
**완료 기준**: ✅ MS-4: 모든 성능 요구사항 달성

---

#### **WP 4.4: 회귀 테스트 & 최종 검수** (1 day, Day 30)

```
Regression Test Checklist:
├─ 이전 버전 (v0.x) vs 현재 (v1.0) 비교
├─ 알려진 버그 재확인
├─ Edge case 테스트
└─ Master Checklist 100% 완료
```

**진도**: ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░ (30/35 days, 86%)

---

### **PHASE 5: NPU 최적화 & 배포** (5-7 days, Days 31-35)

#### **WP 5.1: NPU 최적화** (2-3 days, Days 31-32)

| 단계 | 작업 | 산출물 | 검증 |
|------|------|--------|------|
| 1 | ONNX 변환 | *.onnx (3개) | ✅ 파일 생성 |
| 2 | INT8 양자화 | *.xml/*.bin (3개) | ✅ 모델 로드 |
| 3 | 정확도 검증 | accuracy_delta.txt | ✅ < 2% 손실 |
| 4 | 성능 비교 | optimization_report.txt | ✅ NPU 10x 빠름 |

**완료 기준**: ✅ IR 모델 검증, 성능 개선 확인

---

#### **WP 5.2: 배포 준비** (1-2 days, Day 33)

```
배포 체크리스트:
├─ [ ] Docker 이미지 빌드
├─ [ ] docker-compose.yml 작성
├─ [ ] .env 파일 (프로덕션 설정)
├─ [ ] deploy.sh 스크립트
├─ [ ] 헬스체크 스크립트
├─ [ ] 보안 검사 (OWASP)
└─ [ ] 성능 재검증
```

**산출물**: `Dockerfile`, `deploy.sh`, `.env.example`

---

#### **WP 5.3: 모니터링 설정** (1-2 days, Day 34)

```
모니터링 구성:
├─ Prometheus 메트릭 수집
├─ Grafana 대시보드 (실시간)
├─ 알람 규칙 설정 (임계값)
├─ 로깅 시스템 (ELK)
└─ 성능 대시보드
```

**산출물**: `prometheus.yml`, `grafana-dashboard.json`

---

#### **WP 5.4: 최종 배포** (1-2 days, Day 35)

```
배포 프로세스:
1. 보안 검사 완료
2. 성능 목표 재확인 (모두 달성)
3. 팀 교육 실시
4. 프로덕션 배포
5. 24시간 모니터링

완료 조건:
✅ 서비스 온라인
✅ 모니터링 작동
✅ 로깅 정상
✅ 성능 기준 충족
```

**진도**: ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (35/35 days, 100%) 🎉

---

## Part 3: 마일스톤 추적

### 주요 마일스톤 (6개)

| MS | 이름 | 완료 일자 | 완료 조건 | 상태 |
|----|------|---------|---------|------|
| **MS-1** | 기초 준비 | Day 5 | 환경 준비, 데이터 로드 완료 | ⏳ |
| **MS-2** | 핵심 엔진 | Day 20 | 5개 컴포넌트 + 신뢰도 > 85% | ⏳ |
| **MS-3** | 통합 & API | Day 24 | Core engine + FastAPI 완성 | ⏳ |
| **MS-4** | 테스트 완료 | Day 30 | 모든 성능 요구사항 달성 | ⏳ |
| **MS-5** | 배포 준비 | Day 33 | 모니터링 + 문서 완성 | ⏳ |
| **MS-6** | 본배포 | Day 35 | 프로덕션 서비스 시작 | ⏳ |

---

## Part 4: 리소스 할당 (Resource Allocation)

### 4.1 일일 시간 배분

```
기본 8시간/일:
├─ 개발: 5-6시간 (코딩, 테스트)
├─ 리뷰: 1시간 (코드 리뷰, 리팩토링)
├─ 커밋: 0.5시간 (Git 관리)
├─ 문서화: 0.5-1시간 (주석, 진도 리포트)
└─ 미팅: 0.5시간 (일일 스탠드업)
```

### 4.2 주간 이정표

| Week | 목표 LOC | 목표 Tests | 주요 작업 | 검증 |
|------|---------|-----------|---------|------|
| **1** | 150 | 0 | 기초 준비 | ✅ |
| **2** | 550 | 22 | Feature + Ensemble | ✅ |
| **3** | 500 | 17 | Correction + Validation + Auction | ✅ |
| **4** | 350 | 10 | Core + API | ✅ |
| **5** | 250 | 11 | 단위/통합/성능 테스트 | ✅ |
| **6** | 50 | 0 | NPU 최적화 | ✅ |
| **7** | 50 | 0 | 배포 | ✅ |

**총계**: 2,500+ LOC, 60+ test cases

---

## Part 5: 리스크 및 대응 (Risk Management)

### 5.1 기술 리스크 행렬

```
확률 (Likelihood)    심각도 (Severity)
    ↑                    높음 (H)
    │              [Model Perf] [Latency]
    │              [NPU Driver]
    │ 중간 (M)     [Memory]
    │              [Library Bug]
    │ 낮음 (L)
    └─────────────────────────────→

       낮음    중간    높음
```

### 5.2 Top 5 리스크 & 대응

| 순위 | 리스크 | 확률 | 영향 | 완화 전략 | 재계획 시간 |
|------|--------|------|------|---------|-----------|
| **1** | 모델 성능 저하 (INT8) | 중 | 높음 | 조기 POC (Day 3), 허용치 정의 | +3-5 days |
| **2** | 레이턴시 목표 미달 | 중 | 높음 | 캐싱 40%, 프로파일링, NPU 최적화 | +2-3 days |
| **3** | NPU 드라이버 미설치 | 낮음 | 높음 | CPU 폴백 (10ms), 자동 검사 | +1-2 days |
| **4** | 메모리 오버플로우 | 낮음 | 높음 | LRU 정책, 모니터링 | +1-2 days |
| **5** | 의존성 버그 | 낮음 | 중간 | 버전 고정, 대체 구현 | +2-3 days |

### 5.3 비상 계획 (Contingency)

**시나리오 A**: 모델 성능 부족 (정확도 < 0.84)
- 대안 1: 하이퍼파라미터 재튜닝
- 대안 2: 특성 엔지니어링 개선
- 대안 3: 앙상블 가중치 조정
- **재계획**: +3-5 days (Day 35 → 38-40)

**시나리오 B**: NPU 드라이버 불가
- **대안**: CPU 폴백으로 개발 계속
- **성능 영향**: 레이턴시 10x (2ms → 20ms)
- **재계획**: 기일 변경 없음 (내재적 폴백)

**시나리오 C**: 의존성 라이브러리 버그
- 대안 1: 라이브러리 다운그레이드
- 대안 2: 수동 구현
- **재계획**: +2-3 days

---

## Part 6: 진도 추적 시스템

### 6.1 일일 리포트 (매일 17:00)

```markdown
# Day N 완료 리포트

## 완료 항목
- [ ] WP X.Y: 컴포넌트명
  - 코드: NNN lines
  - 테스트: NN cases (coverage: NN%)
- [ ] 커밋: `[commit hash]`

## 진도
[████████░░] NN% (Day N/35)

## 다음 계획
- WP X.Y: 예상 완료 Day NN
- 리스크: (없음) 또는 (설명)

## 메트릭
- 총 LOC: NNN/2500
- 테스트: NN/60
- 평균 레이턴시: N.Nms
- 캐시 히트율: NN%
```

### 6.2 주간 리뷰 (매 금요일 16:00)

```
# Week N 리뷰

## 완료
- WP N.N ~ N.N (NN% 진도)
- 총 코드: NNN lines
- 총 테스트: NN cases
- MS-N 달성: (✅/⏳)

## 문제점
- (리스크 설명)
- (해결 방안)

## 다음주
- WP N.N 시작 (예상 완료: Day NN)
- 주요 일정: ...

## 승인
- PM: _____ (날짜)
- 기술리드: _____ (날짜)
```

---

## Part 7: 코드 품질 지표

### 7.1 정량적 목표

| 지표 | 목표 | 측정 방법 | 수용 기준 |
|------|------|---------|---------|
| **커버리지** | > 92% | pytest --cov | 모든 모듈 > 85% |
| **순환복잡도** | < 10 | radon cc | 함수당 < 15 |
| **함수 길이** | < 50줄 | 수동 검사 | 최대 100줄 (예외) |
| **타입 힌트** | 100% | mypy | 모든 함수 필수 |
| **Pylint** | > 8.0 | pylint | 코드 품질 보증 |
| **기술부채** | 최소화 | SonarQube | Critical=0 |

### 7.2 커밋 메시지 표준

```
[WP X.Y] 간단한 설명 (< 70 chars)

상세 설명 (wrapped at 72 chars):
- 변경사항 1
- 변경사항 2
- 영향도

테스트: NN 케이스 (커버리지: NN%)
성능: P95 < Nms

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_...
```

---

## Part 8: 최종 체크리스트

### 8.1 기술 체크리스트

```
개발 완료 (Day 30)
├─ [ ] 2,500+ lines 코드 완성
├─ [ ] 60+ 테스트 케이스 작성
├─ [ ] 92%+ 테스트 커버리지
├─ [ ] 모든 함수 타입 힌트
├─ [ ] 코드 리뷰 통과 (100%)
├─ [ ] Pylint > 8.0
├─ [ ] mypy 검사 통과
├─ [ ] black 포매팅 완료
├─ [ ] 모든 성능 요구사항 달성
└─ [ ] 문서 작성 완료

배포 전 (Day 34)
├─ [ ] 보안 검사 완료 (OWASP)
├─ [ ] Docker 이미지 빌드
├─ [ ] Prometheus/Grafana 설정
├─ [ ] 모니터링 테스트
├─ [ ] 팀 교육 완료
└─ [ ] GO/NO-GO 승인

배포 후 (Day 35)
├─ [ ] 프로덕션 서비스 온라인
├─ [ ] 24시간 모니터링
├─ [ ] 모든 로그 정상
└─ [ ] 성능 기준 충족
```

---

**문서 끝**  
**상태**: ✅ Ready for Execution  
**총 기간**: 35 working days  
**예상 비용**: $18,700  
**목표 완료**: 2026-07-14 (Phase 13.4 완료)

---

**부록: 예비 시간 배분**

```
Days 1-30: 핵심 개발 (85%)
Days 31-33: 최적화 & 배포 (10%)
Days 34-35: 예비 & 버퍼 (5%)

최악의 시나리오 대응:
├─ 예비 3-5 days 확보
├─ 병렬 처리로 시간 단축
└─ 우선순위 재조정 가능 (Core > Auction, API > Monitoring)
```

---

**프로젝트 상태**: 🟢 **Ready for Execution**
