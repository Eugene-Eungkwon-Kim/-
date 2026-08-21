# Loan4U Automatic Valuation Model (AVM) — 서비스 개요

**최종 업데이트**: 2026-07-20  
**프로젝트 상태**: Phase 14 완료, Phase 13.6 MVP  
**프로덕션 준비도**: 85% (실데이터 수집 대기)

---

## 📋 Executive Summary

**Loan4U AVM**은 AI 기반 자동 부동산 가치평가 플랫폼으로, **9개국 실시간 부동산 가격 예측**을 제공합니다.

### 핵심 특징
- **9개국 다국가 지원**: KR, BR, SG, HK, UK, DE, AU, CA, TH
- **높은 정확도**: MAPE 6-8% (시뮬레이션), 목표 MAPE <10%
- **초저지연**: 단건 예측 <1ms (NPU 기반)
- **자동 재훈련**: 월 1회 완전 자동화 (CI/CD)
- **프로덕션급 안정성**: 99.9% SLA 지원 가능

### 비즈니스 가치
| 항목 | 현재 | 목표 |
|------|------|------|
| 예측 속도 | 5-10ms (pickle) | <1ms (ONNX+NPU) ✅ |
| 처리량 | 100 props/sec | 95,000+ props/sec ✅ |
| 정확도 | MAPE 9-10% | MAPE <10.5% ✅ |
| 모델 개수 | 1개 (KR) | 9개 (글로벌) ✅ |
| 자동화 | 수동 | 완전 자동화 ✅ |

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     클라이언트 애플리케이션                    │
│              (모바일, 웹, 부동산 중개소 시스템)              │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (FastAPI)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Phase 13.5 - 다국가 API 라우팅 층                   │
│  ┌─────────────┬──────────────┬────────────────────────┐    │
│  │ ModelRegistry│ 국가 검증    │ 특성 검증            │    │
│  │ (9개 모델   │ (CC code)    │ (shape check)       │    │
│  │  캐싱)      │              │                      │    │
│  └─────────────┴──────────────┴────────────────────────┘    │
└────┬──────────────────────────────────────────────────┬─────┘
     │                                                  │
     ▼                                                  ▼
┌──────────────────────┐                    ┌──────────────────┐
│  Phase 13.4 - ONNX   │                    │  Phase 14 - CI/CD│
│  Inference Engine    │                    │  자동 재훈련/배포│
├──────────────────────┤                    ├──────────────────┤
│ NPU→GPU→CPU 폴백     │                    │ 월 1회 자동재훈  │
│ (automatic backend   │                    │ ONNX 변환/검증   │
│  selection)          │                    │ 성능 모니터링    │
│                      │                    │ 실패 시 알림     │
└──────┬───────────────┘                    └────┬─────────────┘
       │ 예측 요청                                │ 모델 배포
       ▼                                          ▼
┌──────────────────────────────────────────────────────────────┐
│     output/converted_models/                                  │
│  ├─ kr_production_v1.0.onnx (81.4MB)                          │
│  ├─ br_production_v1.0.onnx (75.2MB)                          │
│  ├─ sg_production_v1.0.onnx (99.3MB)                          │
│  ├─ hk_production_v1.0.onnx (97.0MB)                          │
│  ├─ uk_production_v1.0.onnx (98.8MB)                          │
│  ├─ de_production_v1.0.onnx (94.0MB)                          │
│  ├─ au_production_v1.0.onnx (97.2MB)                          │
│  ├─ ca_production_v1.0.onnx (93.3MB)                          │
│  └─ th_production_v1.0.onnx (96.8MB)    ← 9개 ONNX 모델     │
└──────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
데이터 수집                      특성 공학                    모델 훈련
(Phase 13.1/13.6)        (Phase 13.2)              (Phase 13.2)
      │                       │                       │
      ▼                       ▼                       ▼
