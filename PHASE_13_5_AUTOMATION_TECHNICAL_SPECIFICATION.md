# Phase 13.5 기술 명세서
## 자동화 루프 & 지속적 개선

**작성일**: 2026-07-01  
**버전**: 1.0  
**상태**: 📋 설계 중  
**기술 스택**: Cron, Bash, Python, Prometheus, Grafana, Slack API

---

## 1. Cron 스케줄링 명세

### 1.1 Cron 작업 설정

```bash
# File: /etc/cron.d/avm-automation

# Format: minute hour day_of_month month day_of_week user command

# Weekly Model Retraining (Every Thursday 10:00 AM)
0 10 * * 4 root cd /opt/avm && bash scripts/run_weekly_retraining.sh

# Daily Health Check (Every day 9:00 AM)
0 9 * * * root cd /opt/avm && bash scripts/daily_health_check.sh

# Monthly Pipeline Test (First Friday 11:00 PM)
0 23 1-7 * 5 root cd /opt/avm && bash scripts/monthly_pipeline_test.sh

# Weekly Report Generation (Every Sunday 8:00 AM)
0 8 * * 0 root cd /opt/avm && python scripts/generate_weekly_report.py

# Hourly Monitoring (Every hour at :30 minutes)
30 * * * * root cd /opt/avm && python scripts/check_model_drift.py
```

### 1.2 작업별 상세 명세

```python
# Weekly Retraining Job (run_weekly_retraining.sh 상세)

def weekly_retraining_workflow():
    """Complete workflow for weekly model retraining"""
    
    steps = {
        'data_collection': {
            'timeout': 1800,  # 30 min
            'description': 'Collect 10K+ new property transactions',
            'rollback_on_failure': True,
            'notification': True
        },
        'data_validation': {
            'timeout': 600,   # 10 min
            'description': 'Validate data quality (null<2%, outlier<3%)',
            'rollback_on_failure': True,
            'notification': False
        },
        'feature_engineering': {
            'timeout': 300,   # 5 min
            'description': '10 base → 45 features, StandardScaler',
            'rollback_on_failure': True,
            'notification': False
        },
        'model_training': {
            'timeout': 1200,  # 20 min
            'description': 'GPU training: XGBoost, LightGBM, GB',
            'rollback_on_failure': True,
            'notification': False
        },
        'model_evaluation': {
            'timeout': 600,   # 10 min
            'description': '5-fold CV, R² >0.84 check',
            'rollback_on_failure': False,  # Continue with decision
            'notification': True
        },
        'deployment_decision': {
            'timeout': 300,   # 5 min
            'description': 'Decide: deploy if R²>0.84, else hold',
            'rollback_on_failure': False,
            'notification': True
        },
        'model_deployment': {
            'timeout': 300,   # 5 min (if deploy decision=True)
            'description': 'ONNX conversion, OpenVINO IR, API restart',
            'rollback_on_failure': True,
            'notification': True
        }
    }
    
    # Total expected time: ~90 minutes
    # SLA: Complete within 120 minutes (2 hour window 10:00-12:00)
```

---

## 2. 자동화 스크립트 명세

### 2.1 Python 주요 스크립트

```python
# scripts/phase13_automation_engine.py

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import logging
import subprocess
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    ROLLED_BACK = 'rolled_back'

@dataclass
class AutomationJob:
    job_id: str
    name: str
    schedule: str  # Cron format
    script_path: str
    timeout_seconds: int
    max_retries: int = 2
    notifications: List[str] = None  # slack, email, sms
    status: JobStatus = JobStatus.PENDING
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class AutomationEngine:
    """Orchestrate automation workflows"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.jobs: Dict[str, AutomationJob] = {}
        self._initialize_jobs()
    
    def execute_job(self, job: AutomationJob) -> Dict:
        """Execute single automation job with error handling"""
        
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now()
        
        try:
            # Execute with timeout
            result = subprocess.run(
                [f'bash {job.script_path}'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=job.timeout_seconds
            )
            
            if result.returncode == 0:
                job.status = JobStatus.SUCCESS
                self._notify(job, 'success', result.stdout)
                return {'status': 'success', 'output': result.stdout}
            else:
                job.status = JobStatus.FAILED
                self._notify(job, 'failure', result.stderr)
                
                # Retry logic
                if job.max_retries > 0:
                    job.max_retries -= 1
                    logger.warning(f"Retrying job {job.name} ({job.max_retries} attempts left)")
                    return self.execute_job(job)
                else:
                    return {'status': 'failed', 'error': result.stderr}
        
        except subprocess.TimeoutExpired:
            job.status = JobStatus.FAILED
            self._notify(job, 'timeout', f"Job exceeded {job.timeout_seconds}s limit")
            return {'status': 'timeout', 'error': 'Execution timeout'}
        
        except Exception as e:
            job.status = JobStatus.FAILED
            self._notify(job, 'error', str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _notify(self, job: AutomationJob, status: str, message: str):
        """Send notifications via configured channels"""
        for channel in (job.notifications or []):
            if channel == 'slack':
                self._send_slack(job, status, message)
            elif channel == 'email':
                self._send_email(job, status, message)
            elif channel == 'sms':
                self._send_sms(job, status, message)
```

