#!/usr/bin/env python3
"""
Phase 13.X.BR - Brazil Feature Engineering
BR 원시 데이터 → 학습용 특성 행렬 (KR 파이프라인 구조 재사용).

실행:
    python scripts/phase13_brazil_feature_engineering.py \
      --data data/raw/BR_raw.csv \
      --output data/processed/BR_engineered.csv
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_brl'
LEAK_PATTERNS = ('price_brl', 'indexed_price')

CITY_CENTERS = {
    'São Paulo': (-23.5505, -46.6333),
    'Rio de Janeiro': (-22.9068, -43.1729),
    'Belo Horizonte': (-19.9167, -43.9345),
    'Brasília': (-15.8267, -47.8822),
    'Salvador': (-12.9714, -38.5014),
    'Curitiba': (-25.4284, -49.2733),
}


def add_city_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """도시 원-핫 인코딩."""
    return pd.get_dummies(df, columns=['city'], prefix='city', dtype=int)


def add_property_type_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """주택 유형 원-핫 인코딩."""
    return pd.get_dummies(df, columns=['property_type'], prefix='type', dtype=int)


def add_building_age(df: pd.DataFrame) -> pd.DataFrame:
    """건물 나이 다항식 (비선형 가격 하락)."""
    current_year = 2026
    df['building_age'] = current_year - df['year_built'].fillna(current_year)
    df['building_age_sq'] = df['building_age'] ** 2
    df['building_age_log'] = np.log1p(df['building_age'])
    return df


def add_area_features(df: pd.DataFrame) -> pd.DataFrame:
    """면적 구간화 및 파생 특성."""
    area_ranges = [0, 60, 100, 150, 220, float('inf')]
    labels = ['small', 'medium_small', 'medium', 'large', 'xlarge']
    df['area_bucket'] = pd.cut(df['area_m2'], bins=area_ranges, labels=labels)
    df = pd.get_dummies(df, columns=['area_bucket'], prefix='area', dtype=int)
    df['area_log'] = np.log1p(df['area_m2'])
    df['area_per_bedroom'] = df['area_m2'] / df['bedrooms'].clip(lower=1)
    return df


def add_distance_to_center(df: pd.DataFrame, city_col_prefix: str = 'city_') -> pd.DataFrame:
    """도시 중심까지 유클리드 거리 (접근성 대리 변수)."""
    df['dist_to_center'] = 0.0
    for city, (lat, lon) in CITY_CENTERS.items():
        col = f'{city_col_prefix}{city}'
        if col not in df.columns:
            continue
        mask = df[col] == 1
        dist = ((df.loc[mask, 'latitude'] - lat) ** 2 +
                (df.loc[mask, 'longitude'] - lon) ** 2) ** 0.5
        df.loc[mask, 'dist_to_center'] = dist
    df['is_central'] = (df['dist_to_center'] < 0.05).astype(int)
    return df


def add_economic_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """IBGE 경제지표 상호작용 특성."""
    df['gdp_density_ratio'] = df['gdp_per_capita_ppp'] / df['population_density'].clip(lower=1)
    df['economic_stress'] = df['unemployment_rate'] * df['gini_index']
    df['fipe_gdp_interaction'] = df['fipe_index'] * df['gdp_per_capita_ppp'] / 10_000
    return df


def normalize_features(df: pd.DataFrame) -> pd.DataFrame:
    """수치형 특성 min-max 정규화 (타겟/누수 컬럼 제외)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if any(p in col for p in LEAK_PATTERNS):
            continue
        min_val, max_val = df[col].min(), df[col].max()
        if max_val > min_val:
            df[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """BR 특성 공학 전체 파이프라인."""
    original_cols = set(df.columns)

    df = add_city_dummies(df)
    df = add_property_type_dummies(df)
    df = add_building_age(df)
    df = add_area_features(df)
    df = add_distance_to_center(df)
    df = add_economic_interactions(df)
    df = normalize_features(df)

    new_features = set(df.columns) - original_cols
    log.info(f"✅ {len(new_features)}개 신규 특성 추가")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.X.BR 특성 공학')
    parser.add_argument('--data', default='data/raw/BR_raw.csv')
    parser.add_argument('--output', default='data/processed/BR_engineered.csv')
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Phase 13.X.BR 특성 공학 시작")
    log.info("=" * 70)

    df = pd.read_csv(args.data)
    log.info(f"데이터 로드: {len(df)} rows × {len(df.columns)} cols")

    df = engineer_features(df)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    log.info(f"✅ 저장 완료: {args.output} ({len(df.columns)} 특성)")


if __name__ == '__main__':
    main()
