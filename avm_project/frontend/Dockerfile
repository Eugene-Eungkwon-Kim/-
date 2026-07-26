# ============================================================
# AVM Dashboard Frontend (Next.js 14)
# 빌드 컨텍스트: avm_project/frontend/  (이 디렉토리)
#   docker build -t avm-frontend .
# ============================================================
FROM node:20-alpine

WORKDIR /app

# 클라이언트 번들에 인라인되는 API 주소 (빌드 시점에 주입)
# 브라우저는 호스트에서 실행되므로 기본값은 localhost:8000
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

# 1) 의존성 설치 (lock 파일이 있으면 우선 사용)
COPY package.json package-lock.json* ./
RUN npm install

# 2) 소스 복사 후 프로덕션 빌드
COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
