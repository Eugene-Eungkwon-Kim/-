# AVM 엔진 한계 및 정직한 현황 (LIMITATIONS)

**작성일**: 2026-06-30
**대상**: Loan4U AVM Engine v1.0-ensemble
**목적**: 현재 모델 성능 지표의 실제 의미를 왜곡 없이 기록한다.

---

## ⚠️ 한 줄 요약

> **R²는 여전히 합성 데이터 기반이라 실거래 일반화 성능이 아니다.**
> 단, 초기 버전의 **타깃 누수는 제거**했다(상관 0.999→0.976).
> 누수 제거 후 정직한 성능은 **R²=0.95, MAPE=11.2%**이며,
> 이는 목표(MAPE<10.5%)를 **초과(FAIL)**한다 — 이것이 정직한 현재 수준이다.

---

## 0. 변경 이력: 타깃 누수 제거 (2026-06-30)

| 지표 | 누수 버전 (이전) | 누수 제거 후 (현재) |
|------|------------------|---------------------|
| old_price ↔ new_price 상관 | 0.9989 (사실상 정답 복사) | 0.976 (상관된 별개 관측치) |
| 앙상블 R² | 0.984 | **0.949** |
| 앙상블 MAPE | 3.1% | **11.2%** |
| 트리비얼(old×k) MAPE | 2.7% | 11.8% |
| **앙상블의 트리비얼 대비 개선** | +0.06%p (무가치) | **+0.6%p (미미하나 실재)** |
| old_price 순열 중요도 | 0.987 | **0.930** |
| 펀더멘털(면적·위경도) 기여 | 1.3% | **7.0%** |

**무엇을 고쳤나**: 초기 생성기는 `old_price = new_price × uniform(0.88,0.98)`로
직전가를 정답의 ±5% 사본으로 만들었다(준-누수). 이를 **동일 물건의 과거(1~4년 전)
실거래가**로 재설계했다 — 같은 펀더멘털을 공유하되 (1)당시 시장수준, (2)당시 연식,
(3)**독립** idiosyncratic 노이즈로 분리. 이제 직전가는 정답의 사본이 아니라
현실의 직전 거래처럼 "상관은 높지만 별개"인 관측치다.

**남은 정직한 한계**: 그래도 R²=0.95는 높다. 직전가가 0.976 상관으로 여전히
대부분의 신호를 운반하기 때문이다(실거래에서도 직전가는 가장 강한 예측변수).
즉 이 모델의 실질 부가가치는 "직전가 × 시세상승률" 대비 MAPE 0.6%p 개선에 그친다.

---

## 1. 데이터의 본질: 합성(Synthetic), 실거래 아님

### 1.1 현재 상태
- `data/raw/KR_data.csv` (10,000행)는 `generate_kr_realistic_data.py`가
  **사람이 정한 공식**으로 만든 가상 데이터다.
- 국토교통부 실거래가 API(Data.go.kr) 데이터는 **현재 0건** 확보.
  (원격 실행 환경의 네트워크 정책이 `apis.data.go.kr` 도메인을 차단 →
  로컬 수집 스크립트 `collect_kr_data_local.py` 실행 대기 중)

### 1.2 왜 R²가 높을 수밖에 없는가 (순환성)
```
가격 공식 정의  →  공식으로 데이터 생성  →  같은 패턴을 모델이 학습
                                                  ↓
                              모델이 공식을 거의 복원 → R² 0.98 (당연)
```
이것은 모델 성능이 아니라 **"공식을 공식으로 맞췄다"**는 동어반복에 가깝다.

---

## 2. 정량적 증거: 강건성 검증 결과

`scripts/validate_robustness.py` 실행 결과 (`output/robustness_report.json`):

### 2.1 선형 베이스라인 대비 — 누수 제거로 앙상블이 정당화됨
| 모델 | 누수 버전 R² | 누수 제거 후 R² |
|------|-------------|------------------|
| 단순 선형회귀 (LinearRegression) | 0.9977 | 0.9495 |
| 3-모델 앙상블 (XGB+LGB+GB) | 0.9983 | 0.9734 |
| **실질 우위** | **+0.06%p (무가치)** | **+2.39%p (유의미)** |

