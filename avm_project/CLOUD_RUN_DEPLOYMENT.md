# Cloud Run 배포 가이드

AVM API를 Google Cloud Run에 배포하는 단계별 가이드입니다.

## 📋 사전 요구사항

### 1. GCP 계정 및 프로젝트 설정
```bash
# Google Cloud SDK 설치 확인
gcloud --version

# GCP 인증
gcloud auth login

# 프로젝트 설정
gcloud config set project YOUR_PROJECT_ID
export GCP_PROJECT_ID=YOUR_PROJECT_ID
```

### 2. 필수 API 활성화
```bash
# Cloud Run, Container Registry, Cloud Build API 활성화
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### 3. IAM 권한 설정
```bash
# 현재 사용자에게 필요한 역할 부여
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=user:YOUR_EMAIL@example.com \
  --role=roles/run.admin

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=user:YOUR_EMAIL@example.com \
  --role=roles/storage.admin

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=user:YOUR_EMAIL@example.com \
  --role=roles/container.developer
```

## 🚀 배포 방법

### 옵션 1: 자동 배포 스크립트 (권장)

```bash
# 배포 스크립트 실행
cd /home/user/-/avm_project
./deploy_cloudrun.sh
```

**환경 변수 설정:**
```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=asia-northeast1  # 기본값
./deploy_cloudrun.sh
```

### 옵션 2: 단계별 수동 배포

#### Step 1: Docker 이미지 빌드
```bash
cd /home/user/-/avm_project
docker build -t gcr.io/YOUR_PROJECT_ID/avm-api:latest .
```

#### Step 2: Docker 인증 설정
```bash
gcloud auth configure-docker
```

#### Step 3: 이미지를 Container Registry에 푸시
```bash
docker push gcr.io/YOUR_PROJECT_ID/avm-api:latest
```

#### Step 4: Cloud Run에 배포
```bash
gcloud run deploy avm-api \
  --image=gcr.io/YOUR_PROJECT_ID/avm-api:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --timeout=3600 \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO"
```

## ✅ 배포 후 검증

### 1. 서비스 URL 확인
```bash
gcloud run services describe avm-api --region=asia-northeast1 --format='value(status.url)'
```

### 2. 헬스체크
```bash
curl -s https://YOUR_SERVICE_URL/health | jq
```

### 3. API 문서 확인
```
https://YOUR_SERVICE_URL/docs
```

### 4. 로그 확인
```bash
# 최근 50개 로그
gcloud run logs read avm-api --region=asia-northeast1 --limit=50

# 실시간 로그
gcloud run logs read avm-api --region=asia-northeast1 --follow
```

## 📊 모니터링 및 관리

### 메트릭 확인
```bash
# 서비스 상세 정보
gcloud run services describe avm-api --region=asia-northeast1

# 리전 목록
gcloud run services list --region=asia-northeast1
```

### 트래픽 관리
```bash
# 최신 리비전으로 100% 트래픽 설정
gcloud run services update-traffic avm-api \
  --to-revisions LATEST=100 \
  --region=asia-northeast1

# 이전 버전으로 롤백
gcloud run services update-traffic avm-api \
  --to-revisions PREVIOUS=100 \
  --region=asia-northeast1
```

### 자동 스케일링 설정
```bash
# 최대 인스턴스 수 변경
gcloud run services update avm-api \
  --max-instances=50 \
  --region=asia-northeast1

# CPU 상한 설정
gcloud run services update avm-api \
  --cpu=4 \
  --region=asia-northeast1
```

## 🔒 보안 설정

### 인증 추가
```bash
# 인증 요구로 변경
gcloud run services update avm-api \
  --no-allow-unauthenticated \
  --region=asia-northeast1

# 서비스 계정으로 호출 (인증된 요청)
gcloud run services call avm-api --region=asia-northeast1
```

### IAM 정책 설정
```bash
# 특정 사용자만 접근 허용
gcloud run services add-iam-policy-binding avm-api \
  --member=user:user@example.com \
  --role=roles/run.invoker \
  --region=asia-northeast1
```

## 🗑️ 정리

### 서비스 삭제
```bash
gcloud run services delete avm-api \
  --region=asia-northeast1 \
  --quiet
```

### 이미지 삭제
```bash
# Container Registry에서 이미지 삭제
gcloud container images delete gcr.io/YOUR_PROJECT_ID/avm-api:latest \
  --quiet
```

## 📈 성능 최적화

### 권장 설정
| 설정 | 값 | 설명 |
|------|-----|------|
| Memory | 2Gi | 모델 로딩 및 예측에 충분 |
| CPU | 2 | 동시 요청 처리 |
| Max Instances | 10 | 비용 제어 |
| Timeout | 3600s | 배치 처리 대응 |

### 비용 절감 팁
1. **Max Instances 조정**: 불필요한 자동 스케일링 방지
2. **요청 최적화**: 배치 처리로 네트워크 오버헤드 감소
3. **메모리 최적화**: 실제 필요한 만큼 할당 (최소 512Mi)
4. **Always-on 설정 최소화**: 필요시만 활성화

## 🐛 트러블슈팅

### 배포 실패
```bash
# 상세 오류 확인
gcloud run deploy avm-api \
  --image=gcr.io/YOUR_PROJECT_ID/avm-api:latest \
  --region=asia-northeast1 \
  --debug
```

### 이미지 로드 실패
```bash
# Container Registry 권한 확인
gcloud container images describe gcr.io/YOUR_PROJECT_ID/avm-api:latest

# 이미지 재구성
docker build -t gcr.io/YOUR_PROJECT_ID/avm-api:latest .
docker push gcr.io/YOUR_PROJECT_ID/avm-api:latest
```

### 헬스체크 실패
```bash
# 로그에서 에러 확인
gcloud run logs read avm-api --region=asia-northeast1

# 포트 확인 (반드시 8000)
# 환경 변수 확인
gcloud run services describe avm-api --region=asia-northeast1
```

## 📚 참고 자료

- [Google Cloud Run 문서](https://cloud.google.com/run/docs)
- [Cloud Run 가격](https://cloud.google.com/run/pricing)
- [FastAPI Docker 배포](https://fastapi.tiangolo.com/deployment/docker/)

---

**마지막 업데이트**: 2026-06-15
**배포 상태**: ✅ 준비 완료
