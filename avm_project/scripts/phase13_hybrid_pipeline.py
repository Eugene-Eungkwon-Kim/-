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
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def load_real_data(country: str) -> pd.DataFrame:
    """Load country-specific real data collector and execute."""
    try:
        collectors = {
            'BR': ('phase13_real_data_br', 'BrazilCollector', 20000),
            'SG': ('phase13_real_data_sg', 'SingaporeCollector', 15000),
            'HK': ('phase13_real_data_hk', 'HongKongCollector', 12000),
            'UK': ('phase13_real_data_uk', 'UKCollector', 50000),
            'DE': ('phase13_real_data_de', 'GermanyCollector', 30000),
            'AU': ('phase13_real_data_au', 'AustraliaCollector', 40000),
            'CA': ('phase13_real_data_ca', 'CanadaCollector', 35000),
            'TH': ('phase13_real_data_th', 'ThailandCollector', 8000),
        }

        if country not in collectors:
            raise NotImplementedError(f"Real data collector not implemented for {country}")

        module_name, class_name, n_records = collectors[country]
        module = __import__(module_name)
        collector_class = getattr(module, class_name)
        collector = collector_class()
        df = collector.collect_enriched(n_records=n_records)
        return df
    except Exception as e:
        log.error(f"Real data loading failed: {e}")
        raise


def load_simulated_data(country: str) -> pd.DataFrame:
    """Load simulated data (existing pipeline)."""
    try:
        from phase13_global_pipeline import COUNTRY_CONFIGS, collect_country_data
        config = COUNTRY_CONFIGS[country]
        df = collect_country_data(country, config, 20000)
        return df
    except KeyError:
        # BR not in global pipeline, generate basic simulation
        if country == 'BR':
            return _generate_basic_simulation(country, 20000)
        raise


def _generate_basic_simulation(country: str, n_records: int) -> pd.DataFrame:
    """Generate basic simulation for countries not in global pipeline."""
    import numpy as np

    price_distributions = {
        'BR': {'mu': 12.8, 'sigma': 0.6, 'currency': 'BRL'},
    }

    if country not in price_distributions:
        raise ValueError(f"Unknown country: {country}")

    dist = price_distributions[country]
    records = []

    for i in range(n_records):
        records.append({
            'property_id': f'{country}_{i:06d}',
            'price_local': np.random.lognormal(dist['mu'], dist['sigma']),
            'area_m2': np.random.uniform(40, 250),
            'bedrooms': np.random.choice([1, 2, 3, 4, 5]),
            'year_built': np.random.randint(1980, 2023),
            'latitude': np.random.uniform(-33.8, 5.0),
            'longitude': np.random.uniform(-73.0, -35.0),
        })

    return pd.DataFrame(records)


def collect_single_country(
    country: str, use_real: bool, fallback: bool
) -> Tuple[str, Optional[pd.DataFrame], bool, float]:
    """Collect data for single country (for parallel execution)."""
    start_time = time.time()
    source = 'simulation'

    try:
        if use_real:
            try:
                df = load_real_data(country)
                source = 'real'
            except Exception as e:
                if fallback:
                    log.warning(f"[{country}] Real data failed: {e}. Falling back to simulation.")
                    df = load_simulated_data(country)
                else:
                    raise
        else:
            df = load_simulated_data(country)

        elapsed = time.time() - start_time
        return country, df, True, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        log.error(f"[{country}] Collection failed: {e}")
        return country, None, False, elapsed


def collect_parallel(
    countries: List[str], use_real: bool, fallback: bool, max_workers: int = 4
) -> Dict[str, Dict]:
    """Collect data for multiple countries in parallel."""
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(collect_single_country, cc, use_real, fallback): cc
            for cc in countries
        }

        for future in as_completed(futures):
            country, df, success, elapsed = future.result()
            results[country] = {
                'dataframe': df,
                'success': success,
                'elapsed': elapsed,
            }

            if success:
                log.info(f"✅ [{country}] Collected ({elapsed:.1f}s)")
            else:
                log.error(f"❌ [{country}] Failed ({elapsed:.1f}s)")

    return results


def save_country_data(
    country: str, df: pd.DataFrame, source: str
) -> None:
    """Save dataframe and metadata for country."""
    raw_file = Path(f'data/raw/{country}_{source}.csv')
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_file, index=False)

    metadata = {
        'country': country,
        'data_source': source,
        'n_records': len(df),
        'n_features': len(df.columns),
        'columns': list(df.columns),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    meta_file = raw_file.parent / f'{country}_hybrid_meta.json'
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    log.info(f"✅ Saved: {raw_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.6+ Hybrid Pipeline')
    parser.add_argument(
        '--country',
        default=None,
        choices=['BR', 'SG', 'HK', 'UK', 'DE', 'AU', 'CA', 'TH'],
        help='Single country (omit for all)',
    )
    parser.add_argument('--use-real-data', action='store_true', help='Try real data')
    parser.add_argument('--fallback', action='store_true', help='Fallback to simulation')
    parser.add_argument('--parallel', action='store_true', help='Parallel collection (default if all countries)')
    parser.add_argument('--workers', type=int, default=4, help='Max parallel workers')
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Phase 13.6+ Hybrid Pipeline")
    log.info("=" * 70)

    start_time = time.time()

    if args.country:
        # Single country (sequential)
        country = args.country
        log.info(f"Collecting {country}...")

        if args.use_real_data:
            try:
                df = load_real_data(country)
                source = 'real'
            except Exception as e:
                if args.fallback:
                    log.warning(f"Real data failed: {e}. Using simulation.")
                    df = load_simulated_data(country)
                    source = 'sim'
                else:
                    raise
        else:
            df = load_simulated_data(country)
            source = 'sim'

        save_country_data(country, df, source)
        log.info(f"📊 {country}: {len(df):,} records, {len(df.columns)} features")

    else:
        # All countries (parallel by default)
        countries = ['BR', 'SG', 'HK', 'UK', 'DE', 'AU', 'CA', 'TH']
        use_parallel = args.parallel or not args.country

        if use_parallel:
            log.info(f"Collecting {len(countries)} countries (parallel, {args.workers} workers)...")
            results = collect_parallel(countries, args.use_real_data, args.fallback, args.workers)

            for country in countries:
                if country in results and results[country]['success']:
                    df = results[country]['dataframe']
                    source = 'real' if args.use_real_data else 'sim'
                    save_country_data(country, df, source)
                    log.info(f"📊 {country}: {len(df):,} records")
        else:
            for country in countries:
                country_result, df, success, _ = collect_single_country(country, args.use_real_data, args.fallback)
                if success:
                    source = 'real' if args.use_real_data else 'sim'
                    save_country_data(country, df, source)

    elapsed = time.time() - start_time
    log.info(f"\n✅ Complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")


if __name__ == '__main__':
    main()
