# Adding New Countries — Developer Guide

**Purpose**: Step-by-step instructions for extending Phase 13.6 to new countries  
**Target Audience**: Backend developers  
**Estimated Time**: 4-8 hours per country  
**Last Updated**: 2026-07-20

---

## Quick Overview

To add a new country:

1. Create `phase13_real_data_{CC}.py` extending `RealDataCollector`
2. Implement `_collect_batch()` and `_mock_batch()` 
3. Add 3-5 `enrich_with_*()` methods (country-specific)
4. Update `phase13_hybrid_pipeline.py` to load the new collector
5. Test with simulation mode first, then with real APIs
6. Add configuration to `config/api_credentials.example.json`
7. Document in `REAL_DATA_API_INTEGRATION_GUIDE.md`

---

## Detailed Implementation Steps

### Step 1: Create Collector Class

Create `scripts/phase13_real_data_{CC}.py` where `{CC}` = country code (e.g., `JP` for Japan):

```python
#!/usr/bin/env python3
"""
Phase 13.6.{CC} - Real Data Collection for {COUNTRY}
{API_1} + {API_2} integration.

Usage:
    python scripts/phase13_real_data_{cc}.py --records {N}
"""

import argparse
import logging
from typing import Dict, List

import pandas as pd

from phase13_real_data_base import RealDataCollector

log = logging.getLogger(__name__)


class {COUNTRY_TITLE}Collector(RealDataCollector):
    """{COUNTRY} real estate collector ({API_1} + {API_2})."""

    def __init__(self, output_dir: str = 'data/raw'):
        super().__init__('{CC}', output_dir)
        self.api_urls = {
            'primary': '{PRIMARY_API_ENDPOINT}',
            'secondary': '{SECONDARY_API_ENDPOINT}',
        }

    def _collect_batch(self, offset: int, limit: int) -> List[Dict]:
        """Batch collection with fallback chain."""
        import os
        import requests

        # Try primary API first
        api_key = os.getenv('{CC}_PRIMARY_API_KEY')
        if not api_key:
            log.debug(f"{'{CC}'} API key not set. Using simulation.")
            return self._mock_batch(offset, limit)

        try:
            headers = {'Authorization': f'Bearer {api_key}'}
            params = {'offset': offset, 'limit': limit}
            response = requests.get(self.api_urls['primary'], headers=headers,
                                   params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            records = self._parse_response(data)
            log.debug(f"Primary API batch: {len(records)} records")
            return records

        except Exception as e:
            log.warning(f"Primary API failed: {e}. Using simulation.")
            return self._mock_batch(offset, limit)

    def _mock_batch(self, offset: int, limit: int) -> List[Dict]:
        """Simulated batch data for {COUNTRY}."""
        import numpy as np

        # Define country-specific simulation parameters
        regions = [...]  # List of major cities/regions
        property_types = [...]  # Common property types
        records = []

        for i in range(limit):
            region = np.random.choice(regions)
            records.append({
                'property_id': f'{CC}_{region}_{offset + i:06d}',
                'region': region,
                'price': np.random.lognormal({μ}, {σ}),  # Local currency
                'area': np.random.uniform({min_area}, {max_area}),
                'bedrooms': np.random.choice([1, 2, 3, 4, 5]),
                'year_built': np.random.randint(1980, 2024),
                'property_type': np.random.choice(property_types),
                'latitude': np.random.uniform({lat_min}, {lat_max}),
                'longitude': np.random.uniform({lon_min}, {lon_max}),
            })

        return records

    def _parse_response(self, data: Dict) -> List[Dict]:
        """Parse API response into records."""
        records = []
        for item in data.get('results', []):
            try:
                records.append({
                    'property_id': item.get('id'),
                    'region': item.get('region'),
                    # ... map all relevant fields
                })
            except Exception as e:
                log.warning(f"Failed to parse record: {e}")
        return records

    def enrich_with_economic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add {COUNTRY}-specific economic data."""
        regional_indicators = {
            'Major_City': {'gdp_index': 1.50, 'unemployment': 5.2},
            'Secondary_City': {'gdp_index': 1.00, 'unemployment': 6.5},
            'Rural': {'gdp_index': 0.70, 'unemployment': 8.0},
        }

        df['gdp_index'] = df['region'].map(
            lambda r: regional_indicators.get(r, {}).get('gdp_index', 1.0)
        )
        df['unemployment_rate'] = df['region'].map(
            lambda r: regional_indicators.get(r, {}).get('unemployment', 6.5)
        )

        log.info("✅ Economic indicators enrichment applied")
        return df

    def enrich_with_regional_premiums(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add region-based price multipliers."""
        regional_premiums = {
            'Capital': 1.50,
            'Major_City': 1.20,
            'Secondary_City': 0.90,
            'Rural': 0.60,
        }

        df['regional_premium'] = df['region'].map(
            lambda r: regional_premiums.get(r, 1.0)
        )

        log.info("✅ Regional premiums enrichment applied")
        return df

    def enrich_with_property_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standardized property metrics."""
        df['price_per_sqm'] = df['price'] / (df['area'] + 1)
        df['price_per_bedroom'] = df['price'] / (df['bedrooms'] + 1)
        df['age'] = 2024 - df['year_built']

        log.info("✅ Property metrics enrichment applied")
        return df

    def collect_enriched(self, n_records: int = {DEFAULT_RECORDS}) -> pd.DataFrame:
        """Full collection + enrichment pipeline."""
        log.info("=" * 70)
        log.info("Phase 13.6.{CC} - {COUNTRY} Data Collection")
        log.info("=" * 70)

        df = self.collect(n_records)
        df = self.enrich_with_economic_indicators(df)
        df = self.enrich_with_regional_premiums(df)
        df = self.enrich_with_property_metrics(df)

        log.info(f"\n✅ Final dataset: {len(df)} records, {len(df.columns)} columns")
        return df


def main() -> None:
    parser = argparse.ArgumentParser(description='{COUNTRY} Real Data Collector')
    parser.add_argument('--records', type=int, default={DEFAULT_RECORDS})
    parser.add_argument('--output', default='data/raw/{CC}_real.csv')
    args = parser.parse_args()

    collector = {COUNTRY_TITLE}Collector()
    df = collector.collect_enriched(args.records)
    print(f"\n📊 Data sample (first 5 rows):")
    print(df.head())
    print(f"\n💾 Saved to: {args.output}")


if __name__ == '__main__':
    main()
```

