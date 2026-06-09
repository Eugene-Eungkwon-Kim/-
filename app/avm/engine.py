"""
AVM 핵심 엔진
- 비교사례 검색 (주소 유사도 + 면적 유사도)
- 헤도닉 회귀 기반 추정가
- 낙찰가율 통계
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.db.models import Property, Appraisal, Auction, Deal


@dataclass
class AVMResult:
    estimated_value: Optional[int]
    confidence: str                    # HIGH / MEDIUM / LOW
    comparable_count: int
    avg_appraisal: Optional[int]
    median_hammer_rate: Optional[float]  # 낙찰가율 (낙찰가/감정가)
    comparables: list


@dataclass
class Comparable:
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


def estimate(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
    land_area: Optional[float] = None,
    building_area: Optional[float] = None,
    max_comparables: int = 10,
) -> AVMResult:

    comps = _find_comparables(
        db, address_sido, address_sigungu, property_type,
        land_area, building_area, max_comparables
    )

    if not comps:
        return AVMResult(
            estimated_value=None,
            confidence="LOW",
            comparable_count=0,
            avg_appraisal=None,
            median_hammer_rate=None,
            comparables=[],
        )

    values = [c.appraisal_value for c in comps if c.appraisal_value]
    hammer_rates = [c.hammer_rate for c in comps if c.hammer_rate]

    avg_val = int(sum(values) / len(values)) if values else None
    median_rate = _median(hammer_rates) if hammer_rates else None

    confidence = "HIGH" if len(comps) >= 5 else ("MEDIUM" if len(comps) >= 2 else "LOW")

    return AVMResult(
        estimated_value=avg_val,
        confidence=confidence,
        comparable_count=len(comps),
        avg_appraisal=avg_val,
        median_hammer_rate=median_rate,
        comparables=comps,
    )


def _find_comparables(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
    land_area: Optional[float],
    building_area: Optional[float],
    limit: int,
) -> list[Comparable]:

    # 동일 시군구, 유사 자산유형 조건
    # 최신 감정평가 1건만 조인 (중복 방지)
    latest_appr = (
        db.query(
            Appraisal.property_id,
            func.max(Appraisal.appraisal_date).label("max_date"),
        )
        .group_by(Appraisal.property_id)
        .subquery()
    )

    q = (
        db.query(Property, Appraisal, Auction, Deal)
        .join(latest_appr, latest_appr.c.property_id == Property.id)
        .join(
            Appraisal,
            and_(
                Appraisal.property_id == Property.id,
                Appraisal.appraisal_date == latest_appr.c.max_date,
            ),
        )
        .join(Auction, Auction.property_id == Property.id, isouter=True)
        .join(Deal, Deal.id == Property.deal_id)
        .filter(
            Property.address_sido == address_sido,
            Property.address_sigungu == address_sigungu,
            Property.property_type.ilike(f"%{property_type}%"),
            Appraisal.total_value.isnot(None),
            Appraisal.total_value > 0,
        )
        .order_by(Appraisal.appraisal_date.desc())
        .limit(limit * 3)
    )

    results = q.all()

    # 면적 유사도 필터링
    # property_id 중복 제거 (경매 여러 건 조인 방지)
    seen_prop_ids = set()
    scored = []
    for prop, appr, auction, deal in results:
        if appr is None or prop.id in seen_prop_ids:
            continue
        seen_prop_ids.add(prop.id)
        score = _area_similarity_score(
            prop.land_area, prop.building_area,
            land_area, building_area,
        )
        scored.append((score, prop, appr, auction, deal))

    scored.sort(key=lambda x: x[0], reverse=True)

    comps = []
    for score, prop, appr, auction, deal in scored[:limit]:
        appr_val = int(appr.total_value) if appr.total_value else None
        hammer = int(auction.hammer_price) if auction and auction.hammer_price else None
        rate = round(hammer / appr_val, 4) if (hammer and appr_val and appr_val > 0) else None

        comps.append(Comparable(
            property_serial=prop.property_serial or "",
            address=prop.address_full or "",
            property_type=prop.property_type or "",
            land_area=prop.land_area,
            building_area=prop.building_area,
            appraisal_date=str(appr.appraisal_date) if appr.appraisal_date else "",
            appraisal_value=appr_val or 0,
            hammer_price=hammer,
            hammer_rate=rate,
            deal_name=deal.deal_name or "",
        ))

    return comps


def _area_similarity_score(
    prop_land, prop_bld,
    query_land, query_bld,
) -> float:
    """면적 유사도 점수 (0~1), 쿼리 면적 없으면 0.5 고정"""
    scores = []
    if query_land and prop_land:
        ratio = min(query_land, prop_land) / max(query_land, prop_land)
        scores.append(ratio)
    if query_bld and prop_bld:
        ratio = min(query_bld, prop_bld) / max(query_bld, prop_bld)
        scores.append(ratio)
    return sum(scores) / len(scores) if scores else 0.5


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def auction_stats(
    db: Session,
    property_type: str,
    address_sido: Optional[str] = None,
) -> dict:
    """자산유형별 낙찰가율 통계"""
    from sqlalchemy import cast, Float as SAFloat
    q = (
        db.query(
            Auction.final_result,
            func.count(Auction.id).label("count"),
            func.avg(
                cast(Auction.hammer_price, SAFloat) / cast(Appraisal.total_value, SAFloat)
            ).label("avg_hammer_rate"),
        )
        .join(Property, Property.id == Auction.property_id)
        .join(Appraisal, Appraisal.property_id == Property.id)
        .filter(
            Property.property_type.ilike(f"%{property_type}%"),
            Auction.hammer_price.isnot(None),
            Auction.hammer_price != 0,
            Appraisal.total_value.isnot(None),
            Appraisal.total_value != 0,
        )
    )
    if address_sido:
        q = q.filter(Property.address_sido == address_sido)

    q = q.group_by(Auction.final_result)
    rows = q.all()

    return {
        "property_type": property_type,
        "address_sido": address_sido,
        "stats": [
            {
                "result": r.final_result,
                "count": r.count,
                "avg_hammer_rate": round(r.avg_hammer_rate, 4) if r.avg_hammer_rate else None,
            }
            for r in rows
        ],
    }
