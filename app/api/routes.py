from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Appraisal, Auction, Deal, Property
from app.avm import engine as avm

router = APIRouter()


class AVMRequest(BaseModel):
    address_sido: str
    address_sigungu: str
    property_type: str
    land_area: Optional[float] = None
    building_area: Optional[float] = None
    max_comparables: int = 10


class AVMResponse(BaseModel):
    estimated_value: Optional[int]
    confidence: str
    comparable_count: int
    avg_appraisal: Optional[int]
    median_hammer_rate: Optional[float]
    comparables: list[dict]


@router.post("/avm/estimate", response_model=AVMResponse, summary="AVM 감정가 추정")
def estimate_value(req: AVMRequest, db: Session = Depends(get_db)):
    result = avm.estimate(
        db=db, address_sido=req.address_sido, address_sigungu=req.address_sigungu,
        property_type=req.property_type, land_area=req.land_area,
        building_area=req.building_area, max_comparables=req.max_comparables,
    )
    return AVMResponse(
        estimated_value=result.estimated_value, confidence=result.confidence,
        comparable_count=result.comparable_count, avg_appraisal=result.avg_appraisal,
        median_hammer_rate=result.median_hammer_rate,
        comparables=[vars(c) for c in result.comparables],
    )


@router.get("/precedents", summary="유사 물건 전례 조회")
def get_precedents(
    sido: str = Query(...),
    sigungu: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    latest_sub = (
        db.query(Appraisal.property_id, func.max(Appraisal.appraisal_date).label("max_date"))
        .group_by(Appraisal.property_id).subquery()
    )
    q = (
        db.query(Property, Appraisal, Deal)
        .outerjoin(latest_sub, latest_sub.c.property_id == Property.id)
        .outerjoin(Appraisal, (Appraisal.property_id == Property.id) &
                   (Appraisal.appraisal_date == latest_sub.c.max_date))
        .join(Deal, Deal.id == Property.deal_id)
        .filter(Property.address_sido == sido)
    )
    if sigungu:
        q = q.filter(Property.address_sigungu == sigungu)
    if property_type:
        q = q.filter(Property.property_type.ilike(f"%{property_type}%"))
    if min_area:
        q = q.filter(Property.building_area >= min_area)
    if max_area:
        q = q.filter(Property.building_area <= max_area)

    rows = q.order_by(Appraisal.appraisal_date.desc()).limit(limit).all()

    # 경매 결과 일괄 prefetch
    prop_ids = [p.id for p, _, _ in rows]
    auctions_map = {}
    for a in db.query(Auction).filter(Auction.property_id.in_(prop_ids)).all():
        auctions_map.setdefault(a.property_id, []).append(a)

    results = []
    for prop, appr, deal in rows:
        auction = max(auctions_map.get(prop.id, []), key=lambda a: a.filing_date or "", default=None)
        results.append({
            "property_serial": prop.property_serial,
            "address": prop.address_full,
            "property_type": prop.property_type,
            "land_area": prop.land_area,
            "building_area": prop.building_area,
            "appraisal_date": str(appr.appraisal_date) if appr else None,
            "appraisal_value": int(appr.total_value) if appr and appr.total_value else None,
            "hammer_price": int(auction.hammer_price) if auction and auction.hammer_price else None,
            "final_result": auction.final_result if auction else None,
            "lapse_count": auction.lapse_count if auction else None,
            "deal_name": deal.deal_name,
            "financial_institution": deal.financial_institution,
        })
    return {"count": len(results), "items": results}


@router.get("/auction-stats", summary="낙찰가율 통계")
def get_auction_stats(
    property_type: str = Query(...),
    sido: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return avm.auction_stats(db, property_type, sido)


@router.get("/properties/{property_serial}", summary="물건 상세 조회")
def get_property(property_serial: str, db: Session = Depends(get_db)):
    prop = db.query(Property).filter_by(property_serial=property_serial).first()
    if not prop:
        raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다")

    appraisals = db.query(Appraisal).filter_by(property_id=prop.id).all()
    auctions = db.query(Auction).filter_by(property_id=prop.id).all()
    deal = db.query(Deal).filter_by(id=prop.deal_id).first()
    latest_appr_val = next((int(a.total_value) for a in sorted(
        appraisals, key=lambda a: a.appraisal_date or "", reverse=True
    ) if a.total_value), None)

    return {
        "property": {
            "serial": prop.property_serial, "address": prop.address_full,
            "type": prop.property_type, "category": prop.property_category,
            "land_area": prop.land_area, "building_area": prop.building_area,
            "mortgage_amount": int(prop.mortgage_amount) if prop.mortgage_amount else None,
            "kb_market_price": int(prop.kb_market_price) if prop.kb_market_price else None,
        },
        "deal": {
            "name": deal.deal_name if deal else None,
            "institution": deal.financial_institution if deal else None,
            "asset_date": str(deal.asset_date) if deal and deal.asset_date else None,
        },
        "appraisals": [
            {"type": a.appraisal_type, "date": str(a.appraisal_date), "appraiser": a.appraiser,
             "land_value": int(a.land_value) if a.land_value else None,
             "building_value": int(a.building_value) if a.building_value else None,
             "total_value": int(a.total_value) if a.total_value else None}
            for a in appraisals
        ],
        "auctions": [
            {"court": a.court, "case_number": a.case_number, "lapse_count": a.lapse_count,
             "final_result": a.final_result,
             "first_legal_price": int(a.first_legal_price) if a.first_legal_price else None,
             "hammer_price": int(a.hammer_price) if a.hammer_price else None,
             "hammer_rate": round(int(a.hammer_price) / latest_appr_val, 4)
             if a.hammer_price and latest_appr_val else None}
            for a in auctions
        ],
    }
