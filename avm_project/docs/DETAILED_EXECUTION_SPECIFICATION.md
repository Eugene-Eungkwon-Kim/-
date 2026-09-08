# AVM 엔진 - 상세 실행 명세서 (Detailed Execution Specification)

**문서 버전**: 2.0  
**작성일**: 2026-06-30  
**대상**: Phase 13.4 개발자 (Day 1-35)  
**상태**: Ready for Development  

---

## Part 1: 개발자 온보딩 (Day 0)

### 1.1 사전 체크리스트

```bash
# 1. 환경 확인
python --version          # 3.9+ 필수
pip --version
git --version

# 2. 저장소 클론
cd /home/user/-
git clone <repo>
cd avm_project

# 3. 브랜치 전환
git checkout claude/eloquent-meitner-lqxu9r
git pull origin claude/eloquent-meitner-lqxu9r

# 4. 의존성 설치
pip install -r requirements.txt
pip install pytest pytest-cov mypy black pylint

# 5. 구조 확인
ls -la avm_project/scripts/
ls -la avm_project/config/
ls -la avm_project/data/raw/
```

### 1.2 코드 스타일 가이드

**Python 명명 규칙**
```python
# 클래스: PascalCase
class AVMFeatureEngineer:
    pass

# 함수/메서드: snake_case
def normalize_features(features: np.ndarray) -> np.ndarray:
    pass

# 상수: UPPER_SNAKE_CASE
FEATURE_MIN = np.array([10.0, 50000.0, 33.0, 126.0, 1.0])

# 변수: snake_case
normalized_price = base_price * region_factor
```

**함수 길이 기준**
- 일반 함수: < 50줄
- 복잡한 로직: < 100줄 (예외)
- 분기/루프 깊이: < 3단계

**Type Hints (필수)**
```python
def valuate(
    self,
    area_sqm: float,
    old_price: float,
    latitude: float,
    longitude: float,
    property_type: str,
    district_grade: str = '3',
    public_appraisal_price: Optional[float] = None
) -> Dict[str, Any]:
    """부동산 가치평가"""
    pass
```

**Docstring (필수)**
```python
def normalize(self, features: np.ndarray) -> np.ndarray:
    """Min-Max 정규화 [0, 1]."""
    # 공식: (x - x_min) / (x_max - x_min)
    normalized = (features - self.feature_min) / (self.feature_max - self.feature_min)
    return np.clip(normalized, 0.0, 1.0)
```

---

## Part 2: 각 모듈별 상세 구현 명세

### 2.1 Module A: Feature Engineering (`avm_feature_engineering.py`)

#### 2.1.1 파일 구조
```python
# avm_feature_engineering.py (250 lines)

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging

log = logging.getLogger(__name__)

# 상수 정의 (Lines 1-40)
FEATURE_RANGES = {...}
PROPERTY_TYPE_MAP = {...}
DISTRICT_GRADE_MAP = {...}

# 클래스 정의 (Lines 41-250)
class AVMFeatureEngineer:
    def __init__(self): ...
    def normalize(self, features: np.ndarray) -> np.ndarray: ...
    def encode_property_type(self, property_type: str) -> int: ...
    def encode_district_grade(self, district_grade: str) -> int: ...
    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def transform(self, input_dict: Dict) -> np.ndarray: ...
```

#### 2.1.2 메서드별 구현 가이드

**Method 1: `__init__()`** (5 lines)
```python
def __init__(self) -> None:
    """엔지니어 초기화"""
    self.feature_min = np.array([10.0, 50000.0, 33.0, 126.0, 1.0], dtype=np.float32)
    self.feature_max = np.array([500.0, 5000000.0, 38.0, 131.0, 5.0], dtype=np.float32)
    self.is_fitted = True
```

**Method 2: `normalize()`** (10 lines)
```python
def normalize(self, features: np.ndarray) -> np.ndarray:
    """Min-Max 정규화 [0, 1]."""
    if features.shape[0] != len(self.feature_min):
        raise ValueError(f"Expected {len(self.feature_min)} features, got {features.shape[0]}")
    
    normalized = (features - self.feature_min) / (self.feature_max - self.feature_min)
    normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)
    
    log.debug(f"Normalized: {features} → {normalized}")
    return normalized
```

**Method 3: `encode_property_type()`** (8 lines)
```python
def encode_property_type(self, property_type: str) -> int:
    """부동산 유형 인코딩 (1-5)."""
    pt_lower = property_type.lower().strip()
    
    if pt_lower not in self.PROPERTY_TYPE_MAP:
        log.warning(f"Unknown property type: {property_type}, using default (apartment=1)")
        return 1
    
    return self.PROPERTY_TYPE_MAP[pt_lower]
```

