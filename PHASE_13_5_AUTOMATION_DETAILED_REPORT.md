# Phase 13.5 상세 보고서
## 자동화 루프 & 지속적 개선

**작성일**: 2026-07-01  
**버전**: 1.0  
**상태**: 📋 설계 중  
**우선순위**: 🟡 P2 (병렬 진행 가능)

---

## Executive Summary

**목표**: Phase 13.4 배포 완료 후, 주간 자동 데이터 수집 → 모델 재학습 → 성능 모니터링 → 알림 시스템 구축 → 지속적 개선 루프 운영화  
**기간**: 2026-07-24 ~ 2026-08-06 (14일, Week 4-5, 병렬 진행 가능)  
**팀 규모**: 1명 (Claude Agent) + 스케줄러 (자동)  
**성공 기준**: 주간 자동화 성공률 >95%, 모니터링 알림 <5분 지연, 재학습 성능 유지 (R² >0.84)  

**핵심 성과**:
- ✅ Cron 기반 주간 자동 데이터 수집 (목요일 10:00)
- ✅ 월간 자동 모델 재학습 (성능 >0.84 유지)
- ✅ 실시간 성능 모니터링 (Prometheus/Grafana)
- ✅ 알림 시스템 (Slack, Email, SMS)
- ✅ A/B 테스팅 인프라 (새 모델 배포 전 검증)
- ✅ 롤백 및 contingency 계획

---

## 1. 자동화 아키텍처

### 1.1 전체 파이프라인

```
┌─────────────────────────────────────────────────┐
│           Cron Scheduler (Linux)                 │
│  0 10 * * 4  (매주 목요일 10:00 AM)             │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼───────┐
         │ Data Collection│ (30 min)
         │ Phase 13.1 재실행
         │ ├─ data.go.kr
         │ ├─ MOLIT
         │ └─ 10K+ 거래정보
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │ Data Validation│ (10 min)
         │ ├─ Null rate
         │ ├─ Outlier detection
         │ └─ Schema validation
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │ Feature Eng.   │ (5 min)
         │ 45 features
         │ StandardScaler
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │ Model Training │ (20 min)
         │ ├─ XGBoost (GPU)
         │ ├─ LightGBM (GPU) ⭐
         │ └─ GB (CPU)
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │ Performance    │ (10 min)
         │ Evaluation     │
         │ ├─ R², MAPE
         │ ├─ 5-fold CV
         │ └─ Decision
         └───────┬───────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     ▼                       ▼
┌────────────────┐   ┌──────────────┐
│ R²>0.84?       │   │ R²≤0.84?     │
│ Deploy         │   │ Hold old     │
│ new model      │   │ model        │
│ (5 min)        │   │ Notify team  │
└────┬───────────┘   └──────────────┘
     │
     ▼
┌──────────────────────────┐
│ Monitoring & Alerting     │
│ ├─ Prometheus metrics     │
│ ├─ Grafana dashboard      │
│ ├─ Slack/Email/SMS alerts │
│ └─ Continuous tracking    │
└──────────────────────────┘

Total Time: ~90 minutes (weekly)
Success Rate: >95%
Manual Intervention: <5% (auto-review)
```

### 1.2 재학습 의사결정 트리

```
월간 모델 재학습 완료
        │
        ▼
     정확도 평가
        │
    ┌───┴───┐
    │       │
R²>0.84  R²≤0.84
    │       │
    ▼       ▼
 배포     보류
    │       │
    │    특성 재엔지니어링
    │    또는 튜닝 재시작
    │       │
    │       ▼
    │    재실행 (반복)
    │
    ▼
Version control
├─ model_v1.0 (baseline, 2026-07-18)
├─ model_v1.1 (2026-08-01)
├─ model_v1.2 (2026-08-15)
└─ ...current (active)
```

---

## 2. 자동화 구성 요소

### 2.1 Cron 작업 정의

