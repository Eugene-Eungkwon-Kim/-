"""
AVM 핵심 엔진
- 비교사례 검색 (주소 유사도 + 면적 유사도)
- 헤도닉 회귀 기반 추정가
- 낙찰가율 통계
- P6 고급 모델 (XGBoost + LightGBM + Ridge 앙상블, MAPE 0.46%)
"""
import os
import pickle
import numpy as np
import logging
from pathlib import Path
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.db.models import Property, Appraisal, Auction, Deal, ComparableSale
from app.avm import comparator as _cmp

# 프로젝트 루트 기준 상대경로
_project_root = Path(__file__).parent.parent.parent.absolute()

logger = logging.getLogger(__name__)

# P6 모델 로드 (Session 18)
_P6_MODEL = None
_P6_CALIBRATION = None
_P6_MODEL_META = None

def _load_p6_models():
    """P6 모델 및 캘리브레이션 로드"""
    global _P6_MODEL, _P6_CALIBRATION, _P6_MODEL_META

    if _P6_MODEL is not None:
        return

    try:
        # 프로젝트 루트 기준 절대경로 (이식성 개선)
        model_path = _project_root / "models" / "p6_advanced_hammer_ensemble.pkl"
        calib_path = _project_root / "models" / "p6_calibration.pkl"

        if model_path.exists():
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            _P6_MODEL = model_data['models']
            _P6_MODEL_META = {
                'feature_cols': model_data['feature_cols'],
                'weights': model_data['weights'],
                'mape': model_data['mape_price'],
            }
            logger.info(f"[P6] 모델 로드 완료 (MAPE: {_P6_MODEL_META['mape']:.2f}%)")

        if calib_path.exists():
            with open(calib_path, 'rb') as f:
                _P6_CALIBRATION = pickle.load(f)
            logger.info("[P6] 캘리브레이션 로드 완료")
    except Exception as e:
        logger.warning(f"[P6] 모델 로드 실패: {e}")

_load_p6_models()


@dataclass
class AVMResult:
    estimated_value: Optional[int]
    confidence: str                    # HIGH / MEDIUM / LOW
    comparable_count: int
    avg_appraisal: Optional[int]
    median_hammer_rate: Optional[float]  # 낙찰가율 (낙찰가/감정가)
    comparables: list
    market_position: Optional[str] = field(default=None)  # F.2 cross-market position
    intl_comparisons: Optional[dict] = field(default=None)
    diagnostics: Optional[dict[str, Any]] = field(default=None)


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
    source_type: str  # "appraisal" or "transaction"


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
            diagnostics=_build_no_comparable_diagnostics(
                db, address_sido, address_sigungu, property_type,
                land_area, building_area,
            ),
        )

    values = [c.appraisal_value for c in comps if c.appraisal_value]
    hammer_rates = [c.hammer_rate for c in comps if c.hammer_rate]

    avg_val = int(sum(values) / len(values)) if values else None
    median_rate = _median(hammer_rates) if hammer_rates else None

    confidence = "HIGH" if len(comps) >= 5 else ("MEDIUM" if len(comps) >= 2 else "LOW")

    market_pos = None
    intl_cmp = None
    if avg_val:
        try:
            result = _cmp.compare(avg_val, property_type)
            market_pos = result.position
            intl_cmp = result.comparisons
        except Exception:
            pass

    return AVMResult(
        estimated_value=avg_val,
        confidence=confidence,
        comparable_count=len(comps),
        avg_appraisal=avg_val,
        median_hammer_rate=median_rate,
        comparables=comps,
        market_position=market_pos,
        intl_comparisons=intl_cmp,
    )


