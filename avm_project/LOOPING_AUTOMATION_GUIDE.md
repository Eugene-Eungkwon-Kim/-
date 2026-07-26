# 🔄 AVM 루핑 자동화 가이드

**상태**: ✅ 완료 (2026-06-16)  
**목표**: 지속적 모델 재학습·성능 추적·모니터링 자동화

---

## 📋 루핑 자동화 구성

### 1️⃣ 주간 자동 재학습
**스케줄**: 매주 목요일 10:00 (UTC)  
**기능**:
- 최신 데이터로 6개 모델 재학습
- 최고 성능 모델 자동 선택
- 성능 회귀 감지 후 승격 여부 결정
- 프로덕션 모델 자동 업데이트

### 2️⃣ 성능 추적
**기록 항목**:
- 타임스탬프
- 모델명
- Test R² (정확도)
- Test RMSE (평균제곱근오차)

**로그 위치**: `logs/performance_history.jsonl`

### 3️⃣ 자동 알림
**감시 항목**:
- 성능 급락 (> 2% 회귀) → HIGH
- 성능 소폭 감소 (≤ 2%) → MEDIUM
- 성능 향상 → INFO

**로그 위치**: `logs/alerts.log`

### 4️⃣ 실시간 모니터링 (선택적)
**감시 항목**:
- API 헬스 상태
- 모델 레지스트리 상태
- 캐시 통계

---

## 🚀 사용 방법

### 옵션 1: 파이썬 스케줄러 (권장 — Crontab 불필요)

#### 스케줄러 모드 (백그라운드)
```bash
# 스케줄러 시작 (매주 목요일 10:00 자동 실행)
python3 scripts/looping_scheduler.py --mode scheduler --interval 60

# 또는 백그라운드 실행
python3 scripts/looping_scheduler.py --mode scheduler &
```

#### 모니터링 모드 (실시간)
```bash
# 실시간 API 상태 감시 (30초 간격)
python3 scripts/looping_scheduler.py --mode monitor --interval 30
```

#### 테스트 실행
```bash
# 즉시 자동 재학습 (--dry-run: 승격 없음)
python3 scripts/auto_retraining.py --dry-run

# 실제 재학습 + 승격
python3 scripts/auto_retraining.py
```

---

## 📊 로그 및 모니터링

### 성능 이력 조회
```bash
# 최근 10개 기록
tail -10 logs/performance_history.jsonl | jq '.'

# 성능 통계 (Python)
python3 << 'EOF'
import json
logs = [json.loads(line) for line in open('logs/performance_history.jsonl')]
r2_values = [e['test_r2'] for e in logs]
print(f"최고: {max(r2_values):.4f}")
print(f"최저: {min(r2_values):.4f}")
print(f"평균: {sum(r2_values)/len(r2_values):.4f}")
print(f"기록 수: {len(r2_values)}")
EOF
```

### 알림 확인
```bash
# 최근 알림
tail -20 logs/alerts.log | jq '.'

# 회귀 알림만 필터
grep "regression" logs/alerts.log | jq '.'
```

### 자동 재학습 로그
```bash
# 최신 실행 로그
tail -100 logs/cron_auto_retraining.log

# 특정 날짜 로그
grep "2026-06-16" logs/cron_auto_retraining.log
```

---

## 🔧 시스템 통합

### 옵션 2: Linux Cron (로컬 환경)

원격 환경에 Crontab이 없어서 파이썬 스케줄러를 사용하지만,
로컬 환경에서는 다음과 같이 Cron 등록 가능:

```bash
# Cron 작업 편집
crontab -e

# 추가 (매주 목요일 10:00)
0 10 * * 4 cd /path/to/avm_project && python3 scripts/auto_retraining.py >> logs/cron_auto_retraining.log 2>&1
```

### 옵션 3: 클라우드 스케줄러 (Cloud Run 배포 후)

Google Cloud Scheduler 사용:
```bash
# Scheduler job 생성
gcloud scheduler jobs create http avm-weekly-retraining \
  --schedule="0 10 * * 4" \
  --http-method=POST \
  --uri=https://your-cloud-run-url/retrain \
  --oidc-service-account-email=your-service-account@project.iam.gserviceaccount.com
```

---

## 📈 성능 추적 분석

### 시계열 그래프 (Python)
```python
import json
import matplotlib.pyplot as plt

# 성능 이력 로드
with open('logs/performance_history.jsonl') as f:
    logs = [json.loads(line) for line in f]

timestamps = [e['timestamp'][:10] for e in logs]
r2_values = [e['test_r2'] for e in logs]

plt.figure(figsize=(10, 5))
plt.plot(timestamps, r2_values, marker='o')
plt.xlabel('Date')
plt.ylabel('Test R²')
plt.title('Model Performance Over Time')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('output/performance_trend.png')
```

---

## ⚙️ 회귀 가드 메커니즘

### 작동 원리
1. **신규 모델 R² 계산**: 새 학습 후 최고 성능 모델 선택
2. **기존 챔피언 R² 비교**: 모델 레지스트리에서 이전 값 조회
3. **회귀 판정**: `신규 R² < 기존 R² - 0.02` → 승격 거부
4. **로그 기록**: 판정 결과 + 상세 원인 기록

### 예시
```json
{
  "timestamp": "2026-06-16T10:17:00",
  "best_model": "LGBMRegressor",
  "new_r2": 0.7488,
  "previous_r2": 0.7600,
  "promoted": false,
  "promotion_reason": "성능 회귀 감지 (신규 0.7488 < 기존 0.7600 - 허용오차 0.02)"
}
```

---

## 🚨 문제 해결

### 1. 스케줄러 실행 안 됨
```bash
# 스케줄러 프로세스 확인
ps aux | grep looping_scheduler

# 로그 확인
tail -50 logs/cron_auto_retraining.log

# 수동 테스트
python3 scripts/auto_retraining.py --dry-run
```

### 2. 모델 학습 실패
```bash
# 데이터 확인
ls -la data/raw/ data/processed/

# 특성 스키마 확인
cat models/feature_schema.json

# 모델 레지스트리 확인
cat models/model_registry.json | jq '.'
```

### 3. API 헬스 체크 실패
```bash
# API 실행 확인 (로컬)
curl http://localhost:8000/health

# 로그 확인
tail -50 logs/api_server.log
```

---

## 📅 유지보수

### 주간 작업
- [ ] 성능 이력 확인
- [ ] 알림 로그 검토
- [ ] 모델 정확도 추이 분석
- [ ] 캐시 통계 확인

### 월간 작업
- [ ] 성능 리포트 생성
- [ ] 데이터 수집 상태 확인 (실제 데이터 수집 시)
- [ ] 모델 특성 검토
- [ ] 알림 규칙 조정

### 분기별 작업
- [ ] 전체 성능 평가
- [ ] 모델 재평가 (새 데이터 통합 여부)
- [ ] 스케줄링 정책 검토
- [ ] 자동화 개선안 수집

---

## 🎯 다음 단계

1. **Phase 1 배포** → Cloud Run 배포 (로컬 환경)
2. **Phase 3 실행** → Data.go.kr API로 실제 데이터 수집
3. **대시보드** → 웹 기반 성능 모니터링 대시보드
4. **고급 분석** → 모델 설명가능성(SHAP), 피처 중요도 분석

---

**상태**: ✅ 루핑 자동화 설정 완료  
**마지막 업데이트**: 2026-06-16 10:17 UTC
