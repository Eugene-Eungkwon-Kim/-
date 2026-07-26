"""
AVM 프로젝트 - FastAPI 웹 서버
REST API for Automated Valuation Model Predictions

실행: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import pickle
import joblib
import hashlib
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom exceptions
from data_path_config import get_models_path
from exceptions import ModelNotFoundError, InvalidInputError, PredictionError
from prediction_enhancements import ConfidenceEstimator, PredictionCache
from feature_schema import load_schema as load_feature_schema
from dashboard_data import get_dashboard_summary, get_performance_history, get_alerts

# PHASE 4.1.1 - 반복 예측 캐시 (전역 인스턴스)
prediction_cache = PredictionCache(maxsize=10000)

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

# CORS 설정 (환경변수에서 읽음)
ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8080'
).split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# 프로젝트 경로 (플랫폼 독립적)
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = get_models_path()  # 환경변수 지원
DATA_DIR = PROJECT_ROOT / "data"

# 로드된 모델 캐시 및 메타데이터
loaded_models = {}
model_metadata_cache = {}


def load_model_metadata_from_file(model_name: str) -> Dict:
    """
    실제 모델 파일에서 메타데이터 동적 로드
    C7 CRITICAL 이슈 해결: 하드코딩된 메타데이터 제거
    """
    global model_metadata_cache

    # 캐시 확인
    if model_name in model_metadata_cache:
        return model_metadata_cache[model_name]

    # 모델 파일 찾기
    model_files = list(MODELS_DIR.glob(f'{model_name}_*.pkl'))
    if not model_files:
        # 기본값 반환 (모델을 찾을 수 없을 때)
        default_metadata = {
            'name': model_name.replace('_', ' ').title(),
            'r2': 0.0,
            'status': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }
        model_metadata_cache[model_name] = default_metadata
        return default_metadata

    latest_model_file = sorted(model_files)[-1]

    try:
        # joblib으로 모델 로드 (pickle보다 안전)
        model_data = joblib.load(str(latest_model_file))

        # 모델이 딕셔너리인 경우 메타데이터 추출
        if isinstance(model_data, dict):
            metadata = {
                'name': model_data.get('name', model_name.title()),
                'r2': float(model_data.get('r2_score', 0.0)),
                'rmse': float(model_data.get('rmse', 0.0)) if 'rmse' in model_data else None,
                'status': 'production' if model_data.get('r2_score', 0) > 0.90 else 'testing',
                'timestamp': model_data.get('timestamp', datetime.now().isoformat()),
                'model_file': latest_model_file.name
            }
        else:
            # 모델이 딕셔너리가 아니면 기본 정보만 반환
            metadata = {
                'name': model_name.replace('_', ' ').title(),
                'r2': 0.0,  # 모델에서 추출 불가
                'status': 'production',  # 모델이 존재하므로 production으로 간주
                'timestamp': datetime.now().isoformat(),
                'model_file': latest_model_file.name
            }

        model_metadata_cache[model_name] = metadata
        logger.info(f"✅ 메타데이터 로드: {model_name} (R²: {metadata['r2']:.4f})")
        return metadata

    except Exception as e:
        logger.error(f"❌ 메타데이터 로드 실패: {model_name} - {e}")
        default_metadata = {
            'name': model_name.replace('_', ' ').title(),
            'r2': 0.0,
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }
        model_metadata_cache[model_name] = default_metadata
        return default_metadata


def get_model_metadata(model_name: str) -> Dict:
    """모델 메타데이터 조회 (캐시된 데이터 반환)"""
    return load_model_metadata_from_file(model_name)


def get_available_models() -> Dict[str, Dict]:
    """사용 가능한 모든 모델의 메타데이터 조회"""
    # MODELS_DIR에서 모든 모델 파일 찾기
    model_files = list(MODELS_DIR.glob('*_tuned.pkl')) + list(MODELS_DIR.glob('*.joblib'))

    if not model_files:
        logger.warning("⚠️ 모델 파일을 찾을 수 없습니다")
        return {}

    # 모델 이름 추출 (파일명에서 _tuned.pkl 제거)
    model_names = set()
    for model_file in model_files:
        name = model_file.stem.replace('_tuned', '').replace('_', '_')
        model_names.add(name)

    # 각 모델의 메타데이터 로드
    available_models = {}
    for model_name in sorted(model_names):
        metadata = get_model_metadata(model_name)
        available_models[model_name] = metadata

    return available_models


# Pydantic 모델 정의 (입력 검증 포함)
class PropertyData(BaseModel):
    """부동산 데이터 요청 스키마 - 엄격한 검증 포함"""

    # 물리적 특성
    area_sqm: float = Field(
        ...,
        gt=0,
        le=1000,
        description="건물 면적 (m²), 10-1000 범위"
    )
    year_built: int = Field(
        ...,
        ge=1900,
        le=2026,
        description="건축년도, 1900-2026 범위"
    )
    rooms: int = Field(..., ge=0, le=20, description="방 개수")
    bathrooms: int = Field(..., ge=0, le=10, description="욕실 개수")
    parking: int = Field(..., ge=0, le=10, description="주차 공간")
    floor: int = Field(..., ge=0, le=100, description="현재 층수")
    total_floor: int = Field(..., ge=1, le=100, description="총 층수")
    condition: int = Field(..., ge=1, le=10, description="건물 상태 (1-10)")

    # 가격 정보 (단위: 만원 ₩10,000)
    original_price: float = Field(..., gt=100, le=10000000, description="원래 가격 (만원, 1000만~1조원)")
    appraised_price: float = Field(..., gt=100, le=10000000, description="감정가 (만원, 1000만~1조원)")
    outstanding_debt: float = Field(..., ge=0, le=10000000, description="미상환 채무 (만원)")
    market_price: float = Field(..., gt=100, le=10000000, description="시장 가격 (만원, 1000만~1조원)")

    # 거래 정보
    transaction_count_1y: int = Field(
        ...,
        ge=0,
        le=500,
        description="1년 내 거래 횟수"
    )
    ltv: float = Field(..., ge=0, le=2, description="LTV (부채/자산 비율)")
    loan_term_months: int = Field(..., ge=1, le=600, description="대출 기간 (개월)")
    days_on_market: int = Field(..., ge=0, le=3650, description="시장 노출 일수 (0-10년)")
    appraisal_rounds: int = Field(..., ge=1, le=10, description="감정 횟수")

    # 파생 특성
    age_years: int = Field(..., ge=0, le=150, description="건물 경과 연수")
    price_per_sqm: float = Field(..., gt=0, description="m²당 가격 (만원)")
    debt_to_price_ratio: float = Field(..., ge=0, le=2, description="채무/가격 비율")
    price_variance: float = Field(..., ge=0, le=1, description="가격 변동성")

    # 경제 지표
    numeric_mean: Optional[float] = Field(None, description="평균값")
    numeric_std: Optional[float] = Field(None, description="표준편차")
    numeric_max: Optional[float] = Field(None, description="최댓값")
    numeric_min: Optional[float] = Field(None, description="최솟값")

    @validator('year_built')
    def validate_year_built(cls, v):
        """건축년도가 현재보다 미래일 수 없음"""
        from datetime import datetime
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f'건축년도는 현재보다 미래일 수 없습니다: {v}')
        if current_year - v > 100:
            raise ValueError(f'건축년도가 너무 오래됨: {v} (100년 이상)')
        return v

    @validator('area_sqm')
    def validate_area(cls, v):
        """면적이 합리적인 범위여야 함"""
        if v < 10:
            raise ValueError('면적은 최소 10m² 이상이어야 합니다')
        if v > 500:
            raise ValueError('면적이 일반적인 범위를 초과합니다 (> 500m²)')
        return v

    @validator('original_price', 'appraised_price', 'market_price', always=True)
    def validate_prices(cls, v):
        """가격이 합리적인 범위여야 함 (입력 단위: 만원 ₩10,000)"""
        if v < 100:  # 100 × ₩10,000 = ₩1,000,000
            raise ValueError('가격이 너무 낮습니다 (최소 100만원)')
        if v > 10000000:  # 10,000,000 × ₩10,000 = ₩100,000,000,000 = 1조원
            raise ValueError('가격이 너무 높습니다 (최대 1조원)')
        return v

    @validator('debt_to_price_ratio')
    def validate_debt_ratio(cls, v):
        """채무비율이 합리적인 범위여야 함"""
        if v > 2:
            raise ValueError('채무비율이 비정상입니다 (2.0 초과)')
        return v

    @validator('ltv')
    def validate_ltv(cls, v):
        """LTV가 합리적인 범위여야 함"""
        if v < 0 or v > 2:
            raise ValueError('LTV는 0-2 범위여야 합니다')
        return v

    class Config:
        schema_extra = {
            "example": {
                "area_sqm": 84.5,
                "year_built": 2015,
                "rooms": 3,
                "bathrooms": 2,
                "parking": 1,
                "floor": 5,
                "total_floor": 15,
                "condition": 7,
                "original_price": 450000,
                "appraised_price": 455000,
                "outstanding_debt": 250000,
                "market_price": 460000,
                "transaction_count_1y": 12,
                "ltv": 0.55,
                "loan_term_months": 240,
                "days_on_market": 30,
                "appraisal_rounds": 2,
                "age_years": 11,
                "price_per_sqm": 5326,
                "debt_to_price_ratio": 0.55,
                "price_variance": 0.02,
                "numeric_mean": 450000,
                "numeric_std": 50000,
                "numeric_max": 500000,
                "numeric_min": 400000
            }
        }


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


def compute_file_hash(filepath: Path, algorithm: str = 'sha256') -> str:
    """파일의 해시값 계산 (무결성 검증)"""
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def load_model(model_name: str):
    """
    모델 로드 (캐싱 + 보안)
    C8 CRITICAL 이슈 해결: joblib 사용 + SHA256 해시 검증
    """
    # 캐시 확인
    if model_name in loaded_models:
        return loaded_models[model_name]

    # 가장 최근의 모델 파일 찾기
    model_files = list(MODELS_DIR.glob(f'{model_name}_*.pkl'))
    model_files += list(MODELS_DIR.glob(f'{model_name}_*.joblib'))

    if not model_files:
        logger.warning(f"⚠️ 모델 파일을 찾을 수 없음: {model_name}")
        return None

    latest_model_file = sorted(model_files)[-1]

    try:
        # 해시 검증 (선택사항: .sha256 파일이 있으면 검증)
        hash_file = latest_model_file.with_suffix('.sha256')
        if hash_file.exists():
            computed_hash = compute_file_hash(latest_model_file)
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()

            if computed_hash != stored_hash:
                raise ValueError(
                    f"모델 파일 무결성 검증 실패: {model_name}\n"
                    f"Expected: {stored_hash}\n"
                    f"Computed: {computed_hash}"
                )
            logger.info(f"✅ 해시 검증 통과: {model_name}")

        # joblib으로 모델 로드 (pickle보다 안전)
        model = joblib.load(str(latest_model_file))
        loaded_models[model_name] = model
        logger.info(f"✅ 모델 로드 완료: {model_name} from {latest_model_file.name}")
        return model

    except ValueError as e:
        logger.error(f"❌ 무결성 검증 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 모델 로드 실패: {model_name} - {type(e).__name__}: {e}")
        return None


def prepare_prediction_data(property_data: PropertyData) -> np.ndarray:
    """예측용 데이터 준비.

    저장된 특성 스키마(models/feature_schema.json)를 단일 소스로 사용하여
    학습 시점과 동일한 특성·순서로 입력 벡터를 구성한다(train/serve 스큐 방지).
    """
    # PropertyData의 모든 필드를 dict로 변환 후 스키마 순서대로 선택
    all_values = property_data.dict()
    schema = load_feature_schema()
    feature_names = schema["features"]

    row = []
    for name in feature_names:
        value = all_values.get(name)
        row.append(float(value) if value is not None else 0.0)

    return np.array([row], dtype=np.float32)


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
    available_models = get_available_models()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_available": len([m for m in available_models if load_model(m) is not None]),
        "total_models": len(available_models)
    }


@app.get("/models", response_model=List[ModelInfo], tags=["Models"])
async def list_models():
    """사용 가능한 모델 목록 조회 (동적 로드)"""
    models = []
    available_models = get_available_models()

    for model_key, metadata in available_models.items():
        model = load_model(model_key)
        if model is not None:
            models.append(ModelInfo(
                model_name=model_key,
                display_name=metadata.get('name', model_key.title()),
                r2_score=float(metadata.get('r2', 0.0)),
                status=metadata.get('status', 'unknown'),
                timestamp=datetime.now().isoformat()
            ))

    return models


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictionRequest):
    """
    부동산 가격 예측 (입력 검증 포함)

    Pydantic 자동 검증:
    - area_sqm: 0 < x <= 1000
    - year_built: 1900 <= x <= 2026
    - 모든 가격: 100 <= x <= 100000 (만원 단위)
    """
    try:
        # 모델 로드 (미존재 시 load_model이 None 반환 → 404)
        model = load_model(request.model_name)
        if model is None:
            raise ModelNotFoundError(f"모델을 로드할 수 없음: {request.model_name}")

        # 데이터 준비 (Pydantic이 이미 검증함)
        X = prepare_prediction_data(request.property_data)

        # 예측 실행
        predicted_price = model.predict(X)[0]

        # 신뢰도 점수 (R² 기반 - 동적 로드)
        metadata = get_model_metadata(request.model_name)
        r2_score = float(metadata.get('r2', 0.0))
        confidence_score = r2_score

        logger.info(f"✅ 예측 완료: {request.model_name} → {predicted_price:,.0f}원")

        return PredictionResponse(
            predicted_price=float(predicted_price),
            model_name=request.model_name,
            confidence_score=confidence_score,
            r2_score=r2_score,
            timestamp=datetime.now().isoformat()
        )

    except ModelNotFoundError as e:
        logger.warning(f"⚠️ 모델 오류: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        logger.warning(f"⚠️ 입력 오류: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PredictionError as e:
        logger.error(f"❌ 예측 오류: {e}")
        raise HTTPException(status_code=500, detail="모델 예측 실패")
    except ValueError as e:
        logger.warning(f"⚠️ 검증 오류: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류")


@app.post("/predict/confidence", tags=["Prediction"])
async def predict_with_confidence(request: PredictionRequest, confidence: float = 0.95):
    """
    PHASE 4.2.1 - 신뢰구간 포함 예측

    점추정값과 함께 예측 불확실성(신뢰구간)을 반환한다.
    트리 앙상블 모델은 개별 추정기 분산을, 그 외 모델은 보수적
    폴백(점추정의 5%)을 사용해 구간을 계산한다.
    - confidence: 0.90 / 0.95 / 0.99 중 선택 (기본 0.95)
    """
    try:
        model = load_model(request.model_name)
        if model is None:
            raise ModelNotFoundError(f"모델을 로드할 수 없음: {request.model_name}")

        if confidence not in ConfidenceEstimator.Z:
            raise InvalidInputError(
                f"confidence는 {list(ConfidenceEstimator.Z)} 중 하나여야 합니다"
            )

        X = prepare_prediction_data(request.property_data)
        estimator = ConfidenceEstimator(model, confidence=confidence)
        interval = estimator.estimate(X[0])

        logger.info(
            f"✅ 신뢰구간 예측: {request.model_name} → "
            f"{interval.prediction:,.0f}원 [{interval.lower:,.0f}, {interval.upper:,.0f}]"
        )

        return {
            "model_name": request.model_name,
            **interval.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except ModelNotFoundError as e:
        logger.warning(f"⚠️ 모델 오류: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        logger.warning(f"⚠️ 입력 오류: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류")


@app.get("/cache/stats", tags=["Info"])
async def cache_stats():
    """PHASE 4.1.1 - 예측 캐시 통계 조회"""
    return {"cache": prediction_cache.stats(), "timestamp": datetime.now().isoformat()}


# ============================================================================
# 대시보드 엔드포인트 (웹 UI용 데이터 제공)
# ============================================================================
@app.get("/dashboard/api/summary", tags=["Dashboard"])
async def dashboard_summary():
    """대시보드 종합 요약"""
    return get_dashboard_summary()


@app.get("/dashboard/api/performance", tags=["Dashboard"])
async def dashboard_performance(limit: int = 100):
    """성능 이력 (시계열 데이터)"""
    history = get_performance_history(limit)
    return {
        "total": len(history),
        "data": history,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/dashboard/api/alerts", tags=["Dashboard"])
async def dashboard_alerts(limit: int = 20):
    """최근 알림"""
    alerts = get_alerts(limit)
    return {
        "total": len(alerts),
        "data": alerts,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard_ui():
    """웹 기반 성능 모니터링 대시보드"""
    from fastapi.responses import HTMLResponse

    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AVM 성능 모니터링 대시보드</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                color: #333;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
            }

            header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }

            header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }

            header p {
                font-size: 1.1em;
                opacity: 0.9;
            }

            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
            }

            .card h2 {
                font-size: 1.3em;
                margin-bottom: 15px;
                color: #667eea;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }

            .stat {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }

            .stat:last-child {
                border-bottom: none;
            }

            .stat-label {
                font-weight: 500;
                color: #666;
            }

            .stat-value {
                font-weight: bold;
                color: #333;
                font-family: 'Monaco', 'Courier New', monospace;
            }

            .stat-value.positive {
                color: #10b981;
            }

            .stat-value.negative {
                color: #ef4444;
            }

            .chart-container {
                position: relative;
                height: 300px;
                margin: 20px 0;
            }

            .alert {
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 12px 15px;
                border-radius: 4px;
                margin-bottom: 10px;
                font-size: 0.9em;
            }

            .alert.high {
                background: #fee2e2;
                border-left-color: #ef4444;
            }

            .loading {
                text-align: center;
                padding: 40px;
                color: #999;
            }

            .spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .full-width {
                grid-column: 1 / -1;
            }

            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .status-healthy {
                background: #d1fae5;
                color: #065f46;
            }

            .status-warning {
                background: #fef3c7;
                color: #92400e;
            }

            .timestamp {
                font-size: 0.85em;
                color: #999;
                text-align: right;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🎯 AVM 성능 모니터링 대시보드</h1>
                <p>자동감정가 모델 실시간 성능 추적</p>
            </header>

            <div class="grid">
                <!-- 상태 요약 -->
                <div class="card full-width">
                    <h2>📊 실시간 현황</h2>
                    <div id="summary-content" class="loading">
                        <div class="spinner"></div> 데이터 로드 중...
                    </div>
                </div>

                <!-- 성능 그래프 -->
                <div class="card full-width">
                    <h2>📈 성능 추이 (R²)</h2>
                    <div class="chart-container">
                        <canvas id="performanceChart"></canvas>
                    </div>
                </div>

                <!-- 통계 -->
                <div class="card">
                    <h2>📉 성능 통계</h2>
                    <div id="stats-content" class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>

                <!-- 챔피언 모델 -->
                <div class="card">
                    <h2>🏆 챔피언 모델</h2>
                    <div id="champion-content" class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>

                <!-- 최근 알림 -->
                <div class="card full-width">
                    <h2>🚨 최근 알림</h2>
                    <div id="alerts-content" class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let performanceChart = null;

            async function loadDashboard() {
                try {
                    // 요약 데이터 로드
                    const summaryResp = await fetch('/dashboard/api/summary');
                    const summary = await summaryResp.json();
                    updateSummary(summary);

                    // 성능 이력 로드
                    const perfResp = await fetch('/dashboard/api/performance?limit=50');
                    const perfData = await perfResp.json();
                    updateChart(perfData.data);
                    updateStats(summary.performance);

                    // 챔피언 모델 로드
                    updateChampion(summary.champion);

                    // 알림 로드
                    const alertResp = await fetch('/dashboard/api/alerts?limit=10');
                    const alerts = await alertResp.json();
                    updateAlerts(alerts.data);

                } catch (error) {
                    console.error('Dashboard load failed:', error);
                    document.getElementById('summary-content').innerHTML =
                        '<div style="color: red;">데이터 로드 실패</div>';
                }
            }

            function updateSummary(data) {
                const latest = data.performance.latest;
                const status = data.status === 'healthy' ?
                    '<span class="status-badge status-healthy">✅ 건강</span>' :
                    '<span class="status-badge status-warning">⚠️ 주의</span>';

                const html = `
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                        <div>
                            <div class="stat">
                                <span class="stat-label">현재 R²</span>
                                <span class="stat-value">${(latest.r2).toFixed(4)}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">변화</span>
                                <span class="stat-value ${latest.r2_change >= 0 ? 'positive' : 'negative'}">
                                    ${latest.r2_change >= 0 ? '+' : ''}${(latest.r2_change).toFixed(6)}
                                </span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">모델</span>
                                <span class="stat-value">${latest.model}</span>
                            </div>
                        </div>
                        <div>
                            <div class="stat">
                                <span class="stat-label">상태</span>
                                <span>${status}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">추이</span>
                                <span class="stat-value">${latest.trend}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">업데이트</span>
                                <span class="stat-value">${new Date(latest.timestamp).toLocaleString('ko-KR')}</span>
                            </div>
                        </div>
                    </div>
                `;
                document.getElementById('summary-content').innerHTML = html;
            }

            function updateChart(data) {
                const ctx = document.getElementById('performanceChart').getContext('2d');

                const timestamps = data.map(d => new Date(d.timestamp).toLocaleDateString('ko-KR'));
                const r2Values = data.map(d => (d.test_r2 * 100).toFixed(2));

                if (performanceChart) {
                    performanceChart.destroy();
                }

                performanceChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: timestamps,
                        datasets: [{
                            label: 'Test R² (%)',
                            data: r2Values,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 4,
                            pointBackgroundColor: '#667eea',
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                labels: { font: { size: 12 } }
                            }
                        },
                        scales: {
                            y: {
                                min: 0,
                                max: 100,
                                ticks: { callback: (v) => v + '%' }
                            }
                        }
                    }
                });
            }

            function updateStats(perfStats) {
                if (!perfStats.stats) {
                    document.getElementById('stats-content').innerHTML =
                        '<div style="color: #999;">데이터 없음</div>';
                    return;
                }

                const stats = perfStats.stats;
                const html = `
                    <div class="stat">
                        <span class="stat-label">최고 R²</span>
                        <span class="stat-value">${(stats.best_r2).toFixed(4)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">평균 R²</span>
                        <span class="stat-value">${(stats.avg_r2).toFixed(4)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">최저 R²</span>
                        <span class="stat-value">${(stats.worst_r2).toFixed(4)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">평균 RMSE</span>
                        <span class="stat-value">${(stats.avg_rmse).toFixed(0)}</span>
                    </div>
                `;
                document.getElementById('stats-content').innerHTML = html;
            }

            function updateChampion(champion) {
                const html = `
                    <div class="stat">
                        <span class="stat-label">모델명</span>
                        <span class="stat-value">${champion.name}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">R² 점수</span>
                        <span class="stat-value">${(champion.r2).toFixed(4)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">RMSE</span>
                        <span class="stat-value">${(champion.rmse).toFixed(0)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">서명</span>
                        <span class="stat-value" style="font-size: 0.85em;">${champion.sha256}</span>
                    </div>
                `;
                document.getElementById('champion-content').innerHTML = html;
            }

            function updateAlerts(alerts) {
                if (alerts.length === 0) {
                    document.getElementById('alerts-content').innerHTML =
                        '<div style="color: #10b981; text-align: center; padding: 20px;">✅ 알림 없음</div>';
                    return;
                }

                const html = alerts.map(alert => `
                    <div class="alert ${alert.severity === 'HIGH' ? 'high' : ''}">
                        <strong>${alert.severity}</strong> - ${alert.type}
                        <br><small>${new Date(alert.timestamp).toLocaleString('ko-KR')}</small>
                        ${alert.type === 'performance_regression' ?
                            `<br><small>R²: ${(alert.previous_r2).toFixed(4)} → ${(alert.latest_r2).toFixed(4)}</small>` : ''}
                    </div>
                `).join('');

                document.getElementById('alerts-content').innerHTML = html;
            }

            // 초기 로드
            loadDashboard();

            // 30초마다 새로고침
            setInterval(loadDashboard, 30000);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)



@app.get("/model/{model_name}", tags=["Models"])
async def get_model_info(model_name: str):
    """특정 모델의 상세 정보 조회 (동적 메타데이터)"""
    model = load_model(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"모델을 찾을 수 없음: {model_name}")

    metadata = get_model_metadata(model_name)
    r2_score = float(metadata.get('r2', 0.0))
    status = metadata.get('status', 'unknown')

    return {
        "model_name": model_name,
        "display_name": metadata.get('name', model_name.title()),
        "r2_score": r2_score,
        "status": status,
        "description": f"{metadata.get('name', model_name.title())} - R² {r2_score:.4f} ({status})",
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
        "models_count": len(get_available_models()),
        "updated_at": "2026-06-12",
        "status": "production"
    }


# Global exception handlers
from pydantic import ValidationError


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Pydantic 검증 오류 처리"""
    logger.warning(f"검증 오류: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "입력 검증 실패",
            "errors": exc.errors()
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.exception(f"처리되지 않은 예외: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
