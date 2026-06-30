"""WP 2.1: Feature Engineering - 부동산 특성 정규화 및 인코딩."""

import logging
from typing import Dict

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

FEATURE_MIN = np.array([10.0, 50000.0, 33.0, 126.0, 1.0], dtype=np.float32)
FEATURE_MAX = np.array([500.0, 5000000.0, 38.0, 131.0, 5.0], dtype=np.float32)

PROPERTY_TYPE_MAP = {
    'apartment': 1, '아파트': 1,
    'multi_family': 2, '다세대': 2,
    'townhouse': 3, '연립': 3,
    'officetel': 4, '오피스텔': 4,
    'land': 5, '토지': 5,
}

DISTRICT_GRADE_MAP = {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6}


class AVMFeatureEngineer:
    """부동산 특성 정규화 및 인코딩."""

    def __init__(self) -> None:
        self.feature_min = FEATURE_MIN.copy()
        self.feature_max = FEATURE_MAX.copy()

    def normalize(self, features: np.ndarray) -> np.ndarray:
        """Min-Max 정규화 [0, 1]."""
        if features.shape[0] != len(self.feature_min):
            raise ValueError(f"Expected {len(self.feature_min)} features, got {features.shape[0]}")
        normalized = (features - self.feature_min) / (self.feature_max - self.feature_min)
        return np.clip(normalized, 0.0, 1.0).astype(np.float32)

    def encode_property_type(self, property_type: str) -> int:
        """부동산 유형 → 숫자 코드 (1-5)."""
        return PROPERTY_TYPE_MAP.get(property_type.lower().strip(), 1)

    def encode_district_grade(self, district_grade: str) -> int:
        """행정구역 등급 → 숫자 코드 (1-6)."""
        return DISTRICT_GRADE_MAP.get(str(district_grade).strip(), 3)

    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """파생변수 생성 (price_per_sqm, age)."""
        df = df.copy()
        df['price_per_sqm'] = (df['old_price'] / df['area_sqm']).fillna(0)
        if 'construction_year' in df.columns:
            df['age'] = (2026 - df['construction_year']).clip(0, 200)
        return df

    def transform(self, input_dict: Dict) -> np.ndarray:
        """입력 데이터 → 정규화된 특성 벡터."""
        required = {'area_sqm', 'old_price', 'latitude', 'longitude', 'property_type'}
        missing = required - set(input_dict.keys())
        if missing:
            raise ValueError(f"Missing keys: {missing}")

        features = np.array([
            float(input_dict['area_sqm']),
            float(input_dict['old_price']),
            float(input_dict['latitude']),
            float(input_dict['longitude']),
            float(self.encode_property_type(str(input_dict['property_type']))),
        ], dtype=np.float32)

        return self.normalize(features)
