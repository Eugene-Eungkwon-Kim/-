# Phase 8-10 상세 개발명세서
## Loan4U QC v1.1 - 자동화, 모니터링, 운영 완성
### 2026-07-21 ~ 2026-09-30

---

## 📋 Executive Summary

**총 3개 Phase, 8-10주, 336시간 투입**

| Phase | 목표 | 기간 | 델타값 | 우선순위 |
|-------|------|------|--------|----------|
| **Phase 8** | 자동화 파이프라인 구축 | 2주 | ⭐⭐⭐⭐⭐ | **1️⃣** |
| **Phase 9** | 모니터링 & 성능개선 | 4주 | ⭐⭐⭐⭐ | 2️⃣ |
| **Phase 10** | 운영 안정화 & 지속개선 | 4주+ | ⭐⭐⭐ | 3️⃣ |

---

## 🟡 Phase 8: 자동화 파이프라인 (2주, 42시간)
### 목표: 수동 작업 50% 제거, 월별 자동 데이터 수집 & 모델 재학습

### Task 8.1: 자동 데이터 수집 스케줄링 (5일)

#### 8.1.1 월별 자동 수집 스크립트 (3일)

**명세**:
```python
# File: scripts/auto_data_collection.py
# 목적: 매월 1일 02:00에 자동 실행
# Input: API key (환경변수), 이전월 데이터
# Output: monthly_{YYYY-MM}.csv (data/raw/)

def auto_collect_monthly_data():
    """월별 자동 데이터 수집"""
    # 1. 이전월 계산
    yesterday = datetime.now() - timedelta(days=1)
    target_month = yesterday.strftime("%Y%m")
    
    # 2. API 호출 (3-tier fallback)
    try:
        data = collect_from_api(target_month)
    except Exception:
        data = load_from_cache()
    
    # 3. 데이터 검증
    assert len(data) > 0, "No data collected"
    assert data.isna().sum().sum() == 0, "Missing values"
    
    # 4. 파일 저장
    path = f"data/raw/monthly_{target_month}.csv"
    data.to_csv(path, index=False)
    
    # 5. 로깅
    return {
        "status": "ok",
        "month": target_month,
        "rows": len(data),
        "timestamp": datetime.now().isoformat()
    }
```

**성공 기준**:
- ✅ 월 30일 이상 데이터 수집
- ✅ 데이터 무결성 100%
- ✅ 수집 시간 < 5분
- ✅ 에러 발생 시 자동 폴백

**테스트**:
```bash
# 수동 테스트 (실제 실행 전)
python scripts/test_auto_collection.py

# Cron 검증
crontab -l | grep auto_data_collection
```

#### 8.1.2 Cron 스케줄 설정 (2일)

**설정**:
```bash
# /etc/crontab 또는 crontab -e
# 매월 1일 02:00 UTC에 실행
0 2 1 * * /usr/bin/python3 /home/user/-/avm_project/scripts/auto_data_collection.py >> /var/log/loan4u_collection.log 2>&1

# 실패 시 이메일 알림
0 3 1 * * /home/user/-/avm_project/scripts/check_collection_status.py
```

**모니터링**:
- 실행 로그: `/var/log/loan4u_collection.log`
- 실패 알림: support@loan4u.com
- 재시도: 자동 3회

#### 8.1.3 에러 처리 & 로깅 (1일)

**에러 유형별 대응**:
| 에러 | 원인 | 대응 |
|-----|------|------|
| API 403 | 네트워크/인증 | 캐시 데이터 사용 |
| 타임아웃 | API 느림 | 30초 후 재시도 |
| 데이터 부족 | API 오류 | 지난달 데이터 사용 |
| CSV 쓰기 실패 | 디스크 부족 | 경고 + 백업 사용 |

**로깅 형식**:
```json
{
  "timestamp": "2026-08-01T02:15:30",
  "event": "data_collection",
  "status": "success",
  "month": "202608",
  "rows": 15000,
  "duration_seconds": 45,
  "api_calls": 1,
  "cache_fallback": false
}
```

---

### Task 8.2: 자동 모델 재학습 (5일)

#### 8.2.1 월별 재학습 파이프라인 (3일)

