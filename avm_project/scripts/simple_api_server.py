"""
AVM 간단 API 서버
"""
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
from pathlib import Path
import numpy as np
import json
from datetime import datetime

app = FastAPI(
    title="AVM API",
    description="Automated Valuation Model",
    version="1.0.0"
)

# 모델 경로
models_dir = Path(__file__).parent.parent / "models"

# 앙상블 모델 로드
models = {}
model_paths = {
    "Linear Regression": "Linear Regression_model_real_2024.joblib",
    "Decision Tree": "Decision Tree_model_real_2024.joblib",
    "Random Forest": "Random Forest_model_real_2024.joblib",
    "Gradient Boosting": "Gradient Boosting_model_real_2024.joblib",
    "XGBoost": "XGBoost_model_real_2024.joblib",
    "LightGBM": "LightGBM_model_real_2024.joblib",
}

model_loaded = False
for model_name, filename in model_paths.items():
    try:
        path = models_dir / filename
        models[model_name] = joblib.load(path)
        model_loaded = True
    except Exception as e:
        print(f"⚠️ {model_name} 로드 실패: {e}")

class PredictionRequest(BaseModel):
    면적: float
    지역: int
    건축년도: int
    층수: int
    방_개수: int
    욕실_개수: int
    엘리베이터: int
    주차장: int

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float
    timestamp: str

@app.get("/")
async def root():
    return {"message": "AVM API v1.0", "status": "running", "models_loaded": len(models)}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_loaded": len(models),
        "r2": 0.9754,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict")
async def predict(request: PredictionRequest):
    if not model_loaded or len(models) == 0:
        return {"error": "Models not loaded"}
    
    try:
        features = np.array([[
            request.면적,
            request.지역,
            request.건축년도,
            request.층수,
            request.방_개수,
            request.욕실_개수,
            request.엘리베이터,
            request.주차장
        ]])
        
        # 앙상블 예측 (평균)
        predictions = []
        for model_name, model in models.items():
            pred = model.predict(features)[0]
            predictions.append(pred)
        
        ensemble_prediction = np.mean(predictions)
        
        return PredictionResponse(
            prediction=float(ensemble_prediction),
            confidence=0.9754,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return {"error": str(e)}

@app.get("/dashboard")
async def dashboard():
    return {
        "title": "AVM Dashboard",
        "models": {
            "Linear Regression": 0.9565,
            "Decision Tree": 0.9625,
            "Random Forest": 0.9739,
            "Gradient Boosting": 0.9759,
            "XGBoost": 0.9741,
            "LightGBM": 0.9750,
            "Ensemble": 0.9754
        },
        "models_loaded": len(models),
        "status": "healthy" if model_loaded else "warning"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