**Method 4: `encode_district_grade()`** (8 lines)
```python
def encode_district_grade(self, district_grade: str) -> int:
    """행정구역 등급 인코딩 (1-6)."""
    grade_str = str(district_grade).strip()
    
    if grade_str not in self.DISTRICT_GRADE_MAP:
        log.warning(f"Invalid grade: {district_grade}, using default (3)")
        return 3
    
    return self.DISTRICT_GRADE_MAP[grade_str]
```

**Method 5: `create_derived_features()`** (15 lines)
```python
def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """파생변수 생성"""
    df_copy = df.copy()
    
    # price_per_sqm
    df_copy['price_per_sqm'] = df_copy['old_price'] / df_copy['area_sqm']
    df_copy['price_per_sqm'] = df_copy['price_per_sqm'].fillna(0)
    
    # age (if construction_year exists)
    if 'construction_year' in df_copy.columns:
        df_copy['age'] = 2026 - df_copy['construction_year']
        df_copy['age'] = df_copy['age'].clip(0, 200)  # 음수/극단값 처리
    
    log.info(f"Created derived features: {list(df_copy.columns)}")
    return df_copy
```

**Method 6: `transform()`** (20 lines)
```python
def transform(self, input_dict: Dict) -> np.ndarray:
    """입력 데이터 → 모델 입력 특성"""
    required_keys = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
    
    # 필수 키 확인
    missing = set(required_keys) - set(input_dict.keys())
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    
    # 1. 유형 인코딩
    property_type_encoded = self.encode_property_type(input_dict['property_type'])
    
    # 2. 배열 생성
    features = np.array([
        input_dict['area_sqm'],
        input_dict['old_price'],
        input_dict['latitude'],
        input_dict['longitude'],
        float(property_type_encoded)
    ], dtype=np.float32)
    
    # 3. 정규화
    normalized = self.normalize(features)
    
    log.debug(f"Transformed: {features} → {normalized}")
    return normalized
```

#### 2.1.3 단위 테스트 (10 케이스)
```python
# tests/test_feature_engineering.py

def test_normalize_range():
    """정규화 범위 확인"""
    engineer = AVMFeatureEngineer()
    features = np.array([100, 500000, 35.5, 126.8, 2], dtype=np.float32)
    normalized = engineer.normalize(features)
    
    assert np.all(normalized >= 0.0) and np.all(normalized <= 1.0)
    assert normalized.dtype == np.float32

def test_encode_property_type():
    """부동산 유형 인코딩"""
    engineer = AVMFeatureEngineer()
    
    assert engineer.encode_property_type('apartment') == 1
    assert engineer.encode_property_type('APARTMENT') == 1
    assert engineer.encode_property_type('unknown') == 1  # 기본값

def test_transform_complete():
    """전체 변환 파이프라인"""
    engineer = AVMFeatureEngineer()
    input_data = {
        'area_sqm': 100,
        'old_price': 500000,
        'latitude': 35.5,
        'longitude': 126.8,
        'property_type': 'apartment'
    }
    
    result = engineer.transform(input_data)
    assert result.shape == (5,)
    assert np.all(result >= 0.0) and np.all(result <= 1.0)

# ... (7개 추가 테스트 케이스)
```

---

### 2.2 Module B: Ensemble Engine (`avm_ensemble_engine.py`)

#### 2.2.1 파일 구조
```python
# avm_ensemble_engine.py (300 lines)

import numpy as np
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from collections import OrderedDict
import pickle
import time

log = logging.getLogger(__name__)

# 상수 (Lines 1-30)
MODEL_WEIGHTS = {'xgboost': 0.80, 'lightgbm': 0.15, 'gradient_boosting': 0.05}
CONFIDENCE_PARAMS = {...}

# 클래스 (Lines 31-300)
class AVMEnsembleEngine:
    def __init__(self, model_dir: str): ...
    def _load_models(self, model_dir: str) -> Dict[str, object]: ...
    def _load_ir_models(self, ir_dir: Path) -> Dict[str, object]: ...
    def _load_pickled_models(self, pkl_dir: Path) -> Dict[str, object]: ...
    def predict(self, features: np.ndarray) -> Tuple[float, float, float]: ...
    def _calculate_confidence(self, predictions: List[float]) -> float: ...
    def get_model_stats(self) -> Dict: ...
```

#### 2.2.2 주요 메서드 구현

**Method 1: `__init__()`** (15 lines)
```python
def __init__(self, model_dir: str) -> None:
    """앙상블 엔진 초기화"""
    self.model_dir = Path(model_dir)
    self.models: Dict[str, object] = {}
    self.cache = OrderedDict()  # LRU 캐시
    self.cache_maxsize = 10000
    self.cache_hits = 0
    self.cache_misses = 0
    self.predictions_count = 0
    self.latencies: List[float] = []
    
    self._load_models(model_dir)
    log.info(f"Ensemble engine initialized with {len(self.models)} models")
```