```bash
# Linux crontab entry
# /etc/cron.d/avm-weekly-retraining

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=admin@loan4u.com

# Weekly model retraining (Every Thursday 10:00 AM)
0 10 * * 4 root /opt/avm/scripts/run_weekly_retraining.sh >> /var/log/avm/weekly_retraining.log 2>&1

# Daily monitoring health check (Every day 09:00 AM)
0 9 * * * root /opt/avm/scripts/health_check.sh >> /var/log/avm/health_check.log 2>&1

# Monthly full pipeline test (First Friday of month 11:00 PM)
0 23 1-7 * 5 root /opt/avm/scripts/full_pipeline_test.sh >> /var/log/avm/pipeline_test.log 2>&1
```

### 2.2 자동화 스크립트 (run_weekly_retraining.sh)

```bash
#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="/opt/avm"
LOG_DIR="/var/log/avm"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="$LOG_DIR/retraining_${TIMESTAMP}.log"

# Start logging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "[$(date)] ========== START Weekly Retraining =========="

# Step 1: Data Collection (30 min expected)
echo "[$(date)] Step 1: Data Collection..."
cd $PROJECT_ROOT
python scripts/phase13_data_collector.py \
    --output data/raw \
    --report output/collection_${TIMESTAMP}.json
if [ $? -ne 0 ]; then
    echo "[ERROR] Data collection failed"
    # Send alert
    curl -X POST https://hooks.slack.com/services/... \
        -d '{"text":"🚨 AVM Weekly Retraining FAILED at Data Collection"}'
    exit 1
fi

# Step 2: Data Validation (10 min)
echo "[$(date)] Step 2: Data Validation..."
python scripts/validate_collected_data.py \
    --input data/raw \
    --output output/validation_${TIMESTAMP}.json

# Step 3: Feature Engineering (5 min)
echo "[$(date)] Step 3: Feature Engineering..."
python scripts/feature_engineering.py \
    --input data/raw \
    --output data/processed/features_${TIMESTAMP}.pkl

# Step 4: Model Training (20 min)
echo "[$(date)] Step 4: Model Training..."
python scripts/phase13_model_trainer.py \
    --data data/processed/features_${TIMESTAMP}.pkl \
    --output models/model_trained_${TIMESTAMP}.pkl \
    --report output/training_${TIMESTAMP}.json

# Step 5: Performance Evaluation (10 min)
echo "[$(date)] Step 5: Performance Evaluation..."
python scripts/evaluate_model.py \
    --model models/model_trained_${TIMESTAMP}.pkl \
    --test_data data/processed/X_test.pkl \
    --output output/evaluation_${TIMESTAMP}.json

# Parse evaluation results
R2_SCORE=$(grep '"r2":' output/evaluation_${TIMESTAMP}.json | sed 's/.*"r2":\s*\([0-9.]*\).*/\1/')
MAPE=$(grep '"mape":' output/evaluation_${TIMESTAMP}.json | sed 's/.*"mape":\s*\([0-9.]*\).*/\1/')

echo "[$(date)] R² Score: $R2_SCORE, MAPE: $MAPE"

# Step 6: Decision Logic
if (( $(echo "$R2_SCORE > 0.84" | bc -l) )); then
    echo "[$(date)] ✓ Performance acceptable (R² > 0.84)"
    
    # Step 7: Deploy new model
    echo "[$(date)] Step 6: Deploying new model..."
    cp models/model_trained_${TIMESTAMP}.pkl models/best_model_kr.pkl
    
    # Convert to ONNX + OpenVINO IR
    python scripts/convert_model_to_onnx.py \
        --input models/best_model_kr.pkl \
        --output models/best_model_kr.onnx
    
    python scripts/convert_onnx_to_ir.py \
        --input models/best_model_kr.onnx \
        --output models/openvino_ir
    
    # Restart API service (zero-downtime deployment)
    docker-compose -f docker-compose.yml up -d --no-deps --build npu-api
    sleep 10  # Wait for service restart
    
    # Health check
    HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$HEALTH_CHECK" == "200" ]; then
        echo "[$(date)] ✓ API service restarted successfully"
        # Notify success
        curl -X POST https://hooks.slack.com/services/... \
            -d "{\"text\":\"✅ AVM Weekly Retraining SUCCESSFUL\n- R² Score: $R2_SCORE\n- MAPE: $MAPE\n- Model deployed\"}"
    else
        echo "[ERROR] API service health check failed"
        docker-compose -f docker-compose.yml restart npu-api
    fi
else
    echo "[$(date)] ⚠ Performance below threshold (R² ≤ 0.84)"
    echo "[$(date)] Keeping previous model active"
    
    # Notify warning
    curl -X POST https://hooks.slack.com/services/... \
        -d "{\"text\":\"⚠️ AVM Weekly Retraining: Model performance below target\n- R² Score: $R2_SCORE (target >0.84)\n- Manual review required\"}"
fi

echo "[$(date)] ========== END Weekly Retraining =========="
```