### Step 2: Define Country Parameters

Before implementing, research and fill in:

```python
# Simulation Parameters
COUNTRY_CODE = 'JP'
COUNTRY_NAME = 'Japan'
PRIMARY_API = 'Suumo.jp' or 'Homes.co.jp'
SECONDARY_API = 'Realty.co.jp'
DEFAULT_RECORDS = 25000  # Estimated total capacity

# Regions
MAJOR_REGIONS = ['Tokyo', 'Osaka', 'Kyoto', 'Yokohama']

# Price Distribution (lognormal)
PRICE_MU = 13.0  # ln(property price)
PRICE_SIGMA = 0.7

# Property Types
PROPERTY_TYPES = ['apartment', 'house', 'condo', 'detached']

# Geographic Bounds
LAT_MIN, LAT_MAX = 30.0, 45.0
LON_MIN, LON_MAX = 130.0, 145.0

# Currency
CURRENCY = 'JPY'

# Rate Limits (from API docs)
PRIMARY_RATE_LIMIT = 60  # req/min
SECONDARY_RATE_LIMIT = 100
```

### Step 3: Implement Enrichment Methods

Design 3-5 enrichment methods specific to the country. Examples:

**For Asian Countries** (Japan, Malaysia, Thailand-like):
```python
def enrich_with_transit_proximity(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add distance to major transit (critical in Asia)."""
    import numpy as np
    df['transit_distance_km'] = np.random.uniform(0.1, 3.0, len(df))
    df['transit_premium'] = 1.0 + (0.3 * np.exp(-df['transit_distance_km']))
    return df

def enrich_with_building_earthquake_rating(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add earthquake safety rating (Japan)."""
    ratings = {0: 0.8, 1: 0.9, 2: 1.0, 3: 1.1}  # 0=old, 3=new seismic standard
    df['seismic_rating'] = np.random.choice(list(ratings.keys()), len(df))
    df['safety_premium'] = df['seismic_rating'].map(ratings)
    return df
```