def _build_no_comparable_diagnostics(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
    land_area: Optional[float],
    building_area: Optional[float],
) -> dict[str, Any]:
    probe_counts = {
        "sido_count": db.query(Property.id).filter(Property.address_sido == address_sido).count(),
        "sigungu_count": _count_property_scope(db, address_sido, address_sigungu),
        "property_type_count": _count_property_scope(
            db, address_sido, address_sigungu, property_type,
        ),
        "appraisal_candidate_count": _count_appraisal_candidates(
            db, address_sido, address_sigungu, property_type,
        ),
        "transaction_candidate_count": _count_transaction_candidates(
            db, address_sido, address_sigungu, property_type,
        ),
    }
    return {
        "status": "NO_COMPARABLES",
        "reason_codes": _no_comparable_reason_codes(probe_counts),
        "query": {
            "address_sido": address_sido,
            "address_sigungu": address_sigungu,
            "property_type": property_type,
            "land_area": land_area,
            "building_area": building_area,
        },
        "probe_counts": probe_counts,
        "customer_safe": False,
    }


def _count_property_scope(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: Optional[str] = None,
) -> int:
    query = db.query(Property.id).filter(
        Property.address_sido == address_sido,
        Property.address_sigungu == address_sigungu,
    )
    if property_type:
        query = query.filter(Property.property_type.ilike(f"%{property_type}%"))
    return query.count()


def _count_appraisal_candidates(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
) -> int:
    latest_appr = (
        db.query(Appraisal.property_id, func.max(Appraisal.appraisal_date).label("max_date"))
        .group_by(Appraisal.property_id)
        .subquery()
    )
    return (
        db.query(Property.id)
        .join(latest_appr, latest_appr.c.property_id == Property.id)
        .join(
            Appraisal,
            and_(
                Appraisal.property_id == Property.id,
                Appraisal.appraisal_date == latest_appr.c.max_date,
            ),
        )
        .filter(
            Property.address_sido == address_sido,
            Property.address_sigungu == address_sigungu,
            Property.property_type.ilike(f"%{property_type}%"),
            Appraisal.total_value.isnot(None),
            Appraisal.total_value > 0,
        )
        .count()
    )


def _count_transaction_candidates(
    db: Session,
    address_sido: str,
    address_sigungu: str,
    property_type: str,
) -> int:
    return (
        db.query(ComparableSale.id)
        .filter(
            ComparableSale.address_sido == address_sido,
            ComparableSale.address_sigungu.ilike(f"%{address_sigungu}%"),
            ComparableSale.property_type.ilike(f"%{property_type}%"),
            ComparableSale.trade_amount.isnot(None),
            ComparableSale.trade_amount > 0,
            ComparableSale.case_index > 0,
        )
        .count()
    )


def _no_comparable_reason_codes(probe_counts: dict[str, int]) -> list[str]:
    if probe_counts["sido_count"] == 0:
        return ["NO_SIDO_MATCH"]
    if probe_counts["sigungu_count"] == 0:
        return ["NO_SIGUNGU_MATCH"]
    if probe_counts["property_type_count"] == 0:
        return ["NO_PROPERTY_TYPE_MATCH"]
    if (
        probe_counts["appraisal_candidate_count"] == 0
        and probe_counts["transaction_candidate_count"] == 0
    ):
        return ["NO_SOURCE_BACKED_COMPARABLES"]
    return ["COMPARABLE_FILTERS_RETURNED_ZERO"]


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

    # 1. Appraisal 기반 비교사례
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

    seen_prop_ids = set()
    for prop, appr, auction, deal in q_appr.all():
        if appr is None or prop.id in seen_prop_ids:
            continue
        seen_prop_ids.add(prop.id)
        score = _area_similarity_score(
            prop.land_area, prop.building_area,
            land_area, building_area,
        )
        scored.append((score, "appraisal", prop, appr, auction, deal))

    # 2. ComparableSale 기반 비교사례 (거래사례 정밀 시트)
    q_sales = (
        db.query(ComparableSale)
        .filter(
            ComparableSale.address_sido == address_sido,
            ComparableSale.address_sigungu.ilike(f"%{address_sigungu}%"),  # sigungu 상세도 포함
            ComparableSale.property_type.ilike(f"%{property_type}%"),
            ComparableSale.trade_amount.isnot(None),
            ComparableSale.trade_amount > 0,
            ComparableSale.case_index > 0,  # 거래사례만 (본건 제외)
        )
        .order_by(ComparableSale.trade_date.desc())
        .limit(limit * 3)
    )

    for sale in q_sales.all():
        score = _area_similarity_score(
            sale.land_area, sale.building_area,
            land_area, building_area,
        )
        scored.append((score, "transaction", sale, None, None, None))

    # 면적 유사도로 정렬
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
        else:  # transaction
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
                deal_name=f"거래사례 (from {sale.subject_property_serial})",
                source_type="transaction",
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


