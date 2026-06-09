"""
파싱된 DealRecord → DB 저장
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from app.parsers.base_parser import DealRecord, DebtorRecord, PropertyRecord
from app.db import models


def upsert_comparable_sale(db: Session, rec) -> models.ComparableSale:
    """거래사례 upsert (파일 + 순번 조합으로 중복 체크)"""
    existing = db.query(models.ComparableSale).filter_by(
        source_file=rec.source_file,
        case_index=rec.case_index,
    ).first()

    if not existing:
        obj = models.ComparableSale(
            source_file=rec.source_file,
            subject_property_serial=rec.subject_property_serial,
            case_index=rec.case_index,
        )
        db.add(obj)
    else:
        obj = existing

    obj.subject_property_serial = rec.subject_property_serial
    obj.address_full = rec.address_full
    obj.address_sido = rec.address_sido
    obj.address_sigungu = rec.address_sigungu
    obj.address_dong = rec.address_dong
    obj.property_type = rec.property_type
    obj.use_zone = rec.use_zone
    obj.land_area = rec.land_area
    obj.building_area = rec.building_area
    obj.structure = rec.structure
    obj.approval_date = rec.approval_date
    obj.trade_amount = rec.trade_amount
    obj.trade_date = rec.trade_date
    obj.unit_price_py = rec.unit_price_py
    obj.land_price_sqm = rec.land_price_sqm
    obj.note = rec.note

    db.flush()
    return obj


def upsert_deal(db: Session, record: DealRecord) -> models.Deal:
    deal = db.query(models.Deal).filter_by(
        deal_name=record.deal_name,
        pool_name=record.pool_name,
    ).first()

    if not deal:
        deal = models.Deal(
            deal_name=record.deal_name,
            pool_name=record.pool_name,
            financial_institution=record.financial_institution,
            asset_date=record.asset_date,
            source_file=record.source_file,
        )
        db.add(deal)
        db.flush()
    else:
        deal.source_file = record.source_file
        deal.asset_date = record.asset_date

    for debtor_rec in record.debtors:
        _upsert_debtor(db, deal, debtor_rec)

    db.commit()
    db.refresh(deal)
    return deal


def _upsert_debtor(db: Session, deal: models.Deal, rec: DebtorRecord):
    debtor = db.query(models.Debtor).filter_by(
        deal_id=deal.id,
        debtor_serial=rec.debtor_serial,
    ).first()

    if not debtor:
        debtor = models.Debtor(
            deal_id=deal.id,
            debtor_serial=rec.debtor_serial,
            debtor_name=rec.debtor_name,
            debtor_type=rec.debtor_type,
            pool_class=rec.pool_class,
        )
        db.add(debtor)
        db.flush()

    for prop_rec in rec.properties:
        _upsert_property(db, deal, debtor, prop_rec)


def _upsert_property(
    db: Session,
    deal: models.Deal,
    debtor: models.Debtor,
    rec: PropertyRecord,
):
    prop = db.query(models.Property).filter_by(
        deal_id=deal.id,
        property_serial=rec.property_serial,
    ).first()

    if not prop:
        prop = models.Property(deal_id=deal.id, debtor_id=debtor.id)
        db.add(prop)

    # 필드 일괄 업데이트
    for field in [
        "property_serial", "property_index",
        "address_sido", "address_sigungu", "address_dong", "address_detail", "address_full",
        "property_type", "property_category",
        "land_area", "building_area",
        "currency", "mortgage_amount", "mortgage_rank", "senior_mortgage_amount",
        "has_provisional_seizure", "provisional_seizure_amount",
        "has_lien", "lien_amount",
        "small_deposit_housing", "small_deposit_commercial",
        "lease_deposit_housing", "lease_deposit_commercial",
        "wage_claim", "current_tax", "tax_claim", "senior_burden_total",
        "kb_market_price", "kb_price_date",
    ]:
        setattr(prop, field, getattr(rec, field, None))

    db.flush()

    # 감정평가 기록
    if rec.total_value or rec.land_value or rec.building_value:
        existing = db.query(models.Appraisal).filter_by(
            property_id=prop.id,
            appraisal_date=rec.appraisal_date,
            appraiser=rec.appraiser,
        ).first()
        if not existing:
            appraisal = models.Appraisal(
                property_id=prop.id,
                appraisal_type=rec.appraisal_type,
                appraisal_date=rec.appraisal_date,
                appraiser=rec.appraiser,
                land_value=rec.land_value,
                building_value=rec.building_value,
                machine_value=rec.machine_value,
                outside_value=rec.outside_value,
                total_value=rec.total_value,
            )
            db.add(appraisal)

    # 경매 기록
    if rec.case_number or rec.is_filed is not None:
        existing = db.query(models.Auction).filter_by(
            property_id=prop.id,
            case_number=rec.case_number or "",
        ).first()
        if not existing:
            auction = models.Auction(
                property_id=prop.id,
                is_filed=rec.is_filed,
                court=rec.court,
                creditor=rec.creditor,
                case_number=rec.case_number or "",
                filing_date=rec.filing_date,
                demand_deadline=rec.demand_deadline,
                claim_amount=rec.claim_amount,
                first_legal_price=rec.first_legal_price,
                first_auction_date=rec.first_auction_date,
                lapse_count=rec.lapse_count,
                final_result=rec.final_result,
                final_auction_date=rec.final_auction_date,
                next_auction_date=rec.next_auction_date,
                hammer_price=rec.hammer_price,
                final_min_bid=rec.final_min_bid,
                next_min_bid=rec.next_min_bid,
            )
            db.add(auction)
