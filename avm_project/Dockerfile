FROM python:3.11-slim@sha256:6b0f2ed4e96ff2dd2e8076b7a4bfa4d6eda7d2a4a5e2b3d4e5c5c5c5c5c5c5c

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY avm_project/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY avm_project/ ./avm_project/

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "avm_project.scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
