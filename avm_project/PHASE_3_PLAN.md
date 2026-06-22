# 🚀 Phase 3: 병렬 실행 - 데이터 연동 + 배포 준비

**시작일:** 2026-06-19  
**예상 완료:** 2026-07-17 (4주)  
**목표:** Phase D-2 + Phase 2 통합 + 실제 데이터 + 배포 준비

---

## 📋 Phase 3 목표

### 1단계: 데이터 연동 (1주)
```
✅ real_estate_2024.csv 연동
✅ FastAPI에서 데이터 로드
✅ 대시보드에 실제 데이터 표시
✅ 모델 파일 로드
```

### 2단계: 시스템 통합 (1주)
```
✅ Phase D-2 스케줄러 통합
✅ 재학습 상태 실시간 모니터링
✅ 성능 메트릭 실시간 업데이트
✅ 알림 시스템 연동
```

### 3단계: 배포 준비 (1주)
```
✅ Docker 이미지 생성
✅ Google Cloud Run 설정
✅ 환경 변수 설정
✅ CI/CD 파이프라인
```

### 4단계: 테스트 & 최적화 (1주)
```
✅ E2E 테스트
✅ 성능 테스트
✅ 보안 감사
✅ 브라우저 호환성
```

---

## 📂 Phase 3 구현 계획

### A. 데이터 연동 모듈

**File: `backend/models.py`**
```python
# Pydantic 모델 정의
from pydantic import BaseModel
from datetime import datetime

class DashboardData(BaseModel):
    ensemble_r2: float
    ensemble_rmse: float
    ensemble_mae: float
    last_updated: datetime
    model_status: str

class ModelPerformance(BaseModel):
    model_id: str
    r2: float
    rmse: float
    mae: float
    training_date: datetime
    data_points: int
```

**File: `backend/database.py`**
```python
# 데이터베이스 연동
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "avm_project" / "data" / "raw"

def load_real_estate_data():
    """부동산 데이터 로드"""
    csv_path = DATA_DIR / "real_estate_2024.csv"
    df = pd.read_csv(csv_path)
    return df

def get_data_quality_metrics():
    """데이터 품질 메트릭"""
    df = load_real_estate_data()
    return {
        "total_rows": len(df),
        "missing_values": df.isnull().sum().sum(),
        "missing_percentage": (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
        "quality_score": 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
    }
```

### B. 모델 로드 및 예측

**File: `backend/ml_models.py`**
```python
# 모델 로드 및 예측
import joblib
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "avm_project" / "models"

class ModelManager:
    def __init__(self):
        self.models = {}
        self.load_models()
    
    def load_models(self):
        """저장된 모델들 로드"""
        for model_file in MODEL_DIR.glob("*.joblib"):
            model_name = model_file.stem
            self.models[model_name] = joblib.load(model_file)
    
    def get_model(self, model_id: str):
        """특정 모델 조회"""
        return self.models.get(model_id)
    
    def make_prediction(self, model_id: str, features: dict):
        """예측 수행"""
        model = self.get_model(model_id)
        if model:
            return model.predict([list(features.values())])
        return None

model_manager = ModelManager()
```

### C. WebSocket 실시간 업데이트

**File: `backend/websocket.py`**
```python
# WebSocket을 통한 실시간 업데이트
from fastapi import WebSocket
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({
                "type": "update",
                "data": json.loads(data)
            })
    except Exception as e:
        manager.disconnect(websocket)
```

### D. 재학습 상태 모니터링

**File: `backend/retraining_monitor.py`**
```python
# Phase D-2와 통합
import json
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path(__file__).parent.parent / "avm_project" / "logs" / "retrain_history.jsonl"

def get_latest_training():
    """최신 재학습 결과 조회"""
    if not HISTORY_FILE.exists():
        return None
    
    with open(HISTORY_FILE, 'r') as f:
        lines = f.readlines()
        if lines:
            return json.loads(lines[-1])
    return None

def get_training_history(limit: int = 10):
    """재학습 이력 조회"""
    if not HISTORY_FILE.exists():
        return []
    
    history = []
    with open(HISTORY_FILE, 'r') as f:
        for line in f:
            history.append(json.loads(line))
    
    return history[-limit:]

@app.get("/dashboard/live-metrics")
async def get_live_metrics():
    """실시간 메트릭 (Phase D-2 연동)"""
    latest = get_latest_training()
    if latest:
        return {
            "ensemble": latest.get("ensemble", {}),
            "models": latest.get("models", {}),
            "status": latest.get("status", "unknown"),
            "timestamp": latest.get("timestamp")
        }
    return {"status": "no-data"}
```

### E. 프론트엔드 실시간 업데이트

