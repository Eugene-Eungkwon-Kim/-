"""국토부 실거래가 API 응답 레코드를 DB에 적재한다.

실거래 기록은 특정 대출 담보물건(Property)에 종속되지 않는 독립적인 시장
데이터이므로 app/db/models.ComparableSale(거래사례 정밀 시트)에 적재한다 —
RAG/AVM 비교사례 검색이 이미 이 테이블을 읽는다. 자산 유형(아파트·상가·
공장창고·토지)마다 레코드 필드 구성이 달라 행 변환 함수만 바꾸고, 중복
방지(`transaction_key`)·커밋·오류 집계는 한 곳(_bulk_ingest)에서 처리한다.
"""

import logging
from typing import Any, Callable, Dict, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

RowBuilder = Callable[[Any], Dict[str, Any]]


def _address_fields(record: Any) -> Dict[str, Any]:
    from app.integrations.sgg_codes import sido_of, sigungu_of

    sido, sigungu = sido_of(record.sgg_code), sigungu_of(record.sgg_code)
    return {
        "address_full": f"{sido} {sigungu} {record.address_dong} {record.address_jibun}".strip(),
        "address_sido": sido,
        "address_sigungu": sigungu,
    }


def _bulk_ingest(db: Session, records: List[Any], build_row: RowBuilder, label: str) -> Dict[str, int]:
    """`transaction_key` 로 중복을 막으며 ComparableSale 에 적재한다.

    같은 지역·월을 다시 수집해도 동일 거래가 두 번 쌓이지 않는다.
    """
    from app.db.models import ComparableSale

    stats = {"inserted": 0, "skipped": 0, "errors": 0}
    for record in records:
        try:
            key = record.transaction_key
            exists = (
                db.query(ComparableSale.id)
                .filter(ComparableSale.transaction_key == key)
                .first()
            )
            if exists:
                stats["skipped"] += 1
                continue

            # case_index=1: 본건(0)이 아닌 독립 시장 거래사례
            db.add(ComparableSale(case_index=1, transaction_key=key, **build_row(record)))
            stats["inserted"] += 1
        except Exception as e:
            logger.warning(f"[db_ingest] {label} 레코드 적재 실패: {e}")
            stats["errors"] += 1

    db.commit()
    return stats


def _residential_row(record: Any) -> Dict[str, Any]:
    return {
        **_address_fields(record),
        "subject_property_serial": f"{record.sgg_code}-{record.complex_name}",
        "property_type": record.property_type,
        "building_area": record.exclusive_area,
        "trade_date": record.contract_date,
        "trade_amount": record.price_won,
        "note": f"{record.complex_name} {record.floor}층" if record.floor else record.complex_name,
    }


def _building_row(record: Any, property_type: str) -> Dict[str, Any]:
    return {
        **_address_fields(record),
        "subject_property_serial": f"{record.sgg_code}-{record.building_name}",
        "property_type": property_type,
        "land_area": record.land_area,
        "building_area": record.building_area,
        "trade_date": record.contract_date,
        "trade_amount": record.price_won,
        "note": record.building_name,
    }


def _land_row(record: Any) -> Dict[str, Any]:
    note = " ".join(part for part in (record.land_category, record.share_deal) if part)
    return {
        **_address_fields(record),
        "subject_property_serial": f"{record.sgg_code}-{record.address_dong}-{record.address_jibun}",
        "property_type": "토지",
        "use_zone": record.use_zone or None,
        "land_area": record.land_area,
        "building_area": None,
        "trade_date": record.contract_date,
        "trade_amount": record.price_won,
        "note": note or None,
    }


def bulk_ingest_transactions(db: Session, records: List[Any]) -> Dict[str, int]:
    """TransactionRecord(아파트·다세대·오피스텔) 리스트를 적재한다."""
    return _bulk_ingest(db, records, _residential_row, "주거용")


def bulk_ingest_commercial_transactions(db: Session, records: List[Any]) -> Dict[str, int]:
    """CommercialTransactionRecord(상업업무용) 리스트를 적재한다."""
    return _bulk_ingest(db, records, lambda r: _building_row(r, "상가"), "상업업무용")


def bulk_ingest_industrial_transactions(db: Session, records: List[Any]) -> Dict[str, int]:
    """IndustrialTransactionRecord(공장/창고) 리스트를 적재한다."""
    return _bulk_ingest(db, records, lambda r: _building_row(r, "공장창고"), "공장/창고")


def bulk_ingest_land_transactions(db: Session, records: List[Any]) -> Dict[str, int]:
    """LandTransactionRecord(토지) 리스트를 적재한다 — 건물면적 없이 대지면적·용도지역 중심."""
    return _bulk_ingest(db, records, _land_row, "토지")
