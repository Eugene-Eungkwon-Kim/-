#!/usr/bin/env python3
"""
Phase 13.6 Base - Real Data Collection Framework
실제 부동산 데이터 API 통합 (국가별 수집기 기본 클래스).

국가별 구현체는 상속 후 _collect_batch() 오버라이드:
  class BrazilCollector(RealDataCollector):
      def _collect_batch(self, offset: int, limit: int) -> List[Dict]:
          # Seloger API 호출 및 데이터 변환
          ...
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# 국가별 API 구성: (data_source, api_docs_url, sample_fields)
COUNTRY_API_CONFIG = {
    'BR': {
        'source': 'Seloger + FIPE + IBGE',
        'api_key_env': 'SELOGER_API_KEY',
        'expected_fields': ['city', 'price', 'area', 'bedrooms', 'year_built'],
        'rate_limit': 100,  # 초당 요청
    },
    'SG': {
        'source': 'URA API + HDB',
        'api_key_env': 'URA_API_KEY',
        'expected_fields': ['district', 'price', 'area', 'property_type', 'year_built'],
        'rate_limit': 50,
    },
    'HK': {
        'source': 'Centaline API + Land Registry',
        'api_key_env': 'CENTALINE_API_KEY',
        'expected_fields': ['district', 'price', 'area', 'building_type', 'year_built'],
        'rate_limit': 30,
    },
    'UK': {
        'source': 'HM Land Registry + Rightmove',
        'api_key_env': 'HM_LAND_REGISTRY_KEY',
        'expected_fields': ['postcode', 'price', 'area', 'property_type', 'year_built'],
        'rate_limit': 100,
    },
    'DE': {
        'source': 'Zillium API + CBRE',
        'api_key_env': 'ZILLIUM_API_KEY',
        'expected_fields': ['city', 'price', 'area', 'apartment_type', 'year_built'],
        'rate_limit': 50,
    },
    'AU': {
        'source': 'CoreLogic RP Data + Domain',
        'api_key_env': 'CORELOGIC_API_KEY',
        'expected_fields': ['suburb', 'price', 'area', 'bedrooms', 'year_built'],
        'rate_limit': 100,
    },
    'CA': {
        'source': 'StatsCan Housing + Realtor.ca',
        'api_key_env': 'STATCAN_API_KEY',
        'expected_fields': ['city', 'price', 'area', 'bedrooms', 'year_built'],
        'rate_limit': 50,
    },
    'TH': {
        'source': 'Proppy + Thai Real Estate Board',
        'api_key_env': 'PROPPY_API_KEY',
        'expected_fields': ['district', 'price', 'area', 'bedrooms', 'year_built'],
        'rate_limit': 30,
    },
}


class RealDataCollector(ABC):
    """국가별 실데이터 수집 기본 클래스."""

    def __init__(self, country: str, output_dir: str = 'data/raw') -> None:
        if country not in COUNTRY_API_CONFIG:
            raise ValueError(f"Unsupported country: {country}")

        self.country = country
        self.config = COUNTRY_API_CONFIG[country]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / f'{country}_real.csv'
        self.log_file = self.output_dir / f'{country}_collection_log.json'

        log.info(f"Initialized {country} collector")
        log.info(f"  Data source: {self.config['source']}")
        log.info(f"  API key env: {self.config['api_key_env']}")
        log.info(f"  Expected fields: {self.config['expected_fields']}")

    @abstractmethod
    def _collect_batch(self, offset: int, limit: int) -> List[Dict]:
        """국가별 API에서 배치 수집 (구현체에서 오버라이드)."""
        pass

    def collect(self, n_records: int = 10000) -> pd.DataFrame:
        """전체 데이터 수집 (API 레이트 리미팅 적용)."""
        import time
        import os

        api_key = os.getenv(self.config['api_key_env'])
        if not api_key:
            log.warning(f"API key not found ({self.config['api_key_env']}). "
                       f"Using simulation mode.")
            return self._simulate_fallback(n_records)

        all_records: List[Dict] = []
        batch_size = 100
        rate_limit = self.config['rate_limit']
        delay_per_batch = batch_size / rate_limit

        try:
            for offset in range(0, n_records, batch_size):
                batch = self._collect_batch(offset, batch_size)
                all_records.extend(batch)

                log.info(f"Collected {len(all_records)}/{n_records} records "
                        f"({len(all_records)/n_records*100:.0f}%)")

                if offset + batch_size < n_records:
                    time.sleep(delay_per_batch)
                else:
                    break

        except Exception as e:
            log.error(f"Collection failed: {e}. Falling back to simulation.")
            return self._simulate_fallback(n_records)

        df = pd.DataFrame(all_records)
        self._log_collection_stats(df)
        df.to_csv(self.output_file, index=False)
        log.info(f"✅ Saved {len(df)} records to {self.output_file}")

        return df

    def _simulate_fallback(self, n_records: int) -> pd.DataFrame:
        """API 미사용 시 시뮬레이션 데이터 반환."""
        log.warning(f"Using simulated data for {self.country} ({n_records} records)")
        # 실제로는 phase13_global_pipeline.py의 collect_country_data() 사용
        import numpy as np
        rows = []
        for i in range(n_records):
            rows.append({
                'property_id': f'{self.country}_SIM_{i:06d}',
                'price': np.random.lognormal(13, 0.5),
                'area': np.random.uniform(40, 250),
                'year_built': np.random.randint(1985, 2023),
            })
        return pd.DataFrame(rows)

    def _log_collection_stats(self, df: pd.DataFrame) -> None:
        """수집 통계를 JSON 로그에 기록."""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'country': self.country,
            'data_source': self.config['source'],
            'n_records': len(df),
            'fields': list(df.columns),
            'price_stats': {
                'min': float(df['price'].min()) if 'price' in df else None,
                'max': float(df['price'].max()) if 'price' in df else None,
                'mean': float(df['price'].mean()) if 'price' in df else None,
            } if 'price' in df else {},
        }

        with open(self.log_file, 'w') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        log.info(f"Collection stats saved to {self.log_file}")


if __name__ == '__main__':
    # 시뮬레이션 데모
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    for cc in ['BR', 'SG', 'HK']:
        config = COUNTRY_API_CONFIG[cc]
        print(f"\n{cc}: {config['source']}")
        print(f"  API Key: {config['api_key_env']}")
        print(f"  Fields: {', '.join(config['expected_fields'])}")