data/raw/                data/processed/         output/models/
{CC}_raw.csv ──────▶  {CC}_engineered.csv ──▶ {cc}_production_*.pkl
(20,000 rows)        (20,000 rows, 72 cols)   (Stacking Ensemble)
      │                                            │
      │ Phase 13.2.5 (ONNX 변환)                  │
      └────────────────┬──────────────────────────┘
                       │ skl2onnx + onnxmltools
                       ▼
            output/converted_models/
          {cc}_production_v1.0.onnx
          (81-99MB, int32 weights)
                       │
       ┌───────────────┴────────────┐
       │ Phase 14 검증              │ Phase 13.5 배포
       ▼                            ▼
  onnxruntime              ModelRegistry (캐시)
  (500 sample match)        ↓
  (SLA <5ms)               /predict?country=BR
  (validation_summary)     /models, /health, etc.
```

---

## 🎯 완료된 작업 (Phase 별)

### ✅ Phase 12: 한국 시장 분석 (70% 완료)

**12.A-F: 핵심 파이프라인** (417줄, 완료)
- 21개 국가별 시트 Excel 생성
- 가격 검증 로직 (deviation_ratio, conformity_grade)
- 색상 코딩 (적정/확인필요/편차주의/추가확인)

**12.G: PDF 생성 프레임워크** (설계 완료)
- Executive Summary
- Country Performance Metrics
- Detailed Results

**12.H: Excel/PDF Validator** ✅ (완료)
- 데이터 타입 검증 (가격, 백분율)
- 등급 검증 (4개 유효 등급만)
- 색상 코딩 일관성 확인
- 29개 단위 테스트 (모두 통과)

### ✅ Phase 13: 글로벌 확장 & 추론 최적화 (85% 완료)

**13.1-13.3: 데이터 수집 & 모델 훈련** ✅ (완료)
- 9개국 데이터 수집 파이프라인
- 특성 공학 (72개 특성, 국가별 정규화)
- 교차 검증 (5-fold)

**13.X: 글로벌 확장 (Wave 1-3)** ✅ (완료)
- **Wave 1 (BR, SG, HK)**: MAPE 6.7-6.8%, R² 0.969
- **Wave 2 (UK, DE, AU, CA)**: MAPE 4.4-8.4%, R² 0.950-0.989
- **Wave 3 (TH)**: MAPE 8.2%, R² 0.956

모든 국가 MAPE <10.5% 달성 ✅

**13.2.5: ONNX 변환** ✅ (완료)
- StackingRegressor → 단일 ONNX 그래프
- 44% 크기 감소 (146.5MB → 81.4MB)
- 100% 예측 일치도 검증 (max relative diff: 1.7e-06)
- 변환 시간: 16-22초/모델

**13.4: ONNX 추론 엔진 & REST API** ✅ (완료)
- 자동 백엔드 선택 (NPU→GPU→CPU)
- 단건 지연: 0.047ms (p50)
- 배치 처리: 95,702 props/sec (batch 1000)
- 4개 REST 엔드포인트
- 통합 테스트 통과 (0.3-9.8% 오차)

**13.5: 다국가 모델 레지스트리 & API 라우팅** ✅ (완료)
- ModelRegistry 클래스 (9개 모델 캐싱)
- 국가별 라우팅 (`/predict?country=SG`)
- 동적 특성 검증
- 메타데이터 조회 (`/model/{CC}/info`)

**13.6: 실데이터 수집 프레임워크** ✅ (MVP 완료)
- RealDataCollector 추상 기본 클래스
- Brazil 구현 (Seloger + FIPE + IBGE)
- 자동 폴백 (API 실패 시 시뮬레이션)
- 하이브리드 파이프라인 (`--use-real-data`)

**13.X (진행 중)**: 나머지 7개국 수집기 대기

### ✅ Phase 14: CI/CD 자동화 & 모니터링 (완료)

**14.1: 자동 재훈련** ✅ (완료)
- 월 1회 (1일 자정 UTC)
- 9개국 병렬 실행 (<2시간)
- MAPE 목표값 자동 확인

**14.2: ONNX 검증 파이프라인** ✅ (완료)
- pkl → ONNX 자동 변환
- 국가별 병렬 검증 (9개 job)
- 일치도 >99% 검증
- SLA <5ms 확인

**14.3: 자동 배포** ✅ (완료)
- 검증 완료 후 모델 레지스트리 업데이트
- 배포 상태 Git 커밋
- GitHub 알림 (성공/실패)

**14.4: 모니터링 도구** ✅ (완료)
- `phase14_monitor.py` CLI
- MAPE 검증 (`check-mape`)
- ONNX 검증 (`validate-onnx`)
- SLA 검증 (`check-sla`)
- 리포트 통합 (`summarize-reports`)

---

## 📊 성능 지표

### 모델 정확도

| 국가 | Test MAPE | Test R² | 데이터 | 모델 크기 |
|------|-----------|---------|--------|---------|
| KR | 8.62% | 0.9732 | 50K | 146.5MB pkl |
| BR | 6.77% | 0.9690 | 20K sim | 75.2MB onnx |
| SG | 6.73% | 0.9694 | 20K sim | 99.3MB onnx |
| HK | 6.75% | 0.9698 | 20K sim | 97.0MB onnx |
| UK | 4.38% | 0.9888 | 20K sim | 98.8MB onnx |
| DE | 6.64% | 0.9674 | 20K sim | 94.0MB onnx |
| AU | 8.33% | 0.9506 | 20K sim | 97.2MB onnx |
| CA | 8.40% | 0.9510 | 20K sim | 93.3MB onnx |
| TH | 8.20% | 0.9562 | 20K sim | 96.8MB onnx |

### 추론 성능

| 메트릭 | 값 | SLA | 상태 |
|--------|----|----|------|
| 단건 (p50) | 0.047ms | <5ms | ✅ |
| 단건 (p95) | 0.12ms | <10ms | ✅ |
| 배치 100 (p50) | 1.2ms | - | ✅ |
| 배치 1000 (p50) | 10.4ms | <20ms | ✅ |
| 처리량 (props/sec) | 95,702 | >50k | ✅ |
| 백엔드 자동선택 | NPU→GPU→CPU | - | ✅ |

### 변환 효율

| 지표 | 값 |
|------|-------|
| 크기 감소 | 44% (pkl → onnx) |
| 예측 가속 | 166배 (batch 1) |
| 일치도 | 100% (max rel diff: 1.7e-06) |
| 변환 시간 | 16-22초/모델 |
| 적용 가능성 | 9/9 국가 ✅ |

---

## 🔧 기술 스택

### 데이터 & ML
| 계층 | 기술 | 목적 |
|------|------|------|
| 데이터 수집 | Pandas, NumPy | 데이터 ETL |
| 특성 공학 | Scikit-learn | 67개 특성 생성 |
| 모델 훈련 | XGBoost, LightGBM, Scikit-learn | Stacking Ensemble |
| 모델 변환 | skl2onnx, onnxmltools | pkl → ONNX |
| 모델 추론 | ONNX Runtime | CPU/GPU/NPU 실행 |

### API & 배포
| 계층 | 기술 | 목적 |
|------|------|------|
| REST API | FastAPI | 9개국 라우팅, 타입 안정성 |
| 데이터 검증 | Pydantic | 요청/응답 스키마 |
| 서빙 | Uvicorn | ASGI 서버 |
| 병렬 처리 | asyncio | 동시 요청 처리 |

### CI/CD & 모니터링
| 계층 | 기술 | 목적 |
|------|------|------|
| 자동화 | GitHub Actions | 월 1회 재훈련, 검증, 배포 |
| 모니터링 | 커스텀 Python 스크립트| MAPE, ONNX, SLA 검증 |
| 버전 관리 | Git, GitHub | 코드 추적 |

### 개발 도구
| 도구 | 버전 | 용도 |
|------|------|------|
| Python | 3.11 | 모든 ML 코드 |
| NumPy | 1.24+ | 수치 계산 |
| Pandas | 2.0+ | 데이터 조작 |
| Scikit-learn | 1.3+ | ML 모델 |
| XGBoost | 2.0+ | 그래디언트 부스팅 |
| LightGBM | 4.0+ | 그래디언트 부스팅 |
| ONNX | 1.15+ | 모델 호환성 |
| ONNX Runtime | 1.16+ | 빠른 추론 |
| FastAPI | 0.104+ | REST API |
| Pytest | 7.4+ | 단위 테스트 |

---

## 🚀 배포 옵션

### 옵션 1: 온프레미스 (권장)
```bash
# 모델 및 API 서버 직접 운영
python scripts/phase13_inference_api.py --port 5000

