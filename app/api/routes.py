from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Appraisal, Auction, Complex, Property, Transaction
from app.avm.engine import AVMEngine
from app.avm.engine_v2 import AVMEngineV2, AVMResult
from app.config import settings

# ─── v1 라우터 ──────────────────────────────────────────────────────────────

router_v1 = APIRouter(prefix="/api/v1", tags=["AVM v1"])


class AVMEstimateRequest(BaseModel):
    property_id: int


@router_v1.post("/avm/estimate")
def estimate_v1(req: AVMEstimateRequest, db: Session = Depends(get_db)):
    prop = db.get(Property, req.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    engine = AVMEngine(db)
    result = engine.estimate(prop)
    return {
        "property_id": result.property_id,
        "estimated_price": result.estimated_price,
        "lower_bound": result.lower_bound,
        "upper_bound": result.upper_bound,
        "confidence_level": result.confidence_level,
        "methodology": result.methodology,
    }


@router_v1.get("/precedents")
def get_precedents(
    sido: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    stmt = select(Transaction).order_by(Transaction.report_date.desc()).limit(limit)
    if sido:
        stmt = (
            select(Transaction)
            .join(Complex, Transaction.complex_id == Complex.id)
            .where(Complex.address_sido == sido)
            .order_by(Transaction.report_date.desc())
            .limit(limit)
        )
    txs = db.execute(stmt).scalars().all()
    return [
        {
            "id": t.id,
            "price": int(t.price),
            "report_date": t.report_date.isoformat() if t.report_date else None,
            "exclusive_area": t.exclusive_area,
        }
        for t in txs
    ]


@router_v1.get("/auction-stats")
def auction_stats(db: Session = Depends(get_db)):
    auctions = db.execute(select(Auction)).scalars().all()
    total = len(auctions)
    won = [a for a in auctions if a.winning_bid]
    avg_ratio = (
        sum(float(a.winning_bid) / float(a.minimum_bid) for a in won if a.minimum_bid)
        / len(won)
        if won
        else None
    )
    return {
        "total_auctions": total,
        "won_auctions": len(won),
        "avg_winning_ratio": round(avg_ratio, 4) if avg_ratio else None,
    }


@router_v1.get("/properties/{serial}")
def get_property(serial: str, db: Session = Depends(get_db)):
    stmt = select(Property).where(Property.serial_number == serial)
    prop = db.execute(stmt).scalars().first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return {
        "id": prop.id,
        "serial_number": prop.serial_number,
        "property_type": prop.property_type,
        "address_full": prop.address_full,
        "building_area": prop.building_area,
        "complex_id": prop.complex_id,
    }


# ─── v2 라우터 ──────────────────────────────────────────────────────────────

router_v2 = APIRouter(prefix="/api/v2", tags=["AVM v2 / Agent"])


class AVMEstimateV2Request(BaseModel):
    property_id: int
    confidence_level: float = 0.85


@router_v2.post("/avm/estimate", response_model=AVMResult)
def estimate_v2(req: AVMEstimateV2Request, db: Session = Depends(get_db)):
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
    from app.agent.avm_agent import AVMAgent

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY 미설정")

    agent = AVMAgent(settings.ANTHROPIC_API_KEY, db)
    try:
        response = agent.query(req.query)
        return {"response": response, "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
