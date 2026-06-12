import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.db.database import SessionLocal
from app.db.models import Deal, Property, Appraisal, Auction
from sqlalchemy import func

db = SessionLocal()

print("=== DB 현황 ===")
deals = db.query(Deal).all()
for d in deals:
    props = db.query(Property).filter_by(deal_id=d.id).count()
    apprs = (db.query(Appraisal)
             .join(Property, Property.id == Appraisal.property_id)
             .filter(Property.deal_id == d.id)
             .filter(Appraisal.total_value > 0).count())
    aucts = (db.query(Auction)
             .join(Property, Property.id == Auction.property_id)
             .filter(Property.deal_id == d.id)
             .filter(Auction.hammer_price.isnot(None)).count())
    print(f"  {d.deal_name}: 물건 {props}개, 유효감정가 {apprs}건, 낙찰 {aucts}건")

total_props = db.query(Property).count()
total_apprs = db.query(Appraisal).filter(Appraisal.total_value > 0).count()
total_aucts = db.query(Auction).filter(Auction.hammer_price.isnot(None)).count()
print(f"\n총계: 물건 {total_props}개, 유효감정가 {total_apprs}건, 낙찰금액있는경매 {total_aucts}건")

db.close()
