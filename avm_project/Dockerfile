FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY scripts/ ./scripts/
COPY config/  ./config/
COPY output/trained_models/ ./output/trained_models/
COPY output/models_ir/      ./output/models_ir/

ENV PYTHONPATH=/app
ENV AVM_CONFIG=/app/config/avm_config.json

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
    || exit 1

CMD ["uvicorn", "scripts.avm_api_service:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--log-level", "info"]