### 2.2 주요 Bash 스크립트 구조

```bash
#!/bin/bash
# scripts/run_weekly_retraining.sh

set -euo pipefail

# Configuration
PROJECT_ROOT="/opt/avm"
SCRIPT_DIR="$PROJECT_ROOT/scripts"
DATA_DIR="$PROJECT_ROOT/data"
LOG_DIR="/var/log/avm"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="$LOG_DIR/retraining_${TIMESTAMP}.log"

# Logging setup
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Error handling
trap 'on_error' ERR
on_error() {
    log_error "Script failed at line $LINENO"
    notify_failure "Retraining failed at line $LINENO"
    exit 1
}

# Notification functions
notify_success() {
    python3 << EOF
import requests
import json
webhook = '${SLACK_WEBHOOK_URL}'
payload = {
    'text': '✅ Weekly Retraining Successful',
    'attachments': [{
        'color': 'good',
        'text': '$1'
    }]
}
requests.post(webhook, json=payload)
EOF
}

notify_failure() {
    python3 << EOF
import requests
webhook = '${SLACK_WEBHOOK_URL}'
payload = {
    'text': '🚨 Weekly Retraining Failed',
    'attachments': [{
        'color': 'danger',
        'text': '$1'
    }]
}
requests.post(webhook, json=payload)
EOF
}

# Main workflow
main() {
    log_info "========== START Weekly Retraining =========="
    
    # Step 1: Data Collection
    log_info "Step 1: Data Collection (target: 30 min)"
    python3 "$SCRIPT_DIR/phase13_data_collector.py" \
        --output "$DATA_DIR/raw" \
        --report "output/collection_${TIMESTAMP}.json" || {
        log_error "Data collection failed"
        notify_failure "Data collection failed"
        exit 1
    }
    log_info "✓ Data collected"
    
    # Step 2: Data Validation
    log_info "Step 2: Data Validation (target: 10 min)"
    python3 "$SCRIPT_DIR/validate_data.py" \
        --input "$DATA_DIR/raw" || {
        log_error "Data validation failed"
        notify_failure "Data validation failed"
        exit 1
    }
    log_info "✓ Data validated"
    
    # Step 3: Feature Engineering
    log_info "Step 3: Feature Engineering (target: 5 min)"
    python3 "$SCRIPT_DIR/feature_engineering.py" \
        --input "$DATA_DIR/raw" \
        --output "$DATA_DIR/processed" || {
        log_error "Feature engineering failed"
        notify_failure "Feature engineering failed"
        exit 1
    }
    log_info "✓ Features engineered"
    
    # Step 4: Model Training
    log_info "Step 4: Model Training (target: 20 min)"
    TRAINING_OUTPUT=$(python3 "$SCRIPT_DIR/phase13_model_trainer.py" \
        --data "$DATA_DIR/processed" \
        --output "models/model_trained_${TIMESTAMP}.pkl" \
        --report "output/training_${TIMESTAMP}.json")
    log_info "✓ Model trained"
    
    # Step 5: Performance Evaluation
    log_info "Step 5: Performance Evaluation (target: 10 min)"
    EVAL_OUTPUT=$(python3 "$SCRIPT_DIR/evaluate_model.py" \
        --model "models/model_trained_${TIMESTAMP}.pkl" \
        --report "output/evaluation_${TIMESTAMP}.json")
    
    # Parse R² score
    R2_SCORE=$(python3 -c "
import json
with open('output/evaluation_${TIMESTAMP}.json') as f:
    data = json.load(f)
print(data['r2_score'])
")
    
    log_info "✓ Model R² Score: $R2_SCORE"
    
    # Step 6: Deployment Decision
    if (( $(python3 -c "print(1 if $R2_SCORE > 0.84 else 0)") )); then
        log_info "✓ Performance acceptable (R² > 0.84)"
        
        # Deploy
        log_info "Step 6: Deploying new model"
        cp "models/model_trained_${TIMESTAMP}.pkl" "models/best_model_kr.pkl"
        
        # Convert to ONNX + OpenVINO
        python3 "$SCRIPT_DIR/convert_model_to_onnx.py" \
            --input "models/best_model_kr.pkl" \
            --output "models/best_model_kr.onnx"
        
        python3 "$SCRIPT_DIR/convert_onnx_to_ir.py" \
            --input "models/best_model_kr.onnx" \
            --output "models/openvino_ir"
        
        # Restart API
        docker-compose -f docker-compose.yml up -d --no-deps npu-api
        sleep 10
        
        # Health check
        curl -f http://localhost:8000/health || {
            log_error "API health check failed"
            docker-compose restart npu-api
            notify_failure "API restart failed"
            exit 1
        }
        
        log_info "✓ Model deployed successfully"
        notify_success "R² Score: $R2_SCORE\nModel deployed successfully"
    else
        log_warning "Performance below threshold (R² ≤ 0.84)"
        notify_failure "R² Score: $R2_SCORE (target >0.84)\nModel held for review"
    fi
    
    log_info "========== END Weekly Retraining =========="
    log_info "Total duration: $(( $(date +%s) - $(date -d "$TIMESTAMP" +%s) )) seconds"
}

# Execute main
main
```

