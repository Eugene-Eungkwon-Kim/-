# 🚀 AVM 배포 및 운영 매뉴얼

**작성일**: 2026-06-17  
**대상**: 운영팀, 개발팀  
**상태**: 프로덕션 배포 준비 완료

---

## 📋 목차

1. [빠른 배포 가이드](#빠른-배포-가이드)
2. [자동화 파이프라인](#자동화-파이프라인)
3. [모니터링 및 알림](#모니터링-및-알림)
4. [운영 절차](#운영-절차)
5. [장애 대응](#장애-대응)
6. [정기 유지보수](#정기-유지보수)

---

## 빠른 배포 가이드

### 📦 사전 준비

```bash
# 1. 저장소 클론
git clone <repository-url> avm_project
cd avm_project

# 2. 의존성 설치
pip install -r requirements-minimal.txt

# 3. 환경 변수 설정
cat > .env <<EOF
DATA_GO_KR_API_KEY=YOUR_API_KEY
DEBUG=False
LOG_LEVEL=INFO
EOF

chmod 600 .env  # 보안: 읽기 권한만
```

### 🚀 배포 (3가지 방법)

#### 방법 1: 통합 자동화 스크립트 (권장)

```bash
# 전체 파이프라인 실행 (Phase 0-5 모두)
bash scripts/run_complete_pipeline.sh full

# 또는 단계별 실행
bash scripts/run_complete_pipeline.sh setup      # 환경 설정
bash scripts/run_complete_pipeline.sh data       # 데이터 준비 + 수집
bash scripts/run_complete_pipeline.sh optimize   # 모델 최적화
bash scripts/run_complete_pipeline.sh explain    # SHAP 분석
bash scripts/run_complete_pipeline.sh monitor    # 모니터링
```

#### 방법 2: Docker (Cloud Run)

```bash
# Dockerfile 생성
cat > Dockerfile <<EOF
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 빌드 및 실행
docker build -t avm-model .
docker run -p 8000:8000 \
  -e DATA_GO_KR_API_KEY=$DATA_GO_KR_API_KEY \
  avm-model
```

#### 방법 3: Cloud Run (GCP)

```bash
# .env 파일을 Secret Manager에 저장
gcloud secrets create avm-env --data-file=.env

# 배포
gcloud run deploy avm-server \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --set-env-vars=DATA_GO_KR_API_KEY=$DATA_GO_KR_API_KEY
```

---

## 자동화 파이프라인

### 주간 자동 재학습

#### 옵션 1: Crontab (Linux/Mac)

```bash
# Crontab 편집
crontab -e

# 매주 목요일 10:00에 실행
0 10 * * 4 cd /home/user/-/avm_project && python3 scripts/auto_retraining.py >> logs/cron.log 2>&1
```

#### 옵션 2: Cloud Scheduler (GCP)

```bash
# Cloud Scheduler 작업 생성
gcloud scheduler jobs create http avm-retraining \
  --schedule="0 10 * * 4" \
  --timezone="Asia/Seoul" \
  --http-method=POST \
  --uri=https://avm-server-abc123.a.run.app/retrain \
  --headers="Authorization: Bearer $(gcloud auth print-identity-token)"
```

#### 옵션 3: Python Schedule (모든 환경)

```bash
# 백그라운드에서 실행
nohup python3 scripts/looping_scheduler.py --mode scheduler > logs/scheduler.log 2>&1 &

# 또는 systemd 서비스로 등록
cat > /etc/systemd/system/avm-scheduler.service <<EOF
[Unit]
Description=AVM Weekly Retraining Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/user/-/avm_project
ExecStart=/usr/bin/python3 scripts/looping_scheduler.py --mode scheduler
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl enable avm-scheduler
sudo systemctl start avm-scheduler
sudo systemctl status avm-scheduler
```

---

## 모니터링 및 알림

### 대시보드 접속

```bash
# API 서버 시작
uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000

# 브라우저 접속
# http://localhost:8000/dashboard
```

### REST API 모니터링

```bash
# 성능 요약
curl http://localhost:8000/dashboard/api/summary

# 성능 이력
curl http://localhost:8000/dashboard/api/performance?limit=10

# 알림 로그
curl http://localhost:8000/dashboard/api/alerts?limit=20
```

### 실시간 로그 확인

```bash
# 성능 이력 실시간 확인
tail -f logs/performance_history.jsonl

# 알림 실시간 확인
tail -f logs/alerts.log

# 전체 파이프라인 로그
tail -f logs/pipeline_*.log
```

### 알림 설정

```bash
# 이메일 알림 (선택사항)
# scripts/api_server.py의 send_alert_email() 함수 구현 필요

# Slack 연동 (선택사항)
# 환경변수: SLACK_WEBHOOK_URL 설정
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# 성능 회귀 감지 시 자동으로 Slack 메시지 전송
```

---

## 운영 절차

### 일일 점검 (Daily)

```bash
#!/bin/bash
# daily_check.sh

echo "=== 일일 점검 ==="

# 1. 프로세스 확인
echo "1. 프로세스 상태"
ps aux | grep -E "uvicorn|looping_scheduler" | grep -v grep

# 2. 로그 확인
echo "2. 최근 오류"
tail -5 logs/alerts.log

# 3. 성능 확인
echo "3. 최신 성능"
tail -1 logs/performance_history.jsonl | python3 -m json.tool

# 4. 디스크 확인
echo "4. 디스크 사용량"
du -sh data/ models/ output/ logs/

echo "=== 점검 완료 ==="
```

### 주간 점검 (Weekly)

```bash
#!/bin/bash
# weekly_check.sh

echo "=== 주간 점검 ==="

# 1. 모델 성능 추이
echo "1. 지난 주 성능 추이"
python3 -c "
import json
from pathlib import Path

perf_log = Path('logs/performance_history.jsonl')
lines = perf_log.read_text().strip().split('\n')
entries = [json.loads(line) for line in lines[-7:] if line]

for entry in entries:
    print(f\"{entry['timestamp']}: {entry['model_name']} R²={entry['test_r2']:.4f}\")
"

# 2. 자동 재학습 확인
echo "2. 자동 재학습 실행 여부"
grep "auto_retraining" logs/cron.log | tail -1

# 3. API 응답 시간
echo "3. API 응답 시간 확인"
curl -w "응답 시간: %{time_total}초\n" -o /dev/null -s http://localhost:8000/health

# 4. 모델 무결성
echo "4. 모델 SHA256 검증"
python3 -c "
import json
with open('models/model_registry.json') as f:
    registry = json.load(f)
print(f\"현재 모델: {registry['champion']['name']}\")
print(f\"SHA256: {registry['champion']['sha256'][:16]}...\")
"

echo "=== 점검 완료 ==="
```

### 월간 점검 (Monthly)

```bash
#!/bin/bash
# monthly_check.sh

echo "=== 월간 점검 ==="

# 1. 모델 성능 통계
echo "1. 월간 성능 통계"
python3 scripts/model_explainability.py  # SHAP 재분석

# 2. 데이터 품질
echo "2. 데이터 품질 검증"
python3 -c "
import pandas as pd
from pathlib import Path

latest_file = max(Path('data/raw').glob('real_estate_*.csv'), key=lambda x: x.stat().st_mtime)
df = pd.read_csv(latest_file)
print(f'행: {len(df):,}, 컬럼: {len(df.columns)}')
print(f'결측치: {df.isnull().sum().sum()}')
print(f'중복: {len(df[df.duplicated()])}')
"

# 3. 로그 압축 및 보관
echo "3. 로그 압축"
tar -czf logs/logs_backup_$(date +%Y%m).tar.gz logs/*.log logs/*.jsonl
rm -f logs/*.log logs/*.jsonl

# 4. 백업
echo "4. 모델 백업"
cp models/production_model.joblib models/backups/production_$(date +%Y%m%d).joblib

echo "=== 점검 완료 ==="
```

---

## 장애 대응

### 문제: API 서버가 응답하지 않음

```bash
# 1. 프로세스 확인
lsof -i :8000

# 2. 포트 강제 해제 (필요시)
kill -9 <PID>

# 3. 서버 재시작
uvicorn scripts.api_server:app --port 8000 --reload
```

### 문제: 모델 성능 급락 (> 2% 회귀)

```bash
# 1. 알림 확인
cat logs/alerts.log | tail -5

# 2. 최근 데이터 확인
head -10 data/raw/real_estate_combined_*.csv

# 3. 이전 모델로 롤백
cp models/backups/production_20260616.joblib models/production_model.joblib

# 4. 대시보드에서 수동 확인
# http://localhost:8000/dashboard
```

### 문제: 메모리 부족

```bash
# 1. 현재 메모리 사용량 확인
free -h

# 2. 프로세스별 메모리 확인
ps aux --sort=-%mem | head -10

# 3. 캐시 정리
sync && echo 3 > /proc/sys/vm/drop_caches

# 4. 불필요한 로그 삭제
rm -f logs/*.log logs/*.jsonl
```

### 문제: API 키 만료

```bash
# 1. 새 API 키 발급 (Data.go.kr 포털)
# https://www.data.go.kr → 마이페이지 → API 관리

# 2. 환경변수 업데이트
export DATA_GO_KR_API_KEY=NEW_KEY
echo "DATA_GO_KR_API_KEY=NEW_KEY" >> .env

# 3. 서버 재시작
systemctl restart avm-scheduler
```

---

## 정기 유지보수

### 월간 유지보수 체크리스트

```markdown
- [ ] 모든 테스트 실행 (pytest tests/)
- [ ] 대시보드 성능 확인
- [ ] API 응답 시간 측정
- [ ] 모델 정확도 검증
- [ ] 로그 압축 및 보관
- [ ] 백업 확인
- [ ] 보안 업데이트 확인
- [ ] 의존성 버전 확인
```

### 보안 점검

```bash
# 1. .env 파일 권한 확인
ls -la .env
# → -rw------- (600) 이어야 함

# 2. 모델 파일 무결성 확인
sha256sum models/production_model.joblib

# 3. API 키 사용 로그 확인
grep -i "api_key\|error" logs/*.log | head -20

# 4. 접근 로그 확인
tail -100 /var/log/nginx/access.log  # (웹서버 사용 시)
```

### 성능 최적화

```bash
# 1. 느린 쿼리 식별
grep "Time:" logs/*.log | sort -k2 -rn | head -10

# 2. 캐시 효율성 확인
python3 -c "
import json
with open('output/cache_stats.json') as f:
    stats = json.load(f)
hit_rate = stats['hits'] / (stats['hits'] + stats['misses']) * 100
print(f'캐시 적중률: {hit_rate:.1f}%')
"

# 3. 모델 추론 속도 측정
python3 -c "
import time
from scripts.api_server import load_model
model = load_model('production')
X = [[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]]
start = time.time()
for _ in range(100):
    model.predict(X)
elapsed = time.time() - start
print(f'100회 예측: {elapsed:.2f}초 (평균: {elapsed/100*1000:.1f}ms)')
"
```

---

## 📊 주요 메트릭

### 대시보드에서 모니터링할 KPI

| 메트릭 | 목표 | 경고 수준 |
|--------|------|---------|
| 모델 R² | > 0.75 | < 0.73 |
| API 응답 시간 | < 100ms | > 200ms |
| 예측 정확도 | > 85% | < 80% |
| 시스템 가용성 | > 99% | < 95% |
| 캐시 적중률 | > 70% | < 50% |

---

## 🎓 운영팀 교육

### 필수 교육 항목

1. **대시보드 사용법** (30분)
   - 성능 메트릭 해석
   - 알림 확인 방법
   - 리포트 생성

2. **장애 대응** (1시간)
   - 일반적인 문제와 해결책
   - 로그 분석 방법
   - 긴급 연락처

3. **정기 유지보수** (30분)
   - 일일/주간/월간 점검
   - 성능 최적화
   - 보안 관리

---

## 📞 지원 및 문의

| 역할 | 담당자 | 연락처 |
|------|--------|--------|
| 기술 리더 | - | - |
| 개발팀 | - | - |
| 운영팀 | - | - |
| 보안팀 | - | - |

---

**최종 검토**: 2026-06-17  
**승인 상태**: 대기 (운영팀 검토)  
**다음 교육**: 2026-06-24