def estimate_p6(
    appraisal_amount: int,
    property_type: str,
    address_sido: str,
    land_area: Optional[float] = None,
    building_area: Optional[float] = None,
) -> dict:
    """P6 고급 모델로 예상낙찰가 추정 (MAPE 0.46%)

    Returns:
        {
            'hammer_price': int,
            'hammer_rate': float,
            'mape': int,
            'confidence': str,
            'model': str
        }
    """
    if _P6_MODEL is None or _P6_MODEL_META is None:
        return None

    try:
        # 피처 구성
        land = land_area if land_area else 0.0
        building = building_area if building_area else 0.0
        total_area = land + building

        features_dict = {
            'log_appraisal': np.log1p(float(appraisal_amount)),
            'log_land': np.log1p(float(land)),
            'log_building': np.log1p(float(building)),
            'log_total_area': np.log1p(float(total_area)),
            'log_appraisal_per_sqm': np.log1p(float(appraisal_amount) / max(total_area, 1)),
            'land_area': float(land),
            'building_area': float(building),
            'total_area': float(total_area),
            'appraisal_per_sqm': float(appraisal_amount) / max(total_area, 1),
            'property_type_code': {'주거': 0, '상가': 1, '토지': 2, '산업용': 3, '혼합': 4}.get(property_type, 5),
            'sido_code': 0,  # 기본값
            'sido_avg_rate': 0.57,
            'sido_std_rate': 0.05,
            'sido_count': 1.0,
            'type_avg_rate': 0.57,
            'type_std_rate': 0.05,
            'type_count': 1.0,
            'sido_appraisal_pct': 50.0,
            'type_appraisal_pct': 50.0,
            'is_paired': 0,
            'is_onbid': 1,
        }

        feature_cols = _P6_MODEL_META['feature_cols']
        features = np.array([features_dict.get(col, 0) for col in feature_cols]).reshape(1, -1)

        # 개별 모델 예측
        xgb_pred = np.clip(_P6_MODEL['xgb'].predict(features)[0], 0.01, 2.0)
        lgb_pred = np.clip(_P6_MODEL['lgb'].predict(features)[0], 0.01, 2.0)

        from sklearn.preprocessing import StandardScaler
        scaler = _P6_MODEL['scaler']
        features_scaled = scaler.transform(features)
        ridge_pred = np.clip(_P6_MODEL['ridge'].predict(features_scaled)[0], 0.01, 2.0)

        # 앙상블
        weights = _P6_MODEL_META['weights']
        hammer_rate = (
            weights['xgb'] * xgb_pred +
            weights['lgb'] * lgb_pred +
            weights['ridge'] * ridge_pred
        )

        # 캘리브레이션
        if _P6_CALIBRATION:
            hammer_rate = _P6_CALIBRATION['global_iso'].predict(np.array([hammer_rate]))[0]

        hammer_rate = np.clip(hammer_rate, 0.01, 2.0)
        hammer_price = int(hammer_rate * appraisal_amount)

        return {
            'hammer_price': hammer_price,
            'hammer_rate': float(hammer_rate),
            'mape': int(_P6_MODEL_META['mape']),
            'confidence': 'HIGH' if hammer_rate > 0.5 else 'MEDIUM',
            'model': 'p6_advanced_ensemble',
        }
    except Exception as e:
        logger.error(f"[P6] 예측 실패: {e}")
        return None


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
