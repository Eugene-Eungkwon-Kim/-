# Loan4U AVM Engine - 상세 명세서 (Detailed Specification)

**문서 버전**: 1.0  
**작성일**: 2026-06-30  
**상태**: Ready for Implementation  
**대상**: Phase 13.4 - NPU-based AVM API Service  

---

## Executive Summary

**목표**: 프로덕션급 자동감정가 모델(AVM) 엔진 구축  
**범위**: 5개 컴포넌트, 7개 모듈, 약 2,500 lines of code  
**일정**: 25-35 working days  
**투입 인력**: 1명 (Senior Python Engineer)  
**성과물**: 
- 통합 AVM 엔진 (3-모델 앙상블)
- FastAPI 기반 REST API
- NPU 최적화 배포
- 모니터링 대시보드

---

## Part 1: 시스템 아키텍처 명세

### 1.1 시스템 개요

```
Input Layer          Processing Layer          Output Layer
┌──────────────────┐ ┌────────────────────┐ ┌──────────────────┐
│ Property Data    │ │ AVM Core Engine    │ │ Valuation Result │
│ • area_sqm       │→│ • Feature Eng.     │→│ • Price          │
│ • old_price      │ │ • Ensemble Pred.   │ │ • Confidence     │
│ • latitude       │ │ • Correction       │ │ • Validation     │
│ • longitude      │ │ • Validation       │ │ • Auction Price  │
│ • property_type  │ │ • Auction Est.     │ │ • Latency        │
│ • district_grade │ │ • Caching          │ │ • Version        │
└──────────────────┘ └────────────────────┘ └──────────────────┘
```

### 1.2 설계 원칙

| 원칙 | 설명 | 구현 |
|-----|------|------|
| **Modularity** | 각 컴포넌트 독립 | 5개 분리된 모듈 |
| **Performance** | 1-2ms 레이턴시 | NPU + 캐싱 + 폴백 |
| **Reliability** | 신뢰도 > 85% | 앙상블 + 검증 + 이상탐지 |
| **Maintainability** | 간편한 버전 관리 | 모델 레지스트리 시스템 |
| **Extensibility** | 새 기능 추가 용이 | 플러그인 아키텍처 |
| **Scalability** | 동시 요청 처리 | FastAPI + 비동기 처리 |

---

## Part 2: 컴포넌트 상세 명세

### 2.1 Component A: Feature Engineering Module

**파일**: `scripts/avm_feature_engineering.py`  
**책임**: 입력 데이터 정규화 및 파생변수 생성  
**의존성**: numpy, pandas  

#### 2.1.1 클래스: `AVMFeatureEngineer`

```python
class AVMFeatureEngineer:
    """부동산 특성 엔지니어링"""
    
    # 정규화 범위 (Min-Max Normalization)
    FEATURE_RANGES = {
        'area_sqm': (10.0, 500.0),           # 건물 면적 (㎡)
        'old_price': (50000, 5000000),       # 기존 가격 (원)
        'latitude': (33.0, 38.0),            # 위도
        'longitude': (126.0, 131.0),         # 경도
        'property_type': (1.0, 5.0)          # 부동산 유형
    }
    
    # 부동산 유형 매핑
    PROPERTY_TYPE_MAP = {
        'apartment': 1,
        'multi_family': 2,
        'townhouse': 3,
        'officetel': 4,
        'land': 5
    }
    
    # 행정구역 등급 (법정동등급)
    DISTRICT_GRADE_MAP = {
        '1': 1, '2': 2, '3': 3,
        '4': 4, '5': 5, '6': 6
    }
```

#### 2.1.2 메서드 명세

**Method 1: `__init__()`**
- 목적: 엔지니어 초기화
- 입력: 없음
- 출력: None
- 에러 처리: 없음

**Method 2: `normalize(features: np.ndarray) -> np.ndarray`**
- 목적: Min-Max 정규화 [0, 1]
- 입력: shape (5,) float32 배열
- 공식: `(x - x_min) / (x_max - x_min)`
- 클립: `np.clip(result, 0.0, 1.0)`
- 출력: shape (5,) float32
- 에러 처리: 입력 길이 검증