**For European Countries** (Germany, France, Spain-like):
```python
def enrich_with_energy_certification(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add EU energy performance certificate (EPC) rating."""
    energy_ratings = {
        'A': 1.20,  # Most efficient
        'B': 1.10,
        'C': 1.00,
        'D': 0.90,
        'E': 0.80,
        'F': 0.70,
        'G': 0.60,  # Least efficient
    }
    df['energy_rating'] = np.random.choice(list(energy_ratings.keys()), len(df))
    df['energy_premium'] = df['energy_rating'].map(energy_ratings)
    return df

def enrich_with_listing_age(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add days on market (important in slow markets)."""
    df['days_on_market'] = np.random.randint(7, 365, len(df))
    df['listing_urgency'] = 1.0 - (df['days_on_market'] / 365 * 0.1)  # Max 10% discount
    return df
```

**For Market-Specific Features**:
```python
def enrich_with_luxury_classification(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add luxury property classification."""
    # Only properties >$2M are luxury in this market
    df['is_luxury'] = (df['price'] > 2_000_000).astype(int)
    df['luxury_premium'] = df['is_luxury'].apply(
        lambda x: 1.15 if x else 0.95  # Luxury gets 15% boost, regular -5%
    )
    return df
```

### Step 4: Update Hybrid Pipeline

Edit `phase13_hybrid_pipeline.py` to add your collector:

```python
def load_real_data(country: str) -> pd.DataFrame:
    """Load country-specific real data collector."""
    collectors = {
        'BR': ('phase13_real_data_br', 'BrazilCollector', 20000),
        'CA': ('phase13_real_data_ca', 'CanadaCollector', 35000),
        'SG': ('phase13_real_data_sg', 'SingaporeCollector', 15000),
        'DE': ('phase13_real_data_de', 'GermanyCollector', 30000),
        'TH': ('phase13_real_data_th', 'ThailandCollector', 8000),
        'AU': ('phase13_real_data_au', 'AustraliaCollector', 40000),
        'HK': ('phase13_real_data_hk', 'HongKongCollector', 12000),
        'UK': ('phase13_real_data_uk', 'UKCollector', 50000),
        'JP': ('phase13_real_data_jp', 'JapanCollector', 25000),  # NEW
    }
    # ... rest of function
```

Also update the CLI argument parser:

```python
parser = argparse.ArgumentParser(...)
parser.add_argument('--country', required=True, 
    choices=['BR', 'SG', 'HK', 'UK', 'DE', 'AU', 'CA', 'TH', 'JP'])  # Added JP
```

### Step 5: Configure API Credentials

Add to `config/api_credentials.example.json`:

```json
{
  "data_sources": {
    "JP": {
      "suumo": {
        "api_key": "YOUR_SUUMO_API_KEY_HERE",
        "endpoint": "https://api.suumo.jp/properties",
        "rate_limit": 60
      },
      "realty": {
        "api_key": "YOUR_REALTY_API_KEY_HERE",
        "endpoint": "https://api.realty.co.jp/search",
        "rate_limit": 100
      }
    }
  },
  "environment_variables": {
    "JP": ["SUUMO_API_KEY", "REALTY_API_KEY"]
  }
}
```

### Step 6: Test Implementation