---

## 3. 모니터링 메트릭 명세

### 3.1 Prometheus 메트릭 정의

```python
# metrics/avm_metrics.py

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

registry = CollectorRegistry()

# Job execution metrics
job_execution_time = Histogram(
    'avm_job_execution_seconds',
    'Job execution time in seconds',
    ['job_name'],
    registry=registry,
    buckets=[60, 300, 600, 900, 1200, 1800, 3600]
)

job_status = Gauge(
    'avm_job_status',
    'Job status (0=pending, 1=running, 2=success, 3=failed)',
    ['job_name'],
    registry=registry
)

# Model metrics
model_r2_score = Gauge(
    'avm_model_r2_score',
    'Current model R² score',
    ['model_version', 'device'],
    registry=registry
)

model_mape = Gauge(
    'avm_model_mape',
    'Current model MAPE',
    ['model_version'],
    registry=registry
)

# Data collection metrics
data_records_collected = Counter(
    'avm_data_records_collected_total',
    'Total records collected',
    ['source'],  # data.go.kr, MOLIT
    registry=registry
)

data_null_rate = Gauge(
    'avm_data_null_rate',
    'Null value rate in collected data',
    registry=registry
)

# API metrics
api_request_latency = Histogram(
    'avm_api_request_latency_ms',
    'API request latency in milliseconds',
    ['device'],  # NPU, GPU, CPU
    registry=registry,
    buckets=[1, 5, 10, 20, 50, 100, 200]
)

api_requests_total = Counter(
    'avm_api_requests_total',
    'Total API requests',
    ['status', 'device'],  # status: 200, 400, 500
    registry=registry
)

# Deployment metrics
model_deployments = Counter(
    'avm_model_deployments_total',
    'Total model deployments',
    ['status', 'version'],  # status: success, failed, rolled_back
    registry=registry
)

model_rollbacks = Counter(
    'avm_model_rollbacks_total',
    'Total automatic rollbacks',
    ['reason'],  # latency, error_rate, r2_drop
    registry=registry
)
```

### 3.2 Grafana 대시보드 정의

```json
{
  "dashboard": {
    "title": "AVM Production Monitoring",
    "panels": [
      {
        "title": "Model R² Score Trend",
        "targets": [
          {
            "expr": "avm_model_r2_score{device='NPU'}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "API Latency Distribution",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(avm_api_request_latency_ms_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Weekly Retraining Status",
        "targets": [
          {
            "expr": "avm_job_status{job_name='weekly_retraining'}"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Data Collection Records",
        "targets": [
          {
            "expr": "increase(avm_data_records_collected_total[1w])"
          }
        ],
        "type": "stat"
      }
    ]
  }
}
```

---

## 4. 알림 규칙 명세

### 4.1 AlertManager 규칙

```yaml
# alerting_rules.yml

groups:
  - name: avm_production
    interval: 30s
    rules:
      # Model performance degradation
      - alert: ModelPerformanceDegraded
        expr: avm_model_r2_score < 0.84
        for: 1h
        severity: critical
        annotations:
          summary: "Model R² below 0.84"
          description: "Current R²: {{ $value }}"
          runbook: "https://wiki.loan4u.com/avm/model-degradation"
      
      # API latency increase
      - alert: APILatencyHigh
        expr: histogram_quantile(0.99, rate(avm_api_request_latency_ms_bucket[5m])) > 20
        for: 5m
        severity: warning
        annotations:
          summary: "API p99 latency >20ms"
      
      # Job failure
      - alert: AutomationJobFailed
        expr: avm_job_status == 3
        for: 1m
        severity: critical
        annotations:
          summary: "Automation job failed: {{ $labels.job_name }}"
      
      # Data collection failure
      - alert: DataCollectionFailed
        expr: increase(avm_data_collection_errors[1h]) > 0
        severity: critical
      
      # API unavailable
      - alert: APIServiceDown
        expr: up{job="avm_api"} == 0
        for: 1m
        severity: critical
```

---

## 5. 배포 패키징

```dockerfile
# Dockerfile for automation container

FROM python:3.11-slim

WORKDIR /opt/avm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-automation.txt

# Setup cron
COPY cron/avm-automation /etc/cron.d/avm-automation
RUN chmod 0644 /etc/cron.d/avm-automation && crontab /etc/cron.d/avm-automation

# Start cron daemon
CMD ["cron", "-f"]
```

---

**기술 명세서 완성**
