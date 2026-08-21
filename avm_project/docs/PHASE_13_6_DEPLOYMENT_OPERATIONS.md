# Phase 13.6 — Deployment & Operations Guide

**Purpose**: Deploy real data collection pipeline to production and monitor operations  
**Status**: Ready for MVP deployment  
**Last Updated**: 2026-07-20

---

## Deployment Checklist

### Pre-Deployment (1-2 hours)

- [ ] All API credentials acquired (see `REAL_DATA_API_INTEGRATION_GUIDE.md`)
- [ ] Credentials stored in `.env` or secrets manager (NOT committed to git)
- [ ] `.gitignore` includes `api_credentials.json`
- [ ] Environment variables tested locally
- [ ] All 8 collectors tested with `--use-real-data --fallback` flag
- [ ] Output files validated (record count, column structure)
- [ ] Enrichment columns verified for each country
- [ ] Fallback to simulation tested (API disabled scenario)

### Deployment (Environment Setup)

#### Option 1: Docker Deployment (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY avm_project/ ./avm_project/
COPY scripts/ ./scripts/

# Set API keys via environment (injected by orchestration)
ENV SELOGER_API_KEY=""
ENV FIPE_API_KEY=""
ENV REALTOR_CA_API_KEY=""
ENV URA_API_KEY=""
ENV ZILLIUM_API_KEY=""
ENV PROPPY_API_KEY=""
ENV CORELOGIC_API_KEY=""
ENV DOMAIN_API_KEY=""
ENV CENTALINE_API_KEY=""
ENV HM_LAND_REGISTRY_KEY=""
ENV RIGHTMOVE_API_KEY=""

ENTRYPOINT ["python", "-m", "scripts.phase13_hybrid_pipeline"]
```

**Build & Test**:
```bash
docker build -t loan4u-avm:phase13.6 .
docker run -e SELOGER_API_KEY="test" loan4u-avm:phase13.6 --country BR
```

#### Option 2: Direct System Deployment

```bash
# Install dependencies
pip install -r avm_project/requirements.txt

# Set up cron job for daily collection
crontab -e
# Add line:
# 0 2 * * * cd /home/loan4u && python scripts/phase13_hybrid_pipeline.py --country BR --use-real-data --fallback >> logs/collection_br.log 2>&1

# Set up log rotation
cat > /etc/logrotate.d/loan4u <<EOF
/home/loan4u/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
}
EOF
```

#### Option 3: Cloud Deployment (GCP / AWS)

**Google Cloud Platform**:
```bash
# Deploy to Cloud Run
gcloud run deploy loan4u-avm-phase13-6 \
  --source . \
  --entry-point phase13_hybrid_pipeline \
  --memory 2Gi \
  --timeout 1800 \
  --set-env-vars SELOGER_API_KEY=$(gcloud secrets versions access latest --secret="seloger-api-key")

# Schedule daily execution
gcloud scheduler jobs create app-engine collect-daily \
  --location us-central1 \
  --schedule "0 2 * * *" \
  --http-method POST \
  --uri https://region-project.cloudfunctions.net/collect-data
```

**AWS Lambda**:
```bash
# Package and deploy
zip -r function.zip avm_project/ scripts/ requirements.txt

aws lambda create-function \
  --function-name loan4u-avm-phase13-6 \
  --runtime python3.11 \
  --handler lambda_handler.main \
  --zip-file fileb://function.zip \
  --environment Variables={SELOGER_API_KEY=...,FIPE_API_KEY=...}

# Schedule with EventBridge
aws events put-rule --name collect-daily --schedule-expression "cron(0 2 * * ? *)"
```

---

## Production Configuration

### Environment Variables

**Required** (if using real data mode):
```bash
# Set these in production secrets manager, not shell history

# Brazil
SELOGER_API_KEY="sk_prod_..."
FIPE_API_KEY="fipe_prod_..."

# Canada
REALTOR_CA_API_KEY="ra_prod_..."

# Singapore
URA_API_KEY="ura_prod_..."  # Optional (HDB is public)

# Germany
ZILLIUM_API_KEY="z_prod_..."

# Thailand
PROPPY_API_KEY="prop_prod_..."

# Australia
CORELOGIC_API_KEY="cl_prod_..."
DOMAIN_API_KEY="domain_prod_..."

# Hong Kong
CENTALINE_API_KEY="cent_prod_..."