> **누수 버전**에선 데이터가 거의 선형이라 단순 선형모델로도 동일 성능 →
> 비싼 앙상블이 정당화되지 않았다.
> **누수 제거 후**엔 직전가가 정답의 사본이 아니게 되어 비선형 펀더멘털 신호가
> 살아나고, 앙상블이 선형 대비 +2.39%p 우위를 보인다 → 앙상블·GPU·NPU 경로가
> 비로소 의미를 갖는다. (단, 절대 R²는 여전히 합성 데이터 기반)

### 2.2 노이즈 강건성 (현재, 누수 제거 후)
| 입력 노이즈 | R² | MAPE |
|------------|------|------|
| 0% | 0.977 | 9.0% |
| 5% | 0.869 | 15.8% |
| 10% | 0.850 | 17.1% |
| 20% | 0.810 | 20.2% |
| 30% | 0.745 | 24.2% |

> 무노이즈 MAPE조차 9.0%로 목표(10.5%)에 근접하고, 실거래에 항상 존재하는
> 5~15% 변동(개별 협상·급매·층/향)을 얹으면 즉시 목표를 초과한다.
> 현재 정확도는 깨끗한 합성 데이터에서만 성립한다.

### 2.3 피처 중요도 — old_price 지배 (현재, `feature_importance_report.json`)
| 피처 | 순열 중요도(3모델 평균) | 누수 버전(참고) |
|------|------------------------|------------------|
| **old_price** | **0.930** | 0.987 |
| area_sqm | 0.029 | 0.005 |
| latitude | 0.023 | 0.005 |
| longitude | 0.017 | 0.003 |
| property_type | 0.000 | 0.000 |

피처 격리 실험 (GradientBoosting, 현재 데이터):
| 입력 구성 | 홀드아웃 R² | MAPE | 누수 버전(참고) |
|-----------|-------------|------|------------------|
| old_price 단독 | 0.941 | 11.8% | 0.997 |
| 펀더멘털만 (면적·위경도·층·연식) | 0.859 | 17.7% | 0.857 |

> **현재 상태**: 누수 제거로 old_price 단독 R²이 0.997→0.941로 내려갔다
> (정답의 사본이 아니라 진짜 직전 거래가가 됐다는 증거). 그래도 old_price는
> 여전히 지배적(0.930)인데, 이는 실거래에서도 직전가가 가장 강한 예측변수이기
> 때문이라 비정상은 아니다. 펀더멘털만으로의 R²=0.859가 "직전가 없이 평가하는
> 능력"의 정직한 지표이며, MAPE 17.7%로 아직 부정확하다.
>
> **콜드스타트 제품화**: 이 펀더멘털 모델을 `avm_coldstart.py` +
> `AVMCoreEngine.valuate_coldstart()`로 제품화했다(R²≈0.87). 담보에 최근
> 실거래가 없을 때 면적·위경도·층·연식만으로 평가하며, 메인 엔진과 ±35% 이내로
> 일치(강남 27.3억 vs 27.6억). 신뢰도는 0.65로 보수적 고정. 직전가가 있으면
> 메인 valuate()를 쓰고, 없을 때만 콜드스타트를 쓴다.

### 2.4 분포 외(OOD) 입력 — ✅ 가드레일 추가됨 (해결)
`avm_core_engine._validate_inputs`로 다음을 처리:
| 입력 | 수정 전 | 수정 후 |
|------|---------|---------|
| 가격 0원 / 음수 | 그럴듯한 숫자 외삽 | **ValueError 거부** |
| 해외 좌표(위도 45) | 5.51억 산출 | 경고 + 신뢰도 ×0.5 (conf 0.35) |
| 비정상 면적/극단가 | 무방비 | input_warnings 플래그 |

---

## 3. 보정계수(correction factor) — ✅ 이중계상 수정됨