**Method 2: `_load_models()`** (25 lines)
```python
def _load_models(self, model_dir: str) -> None:
    """모델 로드 (IR 우선, 폴백: pickle)"""
    ir_dir = Path(model_dir)
    
    # 1. OpenVINO IR 모델 로드 시도
    ir_models = self._load_ir_models(ir_dir)
    self.models.update(ir_models)
    
    # 2. Pickle 모델 로드 (폴백)
    pkl_dir = ir_dir.parent / 'trained_models'
    if pkl_dir.exists() and not self.models:
        pkl_models = self._load_pickled_models(pkl_dir)
        self.models.update(pkl_models)
    
    if not self.models:
        log.error(f"No models found in {model_dir}")
```

**Method 3: `predict()`** (35 lines)
```python
def predict(self, features: np.ndarray) -> Tuple[float, float, float]:
    """앙상블 예측 수행"""
    start = time.perf_counter()
    
    # 1. 캐시 확인
    cache_key = tuple(features)
    if cache_key in self.cache:
        self.cache_hits += 1
        cached = self.cache[cache_key]
        log.debug(f"Cache hit: {cache_key}")
        return cached
    
    self.cache_misses += 1
    
    # 2. 각 모델에서 예측
    predictions = []
    for model_name, model in self.models.items():
        try:
            if hasattr(model, 'predict'):  # sklearn 스타일
                pred = float(model.predict(features.reshape(1, -1))[0])
            else:  # OpenVINO 스타일
                pred = float(model(features)[0])
            
            predictions.append(pred)
        except Exception as e:
            log.warning(f"Model {model_name} prediction failed: {e}")
    
    if not predictions:
        log.error("No valid predictions from any model")
        return 0.0, 0.0, 0.0
    
    # 3. 가중 평균
    base_price = sum(
        pred * self.MODEL_WEIGHTS.get(name, 0.05)
        for pred, name in zip(predictions, self.models.keys())
    )
    
    # 4. 신뢰도 계산
    confidence = self._calculate_confidence(predictions)
    
    # 5. 레이턴시 측정
    latency_ms = (time.perf_counter() - start) * 1000.0
    self.latencies.append(latency_ms)
    
    # 6. 캐시 저장
    if len(self.cache) >= self.cache_maxsize:
        self.cache.popitem(last=False)  # LRU 제거
    self.cache[cache_key] = (base_price, confidence, latency_ms)
    
    self.predictions_count += 1
    return base_price, confidence, latency_ms
```

**Method 4: `_calculate_confidence()`** (12 lines)
```python
def _calculate_confidence(self, predictions: List[float]) -> float:
    """표준편차 기반 신뢰도 계산"""
    if len(predictions) < 2:
        return self.CONFIDENCE_PARAMS['base_confidence']
    
    mean_pred = np.mean(predictions)
    std_pred = np.std(predictions)
    
    # 신뢰도 = base - (std / mean) × penalty
    penalty = (std_pred / mean_pred * 100) * self.CONFIDENCE_PARAMS['std_penalty_factor']
    confidence = self.CONFIDENCE_PARAMS['base_confidence'] - penalty
    
    return max(self.CONFIDENCE_PARAMS['min_confidence'], confidence)
```

#### 2.2.3 성능 벤치마크 테스트
```python
# tests/test_ensemble_performance.py

def test_latency_p95():
    """P95 레이턴시 < 5ms"""
    engine = AVMEnsembleEngine('output/models_ir')
    
    latencies = []
    for _ in range(100):
        features = np.random.rand(5).astype(np.float32)
        _, _, latency = engine.predict(features)
        latencies.append(latency)
    
    p95 = np.percentile(latencies, 95)
    assert p95 < 5.0, f"P95 latency {p95}ms exceeds 5ms target"

def test_cache_hit_rate():
    """캐시 히트율 > 40%"""
    engine = AVMEnsembleEngine('output/models_ir')
    
    # 중복 예측
    features = np.array([100, 500000, 35.5, 126.8, 2], dtype=np.float32)
    for _ in range(100):
        engine.predict(features)
    
    hit_rate = engine.cache_hits / (engine.cache_hits + engine.cache_misses)
    assert hit_rate > 0.40
```

---

### 2.3 Module C: Correction Layer (`avm_correction_layer.py`)

#### 2.3.1 구현 명세

```python
# avm_correction_layer.py (150 lines)

import numpy as np
import pandas as pd
from typing import Dict, Tuple

class CorrectionLayer:
    """지역별, 시간별 보정값 적용"""
    
    # Loan4U 지역별 낙찰가율 (부동산 유형 × 등급)
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
    
    # 연도별 시간 조정 (기준: 2024 = 1.0)
    TEMPORAL_ADJUSTMENT = {
        2024: 1.00, 2023: 0.95, 2022: 0.88,
        2021: 0.82, 2020: 0.75
    }
```

