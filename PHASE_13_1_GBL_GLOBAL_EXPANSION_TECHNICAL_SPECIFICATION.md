# Phase 13.1-GBL 기술 명세서
## 8개국 글로벌 확대 - 코드 아키텍처

**작성일**: 2026-07-01
**버전**: 1.0
**기반**: KR 파이프라인 재사용 (`generate_kr_realistic_data.py`, `train_kr_model.py`, `phase13_model_converter.py`)

---

## 1. 국가별 데이터 생성 명세

### 1.1 공통 인터페이스 (국가별 스크립트가 구현해야 할 계약)

```python
# scripts/generate_{country}_realistic_data.py 공통 템플릿
# (generate_kr_realistic_data.py의 REGION_CONFIG 패턴 재사용)

from typing import Dict, Tuple

# (lat_center, lng_center, lat_std, lng_std, base_price_local_currency)
REGION_CONFIG: Dict[str, Tuple[float, float, float, float, int]] = {
    # 국가별 주요 지역 클러스터 (KR의 gangnam_3gu 패턴과 동일 구조)
    # 예: SG -> {'orchard': (1.304, 103.831, 0.01, 0.01, 2_500_000), ...}
}

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
CURRENCY_CODE = 'XXX'  # ISO 4217 (GBP, SGD, JPY, EUR, AUD, CAD, THB, HKD)

def generate_realistic_data(rows: int) -> pd.DataFrame:
    """KR의 generate_kr_realistic_data.py와 동일한 비선형 가격 공식 재사용:
    면적/층수/건축연도/위치 프리미엄 반영, 지역 클러스터 기반 가우시안 샘플링
    """
    pass
```

### 1.2 국가별 REGION_CONFIG 예시 (SG 우선 구현)

```python
# scripts/generate_sg_realistic_data.py

REGION_CONFIG = {
    'orchard_core':     (1.3048, 103.8318, 0.005, 0.005, 3_200_000),  # SGD
    'marina_bay':       (1.2830, 103.8607, 0.006, 0.006, 2_800_000),
    'sentosa':          (1.2494, 103.8303, 0.008, 0.008, 4_500_000),
    'bukit_timah':      (1.3294, 103.8021, 0.010, 0.010, 2_200_000),
    'east_coast':       (1.3010, 103.9146, 0.015, 0.015, 1_400_000),
    'jurong':           (1.3329, 103.7436, 0.020, 0.020,   850_000),
    'woodlands':        (1.4382, 103.7890, 0.020, 0.020,   650_000),
    'tampines':         (1.3496, 103.9568, 0.015, 0.015,   750_000),
}

CURRENCY_CODE = 'SGD'
TOLERANCE = 0.08  # CLAUDE.md TOLERANCE_MAP 기준
```

---

## 2. 통화/단위 정규화 레이어 (신규 모듈)

### 2.1 currency_converter.py

```python
# scripts/global_currency_converter.py

from dataclasses import dataclass
from typing import Dict
import json
from pathlib import Path

@dataclass
class ExchangeRateSnapshot:
    """고정 환율 스냅샷 (정기 업데이트, 실시간 API 아님)"""
    base_currency: str  # 'USD'
    rates: Dict[str, float]  # {'GBP': 0.79, 'SGD': 1.34, ...}
    snapshot_date: str

class CurrencyConverter:
    """국가별 통화를 USD 기준으로 정규화 (모델 학습용, 표시는 원 통화 유지)"""

    def __init__(self, snapshot_path: str = 'config/exchange_rates.json'):
        self.snapshot = self._load_snapshot(snapshot_path)

    def to_usd(self, amount: float, currency: str) -> float:
        """local currency -> USD (모델 내부 정규화용)"""
        rate = self.snapshot.rates.get(currency)
        if rate is None:
            raise ValueError(f"지원하지 않는 통화: {currency}")
        return amount * rate

    def from_usd(self, amount_usd: float, currency: str) -> float:
        """USD -> local currency (API 응답 표시용)"""
        rate = self.snapshot.rates.get(currency)
        return amount_usd / rate
```

### 2.2 config/exchange_rates.json (스냅샷 예시)

```json
{
  "base_currency": "USD",
  "snapshot_date": "2026-07-01",
  "update_frequency": "monthly",
  "rates": {
    "GBP": 0.79, "SGD": 1.34, "JPY": 156.2,
    "EUR": 0.92, "AUD": 1.51, "CAD": 1.36,
    "THB": 36.4, "HKD": 7.81, "KRW": 1385.0
  }
}
```

### 2.3 unit_converter.py