**수정 전 결함(이중계상)**: 모델 타깃이 new_price(실제 시세)이므로 base_price는
이미 시세 예측치인데, CorrectionLayer가 ×1.20~1.30을 곱해 출력을 체계적으로
+30% 부풀렸다(예: 강남 base 26.8억 → corrected 33.2억). 대출 담보 과대평가는
가장 위험한 조용한 오답이다.

**수정**: 보정계수를 **1.0 중심 잔차 조정**(±3%)으로 재정의 → corrected ≈ base.
이제 강남 84㎡는 33.2억이 아니라 27.6억(시세 타당). 낙찰가율(auction_module)은
별도로 1.0 미만(경매 할인)으로 교정됨.

**남은 한계**: 1.0 중심 ±3% 스프레드, 낙찰가율(0.65~0.93), 시장계수, 등급
앵커 좌표는 여전히 **가정값**이다. 코드에 `ASSUMPTION`/`TODO(calibration)`로
표기했으며 실거래 확보 시 잔차로 재추정해야 한다.

---

## 4. 프로덕션 적합성 판정

| 항목 | 상태 |
|------|------|
| 코드 구조/모듈화 | ✅ 양호 (단일 책임, 타입힌트, 76 테스트) |
| 입력 가드레일 | ✅ 추가됨 (0원/음수 거부, OOD 페널티) |
| 보정 이중계상 | ✅ 수정됨 (1.0 중심, +30% 인플레 제거) |
| 보정계수 근거 | ⚠️ 가정값 (ASSUMPTION 표기) |
| 실거래 데이터 | ❌ 0건 |
| 일반화 성능 | ❌ 미검증 (합성 데이터만) |
| **대출 심사 투입 가능 여부** | **❌ 불가** |

> 코드 품질·구조적 결함(누수·이중계상·죽은코드·가드레일)은 상당 부분 해소됐다.
> 그러나 파이프라인 위에 흐르는 **데이터가 합성**이므로 여전히 **예측값을
> 신뢰해선 안 된다.** 골격은 단단해졌으나 실거래 검증이 남았다.

---

## 5. 실거래 데이터 확보 후 달라지는 것

1. `collect_kr_data_local.py`로 국토부 실거래 수집 → `KR_data.csv` 교체
2. `train_kr_model.py` 재학습 → **이때 나오는 R²가 진짜 성능 지표**
3. 그 R²가 0.84를 넘으면 그제서야 의미 있는 모델
4. 선형 베이스라인 대비 우위가 커지면 앙상블이 정당화됨
5. 보정계수를 실거래로 캘리브레이션

**결론**: 지금의 0.98이 아니라, **실거래로 재학습한 뒤의 숫자**가 평가 대상이다.
이 문서는 그 전까지 현재 지표가 과대평가되지 않도록 하는 안전장치다.

---

## 6. NPU/OpenVINO 배포의 실제 한계 (Phase 13.4)

**"NPU 가속"은 트리 앙상블 모델에 적용되지 않는다.** OpenVINO의 ONNX 프론트엔드는
`ai.onnx.ml.TreeEnsembleRegressor` 연산자(XGBoost/LightGBM/GradientBoosting을
ONNX로 변환하면 나오는 연산)를 지원하지 않는다 — OpenVINO IR/NPU는 신경망
(CNN/RNN 등)을 위한 포맷이기 때문이다. `phase13_model_converter.py`로 4개
앙상블 모델 전부 ONNX 변환은 성공하지만, ONNX→OpenVINO IR 단계는 전부
`onnx_only`로 남는다 — 이는 버그가 아니라 라이브러리의 설계상 한계다.

**실제 채택한 가속 경로**: OpenVINO IR 대신 **ONNX Runtime**(onnxruntime)을
실제 추론 백엔드로 사용한다. 이는 ONNX-ML 연산을 정식 지원하며, 이번 세션에서
측정한 실제(워밍업 후) 지연시간은 **~0.3ms/요청**(CPU, 3-모델 앙상블)으로,
raw sklearn pickle 추론보다 빠르다. "NPU 1ms 목표"라는 표현은 애초에 이
모델군에 적용 불가능한 목표였다.

