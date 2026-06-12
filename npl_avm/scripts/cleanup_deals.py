"""DGB, SH 딜 데이터를 DB에서 삭제 후 재적재 준비"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.db.database import SessionLocal
from app.db.models import Deal, Debtor, Property, Appraisal, Auction

db = SessionLocal()

for inst in ("DGB", "SH"):
    deals = db.query(Deal).filter_by(financial_institution=inst).all()
    for deal in deals:
        props = db.query(Property).filter_by(deal_id=deal.id).all()
        for prop in props:
            db.query(Appraisal).filter_by(property_id=prop.id).delete()
            db.query(Auction).filter_by(property_id=prop.id).delete()
        db.query(Property).filter_by(deal_id=deal.id).delete()
        db.query(Debtor).filter_by(deal_id=deal.id).delete()
        db.delete(deal)
        print(f"삭제: {deal.deal_name}")

db.commit()
db.close()
print("완료")