# UK
HM_LAND_REGISTRY_KEY="land_prod_..."
RIGHTMOVE_API_KEY="rm_prod_..."
```

### Configuration Tuning

**For High-Volume Production** (50K+ records/day):

```python
# phase13_real_data_base.py adjustments
PRODUCTION_CONFIG = {
    'batch_size': 50,  # Reduced from 100 (rate limit safety)
    'rate_limit': 20,  # Conservative: 20 req/min
    'request_timeout': 15,  # Increased from 10 (network stability)
    'max_retries': 3,  # Retry failed batches
    'retry_delay': 5,  # 5 second backoff
    'output_dir': '/var/data/loan4u/raw',  # Production path
}
```

**For Cost Optimization**:

```python
# Simulation-only mode (if API quotas too high)
USE_REAL_DATA = False  # Forces all collections to simulation
# This gives 100% uptime but 2-3% higher MAPE

# OR selective real data (only for top 3 countries)
COUNTRIES_REAL = ['BR', 'CA', 'UK']  # Expensive APIs
COUNTRIES_SIM = ['SG', 'DE', 'TH', 'AU', 'HK']  # Free/cheap fallback
```

---

## Operations & Monitoring

### Scheduled Collection

#### Daily Collection (Recommended)

```bash
#!/bin/bash
# /home/loan4u/scripts/collect_daily.sh

set -e  # Exit on error
LOG_DIR="/var/log/loan4u"
mkdir -p $LOG_DIR

for country in BR CA SG DE TH AU HK UK; do
    echo "[$(date)] Collecting $country..."
    python /home/loan4u/scripts/phase13_hybrid_pipeline.py \
        --country $country \
        --use-real-data \
        --fallback \
        >> $LOG_DIR/collect_$country.log 2>&1
    
    # Validate output
    if [ -f /var/data/loan4u/raw/${country}_real.csv ]; then
        COUNT=$(wc -l < /var/data/loan4u/raw/${country}_real.csv)
        echo "✅ $country: $COUNT records collected"
    else
        echo "⚠️ $country: Fell back to simulation"
    fi
done

echo "[$(date)] Collection complete"
```

**Add to Crontab**:
```bash
# Run daily at 2 AM UTC (0 2 * * *)
0 2 * * * /home/loan4u/scripts/collect_daily.sh

# Run weekly validation (Sundays at 3 AM)
0 3 * * 0 /home/loan4u/scripts/validate_data.sh

# Run monthly archival (1st of month at 4 AM)
0 4 1 * * /home/loan4u/scripts/archive_old_data.sh
```

#### Monthly Model Retraining

```bash
#!/bin/bash
# /home/loan4u/scripts/retrain_monthly.sh

# Collect latest real data for all countries
for country in BR CA SG DE TH AU HK UK; do
    python /home/loan4u/scripts/phase13_hybrid_pipeline.py \
        --country $country \
        --use-real-data \
        --fallback
done

# Feature engineering
python /home/loan4u/scripts/phase13_global_pipeline.py --engineer-features

# Model training
for country in BR CA SG DE TH AU HK UK; do
    python /home/loan4u/scripts/phase13_model_trainer.py \
        --country $country \
        --validate-performance
done

# Validation
python /home/loan4u/scripts/phase14_monitor.py check-mape --threshold 10.5

# Deploy if performance acceptable
if [ $? -eq 0 ]; then
    python /home/loan4u/scripts/phase13_model_converter.py --convert-all
    # Deploy models to inference engine
fi
```

---

## Monitoring & Alerting

### Key Metrics

| Metric | Target | Alert Threshold | Check Frequency |
|--------|--------|-----------------|-----------------|
| Collection Success Rate | >95% | <90% | Daily |
| API Response Time | <2s | >5s | Per request |
| Data Quality (null %) | <1% | >5% | Per collection |
| Model MAPE | <10.5% | >11% | Monthly |
| Inference Latency (p50) | <5ms | >10ms | Every request |
| Storage Usage | <100GB | >80GB | Weekly |
| API Quota Usage | <80% | >90% | Daily |

### Logging Strategy

```python
# Configure structured logging
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'country': getattr(record, 'country', 'N/A'),
            'records_collected': getattr(record, 'count', 0),
            'message': record.getMessage(),
        }
        return json.dumps(log_data)

# Use in collectors
log.info("Collection complete", extra={'country': 'BR', 'count': 20000})
# Output: {"timestamp": "...", "level": "INFO", "country": "BR", "records_collected": 20000, ...}
```

### Example Monitoring Dashboard (Prometheus + Grafana)

```python
# Expose metrics for scraping
from prometheus_client import Counter, Histogram, Gauge

# Counters
collection_total = Counter('collection_total', 'Total collections', ['country', 'status'])
records_collected = Counter('records_collected_total', 'Total records collected', ['country'])

# Gauges
collection_duration = Gauge('collection_duration_seconds', 'Collection time', ['country'])
api_quota_usage = Gauge('api_quota_usage_percent', 'API quota %', ['country'])

# Histograms
api_response_time = Histogram('api_response_time_seconds', 'API latency', ['country'])

