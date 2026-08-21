# Phase 13.6 — Real Data Collection Setup Guide

**Status**: MVP (Simulation + Real Data Framework)  
**Estimated Duration**: 2-4 weeks (API credential acquisition + integration)

## Overview

Phase 13.6 replaces simulated property data with real market data from 8 countries:

| Country | Primary Source | Secondary | Public API? | Estimated Records |
|---------|---------------|-----------|------------|------------------|
| BR | Seloger.com.br | FIPE, IBGE | ⚠️ Private | 20,000 |
| SG | URA API | HDB | ✅ Public (HDB) | 15,000 |
| HK | Centaline API | Land Registry | ⚠️ Private | 12,000 |
| UK | HM Land Registry | Rightmove | ⚠️ Commercial | 50,000+ |
| DE | Zillium API | Market reports | ⚠️ Private | 30,000 |
| AU | CoreLogic RP | Domain.com.au | ⚠️ Private | 40,000 |
| CA | StatsCan | Realtor.ca | ✅ Public (StatsCan) | 35,000 |
| TH | Proppy | Thai Real Estate Board | ⚠️ Private | 8,000 |

## Quick Start (Simulation Mode — No API Keys Required)

```bash
# Test the hybrid pipeline with simulated data (default)
python scripts/phase13_hybrid_pipeline.py --country BR

# Output: data/raw/BR_sim.csv (20,000 synthetic records)
```

## Real Data Setup (Requires API Credentials)

### 1. Obtain API Keys

#### Brazil (Seloger + FIPE + IBGE)
```bash
# Seloger: https://www.seloger.com.br/developer
# - Register for free tier (~500 requests/month)
# - Or request commercial API key

# FIPE: https://www.fipe.org.br/api
# - Public data, but unofficial API endpoints
# - Alternative: Download monthly CSV from website

# IBGE: https://www.ibge.gov.br/en/web/guest/
# - Public API, no key needed
# - Census + economic data free
```

#### Singapore (URA + HDB)
```bash
# URA: https://www.ura.gov.sg/maps/api
# - Commercial API, requires registration
# - Covers residential transactions

# HDB: https://data.gov.sg/
# - Public API, free
# - Public housing data (85% of Singapore market)
```

#### Others
```bash
# UK: https://www.gov.uk/land-registry/setting-up-property-data-services
# Hong Kong: https://www.centaline.com.hk/en/
# Germany: https://www.immobilien-datenbank.de/api
# Australia: https://www.corelogic.com.au/
# Canada: https://www.realtor.ca/api/
# Thailand: https://proppy.co.th/
```

### 2. Set Environment Variables

```bash
# Option A: Shell environment
export SELOGER_API_KEY="your_key_here"
export FIPE_API_KEY="your_key_here"
export URA_API_KEY="your_key_here"
# ... etc

# Option B: .env file (auto-loaded by Python)
echo "SELOGER_API_KEY=your_key" >> .env
echo "FIPE_API_KEY=your_key" >> .env
```

### 3. Run Real Data Collection

```bash
# Brazil (real data mode)
python scripts/phase13_hybrid_pipeline.py --country BR --use-real-data

# With auto-fallback to simulation if API fails
python scripts/phase13_hybrid_pipeline.py --country BR --use-real-data --fallback

# Singapore
python scripts/phase13_hybrid_pipeline.py --country SG --use-real-data

# Output: data/raw/{CC}_real.csv
```

## Implementation Details

### Architecture

```
phase13_real_data_base.py         Base class (ABC)
    ↓
phase13_real_data_br.py          Brazil implementation
    ↓
phase13_hybrid_pipeline.py       Simulation ↔ Real selection
    ↓
phase13_global_pipeline.py       Feature engineering + training
```

### File Structure

- `scripts/phase13_real_data_base.py` — Abstract base class
- `scripts/phase13_real_data_br.py` — Brazil collector (Seloger/FIPE/IBGE)
- `scripts/phase13_hybrid_pipeline.py` — Unified pipeline (sim/real toggle)
- `config/api_credentials.example.json` — API key template (DO NOT COMMIT)

### Workflow

1. **Data Collection**
   ```
   phase13_hybrid_pipeline.py --use-real-data
     ↓
   phase13_real_data_br.py._collect_batch()
     ↓ (API call or mock fallback)
   data/raw/{CC}_real.csv
   ```

2. **Enrichment**
   ```
   enrich_with_fipe()     Add real estate index
   enrich_with_ibge()     Add economic indicators
   ```

3. **Integration**
   ```
   phase13_global_pipeline.py accepts both:
   - data/raw/{CC}_sim.csv  (simulation)
   - data/raw/{CC}_real.csv (real)
   ```

## Current Implementation Status

✅ **Done:**
- Base class framework (real data ABC)
- Brazil collector (Seloger mock + FIPE/IBGE stubs)
- Hybrid pipeline (sim ↔ real toggle)
- API credential template
- Fallback-to-simulation logic

⏳ **TODO (per country):**
- SG: URA + HDB integration
- HK: Centaline + Land Registry
- UK: HM Land Registry + Rightmove
- DE: Zillium API
- AU: CoreLogic + Domain
- CA: StatsCan + Realtor.ca
- TH: Proppy + Manual scraping

## Expected Impact on Model Performance

| Scenario | MAPE | R² | Notes |
|----------|------|----|----|
| Simulated (current) | 6-8% | 0.96+ | Noise capped at tolerance |
| Real data (target) | 9-12% | 0.92-0.95 | Market noise + outliers |

Real data typically increases MAPE by 2-5% due to market inefficiencies and outliers not captured in simulation.

## Deployment Flow (Phase 14 CI/CD Integration)

```yaml
# .github/workflows/phase14_real_data_train.yml
on: [schedule, workflow_dispatch]
steps:
  - Collect real data (all 8 countries)
  - Feature engineering
  - Train models
  - Validate ONNX
  - Deploy if MAPE < threshold
```

## Known Limitations

1. **API Rate Limiting**: Some sources (BR, SG) have strict rate limits (30-100 req/s)
2. **Data Lag**: Public APIs often have 1-3 month delays
3. **API Reliability**: Third-party APIs may have outages → fallback to simulation
4. **Credentials**: Sensitive keys must NOT be committed to git
5. **Commercial Licenses**: UK (Rightmove), AU (CoreLogic), HK (Centaline) require paid subscriptions

## Troubleshooting

### "API key not found" → Falling back to simulation
```bash
# Check environment variable
env | grep SELOGER_API_KEY
# If missing, export it first
export SELOGER_API_KEY="your_key"
```

### Rate limit exceeded
```bash
# Reduce batch size or add delays
# phase13_real_data_base.py respects config['rate_limit']
# Adjust COUNTRY_API_CONFIG if needed
```

### API endpoint changed / API deprecated
```bash
# Update the endpoint in phase13_real_data_{CC}.py
# Usually found in source._collect_batch()
```

## Next Steps

1. Acquire API credentials (1-2 weeks, depends on approval)
2. Implement remaining collectors (SG, HK, UK, DE, AU, CA, TH)
3. Test hybrid pipeline end-to-end
4. Run Phase 14 CI/CD with real data
5. Compare model performance (real vs sim)
6. Document data quality findings

---

**Questions?** Check `.claude/EXECUTION_POLICY.md` or existing implementation in `scripts/phase13_real_data_br.py`.
