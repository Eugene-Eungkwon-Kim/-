#!/bin/bash
#
# Cloud Run 배포 스크립트
# AVM API를 Google Cloud Run에 배포합니다
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
PROJECT_ID="${GCP_PROJECT_ID:-avm-korean-realestate}"
SERVICE_NAME="avm-api"
REGION="${GCP_REGION:-asia-northeast1}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
TAG=$(date +%Y%m%d_%H%M%S)
IMAGE_TAG="${IMAGE_NAME}:${TAG}"
IMAGE_LATEST="${IMAGE_NAME}:latest"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 AVM API Cloud Run 배포${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# 1. GCP 프로젝트 설정 확인
echo -e "\n${YELLOW}📋 Step 1: GCP 설정 확인${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI가 설치되어 있지 않습니다${NC}"
    echo "다음 명령으로 설치하세요: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ gcloud CLI 설치 확인"

# 2. 인증 확인
echo -e "\n${YELLOW}📋 Step 2: GCP 인증 확인${NC}"
if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "${RED}❌ GCP 인증이 필요합니다${NC}"
    echo "다음 명령을 실행하세요: gcloud auth application-default login"
    exit 1
fi

echo "✅ GCP 인증 확인"

# 3. Docker 이미지 빌드
echo -e "\n${YELLOW}📋 Step 3: Docker 이미지 빌드${NC}"
echo "이미지: ${IMAGE_TAG}"

if docker build -t "${IMAGE_TAG}" -t "${IMAGE_LATEST}" -f Dockerfile .; then
    echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"
else
    echo -e "${RED}❌ Docker 이미지 빌드 실패${NC}"
    exit 1
fi

# 4. Docker 이미지 레지스트리에 푸시
echo -e "\n${YELLOW}📋 Step 4: Docker 이미지 푸시 (Google Container Registry)${NC}"

# gcloud auth configure-docker
if gcloud auth configure-docker --quiet 2>/dev/null; then
    echo "✅ Docker 인증 구성"
fi

if docker push "${IMAGE_TAG}"; then
    echo -e "${GREEN}✅ 이미지 푸시 완료: ${IMAGE_TAG}${NC}"
else
    echo -e "${RED}❌ 이미지 푸시 실패${NC}"
    exit 1
fi

if docker push "${IMAGE_LATEST}"; then
    echo -e "${GREEN}✅ 최신 태그 푸시: ${IMAGE_LATEST}${NC}"
else
    echo -e "${YELLOW}⚠️  최신 태그 푸시 실패 (선택사항)${NC}"
fi

# 5. Cloud Run에 배포
echo -e "\n${YELLOW}📋 Step 5: Cloud Run 배포${NC}"
echo "서비스: ${SERVICE_NAME}"
echo "리전: ${REGION}"
echo "이미지: ${IMAGE_TAG}"

# 서비스가 이미 존재하는지 확인
if gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" &>/dev/null 2>&1; then
    echo "기존 서비스 업데이트 중..."
    if gcloud run deploy "${SERVICE_NAME}" \
        --image="${IMAGE_TAG}" \
        --region="${REGION}" \
        --platform="managed" \
        --allow-unauthenticated \
        --port=8000 \
        --memory=2Gi \
        --cpu=2 \
        --max-instances=10 \
        --timeout=3600 \
        --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
        --no-gen2; then
        echo -e "${GREEN}✅ Cloud Run 업데이트 완료${NC}"
    else
        echo -e "${RED}❌ Cloud Run 업데이트 실패${NC}"
        exit 1
    fi
else
    echo "새로운 서비스 생성 중..."
    if gcloud run deploy "${SERVICE_NAME}" \
        --image="${IMAGE_TAG}" \
        --region="${REGION}" \
        --platform="managed" \
        --allow-unauthenticated \
        --port=8000 \
        --memory=2Gi \
        --cpu=2 \
        --max-instances=10 \
        --timeout=3600 \
        --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
        --no-gen2; then
        echo -e "${GREEN}✅ Cloud Run 배포 완료${NC}"
    else
        echo -e "${RED}❌ Cloud Run 배포 실패${NC}"
        exit 1
    fi
fi

# 6. 배포된 서비스 URL 조회
echo -e "\n${YELLOW}📋 Step 6: 배포 완료 정보${NC}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --format='value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${YELLOW}⚠️  서비스 URL을 가져올 수 없습니다${NC}"
else
    echo -e "${GREEN}✅ 서비스 배포 성공${NC}"
    echo -e "${BLUE}🌐 API URL: ${SERVICE_URL}${NC}"
    echo -e "${BLUE}📊 헬스체크: ${SERVICE_URL}/health${NC}"
    echo -e "${BLUE}📚 API 문서: ${SERVICE_URL}/docs${NC}"
fi

# 7. 배포 정보 저장
echo -e "\n${YELLOW}📋 Step 7: 배포 정보 저장${NC}"

DEPLOY_INFO=$(cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "service_name": "${SERVICE_NAME}",
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "image": "${IMAGE_TAG}",
  "service_url": "${SERVICE_URL}",
  "status": "deployed"
}
EOF
)

echo "$DEPLOY_INFO" | tee "deploy_info_${TAG}.json"
echo -e "${GREEN}✅ 배포 정보 저장: deploy_info_${TAG}.json${NC}"

# 8. 배포 후 테스트
echo -e "\n${YELLOW}📋 Step 8: 배포 후 헬스체크${NC}"

if [ -n "$SERVICE_URL" ]; then
    echo "헬스체크 URL: ${SERVICE_URL}/health"
    sleep 5  # 서비스 시작 대기

    if curl -s -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 헬스체크 성공${NC}"
    else
        echo -e "${YELLOW}⚠️  헬스체크 실패 (잠시 후 다시 시도)${NC}"
        sleep 10
        if curl -s -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 헬스체크 성공 (재시도)${NC}"
        else
            echo -e "${YELLOW}⚠️  헬스체크 여전히 실패 (서비스 시작 중)${NC}"
        fi
    fi
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# 추가 명령어
cat <<EOF

📝 배포 후 유용한 명령어:

# 로그 확인
gcloud run logs read ${SERVICE_NAME} --region=${REGION} --limit=50

# 메트릭 확인
gcloud run services describe ${SERVICE_NAME} --region=${REGION}

# 서비스 삭제 (필요시)
gcloud run services delete ${SERVICE_NAME} --region=${REGION}

# 트래픽 설정
gcloud run services update-traffic ${SERVICE_NAME} --to-revisions LATEST=100 --region=${REGION}

EOF

exit 0
