# ============================================================
# AVM Dashboard Backend (FastAPI + ML 모델 서빙)
# 빌드 컨텍스트: avm_project/  (이 디렉토리)
#   docker build -f Dockerfile -t avm-backend .
# ============================================================
FROM python:3.11-slim

# 런타임 의존성:
#  - libgomp1: lightgbm / xgboost 가 OpenMP 런타임을 요구
#  - curl:     HEALTHCHECK 용
#  - gcc/g++:  일부 패키지의 소스 빌드 대비
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) 의존성 먼저 설치 (소스 변경 시에도 레이어 캐시 재사용)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 2) 프로젝트 코드 + 모델 + 데이터 + 설정 복사
#    (.dockerignore 가 frontend/, docs/, 캐시 등을 제외)
COPY . .

# 3) 비루트 사용자로 실행
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 모델 로딩에 수 초가 걸리므로 start-period 를 넉넉히 둔다
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# backend/__init__.py 가 있어 backend 는 정식 패키지 → backend.main:app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
