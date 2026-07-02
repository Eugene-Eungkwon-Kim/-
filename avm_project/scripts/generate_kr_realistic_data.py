"""WP 1: 한국 부동산 현실 데이터 생성 (2024년 KB국민은행 통계 기반).

Phase 13.1-GBL에서 국가 공용 엔진(realistic_data_generator.py)으로 일반화된
알고리즘을 KR_CONFIG로 호출하는 얇은 래퍼. district_code(행정구역 코드)만
KR 고유 후처리로 별도 추가한다.

실행:
    python scripts/generate_kr_realistic_data.py --rows 10000 --output data/raw/KR_data.csv
"""

import argparse
import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from country_configs import KR_CONFIG
from realistic_data_generator import generate_dataset as _generate_dataset
from realistic_data_generator import validate_and_report as _validate_and_report

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

DISTRICT_MAP: Dict[str, str] = {
    'gangnam_3gu': '11680', 'seoul_prime': '11440', 'seoul_central': '11110',
    'seoul_north': '11350', 'seoul_west': '11500', 'gyeonggi_prime': '41130',
    'gyeonggi_mid': '41111', 'gyeonggi_outer': '41590', 'incheon': '28110',
    'busan_haeundae': '26350', 'busan_general': '26110',
}


def generate_dataset(n_rows: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """한국 현실 부동산 데이터셋 생성 (KR_CONFIG + district_code 후처리)."""
    df = _generate_dataset(KR_CONFIG, n_rows=n_rows, seed=seed)
    df['district_code'] = df['region_name'].map(DISTRICT_MAP)
    # district_code를 region_name 앞으로: 리팩토링 전 원본 컬럼 순서와 동일하게 유지
    ordered_cols = [c for c in df.columns if c not in ('district_code', 'region_name')]
    ordered_cols += ['district_code', 'region_name']
    return df[ordered_cols]


def validate_and_report(df: pd.DataFrame) -> None:
    """생성 데이터 품질 검증 및 통계 출력."""
    _validate_and_report(df, KR_CONFIG)


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
