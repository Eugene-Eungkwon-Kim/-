import hashlib
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Complex, Transaction
from app.integrations.korea_api import TransactionRecord
from app.integrations.rtech_crawler import ComplexMaster
from app.integrations.sgg_codes import SGG_CODES

logger = logging.getLogger(__name__)


def _make_complex_from_master(master: ComplexMaster) -> Complex:
    return Complex(
        complex_code=master.complex_code,
        complex_name=master.complex_name,
        property_type=master.property_type,
        address_sido=master.address_sido,
        address_sigungu=master.address_sigungu,
        address_dong=master.address_dong,
        address_jibun=master.address_jibun,
        address_roadname=getattr(master, "address_roadname", ""),
        address_full=master.address_full,
        build_year=master.build_year,
        total_units=master.total_units,
        source=master.source,
        last_updated=datetime.utcnow(),
    )


def upsert_complex(session: Session, master: ComplexMaster) -> Complex:
    existing = session.query(Complex).filter_by(complex_code=master.complex_code).first()
    if existing:
        for k in ("complex_name", "address_sido", "address_sigungu", "address_dong",
                  "address_jibun", "address_full"):
            setattr(existing, k, getattr(master, k))
        if master.build_year:
            existing.build_year = master.build_year
        if master.total_units:
            existing.total_units = master.total_units
        existing.last_updated = datetime.utcnow()
        return existing
    obj = _make_complex_from_master(master)
    session.add(obj)
    return obj


def bulk_upsert_complexes(session: Session, masters: list[ComplexMaster], batch_size: int = 200) -> dict:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    for i, master in enumerate(masters):
        try:
            existing = session.query(Complex).filter_by(complex_code=master.complex_code).first()
            if existing:
                existing.last_updated = datetime.utcnow()
                stats["updated"] += 1
            else:
                session.add(_make_complex_from_master(master))
                stats["inserted"] += 1
            if (i + 1) % batch_size == 0:
                session.commit()
        except Exception as e:
            logger.warning(f"단지 적재 오류 ({master.complex_name}): {e}")
            session.rollback()
            stats["errors"] += 1
    session.commit()
    return stats


def _find_or_create_complex(session: Session, rec: TransactionRecord) -> Optional[Complex]:
    existing = (
        session.query(Complex)
        .filter_by(complex_name=rec.complex_name, property_type=rec.property_type,
                   address_dong=rec.address_dong)
        .first()
        or session.query(Complex)
        .filter_by(complex_name=rec.complex_name, property_type=rec.property_type)
        .first()
    )
    if existing:
        return existing

    sgg_parts = SGG_CODES.get(rec.sgg_code, "").split()
    sido, sigungu = (sgg_parts[0] if sgg_parts else ""), (sgg_parts[1] if len(sgg_parts) > 1 else "")
    auto_code = "API-" + hashlib.md5(
        f"{rec.sgg_code}|{rec.complex_name}|{rec.address_dong}|{rec.property_type}".encode()
    ).hexdigest()[:12]

    obj = Complex(
        complex_code=auto_code,
        complex_name=rec.complex_name,
        property_type=rec.property_type,
        address_sido=sido,
        address_sigungu=sigungu,
        address_dong=rec.address_dong,
        address_jibun=rec.address_jibun,
        address_full=f"{sido} {sigungu} {rec.address_dong} {rec.address_jibun}".strip(),
        build_year=rec.build_year,
        source="api",
        last_updated=datetime.utcnow(),
    )
    try:
        session.add(obj)
        session.flush()
        return obj
    except IntegrityError:
        session.rollback()
        return session.query(Complex).filter_by(complex_code=auto_code).first()


def ingest_transaction(session: Session, rec: TransactionRecord) -> bool:
    if session.query(Transaction).filter_by(transaction_key=rec.transaction_key).first():
        return False

    complex_obj = _find_or_create_complex(session, rec)
    if not complex_obj:
        return False

    price_per_area = rec.price_won / rec.exclusive_area if rec.exclusive_area > 0 else 0
    is_abnormal = not (500_000 <= price_per_area <= 500_000_000)

    session.add(Transaction(
        complex_id=complex_obj.id,
        transaction_key=rec.transaction_key,
        contract_year=rec.contract_year,
        contract_month=rec.contract_month,
        contract_day=rec.contract_day,
        contract_date=rec.contract_date,
        price=rec.price_won,
        price_per_area=round(price_per_area, 2),
        exclusive_area=rec.exclusive_area,
        floor=rec.floor,
        seller_type=rec.seller_type,
        buyer_type=rec.buyer_type,
        sgg_code=rec.sgg_code,
        property_type=rec.property_type,
        is_abnormal=is_abnormal,
        verified=False,
    ))
    return True


def bulk_ingest_transactions(session: Session, records: list[TransactionRecord], batch_size: int = 500) -> dict:
    stats = {"inserted": 0, "skipped": 0, "errors": 0}
    for i, rec in enumerate(records):
        try:
            if ingest_transaction(session, rec):
                stats["inserted"] += 1
            else:
                stats["skipped"] += 1
            if (i + 1) % batch_size == 0:
                session.commit()
        except Exception as e:
            logger.debug(f"거래 적재 오류: {e}")
            session.rollback()
            stats["errors"] += 1
    session.commit()
    return stats
