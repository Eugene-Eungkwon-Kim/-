# 📊 프로덕션 모니터링 및 성능 추적 가이드

**작성일**: 2026-06-17  
**목적**: AVM 시스템의 실시간 성능 모니터링 및 추적  
**대상**: 운영팀, 데이터 과학자, 시스템 관리자

---

## 🚀 빠른 시작 (5분)

### 1️⃣ Terminal 1: API 서버 시작

```bash
cd /home/user/-/avm_project
python -m uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000
```

**출력**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2️⃣ 브라우저에서 대시보드 접근

```
http://localhost:8000/dashboard
```

**보이는 것**:
- 실시간 성능 차트 (자동 30초 갱신)
- 모델 성능 메트릭
- 예측 통계
- 알림 로그

### 3️⃣ Terminal 2: 자동 재학습 스케줄러 (선택)

```bash
python scripts/looping_scheduler.py --mode scheduler
```

**기능**:
- 매주 목요일 10:00 UTC 자동 재학습
- 성능 회귀 자동 감지 (>2% 저하)
- 자동 알림 발송

---

## 📊 모니터링 시스템 구조

### 아키텍처

```
┌─────────────────────────────────────────────┐
│         실시간 모니터링 대시보드             │
│       http://localhost:8000/dashboard       │
├─────────────────────────────────────────────┤
│              FastAPI REST API               │
│  8개 엔드포인트 (성능 데이터 제공)         │
├─────────────────────────────────────────────┤
│          성능 메트릭 추적 시스템            │
│  ├─ R² 점수                                │
│  ├─ RMSE / MAE / MAPE                      │
│  ├─ 응답 시간                              │
│  └─ 처리량                                 │
├─────────────────────────────────────────────┤
│          로깅 및 저장소                      │
│  ├─ logs/performance_history.jsonl         │
│  ├─ logs/alerts.log                        │
│  └─ output/reports/                        │
└─────────────────────────────────────────────┘
```

---

## 🎯 모니터링 메트릭

### 주요 성능 메트릭 (4개)

| 메트릭 | 설명 | 목표값 | 알림값 |
|--------|------|--------|--------|
| **R² 점수** | 모델 설명력 | ≥ 0.78 | < 0.76 (-2%) |
| **RMSE** | 제곱평균제곱근 | ≤ 100M | > 150M |
| **MAE** | 평균절대오차 | ≤ 80M | > 120M |
| **MAPE** | 평균절대백분오차 | ≤ 15% | > 20% |

### 운영 메트릭 (4개)

| 메트릭 | 설명 | 목표값 | 알림값 |
|--------|------|--------|--------|
| **응답 시간** | API 응답 시간 (ms) | < 50ms | > 100ms |
| **처리량** | samples/sec | > 1M | < 500K |
| **에러율** | 에러 비율 (%) | < 1% | > 5% |
| **가용성** | 가용성 (%) | > 99.5% | < 95% |

---

## 📈 대시보드 기능

### 1. 실시간 성능 차트

```
📊 Model Performance (30초 자동 갱신)

R² Score Trend (최근 24시간)
  ┌─────────────────────────────────┐
  │       0.79                      │
  │       0.78 ▁▂▃▄▅▆▇█▆▅▄▃▂▁     │
  │       0.77                      │
  │       0.76                      │
  └─────────────────────────────────┘

RMSE Trend (최근 24시간)
  ┌─────────────────────────────────┐
  │       95M                       │
  │       90M ▅▆▇█▆▅▄▃▂▁▂▃▄▅▆▇█   │
  │       85M                       │
  └─────────────────────────────────┘
```

### 2. 성능 통계

```
📋 Performance Summary

Current Model: GradientBoosting
  R² Score: 0.7917
  RMSE: 95.2M
  MAE: 78.4M
  MAPE: 12.3%

Response Time:
  Avg: 12.5ms
  P95: 25.3ms
  P99: 48.7ms

Prediction Stats:
  Total: 15,234
  Success: 15,230 (99.97%)
  Error: 4 (0.03%)
```

### 3. 알림 로그

```
🔔 Alerts & Warnings

[2026-06-17 11:30] ✅ Scheduled Retraining Started
[2026-06-17 11:25] ⚠️  Response Time High (85ms > 100ms threshold)
[2026-06-17 11:20] ✅ Prediction Successful (1000 samples processed)
[2026-06-17 11:15] ✅ Performance Within Limits (R²=0.7917)
```

---

## 🔍 REST API 엔드포인트

### 1. 상태 확인

```bash
curl http://localhost:8000/health
```