**추가로 발견/수정한 버그**:
- `preprocess_input()`의 old_price 정규화 범위가 학습 시 사용하는
  `avm_feature_engineering.FEATURE_MIN/MAX`(6,000,000,000원)와 1000배
  어긋나(5,000,000원 하드코딩) 추론 결과가 실제 시세와 무관한 값(예:
  37억원)을 냈다 — 학습-추론 정규화 소스를 통일해 수정.
- 컨버터가 XGBoost의 `save_model(".onnx")`를 "네이티브 ONNX"로 오인해
  실제로는 UBJSON을 저장하고 있었다 (OpenVINO가 파싱 실패로 알려줌) →
  onnxmltools 경로만 사용하도록 수정.
- 컨버터가 `xgboost_KR`/`lightgbm_KR`만 변환하고 Phase 13.3에서 실제로
  선정된 `best_model_KR`(이번 실행에서 gradient_boosting)은 변환 대상에서
  빠져 있었다 → 모델 타입 자동 감지로 4개 전부 변환하도록 확장.

---

## 7. `avm_ensemble_engine.py`가 국가 구분 없이 모델을 로드하던 버그 (Phase 13.1-GBL, 수정됨)

`tests/test_kr_valuation.py`의 여러 테스트가 Phase 13.1-GBL(글로벌 확장) 작업
중 간헐적으로 실패했다. 처음에는 "학습 재현성 문제"로 오진했으나(이전 버전의
이 섹션 참조), 근본 원인은 전혀 달랐다:

**실제 원인**: `AVMEnsembleEngine._load_pickled_models()`/`_load_ir_models()`가
`output/trained_models/`, `output/models_ir/`의 **모든** `*.pkl`/`*.xml`
파일을 국가 구분 없이 무조건 globbing해서 로드하고 있었다. KR만 존재할 때는
문제가 없었지만, Phase 13.1-GBL에서 SG/HK 모델을 같은 공유 디렉터리에
추가하자 KR 엔진이 `xgboost_HK.pkl`, `coldstart_KR.pkl`, `best_model_KR.pkl`,
`*_tuned.pkl` 등 의도치 않은 모델까지 전부 앙상블 평균에 섞어버렸다.
특히 HK 모델은 완전히 다른 통화/스케일(HKD, 수백만~수천만)로 정규화되어
있어 KR 정규화 특성 벡터를 넣으면 사실상 무작위에 가까운 값을 반환했고,
이것이 가중평균에 섞이며 예측이 실제값의 절반 수준(예: 12.9억, 정상 24~26억)
으로 크게 왜곡되었다.

개별 학습 함수(`train_xgboost`/`train_lightgbm`/`train_gradient_boosting`)는
검증해본 결과 완전히 결정론적이었다(`np.allclose` 100% 일치) — 즉 이 버그는
학습의 비결정성이 아니라 **다중 국가 모델이 공존할 때 앙상블 엔진의 필터링
누락**이었다.

**수정**: `AVMEnsembleEngine.__init__`에 `country` 파라미터(기본값 'KR')를
추가하고, `ENSEMBLE_MODEL_TYPES = ('xgboost', 'lightgbm', 'gradient_boosting')`
로 정확히 3개 파일(`{model_type}_{country}.{pkl,xml}`)만 로드하도록
`phase13_npu_inference.py`(Phase 13.4에서 이미 이 방식으로 구현됨)와 동일한
패턴으로 변경했다. 수정 후 `output/trained_models/`에 KR+SG+HK 모델이 모두
공존한 상태에서도 `test_kr_valuation.py` 38/38 안정적으로 통과함을 확인했다.

---

## 8. `app/` API 서버가 임포트 단계에서부터 죽어 있던 문제 (2026-09-07, 수정됨)

