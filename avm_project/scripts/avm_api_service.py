"""WP 3.1: AVM FastAPI Service - REST API 엔드포인트."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

app = FastAPI(
    title="Loan4U AVM Engine",
    description="Automatic Valuation Model API - 부동산 자동 가치평가",
    version="1.0.0",
)

engine = None


class PropertyInput(BaseModel):
    """부동산 입력 데이터."""
    area_sqm: float = Field(..., gt=0, le=1000, description="건물면적(㎡)")
    old_price: float = Field(..., gt=0, le=10_000_000, description="기존가격(원)")
    latitude: float = Field(..., ge=33.0, le=38.0, description="위도")
    longitude: float = Field(..., ge=126.0, le=131.0, description="경도")
    property_type: str = Field(default='apartment', description="부동산유형")
    district_grade: str = Field(default='auto', pattern='^(auto|[1-6])$', description="행정구역등급(1-6) 또는 'auto'(좌표 기반 자동)")
    public_appraisal_price: Optional[float] = Field(default=None, gt=0, description="공시가격(원)")
    market_condition: str = Field(default='normal', description="시장상황(rising/normal/declining)")
    reference_year: int = Field(default=2024, ge=2020, le=2026, description="기준연도")


class ValuationResponse(BaseModel):
    """가치평가 응답."""
    base_price: float
    corrected_price: float
    confidence: float
    validation_status: bool
    validation: Dict[str, Any]
    auction_forecast: Dict[str, Any]
    latency_ms: float
    model_version: str
    timestamp: str


class EngineStatus(BaseModel):
    """엔진 상태."""
    version: str
    status: str
    uptime_hours: float
    predictions_count: int
    models: Dict[str, Any]
    performance: Dict[str, Any]


@app.on_event("startup")
async def startup() -> None:
    """서비스 시작 시 엔진 초기화."""
    global engine
    try:
        from scripts.avm_core_engine import AVMCoreEngine
        engine = AVMCoreEngine()
        log.info("AVM Engine initialized")
    except Exception as e:
        log.error(f"Engine init failed: {e}")
        engine = None


@app.post("/api/valuate", response_model=ValuationResponse)
async def valuate_property(request: PropertyInput) -> ValuationResponse:
    """부동산 개별 가치평가."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        result = engine.valuate(**request.dict())
        return ValuationResponse(**result)
    except Exception as e:
        log.error(f"Valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-valuate")
async def batch_valuate(requests: List[PropertyInput]) -> List[Dict]:
    """대량 가치평가."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        return engine.batch_valuate([r.dict() for r in requests])
    except Exception as e:
        log.error(f"Batch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auction-forecast")
async def auction_forecast(request: PropertyInput) -> Dict:
    """낙찰가 추정."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        result = engine.valuate(**request.dict())
        return result['auction_forecast']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/engine-status", response_model=EngineStatus)
async def engine_status() -> EngineStatus:
    """엔진 상태 및 성능 통계."""
    if not engine:
        return EngineStatus(
            version='v1.0-ensemble', status='not_initialized',
            uptime_hours=0, predictions_count=0,
            models={}, performance={},
        )
    return EngineStatus(**engine.get_engine_stats())


@app.get("/api/health")
async def health_check() -> Dict:
    """헬스체크."""
    return {
        "status": "healthy" if engine else "degraded",
        "engine": "ready" if engine else "not_initialized",
    }


@app.get("/api/models")
async def get_models() -> Dict:
    """로드된 모델 정보."""
    if not engine:
        return {"models_loaded": 0, "model_names": [], "device": "unavailable"}
    return engine.ensemble.get_model_stats()


@app.get("/")
async def root() -> Dict:
    """API 루트."""
    return {"service": "Loan4U AVM Engine", "version": "1.0.0", "docs": "/docs"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
