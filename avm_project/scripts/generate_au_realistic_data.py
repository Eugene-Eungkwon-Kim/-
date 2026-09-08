"""Phase 13.1-GBL - 호주 부동산 현실 데이터 생성.

PHASE_13_1_GBL_GLOBAL_EXPANSION_WBS.md의 4순위 확장 국가(AU). 국가 공용
엔진(realistic_data_generator.py)을 AU_CONFIG로 호출하는 얇은 래퍼로,
generate_sg_realistic_data.py/generate_hk_realistic_data.py/
generate_uk_realistic_data.py와 동일한 패턴을 따른다.

실행:
    python scripts/generate_au_realistic_data.py --rows 10000 --output data/raw/AU_data.csv
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from country_configs import AU_CONFIG
from realistic_data_generator import generate_dataset as _generate_dataset
from realistic_data_generator import validate_and_report as _validate_and_report

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def generate_dataset(n_rows: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """호주 현실 부동산 데이터셋 생성."""
    return _generate_dataset(AU_CONFIG, n_rows=n_rows, seed=seed)


def validate_and_report(df: pd.DataFrame) -> None:
    """생성 데이터 품질 검증 및 통계 출력."""
    _validate_and_report(df, AU_CONFIG)


def main() -> None:
    parser = argparse.ArgumentParser(description='AU 현실 부동산 데이터 생성')
    parser.add_argument('--rows',   type=int, default=10_000)
    parser.add_argument('--seed',   type=int, default=42)
    parser.add_argument('--output', default='data/raw/AU_data.csv')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"AU 현실 데이터 생성: {args.rows:,}행")
    log.info("=" * 60)

    df = generate_dataset(n_rows=args.rows, seed=args.seed)
    validate_and_report(df)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding='utf-8-sig')
    log.info(f"\n✅ 저장 완료: {out} ({len(df):,}행 × {len(df.columns)}컬럼)")


if __name__ == '__main__':
    main()