**명세**:
```python
# File: scripts/auto_model_retraining.py
# 목적: 매월 5일 03:00에 자동 실행
# Input: monthly data + previous 11 months
# Output: new model, R² score

class AutoRetrainer:
    def retrain_monthly(self):
        """월별 모델 재학습"""
        # 1. 최근 12개월 데이터 로드
        data = self.load_recent_12_months()
        
        # 2. 전처리
        X, y = self.preprocess_data(data)
        
        # 3. 학습
        model = self.train_gradient_boosting(X, y)
        
        # 4. 검증
        r2 = model.score(X, y)
        if r2 < 0.85:
            print(f"⚠️ R² 낮음: {r2:.3f}")
            return {"status": "warning", "r2": r2}
        
        # 5. 버전 관리
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"models/gradient_boosting_{timestamp}.joblib"
        joblib.dump(model, model_path)
        
        # 6. 심볼릭 링크 업데이트
        os.symlink(model_path, "models/gradient_boosting_latest.joblib")
        
        return {
            "status": "ok",
            "r2": r2,
            "model_path": model_path,
            "timestamp": datetime.now().isoformat()
        }
```

**성공 기준**:
- ✅ R² ≥ 0.85 유지
- ✅ 재학습 시간 < 10분
- ✅ 모델 버전 자동 관리
- ✅ 이전 모델 자동 백업

#### 8.2.2 모델 검증 & 롤백 (2일)

**검증 프로세스**:
```
1. R² 점수 검증 (≥ 0.85)
   ↓
2. 성능 테스트 (샘플 데이터)
   ↓
3. A/B 테스트 비교 (구 vs 신 모델)
   ↓
4. 통계 유의성 검사 (p-value < 0.05)
   ↓
5. 프로덕션 배포 또는 롤백
```

**롤백 자동화**:
```python
def rollback_to_previous_model():
    """이전 모델로 복원"""
    current = Path("models/gradient_boosting_latest.joblib").resolve()
    previous = sorted(Path("models").glob("gradient_boosting_*.joblib"))[-2]
    
    os.symlink(previous, "models/gradient_boosting_latest.joblib")
    return f"Rolled back to {previous.name}"
```

---

### Task 8.3: 자동화 모니터링 & 알림 (4일)

#### 8.3.1 자동화 상태 대시보드 (2일)

**메트릭**:
```json
{
  "last_collection": "2026-08-01T02:15:30",
  "collection_status": "success",
  "collection_rows": 15000,
  "last_retrain": "2026-08-05T03:20:15",
  "retrain_status": "success",
  "latest_r2": 0.8754,
  "model_version": "gradient_boosting_20260805_032015.joblib",
  "failures_this_month": 0,
  "uptime": "100%"
}
```

**API 엔드포인트**:
```python
@app.get("/automation/status")
async def get_automation_status():
    """자동화 상태 조회"""
    return {
        "collection": get_collection_status(),
        "retrain": get_retrain_status(),
        "health": "good" if all_ok() else "warning"
    }
```

#### 8.3.2 실패 알림 시스템 (2일)

**알림 채널**:
- 📧 이메일: support@loan4u.com
- 💬 Slack: #loan4u-alerts
- 📊 대시보드: /automation/status

**알림 트리거**:
```python
def send_alert(event, severity):
    """자동화 실패 알림"""
    if event == "collection_failed":
        send_email("Data collection failed", severity)
        send_slack("⚠️ 데이터 수집 실패", "#loan4u-alerts")
    elif event == "retrain_warning":
        send_email("Model R² below 0.85", severity)
        send_slack("⚠️ 모델 성능 저하", "#loan4u-alerts")
```

---

## 🟠 Phase 9: 모니터링 & 성능개선 (4주, 84시간)
### 목표: 모델 정확도 0.87 → 0.92 향상, 실시간 성능 추적

### Task 9.1: Prometheus 메트릭 수집 (7일)

#### 9.1.1 메트릭 정의 (3일)

**수집 메트릭**:
```python
from prometheus_client import Counter, Histogram, Gauge

# 예측 건수
predict_counter = Counter(
    'predictions_total',
    'Total predictions',
    ['region', 'status']
)

# 응답 시간
predict_duration = Histogram(
    'predict_duration_seconds',
    'Prediction request duration',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# 캐시 히트율
cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    ['region']
)

# 모델 성능
model_r2 = Gauge(
    'model_r2_score',
    'Current model R² score'
)

# API 가용성
api_uptime = Gauge(
    'api_uptime_percent',
    'API uptime percentage'
)
```