# Use in collection
with api_response_time.labels(country='BR').time():
    df = collector.collect_enriched()
    collection_total.labels(country='BR', status='success').inc()
    records_collected.labels(country='BR').inc(len(df))
```

### Alert Examples

**Email Alert Template**:
```
Subject: ⚠️ Loan4U AVM Phase 13.6 Alert - Collection Failed

Body:
Collection Status: FAILED
Country: Brazil (BR)
Time: 2026-07-20 02:15:00 UTC
Reason: API returned HTTP 429 (rate limit exceeded)

Actions Taken:
- Automatic fallback to simulation: SUCCESS
- Fallback records: 20,000 (expected: 20,000)
- Data quality: PASSED

Next Collection: 2026-07-21 02:00:00 UTC

Dashboard: https://monitoring.loan4u.com/dashboard
Logs: https://logging.loan4u.com/logs?country=BR&date=2026-07-20
```

**Slack Integration**:
```python
# Post to Slack on failures
import requests

def alert_slack(country: str, status: str, message: str):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return
    
    payload = {
        'text': f"🚨 Phase 13.6 Alert - {country}",
        'blocks': [
            {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f"**Status**: {status}\n**Country**: {country}\n**Message**: {message}"}}
        ]
    }
    requests.post(webhook_url, json=payload)
```

---

## Troubleshooting

### Collection Failures

**Symptom**: Collection runs but produces no output

**Diagnosis**:
```bash
# Check logs
tail -f /var/log/loan4u/collect_br.log

# Test collector directly
python scripts/phase13_real_data_br.py --records 100

# Check directory permissions
ls -la data/raw/
chmod 755 data/raw/

# Verify API keys set
env | grep SELOGER_API_KEY
```

**Fix**:
```bash
# Ensure output directory exists
mkdir -p data/raw/

# Set permissions
chmod 755 data/raw/

# Restart collection
python scripts/phase13_hybrid_pipeline.py --country BR --use-real-data --fallback
```

### High API Quota Usage

**Symptom**: API quota exceeded in middle of month

**Root Causes**:
- Batch size too large (trying to collect too many records)
- Rate limiting not respected
- Multiple concurrent collection processes

**Solutions**:
```python
# Reduce batch size
BATCH_SIZE = 50  # Reduced from 100

# Add request delay
import time
time.sleep(1)  # 1 second between requests