---

## 3. 모니터링 & 알림 시스템

### 3.1 Prometheus 메트릭

```python
# Custom metrics for model monitoring
model_retraining_duration = Gauge(
    'avm_model_retraining_duration_seconds',
    'Time spent retraining model (seconds)'
)

model_r2_score = Gauge(
    'avm_model_r2_score',
    'Model R² score',
    ['model_version']
)

model_mape = Gauge(
    'avm_model_mape',
    'Model MAPE',
    ['model_version']
)

data_collection_records = Gauge(
    'avm_data_collection_records',
    'Number of records collected',
    ['source']  # data.go.kr, MOLIT
)

api_inference_latency = Histogram(
    'avm_api_inference_latency_ms',
    'API inference latency (ms)',
    ['device']  # NPU, GPU, CPU
)

model_deployment_count = Counter(
    'avm_model_deployments_total',
    'Total model deployments',
    ['status']  # success, failure
)
```

### 3.2 알림 규칙 (AlertManager)

```yaml
# /etc/alertmanager/avm_rules.yml

groups:
  - name: avm_alerts
    rules:
      # Model performance alert
      - alert: ModelPerformanceDegraded
        expr: avm_model_r2_score < 0.84
        for: 1h
        annotations:
          summary: "Model R² below 0.84"
          description: "Current R²: {{ $value }}"
          severity: critical
      
      # API latency alert
      - alert: APILatencyHigh
        expr: avm_api_inference_latency_ms > 20
        for: 5m
        annotations:
          summary: "API latency exceeds 20ms"
          description: "p99 latency: {{ $value }}ms"
          severity: warning
      
      # Data collection failure
      - alert: DataCollectionFailed
        expr: increase(avm_data_collection_errors_total[1h]) > 0
        annotations:
          summary: "Weekly data collection failed"
          severity: critical
      
      # Service availability
      - alert: APIServiceDown
        expr: up{job="avm_api"} == 0
        for: 1m
        annotations:
          summary: "AVM API service is down"
          severity: critical
```

### 3.3 알림 채널 (Slack, Email, SMS)

```python
class NotificationService:
    """Multi-channel notification service"""
    
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK')
        self.email_service = EmailService()
        self.sms_service = SMSService()
    
    def notify_retraining_complete(self, result: Dict):
        """Notify all channels on retraining completion"""
        
        message = f"""
        🔄 Weekly Model Retraining Complete
        
        📊 Performance:
        - R² Score: {result['r2']:.4f}
        - MAPE: {result['mape']:.2%}
        
        {'✅ Model Deployed' if result['deployed'] else '⚠ Model Held for Review'}
        
        Timestamp: {datetime.now().isoformat()}
        """
        
        # Slack
        if result['r2'] < 0.84:
            self.slack_webhook.post(
                text=message,
                channel='#avm-alerts',
                icon_emoji=':warning:'
            )
        
        # Email (on critical alerts only)
        if result['r2'] < 0.83:
            self.email_service.send(
                to=['team@loan4u.com'],
                subject='🚨 AVM Model Performance Alert',
                body=message
            )
        
        # SMS (emergency only)
        if not result['deployed'] and result['r2'] < 0.80:
            self.sms_service.send(
                to=['010-1234-5678'],  # On-call engineer
                message=f"🚨 CRITICAL: Model R²={result['r2']:.3f} below threshold"
            )
```

