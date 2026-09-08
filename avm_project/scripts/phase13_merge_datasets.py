#!/usr/bin/env python3
"""
Phase 13.2 - Merge Engineered + Integrated Feature Sets
특성 공학(54개) + 외부 데이터(20개) 결합 → 통합 학습 데이터 생성.

실행:
    python scripts/phase13_merge_datasets.py
"""

import logging
import pandas as pd
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

RAW_PATH = 'data/raw/KR_data.csv'
ENGINEERED_PATH = 'data/processed/KR_engineered.csv'
INTEGRATED_PATH = 'data/processed/KR_integrated.csv'
OUTPUT_PATH = 'data/processed/KR_combined.csv'
KEY_COL = 'property_id'


def main() -> None:
    raw_cols = set(pd.read_csv(RAW_PATH, nrows=0).columns)
    engineered = pd.read_csv(ENGINEERED_PATH)
    integrated = pd.read_csv(INTEGRATED_PATH)

    external_cols = [c for c in integrated.columns if c not in raw_cols]
    log.info(f"특성 공학 데이터: {engineered.shape[1]}개 컬럼")
    log.info(f"외부 데이터 신규 컬럼: {len(external_cols)}개")

    merged = engineered.merge(
        integrated[[KEY_COL] + external_cols], on=KEY_COL, validate='one_to_one'
    )
    assert len(merged) == len(engineered), "병합 후 행 수 불일치"

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False)
    log.info(f"✅ 저장 완료: {OUTPUT_PATH} ({merged.shape[0]} rows × {merged.shape[1]} cols)")


if __name__ == '__main__':
    main()