**응답**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-17T11:30:00",
  "uptime": 3600
}
```

### 2. 버전 확인

```bash
curl http://localhost:8000/api/version
```

**응답**:
```json
{
  "version": "1.0",
  "model": "GradientBoosting",
  "r2_score": 0.7917
}
```

### 3. 단일 예측

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "area_sqm": 102.5,
    "year_built": 2010,
    "rooms": 3,
    "location": "서울"
  }'
```

**응답**:
```json
{
  "prediction": 485320000,
  "confidence": 0.89,
  "unit": "KRW"
}
```

### 4. 배치 예측

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"area_sqm": 102.5, "year_built": 2010},
    {"area_sqm": 85.0, "year_built": 2015}
  ]'
```

### 5. 성능 이력

```bash
curl http://localhost:8000/dashboard/api/performance
```

**응답**:
```json
{
  "data": [
    {"timestamp": "2026-06-17T10:00", "r2": 0.7825},
    {"timestamp": "2026-06-17T11:00", "r2": 0.7917}
  ]
}
```

### 6. 알림 로그

```bash
curl http://localhost:8000/dashboard/api/alerts
```

### 7. 대시보드 요약

```bash
curl http://localhost:8000/dashboard/api/summary
```

### 8. 캐시 통계

```bash
curl http://localhost:8000/cache/stats
```

---

## 📋 성능 로그 분석

### 로그 파일 위치

```
logs/
├── performance_history.jsonl    (성능 메트릭, 1줄=1개 레코드)
├── alerts.log                   (알림 로그)
└── errors.log                   (에러 로그)
```

### 로그 형식 (JSONL)

```json
{"timestamp": "2026-06-17T11:30:00", "model": "GradientBoosting", "r2_score": 0.7917, "rmse": 95.2}
{"timestamp": "2026-06-17T11:35:00", "model": "GradientBoosting", "r2_score": 0.7915, "rmse": 96.1}
{"timestamp": "2026-06-17T11:40:00", "model": "GradientBoosting", "r2_score": 0.7920, "rmse": 94.8}
```

### 로그 분석 (Python)

```python
import json
import pandas as pd

# 로그 읽기
logs = []
with open('logs/performance_history.jsonl', 'r') as f:
    for line in f:
        logs.append(json.loads(line))

# DataFrame 변환
df = pd.DataFrame(logs)

# 성능 추이
print(df[['timestamp', 'r2_score', 'rmse']].tail(10))

# 평균값
print(f"평균 R²: {df['r2_score'].mean():.4f}")
print(f"평균 RMSE: {df['rmse'].mean():.1f}")

# 변화율 계산
df['r2_change'] = df['r2_score'].pct_change()
df['regression_alert'] = df['r2_change'] < -0.02
print(f"회귀 감지: {df['regression_alert'].sum()}개")
```

---

## 🔔 알림 시스템

### 자동 알림 조건

#### 1. 성능 회귀 (R² > 2% 감소)

```
❌ 알림 조건: R² 감소량 > 2%
   예: 0.7917 → 0.7759 (2.0% 감소)

✅ 액션:
   1. 즉시 알림 발송
   2. 로그 기록
   3. 대시보드에 표시
   4. 선택: 자동 재학습 트리거
```

#### 2. 응답 시간 초과

```
❌ 알림 조건: 응답 시간 > 100ms
   예: API 평균 응답 시간 120ms

✅ 액션:
   1. 성능 저하 알림
   2. 캐싱 전략 검토
   3. 로드 밸런싱 검토
```

#### 3. 에러율 증가

```
❌ 알림 조건: 에러율 > 5%
   예: 1,000개 중 60개 실패

✅ 액션:
   1. 즉시 알림 발송
   2. 로그 분석
   3. 모델 상태 확인
```

---

## 🔄 자동 재학습 스케줄

### 스케줄 구성

```
매주 목요일 10:00 UTC

↓

1️⃣  데이터 수집 (Data.go.kr API)
    ├─ 최근 1개월 부동산 데이터
    ├─ 데이터 검증
    └─ 정규화 처리

↓

2️⃣  모델 학습
    ├─ 기준선 모델 평가 (6개 모델)
    ├─ 하이퍼파라미터 튜닝
    └─ 특성 선택

↓

3️⃣  성능 비교
    ├─ 현재 모델 vs 새 모델
    ├─ R² 비교 (2% 이상 개선 필요)
    └─ 회귀 감지

↓

4️⃣  모델 승격 (선택)
    ├─ 개선 시: 자동 배포
    └─ 미개선 시: 기존 모델 유지

↓

5️⃣  로깅 및 알림
    ├─ 성능 로그 기록
    ├─ 알림 발송
    └─ 대시보드 업데이트
