"""
AVM 핵심 엔진
- 비교사례 검색 (주소 + 면적 유사도)
- 단가(원/㎡) 기반 가중 추정가 — 면적 유사도를 가중치로 활용
- 낙찰가율 통계
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.db.models import Property, Appraisal, Auction, Deal, ComparableSale


@dataclass
class AVMResult:
    estimated_value: Optional[int]
    confidence: str                     # HIGH / MEDIUM / LOW
    comparable_count: int
    avg_appraisal: Optional[int]
    median_hammer_rate: Optional[float]
    unit_price_per_sqm: Optional[int]   # 추정 단가 (원/㎡)
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
    source_type: str  # "appraisal" | "transaction"


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
            unit_price_per_sqm=None,
            comparables=[],
        )

    values = [c.appraisal_value for c in comps if c.appraisal_value]
    hammer_rates = [c.hammer_rate for c in comps if c.hammer_rate]
    median_rate = _median(hammer_rates) if hammer_rates else None

    # 단가(원/㎡) 기반 가중 추정
    estimated_value, unit_price = _weighted_estimate(comps, building_area)

    # 단순 평균 (fallback)
    avg_val = int(sum(values) / len(values)) if values else None
    if estimated_value is None:
        estimated_value = avg_val

    # 신뢰도: 비교사례 수 + 단가 변동계수(CV)
    confidence = _confidence(comps, values)

    return AVMResult(
        estimated_value=estimated_value,
        confidence=confidence,
        comparable_count=len(comps),
        avg_appraisal=avg_val,
        median_hammer_rate=median_rate,
        unit_price_per_sqm=unit_price,
        comparables=comps,
    )


def _weighted_estimate(
    comps: list,
    target_building_area: Optional[float],
) -> tuple[Optional[int], Optional[int]]:
    """
    면적 유사도를 가중치로 한 단가(원/㎡) 기반 추정.
    target_building_area 가 없으면 None 반환.
    """
    if not target_building_area or target_building_area <= 0:
        return None, None

    weighted_sum = 0.0
    weight_total = 0.0

    for comp in comps:
        if not comp.appraisal_value or not comp.building_area or comp.building_area <= 0:
            continue
        unit_price = comp.appraisal_value / comp.building_area
        # 면적 유사도 → 가중치 (유사할수록 높은 가중치)
        area_ratio = min(target_building_area, comp.building_area) / max(target_building_area, comp.building_area)
        weighted_sum += unit_price * area_ratio
        weight_total += area_ratio

    if weight_total == 0:
        return None, None

    avg_unit_price = weighted_sum / weight_total
    estimated = int(avg_unit_price * target_building_area)
    return estimated, int(avg_unit_price)


def _confidence(comps: list, values: list) -> str:
    """
    비교사례 수와 단가 분산(CV)으로 신뢰도 산출.
    CV < 0.15 → HIGH, < 0.30 → MEDIUM, 그 이상 → LOW
    """
    n = len(comps)
    if n == 0:
        return "LOW"
    if n < 2:
        return "LOW"

    unit_prices = [
        c.appraisal_value / c.building_area
        for c in comps
        if c.appraisal_value and c.building_area and c.building_area > 0
    ]
    if len(unit_prices) >= 2:
        mean = sum(unit_prices) / len(unit_prices)
        if mean > 0:
            std = (sum((p - mean) ** 2 for p in unit_prices) / len(unit_prices)) ** 0.5
            cv = std / mean
            if n >= 5 and cv < 0.15:
                return "HIGH"
            if n >= 3 and cv < 0.30:
                return "MEDIUM"
            return "LOW"

    return "HIGH" if n >= 5 else ("MEDIUM" if n >= 2 else "LOW")


def _find_comparables(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
    land_area: Optional[float],
    building_area: Optional[float],
    limit: int,
) -> list[Comparable]:

    scored = []

    # 1. Appraisal 기반 비교사례 (최신 감정평가만)
    latest_appr = (
        db.query(
            Appraisal.property_id,
            func.max(Appraisal.appraisal_date).label("max_date"),
        )
        .group_by(Appraisal.property_id)
        .subquery()
    )

    q_appr = (
        db.query(Property, Appraisal, Auction, Deal)
        .join(latest_appr, latest_appr.c.property_id == Property.id)
        .join(
            Appraisal,
            and_(
                Appraisal.property_id == Property.id,
                Appraisal.appraisal_date == latest_appr.c.max_date,
            ),
        )
        .outerjoin(Auction, Auction.property_id == Property.id)
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

    seen_prop_ids = set()
    for prop, appr, auction, deal in q_appr.all():
        if prop.id in seen_prop_ids:
            continue
        seen_prop_ids.add(prop.id)
        score = _area_similarity_score(prop.land_area, prop.building_area, land_area, building_area)
        scored.append((score, "appraisal", prop, appr, auction, deal))

    # 2. ComparableSale 기반 비교사례 (거래사례 정밀 시트)
    q_sales = (
        db.query(ComparableSale)
        .filter(
            ComparableSale.address_sido == address_sido,
            ComparableSale.address_sigungu.ilike(f"%{address_sigungu}%"),
            ComparableSale.property_type.ilike(f"%{property_type}%"),
            ComparableSale.trade_amount.isnot(None),
            ComparableSale.trade_amount > 0,
            ComparableSale.case_index > 0,
        )
        .order_by(ComparableSale.trade_date.desc())
        .limit(limit * 3)
    )

    for sale in q_sales.all():
        score = _area_similarity_score(sale.land_area, sale.building_area, land_area, building_area)
        scored.append((score, "transaction", sale, None, None, None))

    scored.sort(key=lambda x: x[0], reverse=True)

    comps = []
    for score, src_type, obj1, obj2, obj3, obj4 in scored[:limit]:
        if src_type == "appraisal":
            prop, appr, auction, deal = obj1, obj2, obj3, obj4
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
                source_type="appraisal",
            ))
        else:
            sale = obj1
            trade_val = int(sale.trade_amount) if sale.trade_amount else None
            comps.append(Comparable(
                property_serial=sale.subject_property_serial or "",
                address=sale.address_full or "",
                property_type=sale.property_type or "",
                land_area=sale.land_area,
                building_area=sale.building_area,
                appraisal_date=str(sale.trade_date) if sale.trade_date else "",
                appraisal_value=trade_val or 0,
                hammer_price=None,
                hammer_rate=None,
                deal_name=f"거래사례 ({sale.subject_property_serial})",
                source_type="transaction",
            ))

    return comps


def _area_similarity_score(
    prop_land, prop_bld,
    query_land, query_bld,
) -> float:
    scores = []
    if query_land and prop_land:
        scores.append(min(query_land, prop_land) / max(query_land, prop_land))
    if query_bld and prop_bld:
        scores.append(min(query_bld, prop_bld) / max(query_bld, prop_bld))
    return sum(scores) / len(scores) if scores else 0.5


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]


def auction_stats(
    db: Session,
    property_type: str,
    address_sido: Optional[str] = None,
) -> dict:
    """자산유형별 낙찰가율 통계 — 최신 감정평가 기준"""
    from sqlalchemy import cast, Float as SAFloat

    # 최신 감정평가만 사용 (중복 제거)
    latest_appr = (
        db.query(
            Appraisal.property_id,
            func.max(Appraisal.appraisal_date).label("max_date"),
        )
        .group_by(Appraisal.property_id)
        .subquery()
    )

    q = (
        db.query(
            Auction.final_result,
            func.count(Auction.id).label("count"),
            func.avg(
                cast(Auction.hammer_price, SAFloat) / cast(Appraisal.total_value, SAFloat)
            ).label("avg_hammer_rate"),
            func.min(
                cast(Auction.hammer_price, SAFloat) / cast(Appraisal.total_value, SAFloat)
            ).label("min_hammer_rate"),
            func.max(
                cast(Auction.hammer_price, SAFloat) / cast(Appraisal.total_value, SAFloat)
            ).label("max_hammer_rate"),
        )
        .join(Property, Property.id == Auction.property_id)
        .join(latest_appr, latest_appr.c.property_id == Property.id)
        .join(
            Appraisal,
            and_(
                Appraisal.property_id == Property.id,
                Appraisal.appraisal_date == latest_appr.c.max_date,
            ),
        )
        .filter(
            Property.property_type.ilike(f"%{property_type}%"),
            Auction.hammer_price.isnot(None),
            Auction.hammer_price > 0,
            Appraisal.total_value.isnot(None),
            Appraisal.total_value > 0,
        )
    )
    if address_sido:
        q = q.filter(Property.address_sido == address_sido)

    rows = q.group_by(Auction.final_result).all()

    return {
        "property_type": property_type,
        "address_sido": address_sido,
        "stats": [
            {
                "result": r.final_result,
                "count": r.count,
                "avg_hammer_rate": round(r.avg_hammer_rate, 4) if r.avg_hammer_rate else None,
                "min_hammer_rate": round(r.min_hammer_rate, 4) if r.min_hammer_rate else None,
                "max_hammer_rate": round(r.max_hammer_rate, 4) if r.max_hammer_rate else None,
            }
            for r in rows
        ],
    }
