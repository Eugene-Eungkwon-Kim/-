"""국토부 실거래가 API 응답(TransactionRecord)을 DB에 적재한다.

scripts/fetch_transactions_parallel.py 가 이 모듈을 참조했지만 실체가
없었다. 실거래 기록은 특정 대출 담보물건(Property)에 종속되지 않는
독립적인 시장 데이터이므로, app/db/models.ComparableSale(거래사례 정밀
시트)에 적재한다 — RAG/AVM 비교사례 검색이 이미 이 테이블을 읽는다.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def bulk_ingest_transactions(db: Session, records: List[Any]) -> Dict[str, int]:
    """TransactionRecord 리스트를 ComparableSale 로 적재한다.

    `transaction_key` 로 중복을 막는다 — 같은 지역·월을 다시 수집해도
    동일 거래가 두 번 쌓이지 않는다.
    """
    from app.db.models import ComparableSale
    from app.integrations.sgg_codes import sido_of, sigungu_of

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

            db.add(ComparableSale(
                subject_property_serial=f"{record.sgg_code}-{record.complex_name}",
                case_index=1,  # 독립 시장 거래사례 (본건 아님)
                transaction_key=key,
                address_full=f"{sido_of(record.sgg_code)} {sigungu_of(record.sgg_code)} "
                             f"{record.address_dong} {record.address_jibun}".strip(),
                address_sido=sido_of(record.sgg_code),
                address_sigungu=sigungu_of(record.sgg_code),
                property_type=record.property_type,
                building_area=record.exclusive_area,
                trade_date=record.contract_date,
                trade_amount=record.price_won,
                note=f"{record.complex_name} {record.floor}층" if record.floor else record.complex_name,
            ))
            stats["inserted"] += 1
        except Exception as e:
            logger.warning(f"[db_ingest] 레코드 적재 실패: {e}")
            stats["errors"] += 1

    db.commit()
    return stats
