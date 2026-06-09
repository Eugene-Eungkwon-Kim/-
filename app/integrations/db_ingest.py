"""
공공API 데이터 → DB 적재 모듈

TransactionRecord → Transaction 테이블
ComplexMaster    → Complex 테이블
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Complex, Transaction, Unit
from app.integrations.korea_api import TransactionRecord
from app.integrations.rtech_crawler import ComplexMaster

logger = logging.getLogger(__name__)


# ─── Complex 적재 ─────────────────────────────────────────────

def upsert_complex(session: Session, master: ComplexMaster) -> Complex:
    """
    ComplexMaster → complexes 테이블 UPSERT

    complex_code 기준으로 중복 방지
    """
    # 기존 데이터 조회
    existing = session.query(Complex).filter(
        Complex.complex_code == master.complex_code
    ).first()

    if existing:
        # 업데이트 (최신 정보로)
        existing.complex_name = master.complex_name
        existing.address_sido = master.address_sido
        existing.address_sigungu = master.address_sigungu
        existing.address_dong = master.address_dong
        existing.address_jibun = master.address_jibun
        existing.address_roadname = master.address_roadname
        existing.address_full = master.address_full
        if master.build_year:
            existing.build_year = master.build_year
        if master.total_units:
            existing.total_units = master.total_units
        existing.last_updated = datetime.utcnow()
        return existing
    else:
        # 신규 생성
        complex_obj = Complex(
            complex_code=master.complex_code,
            complex_name=master.complex_name,
            property_type=master.property_type,
            address_sido=master.address_sido,
            address_sigungu=master.address_sigungu,
            address_dong=master.address_dong,
            address_jibun=master.address_jibun,
            address_roadname=master.address_roadname,
            address_full=master.address_full,
            build_year=master.build_year,
            total_units=master.total_units,
            source=master.source,
            last_updated=datetime.utcnow(),
        )
        session.add(complex_obj)
        return complex_obj


def bulk_upsert_complexes(session: Session,
                          masters: list[ComplexMaster],
                          batch_size: int = 200) -> dict:
    """
    단지 마스터 일괄 UPSERT

    Returns:
        {'inserted': N, 'updated': N, 'errors': N}
    """
    stats = {"inserted": 0, "updated": 0, "errors": 0}

    for i, master in enumerate(masters):
        try:
            existing = session.query(Complex).filter(
                Complex.complex_code == master.complex_code
            ).first()

            if existing:
                existing.last_updated = datetime.utcnow()
                stats["updated"] += 1
            else:
                complex_obj = Complex(
                    complex_code=master.complex_code,
                    complex_name=master.complex_name,
                    property_type=master.property_type,
                    address_sido=master.address_sido,
                    address_sigungu=master.address_sigungu,
                    address_dong=master.address_dong,
                    address_jibun=master.address_jibun,
                    address_full=master.address_full,
                    build_year=master.build_year,
                    total_units=master.total_units,
                    source=master.source,
                    last_updated=datetime.utcnow(),
                )
                session.add(complex_obj)
                stats["inserted"] += 1

            # 배치 커밋
            if (i + 1) % batch_size == 0:
                session.commit()
                logger.info(f"  단지 진행: {i+1}/{len(masters)}")

        except Exception as e:
            logger.warning(f"단지 적재 오류 ({master.complex_name}): {e}")
            session.rollback()
            stats["errors"] += 1

    session.commit()
    return stats


# ─── Transaction 적재 ─────────────────────────────────────────

def find_or_create_complex_for_transaction(session: Session,
                                            rec: TransactionRecord) -> Optional[Complex]:
    """
    거래 레코드에서 단지 참조 조회/생성

    전략:
    1. complex_name + address_dong 으로 exact match
    2. 없으면 임시 Complex 레코드 생성
    """
    # 1. 정확 매칭 (단지명 + 법정동)
    existing = session.query(Complex).filter(
        Complex.complex_name == rec.complex_name,
        Complex.address_dong == rec.address_dong,
        Complex.property_type == rec.property_type,
    ).first()

    if existing:
        return existing

    # 2. 단지명만 매칭 (법정동 다를 수 있음)
    existing = session.query(Complex).filter(
        Complex.complex_name == rec.complex_name,
        Complex.property_type == rec.property_type,
    ).first()

    if existing:
        return existing

    # 3. 임시 Complex 생성 (API 거래 데이터 기반)
    # sgg_code → sido, sigungu 역매핑
    from app.integrations.sgg_codes import SGG_CODES
    sgg_name = SGG_CODES.get(rec.sgg_code, "")
    parts = sgg_name.split()
    sido = parts[0] if parts else ""
    sigungu = parts[1] if len(parts) > 1 else ""

    import hashlib
    code_raw = f"{rec.sgg_code}|{rec.complex_name}|{rec.address_dong}|{rec.property_type}"
    auto_code = "API-" + hashlib.md5(code_raw.encode()).hexdigest()[:12]

    complex_obj = Complex(
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
        session.add(complex_obj)
        session.flush()  # ID 확보 (commit 전)
        return complex_obj
    except IntegrityError:
        session.rollback()
        # 동시 삽입 경쟁 → 재조회
        return session.query(Complex).filter(
            Complex.complex_code == auto_code
        ).first()


def ingest_transaction(session: Session, rec: TransactionRecord) -> bool:
    """
    TransactionRecord → transactions 테이블 저장

    Returns:
        True if inserted, False if duplicate or error
    """
    # 중복 확인
    existing = session.query(Transaction).filter(
        Transaction.transaction_key == rec.transaction_key
    ).first()

    if existing:
        return False  # 이미 있음

    # 단지 참조 확보
    complex_obj = find_or_create_complex_for_transaction(session, rec)
    if not complex_obj:
        logger.warning(f"단지 생성 실패: {rec.complex_name}")
        return False

    # 이상거래 체크 (간단한 상한 필터)
    is_abnormal = False
    if rec.price_won <= 0:
        return False
    if rec.exclusive_area <= 0:
        return False
    price_per_area = rec.price_won / rec.exclusive_area
    # 전용㎡당 50만원 이하 또는 5억원 이상 → 이상거래
    if price_per_area < 500_000 or price_per_area > 500_000_000:
        is_abnormal = True

    transaction = Transaction(
        complex_id=complex_obj.id,
        transaction_key=rec.transaction_key,
        contract_year=rec.contract_year,
        contract_month=rec.contract_month,
        contract_day=rec.contract_day,
        contract_date=rec.contract_date,
        price=rec.price_won,
        price_per_area=round(rec.price_per_area, 2) if rec.price_per_area else None,
        exclusive_area=rec.exclusive_area,
        floor=rec.floor,
        seller_type=rec.seller_type,
        buyer_type=rec.buyer_type,
        sgg_code=rec.sgg_code,
        property_type=rec.property_type,
        is_abnormal=is_abnormal,
        verified=False,
    )

    session.add(transaction)
    return True


def bulk_ingest_transactions(session: Session,
                              records: list[TransactionRecord],
                              batch_size: int = 500) -> dict:
    """
    거래 레코드 일괄 적재

    Returns:
        {'inserted': N, 'skipped': N, 'abnormal': N, 'errors': N}
    """
    stats = {"inserted": 0, "skipped": 0, "abnormal": 0, "errors": 0}

    for i, rec in enumerate(records):
        try:
            inserted = ingest_transaction(session, rec)
            if inserted:
                stats["inserted"] += 1
            else:
                stats["skipped"] += 1

            # 배치 커밋
            if (i + 1) % batch_size == 0:
                session.commit()
                logger.debug(f"  거래 진행: {i+1}/{len(records)}")

        except Exception as e:
            logger.debug(f"거래 적재 오류: {e}")
            session.rollback()
            stats["errors"] += 1

    try:
        session.commit()
    except Exception as e:
        logger.error(f"최종 commit 오류: {e}")
        session.rollback()

    return stats