```

### 수동 재학습 명령

```bash
# 재학습 트리거 (모니터 모드)
python scripts/looping_scheduler.py --mode monitor

# 스케줄러 시작 (자동 재학습)
python scripts/looping_scheduler.py --mode scheduler
```

---

## 📈 성능 추적 방법

### 방법 1: 대시보드 시각화

**최고의 실시간 모니터링 방법**

```
브라우저 열기 → http://localhost:8000/dashboard
자동 30초 갱신 → 실시간 성능 확인
차트 보기 → R², RMSE 추이 분석
```

### 방법 2: REST API 폴링

**프로그래밍 기반 추적**

```python
import requests
import json
from datetime import datetime

# 매 1분마다 성능 확인
while True:
    response = requests.get('http://localhost:8000/dashboard/api/summary')
    data = response.json()
    
    print(f"[{datetime.now()}] R²={data['r2_score']:.4f}, RMSE={data['rmse']:.1f}")
    
    time.sleep(60)
```

### 방법 3: 로그 파일 분석

**이력 기반 심층 분석**

```bash
# 최근 10개 성능 기록 보기
tail -10 logs/performance_history.jsonl | jq .

# R² 추이 그래프 생성
python -c "
import json
import pandas as pd
logs = [json.loads(line) for line in open('logs/performance_history.jsonl')]
df = pd.DataFrame(logs)
df.plot(x='timestamp', y='r2_score', kind='line')
"
```

---

## 🎯 모니터링 체크리스트

### 일일 점검

- [ ] API 서버 정상 작동 확인
- [ ] 대시보드 접근 가능 확인
- [ ] 최근 성능 메트릭 확인
- [ ] 알림 로그 검토
- [ ] 에러 로그 확인

### 주간 점검

- [ ] 성능 추이 분석 (R², RMSE)
- [ ] 회귀 감지 여부 확인
- [ ] 응답 시간 변화 분석
- [ ] 자동 재학습 상태 확인
- [ ] 성능 리포트 생성

### 월간 점검

- [ ] 전체 성능 요약 리포트
- [ ] 트렌드 분석
- [ ] 개선 기회 식별
- [ ] 임계값 조정 필요 여부
- [ ] 향후 개선안 계획

---

## 🚨 문제 해결

### 문제: 대시보드 접근 불가

```
증상: http://localhost:8000/dashboard 응답 없음

해결:
1. API 서버 실행 확인
   ps aux | grep uvicorn

2. 포트 확인
   lsof -i :8000

3. 방화벽 확인
   sudo ufw allow 8000

4. 서버 재시작
   python -m uvicorn scripts.api_server:app --port 8000
```

### 문제: 성능 메트릭 부족

```
증상: 성능 로그가 비어있음

해결:
1. 로그 파일 확인
   ls -la logs/

2. 스케줄러 실행
   python scripts/looping_scheduler.py --mode scheduler

3. 수동 예측으로 로그 생성
   curl -X POST http://localhost:8000/predict ...
```

### 문제: 응답 시간 느림

```
증상: API 응답 시간 > 100ms

해결:
1. 시스템 리소스 확인
   top, free -m

2. 모델 크기 확인
   ls -lh models/

3. 캐싱 활성화 확인
   curl http://localhost:8000/cache/stats

4. 백그라운드 프로세스 확인
   ps aux
```

---

## 📞 지원

### 문서

- 📖 [AVM_COMPLETE_GUIDE.md](AVM_COMPLETE_GUIDE.md) - 전체 기술 가이드
- 📊 [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) - 대시보드 사용법
- 🔧 [LOOPING_AUTOMATION_GUIDE.md](LOOPING_AUTOMATION_GUIDE.md) - 자동화 설정

### 로그 위치

```
logs/
├── performance_history.jsonl  # 성능 메트릭
├── alerts.log                 # 알림
└── errors.log                 # 에러
```

---

## 🎓 결론

### 모니터링 시스템 정리

```
✅ 실시간 대시보드: 시각화된 성능 추적
✅ REST API: 프로그래밍 기반 접근
✅ 자동 로깅: JSONL 포맷 기록
✅ 자동 알림: 회귀 감지 및 알림
✅ 자동 재학습: 주간 자동 갱신
```

### 권고사항

1. **일일 모니터링**: 대시보드로 실시간 확인
2. **주간 분석**: 성능 추이 분석
3. **월간 리포트**: 종합 평가 및 개선안

---

**모니터링 시스템**: ✅ **준비 완료**  
**대시보드**: 🌐 **http://localhost:8000/dashboard**  
**성능 추적**: 📊 **실시간 활성화 준비됨**