# Check for duplicate processes
ps aux | grep phase13_hybrid_pipeline
# Kill if multiple running
pkill -f phase13_hybrid_pipeline
```

### Stale Data Issues

**Symptom**: Collections succeed but data seems old

**Solutions**:
```bash
# Check file timestamps
ls -l data/raw/*.csv

# Verify recent timestamps
find data/raw -name "*.csv" -mtime -1  # Files modified in last day

# Check metadata
cat data/raw/BR_hybrid_meta.json | jq '.timestamp'
```

### Storage Quota Issues

**Symptom**: "No space left on device"

**Solutions**:
```bash
# Check disk usage
df -h

# Archive old data
tar -czf archive_2026_06.tar.gz data/raw/*_2026_06*.csv
rm data/raw/*_2026_06*.csv

# Cleanup
du -sh data/raw/
# Keep only last 30 days of data
find data/raw -name "*.csv" -mtime +30 -delete
```

---

## Maintenance Tasks

### Weekly Tasks

1. **Review Collection Logs**
   ```bash
   # Check for errors
   grep "ERROR" /var/log/loan4u/collect_*.log
   grep "WARNING" /var/log/loan4u/collect_*.log
   
   # Check collection counts
   grep "✅ Final dataset" /var/log/loan4u/collect_*.log
   ```

2. **Verify Data Quality**
   ```python
   import pandas as pd
   for country in ['BR', 'CA', 'SG', 'DE', 'TH', 'AU', 'HK', 'UK']:
       df = pd.read_csv(f'data/raw/{country}_real.csv')
       print(f"{country}: {len(df)} records, {df.isnull().sum().max()} nulls")
   ```

3. **Check API Health**
   ```bash
   # Ping each API endpoint
   curl -I https://api.seloger.com.br/search
   curl -I https://api.realtor.ca
   curl -I https://data.gov.sg/api/action
   # etc
   ```

### Monthly Tasks

1. **Model Retraining**
   - Run retrain script (see scheduled section above)
   - Validate MAPE < threshold
   - If passed, deploy new models

2. **Capacity Planning**
   ```bash
   # Forecast storage needs
   du -sh data/raw/  # Current usage
   # If 210K records/month at ~50KB each = ~10GB/month
   # Plan for 365 days = ~120GB needed
   ```

3. **API Quota Review**
   ```bash
   # Check actual vs. planned usage for cost optimization
   # Seloger: 30,000 used / 500,000 available
   # Realtor.ca: unlimited (no charges)
   # etc
   ```

### Quarterly Tasks

1. **Security Audit**
   - Rotate API keys
   - Audit access logs
   - Verify .gitignore includes credentials

2. **Performance Optimization**
   - Review collection times and optimize if > 30min total
   - Check for unused enrichment steps (remove if not improving model)

3. **Documentation Update**
   - Update API endpoint URLs if changed
   - Document any custom modifications
   - Update this guide with lessons learned

---

## Incident Response

### Severity Levels

| Level | Impact | Response Time |
|-------|--------|----------------|
| 🔴 Critical | No new data (>24h gap) | 15 minutes |
| 🟠 High | Partial data (2+ countries failed) | 1 hour |
| 🟡 Medium | Single country failed | 4 hours |
| 🟢 Low | Non-critical warnings in logs | 24 hours |

### Example Incident Response

**Incident**: Collection fails for all countries

**Steps**:
1. **Immediate Action** (within 15 min)
   - Check if all APIs are down: `curl -I https://api.seloger.com.br`
   - If yes, confirm on provider status pages
   - If no, check local network/firewall

2. **Diagnosis** (within 30 min)
   - Run test collection: `python scripts/phase13_hybrid_pipeline.py --country BR`
   - Check logs: `tail -100 /var/log/loan4u/collect_br.log`
   - Verify API keys not expired

3. **Fallback** (within 1 hour)
   - Ensure simulation mode available
   - Re-run with fallback flag: `--use-real-data --fallback`
   - Verify fallback collections succeeded

4. **Communication** (immediately)
   - Notify stakeholders: "Using simulated data, real APIs temporarily unavailable"
   - Provide ETA for recovery

5. **Root Cause Analysis** (within 24 hours)
   - Document what happened
   - Plan remediation (API upgrade, fallback improvement, etc.)
   - Update incident log

---

## Disaster Recovery

### Data Loss Recovery

```bash
# Backup strategy
# Daily backup to cold storage
gsutil -m cp -r gs://loan4u-backups/data/raw/* \
  gs://loan4u-cold-storage/daily/$(date +%Y%m%d)/

# Weekly full backup
tar -czf /backup/loan4u_full_$(date +%Y%m%d).tar.gz \
  data/raw/ config/ output/

# Retention: Keep 90 days of daily backups, 1 year of weekly
```

### Restore Procedure

```bash
# Restore latest collection
gsutil -m cp -r \
  gs://loan4u-backups/data/raw/BR_real.csv \
  data/raw/BR_real.csv

# Restore from full backup if needed
tar -xzf /backup/loan4u_full_20260720.tar.gz
```

---

## Capacity & Scaling

### Current Scale (MVP)

- **Total Records**: 210,000 per collection cycle
- **Collection Time**: 30-45 minutes (all 8 countries parallel)
- **Storage**: ~10GB per month
- **API Quota**: Moderate usage (<80% of most providers)

### Scaling to 10x

To scale to 2.1M records/cycle:

1. **Parallel Collection**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   countries = ['BR', 'CA', 'SG', 'DE', 'TH', 'AU', 'HK', 'UK']
   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [
           executor.submit(collect_country, c) 
           for c in countries
       ]
       results = [f.result() for f in futures]
   # Total time: ~10 minutes (vs. 45 min sequential)
   ```

2. **Streaming to Database**
   ```python
   # Instead of CSV, stream directly to BigQuery
   from google.cloud import bigquery
   
   client = bigquery.Client()
   job = client.load_table_from_dataframe(
       df, 'loan4u.properties_raw', job_config=config
   )
   ```

3. **Distributed Collection**
   - Deploy collectors to separate servers/containers
   - Coordinate via message queue (Kafka, Pub/Sub)
   - Aggregate results in data warehouse

---

## Production Checklist

Before going live:

- [ ] All 8 country collectors tested with real data
- [ ] Fallback to simulation verified for each country
- [ ] API credentials securely stored (secrets manager)
- [ ] Logging configured and tested
- [ ] Monitoring dashboards set up (Prometheus/Grafana)
- [ ] Alerting configured (email, Slack)
- [ ] Backup/restore procedures documented and tested
- [ ] Runbooks written for common issues
- [ ] On-call rotation established
- [ ] Incident response procedures practiced

---

**End of Deployment & Operations Guide**

For implementation questions, see: `PHASE_13_6_IMPLEMENTATION_GUIDE.md`  
For API setup, see: `REAL_DATA_API_INTEGRATION_GUIDE.md`  
For extending to new countries, see: `ADDING_NEW_COUNTRY_GUIDE.md`