```bash
# Test 1: Simulation mode (no API needed)
python scripts/phase13_hybrid_pipeline.py --country JP
# Expected: data/raw/JP_sim.csv with 25,000 records

# Test 2: Verify structure
python -c "
import pandas as pd
df = pd.read_csv('data/raw/JP_sim.csv')
print(f'Records: {len(df)}')
print(f'Columns: {list(df.columns)}')
print(f'Nulls: {df.isnull().sum().sum()}')
print(df.head())
"

# Test 3: Run statistics
python scripts/phase13_real_data_jp.py --records 100
```

### Step 7: Test with Real APIs (Once Configured)

```bash
# Set API keys
export SUUMO_API_KEY="your_key"
export REALTY_API_KEY="your_key"

# Test with real data
python scripts/phase13_hybrid_pipeline.py --country JP --use-real-data --fallback

# Verify real data collection
grep "✅ Real data" /tmp/*.log
ls -lh data/raw/JP_real.csv
```

### Step 8: Integration Testing

```python
# tests/test_phase13_real_data_jp.py
import unittest
import pandas as pd
from avm_project.scripts.phase13_real_data_jp import JapanCollector

class TestJapanCollector(unittest.TestCase):
    
    def setUp(self):
        self.collector = JapanCollector()
    
    def test_mock_batch_valid_structure(self):
        batch = self.collector._mock_batch(0, 100)
        self.assertEqual(len(batch), 100)
        required_fields = ['property_id', 'region', 'price', 'area', 'bedrooms']
        for record in batch:
            for field in required_fields:
                self.assertIn(field, record)
    
    def test_collect_enriched_adds_columns(self):
        df = self.collector.collect_enriched(n_records=100)
        expected_cols = [
            'gdp_index', 'unemployment_rate', 'regional_premium',
            'price_per_sqm', 'price_per_bedroom', 'age'
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns)
    
    def test_enrichment_order(self):
        # Verify enrichment methods run in correct order
        df = self.collector.collect_enriched(n_records=10)
        # After enrich_with_economic_indicators
        self.assertIn('gdp_index', df.columns)
        # After enrich_with_regional_premiums
        self.assertIn('regional_premium', df.columns)
        # After enrich_with_property_metrics
        self.assertIn('price_per_sqm', df.columns)

if __name__ == '__main__':
    unittest.main()
```

---

## Common Patterns & Templates

### Pattern 1: Economic Indicators (All Countries)

```python
def enrich_with_economic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
    """Template for economic enrichment."""
    # Define region-based indicators
    indicators = {
        'Region_A': {'gdp_index': 1.50, 'unemployment': 5.0},
        'Region_B': {'gdp_index': 1.00, 'unemployment': 6.5},
        'Region_C': {'gdp_index': 0.70, 'unemployment': 8.0},
    }
    
    # Map to regions in dataframe
    df['gdp_index'] = df['region'].map(lambda r: indicators.get(r, {}).get('gdp_index', 1.0))
    df['unemployment'] = df['region'].map(lambda r: indicators.get(r, {}).get('unemployment', 6.5))
    
    log.info("✅ Economic indicators enrichment applied")
    return df
```

### Pattern 2: Regional Premiums (All Countries)

```python
def enrich_with_regional_premiums(self, df: pd.DataFrame) -> pd.DataFrame:
    """Template for regional price adjustments."""
    premiums = {
        'Capital': 1.80,
        'Major_City': 1.20,
        'Medium_City': 0.90,
        'Rural': 0.60,
    }
    
    df['regional_premium'] = df['region'].map(lambda r: premiums.get(r, 1.0))
    
    log.info("✅ Regional premiums enrichment applied")
    return df
```

### Pattern 3: Age/Condition Impact

```python
def enrich_with_age_impact(self, df: pd.DataFrame) -> pd.DataFrame:
    """Template for building age effects."""
    import numpy as np
    
    df['age'] = 2024 - df['year_built']
    
    # Depreciation: 1-2% per year for first 30 years, then steeper
    df['age_factor'] = np.where(
        df['age'] <= 30,
        1.0 - (df['age'] * 0.015),  # 1-2% depreciation
        1.0 - (30 * 0.015) - ((df['age'] - 30) * 0.03)  # 3% after 30 years
    ).clip(lower=0.3)  # Don't go below 30% of original value
    
    log.info("✅ Age impact enrichment applied")
    return df
```

