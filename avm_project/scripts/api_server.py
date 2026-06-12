"""
AVM 프로젝트 - FastAPI 웹 서버
REST API for Automated Valuation Model Predictions

실행: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="AVM API",
    description="자동감정가 모델 (Automated Valuation Model) REST API",
    version="1.0.0"
)

# CORS 설정 (모든 출처에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

# 로드된 모델 캐시
loaded_models = {}
model_metadata = {
    'linear_regression': {'name': 'Linear Regression', 'r2': 1.0000, 'status': 'perfect_fit'},
    'random_forest': {'name': 'Random Forest', 'r2': 0.9717, 'status': 'production'},
    'gradient_boosting': {'name': 'Gradient Boosting', 'r2': 0.9683, 'status': 'production'},
    'decision_tree': {'name': 'Decision Tree', 'r2': 0.9053, 'status': 'production'},
    'xgboost': {'name': 'XGBoost', 'r2': 0.9701, 'status': 'production'},
    'lightgbm': {'name': 'LightGBM', 'r2': 0.9719, 'status': 'recommended'},
    'neural_network': {'name': 'Neural Network', 'r2': 0.9445, 'status': 'production'}
}


# Pydantic 모델 정의
class PropertyData(BaseModel):
    """부동산 데이터 요청 스키마"""
    area_sqm: float
    year_built: int
    rooms: int
    bathrooms: int
    parking: int
    floor: int
    total_floor: int
    condition: int
    original_price: float
    appraised_price: float
    outstanding_debt: float
    market_price: float
    transaction_count_1y: int
    ltv: float
    loan_term_months: int
    days_on_market: int
    appraisal_rounds: int
    age_years: int
    price_per_sqm: float
    debt_to_price_ratio: float
    price_variance: float
    numeric_mean: Optional[float] = None
    numeric_std: Optional[float] = None
    numeric_max: Optional[float] = None
    numeric_min: Optional[float] = None


class PredictionRequest(BaseModel):
    """예측 요청 스키마"""
    property_data: PropertyData
    model_name: str = 'lightgbm'  # 기본값: LightGBM


class PredictionResponse(BaseModel):
    """예측 응답 스키마"""
    predicted_price: float
    model_name: str
    confidence_score: float
    r2_score: float
    timestamp: str


class ModelInfo(BaseModel):
    """모델 정보 스키마"""
    model_name: str
    display_name: str
    r2_score: float
    status: str
    timestamp: str


def load_model(model_name: str):
    """모델 로드 (캐싱)"""
    if model_name in loaded_models:
        return loaded_models[model_name]

    # 가장 최근의 모델 파일 찾기
    model_files = list(MODELS_DIR.glob(f'{model_name}_*.pkl'))
    if not model_files:
        logger.warning(f"모델 파일을 찾을 수 없음: {model_name}")
        return None

    latest_model_file = sorted(model_files)[-1]
    try:
        with open(latest_model_file, 'rb') as f:
            model = pickle.load(f)
        loaded_models[model_name] = model
        logger.info(f"모델 로드됨: {model_name} from {latest_model_file.name}")
        return model
    except Exception as e:
        logger.error(f"모델 로드 실패: {model_name} - {e}")
        return None


def prepare_prediction_data(property_data: PropertyData) -> np.ndarray:
    """예측용 데이터 준비"""
    data = {
        'area_sqm': property_data.area_sqm,
        'year_built': property_data.year_built,
        'rooms': property_data.rooms,
        'bathrooms': property_data.bathrooms,
        'parking': property_data.parking,
        'floor': property_data.floor,
        'total_floor': property_data.total_floor,
        'condition': property_data.condition,
        'original_price': property_data.original_price,
        'appraised_price': property_data.appraised_price,
        'outstanding_debt': property_data.outstanding_debt,
        'market_price': property_data.market_price,
        'transaction_count_1y': property_data.transaction_count_1y,
        'ltv': property_data.ltv,
        'loan_term_months': property_data.loan_term_months,
        'days_on_market': property_data.days_on_market,
        'appraisal_rounds': property_data.appraisal_rounds,
        'age_years': property_data.age_years,
        'price_per_sqm': property_data.price_per_sqm,
        'debt_to_price_ratio': property_data.debt_to_price_ratio,
        'price_variance': property_data.price_variance,
        'numeric_mean': property_data.numeric_mean or 0.0,
        'numeric_std': property_data.numeric_std or 0.0,
        'numeric_max': property_data.numeric_max or 0.0,
        'numeric_min': property_data.numeric_min or 0.0,
    }

    df = pd.DataFrame([data])
    return df.values.astype(np.float32)


@app.get("/", tags=["Info"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "name": "AVM API",
        "description": "자동감정가 모델 (Automated Valuation Model) REST API",
        "version": "1.0.0",
        "endpoints": {
            "predict": "/predict",
            "models": "/models",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_available": len([m for m in model_metadata.keys() if load_model(m) is not None])
    }


@app.get("/models", response_model=List[ModelInfo], tags=["Models"])
async def list_models():
    """사용 가능한 모델 목록 조회"""
    models = []
    for model_key, metadata in model_metadata.items():
        model = load_model(model_key)
        if model is not None:
            models.append(ModelInfo(
                model_name=model_key,
                display_name=metadata['name'],
                r2_score=metadata['r2'],
                status=metadata['status'],
                timestamp=datetime.now().isoformat()
            ))
    return models


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictionRequest):
    """
    부동산 가격 예측

    요청 예시:
    ```json
    {
        "property_data": {
            "area_sqm": 100.5,
            "year_built": 2010,
            "rooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "floor": 5,
            "total_floor": 20,
            "condition": 7,
            "original_price": 500000000,
            "appraised_price": 480000000,
            "outstanding_debt": 300000000,
            "market_price": 490000000,
            "transaction_count_1y": 5,
            "ltv": 0.62,
            "loan_term_months": 240,
            "days_on_market": 30,
            "appraisal_rounds": 2,
            "age_years": 14,
            "price_per_sqm": 4876000,
            "debt_to_price_ratio": 0.61,
            "price_variance": 0.02
        },
        "model_name": "lightgbm"
    }
    ```
    """
    try:
        # 모델 로드
        model = load_model(request.model_name)
        if model is None:
            raise HTTPException(
                status_code=400,
                detail=f"모델을 로드할 수 없음: {request.model_name}"
            )

        # 데이터 준비
        X = prepare_prediction_data(request.property_data)

        # 예측
        predicted_price = model.predict(X)[0]

        # 신뢰도 점수 (R² 기반)
        r2_score = model_metadata[request.model_name]['r2']
        confidence_score = float(r2_score)

        logger.info(f"예측 완료: {request.model_name} → {predicted_price:,.0f}원")

        return PredictionResponse(
            predicted_price=float(predicted_price),
            model_name=request.model_name,
            confidence_score=confidence_score,
            r2_score=r2_score,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"예측 실패: {e}")
        raise HTTPException(status_code=500, detail=f"예측 중 오류 발생: {str(e)}")


@app.get("/model/{model_name}", tags=["Models"])
async def get_model_info(model_name: str):
    """특정 모델의 상세 정보 조회"""
    if model_name not in model_metadata:
        raise HTTPException(status_code=404, detail=f"모델을 찾을 수 없음: {model_name}")

    model = load_model(model_name)
    if model is None:
        raise HTTPException(status_code=400, detail=f"모델을 로드할 수 없음: {model_name}")

    metadata = model_metadata[model_name]
    return {
        "model_name": model_name,
        "display_name": metadata['name'],
        "r2_score": metadata['r2'],
        "status": metadata['status'],
        "description": f"{metadata['name']} - R² {metadata['r2']:.4f} ({metadata['status']})",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/predict/batch", tags=["Prediction"])
async def batch_predict(requests: List[PredictionRequest]):
    """
    배치 예측 (여러 부동산 한 번에 예측)

    최대 100개까지 한 번에 처리 가능
    """
    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="최대 100개까지만 배치 처리 가능")

    results = []
    for req in requests:
        try:
            result = await predict(req)
            results.append(result)
        except Exception as e:
            logger.error(f"배치 예측 중 오류: {e}")
            results.append({"error": str(e)})

    return {"count": len(results), "predictions": results}


@app.get("/api/version", tags=["Info"])
async def get_version():
    """API 버전 정보"""
    return {
        "api_version": "1.0.0",
        "models_count": len(model_metadata),
        "updated_at": "2026-06-12",
        "status": "production"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
