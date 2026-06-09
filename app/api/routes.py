from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Property, Appraisal, Auction, Deal
from app.avm import engine as avm

router = APIRouter()


# ─── 요청/응답 스키마 ────────────────────────────────────────────────────────

class AVMRequest(BaseModel):
    address_sido: str
    address_sigungu: str
    property_type: str
    land_area: Optional[float] = None
    building_area: Optional[float] = None
    max_comparables: int = 10


class ComparableOut(BaseModel):
    property_serial: str
    address: str
    property_type: str
    land_area: Optional[float]
    building_area: Optional[float]
    appraisal_date: str
    appraisal_value: int
    hammer_price: Optional[int]
    hammer_rate: Optional[float]
    deal_name: str


class AVMResponse(BaseModel):
    estimated_value: Optional[int]
    confidence: str
    comparable_count: int
    avg_appraisal: Optional[int]
    median_hammer_rate: Optional[float]
    comparables: list[ComparableOut]


# ─── AVM 추정 ────────────────────────────────────────────────────────────────

@router.post("/avm/estimate", response_model=AVMResponse, summary="AVM 감정가 추정")
def estimate_value(req: AVMRequest, db: Session = Depends(get_db)):
    result = avm.estimate(
        db=db,
        address_sido=req.address_sido,
        address_sigungu=req.address_sigungu,
        property_type=req.property_type,
        land_area=req.land_area,
        building_area=req.building_area,
        max_comparables=req.max_comparables,
    )
    return AVMResponse(
        estimated_value=result.estimated_value,
        confidence=result.confidence,
        comparable_count=result.comparable_count,
        avg_appraisal=result.avg_appraisal,
        median_hammer_rate=result.median_hammer_rate,
        comparables=[ComparableOut(**vars(c)) for c in result.comparables],
    )


# ─── 전례 조회 ───────────────────────────────────────────────────────────────

@router.get("/precedents", summary="유사 물건 전례 조회")
def get_precedents(
    sido: str = Query(..., description="시/도 (예: 경기도)"),
    sigungu: Optional[str] = Query(None, description="시/군/구"),
    property_type: Optional[str] = Query(None, description="자산유형 (예: 아파트, 창고)"),
    min_area: Optional[float] = Query(None, description="최소 건물면적(㎡)"),
    max_area: Optional[float] = Query(None, description="최대 건물면적(㎡)"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc
    # 최신 감정평가 1건만 (중복 방지)
    latest_appr_sub = (
        db.query(
            Appraisal.property_id,
            sqlfunc.max(Appraisal.appraisal_date).label("max_date"),
        )
        .group_by(Appraisal.property_id)
        .subquery()
    )

    q = (
        db.query(Property, Appraisal, Deal)
        .outerjoin(latest_appr_sub, latest_appr_sub.c.property_id == Property.id)
        .outerjoin(
            Appraisal,
            (Appraisal.property_id == Property.id) &
            (Appraisal.appraisal_date == latest_appr_sub.c.max_date),
        )
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

    q = q.order_by(Appraisal.appraisal_date.desc()).limit(limit)
    rows = q.all()

    results = []
    for prop, appr, deal in rows:
        # 해당 물건 최신 경매 결과
        auction = (db.query(Auction)
            .filter_by(property_id=prop.id)
            .order_by(Auction.filing_date.desc())
            .first())
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


# ─── 낙찰가율 통계 ───────────────────────────────────────────────────────────

@router.get("/auction-stats", summary="낙찰가율 통계")
def get_auction_stats(
    property_type: str = Query(..., description="자산유형"),
    sido: Optional[str] = Query(None, description="시/도"),
    db: Session = Depends(get_db),
):
    return avm.auction_stats(db, property_type, sido)


# ─── 물건 상세 ───────────────────────────────────────────────────────────────

@router.get("/properties/{property_serial}", summary="물건 상세 조회")
def get_property(property_serial: str, db: Session = Depends(get_db)):
    prop = db.query(Property).filter_by(property_serial=property_serial).first()
    if not prop:
        raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다")

    appraisals = db.query(Appraisal).filter_by(property_id=prop.id).all()
    auctions = db.query(Auction).filter_by(property_id=prop.id).all()
    deal = db.query(Deal).filter_by(id=prop.deal_id).first()

    return {
        "property": {
            "serial": prop.property_serial,
            "address": prop.address_full,
            "type": prop.property_type,
            "category": prop.property_category,
            "land_area": prop.land_area,
            "building_area": prop.building_area,
            "mortgage_amount": int(prop.mortgage_amount) if prop.mortgage_amount else None,
            "senior_burden_total": int(prop.senior_burden_total) if prop.senior_burden_total else None,
            "kb_market_price": int(prop.kb_market_price) if prop.kb_market_price else None,
        },
        "deal": {
            "name": deal.deal_name if deal else None,
            "institution": deal.financial_institution if deal else None,
            "asset_date": str(deal.asset_date) if deal and deal.asset_date else None,
        },
        "appraisals": [
            {
                "type": a.appraisal_type,
                "date": str(a.appraisal_date),
                "appraiser": a.appraiser,
                "land_value": int(a.land_value) if a.land_value else None,
                "building_value": int(a.building_value) if a.building_value else None,
                "total_value": int(a.total_value) if a.total_value else None,
            }
            for a in appraisals
        ],
        "auctions": [
            {
                "court": a.court,
                "case_number": a.case_number,
                "first_legal_price": int(a.first_legal_price) if a.first_legal_price else None,
                "lapse_count": a.lapse_count,
                "final_result": a.final_result,
                "hammer_price": int(a.hammer_price) if a.hammer_price else None,
                "hammer_rate": round(
                    int(a.hammer_price) / int(
                        db.query(Appraisal).filter_by(property_id=prop.id)
                        .order_by(Appraisal.appraisal_date.desc()).first().total_value
                    ), 4
                ) if a.hammer_price and appraisals else None,
            }
            for a in auctions
        ],
    }