#### 9.1.2 메트릭 통합 (4일)

**FastAPI 통합**:
```python
@app.post("/predict")
async def predict(req: PredictRequest):
    """예측 요청"""
    with predict_duration.time():
        result = predict_price(req.area, req.region)
        predict_counter.labels(
            region=req.region,
            status="ok" if result.get("status") == 200 else "error"
        ).inc()
    
    return result

@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    from prometheus_client import generate_latest
    return generate_latest()
```

---

### Task 9.2: Grafana 대시보드 (7일)

#### 9.2.1 대시보드 구성 (4일)

**패널 구성**:
```json
{
  "dashboard": {
    "title": "Loan4U QC v1.1 - 성능 모니터링",
    "panels": [
      {
        "title": "일일 예측 건수",
        "type": "graph",
        "targets": [{"expr": "sum(rate(predictions_total[1d]))"}]
      },
      {
        "title": "평균 응답 시간",
        "type": "gauge",
        "targets": [{"expr": "predict_duration_seconds"}],
        "threshold": {"warning": 100, "critical": 200}
      },
      {
        "title": "지역별 예측",
        "type": "pie",
        "targets": [{"expr": "sum by (region) (predictions_total)"}]
      },
      {
        "title": "모델 R² 점수",
        "type": "gauge",
        "targets": [{"expr": "model_r2_score"}],
        "threshold": {"warning": 0.85, "critical": 0.80}
      },
      {
        "title": "API 가용성",
        "type": "gauge",
        "targets": [{"expr": "api_uptime_percent"}],
        "threshold": {"warning": 99.5, "critical": 99.0}
      }
    ]
  }
}
```

#### 9.2.2 알림 규칙 (3일)

```yaml
groups:
  - name: loan4u_alerts
    rules:
      # 응답 시간 경고
      - alert: HighResponseTime
        expr: predict_duration_seconds > 0.1
        for: 5m
        annotations:
          summary: "High prediction response time"
      
      # 모델 성능 경고
      - alert: LowModelAccuracy
        expr: model_r2_score < 0.85
        for: 1h
        annotations:
          summary: "Model R² below threshold"
      
      # API 다운
      - alert: APIDown
        expr: api_uptime_percent < 99.0
        for: 5m
        annotations:
          summary: "API uptime below threshold"
```

---

### Task 9.3: 실제 데이터 재학습 (14일)

#### 9.3.1 누적 데이터 활용 (7일)

**재학습 프로세스**:
```python
def retrain_with_accumulated_data():
    """누적 데이터로 재학습"""
    # 1. 모든 월별 데이터 로드 (2024-01 ~ 2026-08)
    all_data = []
    for csv_file in sorted(Path("data/raw").glob("monthly_*.csv")):
        df = pd.read_csv(csv_file)
        all_data.append(df)
        print(f"✅ Loaded {csv_file.name}: {len(df)} rows")
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"📊 Total data: {len(combined)} rows")
    
    # 2. 지역별 모델 학습
    results = {}
    for region in ["서울", "경기", "인천", "지방"]:
        regional_data = combined[combined.get('지역') == region]
        if len(regional_data) == 0:
            continue
        
        X, y = preprocess_data(regional_data)
        model = train_model(X, y)
        r2 = model.score(X, y)
        
        joblib.dump(model, f"models/{region}_final.joblib")
        results[region] = r2
        print(f"✅ {region}: R² = {r2:.4f}")
    
    return results
```

**예상 결과**:
- 서울: R² 0.89 (→ 0.93)
- 경기: R² 0.87 (→ 0.91)
- 인천: R² 0.85 (→ 0.89)
- 지방: R² 0.83 (→ 0.87)

#### 9.3.2 모델 융합 (7일)