**File: `frontend/hooks/useRealtimeData.ts`**
```typescript
'use client'

import { useEffect, useState } from 'react'

export function useRealtimeData() {
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    // WebSocket 연결
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(
      `${protocol}//localhost:8000/ws/dashboard`
    )

    ws.onopen = () => {
      setConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      setData(message.data)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnected(false)
    }

    ws.onclose = () => {
      setConnected(false)
      console.log('WebSocket disconnected')
    }

    return () => ws.close()
  }, [])

  return { data, connected }
}
```

---

## 🐳 Docker & 배포

### File: `Dockerfile`
```dockerfile
# Frontend 빌드
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Backend
FROM python:3.11-slim
WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프론트엔드 빌드 결과 복사
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# 애플리케이션
COPY backend/ ./backend/
COPY avm_project/ ./avm_project/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### File: `docker-compose.yml`
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:///./avm.db
    volumes:
      - ./avm_project:/app/avm_project

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api
```

### File: `cloudbuild.yaml` (Google Cloud Build)
```yaml
steps:
  # Step 1: Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: 
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/avm-dashboard:$SHORT_SHA'
      - '.'

  # Step 2: Push to Google Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/avm-dashboard:$SHORT_SHA'

  # Step 3: Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args:
      - run
      - --service_account=cloud-run-deployer
      - --image=gcr.io/$PROJECT_ID/avm-dashboard:$SHORT_SHA
      - --service_name=avm-dashboard
      - --region=asia-northeast1

images:
  - 'gcr.io/$PROJECT_ID/avm-dashboard:$SHORT_SHA'
```

---

## 🔄 CI/CD 파이프라인

### File: `.github/workflows/deploy.yml`
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd frontend && npm install
          cd ../backend && pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd frontend && npm run test
          cd ../backend && python -m pytest
      
      - name: Build Docker image
        run: docker build -t avm-dashboard:latest .
      
      - name: Push to Google Container Registry
        run: |
          docker tag avm-dashboard:latest gcr.io/${{ secrets.GCP_PROJECT_ID }}/avm-dashboard:latest
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/avm-dashboard:latest
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy avm-dashboard \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/avm-dashboard:latest \
            --platform managed \
            --region asia-northeast1 \
            --allow-unauthenticated
```

---

## 📊 테스트 계획

### Frontend 테스트
```bash
# Jest 단위 테스트
npm run test

# E2E 테스트 (Playwright)
npm run test:e2e

# 성능 테스트 (Lighthouse)
npm run test:lighthouse
```

### Backend 테스트
```bash
# Pytest 단위 테스트
pytest tests/

# 통합 테스트
pytest tests/integration/

# API 테스트
pytest tests/api/
```

---

## 📈 모니터링 & 로깅

### Application Insights
```python
# backend/monitoring.py
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

handler = AzureLogHandler(connection_string="InstrumentationKey=...")
logging.getLogger(__name__).addHandler(handler)
```

### Google Cloud Logging
```python
# 자동으로 Cloud Logging에 기록
import logging

logging.basicConfig(level=logging.INFO)
```

---

## ✅ Phase 3 체크리스트

### 1주차: 데이터 연동
- [ ] `backend/models.py` 작성
- [ ] `backend/database.py` 작성
- [ ] 실제 CSV 데이터 로드 테스트
- [ ] 대시보드에 실제 데이터 표시
- [ ] 모델 파일 로드 확인

### 2주차: 시스템 통합
- [ ] `backend/ml_models.py` 작성
- [ ] `backend/retraining_monitor.py` 작성
- [ ] Phase D-2 통합 테스트
- [ ] 실시간 모니터링 구현
- [ ] WebSocket 연동

### 3주차: 배포 준비
- [ ] `Dockerfile` 작성
- [ ] `docker-compose.yml` 작성
- [ ] `cloudbuild.yaml` 작성
- [ ] Google Cloud 프로젝트 설정
- [ ] 환경 변수 관리

### 4주차: 테스트 & 배포
- [ ] 단위 테스트 작성
- [ ] E2E 테스트 작성
- [ ] 성능 최적화
- [ ] 보안 감사
- [ ] Google Cloud Run 배포

---

## 🎯 최종 목표

```
✅ Phase D-2 (자동화) + Phase 2 (대시보드) 통합
✅ 실제 데이터 기반 실시간 모니터링
✅ 모든 기능이 자동으로 동작하는 시스템
✅ Google Cloud Run에서 24/7 실행
✅ 주간 자동 재학습 + 대시보드 자동 업데이트
✅ 프로덕션급 안정성과 성능
```

---

**다음 진행:**
1. 데이터 연동 모듈 작성
2. FastAPI 엔드포인트 확장
3. 프론트엔드 실시간 업데이트
4. Docker 빌드 및 테스트
5. Google Cloud Run 배포

**예상 완료:** 2026-07-17  
**상태:** Phase 3 시작 준비