#### 2.3.2 핵심 메서드

```python
def get_region_correction(self, property_type: str, district_grade: str) -> float:
    """지역 보정값 조회"""
    pt_map = self.REGION_CORRECTION_MAP.get(property_type.lower(), {})
    return pt_map.get(district_grade, pt_map.get('default', 1.20))

def apply_corrections(
    self,
    base_price: float,
    property_type: str,
    district_grade: str,
    reference_year: int = 2024
) -> float:
    """보정값 적용: Base × Region × Temporal"""
    region_factor = self.get_region_correction(property_type, district_grade)
    temporal_factor = self.TEMPORAL_ADJUSTMENT.get(reference_year, 1.0)
    
    corrected_price = base_price * region_factor * temporal_factor
    
    return corrected_price

def get_correction_breakdown(
    self,
    base_price: float,
    property_type: str,
    district_grade: str
) -> Dict:
    """보정값 상세 분석 (디버깅용)"""
    region_factor = self.get_region_correction(property_type, district_grade)
    corrected = base_price * region_factor
    
    return {
        'base_price': base_price,
        'region_factor': region_factor,
        'corrected_price': corrected,
        'adjustment_pct': (region_factor - 1.0) * 100
    }
```

---

### 2.4 Module D: Validation Engine (`avm_validation_engine.py`)

#### 2.4.1 구조 및 알고리즘

```python
# avm_validation_engine.py (350 lines)

from sklearn.ensemble import IsolationForest
import numpy as np
from typing import Dict, Any

class ValidationEngine:
    """예측값 검증 및 신뢰도"""
    
    def __init__(self):
        """엔진 초기화"""
        self.anomaly_detector = IsolationForest(
            contamination=0.05,
            random_state=42
        )
        self.is_fitted = False
    
    def fit_anomaly_detector(self, X: np.ndarray) -> None:
        """이상탐지 모델 학습"""
        self.anomaly_detector.fit(X)
        self.is_fitted = True
    
    def check_anomaly(self, features: np.ndarray) -> Dict[str, Any]:
        """이상치 감지"""
        if not self.is_fitted:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'status': 'not_fitted'
            }
        
        prediction = self.anomaly_detector.predict([features])[0]
        score = self.anomaly_detector.score_samples([features])[0]
        
        return {
            'is_anomaly': bool(prediction == -1),
            'anomaly_score': float(score),
            'status': 'anomaly' if prediction == -1 else 'normal'
        }
    
    def estimate_confidence_interval(
        self,
        predicted_price: float,
        std: float = None,
        confidence_level: float = 0.95
    ) -> Dict[str, float]:
        """신뢰도 구간 (Z-score 기반)"""
        if std is None:
            std = abs(predicted_price) * 0.05  # 예측가의 5%
        
        z_score = 1.96 if confidence_level == 0.95 else 2.576
        margin = z_score * std
        
        return {
            'prediction': predicted_price,
            'lower_bound': predicted_price - margin,
            'upper_bound': predicted_price + margin,
            'std': std,
            'confidence_level': confidence_level
        }
    
    def check_appraisal_range(
        self,
        predicted_price: float,
        public_appraisal_price: float,
        tolerance_warning: float = 0.10,
        tolerance_critical: float = 0.20
    ) -> Dict[str, Any]:
        """공시가격 범위 검증"""
        deviation = abs(predicted_price - public_appraisal_price) / public_appraisal_price
        
        if deviation <= tolerance_warning:
            status = 'acceptable'
        elif deviation <= tolerance_critical:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'deviation_pct': deviation * 100,
            'status': status,
            'message': f"Deviation {deviation*100:.1f}% vs public appraisal"
        }
    
    def validate(
        self,
        features: np.ndarray,
        predicted_price: float,
        public_appraisal_price: float = None
    ) -> Dict[str, Any]:
        """종합 검증"""
        results = {
            'is_valid': True,
            'risk_level': 'low'
        }
        
        # 1. 이상탐지
        anomaly_check = self.check_anomaly(features)
        results['anomaly'] = anomaly_check
        
        if anomaly_check['is_anomaly']:
            results['is_valid'] = False
            results['risk_level'] = 'high'
        
        # 2. 신뢰도 구간
        ci = self.estimate_confidence_interval(predicted_price)
        results['confidence_interval'] = ci
        
        # 3. 공시가격 검증
        if public_appraisal_price:
            appraisal_check = self.check_appraisal_range(
                predicted_price, public_appraisal_price
            )
            results['appraisal_check'] = appraisal_check
            
            if appraisal_check['status'] in ['warning', 'critical']:
                results['risk_level'] = 'medium' if results['risk_level'] == 'low' else 'high'
        
        return results
```

---

### 2.5 Module E: Auction Module (`avm_auction_module.py`)

