# Real Data API Integration Guide

**Purpose**: Step-by-step instructions for acquiring and configuring API credentials for each country  
**Status**: Complete for all 8 countries  
**Last Updated**: 2026-07-20

---

## Quick Reference Table

| Country | Primary API | Key Required? | Free Tier? | Setup Time | Documentation |
|---------|-------------|---------------|-----------|------------|---|
| BR | Seloger.com.br | ✅ | 500 req/mo | 2-3 days | https://www.seloger.com.br/developer |
| CA | Realtor.ca | ✅ | No | 1-2 days | https://www.realtor.ca/api/ |
| SG | URA / HDB | Mixed | HDB ✅ | 2-7 days | https://data.gov.sg/ |
| DE | Zillium | ✅ | No | 3-5 days | https://www.immobilien-datenbank.de |
| TH | Proppy | ✅ | No | 3-5 days | https://proppy.co.th/ |
| AU | CoreLogic | ✅ | No | 5-7 days | https://www.corelogic.com.au/ |
| HK | Centaline | ✅ | No | 3-5 days | https://www.centaline.com.hk/en/ |
| UK | Land Registry | ✅ | No | 5-10 days | https://www.gov.uk/land-registry/ |

**Legend**: ✅ = Available, ❌ = Not available, Mixed = Some free, some commercial

---

## Brazil (BR) — Seloger + FIPE + IBGE

### 1. Seloger API (Primary Source)

**Endpoint**: https://api.seloger.com.br  
**Authentication**: Bearer token  
**Rate Limit**: 100 req/min (free tier: 500 total/month)  
**Documentation**: https://www.seloger.com.br/developer

#### Setup Steps

1. **Register Developer Account**
   - Go to https://www.seloger.com.br/developer
   - Click "Sign Up" → Fill in email, password, company info
   - Accept terms of service
   - Verify email (check inbox)

2. **Create Application**
   - Login → Dashboard → "New Application"
   - App name: `loan4u_avm`
   - App type: `Backend Service`
   - Click "Create"

3. **Get API Key**
   - Dashboard → "API Keys" tab
   - Copy your `API_KEY` (looks like: `sk_test_abc123...`)
   - ⚠️ Keep this secret — don't commit to git

4. **Test Connection**
   ```bash
   export SELOGER_API_KEY="sk_test_your_key_here"
   curl -H "Authorization: Bearer $SELOGER_API_KEY" \
     https://api.seloger.com.br/search?country=BR&limit=10
   ```

### 2. FIPE API (Secondary: Real Estate Index)

**Endpoint**: https://www.fipe.org.br/api/v2  
**Authentication**: Bearer token  
**Rate Limit**: 50 req/min  
**Documentation**: https://www.fipe.org.br/api

#### Setup Steps

1. **Request API Access**
   - Go to https://www.fipe.org.br/api
   - Click "Request Access" → Fill form
   - Wait for email approval (1-2 days)

2. **Receive API Key**
   - Email will contain your API key
   - Typical format: `fipe_key_abc123...`

3. **Configure**
   ```bash
   export FIPE_API_KEY="fipe_key_your_key_here"
   ```

### 3. IBGE API (Tertiary: Census — Public, No Key)

**Endpoint**: https://servicodados.ibge.gov.br/api/v1  
**Authentication**: None (public)  
**Rate Limit**: 100 req/min (unlimited)  
**Documentation**: https://www.ibge.gov.br/en/web/guest/

#### Configuration

No key needed. Used automatically by BrazilCollector for economic indicators:
- State-level GDP index
- Population density
- Unemployment rates

---

## Canada (CA) — StatsCan + Realtor.ca

### 1. Realtor.ca API (Primary Source)

**Endpoint**: https://www.realtor.ca/api  
**Authentication**: Bearer token  
**Rate Limit**: 100 req/min  
**Documentation**: https://www.realtor.ca/api/

#### Setup Steps

1. **Register Developer Account**
   - Go to https://www.realtor.ca/developers
   - Create account with email/password
   - Accept API terms

2. **Generate API Key**
   - Dashboard → API Keys → "Generate New Key"
   - Copy token
   - Typical format: `ra_prod_abc123...`

3. **Set Environment Variable**
   ```bash
   export REALTOR_CA_API_KEY="ra_prod_your_key_here"
   ```

### 2. Statistics Canada (StatsCan) — Public, No Key