```python
# scripts/global_unit_converter.py

SQFT_TO_SQM = 0.092903

def sqft_to_sqm(sqft: float) -> float:
    """UK/US 계열 국가(부분 데이터셋)의 sqft를 sqm으로 통일"""
    return sqft * SQFT_TO_SQM

def normalize_area(value: float, source_unit: str) -> float:
    """모든 국가 데이터를 sqm 기준으로 통일 (KR 학습 파이프라인과 호환)"""
    if source_unit == 'sqft':
        return sqft_to_sqm(value)
    return value  # already sqm
```

---

## 3. Country-Aware Ensemble Engine 확장

### 3.1 avm_ensemble_engine.py 수정 명세

```python
# 기존 (KR 전용):
class EnsembleEngine:
    def __init__(self, model_dir: str) -> None:
        self.model_dir = Path(model_dir)

# 변경 (국가 파라미터화):
class EnsembleEngine:
    def __init__(self, model_dir: str, country_code: str = 'KR') -> None:
        self.model_dir = Path(model_dir) / country_code
        self.country_code = country_code
        self.currency = COUNTRY_CURRENCY_MAP[country_code]
        self.tolerance = TOLERANCE_MAP[country_code]  # CLAUDE.md 기준
```

**디렉토리 구조 변경**:
```
output/models_ir/
├── KR/
│   ├── xgboost_KR.onnx
│   └── lightgbm_KR.onnx
├── SG/
│   ├── xgboost_SG.onnx
│   └── lightgbm_SG.onnx
├── HK/
│   └── ...
└── ... (8개국)
```

### 3.2 Multi-Country API 엔드포인트

```python
# phase13_api_service.py 확장

from functools import lru_cache

SUPPORTED_COUNTRIES = ['KR', 'SG', 'HK', 'UK', 'AU', 'CA', 'DE', 'JP', 'TH']

@lru_cache(maxsize=len(SUPPORTED_COUNTRIES))
def get_engine(country_code: str) -> EnsembleEngine:
    """국가별 엔진 lazy loading + 캐싱"""
    if country_code not in SUPPORTED_COUNTRIES:
        raise HTTPException(400, f"미지원 국가: {country_code}")
    return EnsembleEngine(model_dir='output/models_ir', country_code=country_code)

@app.post("/api/valuation/{country_code}")
async def valuate_property(country_code: str, request: PropertyValuationRequest):
    engine = get_engine(country_code)
    result = engine.valuate(request.dict())
    return result

@app.get("/api/countries")
async def list_supported_countries():
    return {"countries": SUPPORTED_COUNTRIES}
```

---

## 4. 테스트 명세

### 4.1 국가별 테스트 템플릿 (tests/test_kr_valuation.py 패턴 재사용)

```python
# tests/test_sg_valuation.py (SG 우선 구현 예시)

import pytest
from scripts.avm_core_engine import AVMCoreEngine

REGION_TEST_CASES = [
    # (name, area_sqm, old_price_sgd, lat, lng, prop_type, min_b, max_b)  # 단위: 백만 SGD
    ('orchard_90sqm', 90, 3_200_000, 1.3048, 103.8318, 'condo', 2.9, 4.3),
    ('jurong_70sqm',  70,   850_000, 1.3329, 103.7436, 'condo', 0.7, 1.1),
]

class TestSGValuation:
    @pytest.mark.parametrize("name,area,old_price,lat,lng,ptype,min_b,max_b", REGION_TEST_CASES)
    def test_price_in_market_range(self, name, area, old_price, lat, lng, ptype, min_b, max_b):
        engine = AVMCoreEngine(country_code='SG')
        result = engine.valuate(area_sqm=area, old_price=old_price, latitude=lat,
                                  longitude=lng, property_type=ptype)
        price_millions = result['corrected_price'] / 1_000_000
        assert min_b <= price_millions <= max_b, f"{name}: {price_millions}M SGD 범위 이탈"
```

### 4.2 통합 테스트 (국가 간 일관성)

```python
def test_all_countries_api_responds():
    """8개국 모두 /api/valuation/{country} 정상 응답 확인"""
    for country in SUPPORTED_COUNTRIES:
        response = client.post(f"/api/valuation/{country}", json=SAMPLE_REQUEST[country])
        assert response.status_code == 200

def test_currency_conversion_consistency():
    """USD 정규화 후 재환산 시 원본과 일치하는지 검증"""
    converter = CurrencyConverter()
    original = 1_000_000  # SGD
    usd = converter.to_usd(original, 'SGD')
    back = converter.from_usd(usd, 'SGD')
    assert abs(back - original) < 1.0
```

---

## 5. 의존성

```
# 기존 KR 파이프라인 의존성 재사용 (requirements.txt)
pandas, numpy, scikit-learn, xgboost, lightgbm
skl2onnx, onnx, onnxmltools, onnxruntime, openvino

# 신규 추가 없음 (통화 변환은 순수 Python dict 기반, 외부 API 불필요)
```

---

**기술 명세서 완성**
**다음 문서**: Phase 13.1-GBL WBS
