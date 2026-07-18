#!/usr/bin/env python3
"""
Phase 13.X - Global Country Expansion Pipeline
국가 설정만 추가하면 수집→특성공학→학습→평가까지 실행되는 범용 파이프라인.
BR 파이프라인 구조를 일반화 (신규 국가 델타 = COUNTRY_CONFIGS 항목 1개).

실행:
    python scripts/phase13_global_pipeline.py --country SG
    python scripts/phase13_global_pipeline.py --country HK --records 20000

산출물:
    data/raw/{CC}_raw.csv
    data/processed/{CC}_engineered.csv
    output/models/{cc}_production_v1.0.pkl (+ metadata JSON)
"""

import argparse
import json
import logging
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from phase13_brazil_model_trainer import build_stacking_model, evaluate

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_local'
LEAK_PATTERNS = ('price_local', 'indexed_price')
PROPERTY_TYPES = {'Studio': 0.85, '1BR': 0.95, '2BR': 1.0, '3BR': 1.12, '4BR+': 1.30}
BEDROOM_MAP = {'Studio': 0, '1BR': 1, '2BR': 2, '3BR': 3, '4BR+': 4}
MAPE_TARGET = 0.10

# city: (lat, lon, weight, regional_index, density, gdp_ppp, unemployment, gini)
COUNTRY_CONFIGS: Dict[str, Dict] = {
    'SG': {
        'name': 'Singapore', 'currency': 'SGD', 'price_per_m2': 15_000, 'tolerance': 0.08,
        'cities': {
            'Core Central': (1.290, 103.850, 0.40, 1.50, 11_000, 72_000, 0.021, 0.44),
            'East Region': (1.324, 103.940, 0.30, 1.10, 8_500, 65_000, 0.023, 0.42),
            'North Region': (1.429, 103.790, 0.15, 0.85, 7_000, 58_000, 0.026, 0.41),
            'West Region': (1.350, 103.700, 0.15, 0.90, 7_800, 60_000, 0.025, 0.42),
        },
    },
    'HK': {
        'name': 'Hong Kong', 'currency': 'HKD', 'price_per_m2': 130_000, 'tolerance': 0.08,
        'cities': {
            'HK Island': (22.280, 114.160, 0.35, 1.60, 16_000, 62_000, 0.031, 0.54),
            'Kowloon': (22.320, 114.170, 0.35, 1.20, 43_000, 48_000, 0.038, 0.53),
            'New Territories': (22.440, 114.030, 0.30, 0.90, 6_800, 42_000, 0.041, 0.50),
        },
    },
    'UK': {
        'name': 'United Kingdom', 'currency': 'GBP', 'price_per_m2': 4_500, 'tolerance': 0.05,
        'cities': {
            'London': (51.507, -0.128, 0.40, 1.80, 5_700, 56_000, 0.046, 0.36),
            'Manchester': (53.480, -2.242, 0.20, 0.90, 4_800, 38_000, 0.052, 0.34),
            'Birmingham': (52.489, -1.898, 0.20, 0.85, 4_100, 35_000, 0.058, 0.35),
            'Edinburgh': (55.953, -3.188, 0.20, 1.00, 1_900, 45_000, 0.038, 0.32),
        },
    },
    'DE': {
        'name': 'Germany', 'currency': 'EUR', 'price_per_m2': 5_000, 'tolerance': 0.08,
        'cities': {
            'Berlin': (52.520, 13.405, 0.30, 1.10, 4_100, 46_000, 0.089, 0.29),
            'Munich': (48.137, 11.575, 0.30, 1.60, 4_800, 62_000, 0.038, 0.29),
            'Hamburg': (53.551, 9.994, 0.20, 1.20, 2_500, 55_000, 0.068, 0.30),
            'Frankfurt': (50.110, 8.682, 0.20, 1.30, 3_100, 60_000, 0.055, 0.31),
        },
    },
    'AU': {
        'name': 'Australia', 'currency': 'AUD', 'price_per_m2': 9_000, 'tolerance': 0.10,
        'cities': {
            'Sydney': (-33.869, 151.209, 0.40, 1.50, 2_100, 58_000, 0.041, 0.34),
            'Melbourne': (-37.814, 144.963, 0.35, 1.20, 1_900, 52_000, 0.044, 0.33),
            'Brisbane': (-27.470, 153.026, 0.25, 0.95, 1_100, 48_000, 0.046, 0.33),
        },
    },
    'CA': {
        'name': 'Canada', 'currency': 'CAD', 'price_per_m2': 8_500, 'tolerance': 0.10,
        'cities': {
            'Toronto': (43.651, -79.383, 0.40, 1.40, 4_400, 52_000, 0.061, 0.32),
            'Vancouver': (49.283, -123.121, 0.30, 1.60, 5_500, 50_000, 0.055, 0.34),
            'Montreal': (45.502, -73.567, 0.30, 0.90, 3_900, 44_000, 0.065, 0.31),
        },
    },
    'TH': {
        'name': 'Thailand', 'currency': 'THB', 'price_per_m2': 110_000, 'tolerance': 0.15,
        'cities': {
            'Bangkok': (13.756, 100.502, 0.50, 1.30, 5_300, 23_000, 0.011, 0.43),
            'Chiang Mai': (18.788, 98.985, 0.25, 0.70, 3_100, 15_000, 0.014, 0.40),
            'Phuket': (7.881, 98.392, 0.25, 1.00, 750, 19_000, 0.012, 0.41),
        },
    },
}