**Endpoint**: https://www.statcan.gc.ca/developers/json  
**Authentication**: None  
**Rate Limit**: 100 req/min (unlimited)  
**Documentation**: https://www.statcan.gc.ca/

#### Configuration

No key needed. Used for:
- Province-level GDP index
- Unemployment rates
- Housing market statistics

---

## Singapore (SG) — URA + HDB

### 1. HDB Public API (Primary: 85% of Market)

**Endpoint**: https://data.gov.sg/api/action  
**Authentication**: None (public)  
**Rate Limit**: 100 req/min  
**Documentation**: https://data.gov.sg/

#### Setup Steps

No registration needed! HDB data is freely available.

1. **Browse Available Datasets**
   - Visit https://data.gov.sg/
   - Search "HDB" or "housing"
   - Note resource ID for resale prices

2. **Use in Code** (Already configured)
   ```python
   # SingaporeCollector._collect_from_hdb() uses:
   # resource_id: 'f1645b29-c2f0-4352-9563-c2177cfc61e0'
   # (HDB resale prices dataset)
   ```

### 2. URA API (Secondary: Private Market)

**Endpoint**: https://www.ura.gov.sg/maps/api  
**Authentication**: Bearer token  
**Rate Limit**: 50 req/min  
**Documentation**: https://www.ura.gov.sg/

#### Setup Steps (If Needed)

1. **Contact URA**
   - Email: api@ura.gov.sg
   - Subject: "API Access Request for Property Data"
   - Explain use case (property valuation research)
   - Wait for approval (5-7 days)

2. **Receive Credentials**
   - Email contains API key and endpoint

3. **Configure**
   ```bash
   export URA_API_KEY="your_ura_key_here"
   ```

**Note**: HDB alone covers 85% of Singapore market. URA optional for completeness.

---

## Germany (DE) — Zillium API

**Endpoint**: https://api.zillium.de  
**Authentication**: Bearer token  
**Rate Limit**: 50 req/min  
**Documentation**: https://www.zillium.de/

#### Setup Steps

1. **Register for Zillium**
   - Go to https://www.immobilien-datenbank.de/api
   - Click "Request API Access"
   - Fill in company info, use case
   - Wait for approval (3-5 days)

2. **Receive API Key**
   - Zillium will email credentials
   - Typical format: `z_key_abc123...`

3. **Configure**
   ```bash
   export ZILLIUM_API_KEY="z_key_your_key_here"
   ```

4. **Test**
   ```bash
   curl -H "Authorization: Bearer $ZILLIUM_API_KEY" \
     https://api.zillium.de/properties/search?country=DE&limit=10
   ```

---

## Thailand (TH) — Proppy

**Endpoint**: https://api.proppy.co.th  
**Authentication**: Bearer token  
**Rate Limit**: 30 req/min  
**Documentation**: https://proppy.co.th/

#### Setup Steps

1. **Register Developer Account**
   - Visit https://proppy.co.th/developers
   - Sign up with email
   - Complete profile
   - Agree to API terms

2. **Create Application**
   - Dashboard → Applications → "Create New"
   - App name: `loan4u_avm`
   - App type: Real Estate Data
   - Accept Terms

3. **Get API Key**
   - Applications → Your app → API Keys tab
   - Copy key (format: `prop_key_abc123...`)

4. **Configure**
   ```bash
   export PROPPY_API_KEY="prop_key_your_key_here"
   ```

---

## Australia (AU) — CoreLogic + Domain

### 1. CoreLogic API (Primary Source)

**Endpoint**: https://api.corelogic.com.au  
**Authentication**: OAuth 2.0  
**Rate Limit**: 100 req/min  
**Documentation**: https://www.corelogic.com.au/

#### Setup Steps

1. **Contact CoreLogic Sales**
   - Email: api@corelogic.com.au
   - Subject: "API Access for Property Valuation Research"
   - Mention: loan4u AVM for residential property assessment
   - Provide: Company name, use case, estimated volume
   - Wait: 5-7 days for response

2. **Receive Credentials**
   - CoreLogic provides OAuth2 client ID and secret
   - Endpoint: https://auth.corelogic.com.au/oauth/authorize

3. **Configure**
   ```bash
   export CORELOGIC_API_KEY="your_corelogic_key"
   export CORELOGIC_CLIENT_ID="your_client_id"
   export CORELOGIC_CLIENT_SECRET="your_client_secret"
   ```

### 2. Domain.com.au API (Secondary)