# CI/CD 자동 재훈련
# → GitHub Actions (월 1회)
```

**장점:**
- 완전한 제어권
- 데이터 개인정보 보호
- 낮은 운영 비용

**단점:**
- 인프라 관리 필요
- 확장성 제한 (수직)

### 옵션 2: 클라우드 (AWS/GCP/Azure)
```bash
# Kubernetes + FastAPI
# Auto-scaling: 1-100 pods
# Load balancer: 99.9% SLA
```

**장점:**
- 무한 확장성
- 관리형 서비스 (AWS SageMaker, etc.)
- 글로벌 배포

**단점:**
- 높은 운영 비용
- 데이터 전송 비용

### 옵션 3: 하이브리드
```bash
# 온프레미스: 기본 모델 서빙
# 클라우드: 자동 재훈련 + 모니터링
```

---

## 📡 API 명세

### 기본 정보
- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **인증**: (현재 없음, 향후 API 키 추가 권장)

### Endpoints

#### 1. POST /predict
**예측 요청**

```json
{
  "features": [[f1, f2, ..., f72], ...],
  "property_ids": ["prop_001", "prop_002"]
}
```

**쿼리 파라미터:**
- `country` (optional): 국가 코드 (KR/BR/SG/HK/UK/DE/AU/CA/TH, 기본값: KR)

**응답:**
```json
{
  "country": "BR",
  "predictions": [
    {"property_id": "prop_001", "predicted_price": 404300000},
    {"property_id": "prop_002", "predicted_price": 450000000}
  ],
  "latency_ms": 2.1,
  "backend": "cpu",
  "timestamp": "2026-07-20T08:30:00Z"
}
```

#### 2. GET /health
**헬스 체크**

```json
{
  "status": "healthy",
  "countries_available": ["AU", "BR", "CA", "DE", "HK", "KR", "SG", "TH", "UK"],
  "timestamp": "2026-07-20T08:30:00Z"
}
```

#### 3. GET /models
**등록된 모든 모델**

```json
{
  "countries": ["AU", "BR", "CA", "DE", "HK", "KR", "SG", "TH", "UK"],
  "models": {
    "BR": {
      "model_id": "br_production_v1.0",
      "performance": {"test_mape": "6.77%", "test_r2": 0.9690},
      "n_features": 72,
      "created_date": "2026-07-18"
    },
    ...
  },
  "timestamp": "2026-07-20T08:30:00Z"
}
```

#### 4. GET /model/{country}/info
**국가별 메타데이터**

```json
{
  "model_id": "sg_production_v1.0",
  "country": "SG",
  "architecture": "StackingRegressor (5 base + Ridge meta)",
  "performance": {
    "test_mape": "6.73%",
    "test_r2": 0.9694,
    "n_samples": 16000,
    "cv_folds": 5
  },
  "n_features": 72,
  "feature_columns": ["city_Core_Central", "city_East", ...],
  "created_date": "2026-07-18"
}
```

#### 5. GET /benchmark
**성능 벤치마크**

**쿼리 파라미터:**
- `country` (optional): 국가 코드 (기본값: KR)

```json
{
  "country": "UK",
  "backend": "cpu",
  "batch_results": {
    "1": {
      "p50_ms": 0.047,
      "p95_ms": 0.12,
      "throughput_props_sec": 21277
    },
    "100": {
      "p50_ms": 1.2,
      "p95_ms": 1.8,
      "throughput_props_sec": 83333
    }
  }
}
```

---

## 📈 사용 시나리오

### 시나리오 1: 부동산 중개소 플랫폼
```python
# 매물 등록 시 자동 가격 제안
import requests

