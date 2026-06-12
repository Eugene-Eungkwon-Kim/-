import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.db.database import get_db
from app.db.models import Property, Appraisal, Auction, Deal, ComparableSale
from app.utils.export_utils import export_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


@router.get(
    "/precedents",
    summary="전례 데이터 내보내기",
    description="조회된 전례 데이터를 다양한 포맷으로 내보냅니다",
)
def export_precedents(
    format: str = Query("csv", pattern="^(csv|excel|json)$"),
    sido: Optional[str] = Query(None),
    sigungu: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    limit: int = Query(1000, le=10000),
    db: Session = Depends(get_db),
):
    """
    조건에 맞는 전례 데이터를 다운로드합니다.

    **포맷**: csv, excel, json
    """
    try:
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
            db.query(Property, Appraisal, Deal, Auction)
            .outerjoin(latest_appr_sub, latest_appr_sub.c.property_id == Property.id)
            .outerjoin(
                Appraisal,
                (Appraisal.property_id == Property.id)
                & (Appraisal.appraisal_date == latest_appr_sub.c.max_date),
            )
            .join(Deal, Deal.id == Property.deal_id)
            .outerjoin(Auction, Auction.property_id == Property.id)
        )

        if sido:
            q = q.filter(Property.address_sido == sido)
        if sigungu:
            q = q.filter(Property.address_sigungu == sigungu)
        if property_type:
            q = q.filter(Property.property_type == property_type)
        if min_area:
            q = q.filter(Property.building_area >= min_area)
        if max_area:
            q = q.filter(Property.building_area <= max_area)

        results = q.limit(limit).all()

        if not results:
            raise HTTPException(status_code=404, detail="일치하는 데이터가 없습니다")

        data = []
        for prop, appraisal, deal, auction in results:
            appr_val = int(appraisal.total_value) if appraisal and appraisal.total_value else None
            hammer = int(auction.hammer_price) if auction and auction.hammer_price else None
            hammer_rate = round(hammer / appr_val, 4) if (hammer and appr_val) else None
            data.append({
                "물건번호": prop.property_serial,
                "주소": prop.address_full,
                "자산유형": prop.property_type,
                "대지면적_sqm": prop.land_area,
                "건물면적_sqm": prop.building_area,
                "감정평가액": appr_val,
                "감정일자": str(appraisal.appraisal_date) if appraisal else None,
                "낙찰가": hammer,
                "낙찰가율": hammer_rate,
                "딜명": deal.deal_name if deal else None,
                "금융기관": deal.financial_institution if deal else None,
            })

        file_data = export_manager.export_data(data=data, format=format)
        filename = f"precedents.{export_manager.get_file_extension(format)}"

        return StreamingResponse(
            iter([file_data]),
            media_type=export_manager.get_content_type(format),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전례 데이터 내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/comparables",
    summary="비교사례 데이터 내보내기",
    description="거래사례 정밀 시트 데이터를 내보냅니다",
)
def export_comparables(
    sido: str = Query(..., description="시/도"),
    sigungu: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|excel|json)$"),
    limit: int = Query(1000, le=10000),
    db: Session = Depends(get_db),
):
    try:
        q = db.query(ComparableSale).filter(ComparableSale.address_sido == sido)
        if sigungu:
            q = q.filter(ComparableSale.address_sigungu.ilike(f"%{sigungu}%"))
        if property_type:
            q = q.filter(ComparableSale.property_type.ilike(f"%{property_type}%"))

        rows = q.order_by(ComparableSale.trade_date.desc()).limit(limit).all()

        if not rows:
            raise HTTPException(status_code=404, detail="일치하는 거래사례가 없습니다")

        data = [
            {
                "본건물건번호": sale.subject_property_serial,
                "주소": sale.address_full,
                "자산유형": sale.property_type,
                "용도지역": sale.use_zone,
                "대지면적_sqm": sale.land_area,
                "건물면적_sqm": sale.building_area,
                "구조": sale.structure,
                "거래금액": int(sale.trade_amount) if sale.trade_amount else None,
                "거래일자": str(sale.trade_date) if sale.trade_date else None,
                "평당단가": sale.unit_price_py,
                "토지단가_sqm": sale.land_price_sqm,
                "비고": sale.note,
            }
            for sale in rows
        ]

        file_data = export_manager.export_data(data=data, format=format)
        filename = f"comparables.{export_manager.get_file_extension(format)}"

        return StreamingResponse(
            iter([file_data]),
            media_type=export_manager.get_content_type(format),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비교사례 내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats", summary="지원 내보내기 포맷 목록")
def get_supported_formats():
    return {
        "formats": [
            {"name": "csv", "extension": "csv", "content_type": "text/csv"},
            {
                "name": "excel",
                "extension": "xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            {"name": "json", "extension": "json", "content_type": "application/json"},
        ]
    }
