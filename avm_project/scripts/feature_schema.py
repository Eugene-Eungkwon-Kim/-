"""
공유 특성 스키마 (학습/서빙 단일 소스)

train/serve 스큐 방지를 위해 학습 파이프라인과 API 서버가 동일한
특성 목록·순서를 사용하도록 강제한다.

설계 원칙:
  - 타깃(market_price)은 특성에서 제외
  - 식별자(property_id) 제외
  - 누수(leakage) 컬럼 제외:
      * final_sale_price : 추론 시점에 알 수 없음 + 타깃과 강한 상관
      * numeric_mean/std/max/min : 타깃 포함 행 단위 집계 → 누수
  - 문자열 컬럼(property_type/region/district/condition) 제외
  - 서빙(PropertyData)에서 모두 제공 가능한 수치 변수만 채택
"""

from __future__ import annotations

import json
from pathlib import Path

# 타깃 변수
TARGET = "market_price"

# 학습/서빙 공통 특성 (순서 고정 — 모델 입력 순서와 일치해야 함)
SERVING_FEATURES = [
    "area_sqm",
    "year_built",
    "floor",
    "total_floor",
    "rooms",
    "bathrooms",
    "parking",
    "original_price",
    "appraised_price",
    "outstanding_debt",
    "transaction_count_1y",
    "ltv",
    "loan_term_months",
    "days_on_market",
    "appraisal_rounds",
    "age_years",
    "price_per_sqm",
    "debt_to_price_ratio",
    "price_variance",
]

# 누수/식별자/문자열 — 학습에서 명시적으로 제외
EXCLUDED_COLUMNS = [
    "property_id",
    "final_sale_price",
    "numeric_mean",
    "numeric_std",
    "numeric_max",
    "numeric_min",
    "property_type",
    "region",
    "district",
    "condition",
    TARGET,
]

SCHEMA_FILE = Path(__file__).parent.parent / "models" / "feature_schema.json"


def save_schema(features: list[str], target: str = TARGET, path: Path = SCHEMA_FILE) -> Path:
    """학습 시 실제 사용한 특성 스키마를 디스크에 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"features": features, "target": target}, f, indent=2, ensure_ascii=False)
    return path


def load_schema(path: Path = SCHEMA_FILE) -> dict:
    """저장된 특성 스키마 로드. 없으면 기본 SERVING_FEATURES 사용."""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"features": list(SERVING_FEATURES), "target": TARGET}
