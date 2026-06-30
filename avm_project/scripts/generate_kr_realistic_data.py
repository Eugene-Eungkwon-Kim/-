"""WP 1: 한국 부동산 현실 데이터 생성 (2024년 KB국민은행 통계 기반).

실행:
    python scripts/generate_kr_realistic_data.py --rows 10000 --output data/raw/KR_data.csv
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# (lat_center, lng_center, lat_std, lng_std, base_price_84sqm_won)
REGION_CONFIG: Dict[str, Tuple[float, float, float, float, int]] = {
    'gangnam_3gu':    (37.497, 127.024, 0.020, 0.030, 2_500_000_000),
    'seoul_prime':    (37.540, 126.975, 0.025, 0.035, 1_500_000_000),
    'seoul_central':  (37.572, 127.005, 0.030, 0.040, 1_000_000_000),
    'seoul_north':    (37.612, 127.025, 0.040, 0.045,   750_000_000),
    'seoul_west':     (37.548, 126.880, 0.035, 0.040,   800_000_000),
    'gyeonggi_prime': (37.420, 127.130, 0.030, 0.040, 1_100_000_000),
    'gyeonggi_mid':   (37.280, 127.010, 0.060, 0.070,   580_000_000),
    'gyeonggi_outer': (37.100, 127.200, 0.080, 0.090,   350_000_000),
    'incheon':        (37.456, 126.705, 0.045, 0.060,   420_000_000),
    'busan_haeundae': (35.163, 129.163, 0.015, 0.025,   900_000_000),
    'busan_general':  (35.175, 129.050, 0.050, 0.060,   430_000_000),
}

REGION_KEYS   = list(REGION_CONFIG.keys())
REGION_WEIGHTS = [0.08, 0.10, 0.08, 0.09, 0.08, 0.10, 0.15, 0.07, 0.08, 0.05, 0.12]

# (min_sqm, max_sqm, weight)
AREA_BINS: List[Tuple[float, float, float]] = [
    (16.5,  33.0, 0.08),
    (33.0,  50.0, 0.15),
    (50.0,  66.0, 0.22),
    (66.0,  85.0, 0.30),
    (85.0, 115.0, 0.18),
    (115.0,200.0, 0.07),
]

YEAR_BINS: List[Tuple[int, int, float]] = [
    (1975, 1990, 0.15),
    (1990, 2000, 0.25),
    (2000, 2010, 0.25),
    (2010, 2018, 0.20),
    (2018, 2024, 0.15),
]

# 연도별 시장 시세 수준 (2024=1.0 기준, 한국 부동산 사이클 반영)
MARKET_LEVEL: Dict[int, float] = {
    2020: 0.75, 2021: 0.85, 2022: 0.98, 2023: 0.93, 2024: 1.00,
}

# 거래가 idiosyncratic 변동성 (개별 협상/급매/층향 차이) — 신/구 거래 독립
IDIOSYNCRATIC_SIGMA = 0.08

DISTRICT_MAP: Dict[str, str] = {
    'gangnam_3gu': '11680', 'seoul_prime': '11440', 'seoul_central': '11110',
    'seoul_north': '11350', 'seoul_west': '11500', 'gyeonggi_prime': '41130',
    'gyeonggi_mid': '41111', 'gyeonggi_outer': '41590', 'incheon': '28110',
    'busan_haeundae': '26350', 'busan_general': '26110',
}


def _sample_region(rng: np.random.Generator) -> str:
    weights = np.array(REGION_WEIGHTS, dtype=float)
    return REGION_KEYS[rng.choice(len(REGION_KEYS), p=weights / weights.sum())]


def _sample_area(rng: np.random.Generator) -> float:
    bins, weights = zip(*[(b[:2], b[2]) for b in AREA_BINS])
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
    region: str, lat: float, lng: float,
    area: float, construction_year: int,
    floor: int,
    rng: np.random.Generator,
) -> Tuple[float, float, int]:
    """(new_price, old_price, old_year) — 누수 없는 가격 공식.

    new_price: 2024년 거래가. 펀더멘털 × 시장수준(2024) × 독립 노이즈.
    old_price: 동일 물건의 과거(1~4년 전) 거래가. 같은 펀더멘털을 공유하되
               (1) 당시 시장수준, (2) 당시 연식, (3) *독립* idiosyncratic 노이즈로 분리.
               → old_price는 new_price의 사본이 아니라 상관된 별개 관측치.
    """
    lat_c, lng_c, lat_s, lng_s, base = REGION_CONFIG[region]
    dist_sq = ((lat - lat_c) / max(lat_s, 1e-6)) ** 2 + \
              ((lng - lng_c) / max(lng_s, 1e-6)) ** 2
    location_factor = 1.0 + 0.30 * float(np.exp(-dist_sq / 2.0))
    price_per_sqm = (base / 84.0) * (84.0 / area) ** 0.15
    floor_factor  = 1.0 + 0.008 * min(floor, 15) - 0.003 * max(0, floor - 20)

    def fundamental(at_year: int) -> float:
        age = max(0, at_year - construction_year)
        age_factor = max(0.60, 1.0 - 0.012 * age)
        market = MARKET_LEVEL.get(at_year, 1.0)
        return price_per_sqm * area * location_factor * floor_factor * age_factor * market

    new_noise = float(rng.lognormal(0.0, IDIOSYNCRATIC_SIGMA))
    new_price = fundamental(2024) * new_noise

    gap = int(rng.integers(1, 5))                       # 1~4년 전 거래
    old_year = max(construction_year, 2024 - gap)
    old_year = min(old_year, 2023)
    old_noise = float(rng.lognormal(0.0, IDIOSYNCRATIC_SIGMA))   # new와 독립
    old_price = fundamental(old_year) * old_noise

    new_price = max(50_000_000.0, min(6_000_000_000.0, new_price))
    old_price = max(40_000_000.0, min(6_000_000_000.0, old_price))
    return round(new_price, -4), round(old_price, -4), old_year


def generate_dataset(n_rows: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """한국 현실 부동산 데이터셋 생성."""
    rng = np.random.default_rng(seed)
    months = [f'2024{m:02d}' for m in range(1, 13)]
    rows: List[Dict[str, Any]] = []

    for i in range(n_rows):
        region = _sample_region(rng)
        lat_c, lng_c, lat_s, lng_s, _ = REGION_CONFIG[region]
        lat  = float(np.clip(rng.normal(lat_c, lat_s), 33.0, 38.0))
        lng  = float(np.clip(rng.normal(lng_c, lng_s), 126.0, 131.0))
        area = _sample_area(rng)
        year = _sample_year(rng)
        floor = int(rng.integers(1, 46))
        month = months[i % 12]
        new_price, old_price, old_year = _compute_price(
            region, lat, lng, area, year, floor, rng,
        )

        rows.append({
            'property_id':       f'KR_{month}_{i:06d}',
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
            'district_code':     DISTRICT_MAP[region],
            'region_name':       region,
        })

    return pd.DataFrame(rows)


def validate_and_report(df: pd.DataFrame) -> None:
    """생성 데이터 품질 검증 및 통계 출력."""
    assert df.isnull().sum().sum() == 0, "null 값 발견"
    assert df['latitude'].between(33.0, 38.0).all(), "위도 범위 오류"
    assert df['longitude'].between(126.0, 131.0).all(), "경도 범위 오류"
    assert (df['new_price'] >= 50_000_000).all(), "가격 하한 위반"

    corr_old = df['old_price'].corr(df['new_price'])
    log.info(f"  총 행수: {len(df):,}")
    log.info(f"  가격 범위: {df['new_price'].min()/1e8:.1f}억 ~ {df['new_price'].max()/1e8:.1f}억")
    log.info(f"  평균 면적: {df['area_sqm'].mean():.1f}㎡")
    log.info(f"  면적-가격 상관계수: {df['area_sqm'].corr(df['new_price']):.3f}")
    log.info(f"  old_price-new_price 상관계수: {corr_old:.3f}  (누수 방지: 1.0 미만이어야 함)")
    # 직전가가 정답의 사본이면 0.99+가 되어 누수. 0.97 미만이면 분리 성공.
    assert corr_old < 0.985, f"old_price 누수 의심: corr={corr_old:.3f}"

    by_region = df.groupby('region_name')['new_price'].mean().sort_values(ascending=False)
    for region, avg in by_region.items():
        log.info(f"    {region}: 평균 {avg/1e8:.2f}억")


def main() -> None:
    parser = argparse.ArgumentParser(description='KR 현실 부동산 데이터 생성')
    parser.add_argument('--rows',   type=int, default=10_000)
    parser.add_argument('--seed',   type=int, default=42)
    parser.add_argument('--output', default='data/raw/KR_data.csv')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"KR 현실 데이터 생성: {args.rows:,}행")
    log.info("=" * 60)

    df = generate_dataset(n_rows=args.rows, seed=args.seed)
    validate_and_report(df)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding='utf-8-sig')
    log.info(f"\n✅ 저장 완료: {out} ({len(df):,}행 × {len(df.columns)}컬럼)")


if __name__ == '__main__':
    main()
