# PHASE 1: Cloud Run 배포 로컬 실행 가이드

**상태**: 배포 준비 100% 완료, 로컬 실행 필요  
**예상 시간**: 1-2시간  
**필수 환경**: GCP 계정, gcloud CLI, Docker

---

## 🚀 로컬 환경에서 배포 실행

### Step 1: 사전 준비 (30분)

#### 1-1. gcloud CLI 설치
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Windows
다운로드: https://cloud.google.com/sdk/docs/install-sdk
```

#### 1-2. GCP 인증
```bash
# GCP 계정으로 인증
gcloud auth application-default login

# 또는 서비스 계정 사용
gcloud auth activate-service-account --key-file=service-account.json

# 프로젝트 설정
gcloud config set project avm-korean-realestate
```

#### 1-3. 필수 API 활성화
```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 2: 배포 실행 (5분)

```bash
# 프로젝트 디렉토리로 이동
cd /home/user/-/avm_project

# 배포 환경 변수 설정
export GCP_PROJECT_ID=avm-korean-realestate
export GCP_REGION=asia-northeast1

# 자동 배포 스크립트 실행
bash deploy_cloudrun.sh
```

**배포 스크립트가 자동으로 처리하는 작업:**
1. ✅ Docker 이미지 빌드 (gcr.io/avm-korean-realestate/avm-api:latest)
2. ✅ Container Registry 푸시
3. ✅ Cloud Run 서비스 배포 (2 CPU, 2GB RAM)
4. ✅ 헬스체크 수행
5. ✅ 서비스 URL 출력

### Step 3: 배포 검증 (45분)

```bash
# 서비스 URL 확인
SERVICE_URL=$(gcloud run services describe avm-api \
  --region=asia-northeast1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# 헬스체크
curl -s $SERVICE_URL/health | jq

# API 문서 확인
echo "API Docs: $SERVICE_URL/docs"

# 샘플 예측 테스트
curl -X POST $SERVICE_URL/predict \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "APT",
    "area_sqm": 85.5,
    "year_built": 2020,
    "condition": "GOOD",
    "region": "SEOUL",
    "district": "GANGNAM"
  }'
```

---

## 📊 배포 후 단계

### PHASE 2: AUTO-LOOP 자동화 활성화

배포 완료 후 자동화를 활성화하세요:

```bash
# 1. Cron 설정
crontab -e

# 다음을 추가:
0 10 * * 4 python scripts/avm_injection_engine.py >> /var/log/avm/automation.log 2>&1
20 10 * * 4 cd /home/user/-/avm_project && gcloud run deploy avm-api --update-image >> /var/log/avm/automation.log 2>&1

# 2. 로그 디렉토리 생성
mkdir -p /var/log/avm

# 3. Cron 작업 확인
crontab -l
```

### PHASE 3: 모니터링 설정

```bash
# Cloud Console에서 메트릭 대시보드 설정
gcloud monitoring dashboards create --config-from-file=monitoring-config.yaml

# 알람 설정
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="AVM API Error Rate"
```

---

## 🐛 문제 해결

### Docker 빌드 실패
```bash
# Docker 이미지 수동 빌드
docker build -t gcr.io/avm-korean-realestate/avm-api:latest .

# Container Registry 인증
gcloud auth configure-docker

# 이미지 푸시
docker push gcr.io/avm-korean-realestate/avm-api:latest
```

### 배포 실패
```bash
# 상세 로그 확인
gcloud run deploy avm-api \
  --region=asia-northeast1 \
  --debug

# 서비스 로그 확인
gcloud run logs read avm-api --limit=50
```

### 헬스체크 실패
```bash
# 서비스 상태 확인
gcloud run services describe avm-api --region=asia-northeast1

# 환경 변수 확인
gcloud run services describe avm-api --region=asia-northeast1 --format='value(spec.template.spec.containers[0].env)'
```

---

## ✅ 배포 완료 체크리스트

- [ ] gcloud CLI 설치 및 인증 완료
- [ ] 필수 API 활성화 확인
- [ ] deploy_cloudrun.sh 실행 완료
- [ ] 서비스 URL 획득 성공
- [ ] GET /health → 200 OK
- [ ] POST /predict → 예측값 반환
- [ ] Swagger 문서 로드 성공
- [ ] AUTO-LOOP 설정 완료

---

## 📞 배포 후 지원

**API 문서**: https://SERVICE_URL/docs  
**Cloud Run 콘솔**: https://console.cloud.google.com/run  
**로그 확인**: `gcloud run logs read avm-api --limit=50`

---

**배포 준비 완료 상태**: ✅  
**예상 배포 시간**: 1-2시간  
**운영 시작**: 배포 직후 즉시 가능

