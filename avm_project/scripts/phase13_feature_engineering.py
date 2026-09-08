#!/usr/bin/env python3
"""
Phase 13.2.1 - Feature Engineering for KPI Improvement
특성 공학으로 MAPE 0.5~1.5% 개선 (11.33% → 9.8~10.8% 목표).

실행:
    python scripts/phase13_feature_engineering.py --data data/raw/KR_data.csv
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']


def add_regional_features(df: pd.DataFrame) -> pd.DataFrame:
    """지역 특성 11개 카테고리로 확대 (이진 변수 → 다중 분류)."""
    regions = {
        'gangnam_3gu': (37.45, 37.55, 127.0, 127.1),
        'seoul_prime': (37.5, 37.6, 126.9, 127.0),
        'seoul_central': (37.55, 37.65, 126.95, 127.05),
        'seoul_north': (37.6, 37.7, 126.95, 127.05),
        'seoul_west': (37.5, 37.6, 126.85, 126.95),
        'gyeonggi_prime': (37.4, 37.5, 127.0, 127.1),
        'gyeonggi_mid': (37.2, 37.4, 126.95, 127.05),
        'gyeonggi_outer': (37.0, 37.2, 126.9, 127.1),
        'incheon': (37.4, 37.6, 126.5, 126.8),
        'busan_haeundae': (35.15, 35.2, 129.15, 129.2),
        'busan_general': (35.1, 35.2, 129.0, 129.1),
    }

    for region, (lat_min, lat_max, lon_min, lon_max) in regions.items():
        mask = ((df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
                (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max))
        df[f'region_{region}'] = mask.astype(int)

    return df


def add_building_age_polynomial(df: pd.DataFrame) -> pd.DataFrame:
    """준공 연도 → 건물 나이 다항식 (비선형 가격 하락)."""
    current_year = 2026
    col = 'construction_year' if 'construction_year' in df.columns else 'year_built'
    df['building_age'] = current_year - df[col].fillna(current_year)
    df['building_age_sq'] = df['building_age'] ** 2
    df['building_age_log'] = np.log1p(df['building_age'])
    return df


def add_area_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """면적 구간화 (연속 → 이산)."""
    area_ranges = [0, 30, 60, 80, 100, float('inf')]
    labels = ['small', 'medium_small', 'medium', 'large', 'xlarge']
    df['area_bucket'] = pd.cut(df['area_sqm'], bins=area_ranges, labels=labels)
    return pd.get_dummies(df, columns=['area_bucket'], prefix='area')


def add_floor_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """층수 비율 (고층 선호도 반영)."""
    if 'floor' in df.columns and 'max_floor' in df.columns:
        df['floor_ratio'] = df['floor'].fillna(1) / df['max_floor'].fillna(10)
        df['is_high_floor'] = (df['floor_ratio'] > 0.7).astype(int)
    return df


def add_market_signals(df: pd.DataFrame) -> pd.DataFrame:
    """시장 신호: 활성도, 계절 (타겟 new_price 파생 변수는 누수이므로 생성 금지)."""
    quarter_map = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4, 11: 4, 12: 1}
    if 'transaction_month' in df.columns:
        month = df['transaction_month'] % 100  # YYYYMM 형식 대응
        month = month.where((month >= 1) & (month <= 12), df['transaction_month'])
        df['season'] = month.map(quarter_map).fillna(2).astype(int)
        df['is_winter'] = month.isin([12, 1, 2]).astype(int)
    else:
        df['season'] = 2
        df['is_winter'] = 0
    return df


def add_distance_features(df: pd.DataFrame) -> pd.DataFrame:
    """학교, 지하철 접근성 (대리 변수: 좌표 기반 거리)."""
    famous_schools = {
        'kangnam_hs': (37.495, 127.023),
        'ewha_hs': (37.555, 126.975),
        'kisti_hs': (37.415, 127.095),
    }

    for school, (lat, lon) in famous_schools.items():
        dist = ((df['latitude'] - lat) ** 2 + (df['longitude'] - lon) ** 2) ** 0.5
        df[f'dist_to_{school}'] = dist
        df[f'{school}_nearby'] = (dist < 0.05).astype(int)

    return df


TARGET_COL = 'new_price'


def normalize_new_features(df: pd.DataFrame) -> pd.DataFrame:
    """신규 특성 정규화 (타겟은 제외 - 누수 방지)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col == TARGET_COL:
            continue
        if col not in FEATURE_COLS and df[col].notna().sum() > 0:
            min_val, max_val = df[col].min(), df[col].max()
            if max_val > min_val:
                df[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """특성 공학 전체 파이프라인."""
    log.info("특성 공학 시작...")

    original_cols = set(df.columns)
    df = add_regional_features(df)
    df = add_building_age_polynomial(df)
    df = add_area_buckets(df)
    df = add_floor_ratio(df)
    df = add_market_signals(df)
    df = add_distance_features(df)
    df = normalize_new_features(df)

    new_features = set(df.columns) - original_cols
    log.info(f"✅ {len(new_features)}개 신규 특성 추가")
    log.info(f"   예: {list(new_features)[:5]}...")

    return df


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Phase 13.2.1 특성 공학')
    parser.add_argument('--data', default='data/raw/KR_data.csv')
    parser.add_argument('--output', default='data/processed/KR_engineered.csv')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Phase 13.2.1 특성 공학 시작")
    log.info("=" * 60)

    df = pd.read_csv(args.data)
    log.info(f"데이터 로드: {len(df)} rows")

    df = engineer_features(df)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    log.info(f"✅ 저장 완료: {args.output}")
    log.info(f"총 특성: {len(df.columns)} (원본: 13 + 신규 {len(df.columns)-13})")


if __name__ == '__main__':
    main()
