# 코딩 표준 (Coding Standards)

**적용 범위**: Phase 13.1-GBL 이후 모든 신규 코드  
**기준 구현**: `avm_project/scripts/country_configs.py`, `avm_project/scripts/realistic_data_generator.py`

## 1. 함수 크기 (Function Size)

### 규칙
```python
# Good: 50줄 이하
def validate_config(config: CountryConfig) -> bool:
    """단일 책임: 설정 검증만 수행."""
    assert config.region_weights.sum() == pytest.approx(1.0)
    assert len(config.region_config) == len(config.region_weights)
    return True

# Bad: 65줄 (분해 필요)
def validate_and_process_and_save(data, config):  # 3가지 책임!
    # ...많은 코드...
```

### 예외
- 복잡한 비즈니스 로직만 **최대 100줄** 허용
- 정당화 필요 (커밋 메시지에 WHY 작성)

---

## 2. 타입 힌트 (Type Hints)

### 규칙: 100% 커버리지
```python
# Good: 모든 파라미터와 반환타입 명시
def generate_dataset(
    config: CountryConfig,
    n_rows: int = 10_000,
    seed: int = 42
) -> pd.DataFrame:
    """국가 설정 기반 현실 부동산 데이터셋 생성."""
    return pd.DataFrame(...)

# Bad: 타입 힌트 부재
def generate_dataset(config, n_rows=10000, seed=42):
    return pd.DataFrame(...)
```

### 복잡한 타입
```python
from typing import Dict, List, Optional, Tuple

# Collection 타입 명시
region_weights: Tuple[float, ...] = (0.1, 0.2, 0.3)
market_level: Dict[int, float] = {2020: 0.75, 2024: 1.0}
feature_range: Tuple[float, float, float, float, float] = (10.0, 500.0, 33.0, 126.0, 1.0)

# Union 타입
result: Optional[pd.DataFrame] = fetch_data()
config: CountryConfig | None = get_country_config("KR")
```

---

## 3. 명명 규칙 (Naming)

### 함수/변수: snake_case
```python
def generate_realistic_data() -> pd.DataFrame:  # ✓
def generateRealisticData() -> pd.DataFrame:   # ✗

price_floor: float = 50_000_000.0  # ✓
priceFloor: float = 50_000_000.0   # ✗
```

### 상수: UPPER_CASE
```python
DEFAULT_AREA_BINS: Tuple = (...)
TOLERANCE_MAP: Dict = {'UK': 0.05}
PRICE_CEILING: float = 10_000_000.0
```

### 클래스: PascalCase
```python
class CountryConfig:  # ✓
    pass

class country_config:  # ✗
    pass
```

---

## 4. 주석 정책 (Comments)

### 규칙: WHY만, WHAT은 제외

```python
# Good: WHY (판단의 근거)
def generate_price(...):
    # 지역 클러스터가 촘촘한 국가(HK)는 기본 sigma(0.08)로는
    # old/new 상관계수가 누수 임계값(0.985)에 근접하므로 0.11로 상향
    idiosyncratic_sigma: float = 0.11

# Bad: WHAT (코드가 이미 표현)
def generate_price(...):
    # sigma를 0.11로 설정
    idiosyncratic_sigma: float = 0.11
```

### 모듈 docstring은 필수
```python
"""Phase 13.1-GBL - 국가별 부동산 시장 설정.

각 국가의 지역 클러스터, 통화, 정규화 범위를 한 곳에 모아
realistic_data_generator.py 호출 시 국가별 분기가 이 모듈만 참조하도록 한다.
"""
```

### 함수 docstring
```python
def get_country_config(country_code: str) -> CountryConfig:
    """국가 코드로 설정 조회.
    
    Args:
        country_code: 국가 코드 (KR, SG, HK 등)
    
    Returns:
        CountryConfig: 해당 국가의 설정 객체
    
    Raises:
        ValueError: 미지원 국가 코드
    """
```

---

## 5. 임포트 정렬 (Import Order)

```python
# 1. 표준 라이브러리
import logging
from pathlib import Path
from typing import Dict, List, Optional

# 2. 서드파티
import numpy as np
import pandas as pd
import pytest

# 3. 로컬 모듈
from country_configs import CountryConfig, get_country_config
from realistic_data_generator import generate_dataset
```

---

## 6. 반복 코드 제거 (DRY)

### 규칙: 3줄 이상 반복 → 함수/루프로 추출

```python
# Bad: 반복 (6줄 × 5회 = 30줄)
sg_dataset = generate_dataset(SG_CONFIG, n_rows=1000)
sg_corr = sg_dataset['old_price'].corr(sg_dataset['new_price'])
assert sg_corr < 0.985

hk_dataset = generate_dataset(HK_CONFIG, n_rows=1000)
hk_corr = hk_dataset['old_price'].corr(hk_dataset['new_price'])
assert hk_corr < 0.985
# ... 더 많은 국가들

# Good: 헬퍼 함수 + 루프
def test_no_leakage(config: CountryConfig, n_rows: int = 1000) -> None:
    df = generate_dataset(config, n_rows=n_rows, seed=42)
    corr = df['old_price'].corr(df['new_price'])
    assert corr < 0.985

for config in [SG_CONFIG, HK_CONFIG, UK_CONFIG, AU_CONFIG]:
    test_no_leakage(config)
```

---

## 7. 테스트 작성 기준

### 최소 요건
- 모든 public 함수에 최소 1개 단위 테스트
- edge cases 커버: None, 빈 데이터, 경계값
- 성공 경로 + 실패 경로

### 예제 (country_configs.py)
```python
class TestCountryConfigs:
    def test_all_nine_countries_registered(self):
        assert set(COUNTRY_CONFIGS) == {'KR', 'SG', 'HK', 'UK', 'AU', 'TH'}
    
    def test_tolerances_match_claude_md(self):
        expected = {'UK': 0.05, 'SG': 0.08, 'TH': 0.15}
        for code, tolerance in expected.items():
            assert COUNTRY_CONFIGS[code].tolerance == tolerance
```

---

## 8. 제출 체크리스트

커밋 전 확인사항:

```markdown
- [ ] 모든 함수 ≤50줄 (정당화 없으면 >100줄 금지)
- [ ] 100% type hints 추가
- [ ] 주석은 WHY만 (WHAT 제거)
- [ ] 반복 코드 없음 (DRY 준수)
- [ ] 모듈/함수 docstring 있음
- [ ] 테스트 작성됨 (public 함수 100%)
- [ ] 임포트 정렬됨 (표준→서드파티→로컬)
- [ ] 변수명: snake_case, 상수: UPPER_CASE
- [ ] Commit 메시지 명확함
```

---

## 9. 참조 구현

### 모범 사례
- `avm_project/scripts/country_configs.py` (229줄, 5 함수)
- `avm_project/scripts/realistic_data_generator.py` (144줄, 7 함수)
- `avm_project/tests/test_phase13_1_gbl_expansion.py` (254줄, 45 테스트)

### 기준 메트릭
| 메트릭 | 목표 | 예제 |
|--------|------|------|
| 평균 함수 크기 | ~30줄 | country_configs: 46줄 |
| Type hints | 100% | realistic_data_generator: 100% |
| 테스트 커버리지 | >90% | test_expansion: 45 테스트 |
| 순환 복잡도 | <5 | 대부분 선형 로직 |

---

**마지막 업데이트**: 2026-07-09  
**적용 시작**: Phase 13.1-GBL 완료 후 (2026-07-09)