def collect_country_data(country: str, config: Dict, n_records: int) -> pd.DataFrame:
    """특성 기반 가격 시뮬레이션으로 국가 데이터 수집."""
    noise_sigma = min(config['tolerance'], 0.10)
    rows: List[Dict] = []

    for city, (lat, lon, weight, idx, density, gdp, unemp, gini) in config['cities'].items():
        base_per_m2 = config['price_per_m2'] * idx
        for i in range(int(n_records * weight)):
            prop_type = np.random.choice(list(PROPERTY_TYPES.keys()))
            area = np.random.uniform(40, 250)
            year_built = np.random.randint(1985, 2023)
            lat_off, lon_off = np.random.normal(0, 0.08, 2)

            age_factor = max(0.6, 1.0 - (2026 - year_built) * 0.008)
            dist_factor = max(0.7, 1.0 - (lat_off ** 2 + lon_off ** 2) ** 0.5 * 1.5)
            price = (base_per_m2 * area * PROPERTY_TYPES[prop_type] * age_factor
                     * dist_factor * np.random.lognormal(0, noise_sigma))

            rows.append({
                'property_id': f'{country}_{city[:3].upper()}_{i:06d}',
                'city': city, 'property_type': prop_type,
                'bedrooms': BEDROOM_MAP[prop_type], 'area_m2': area,
                'year_built': year_built, 'price_local': price,
                'latitude': lat + lat_off, 'longitude': lon + lon_off,
                'regional_index': idx, 'population_density': density,
                'gdp_per_capita_ppp': gdp, 'unemployment_rate': unemp, 'gini_index': gini,
            })

    return pd.DataFrame(rows)


def engineer_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """도시/유형 인코딩, 연식, 면적, 접근성, 경제 상호작용 특성 생성."""
    city_centers = {c: (v[0], v[1]) for c, v in config['cities'].items()}

    df = pd.get_dummies(df, columns=['city', 'property_type'], prefix=['city', 'type'], dtype=int)

    df['building_age'] = 2026 - df['year_built']
    df['building_age_sq'] = df['building_age'] ** 2
    df['building_age_log'] = np.log1p(df['building_age'])

    df['area_log'] = np.log1p(df['area_m2'])
    df['area_per_bedroom'] = df['area_m2'] / df['bedrooms'].clip(lower=1)

    df['dist_to_center'] = 0.0
    for city, (lat, lon) in city_centers.items():
        col = f'city_{city}'
        if col in df.columns:
            mask = df[col] == 1
            df.loc[mask, 'dist_to_center'] = ((df.loc[mask, 'latitude'] - lat) ** 2 +
                                              (df.loc[mask, 'longitude'] - lon) ** 2) ** 0.5
    df['is_central'] = (df['dist_to_center'] < 0.05).astype(int)

    df['gdp_density_ratio'] = df['gdp_per_capita_ppp'] / df['population_density'].clip(lower=1)
    df['economic_stress'] = df['unemployment_rate'] * df['gini_index']
    return df


def train_and_save(df: pd.DataFrame, country: str, output_dir: Path) -> Dict:
    """Stacking Ensemble 학습, 평가, pkl+메타데이터 저장."""
    from sklearn.model_selection import train_test_split

    y = df[TARGET_COL].to_numpy(dtype=np.float64)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
    X = df[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = build_stacking_model()
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0

    metrics = evaluate(model, X_train, y_train, X_test, y_test)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f'{country.lower()}_production_v1.0.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    metadata = {
        'model_id': f'{country.lower()}_production_v1.0',
        'country': country,
        'architecture': 'StackingRegressor (5 base + Ridge meta)',
        'performance': metrics,
        'mape_target': MAPE_TARGET,
        'target_met': metrics['test_mape'] < MAPE_TARGET,
        'n_features': len(feature_cols),
        'n_samples': int(X.shape[0]),
        'feature_columns': feature_cols,
        'training_sec': round(elapsed, 1),
        'model_size_mb': round(model_path.stat().st_size / 1024 / 1024, 1),
        'created_date': datetime.now().strftime('%Y-%m-%d'),
    }
    with open(output_dir / f'{country.lower()}_production_v1.0_metadata.json', 'w',
              encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return metadata


def run_pipeline(country: str, n_records: int) -> Dict:
    """국가 전체 파이프라인: 수집 → 특성공학 → 학습 → 저장."""
    config = COUNTRY_CONFIGS[country]
    log.info("=" * 70)
    log.info(f"Phase 13.X.{country} - {config['name']} 파이프라인")
    log.info("=" * 70)

    df = collect_country_data(country, config, n_records)
    raw_path = Path(f'data/raw/{country}_raw.csv')
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_path, index=False)
    log.info(f"✅ 수집: {len(df):,} rows → {raw_path}")

    df = engineer_features(df, config)
    proc_path = Path(f'data/processed/{country}_engineered.csv')
    proc_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(proc_path, index=False)
    log.info(f"✅ 특성공학: {len(df.columns)} 특성 → {proc_path}")

    metadata = train_and_save(df, country, Path('output/models'))
    perf = metadata['performance']
    log.info(f"\n{country} 성능 (목표 MAPE < {MAPE_TARGET:.0%}):")
    log.info(f"  Test MAPE: {perf['test_mape']:.2%}  "
             f"{'✅ PASS' if metadata['target_met'] else '❌ FAIL'}")
    log.info(f"  Test R²:   {perf['test_r2']:.4f}")
    log.info(f"  학습 시간: {metadata['training_sec']}초")

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.X 글로벌 확장 파이프라인')
    parser.add_argument('--country', required=True, choices=sorted(COUNTRY_CONFIGS.keys()))
    parser.add_argument('--records', type=int, default=20000)
    args = parser.parse_args()

    metadata = run_pipeline(args.country, args.records)
    exit(0 if metadata['target_met'] else 1)


if __name__ == '__main__':
    main()
