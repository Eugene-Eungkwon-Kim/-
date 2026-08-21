# 📋 WBS 실행 보고서 (Phase 2-4)

**실행일**: 2026-06-16
**브랜치**: `claude/eloquent-meitner-lqxu9r`
**커밋**: a9f64d4

---

## ✅ 실행 완료 항목

| Phase | 작업 | 상태 | 비고 |
|-------|------|------|------|
| 1.1.6 | Docker 빌드 검증 | ⚠️ 차단 | 원격 환경에 Docker 데몬 부재 (로컬 전용) |
| 1.2~1.4 | Cloud Run 배포 | ⚠️ 차단 | gcloud 미설치 (로컬 전용) |
| 2.1.2 | 자동 재학습 스크립트 | ✅ 완료 | `auto_retraining.py` 작성·검증 |
| 3.4 | 모델 재학습 | ✅ 완료 | 6개 모델 Pipeline 재학습 |
| 3.5 | 모델 승격 | ✅ 완료 | production_model.joblib + SHA256 |
| 4.1.1 | 모델 캐싱 | ✅ 완료 | `PredictionCache` (LRU) |
| 4.2.1 | 신뢰도 추정 | ✅ 완료 | `ConfidenceEstimator` |
| 4.2.2 | 이상탐지 | ✅ 완료 | `AnomalyDetector` |

> Phase 1(Cloud Run 배포)은 코드/스크립트가 모두 준비되어 있으며,
> gcloud가 설치된 로컬 환경에서 `PHASE1_DEPLOYMENT_MANUAL.md`를 따라
> 즉시 실행 가능합니다. 원격 실행 환경의 제약일 뿐 산출물 결함이 아닙니다.

---

## 🔴 실행 중 발견·수정한 프로덕션 버그

기존 158개 테스트는 **엔드포인트를 TestClient로 실제 호출하지 않아서**
아래 런타임 버그들을 모두 놓치고 있었습니다.

### 1. NameError — `/predict` 전면 장애 (CRITICAL)
- `/predict`, `/predict/batch`, `/api/version`이 **정의되지 않은 전역
  `model_metadata`**를 참조 → 모든 예측 요청이 HTTP 500
- 수정: 중복된 멤버십 체크 제거, `load_model() is None → 404`로 일원화

### 2. train/serve 특성 스큐 + 데이터 누수 (CRITICAL)
- 학습은 21개 특성, 서빙은 25개 특성 → shape 불일치로 예측 불가
- 더 심각한 문제: **학습 특성에 누수 컬럼 포함**
  - `property_id` (식별자)
  - `final_sale_price` (추론 시점 미지 + 타깃 강상관 → 누수)
  - `numeric_mean/std/max/min` (타깃 포함 행단위 집계 → 누수)
- 수정: `feature_schema.py` 단일 소스로 **19개 정직한 특성** 통일
  (학습·서빙이 동일 목록·순서 사용)

### 3. 정규화 스큐 (HIGH)
- 학습은 Min-Max 정규화, 서빙은 raw 입력 → LinearRegression이
  `-44조` 같은 무의미값 출력
- 수정: `MinMaxScaler`를 모델 `Pipeline`에 내장 → 서빙 시 raw 입력을
  넣어도 내부에서 동일하게 스케일링

---

## 📊 정직한 성능 재평가

| 구분 | 기존(누수 포함) | 수정 후(정직) |
|------|----------------|---------------|
| 최고 모델 | LinearRegression | LGBMRegressor |
| Test R² | **0.9251** ❌ 부풀려짐 | **0.7488** ✅ 정직 |
| 원인 | final_sale_price 등 누수 | 누수 제거 |

**중요**: 기존에 보고된 R²=0.9251은 `final_sale_price`(사실상 타깃) 등이
입력 특성에 포함되어 발생한 **데이터 누수로 인한 과대평가**였습니다.
실제 운영 환경에서는 추론 시점에 `final_sale_price`를 알 수 없으므로
이 값은 사용할 수 없으며, 누수를 제거한 정직한 성능은 R²≈0.75입니다.

샘플 데이터(무작위 생성) 기준이므로 **실제 부동산 데이터(Phase 3)** 로
재학습하면 더 높은 성능을 기대할 수 있습니다.

---

## 🧪 테스트 현황

| 테스트 모듈 | 개수 | 내용 |
|------------|------|------|
| 기존 6개 모듈 | 158 | 단위/통합 |
| test_prediction_enhancements.py | 13 | 캐싱/신뢰도/이상탐지 |
| test_api_endpoints.py | 9 | **TestClient 실호출** (기존 공백 보완) |
| **합계** | **180** | **전부 통과** |

엔드포인트 실호출 테스트를 추가하여, 향후 동일 유형의 런타임 버그가
CI에서 즉시 검출되도록 했습니다.

---

## 📁 추가/변경 파일

**신규**
- `scripts/auto_retraining.py` — 자동 재학습 오케스트레이터
- `scripts/feature_schema.py` — 학습/서빙 공유 특성 스키마
- `scripts/prediction_enhancements.py` — 캐싱/신뢰도/이상탐지
- `tests/test_prediction_enhancements.py`
- `tests/test_api_endpoints.py`

**변경**
- `scripts/api_server.py` — NameError 수정, 스키마 기반 입력 구성, 신규 엔드포인트
- `scripts/avm_injection_engine.py` — 누수 제거, Pipeline(Scaler) 내장

---

## 🔜 권장 다음 단계

1. **Phase 1 배포** (로컬): gcloud 설치 후 `PHASE1_DEPLOYMENT_MANUAL.md` 실행
2. **Phase 3 실데이터**: Data.go.kr 실거래가로 재학습 → 정직한 R² 향상 기대
3. **단위 정합성**: 학습 데이터 가격 단위(원) vs API 입력 단위(만원) 정의 통일
   (현재 모델은 학습 데이터와 동일 단위로 일관 예측하나, 외부 계약 단위는
   별도 합의 필요)
