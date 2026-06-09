"""
AVM v2 엔드포인트 — 확장 엔진 + LLM Agent
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Property
from app.avm.engine_v2 import AVMEngineV2, AVMResult
from app.config import settings

router_v2 = APIRouter(prefix="/api/v2", tags=["AVM v2 / Agent"])


class AVMEstimateV2Request(BaseModel):
    property_id: int
    confidence_level: float = 0.85


@router_v2.post("/avm/estimate", response_model=AVMResult)
def estimate_v2(req: AVMEstimateV2Request, db: Session = Depends(get_db)):
    """확장 AVM 엔진으로 감정가 추정 (비교사례 + 시점수정)"""
    prop = db.get(Property, req.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    try:
        engine = AVMEngineV2(db)
        return engine.estimate(prop, req.confidence_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)


@router_v2.post("/agent/query")
def agent_query(req: AgentQueryRequest, db: Session = Depends(get_db)):
    """자연어 기반 감정평가 조회 (Claude Tool Use Agent)"""
    from app.agent.avm_agent import AVMAgent

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY 미설정")

    agent = AVMAgent(settings.ANTHROPIC_API_KEY, db)
    try:
        response = agent.query(req.query)
        return {"response": response, "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