RAG 벡터 DB·XAI 구축 작업을 시작하려다 보니, `app/main.py`가 참조하는
`app.db.database`, `app.db.models`, `app.avm.comparator`,
`app.avm.rag_pipeline`, `app.avm.confidence_scorer` **다섯 모듈이 전부
실체 없이 import 문만 존재**했다. `python -c "import app.main"` 이 최초
`ModuleNotFoundError: No module named 'app.db'` 로 즉시 죽었다 — API
서버가 한 번도 부팅에 성공한 적이 없었다는 뜻이다.

engine.py/routes.py 가 실제로 쓰는 컬럼·쿼리를 전수 조사해 스키마를
역산하고 다섯 모듈을 신설했다(공식 설계 문서 없음 — 사용 패턴에서 역산한
초안). Milvus(pymilvus[milvus_lite], 서버 없이 파일 하나로 동작)로 실제
벡터 검색을 연결했고, OpenAI 는 키가 없어 결정적 템플릿 설명으로 대체했다.

### 8.1 부수적으로 발견·수정한 실제 버그 4건

- **재개 시 중복 제거 무효** (별개 프로젝트, phonesort — 저널의 해시를
  재개 시 대조하지 않아 이미 옮긴 보존본이 사본으로 승격되던 문제.
  `claude/phonesort-refactor` 브랜치에서 수정).
- **NULL 조인으로 비교사례가 조용히 0건**: `Appraisal.appraisal_date`
  를 비워두면 `_find_comparables`의 "최신 감정가" 조인
  (`appraisal_date == MAX(appraisal_date)`)이 SQL NULL 비교 규칙 때문에
  항상 실패한다. OnBid 데이터 임포터(`import_onbid_csv.py`)가 이 값을
  안 채우고 있어 데이터를 넣어도 비교사례 검색이 늘 0건이었다 —
  가져온 시점 날짜로 채우도록 수정.
- **Decimal/float TypeError**: SQLAlchemy `Numeric` 컬럼(`trade_amount`)
  이 `Decimal` 로 반환되는데, 엑셀 내보내기(`export_comparable_sales_
  excel.py`)가 `float` 와 그대로 나눠 실제 데이터로 돌리자마자 죽었다.
- **CI 의존성 충돌**: `.github/workflows/backend-test.yml` 이
  `backend/requirements.txt` 만 설치하고 `tests/` 전체를 돌리는데, 이
  파일에 새 테스트가 쓰는 sqlalchemy/pymilvus/openpyxl/requests 가 아예
  없었다 — 즉 이 항목들을 쓰는 커밋들이 CI를 계속 실패시키고 있었을
  가능성이 높다. 추가하자 `pymilvus`(python-dotenv>=1.0.1 요구)와
  `python-dotenv==1.0.0` 고정이 정면으로 충돌해 설치 자체가 실패하는
  것도 함께 드러났다 — 두 requirements 파일 모두 1.0.1 로 올려 해결.
  깨끗한 가상환경에 `backend/requirements.txt` 만 설치해 실제 CI와
  동일한 경로로 재현·검증했다.
- **관리자 화면 고정값**: `backend/main.py`의 `/data/quality`,
  `/data/price-distribution`, `/data/region-distribution` 세 엔드포인트가
  DB를 전혀 조회하지 않고 코드에 박힌 데모용 고정값을 리턴하고 있었다.
  기존 엔드포인트는 그대로 두고 `/data/comparable-sales/*` 를 신설해
  실측 조회로 대체했다 — `property_type` 으로 그냥 GROUP BY 하는 일반
  쿼리라 특정 자산유형에 매여 있지 않다(아파트/상가/공장창고/토지 4종을
  섞어 넣고 코드 변경 없이 정확히 집계됨을 테스트로 확인).

### 8.2 이 세션이 닫지 못한 것 — 코드가 아니라 정보 자체가 없어서

아래 네 가지는 추가 코드나 검색으로 해결되지 않는다. 이 README 상단에도
이미 적혀 있듯 이 프로젝트의 실데이터는 **외장하드**(`D:\NPL폴더`, 세션
따라 D:/E:/F: 로 잡힘)에 있고, 이 항목들은 전부 거기 있거나 사용자만
가진 정보다.