**Method 3: `encode_property_type(property_type: str) -> int`**
- 목적: 문자열 유형 → 숫자 코드
- 입력: 'apartment', 'multi_family' 등
- 매핑: PROPERTY_TYPE_MAP 사용
- 기본값: 1 (아파트)
- 출력: int (1-5)

**Method 4: `create_derived_features(df: pd.DataFrame) -> pd.DataFrame`**
- 목적: 파생변수 생성
- 입력: 원본 데이터프레임
- 생성 변수:
  - `price_per_sqm = old_price / area_sqm`
  - `age = 2026 - construction_year`
  - `district_code = encode_district(district_grade)`
- 출력: 확장된 데이터프레임

**Method 5: `transform(input_dict: Dict) -> np.ndarray`**
- 목적: 입력 데이터 → 모델 입력 특성
- 입력: Dict with keys (area_sqm, old_price, latitude, longitude, property_type)
- 프로세스:
  1. 유형 인코딩
  2. 배열 변환
  3. 정규화
- 출력: shape (5,) float32
- 에러 처리: 키 누락 시 ValueError

---

### 2.2 Component B: Ensemble Prediction Engine

**파일**: `scripts/avm_ensemble_engine.py`  
**책임**: 3-모델 앙상블 예측  
**의존성**: xgboost, lightgbm, sklearn, numpy  

#### 2.2.1 클래스: `AVMEnsembleEngine`

```python
class AVMEnsembleEngine:
    """3-모델 앙상블 (XGBoost, LightGBM, GradientBoosting)"""
    
    # 모델 가중치 (Weight된 평균)
    MODEL_WEIGHTS = {
        'xgboost': 0.80,           # 주요 모델 (80%)
        'lightgbm': 0.15,          # 보조 모델 (15%)
        'gradient_boosting': 0.05  # 검증 모델 (5%)
    }
    
    # 신뢰도 계산 파라미터
    CONFIDENCE_PARAMS = {
        'base_confidence': 0.90,
        'std_penalty_factor': 0.1,  # 표준편차 페널티
        'min_confidence': 0.70
    }
```

#### 2.2.2 메서드 명세

**Method 1: `__init__(model_dir: str)`**
- 목적: 엔진 초기화
- 입력: 모델 저장 디렉토리
- 프로세스:
  1. 모델 로드 (`_load_models()`)
  2. 캐시 초기화 (LRU, size=10000)
  3. 성능 로그 초기화
- 출력: None
- 에러 처리: 모델 로드 실패 시 로깅