#### 2.5.1 구현 명세

```python
# avm_auction_module.py (150 lines)

class AuctionModule:
    """낙찰가 추정: Base × Region × Market"""
    
    MARKET_CONDITIONS = {
        'rising': 1.05,      # +5%
        'normal': 1.00,      # 기준
        'declining': 0.95    # -5%
    }
    
    def estimate_auction_price(
        self,
        base_price: float,
        property_type: str,
        district_grade: str,
        market_condition: str = 'normal'
    ) -> Dict[str, float]:
        """Loan4U 공식: Base × Region Rate × Market Factor"""
        
        # 1. 지역 낙찰가율
        region_rate = self._get_region_rate(property_type, district_grade)
        
        # 2. 시장 조정 인자
        market_factor = self.MARKET_CONDITIONS.get(market_condition, 1.00)
        
        # 3. 낙찰 예상가 계산
        auction_price = base_price * region_rate * market_factor
        
        return {
            'base_price': base_price,
            'region_rate': region_rate,
            'market_factor': market_factor,
            'estimated_auction_price': auction_price,
            'confidence': 0.88
        }
    
    def _get_region_rate(self, property_type: str, grade: str) -> float:
        """지역별 낙찰가율 테이블"""
        rates = {
            'apartment': {
                '1': 1.30, '2': 1.28, '3': 1.26,
                '4': 1.24, '5': 1.22, '6': 1.20
            },
            'multi_family': {
                '1': 1.30, '2': 1.26, '3': 1.22,
                '4': 1.20, '5': 1.20, '6': 1.20
            }
            # ... (다른 유형)
        }
        
        default_rates = rates.get(property_type.lower(), {})
        return default_rates.get(grade, 1.20)
```

---

### 2.6 Module F: Core Engine (`avm_core_engine.py`)

#### 2.6.1 통합 엔진 구현

```python
# avm_core_engine.py (350 lines)

class AVMCoreEngine:
    """AVM 엔진 (모든 컴포넌트 통합)"""
    
    VERSION = 'v1.0-ensemble'
    
    def __init__(self, config_path: str = 'config/avm_config.json'):
        """엔진 초기화"""
        self.config = self._load_config(config_path)
        
        # 컴포넌트 초기화
        self.feature_engineer = AVMFeatureEngineer()
        self.ensemble = AVMEnsembleEngine(self.config['model_dir'])
        self.corrections = CorrectionLayer()
        self.validator = ValidationEngine()
        self.auction = AuctionModule()
        
        # 모니터링
        self.performance_log = []
        self.start_time = time.time()
    
    def valuate(
        self,
        area_sqm: float,
        old_price: float,
        latitude: float,
        longitude: float,
        property_type: str,
        district_grade: str = '3',
        public_appraisal_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """완전한 가치평가 프로세스 (5단계)"""
        
        start = time.perf_counter()
        
        try:
            # Step 1: 특성 엔지니어링
            input_dict = {
                'area_sqm': area_sqm,
                'old_price': old_price,
                'latitude': latitude,
                'longitude': longitude,
                'property_type': property_type
            }
            features = self.feature_engineer.transform(input_dict)
            
            # Step 2: 앙상블 예측
            base_price, confidence, ensemble_latency = self.ensemble.predict(features)
            
            # Step 3: 보정값 적용
            corrected_price = self.corrections.apply_corrections(
                base_price, property_type, district_grade
            )
            
            # Step 4: 검증
            validation = self.validator.validate(
                features, corrected_price, public_appraisal_price
            )
            
            # Step 5: 낙찰가 추정
            auction = self.auction.estimate_auction_price(
                corrected_price, property_type, district_grade
            )
            
            # 최종 신뢰도 조정
            final_confidence = confidence
            if not validation['is_valid']:
                final_confidence *= 0.70  # 검증 실패시 30% 감소
            
            latency_ms = (time.perf_counter() - start) * 1000.0
            
            result = {
                'base_price': float(base_price),
                'corrected_price': float(corrected_price),
                'confidence': float(final_confidence),
                'validation_status': validation['is_valid'],
                'validation': validation,
                'auction_forecast': auction,
                'latency_ms': float(latency_ms),
                'model_version': self.VERSION,
                'timestamp': datetime.now().isoformat()
            }
            
            # 로깅
            log.info(f"Valuation: {corrected_price:,.0f} KRW (conf={final_confidence:.1%}, {latency_ms:.1f}ms)")
            self.performance_log.append({
                'timestamp': datetime.now(),
                'latency_ms': latency_ms,
                'confidence': final_confidence
            })
            
            return result
            
        except Exception as e:
            log.error(f"Valuation failed: {e}")
            raise
    
    def batch_valuate(self, properties: List[Dict]) -> List[Dict]:
        """대량 가치평가"""
        results = []
        for prop in properties:
            result = self.valuate(**prop)
            results.append(result)
        return results
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """엔진 상태 및 성능 통계"""
        uptime = (time.time() - self.start_time) / 3600  # hours
        
        if self.performance_log:
            latencies = [log['latency_ms'] for log in self.performance_log]
            avg_latency = np.mean(latencies)
            p95_latency = np.percentile(latencies, 95)
            avg_confidence = np.mean([log['confidence'] for log in self.performance_log])
        else:
            avg_latency = p95_latency = avg_confidence = 0.0
        
        return {
            'version': self.VERSION,
            'status': 'ready' if self.ensemble.models else 'degraded',
            'models_loaded': len(self.ensemble.models),
            'uptime_hours': uptime,
            'predictions_count': self.ensemble.predictions_count,
            'cache_hit_rate': self.ensemble.cache_hits / max(1, self.ensemble.cache_hits + self.ensemble.cache_misses),
            'performance': {
                'avg_latency_ms': avg_latency,
                'p95_latency_ms': p95_latency,
                'avg_confidence': avg_confidence
            }
        }
```