---

## 4. A/B 테스팅 인프라

### 4.1 새 모델 배포 전 검증

```
Old Model (v1.0)          New Model (v1.1)
├─ 95% traffic            ├─ 5% traffic (canary)
├─ Baseline metrics       ├─ Compare metrics
└─ Production SLA         └─ Statistical test

If (p-value < 0.05 AND new_r2 > old_r2):
    → Gradual rollout (5% → 25% → 50% → 100%)
Else:
    → Rollback to old model
    → Investigate issues
    → Schedule retrain
```

### 4.2 구현

```python
class ABTestingManager:
    """A/B testing for new model deployments"""
    
    def __init__(self, old_model, new_model):
        self.old_model = old_model
        self.new_model = new_model
        self.traffic_split = {'old': 0.95, 'new': 0.05}
    
    def route_prediction(self, request):
        """Route request to old or new model"""
        rand = random.random()
        if rand < self.traffic_split['new']:
            return self.new_model.predict(request)
        else:
            return self.old_model.predict(request)
    
    def statistical_test(self, predictions_old, predictions_new):
        """Paired t-test for model comparison"""
        from scipy import stats
        
        t_stat, p_value = stats.ttest_rel(predictions_old, predictions_new)
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    def gradual_rollout(self, new_model_approved: bool):
        """Gradually increase traffic to new model"""
        if new_model_approved:
            stages = [
                {'new': 0.05, 'duration': 1},  # 5% for 1h
                {'new': 0.25, 'duration': 2},  # 25% for 2h
                {'new': 0.50, 'duration': 2},  # 50% for 2h
                {'new': 1.00, 'duration': 0},  # 100% (final)
            ]
            
            for stage in stages:
                self.traffic_split['new'] = stage['new']
                self.traffic_split['old'] = 1.0 - stage['new']
                time.sleep(stage['duration'] * 3600)
                
                # Monitor metrics at each stage
                metrics = self.collect_metrics()
                if metrics['error_rate'] > 0.02:  # >2% error
                    self.rollback()
                    return False
            
            return True  # Deployment successful
```

---

## 5. 롤백 및 Contingency

### 5.1 자동 롤백 조건

```
Automatic Rollback Triggers:
├─ API latency p99 > 50ms (vs. baseline 20ms)
├─ Error rate > 2% (vs. baseline <0.1%)
├─ R² drop > 5% (vs. previous model)
├─ Memory usage > 80%
└─ API downtime > 5 minutes

Automatic Actions:
1. Stop new model immediately
2. Route all traffic to old model
3. Alert on-call engineer
4. Log incident details
5. Preserve new model for post-mortem
```

### 5.2 롤백 스크립트

```bash
#!/bin/bash
# Automatic rollback on critical failure

MODEL_VERSION=$(cat models/current_version.txt)
PREVIOUS_VERSION=$(cat models/previous_version.txt)

echo "Rolling back from $MODEL_VERSION to $PREVIOUS_VERSION"

# Stop current model
docker-compose stop npu-api

# Revert model files
cp models/archive/$PREVIOUS_VERSION/best_model_kr.onnx models/best_model_kr.onnx
cp models/archive/$PREVIOUS_VERSION/best_model_kr.xml models/openvino_ir/best_model_kr.xml
cp models/archive/$PREVIOUS_VERSION/best_model_kr.bin models/openvino_ir/best_model_kr.bin

# Restart API with previous model
docker-compose up -d npu-api

# Wait for health check
sleep 10
curl -f http://localhost:8000/health || {
    echo "Health check failed after rollback!"
    echo "Manual intervention required"
    exit 1
}

echo "✓ Rollback successful"

# Alert team
curl -X POST $SLACK_WEBHOOK \
    -d '{"text":"🔄 Automatic rollback completed to version '$PREVIOUS_VERSION'"}'
```

---

## 6. 성능 메트릭 추적

### 6.1 월간 메트릭 대시보드