**Endpoint**: https://api.domain.com.au/v1/listings  
**Authentication**: Bearer token  
**Rate Limit**: 50 req/min  
**Documentation**: https://developer.domain.com.au/

#### Setup Steps

1. **Register Developer Account**
   - Visit https://developer.domain.com.au/
   - Create account
   - Accept API terms

2. **Generate API Key**
   - Dashboard → API Keys → "Generate"
   - Copy token

3. **Configure**
   ```bash
   export DOMAIN_API_KEY="your_domain_key"
   ```

---

## Hong Kong (HK) — Centaline

**Endpoint**: https://api.centaline.com.hk  
**Authentication**: Bearer token  
**Rate Limit**: 30 req/min  
**Documentation**: https://www.centaline.com.hk/en/

#### Setup Steps

1. **Contact Centaline**
   - Email: api@centaline.com.hk
   - Subject: "API Access Request - Property Valuation Platform"
   - Provide: Company background, use case, expected volume
   - Wait: 3-5 days

2. **Receive API Key**
   - Email contains authentication token
   - Format: typically OAuth or API key

3. **Configure**
   ```bash
   export CENTALINE_API_KEY="your_centaline_key"
   ```

### Optional: Land Registry API

Hong Kong's Land Registry provides transaction history:

**Endpoint**: https://www.landreg.gov.hk/en/xml/  
**Authentication**: None (public XML feeds)  
**Documentation**: https://www.landreg.gov.hk/

⚠️ Land Registry data is XML format and requires parsing. Currently, Centaline API is sufficient for valuations.

---

## United Kingdom (UK) — HM Land Registry + Rightmove

### 1. HM Land Registry API

**Endpoint**: https://www.gov.uk/land-registry  
**Authentication**: OAuth 2.0  
**Rate Limit**: 100 req/min  
**Documentation**: https://www.gov.uk/land-registry/setting-up-property-data-services

#### Setup Steps

1. **Request Access**
   - Email: dataservices@landregistry.gov.uk
   - Subject: "API Access Request - Property Valuation Service"
   - Provide: Organization details, use case, volume estimates
   - Note: This is a commercial service
   - Wait: 5-10 days for evaluation

2. **License Agreement**
   - Land Registry may require commercial license
   - Fees: Typically £xxx/month based on volume
   - Once approved, receive OAuth2 credentials

3. **Configure OAuth2**
   ```bash
   export HM_LAND_REGISTRY_KEY="your_oauth_token"
   export HM_LAND_REGISTRY_CLIENT_ID="your_client_id"
   export HM_LAND_REGISTRY_CLIENT_SECRET="your_client_secret"
   ```

### 2. Rightmove API (Secondary)

**Endpoint**: https://api.rightmove.co.uk/v1/properties  
**Authentication**: Bearer token  
**Rate Limit**: 50 req/min  
**Documentation**: https://developer.rightmove.co.uk/

#### Setup Steps

1. **Register Developer Account**
   - Visit https://developer.rightmove.co.uk/
   - Sign up → API access request form
   - Describe use case
   - Wait: 2-3 days

2. **Receive API Key**
   - Email contains authentication token
   - Format: `rm_key_abc123...`

3. **Configure**
   ```bash
   export RIGHTMOVE_API_KEY="your_rightmove_key"
   ```

---

## Configuration Setup (All Countries)

### Method 1: Environment Variables (Recommended)

```bash
# Create .env file or add to ~/.bashrc
export SELOGER_API_KEY="your_seloger_key"
export FIPE_API_KEY="your_fipe_key"
export REALTOR_CA_API_KEY="your_realtor_key"
export URA_API_KEY="your_ura_key"
export ZILLIUM_API_KEY="your_zillium_key"
export PROPPY_API_KEY="your_proppy_key"
export CORELOGIC_API_KEY="your_corelogic_key"
export DOMAIN_API_KEY="your_domain_key"
export CENTALINE_API_KEY="your_centaline_key"
export HM_LAND_REGISTRY_KEY="your_land_registry_key"
export RIGHTMOVE_API_KEY="your_rightmove_key"

# Load in current shell
source ~/.bashrc
```

### Method 2: api_credentials.json (Local Development)

```bash
# Copy template
cp config/api_credentials.example.json config/api_credentials.json

# Edit with your keys
nano config/api_credentials.json

# ⚠️ IMPORTANT: Add to .gitignore
echo "config/api_credentials.json" >> .gitignore
git add .gitignore
git commit -m "Ignore API credentials"
```