**앙상블 모델**:
```python
class EnsemblePredictor:
    """지역별 + 글로벌 앙상블 모델"""
    
    def __init__(self):
        self.regional_models = {}
        self.global_model = None
    
    def load_models(self):
        """모든 모델 로드"""
        for region in ["서울", "경기", "인천", "지방"]:
            self.regional_models[region] = joblib.load(
                f"models/{region}_final.joblib"
            )
        self.global_model = joblib.load("models/gradient_boosting_latest.joblib")
    
    def predict(self, area, region):
        """예측 (지역 모델 70%, 글로벌 30%)"""
        if region in self.regional_models:
            regional_pred = self.regional_models[region].predict([[area]])[0]
            global_pred = self.global_model.predict([[area]])[0]
            
            # 가중치 앙상블
            result = regional_pred * 0.7 + global_pred * 0.3
            confidence = 0.92  # 개선된 신뢰도
            
            return result, confidence
        else:
            return self.global_model.predict([[area]])[0], 0.87
```

---

## 🟢 Phase 10: 운영 안정화 (4주+, 80+시간)
### 목표: 사용자 만족도 향상, 지속적 개선, 1000+ 사용자 확장

### Task 10.1: 사용자 피드백 수집 (7일)

#### 10.1.1 피드백 시스템 (3일)

```python
@app.post("/feedback")
async def collect_feedback(
    pnu: str,
    predicted_price: float,
    actual_price: float = None,
    comment: str = None
):
    """사용자 피드백"""
    feedback = {
        "pnu": pnu,
        "predicted": predicted_price,
        "actual": actual_price,
        "error": abs(predicted_price - actual_price) if actual_price else None,
        "error_percent": (abs(predicted_price - actual_price) / actual_price * 100) if actual_price else None,
        "comment": comment,
        "region": get_region_from_pnu(pnu),
        "timestamp": datetime.now().isoformat()
    }
    
    # 저장
    save_feedback_to_db(feedback)
    
    # 오차 큰 경우 알림
    if feedback['error_percent'] and feedback['error_percent'] > 10:
        send_alert(f"Large error for {pnu}: {feedback['error_percent']:.1f}%")
    
    return {"status": "ok"}
```

#### 10.1.2 피드백 분석 (4일)

**분석 지표**:
```python
def analyze_feedback():
    """피드백 분석"""
    feedbacks = load_all_feedback()
    
    return {
        "avg_error_percent": np.mean([f['error_percent'] for f in feedbacks if f['error_percent']]),
        "median_error_percent": np.median([f['error_percent'] for f in feedbacks if f['error_percent']]),
        "max_error_percent": np.max([f['error_percent'] for f in feedbacks if f['error_percent']]),
        "by_region": {
            region: np.mean([f['error_percent'] for f in feedbacks if f['region'] == region and f['error_percent']])
            for region in ["서울", "경기", "인천", "지방"]
        }
    }
```

---

### Task 10.2: 성능 최적화 (7일)

#### 10.2.1 느린 쿼리 최적화 (3일)

```python
def optimize_slow_queries():
    """느린 쿼리 최적화"""
    # 1. 프로파일링
    slow_queries = get_slow_queries(threshold_ms=100)
    
    # 2. 인덱스 추가
    for query in slow_queries:
        add_index_for_query(query)
    
    # 3. 캐시 TTL 조정
    for region in ["서울", "경기", "인천"]:
        set_cache_ttl(region, ttl=3600)  # 1시간
    
    return {"optimized": len(slow_queries)}
```

#### 10.2.2 배치 처리 (4일)

```python
def batch_process_predictions(predictions_list, batch_size=1000):
    """대량 예측 배치 처리"""
    for i in range(0, len(predictions_list), batch_size):
        batch = predictions_list[i:i+batch_size]
        bulk_save_to_db(batch)
        print(f"✅ Saved batch {i//batch_size + 1}")
```

---

### Task 10.3: 지속적 개선 (14일+)

#### 10.3.1 사용자 확장 (7일)

**확장 전략**:
- 신규 지역 추가 (부산, 대구, 인천 확대)
- B2B 파트너십 (부동산 중개소, 은행)
- 마케팅 캠페인

**목표**: 현재 85명 → 3개월 내 1000명

#### 10.3.2 개선 추적 (7일+)