**Method 2: `_load_models(model_dir: str) -> Dict[str, object]`**
- 목적: 저장된 모델 로드
- 입력: 모델 디렉토리
- 소스:
  1. OpenVINO IR 모델 (output/models_ir/*.xml)
  2. Pickled sklearn 모델 (output/trained_models/*.pkl)
- 출력: {model_name: model_object}
- 에러 처리: 모델 로드 실패 → 로깅 후 계속

**Method 3: `predict(features: np.ndarray) -> Tuple[float, float, float]`**
- 목적: 앙상블 예측 수행
- 입력: shape (5,) 정규화된 특성
- 프로세스:
  1. 캐시 확인 (hit 시 반환)
  2. 각 모델 예측 수행
  3. 가중 평균 계산
  4. 표준편차 기반 신뢰도 계산
  5. 레이턴시 측정
  6. 캐시 저장
- 출력: (base_price: float, confidence: float, latency_ms: float)
- 신뢰도 공식:
  ```
  confidence = base_confidence - (std / base_price * std_penalty_factor)
  confidence = max(min_confidence, confidence)
  ```

**Method 4: `get_model_stats() -> Dict`**
- 목적: 엔진 상태 조회
- 출력:
  ```python
  {
      'models_loaded': int,
      'model_names': List[str],
      'device': 'CPU' | 'NPU',
      'cache_size': int,
      'cache_hit_rate': float,
      'avg_latency_ms': float
  }
  ```

---

### 2.3 Component C: Correction Layer

**파일**: `scripts/avm_correction_layer.py`  
**책임**: 지역별, 부동산유형별 보정값 적용 (Loan4U 방식)  
**의존성**: pandas, numpy  

#### 2.3.1 클래스: `CorrectionLayer`

```python
class CorrectionLayer:
    """부동산 가격 보정값 시스템"""
    
    # Loan4U의 지역별 낙찰가율 (부동산 유형 × 행정구역등급)
    REGION_CORRECTION_MAP = {
        'apartment': {
            '1': 1.30, '2': 1.28, '3': 1.26,
            '4': 1.24, '5': 1.22, '6': 1.20,
            'default': 1.20
        },
        'multi_family': {
            '1': 1.30, '2': 1.26, '3': 1.22,
            '4': 1.20, '5': 1.20, '6': 1.20,
            'default': 1.20
        },
        'townhouse': {
            '1': 1.30, '2': 1.26, '3': 1.22,
            '4': 1.20, '5': 1.20, '6': 1.20,
            'default': 1.20
        },
        'officetel': {
            '1': 1.20, '2': 1.18, '3': 1.16,
            '4': 1.15, '5': 1.17, '6': 1.20,
            'default': 1.20
        },
        'default': 1.20
    }
    
    # 연도별 시간 조정 인자 (기준: 2024년 = 1.0)
    TEMPORAL_ADJUSTMENT = {
        2024: 1.00,    # 기준연도
        2023: 0.95,    # 5% 하향
        2022: 0.88,    # 12% 하향
        2021: 0.82,    # 18% 하향
        2020: 0.75     # 25% 하향
    }
```

#### 2.3.2 메서드 명세

**Method 1: `__init__()`**
- 목적: 보정 레이어 초기화
- 입력: 없음
- 출력: None

**Method 2: `get_region_correction(property_type: str, district_grade: str) -> float`**
- 목적: 지역 보정값 조회
- 입력:
  - property_type: 'apartment', 'multi_family' 등
  - district_grade: '1'-'6'
- 로직: REGION_CORRECTION_MAP에서 조회
- 기본값: 1.20
- 출력: float (0.5-2.0 범위)

**Method 3: `get_temporal_adjustment(reference_year: int) -> float`**
- 목적: 연도별 시간 조정값 조회
- 입력: reference_year (2020-2024)
- 로직: TEMPORAL_ADJUSTMENT에서 조회
- 기본값: 1.0 (2024년)
- 출력: float (0.75-1.0)

**Method 4: `apply_corrections(base_price: float, property_type: str, district_grade: str, reference_year: int = 2024) -> float`**
- 목적: 기본 예측가에 모든 보정값 적용
- 입력:
  - base_price: 앙상블 예측가
  - property_type: 부동산 유형
  - district_grade: 행정구역등급
  - reference_year: 기준 연도
- 공식:
  ```
  region_factor = get_region_correction(property_type, district_grade)
  temporal_factor = get_temporal_adjustment(reference_year)
  corrected_price = base_price × region_factor × temporal_factor
  ```
- 출력: float (보정된 가격)
- 에러 처리: 입력값 범위 검증

**Method 5: `get_correction_breakdown(base_price: float, property_type: str, district_grade: str) -> Dict`**
- 목적: 보정값 상세 조회 (디버깅용)
- 출력:
  ```python
  {
      'base_price': float,
      'region_factor': float,
      'temporal_factor': float,
      'corrected_price': float,
      'region_adjustment_pct': float,
      'temporal_adjustment_pct': float
  }
  ```

---

### 2.4 Component D: Validation Engine

**파일**: `scripts/avm_validation_engine.py`  
**책임**: 예측값 검증 및 신뢰도 계산  
**의존성**: sklearn, numpy, pandas  

#### 2.4.1 클래스: `ValidationEngine`

```python
class ValidationEngine:
    """예측값 검증 및 신뢰도 평가"""
    
    # 이상탐지 파라미터
    ANOMALY_DETECTION_CONFIG = {
        'contamination': 0.05,  # 예상 이상치 비율
        'random_state': 42
    }
    
    # 신뢰도 구간 파라미터
    CONFIDENCE_INTERVAL_CONFIG = {
        'confidence_level': 0.95,
        'z_score_95pct': 1.96,
        'z_score_99pct': 2.576
    }
    
    # 공시가격 편차 임계값
    APPRAISAL_TOLERANCE = {
        'warning': 0.10,   # 10% - 경고
        'critical': 0.20   # 20% - 위험
    }
```

#### 2.4.2 메서드 명세

**Method 1: `__init__()`**
- 목적: 엔진 초기화
- 프로세스:
  1. AnomalyDetector 초기화
  2. ConfidenceEstimator 초기화
- 출력: None

**Method 2: `check_anomaly(features: List[float]) -> Dict`**
- 목적: 이상치 감지
- 입력: 정규화된 특성
- 출력:
  ```python
  {
      'is_anomaly': bool,
      'anomaly_score': float (-1.0 ~ 1.0),
      'interpretation': 'normal' | 'anomaly'
  }
  ```

**Method 3: `estimate_confidence_interval(features: List[float], base_price: float) -> Dict`**
- 목적: 신뢰도 구간 계산
- 입력: 특성, 기본 예측가
- 출력:
  ```python
  {
      'prediction': float,
      'lower_bound': float,
      'upper_bound': float,
      'std': float,
      'confidence_level': float
  }
  ```

**Method 4: `check_appraisal_range(predicted_price: float, public_appraisal_price: float) -> Dict`**
- 목적: 공시가격 범위 검증
- 입력: 예측가, 공시가격
- 계산:
  ```
  deviation = abs(predicted_price - public_appraisal_price) / public_appraisal_price
  ```
- 출력:
  ```python
  {
      'deviation_pct': float,
      'status': 'acceptable' | 'warning' | 'critical',
      'message': str
  }
  ```

**Method 5: `validate(features: List[float], predicted_price: float, public_appraisal_price: Optional[float] = None) -> Dict`**
- 목적: 종합 검증
- 입력: 특성, 예측가, 선택적 공시가격
- 프로세스:
  1. 이상탐지 수행
  2. 신뢰도 구간 계산
  3. 공시가격 검증 (제공시)
  4. 최종 신뢰도 조정
- 출력:
  ```python
  {
      'is_valid': bool,
      'anomaly_score': float,
      'anomaly_status': str,
      'confidence_interval': Dict,
      'appraisal_check': Dict,
      'final_confidence': float,
      'risk_level': 'low' | 'medium' | 'high'
  }
  ```

---

### 2.5 Component E: Auction Price Module

**파일**: `scripts/avm_auction_module.py`  
**책임**: 낙찰가 예상 (Loan4U 공식)  
**의존성**: numpy, pandas  

#### 2.5.1 클래스: `AuctionModule`

```python
class AuctionModule:
    """낙찰가 예상: Base × Region Rate × Market Adjustment"""
    
    # 시장 상황별 조정 인자
    MARKET_CONDITIONS = {
        'rising': 1.05,      # 상승장 (+5%)
        'normal': 1.00,      # 보통 (기준)
        'declining': 0.95    # 하강장 (-5%)
    }
    
    # Loan4U 지역별 낙찰가율
    REGION_RATES = {
        'apartment': {
            '1': 1.30, '2': 1.28, '3': 1.26,
            '4': 1.24, '5': 1.22, '6': 1.20
        },
        'multi_family': {
            '1': 1.30, '2': 1.26, '3': 1.22,
            '4': 1.20, '5': 1.20, '6': 1.20
        },
        'townhouse': {
            '1': 1.30, '2': 1.26, '3': 1.22,
            '4': 1.20, '5': 1.20, '6': 1.20
        },
        'officetel': {
            '1': 1.20, '2': 1.18, '3': 1.16,
            '4': 1.15, '5': 1.17, '6': 1.20
        }
    }
```

#### 2.5.2 메서드 명세

**Method 1: `__init__()`**
- 목적: 모듈 초기화
- 출력: None

**Method 2: `get_region_rate(property_type: str, district_grade: str) -> float`**
- 목적: 지역별 낙찰가율 조회
- 입력: 부동산 유형, 등급
- 로직: REGION_RATES 테이블 참조
- 기본값: 1.20
- 출력: float

**Method 3: `get_market_factor(market_condition: str) -> float`**
- 목적: 시장 상황 조정값 조회
- 입력: 'rising', 'normal', 'declining'
- 기본값: 'normal'
- 출력: float

**Method 4: `estimate_auction_price(base_price: float, property_type: str, district_grade: str, market_condition: str = 'normal') -> Dict`**
- 목적: 낙찰 예상가 계산 (Loan4U 공식)
- 입력:
  - base_price: 기본 예측가
  - property_type: 부동산 유형
  - district_grade: 행정구역등급
  - market_condition: 시장 상황
- 공식:
  ```
  region_rate = get_region_rate(property_type, district_grade)
  market_factor = get_market_factor(market_condition)
  estimated_auction_price = base_price × region_rate × market_factor
  ```
- 출력:
  ```python
  {
      'base_price': float,
      'region_rate': float,
      'market_factor': float,
      'estimated_auction_price': float,
      'confidence': float (0.85-0.95)
  }
  ```

---

### 2.6 Component F: AVM Core Engine (Integration)

**파일**: `scripts/avm_core_engine.py`  
**책임**: 모든 컴포넌트 통합  
**의존성**: 위의 모든 컴포넌트  

#### 2.6.1 클래스: `AVMCoreEngine`

```python
class AVMCoreEngine:
    """통합 AVM 엔진"""
    
    # 모듈 버전
    VERSION = 'v1.0-ensemble'
    
    # 설정 파일
    CONFIG_PATH = 'config/avm_config.json'
```

#### 2.6.2 메서드 명세

**Method 1: `__init__(config_path: str = CONFIG_PATH)`**
- 목적: 엔진 초기화
- 프로세스:
  1. 설정 파일 로드
  2. 각 컴포넌트 초기화
  3. 성능 로깅 시스템 준비
- 출력: None

**Method 2: `valuate(area_sqm: float, old_price: float, latitude: float, longitude: float, property_type: str, district_grade: str = '3', public_appraisal_price: Optional[float] = None) -> Dict`**
- 목적: 완전한 부동산 가치평가
- 입력:
  - area_sqm: 건물 면적 (10-500 ㎡)
  - old_price: 기존 가격 (50,000-5,000,000 원)
  - latitude: 위도 (33-38)
  - longitude: 경도 (126-131)
  - property_type: 'apartment', 'multi_family' 등
  - district_grade: '1'-'6' (기본값: '3')
  - public_appraisal_price: 공시가격 (선택)
- 프로세스:
  1. **특성 엔지니어링**: 정규화
  2. **앙상블 예측**: base_price 계산
  3. **보정값 적용**: corrected_price 계산
  4. **검증**: 이상탐지, 신뢰도 구간, 공시가격 확인
  5. **낙찰가 추정**: auction_forecast 계산
  6. **최종 신뢰도 조정**: validation 결과 반영
- 출력:
  ```python
  {
      'base_price': float,           # 앙상블 예측가
      'corrected_price': float,      # 보정된 최종 예측가
      'confidence': float,           # 최종 신뢰도 (0-1)
      'validation_status': bool,     # 검증 통과 여부
      'validation': {
          'is_valid': bool,
          'anomaly_score': float,
          'anomaly_status': str,
          'confidence_interval': Dict,
          'appraisal_check': Dict,
          'risk_level': str
      },
      'auction_forecast': {
          'base_price': float,
          'region_rate': float,
          'market_factor': float,
          'estimated_auction_price': float,
          'confidence': float
      },
      'latency_ms': float,           # 응답 시간
      'model_version': str,          # v1.0-ensemble
      'timestamp': str               # ISO 8601 timestamp
  }
  ```

**Method 3: `batch_valuate(properties: List[Dict]) -> List[Dict]`**
- 목적: 대량 가치평가
- 입력: 부동산 정보 딕셔너리 리스트
- 처리: 각 부동산에 대해 valuate() 호출
- 출력: valuate() 결과 리스트
- 성능: 캐시를 통한 중복 제거

**Method 4: `get_engine_stats() -> Dict`**
- 목적: 엔진 상태 및 성능 통계
- 출력:
  ```python
  {
      'version': str,
      'status': 'ready' | 'degraded',
      'components': {
          'ensemble': {...},
          'cache': {...},
          'models': [...]
      },
      'performance': {
          'avg_latency_ms': float,
          'cache_hit_rate': float,
          'predictions_count': int
      },
      'uptime_hours': float
  }
  ```

---

### 2.7 Component G: FastAPI Service

**파일**: `scripts/avm_api_service.py`  
**책임**: REST API 엔드포인트  
**의존성**: fastapi, uvicorn, pydantic  

#### 2.7.1 Pydantic 모델

```python
class PropertyInput(BaseModel):
    """부동산 입력 데이터"""
    area_sqm: float = Field(..., gt=0, le=1000)
    old_price: float = Field(..., gt=0, le=10000000)
    latitude: float = Field(..., ge=33, le=38)
    longitude: float = Field(..., ge=126, le=131)
    property_type: str = Field(..., pattern='^(apartment|multi_family|townhouse|officetel|land)$')
    district_grade: str = Field(default='3', pattern='^[1-6]$')
    public_appraisal_price: Optional[float] = Field(default=None, gt=0)

class ValuationResponse(BaseModel):
    """가치평가 응답"""
    base_price: float
    corrected_price: float
    confidence: float
    validation_status: bool
    validation: Dict
    auction_forecast: Dict
    latency_ms: float
    model_version: str
    timestamp: str

class EngineStatusResponse(BaseModel):
    """엔진 상태 응답"""
    status: str
    models_loaded: int
    device: str
    cache_hit_rate: float
    avg_latency_ms: float
```

#### 2.7.2 엔드포인트 명세

| Method | Path | 설명 | 입력 | 출력 |
|--------|------|------|------|------|
| POST | `/api/valuate` | 부동산 가치평가 | PropertyInput | ValuationResponse |
| POST | `/api/batch-valuate` | 대량 가치평가 | List[PropertyInput] | List[ValuationResponse] |
| POST | `/api/auction-forecast` | 낙찰가 추정 | PropertyInput | Dict |
| GET | `/api/engine-status` | 엔진 상태 | - | EngineStatusResponse |
| GET | `/api/health` | 헬스체크 | - | {status, engine} |
| GET | `/api/models` | 모델 정보 | - | {models_loaded, device} |
| GET | `/` | API 루트 | - | {service, version, docs} |

---

## Part 3: 데이터 명세

### 3.1 입력 데이터 스펙

| 필드 | 타입 | 범위 | 단위 | 검증 |
|------|------|------|------|------|
| area_sqm | float | 10-500 | ㎡ | > 0, <= 1000 |
| old_price | float | 50K-5M | 원 | > 0, <= 10M |
| latitude | float | 33-38 | 도 | >= 33, <= 38 |
| longitude | float | 126-131 | 도 | >= 126, <= 131 |
| property_type | str | 5종류 | - | enum check |
| district_grade | str | 1-6 | - | pattern ^[1-6]$ |
| construction_year | int | 1970-2026 | - | optional |

### 3.2 출력 데이터 스펙

| 필드 | 타입 | 범위 | 설명 |
|------|------|------|------|
| base_price | float | 100K-10M | 앙상블 예측가 |
| corrected_price | float | 100K-15M | 보정된 최종가 |
| confidence | float | 0.70-1.0 | 신뢰도 |
| latency_ms | float | 1-100 | 응답시간 |
| model_version | str | v1.0+ | 모델 버전 |
| timestamp | str | ISO8601 | UTC 타임스탬프 |

---

## Part 4: 성능 요구사항

### 4.1 지연시간 (Latency)

| 항목 | 목표 | 허용값 | 측정 방법 |
|------|------|--------|---------|
| 평균 응답시간 | 2ms | 1-5ms | time.perf_counter() |
| P95 응답시간 | 3ms | <10ms | 100개 샘플 측정 |
| P99 응답시간 | 5ms | <20ms | 1000개 샘플 측정 |

### 4.2 정확도 (Accuracy)

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| R² Score | > 0.84 | sklearn.metrics.r2_score |
| MAPE | < 10.5% | Mean Absolute Percentage Error |
| 신뢰도 | > 0.85 | 평균 confidence 점수 |

### 4.3 신뢰성 (Reliability)

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| 가용성 | > 99.5% | uptime / total_time |
| 캐시 히트율 | > 40% | cache_hits / total_requests |
| 에러율 | < 0.1% | error_count / total_requests |

### 4.4 확장성 (Scalability)

| 항목 | 목표 | 구현 |
|------|------|------|
| 동시 요청 | 100+ req/sec | FastAPI 비동기 처리 |
| 메모리 사용 | < 2GB | 모델 캐싱 및 LRU 정책 |
| 캐시 크기 | 10,000개 | OrderedDict 관리 |

---

## Part 5: 에러 처리 및 복구

### 5.1 에러 분류

| 에러 타입 | HTTP 코드 | 설명 | 복구 전략 |
|-----------|----------|------|---------|
| ValidationError | 422 | 입력값 검증 실패 | 클라이언트에 사유 반환 |
| ModelNotLoaded | 503 | 모델 로드 실패 | 폴백 모델 사용 |
| AnomalyDetected | 206 | 이상치 감지 | 신뢰도 감소 후 반환 |
| CacheError | 500 | 캐시 작업 실패 | 캐시 무시 후 재계산 |
| TimeoutError | 504 | 타임아웃 | 부분 결과 반환 |

### 5.2 복구 메커니즘

```python
# 1. 모델 폴백
if xgboost_fail:
    use_lightgbm
elif lightgbm_fail:
    use_gradient_boosting

# 2. 캐시 폴백
if cache_fail:
    recalculate_prediction()
    skip_caching()

# 3. 부분 검증
if full_validation_fail:
    skip_anomaly_detection
    reduce_confidence_by_30%
```

---

## Part 6: 테스트 계획

### 6.1 단위 테스트 (Unit Tests)

| 모듈 | 테스트 케이스 | 목표 커버리지 |
|------|-------------|------------|
| feature_engineering.py | 12개 | > 95% |
| ensemble_engine.py | 10개 | > 90% |
| correction_layer.py | 8개 | > 95% |
| validation_engine.py | 15개 | > 92% |
| auction_module.py | 6개 | > 95% |
| core_engine.py | 10개 | > 90% |

### 6.2 통합 테스트 (Integration Tests)

```python
# test_full_pipeline.py
def test_complete_valuation_flow():
    """완전한 가치평가 흐름"""
    engine = AVMCoreEngine()
    result = engine.valuate(
        area_sqm=100,
        old_price=500000,
        latitude=35.5,
        longitude=126.8,
        property_type='apartment',
        district_grade='3'
    )
    assert result['corrected_price'] > 0
    assert 0.70 <= result['confidence'] <= 1.0
```

### 6.3 성능 테스트 (Performance Tests)

```python
# test_performance.py
def test_latency():
    """레이턴시 측정"""
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        engine.valuate(...)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    assert np.mean(latencies) < 2.0  # 평균 2ms 이하
    assert np.percentile(latencies, 95) < 5.0  # P95 < 5ms
```

---

## Part 7: 배포 및 모니터링

### 7.1 배포 전략

```bash
# 1. 로컬 테스트
pytest tests/ -v --cov=scripts

# 2. NPU 최적화 변환
python scripts/phase13_model_converter.py --output output/models_ir

# 3. 서비스 시작
python scripts/avm_api_service.py --host 0.0.0.0 --port 8000

# 4. 헬스체크
curl http://localhost:8000/api/health
```

### 7.2 모니터링 항목

```python
MONITORING_METRICS = {
    'performance': ['avg_latency_ms', 'p95_latency', 'p99_latency'],
    'accuracy': ['r2_score', 'mape', 'confidence_mean'],
    'reliability': ['uptime_pct', 'error_rate', 'cache_hit_rate'],
    'business': ['predictions_count', 'batch_valuations', 'api_calls']
}
```

---

**문서 끝**  
**다음 단계**: WBS (Work Breakdown Structure) 문서 참조
