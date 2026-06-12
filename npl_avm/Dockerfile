# Multi-stage build: Builder
FROM python:3.12-slim as builder

WORKDIR /tmp

# 의존성 설치
COPY requirements.txt .
RUN python -m pip install --user --no-cache-dir -r requirements.txt

# ===== Runtime Stage =====
FROM python:3.12-slim

WORKDIR /app

# 보안 업데이트
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Builder에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local

# 환경 변수
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 애플리케이션 코드 복사
COPY scripts/ /app/scripts/
COPY models/ /app/models/
COPY data/ /app/data/
COPY app.py /app/

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=2)" || exit 1

# 비root 사용자로 실행 (보안)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000 9090

# 시작 스크립트
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