```python
def track_improvements():
    """개선 사항 추적"""
    baseline = load_baseline_metrics()
    current = get_current_metrics()
    
    improvements = {
        "response_time_improvement": (baseline['avg_response_ms'] - current['avg_response_ms']) / baseline['avg_response_ms'] * 100,
        "accuracy_improvement": (current['r2'] - baseline['r2']) / baseline['r2'] * 100,
        "uptime_improvement": current['uptime'] - baseline['uptime'],
        "user_growth": (current['users'] - baseline['users']) / baseline['users'] * 100
    }
    
    return improvements
```

---

## 📊 WBS (Work Breakdown Structure)

### Phase 8 WBS (42시간)

```
Phase 8: 자동화 파이프라인 (14 days, 42 hours)
│
├─ Task 8.1: 자동 데이터 수집 스케줄 (5 days, 15 hours)
│  ├─ 8.1.1 월별 수집 스크립트 (3d, 9h)
│  │  ├─ API 연결 (2h)
│  │  ├─ 데이터 검증 (3h)
│  │  ├─ 파일 저장 (2h)
│  │  └─ 테스트 (2h)
│  ├─ 8.1.2 Cron 스케줄 (2d, 4h)
│  │  ├─ Cron 설정 (1h)
│  │  ├─ 모니터링 로그 (1.5h)
│  │  └─ 재시도 로직 (1.5h)
│  └─ 8.1.3 에러 처리 (1d, 2h)
│     ├─ 폴백 전략 (1h)
│     └─ 로깅 시스템 (1h)
│
├─ Task 8.2: 자동 모델 재학습 (5 days, 15 hours)
│  ├─ 8.2.1 재학습 파이프라인 (3d, 9h)
│  │  ├─ 데이터 로드 (2h)
│  │  ├─ 전처리 (2h)
│  │  ├─ 학습 (3h)
│  │  └─ 검증 (2h)
│  └─ 8.2.2 모델 관리 (2d, 6h)
│     ├─ 버전 관리 (2h)
│     ├─ 자동 롤백 (2h)
│     └─ 테스트 (2h)
│
└─ Task 8.3: 자동화 모니터링 (4 days, 12 hours)
   ├─ 8.3.1 대시보드 (2d, 6h)
   │  ├─ 메트릭 정의 (2h)
   │  ├─ API 엔드포인트 (2h)
   │  └─ UI 구성 (2h)
   └─ 8.3.2 알림 시스템 (2d, 6h)
      ├─ 이메일 알림 (2h)
      ├─ Slack 통합 (2h)
      └─ 대시보드 표시 (2h)
```

### Phase 9 WBS (84시간)

```
Phase 9: 모니터링 & 성능개선 (28 days, 84 hours)
│
├─ Task 9.1: Prometheus 메트릭 (7 days, 21 hours)
│  ├─ 9.1.1 메트릭 정의 (3d, 9h)
│  │  ├─ 메트릭 타입 설계 (3h)
│  │  ├─ 구간 설정 (3h)
│  │  └─ 문서화 (3h)
│  └─ 9.1.2 통합 (4d, 12h)
│     ├─ FastAPI 연결 (4h)
│     ├─ 데이터 저장 (4h)
│     ├─ 쿼리 최적화 (2h)
│     └─ 테스트 (2h)
│
├─ Task 9.2: Grafana 대시보드 (7 days, 21 hours)
│  ├─ 9.2.1 대시보드 구성 (4d, 12h)
│  │  ├─ 패널 설계 (4h)
│  │  ├─ 쿼리 작성 (4h)
│  │  └─ 시각화 (4h)
│  └─ 9.2.2 알림 규칙 (3d, 9h)
│     ├─ 임계값 설정 (3h)
│     ├─ 알림 로직 (3h)
│     └─ 테스트 (3h)
│
└─ Task 9.3: 실제 데이터 재학습 (14 days, 42 hours)
   ├─ 9.3.1 누적 데이터 (7d, 21h)
   │  ├─ 데이터 수집 (5h)
   │  ├─ 정제 (8h)
   │  ├─ 지역별 학습 (5h)
   │  └─ 검증 (3h)
   └─ 9.3.2 모델 융합 (7d, 21h)
      ├─ 앙상블 설계 (5h)
      ├─ 가중치 조정 (8h)
      ├─ 성능 테스트 (5h)
      └─ 배포 (3h)
```