**Format**:
```json
{
  "data_sources": {
    "BR": {
      "seloger": {
        "api_key": "your_seloger_key",
        "endpoint": "https://api.seloger.com.br"
      },
      "fipe": {
        "api_key": "your_fipe_key",
        "endpoint": "https://www.fipe.org.br/api/v2"
      }
    },
    ...
  }
}
```

### Method 3: Cloud Secrets Manager (Production)

For production deployments:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name loan4u/api_keys/seloger \
  --secret-string '{"api_key":"your_key"}'

# Google Secret Manager
gcloud secrets create seloger-api-key \
  --replication-policy="automatic" \
  --data-file=-

# Load in application
os.getenv('SELOGER_API_KEY')  # Injected by CI/CD
```

---

## Verification Steps

### Test Each Collector

```bash
# Test with simulator (no keys needed)
python scripts/phase13_hybrid_pipeline.py --country BR
python scripts/phase13_hybrid_pipeline.py --country CA
python scripts/phase13_hybrid_pipeline.py --country SG
# ... etc

# Verify output
ls -lh data/raw/*.csv
wc -l data/raw/BR_sim.csv  # Should show 20,000+ lines
```

### Test with Real Data

```bash
# Set API keys
export SELOGER_API_KEY="your_key"
export REALTOR_CA_API_KEY="your_key"

# Test with real data
python scripts/phase13_hybrid_pipeline.py --country BR --use-real-data --fallback
python scripts/phase13_hybrid_pipeline.py --country CA --use-real-data --fallback

# Check logs for success
# Should see: "✅ Real data loaded: 20,000 records"
# OR: "Real data failed. Falling back to simulation."
```

### Validate Data Quality

```python
import pandas as pd

# Load collected data
df = pd.read_csv('data/raw/BR_sim.csv')

# Check structure
print(df.info())  # Column names, types
print(df.describe())  # Statistics
print(df.isnull().sum())  # Missing values

# Verify enrichment columns
required_cols = ['price', 'area', 'bedrooms', 'fipe_index', 'gdp_index']
assert all(col in df.columns for col in required_cols), "Missing enrichment columns"

# Check price distribution
import numpy as np
log_prices = np.log(df['price'])
print(f"Price distribution: μ={log_prices.mean():.2f}, σ={log_prices.std():.2f}")
```

---

## Troubleshooting

### API Authentication Issues

**Problem**: `"HTTP 401 Unauthorized"`

**Solutions**:
1. Verify API key spelling (copy-paste from email)
2. Check key hasn't expired or been revoked
3. Confirm key matches environment variable name (e.g., `SELOGER_API_KEY`)
4. Try with test/staging key first (if available)

```bash
# Debug: Print key being used
python -c "import os; print(os.getenv('SELOGER_API_KEY'))"
```

### Rate Limiting

**Problem**: `"HTTP 429 Too Many Requests"`

**Solutions**:
1. Reduce batch size in config (default: 100)
2. Add delay between requests
3. Check if API quota already used up

```python
# In collector config
config = {
    'batch_size': 50,  # Reduced from 100
    'rate_limit': 30,  # Requests per minute
    'request_delay': 2.0,  # Seconds between requests
}
```

### Network/Proxy Issues

**Problem**: `"Connection timed out"` or proxy errors

**Solutions**:
1. Check internet connection: `ping 8.8.8.8`
2. Verify proxy settings
3. Increase timeout value
4. Try VPN if geographic restrictions apply

```bash
# Check if proxy needed
echo $HTTPS_PROXY
echo $HTTP_PROXY

# Set proxy if needed
export HTTPS_PROXY="http://proxy.company.com:8080"
```

### Data Format Issues

**Problem**: `"JSON decode error"` in `_parse_*_response()`

**Solutions**:
1. Log raw response for debugging
2. Check if API endpoint changed
3. Verify API documentation for latest format
4. Update parser to handle both old and new formats

```python
# Debug: Print raw response
import logging
logging.basicConfig(level=logging.DEBUG)
# Now see raw API responses in logs
```

---

## Support & Next Steps

- ✅ **Setup complete?** Test with `python scripts/phase13_hybrid_pipeline.py --country BR`
- ❌ **Having issues?** Check `.log` files in project root
- 📚 **Want more details?** See `PHASE_13_6_IMPLEMENTATION_GUIDE.md`
- 🚀 **Ready to deploy?** See `PHASE_13_6_DEPLOYMENT_OPERATIONS.md`

---

**End of API Integration Guide**