---

## Checklist for New Country

- [ ] Collector class created: `phase13_real_data_{CC}.py`
- [ ] `_collect_batch()` implemented with API fallback
- [ ] `_mock_batch()` generates realistic data
- [ ] `_parse_response()` correctly parses API format
- [ ] 3-5 `enrich_with_*()` methods implemented
- [ ] `collect_enriched()` orchestrates full pipeline
- [ ] CLI interface working (`--records`, `--output`)
- [ ] Hybrid pipeline updated with new collector
- [ ] CLI argument parser includes new country code
- [ ] API credentials added to `config/api_credentials.example.json`
- [ ] Environment variables documented
- [ ] Simulation mode tested (no API keys needed)
- [ ] Unit tests written and passing
- [ ] Integration test with hybrid pipeline passing
- [ ] Documentation updated (API guide, deployment guide)
- [ ] Real API testing done (if keys available)
- [ ] Code review completed
- [ ] Merged to main branch

---

## Performance Expectations

### Collection Speed

Expected rates (batches of 100 records):

| Source | Records/Minute |
|--------|----------------|
| Simulation | 150-200 |
| Real API (fast) | 50-70 |
| Real API (slow) | 20-40 |

**Example**: 25,000 records
- Simulation: ~2 minutes
- Real API: ~6-12 minutes

### Enrichment Speed

Enrichment should add <20% to total time:

- Economic indicators: ~50ms per 1000 records
- Regional premiums: ~30ms per 1000 records
- Property metrics: ~20ms per 1000 records

**Total for 25K records**: ~2-3 minutes

### Memory Usage

- 25,000 records × 100+ columns ≈ 300-500MB
- Total with enrichment: <1GB for single country

---

## Troubleshooting New Implementation

### "ModuleNotFoundError: No module named 'phase13_real_data_{cc}'"

**Cause**: Module not in `scripts/` directory or wrong name  
**Fix**: Verify file is `scripts/phase13_real_data_{cc}.py` (lowercase country code)

### "ValueError: Invalid choice: {cc}"

**Cause**: Country code not added to CLI parser  
**Fix**: Update `phase13_hybrid_pipeline.py` choices list

### "KeyError: 'gdp_index'" when running feature engineering

**Cause**: Enrichment column missing  
**Fix**: Verify all `enrich_with_*()` methods run and add expected columns

### API returns HTML instead of JSON

**Cause**: Endpoint URL incorrect  
**Fix**: Check API documentation, test with `curl` first

---

## Code Quality Standards

All new collectors must follow:

1. **Type Hints**: All functions must have complete type hints
   ```python
   def _collect_batch(self, offset: int, limit: int) -> List[Dict]:
   ```

2. **Max 50 Lines per Function** (100 max for complex logic)
   ```python
   # Keep individual enrichment methods under 30 lines
   def enrich_with_feature(self, df: pd.DataFrame) -> pd.DataFrame:
       # Implementation: 20-25 lines
       return df
   ```

3. **Docstrings**: Brief, purpose-focused
   ```python
   def enrich_with_economic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
       """Add region-based GDP and unemployment indicators."""
   ```

4. **No Debug Code**: No print statements or commented code

5. **Error Handling**: All API calls wrapped in try-except with fallback

---

## Support

- **Questions about base class?** → See `phase13_real_data_base.py` docstrings
- **Example implementations?** → Check `phase13_real_data_br.py` or `phase13_real_data_uk.py`
- **Testing help?** → See test files in `tests/` directory
- **Documentation updates?** → Edit this file

---

**End of Developer Guide**

Created new country? Update this section:

```markdown
## Supported Countries

| Code | Name | Status | Contributor | Date |
|------|------|--------|-------------|------|
| BR | Brazil | ✅ Complete | Original team | 2026-07-20 |
| JP | Japan | ✅ Complete | @newcontributor | 2026-07-27 |
```