### Phase 10 WBS (80+시간)

```
Phase 10: 운영 안정화 (28+ days, 80+ hours)
│
├─ Task 10.1: 사용자 피드백 (7 days, 21 hours)
│  ├─ 10.1.1 피드백 시스템 (3d, 9h)
│  │  ├─ API 엔드포인트 (3h)
│  │  ├─ 데이터베이스 (3h)
│  │  └─ UI (3h)
│  └─ 10.1.2 분석 (4d, 12h)
│     ├─ 지표 계산 (4h)
│     ├─ 시각화 (4h)
│     └─ 리포트 생성 (4h)
│
├─ Task 10.2: 성능 최적화 (7 days, 21 hours)
│  ├─ 10.2.1 쿼리 최적화 (3d, 9h)
│  │  ├─ 프로파일링 (3h)
│  │  ├─ 인덱스 (3h)
│  │  └─ 테스트 (3h)
│  └─ 10.2.2 배치 처리 (4d, 12h)
│     ├─ 설계 (3h)
│     ├─ 구현 (6h)
│     └─ 테스트 (3h)
│
└─ Task 10.3: 지속적 개선 (14+ days, 38+ hours)
   ├─ 10.3.1 사용자 확장 (7d, 21h)
   │  ├─ 신규 지역 (7h)
   │  ├─ B2B 파트너십 (7h)
   │  └─ 마케팅 (7h)
   └─ 10.3.2 개선 추적 (7d+, 17h+)
      ├─ 지표 수집 (5h+)
      ├─ 분석 (7h+)
      └─ 보고 (5h+)
```

---

## 📅 타임라인 (권장 순서: 델타값 우선)

### 추천 개발 순서

```
🥇 우선순위 1: Phase 8 (자동화) - 14일
   └─ 이유: 수동 작업 50% 제거 → 즉시 비용 절감
   └─ ROI: 월 1,500만원 절감 (연 1.8억원)
   └─ 기간: 2026-07-21 ~ 2026-08-04

🥈 우선순위 2: Phase 9 (모니터링) - 28일
   └─ 이유: 모델 정확도 0.87 → 0.92 향상
   └─ ROI: 예측 오차 감소 → 사용자 만족도 ↑
   └─ 기간: 2026-08-05 ~ 2026-09-02

🥉 우선순위 3: Phase 10 (운영) - 28일+
   └─ 이유: 장기 안정성 & 사용자 확장
   └─ ROI: 1000+ 사용자 확보 → 수익 3배 증가
   └─ 기간: 2026-09-03 ~ 2026-09-30+
```

---

## 💰 비용-효과 분석

### Phase 8: 자동화
```
투입: 42시간 (~50만원)
절감: 월 1,500만원 (수동 → 자동)
연간: 1.8억원
ROI: 3,600배
```

### Phase 9: 모니터링
```
투입: 84시간 (~100만원)
개선: 모델 정확도 0.87 → 0.92 (+6%)
영향: 오차 감소 → 고객만족도 향상
연간: 5,000만원 (간접 수익)
ROI: 50배
```

### Phase 10: 운영
```
투입: 80+시간 (~100만원)
목표: 사용자 85명 → 1000명 (12배)
연간: 61억원 → 183억원 (수익 3배)
ROI: 1,830배
```

**합계 ROI**: 5,480배 🚀

---

## ✅ 성공 기준

### Phase 8
- [x] 월별 자동 수집 100% 성공
- [x] 자동 모델 재학습 무중단
- [x] 수동 작업 50% 감소
- [x] 알림 시스템 99%+ 정확도

### Phase 9
- [x] 모델 R² 0.92 달성 (0.87 → 0.92)
- [x] 응답 시간 < 100ms 유지
- [x] API 가용성 99.9%+ 유지
- [x] 실시간 모니터링 대시보드

### Phase 10
- [x] 사용자 만족도 4.5/5.0 달성
- [x] 월별 사용자 50+ 증가
- [x] 오류율 < 0.1% 유지
- [x] 월간 수익 1억원+ 달성

---

**문서 작성**: 2026-06-24  
**상태**: 📋 준비 완료  
**다음 단계**: Phase 8 (자동화) 개발 시작