---

### 2.7 Module G: FastAPI Service (`avm_api_service.py`)

#### 2.7.1 구현 명세

```python
# avm_api_service.py (300 lines)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import logging
from avm_core_engine import AVMCoreEngine

log = logging.getLogger(__name__)

# Pydantic 모델 (50 lines)
class PropertyInput(BaseModel):
    area_sqm: float = Field(..., gt=0, le=1000, description="건물면적(㎡)")
    old_price: float = Field(..., gt=0, le=10000000, description="기존가격(원)")
    latitude: float = Field(..., ge=33, le=38, description="위도")
    longitude: float = Field(..., ge=126, le=131, description="경도")
    property_type: str = Field(..., regex='^(apartment|multi_family|townhouse|officetel|land)$')
    district_grade: str = Field(default='3', regex='^[1-6]$')
    public_appraisal_price: Optional[float] = Field(default=None, gt=0)

class ValuationResponse(BaseModel):
    base_price: float
    corrected_price: float
    confidence: float
    validation_status: bool
    validation: Dict
    auction_forecast: Dict
    latency_ms: float
    model_version: str

# FastAPI 앱 (250 lines)
app = FastAPI(
    title="Loan4U AVM Engine",
    description="Automatic Valuation Model API",
    version="1.0.0"
)

engine = None

@app.on_event("startup")
async def startup():
    """서비스 시작시 엔진 초기화"""
    global engine
    try:
        engine = AVMCoreEngine('config/avm_config.json')
        log.info("AVM Engine initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize AVM Engine: {e}")

@app.post("/api/valuate", response_model=ValuationResponse)
async def valuate_property(request: PropertyInput) -> ValuationResponse:
    """부동산 개별 가치평가"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        result = engine.valuate(**request.dict())
        return ValuationResponse(**result)
    except Exception as e:
        log.error(f"Valuation error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.post("/api/batch-valuate")
async def batch_valuate(requests: List[PropertyInput]) -> List[Dict]:
    """대량 가치평가"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        property_dicts = [r.dict() for r in requests]
        results = engine.batch_valuate(property_dicts)
        return results
    except Exception as e:
        log.error(f"Batch valuation error: {e}")
        raise HTTPException(status_code=500, detail="Batch prediction failed")

@app.get("/api/engine-status")
async def engine_status() -> Dict:
    """엔진 상태 및 통계"""
    if not engine:
        return {"status": "not_initialized"}
    
    return engine.get_engine_stats()

@app.get("/api/health")
async def health_check() -> Dict:
    """헬스체크"""
    return {
        "status": "healthy" if engine else "degraded",
        "engine": "ready" if engine else "not_initialized"
    }

@app.get("/")
async def root() -> Dict:
    """API 루트"""
    return {
        "service": "Loan4U AVM Engine",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Part 3: 상세 테스트 계획

### 3.1 단위 테스트 (51개 케이스)

```python
# tests/test_all_modules.py

# Feature Engineering (12 cases)
def test_normalize_range(): ...
def test_normalize_dtype(): ...
def test_encode_property_type(): ...
def test_encode_district_grade(): ...
def test_transform_complete(): ...
# ... (7개 추가)

# Ensemble Engine (10 cases)
def test_model_loading(): ...
def test_prediction_shape(): ...
def test_cache_functionality(): ...
def test_latency_p95(): ...
def test_cache_hit_rate(): ...
# ... (5개 추가)

# Correction Layer (8 cases)
def test_region_correction(): ...
def test_temporal_adjustment(): ...
def test_apply_corrections(): ...
# ... (5개 추가)

# Validation Engine (15 cases)
def test_anomaly_detection(): ...
def test_confidence_interval(): ...
def test_appraisal_range(): ...
# ... (12개 추가)

