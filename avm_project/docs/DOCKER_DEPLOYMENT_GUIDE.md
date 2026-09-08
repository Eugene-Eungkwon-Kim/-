# Docker 배포 가이드

**버전:** 1.0.0  
**상태:** Production Ready ✅  
**사전 요구사항:** Docker & Docker Compose

---

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [Dockerfile 설명](#dockerfile-설명)
3. [docker-compose 설명](#docker-compose-설명)
4. [로컬 배포](#로컬-배포)
5. [클라우드 배포](#클라우드-배포)
6. [모니터링 & 로깅](#모니터링--로깅)
7. [트러블슈팅](#트러블슈팅)

---

## 🚀 빠른 시작

### 필수 설치
```bash
# macOS
brew install docker docker-compose

# Ubuntu
sudo apt-get install docker.io docker-compose

# Windows
# Docker Desktop 다운로드: https://www.docker.com/products/docker-desktop
```

### 1단계: Docker 이미지 빌드
```bash
cd avm_project
docker build -t avm-api:1.0 .
```

### 2단계: 컨테이너 실행 (docker-compose)
```bash
docker-compose up -d
```

### 3단계: 서버 확인
```bash
# 헬스체크
curl http://localhost:8000/health

# API 문서
http://localhost:8000/docs
```

### 4단계: 컨테이너 중지
```bash
docker-compose down
```

---

## 📄 Dockerfile 설명

```dockerfile
FROM python:3.11-slim
```
- **Python 3.11** 기반 이미지
- **slim** 태그: 불필요한 패키지 제외로 이미지 크기 최소화
- **최종 이미지 크기:** ~500MB

```dockerfile
WORKDIR /app
```
- 컨테이너 내 작업 디렉토리 설정

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gcc
```
- 컴파일러 설치 (일부 Python 패키지 필요)
- `--no-install-recommends`: 불필요한 패키지 제외

```dockerfile
COPY avm_project/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- Python 의존성 설치
- `--no-cache-dir`: pip 캐시 제외로 이미지 크기 감소

```dockerfile
COPY avm_project/ ./avm_project/
```
- 애플리케이션 코드 복사

```dockerfile
EXPOSE 8000
```
- 포트 8000 노출

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```
- **30초마다** 헬스체크
- **10초 이내**에 응답 필요
- **5초** 대기 후 첫 체크 시작
- **3회** 실패 시 컨테이너 재시작

```dockerfile
CMD ["python", "-m", "uvicorn", "avm_project.scripts.api_server:app", ...]
```
- FastAPI 애플리케이션 시작

---

## 🐳 docker-compose 설명

```yaml
version: '3.8'
```
- Docker Compose API 버전

```yaml
services:
  avm-api:
    build:
      context: .
      dockerfile: Dockerfile
```
- 현재 디렉토리의 Dockerfile로 이미지 빌드

```yaml
container_name: avm-api-server
ports:
  - "8000:8000"
```
- 컨테이너 이름 지정
- 로컬 8000 → 컨테이너 8000 포트 매핑

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - LOG_LEVEL=info
```
- Python 버퍼링 비활성화 (로그 실시간 출력)
- 로그 레벨 설정

```yaml
volumes:
  - ./avm_project/models:/app/avm_project/models:ro
  - ./avm_project/data:/app/avm_project/data:ro
  - ./avm_project/logs:/app/avm_project/logs
```
- 로컬 디렉토리를 컨테이너와 공유
- `ro`: 읽기 전용 마운트 (모델, 데이터)
- 로그는 쓰기 가능

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```
- 30초마다 헬스체크
- 10초 타임아웃
- 3회 연속 실패 시 unhealthy 표시

```yaml
restart: unless-stopped
```
- 컨테이너 충돌 시 자동 재시작
- `docker-compose down`으로만 중지 가능

```yaml
networks:
  avm-network:
    driver: bridge
```
- 사용자 정의 네트워크 생성
- 향후 여러 컨테이너 연결 가능

---

## 🏠 로컬 배포

### 기본 사용법

#### 시작
```bash
cd avm_project
docker-compose up
```

#### 백그라운드 실행
```bash
docker-compose up -d
```

#### 로그 확인
```bash
docker-compose logs -f avm-api
```

#### 컨테이너 상태 확인
```bash
docker-compose ps
```

#### 중지
```bash
docker-compose down
```

### 이미지 빌드만 (실행 안함)
```bash
docker-compose build
```

### 강제 재빌드 (캐시 무시)
```bash
docker-compose build --no-cache
```

### 특정 로그 라인 수만 출력
```bash
docker-compose logs --tail=50 avm-api
```

---

## 🌍 클라우드 배포

### 1. Google Cloud Run (권장) ⭐

#### 단계별 가이드

**1단계: Artifact Registry에 이미지 푸시**
```bash
# 설정
PROJECT_ID="your-project-id"
REGION="us-central1"
IMAGE_NAME="avm-api"

# 인증
gcloud auth configure-docker $REGION-docker.pkg.dev

# 이미지 빌드
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest .

# 이미지 푸시
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest
```

**2단계: Cloud Run 배포**
```bash
gcloud run deploy avm-api \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest \
  --platform managed \
  --region $REGION \
  --port 8000 \
  --allow-unauthenticated \
  --set-env-vars "LOG_LEVEL=info"
```

**3단계: 배포 확인**
```bash
gcloud run services describe avm-api --region $REGION
```

**장점:**
- 완전 관리형 서비스
- 자동 스케일링 (0에서 무제한)
- 사용한 시간만 비용 청구
- SSL/HTTPS 자동 처리
- 빠른 배포

**비용:** 월 ~$0.4 (무료 크레딧 포함)

---

### 2. AWS Elastic Container Service (ECS)

#### 단계별 가이드

**1단계: ECR에 이미지 푸시**
```bash
# AWS CLI 설정
aws configure

# ECR 저장소 생성
aws ecr create-repository --repository-name avm-api

# 인증
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# 이미지 빌드 및 푸시
docker build -t avm-api:latest .
docker tag avm-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/avm-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/avm-api:latest
```

**2단계: ECS 작업 정의 생성**
```json
{
  "family": "avm-api",
  "containerDefinitions": [
    {
      "name": "avm-api",
      "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/avm-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/avm-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**3단계: ECS 서비스 생성**
```bash
aws ecs create-service \
  --cluster default \
  --service-name avm-api \
  --task-definition avm-api \
  --desired-count 1
```

**장점:**
- AWS 생태계 통합
- EC2 또는 Fargate 옵션
- 로드 밸런싱
- 자동 스케일링

**비용:** Fargate ~$10-15/월

---

### 3. Azure Container Instances (ACI)

```bash
# 이미지 푸시
az acr build --registry <acr-name> --image avm-api:latest .

# 컨테이너 배포
az container create \
  --resource-group myResourceGroup \
  --name avm-api-container \
  --image <acr-name>.azurecr.io/avm-api:latest \
  --cpu 1 \
  --memory 1 \
  --port 8000 \
  --protocol TCP
```

---

## 🔍 모니터링 & 로깅

### 컨테이너 상태 모니터링
```bash
# 실시간 CPU/메모리 사용량
docker stats avm-api-server

# 컨테이너 상세 정보
docker inspect avm-api-server

# 헬스 상태 확인
docker inspect --format='{{.State.Health.Status}}' avm-api-server
```

### 로그 확인
```bash
# 전체 로그
docker-compose logs avm-api

# 실시간 로그 (tail)
docker-compose logs -f avm-api

# 마지막 100줄
docker-compose logs --tail=100 avm-api

# 타임스탬프 포함
docker-compose logs --timestamps avm-api
```

### 이미지 크기 확인
```bash
docker images | grep avm-api
```

**예상 이미지 크기:**
```
avm-api:latest    ~500MB (slim 기반)
avm-api:1.0       ~500MB
```

---

## 🐛 트러블슈팅

### 1. 포트 이미 사용 중
```bash
# 포트 사용 프로세스 찾기
lsof -i :8000

# 다른 포트 사용
docker-compose down
# docker-compose.yml 수정: ports: "9000:8000"
docker-compose up
```

### 2. 메모리 부족
```bash
# 컨테이너 메모리 제한 확인
docker inspect avm-api-server | grep -i memory

# docker-compose.yml에 제한 추가
services:
  avm-api:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

### 3. 헬스체크 실패
```bash
# 수동 헬스체크
curl -v http://localhost:8000/health

# 로그에서 에러 확인
docker-compose logs avm-api
```

### 4. 이미지 빌드 실패
```bash
# 캐시 제거하고 재빌드
docker-compose build --no-cache

# 매우 상세한 로그
docker-compose build --verbose
```

### 5. 컨테이너 자동 재시작 안됨
```bash
# 재시작 정책 확인
docker inspect avm-api-server | grep -i "RestartPolicy"

# 수동 재시작
docker restart avm-api-server
```

---

## 📊 성능 최적화

### 1. 이미지 크기 최소화 ✅
```dockerfile
FROM python:3.11-slim  # 일반 python:3.11은 900MB+
RUN pip install --no-cache-dir  # 캐시 제외
```

### 2. 멀티스테이지 빌드 (선택)
```dockerfile
# Stage 1: 빌드
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: 실행
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

### 3. 캐싱 활용
```dockerfile
# requirements.txt를 먼저 복사 (변경 빈번도 낮음)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드는 나중에 복사 (자주 변경)
COPY avm_project/ ./avm_project/
```

---

## 📈 프로덕션 체크리스트

- [x] Dockerfile 최적화 ✅
- [x] Health check 설정 ✅
- [x] 환경 변수 설정 ✅
- [x] 로그 설정 ✅
- [x] 볼륨 마운트 ✅
- [x] 네트워크 설정 ✅
- [ ] SSL/HTTPS (클라우드에서 자동 처리)
- [ ] 로드 밸런싱 (다중 인스턴스)
- [ ] 모니터링 (Prometheus, DataDog)
- [ ] 로그 수집 (ELK, CloudWatch)

---

## 🎯 다음 단계

1. **로컬 테스트**: `docker-compose up`
2. **클라우드 선택**: GCP Cloud Run (권장)
3. **이미지 푸시**: 컨테이너 레지스트리
4. **서비스 배포**: 클라우드 플랫폼
5. **모니터링 설정**: 헬스 확인 및 알림

---

## 📞 참고 링크

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 레퍼런스](https://docs.docker.com/compose/compose-file/)
- [Google Cloud Run](https://cloud.google.com/run)
- [AWS ECS](https://aws.amazon.com/ecs/)
- [Azure Container Instances](https://azure.microsoft.com/services/container-instances/)

---

**마지막 업데이트:** 2026-06-12  
**상태:** Production Ready ✅
