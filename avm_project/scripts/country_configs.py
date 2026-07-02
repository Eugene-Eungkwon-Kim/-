"""Phase 13.1-GBL - 국가별 부동산 시장 설정.

각 국가의 지역 클러스터, 통화, 정규화 범위를 한 곳에 모아
generate_kr_realistic_data.py/realistic_data_generator.py와
train_kr_model.py의 국가별 분기가 이 모듈만 참조하도록 한다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 기본 면적 분포 (min_sqm, max_sqm, weight) - 한국 아파트 평형 기준
DEFAULT_AREA_BINS: Tuple[Tuple[float, float, float], ...] = (
    (16.5,  33.0, 0.08),
    (33.0,  50.0, 0.15),
    (50.0,  66.0, 0.22),
    (66.0,  85.0, 0.30),
    (85.0, 115.0, 0.18),
    (115.0,200.0, 0.07),
)


@dataclass(frozen=True)
class CountryConfig:
    """단일 국가의 합성 데이터 생성 + 학습 정규화 설정."""
    country_code: str
    currency: str
    # region_name -> (lat_center, lng_center, lat_std, lng_std, base_price_84sqm)
    region_config: Dict[str, Tuple[float, float, float, float, float]]
    region_weights: Tuple[float, ...]
    lat_range: Tuple[float, float]
    lng_range: Tuple[float, float]
    market_level: Dict[int, float]  # 연도 -> 2024=1.0 기준 시장수준
    price_floor: float
    price_ceiling: float
    # avm_feature_engineering과 동일 순서: [area_sqm, old_price, latitude, longitude, property_type]
    feature_min: Tuple[float, float, float, float, float]
    feature_max: Tuple[float, float, float, float, float]
    tolerance: float = 0.10  # CLAUDE.md TOLERANCE_MAP 기준
    area_bins: Tuple[Tuple[float, float, float], ...] = DEFAULT_AREA_BINS
    # 거래가 idiosyncratic 변동성(개별 협상/급매/층향 차이, new/old 독립).
    # 지역 클러스터가 촘촘한 국가(예: HK)는 펀더멘털 분산이 작아 old_price-
    # new_price 상관계수가 누수 임계값(0.985)에 근접할 수 있어 값을 높인다.
    idiosyncratic_sigma: float = 0.08


KR_CONFIG = CountryConfig(
    country_code='KR',
    currency='KRW',
    region_config={
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
    },
    region_weights=(0.08, 0.10, 0.08, 0.09, 0.08, 0.10, 0.15, 0.07, 0.08, 0.05, 0.12),
    lat_range=(33.0, 38.0),
    lng_range=(126.0, 131.0),
    market_level={2020: 0.75, 2021: 0.85, 2022: 0.98, 2023: 0.93, 2024: 1.00},
    price_floor=50_000_000.0,
    price_ceiling=6_000_000_000.0,
    feature_min=(10.0, 50_000_000.0, 33.0, 126.0, 1.0),
    feature_max=(500.0, 6_000_000_000.0, 38.0, 131.0, 5.0),
    tolerance=0.10,
)

# 싱가포르: PHASE_13_1_GBL 계획서 상 1순위 확장 국가 (URA 데이터 품질 높음, 소규모 시장)
SG_CONFIG = CountryConfig(
    country_code='SG',
    currency='SGD',
    region_config={
        'orchard_core':  (1.3048, 103.8318, 0.005, 0.005, 3_200_000),
        'marina_bay':    (1.2830, 103.8607, 0.006, 0.006, 2_800_000),
        'sentosa':       (1.2494, 103.8303, 0.008, 0.008, 4_500_000),
        'bukit_timah':   (1.3294, 103.8021, 0.010, 0.010, 2_200_000),
        'east_coast':    (1.3010, 103.9146, 0.015, 0.015, 1_400_000),
        'jurong':        (1.3329, 103.7436, 0.020, 0.020,   850_000),
        'woodlands':     (1.4382, 103.7890, 0.020, 0.020,   650_000),
        'tampines':      (1.3496, 103.9568, 0.015, 0.015,   750_000),
    },
    region_weights=(0.12, 0.10, 0.06, 0.14, 0.14, 0.16, 0.14, 0.14),
    lat_range=(1.20, 1.48),
    lng_range=(103.60, 104.05),
    market_level={2020: 0.82, 2021: 0.88, 2022: 0.96, 2023: 0.99, 2024: 1.00},
    price_floor=300_000.0,
    price_ceiling=10_000_000.0,
    feature_min=(30.0, 300_000.0, 1.20, 103.60, 1.0),
    feature_max=(250.0, 10_000_000.0, 1.48, 104.05, 5.0),
    tolerance=0.08,
    # HDB/콘도 중심, 한국 아파트보다 소형 유닛 비중이 높음
    area_bins=(
        (35.0,  50.0, 0.15),
        (50.0,  70.0, 0.30),
        (70.0,  95.0, 0.28),
        (95.0, 125.0, 0.17),
        (125.0,180.0, 0.10),
    ),
)

# 홍콩: PHASE_13_1_GBL WBS 상 2순위 확장 국가 (Centaline 데이터 신뢰도 높음, SG와 유사 규모)
HK_CONFIG = CountryConfig(
    country_code='HK',
    currency='HKD',
    region_config={
        'the_peak':          (22.271, 114.150, 0.006, 0.006, 45_000_000),
        'central_midlevels': (22.280, 114.155, 0.008, 0.008, 28_000_000),
        'wan_chai':          (22.277, 114.172, 0.008, 0.008, 16_000_000),
        'causeway_bay':      (22.280, 114.185, 0.007, 0.007, 15_000_000),
        'tsim_sha_tsui':     (22.297, 114.172, 0.010, 0.010, 13_000_000),
        'mong_kok':          (22.319, 114.169, 0.012, 0.012,  9_500_000),
        'sha_tin':           (22.382, 114.188, 0.020, 0.020,  7_000_000),
        'tsuen_wan':         (22.371, 114.113, 0.020, 0.020,  6_200_000),
        'tung_chung':        (22.289, 113.943, 0.018, 0.018,  5_500_000),
    },
    region_weights=(0.03, 0.08, 0.12, 0.10, 0.14, 0.16, 0.15, 0.13, 0.09),
    lat_range=(22.15, 22.55),
    lng_range=(113.83, 114.40),
    market_level={2020: 0.92, 2021: 0.95, 2022: 0.90, 2023: 0.94, 2024: 1.00},
    price_floor=2_000_000.0,
    price_ceiling=80_000_000.0,
    feature_min=(15.0, 2_000_000.0, 22.15, 113.83, 1.0),
    feature_max=(220.0, 80_000_000.0, 22.55, 114.40, 5.0),
    tolerance=0.08,
    # 홍콩 주택은 세계에서 가장 작은 축 — 20~50sqm(200~500sqft)이 주력 평형
    area_bins=(
        (15.0,  30.0, 0.22),
        (30.0,  45.0, 0.28),
        (45.0,  65.0, 0.24),
        (65.0,  95.0, 0.16),
        (95.0, 150.0, 0.07),
        (150.0,220.0, 0.03),
    ),
    idiosyncratic_sigma=0.11,
)

COUNTRY_CONFIGS: Dict[str, CountryConfig] = {
    'KR': KR_CONFIG,
    'SG': SG_CONFIG,
    'HK': HK_CONFIG,
}


def get_country_config(country_code: str) -> CountryConfig:
    """국가 코드로 설정 조회."""
    if country_code not in COUNTRY_CONFIGS:
        raise ValueError(f"미지원 국가: {country_code} (지원: {list(COUNTRY_CONFIGS)})")
    return COUNTRY_CONFIGS[country_code]