| 항목 | 상태 | 필요한 것 |
|---|---|---|
| 토지 실거래 API 서비스 코드 | 12회+ 웹 검색 시도, 확인 실패 | data.go.kr 마이페이지 → 활용신청 내역 |
| OnBid 경매 데이터 | 임포터(`import_onbid_csv.py`)는 완성, 실데이터 0건 | 외장하드 `npl_avm.db`의 `onbid_auction_results` CSV 내보내기 |
| P6 가격 추정 모델 | 학습 데이터 없어 미구현 (가짜 모델 생성은 거부 — 대출 심사에 쓰일 수 있는 값이라 위험) | 외장하드의 학습 데이터 또는 이미 학습된 모델 파일 |
| Loan4U 업로드 엑셀 정확한 포맷 | 대체 도구(`export_comparable_sales_excel.py`, 기존 가격판정 로직 재사용)만 존재 | 실제 업로드 템플릿 파일 |
| 공장/상업 API 필드 태그명 | 서비스 코드는 확인됐으나 실응답 미검증(샌드박스 egress 정책이 apis.data.go.kr 차단) | 네트워크 제약 없는 환경에서 `--debug` 실행 |

### 8.3 회귀 검증 — 이번 세션이 기존 테스트를 깨뜨리지 않았는지 확인

`tests/` 전체(342개 기존 + 43개 신규)를 처음으로 한 번에 돌려봤다.
50개 실패 + 24개 수집 오류가 나왔지만, 전부 이번 세션 이전부터 있던
문제였다 — 실패한 파일 어디에도 이번 세션이 건드린 모듈(app.db,
app.avm.rag_pipeline/confidence_scorer/comparator, app.integrations.*,
backend.main 신규 엔드포인트)을 참조하는 곳이 없었고, 최초 커밋
(a473489)의 원본 파일로 되돌려 동일 테스트를 돌려도 **글자 하나
다르지 않게 같은 실패**가 재현됐다(예: test_avm_engine.py 4건 —
"All models failed prediction", 학습된 모델 파일이 애초에 없어서).
나머지도 원인이 전부 이번 세션과 무관하다: `models/` 디렉터리 부재,
`/mnt/avm_data` 외부 경로 부재, `torch`/`reportlab` 미설치,
`Phase12Validator` 생성자 시그니처 불일치(pre-existing) 등.

**결론**: 이번 세션의 변경은 기존 342개 테스트 중 어느 것도 새로
깨뜨리지 않았다. 신규 43개를 더해 전부 통과.

위 표의 OnBid·P6 모델 항목은 `scripts/sync_from_external_drive.py` 로
수작업 없이 한 번에 가져올 수 있다 — 외장하드를 연결한 PC에서
`python scripts/sync_from_external_drive.py` 실행 한 줄이면 드라이브
문자(D:/E:/F:)를 자동으로 훑어 `npl_avm.db`의 OnBid 데이터를 SQL 쿼리
직접 작성 없이 바로 적재하고, 학습된 P6 모델 파일을 찾아
`models/`(engine.py 가 이미 보는 위치)로 복사한다.

## 9. GitHub Actions 워크플로우 4종 실행 불가 버그 (2026-09-08, 수정됨)

`.github/workflows/`는 저장소 루트에 있는 파일만 GitHub이 실제로
인식한다 — `avm_project/.github/workflows/*.yml` 8개는 애초에
디스커버리 대상이 아니었다(경로 착오). 실제로 발동 가능한 건 루트의
4개(`korea_monthly_retrain.yml`, `phase14_deploy.yml`,
`phase14_global_train.yml`, `phase14_model_validation.yml`)뿐이었고,
전부 `working-directory` 미지정으로 모든 스텝이 "파일 없음"으로
죽는 상태였다 — 4개 전부 수정.

이후 실제 스크립트의 `argparse` 정의와 대조해 CLI 인자까지 정밀
검증한 결과, 추가로 3건의 실행 차단 버그를 발견·수정했다:

