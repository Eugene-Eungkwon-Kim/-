"""Phase 13.1-GBL - 국가 공용 현실 부동산 데이터 생성 엔진.

generate_kr_realistic_data.py에서 검증된 생성 알고리즘(지역/면적/연식
샘플링, 위치·층·연식·시장수준 반영 가격 공식, old_price 타깃 누수 방지)을
country_configs.CountryConfig로 파라미터화해 여러 국가에서 재사용한다.

가격 공식의 형태(위치 프리미엄 0.30, 면적 탄력성 0.15, 층 계수, 연식 감가
0.012)는 국가별 실거래로 보정되지 않은 가정값이다 — docs/LIMITATIONS.md와
동일한 한계를 모든 국가가 공유한다.
"""

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from country_configs import CountryConfig

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

YEAR_BINS: List[Tuple[int, int, float]] = [
    (1975, 1990, 0.15),
    (1990, 2000, 0.25),
    (2000, 2010, 0.25),
    (2010, 2018, 0.20),
    (2018, 2024, 0.15),
]

IDIOSYNCRATIC_SIGMA = 0.08


def _sample_region(config: CountryConfig, rng: np.random.Generator) -> str:
    keys = list(config.region_config.keys())
    weights = np.array(config.region_weights, dtype=float)
    return keys[rng.choice(len(keys), p=weights / weights.sum())]


def _sample_area(config: CountryConfig, rng: np.random.Generator) -> float:
    bins, weights = zip(*[(b[:2], b[2]) for b in config.area_bins])
    weights_arr = np.array(weights, dtype=float)
    idx = rng.choice(len(bins), p=weights_arr / weights_arr.sum())
    lo, hi = bins[idx]
    return round(float(rng.uniform(lo, hi)), 1)


def _sample_year(rng: np.random.Generator) -> int:
    bins, weights = zip(*[(b[:2], b[2]) for b in YEAR_BINS])
    weights_arr = np.array(weights, dtype=float)
    idx = rng.choice(len(bins), p=weights_arr / weights_arr.sum())
    lo, hi = bins[idx]
    return int(rng.integers(lo, hi))


def _compute_price(
    config: CountryConfig, region: str, lat: float, lng: float,
    area: float, construction_year: int, floor: int,
    rng: np.random.Generator,
) -> Tuple[float, float, int]:
    """(new_price, old_price, old_year) — 누수 없는 가격 공식 (국가 공용)."""
    lat_c, lng_c, lat_s, lng_s, base = config.region_config[region]
    dist_sq = ((lat - lat_c) / max(lat_s, 1e-6)) ** 2 + \
              ((lng - lng_c) / max(lng_s, 1e-6)) ** 2
    location_factor = 1.0 + 0.30 * float(np.exp(-dist_sq / 2.0))
    price_per_sqm = (base / 84.0) * (84.0 / area) ** 0.15
    floor_factor = 1.0 + 0.008 * min(floor, 15) - 0.003 * max(0, floor - 20)

    def fundamental(at_year: int) -> float:
        age = max(0, at_year - construction_year)
        age_factor = max(0.60, 1.0 - 0.012 * age)
        market = config.market_level.get(at_year, 1.0)
        return price_per_sqm * area * location_factor * floor_factor * age_factor * market

    new_noise = float(rng.lognormal(0.0, IDIOSYNCRATIC_SIGMA))
    new_price = fundamental(2024) * new_noise

    gap = int(rng.integers(1, 5))
    old_year = max(construction_year, 2024 - gap)
    old_year = min(old_year, 2023)
    old_noise = float(rng.lognormal(0.0, IDIOSYNCRATIC_SIGMA))
    old_price = fundamental(old_year) * old_noise

    new_price = max(config.price_floor, min(config.price_ceiling, new_price))
    old_price = max(config.price_floor * 0.8, min(config.price_ceiling, old_price))
    return round(new_price, -4 if config.price_ceiling >= 1e9 else 0), \
        round(old_price, -4 if config.price_ceiling >= 1e9 else 0), old_year


def generate_dataset(config: CountryConfig, n_rows: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """국가 설정 기반 현실 부동산 데이터셋 생성."""
    rng = np.random.default_rng(seed)
    months = [f'2024{m:02d}' for m in range(1, 13)]
    rows: List[Dict[str, Any]] = []

    for i in range(n_rows):
        region = _sample_region(config, rng)
        lat_c, lng_c, lat_s, lng_s, _ = config.region_config[region]
        lat = float(np.clip(rng.normal(lat_c, lat_s), *config.lat_range))
        lng = float(np.clip(rng.normal(lng_c, lng_s), *config.lng_range))
        area = _sample_area(config, rng)
        year = _sample_year(rng)
        floor = int(rng.integers(1, 46))
        month = months[i % 12]
        new_price, old_price, old_year = _compute_price(
            config, region, lat, lng, area, year, floor, rng,
        )

        rows.append({
            'property_id':       f'{config.country_code}_{month}_{i:06d}',
            'area_sqm':          area,
            'old_price':         old_price,
            'new_price':         new_price,
            'latitude':          round(lat, 6),
            'longitude':         round(lng, 6),
            'property_type':     1,
            'floor':             floor,
            'construction_year': year,
            'transaction_month': month,
            'prior_transaction_year': old_year,
            'region_name':       region,
        })

    return pd.DataFrame(rows)


def validate_and_report(df: pd.DataFrame, config: CountryConfig) -> None:
    """생성 데이터 품질 검증 및 통계 출력 (국가 공용)."""
    assert df.isnull().sum().sum() == 0, "null 값 발견"
    assert df['latitude'].between(*config.lat_range).all(), "위도 범위 오류"
    assert df['longitude'].between(*config.lng_range).all(), "경도 범위 오류"
    assert (df['new_price'] >= config.price_floor).all(), "가격 하한 위반"

    corr_old = df['old_price'].corr(df['new_price'])
    log.info(f"  총 행수: {len(df):,}")
    log.info(f"  통화: {config.currency}")
    log.info(f"  가격 범위: {df['new_price'].min():,.0f} ~ {df['new_price'].max():,.0f} {config.currency}")
    log.info(f"  평균 면적: {df['area_sqm'].mean():.1f}㎡")
    log.info(f"  면적-가격 상관계수: {df['area_sqm'].corr(df['new_price']):.3f}")
    log.info(f"  old_price-new_price 상관계수: {corr_old:.3f}  (누수 방지: 1.0 미만이어야 함)")
    assert corr_old < 0.985, f"old_price 누수 의심: corr={corr_old:.3f}"

    by_region = df.groupby('region_name')['new_price'].mean().sort_values(ascending=False)
    for region, avg in by_region.items():
        log.info(f"    {region}: 평균 {avg:,.0f} {config.currency}")
