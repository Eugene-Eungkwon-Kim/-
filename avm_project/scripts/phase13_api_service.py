#!/usr/bin/env python3
"""
Loan4U Phase 13.4.1 - NPU-based AVM API Service
FastAPI wrapper for NPU inference engine with real-time property valuation.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']

app = FastAPI(
    title="Loan4U AVM API",
    description="Automatic Valuation Model via NPU inference",
    version="1.0.0"
)


class PropertyInput(BaseModel):
    """Property features for valuation."""
    area_sqm: float = Field(..., gt=0, le=1000, description="건물면적(㎡)")
    old_price: float = Field(..., gt=0, le=10000000, description="기존가격(원)")
    latitude: float = Field(..., ge=33, le=38, description="위도")
    longitude: float = Field(..., ge=126, le=131, description="경도")
    property_type: int = Field(..., ge=1, le=5, description="부동산유형(1-5)")


class ValuationResponse(BaseModel):
    """Valuation prediction result."""
    predicted_price: float = Field(..., description="예측가격(원)")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도(0-1)")
    latency_ms: float = Field(..., ge=0, description="응답시간(ms)")
    model_version: str = Field(default="v13.4.1", description="모델버전")


class ModelStats(BaseModel):
    """Inference engine status."""
    models_loaded: int
    model_names: list
    device: str
    ready: bool


inference_engine: Optional[object] = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize NPU inference engine on startup."""
    global inference_engine
    try:
        from phase13_npu_inference import NPUInferenceEngine

        ir_dir = Path("output/models_ir")
        if not ir_dir.exists():
            log.warning(f"Model directory not found: {ir_dir}")
            inference_engine = None
            return

        inference_engine = NPUInferenceEngine(str(ir_dir))
        log.info("NPU inference engine initialized")
    except Exception as e:
        log.warning(f"Failed to initialize inference engine: {e}")
        inference_engine = None


@app.post("/api/valuation", response_model=ValuationResponse)
async def valuate_property(features: PropertyInput) -> ValuationResponse:
    """Predict property valuation using NPU ensemble."""
    if not inference_engine:
        raise HTTPException(status_code=503, detail="Inference engine not available")

    try:
        feature_array = np.array(
            [features.area_sqm, features.old_price, features.latitude,
             features.longitude, features.property_type],
            dtype=np.float32
        )
        price, confidence, latency = inference_engine.predict(feature_array)

        return ValuationResponse(
            predicted_price=float(price),
            confidence=float(confidence),
            latency_ms=float(latency)
        )
    except Exception as e:
        log.error(f"Valuation failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")


@app.get("/api/models", response_model=ModelStats)
async def get_model_status() -> ModelStats:
    """Get inference engine status."""
    if not inference_engine:
        return ModelStats(
            models_loaded=0,
            model_names=[],
            device="unavailable",
            ready=False
        )

    stats = inference_engine.get_model_stats()
    return ModelStats(
        models_loaded=stats['models_loaded'],
        model_names=stats['model_names'],
        device=stats['device'],
        ready=stats['models_loaded'] > 0
    )


@app.get("/api/health")
async def health_check() -> Dict[str, object]:
    """Health check endpoint."""
    return {
        "status": "healthy" if inference_engine else "degraded",
        "engine": "ready" if inference_engine else "not_initialized"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """API root endpoint."""
    return {
        "service": "Loan4U AVM API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