- **GHA 표현식 문법 오류**: `phase14_model_validation.yml`이
  `${{ matrix.country | lower }}`를 사용했다 — GitHub Actions
  표현식에는 파이프(`|`)나 `lower()` 함수 자체가 없다(Jinja/Ansible
  문법과 혼동). ONNX 변환·검증·추론 3개 스텝이 9개국 전부에서 항상
  실패하는 구조였다 — `matrix.include`로 `country_lower`를 값으로
  직접 명시하는 방식으로 교체.
- **존재하지 않는 argparse choice**: `phase14_global_train.yml`이
  `phase13_global_pipeline.py --country KR`을 호출했는데, 이 스크립트의
  `--country choices`에는 KR이 없다(한국은 `phase13_korea_model_
  trainer.py`/`korea_monthly_retrain.yml`로 완전히 분리된 전용
  파이프라인). 항상 argparse 오류로 실패하던 호출이라 제거.
- **JSON이 아닌 파일에 `.json` 확장자**: `phase13_model_registry.py`의
  `__main__`이 사람이 읽는 텍스트를 `print`하는데, `phase14_deploy.yml`이
  이 stdout을 그대로 `model_registry_status.json`으로 리다이렉트해
  커밋·아티팩트로 보관하고 있었다 — `json.dumps(get_model_summary())`로
  교체.

**검증**: 4개 워크플로우 YAML 전부 재파싱 성공, `avm_project` 전체
pytest 스위트 결과가 수정 전/후 정확히 동일(490 passed / 50 failed /
22 errors, 전부 `torch` 미설치·`ModelMetadata` 임포트 누락 등 이번
변경과 무관한 기존 문제임을 `git stash` 대조로 확인) — 회귀 없음.

**아직 막혀 있는 것**: 이 4개 워크플로우는 이제 코드상으로는 정상
동작하지만, 저장소 `default_branch`가 이 작업 브랜치
(`claude/eloquent-meitner-lqxu9r`)가 아닌 `claude/mobile-file-
organization-AuPIl`로 설정돼 있어 `workflow_dispatch` 수동 실행이
404로 거부된다. `default_branch` 변경 또는 이 브랜치 병합 중 하나가
필요하며, 저장소 설정을 세션이 임의로 바꾸지 않는다는 원칙에 따라
사용자 결정을 기다리는 중이다.

## 10. Phase 13.5 자동화 엔진이 애초에 임포트조차 안 되던 문제 (2026-09-08, 수정됨)

`phase13_automation_engine.py`(주간 KR 재학습→검증→배포결정→등록
파이프라인)는 `phase13_model_registry.py`에서 `ModelMetadata`를
임포트하고 `registry.register_model()`/`registry.list_models()`를
호출하는데, 그 모듈의 `ModelRegistry`는 추론 라우팅용 절반
(`load_model`/`get_info`/`get_model_summary`)만 구현돼 있었고 등록
API는 애초에 존재한 적이 없었다. 결과적으로
`tests/test_phase13_5_automation.py`는 수집 단계에서부터
`ImportError`로 죽어 있었고, 이 자동화 엔진 자체가 프로덕션에서도
임포트되지 않는 상태였다 — Phase 13.5는 이름만 있고 실행 불가능한
기능이었던 것.

`ModelMetadata` 데이터클래스와 `ModelRegistry.register_model()`/
`list_models()`(국가별 등록 이력을 `registry_dir` 아래 JSON으로 최신순
누적, 과거 이력을 지우지 않는 감사 가능한 구조)를 새로 구현해 해결.
기존 `model_dir`/`metadata_dir` 기반 추론 라우팅 API(`phase14_deploy.
yml`, `phase13_inference_api.py`가 사용)는 그대로 두고 `registry_dir`를
추가 파라미터로만 얹어 하위 호환을 유지했다.

**검증**: `test_phase13_5_automation.py` 10개 전부 수집 오류에서
통과로 전환. 전체 스위트 500 passed(기존 490에서 +10), 실패·에러
50/22건은 이번 변경 전후 완전히 동일한 목록(전부 `torch` 미설치,
`test_phase13_korea_model_trainer.py`/`test_model_performance.py`의
사전 학습 모델 파일 부재 등 무관한 기존 문제) — 회귀 없음.