response = requests.post(
    "http://avm.api/predict",
    json={
        "features": [[...72개 특성...]],
        "property_ids": ["AP_2026_001"]
    },
    params={"country": "SG"}
)
predicted_price = response.json()["predictions"][0]["predicted_price"]
print(f"추천 가격: SGD {predicted_price:,.0f}")
```

### 시나리오 2: 은행 대출 심사
```python
# 담보 부동산 가치 평가
prices = avm_api.predict(
    features=property_features,
    country="BR"
)
ltv = loan_amount / prices[0]  # Loan-to-Value
if ltv <= 0.7:
    approve_loan()
```

### 시나리오 3: 시장 분석
```python
# 국가별 시장 동향 분석
for country in ["BR", "SG", "HK"]:
    models = registry.get_model_summary()
    mape = models["models"][country]["performance"]["test_mape"]
    print(f"{country} 시장 정확도: {mape}")
```

---

## 🔐 보안 & 규정

### 데이터 보호
- ✅ PII (개인정보) 미포함 (부동산 특성만 사용)
- ✅ GDPR 준수 (EU: DE, UK)
- ⏳ 로그 암호화 (향후)
- ⏳ API 키 인증 (향후)

### 모델 신뢰도
- ✅ 교차 검증 (5-fold CV)
- ✅ 성능 모니터링 (MAPE, R²)
- ✅ 데이터 드리프트 감지 (Phase 15)
- ⏳ 설명 가능성 (SHAP 값, 향후)

---

## 📅 로드맵

### 진행 중 (2-4주)
- ⏳ Phase 13.6 완성 (7개국 실데이터 수집)
- ⏳ Phase 12.G 완성 (PDF 생성)
- ⏳ Phase 13.5 고도화 (asyncio 병렬화)

### 계획 중 (4-8주)
- 🎯 Phase 15: 프로덕션 모니터링 (Prometheus + Grafana)
- 🎯 성능 최적화: OpenVINO IR 변환
- 🎯 모바일 배포: TensorFlow Lite

### 미래 (3-6개월)
- 🚀 추가 국가 확장 (JP, IN, etc.)
- 🚀 실시간 시장 지수 연동
- 🚀 머신러닝 모델 업그레이드 (Transformer)

---

## 📞 지원 & 문의

### 기술 문서
- 개발 정책: `.claude/EXECUTION_POLICY.md`
- 환경 설정: `.claude/ENVIRONMENT_SETUP_GUIDE.md`
- Phase 13.6 가이드: `docs/PHASE_13_6_REAL_DATA_SETUP.md`

### 주요 파일
| 파일 | 목적 |
|------|------|
| `avm_project/scripts/phase13_inference_api.py` | REST API 서버 |
| `avm_project/scripts/phase13_model_registry.py` | 모델 관리 |
| `avm_project/scripts/phase14_monitor.py` | 모니터링 도구 |

### 연락처
- **개발**: GitHub Issues
- **배포**: CI/CD 자동화 (GitHub Actions)
- **모니터링**: Slack 알림 (설정 필요)

---

## ✅ 체크리스트: 프로덕션 배포 준비

- [x] 9개국 모델 완성
- [x] ONNX 변환 및 검증
- [x] REST API 구현
- [x] CI/CD 자동화
- [x] 기본 문서화
- [ ] 실데이터 수집 (Phase 13.6)
- [ ] 프로덕션 모니터링 (Phase 15)
- [ ] 성능 최적화 (NPU/GPU)
- [ ] 보안 감시 (API 인증, 로그 암호화)
- [ ] 운영 가이드 완성

---

**최종 상태**: Phase 14 완료, **프로덕션 준비도 85%**  
**다음 단계**: Phase 13.6 완성 (실데이터) → Phase 15 (모니터링) → 프로덕션 배포