```
┌─────────────────────────────────────────┐
│      AVM Monthly Performance Report      │
├─────────────────────────────────────────┤
│ Period: 2026-08-01 ~ 2026-08-31         │
│                                         │
│ Model Performance:                      │
│ ├─ R² Score: 0.851 (target: >0.84) ✓   │
│ ├─ MAPE: 0.091 (target: <10.5%) ✓      │
│ ├─ RMSE: 1.9M KRW                       │
│ └─ Training Date: 2026-08-01            │
│                                         │
│ API Performance:                        │
│ ├─ Latency (p50): 6.5ms                │
│ ├─ Latency (p99): 12ms                 │
│ ├─ Throughput: 1,150 req/min           │
│ └─ Availability: 99.95%                 │
│                                         │
│ Data Collection:                        │
│ ├─ Records/week: 10,500                │
│ ├─ Collection Success: 100%             │
│ └─ Data Quality: null<2%, outlier<3%   │
│                                         │
│ System Health:                          │
│ ├─ Retraining Success: 4/4 weeks ✓     │
│ ├─ Deployments: 1 (successful)         │
│ ├─ Rollbacks: 0                        │
│ └─ Alerts: 2 (minor, resolved)         │
│                                         │
│ Recommendations:                        │
│ ├─ Continue weekly retraining           │
│ ├─ Monitor feature drift                │
│ └─ Plan Q3 model enhancement           │
└─────────────────────────────────────────┘
```

---

## 7. 지속적 개선 계획

### 7.1 단계별 개선 로드맵

```
Phase 13.5 (현재): 기본 자동화 루프
├─ 주간 재학습
├─ 기본 모니터링
└─ 수동 승인

Phase 13.6 (Q3 2026): 고급 자동화
├─ 자동 재학습 승인 (성능 기준 충족 시)
├─ 자동 특성 엔지니어링 최적화
├─ 이상 탐지 (anomaly detection)
└─ 자동 알림 및 조치

Phase 13.7 (Q4 2026): ML Ops 완성
├─ MLflow 기반 모델 관리
├─ Kubeflow 기반 배포 자동화
├─ 자동 성능 리포팅
└─ 실시간 모니터링 대시보드
```

### 7.2 특성 드리프트 감지

```python
class FeatureDriftDetector:
    """Detect data drift in production"""
    
    def __init__(self, reference_data):
        self.reference_stats = self._compute_stats(reference_data)
    
    def detect_drift(self, current_data):
        """
        Statistical test for data drift
        (Kolmogorov-Smirnov test)
        """
        from scipy.stats import ks_2samp
        
        drifts = {}
        for feature in self.reference_stats:
            stat, p_value = ks_2samp(
                self.reference_stats[feature],
                current_data[feature]
            )
            
            if p_value < 0.05:  # Significant drift
                drifts[feature] = {
                    'p_value': p_value,
                    'severity': 'high' if p_value < 0.01 else 'medium'
                }
        
        return drifts  # Empty if no drift detected
```

---

## 8. 결론

**Phase 13.5는 모델을 프로덕션 운영 체제로 완성하는 단계**입니다:
- Cron 기반 자동 재학습으로 모델 신선도 유지
- 실시간 모니터링과 알림으로 빠른 대응
- A/B 테스팅으로 안전한 배포
- 자동 롤백으로 위험 최소화
- 지속적 개선으로 성능 향상

**Success Scenario**:
```
2026-08-06 완료 상태 (Week 4-5 병렬 진행):
├── Cron 자동화 설정 완료 (주간 재학습) ✅
├── 첫 주간 재학습 성공 (R² 0.851 유지) ✅
├── Prometheus/Grafana 모니터링 운영 ✅
├── Slack/Email/SMS 알림 시스템 운영 ✅
├── A/B 테스팅 인프라 구축 (자동 배포 테스트) ✅
├── 자동 롤백 메커니즘 검증 ✅
└── Phase 13 전체 완료 → 운영 체제 전환
```

---

**작성자**: Claude Sonnet 5  
**최종 검토**: TBD (사용자 승인 대기)  
**다음 단계**: Phase 13.5 기술 명세서 & WBS 작성
