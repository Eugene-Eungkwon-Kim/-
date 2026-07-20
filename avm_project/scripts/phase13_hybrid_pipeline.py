#!/usr/bin/env python3
"""
Phase 13.6+ - Hybrid Pipeline (Simulation ↔ Real Data)
시뮬레이션 데이터와 실데이터 수집 간 선택 가능한 통합 파이프라인.

실행:
    # 시뮬레이션 (기본)
    python phase13_hybrid_pipeline.py --country BR

    # 실데이터 (API 키 필요)
    python phase13_hybrid_pipeline.py --country BR --use-real-data
    export SELOGER_API_KEY="..."

    # 혼합 (실데이터 실패 시 시뮬레이션 자동 폴백)
    python phase13_hybrid_pipeline.py --country BR --use-real-data --fallback
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def load_real_data(country: str) -> pd.DataFrame:
    """국가별 실데이터 수집기 동적 임포트 및 실행."""
    try:
        if country == 'BR':
            from phase13_real_data_br import BrazilCollector
            collector = BrazilCollector()
            df = collector.collect_enriched(n_records=20000)
            return df
        # 추후 SG, HK 등 추가
        raise NotImplementedError(f"Real data collector not yet implemented for {country}")
    except Exception as e:
        log.error(f"Real data loading failed: {e}")
        raise


def load_simulated_data(country: str) -> pd.DataFrame:
    """시뮬레이션 데이터 로드 (기존 파이프라인)."""
    from phase13_global_pipeline import COUNTRY_CONFIGS, collect_country_data, engineer_features

    config = COUNTRY_CONFIGS[country]
    df = collect_country_data(country, config, 20000)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description='Hybrid Pipeline: Simulation ↔ Real Data')
    parser.add_argument('--country', required=True, choices=['BR', 'SG', 'HK', 'UK', 'DE', 'AU', 'CA', 'TH'])
    parser.add_argument('--use-real-data', action='store_true', help='Try real data (fallback to simulation if fails)')
    parser.add_argument('--fallback', action='store_true', help='Enable auto-fallback to simulation')
    parser.add_argument('--records', type=int, default=20000)
    args = parser.parse_args()

    log.info("=" * 70)
    log.info(f"Phase 13.6+ Hybrid Pipeline - {args.country}")
    log.info("=" * 70)

    # 데이터 로드
    use_real = False
    if args.use_real_data:
        try:
            log.info(f"Loading real data for {args.country}...")
            df = load_real_data(args.country)
            use_real = True
            log.info(f"✅ Real data loaded: {len(df)} records")
        except Exception as e:
            if args.fallback:
                log.warning(f"Real data failed ({e}). Falling back to simulation.")
                df = load_simulated_data(args.country)
            else:
                raise
    else:
        log.info(f"Loading simulated data for {args.country}...")
        df = load_simulated_data(args.country)
        log.info(f"✅ Simulated data loaded: {len(df)} records")

    # 저장
    raw_file = Path(f'data/raw/{args.country}_{"real" if use_real else "sim"}.csv')
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_file, index=False)
    log.info(f"✅ Data saved: {raw_file}")

    # 메타데이터
    metadata = {
        'country': args.country,
        'data_source': 'real' if use_real else 'simulated',
        'n_records': len(df),
        'n_features': len(df.columns),
        'columns': list(df.columns),
    }
    import json
    meta_file = raw_file.parent / f'{args.country}_hybrid_meta.json'
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n📊 {args.country} Data Ready:")
    print(f"   Source: {'🌐 Real API' if use_real else '🎲 Simulation'}")
    print(f"   Records: {len(df):,}")
    print(f"   Features: {len(df.columns)}")


if __name__ == '__main__':
    main()