# Auction Module (6 cases)
def test_auction_calculation(): ...
def test_market_factors(): ...
# ... (4개 추가)
```

### 3.2 통합 테스트

```python
# tests/test_integration.py

def test_end_to_end_valuation():
    """전체 파이프라인 (5단계)"""
    engine = AVMCoreEngine()
    result = engine.valuate(
        area_sqm=100,
        old_price=500000,
        latitude=35.5,
        longitude=126.8,
        property_type='apartment',
        district_grade='3'
    )
    
    assert 'corrected_price' in result
    assert result['confidence'] > 0.7
    assert result['latency_ms'] < 10

def test_batch_valuation():
    """대량 처리 (100개)"""
    engine = AVMCoreEngine()
    properties = [
        {
            'area_sqm': 100,
            'old_price': 500000,
            'latitude': 35.5,
            'longitude': 126.8,
            'property_type': 'apartment'
        }
        for _ in range(100)
    ]
    
    results = engine.batch_valuate(properties)
    assert len(results) == 100
```

### 3.3 성능 테스트

```python
# tests/test_performance.py

def test_latency_distribution():
    """레이턴시 분포 측정"""
    engine = AVMCoreEngine()
    latencies = []
    
    for i in range(1000):
        features = np.random.rand(5).astype(np.float32)
        _, _, latency = engine.ensemble.predict(features)
        latencies.append(latency)
    
    assert np.mean(latencies) < 2.0    # 평균 < 2ms
    assert np.percentile(latencies, 95) < 5.0  # P95 < 5ms
    assert np.percentile(latencies, 99) < 10.0 # P99 < 10ms

def test_throughput():
    """처리량 (req/sec)"""
    engine = AVMCoreEngine()
    start = time.time()
    count = 0
    
    while time.time() - start < 1.0:  # 1초 동안
        engine.valuate(100, 500000, 35.5, 126.8, 'apartment')
        count += 1
    
    assert count > 100  # 최소 100 req/sec
```

---

## Part 4: 일일 개발 로드맵 (Daily Sprint)

### Week 1: 기초 준비 (Days 1-5)

```
Day 1 (월요일) - 환경 설정
├─ 09:00-10:00: 프로젝트 킥오프 미팅
├─ 10:00-11:00: 저장소 준비, 의존성 설치
├─ 11:00-12:00: 디렉토리 구조 생성
├─ 13:00-14:00: 설정 파일 (avm_config.json) 작성
└─ 14:00-17:00: 데이터 로드 테스트

Day 2-3 (화-수) - 데이터 준비
├─ 데이터 수집 및 검증 (KR, AU, SG)
├─ 결측치 확인 및 처리
├─ 이상치 탐지
└─ 학습/검증 분할 (70/30)

Day 4-5 (목-금) - 모델 준비
├─ 기존 모델 로드 및 검증
├─ R² 점수 확인
├─ 모델 직렬화 (pickle)
└─ 성능 벤치마크
```

### Week 2: Feature Engineering & Ensemble (Days 6-10)

```
Day 6 (월요일) - Feature Engineering 시작
├─ 09:00-10:00: 클래스 구조 설계
├─ 10:00-12:00: normalize() 구현 + 테스트 (2 cases)
├─ 13:00-14:00: encode_property_type() 구현 (2 cases)
└─ 14:00-17:00: encode_district_grade() 구현 (2 cases)

Day 7 (화요일) - Feature Engineering 완성
├─ 09:00-10:00: create_derived_features() 구현
├─ 10:00-11:00: transform() 통합 함수
├─ 11:00-12:00: 단위 테스트 (10 cases)
└─ 13:00-17:00: 코드 리뷰 + 리팩토링

Day 8-9 (수-목) - Ensemble Engine
├─ 클래스 설계 및 상수 정의
├─ _load_models() 구현 (IR + pickle)
├─ predict() 구현 (35 lines)
├─ 캐싱 로직 구현
└─ 테스트 작성 (10 cases)

Day 10 (금요일) - 통합 및 성능 검증
├─ Feature + Ensemble 통합 테스트
├─ 레이턴시 벤치마크
├─ 캐시 히트율 검증
└─ 주간 리뷰
```

### Week 3: 나머지 컴포넌트 (Days 11-15)

```
Day 11-12 (월-화) - Correction Layer
├─ 보정값 테이블 입력 (30개 항목)
├─ apply_corrections() 구현
├─ breakdown() 디버깅 함수
└─ 8개 테스트 케이스

Day 13-14 (수-목) - Validation Engine
├─ 이상탐지 모델 (Isolation Forest)
├─ 신뢰도 구간 (Z-score)
├─ 공시가격 검증
└─ 15개 테스트 케이스