## 11. 남아 있던 49 failed / 22 errors 정리 (2026-09-08, 수정됨)

섹션 8.3·10에서 "기존 문제"로 남겨 뒀던 실패를 원인별로 갈라 전부
처리했다. 결과: **555 passed / 9 skipped / 0 failed / 0 errors**
(`test_phase13_2_gpu_training.py` 는 `torch` 미설치 환경이라 제외).

코드 버그였던 것(수정):

- `tier2_monitoring.py`: 형제 모듈 `avm_paths` 를 flat 임포트해
  패키지 경로(`avm_project.scripts.…`)로 임포트하면 죽었다. 또 DB 기반
  메트릭 4개가 측정 실패 시 예외를 삼키고 메트릭 자체를 빠뜨려
  "5개 메트릭 보고"가 실제로는 1개만 나왔다 — 실패도 `UNAVAILABLE`
  상태로 남기게 바꾸고, 기본 `sqlite3.connect()` 가 DB가 없으면 빈
  파일을 만들어 버리던 것을 읽기 전용 URI 연결로 막았다.
- `phase12_validator.py`: 테스트와 파이프라인이 기대하는
  `Phase12Validator().validate_workbook(path) -> dict` API가 없고
  `Phase12Validator(path).validate_all()` 만 있었다(ModelRegistry와 같은
  "두 설계가 합쳐지지 않은" 패턴). 기존 API는 그대로 두고 추가.
- `api_server.py` `/predict/confidence`: 모델 로드를 입력 검증보다
  먼저 해서 잘못된 `confidence` 가 모델 없는 환경에선 400 대신 404로
  나왔다 — 순서 교정.
- `requirements.txt` 에 `pytest-benchmark` 누락(backend 쪽에만 있었다).

데이터·산출물 부재였던 것(테스트를 자급자족/명시적 skip으로):

- `test_phase13_korea_model_trainer.py` 16건: `data/raw/KR_raw.csv` 가
  없으면 즉시 에러였다. `phase13_real_data_kr.py` 가 실제로는 네트워크
  없이 도는 합성 생성기이므로, 파일이 없을 때 그걸로 임시 CSV를 만들어
  쓰게 했다 — 18/18 통과(스태킹 학습이라 약 4분).
- `test_kr_valuation.py`/`test_avm_engine.py` 34건: `output/trained_
  models/` 가 비어 있었다. 프로젝트 자체 파이프라인
  (`generate_kr_realistic_data.py` → `train_kr_model.py` →
  `avm_coldstart.py`, 전부 합성 데이터)으로 만들면 80/80 통과한다.
  산출물은 `.gitignore` 대상이라 커밋되지 않으므로, 모델이 없는
  환경에서는 "가격 ≤ 0" 같은 오해할 실패 대신 생성 명령을 적은 skip이
  나오게 픽스처를 고쳤다. 학습 결과(3/3 모델 목표 미달, MAPE 11~13%)는
  섹션 1·5의 정직한 현황과 일치한다 — 새 문제가 아니다.
- `test_model_performance.py`/`test_api_endpoints.py` 예측 3건:
  `models/*.joblib` 은 **실데이터**(외장하드의 real_estate_2024·signal)로
  학습한 산출물이라 이 환경에서 만들 수 없다(합성으로 만들면 "real"
  모델을 위조하는 셈). 산출물이 없으면 이유를 적어 skip.

**재현되지 않은 것**: 첫 전체 실행 직후 `config/automation_schedule.
json`·`crontab_entries.txt`·`monitoring_setup.json` 세 파일의 타임스탬프가
바뀌어 있었다. 쓰는 스크립트(`setup_cron_automation.py`,
`production_monitoring_setup.py`)를 테스트에서 부르는 경로는 없고, 이후
파일별 실행 1회 + 전체 실행 5회에서 재현되지 않았다. 원인 미상으로
남기며, 전체 실행 후 `git status config/` 확인을 습관으로 둔다.