Day 15 (금요일) - Auction Module
├─ 낙찰가 공식 구현
├─ 시장 조정 인자
├─ 6개 테스트 케이스
└─ MS-2 달성: 앙상블 + 신뢰도 > 85%
```

### Week 4: Core Engine & API (Days 16-20)

```
Day 16-17 (월-화) - Core Engine 통합
├─ valuate() 5단계 파이프라인
├─ batch_valuate() 구현
├─ get_engine_stats() 모니터링
└─ 10개 테스트 케이스

Day 18-19 (수-목) - FastAPI Service
├─ Pydantic 모델 정의
├─ 7개 엔드포인트 구현
├─ 에러 처리
└─ Swagger 문서화

Day 20 (금요일) - API 테스트
├─ curl/TestClient 테스트
├─ 동시 요청 처리 (10개)
└─ MS-3 달성: API 완성
```

### Week 5: 테스트 (Days 21-25)

```
Day 21 (월요일) - 단위 테스트
├─ pytest 실행
├─ 각 모듈 > 85% 커버리지
└─ 버그 수정

Day 22-23 (화-수) - 통합 & 성능 테스트
├─ End-to-end 테스트
├─ 레이턴시 분포 (P95 < 5ms)
├─ 캐시 히트율 > 40%
└─ MS-4 달성: 모든 성능 요구사항

Day 24 (목요일) - 회귀 테스트
├─ 이전 버그 재확인
├─ 마스터 체크리스트
└─ 배포 준비

Day 25 (금요일) - 최종 검수
├─ 코드 스타일 (black, pylint)
├─ 타입 검사 (mypy)
└─ 문서 검수
```

### Week 6-7: NPU 최적화 & 배포 (Days 26-35)

```
Day 26-27 (월-화) - NPU 최적화
├─ ONNX 변환 (XGBoost, LightGBM)
├─ INT8 양자화 (OpenVINO IR)
├─ 정확도 손실 검증 (< 2%)
└─ 성능 비교 (NPU vs CPU)

Day 28-29 (수-목) - 배포 준비
├─ Docker 이미지 빌드
├─ 배포 스크립트 작성
├─ 프로덕션 설정 분리
└─ 헬스체크 스크립트

Day 30-31 (금-다음주 월) - 모니터링
├─ Prometheus 메트릭
├─ Grafana 대시보드
├─ 알람 규칙 설정
└─ 로깅 시스템

Day 32-35 (화-금) - 최종 배포
├─ 보안 검사 (OWASP)
├─ 성능 재검증
├─ 팀 교육
├─ MS-6: 본배포 완료
└─ Phase 13.4 종료 🎉
```

---

## Part 5: 진도 추적 지표

### 5.1 일일 메트릭

```python
# tracking/daily_metrics.py

DAILY_METRICS = {
    'lines_of_code': {
        'target': 360,  # 주당 2500 lines ÷ 7 days
        'weekly': [0, 0, 0, 0, 0, 0, 0]
    },
    'test_cases': {
        'target': 9,    # 주당 60 cases ÷ 7 days
        'weekly': [0, 0, 0, 0, 0, 0, 0]
    },
    'test_coverage': {
        'target': 92,   # 최종 92%
        'weekly': [0, 0, 0, 0, 0, 0, 0]
    },
    'commits': {
        'target': 1,
        'weekly': [0, 0, 0, 0, 0, 0, 0]
    }
}
```

### 5.2 주간 리포트 템플릿

```
# 주간 진도 리포트 (매 금요일)

## Week N 완료

### 완료 항목
- [ ] WP X.Y: 컴포넌트명 (라인: 250, 테스트: 12)
- [ ] 단위 테스트: NN 케이스 (커버리지: XX%)
- [ ] 코드 리뷰: ✅ 통과
- [ ] 커밋: N개 (해시: ...)

### 진도
```
[████████░░] 80% 완료 (Day N/35)
```

### 다음주 계획
- WP X.Y 시작
- 기대 완료일: Day NN

### 리스크
- (없음) 또는 (리스크 설명 + 대응 방안)

### 성능 지표
- 코드 라인: NNN/2500 (NN%)
- 테스트 케이스: NN/60 (NN%)
- 평균 레이턴시: N.Nms
- 캐시 히트율: NN%
```

---

## Part 6: 코드 리뷰 체크리스트

**모든 커밋 전에 확인:**

- [ ] 함수 길이 < 50줄
- [ ] Type hints 100% 완전
- [ ] Docstring 작성됨
- [ ] 단위 테스트 추가됨
- [ ] 테스트 커버리지 > 85%
- [ ] `black` 포매팅 적용
- [ ] `pylint` 점수 > 8.0
- [ ] `mypy` 타입 검사 통과
- [ ] 주석은 WHY만 (WHAT 아님)
- [ ] 반복 코드 없음 (3+ lines 제거)

---

**문서 끝**  
**상태**: Ready for Development  
**다음 단계**: 개발 시작 (Day 1)
