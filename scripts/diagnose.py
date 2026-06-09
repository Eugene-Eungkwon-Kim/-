import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.db.database import SessionLocal
from app.db.models import Property, Appraisal, Deal

db = SessionLocal()

# 부산 전체
busan = db.query(Property).filter(Property.address_sido == '부산광역시').count()
busan_appr = (db.query(Property)
    .join(Appraisal, Appraisal.property_id == Property.id)
    .filter(Property.address_sido == '부산광역시')
    .count())
print(f'부산광역시 전체 물건: {busan}건 (감정가 있음: {busan_appr}건)')

props = (db.query(Property)
    .filter(Property.address_sido == '부산광역시',
            Property.property_type.ilike('%근린%'))
    .limit(5).all())
print(f'부산 근린 유형: {len(props)}건')
for p in props:
    appr = db.query(Appraisal).filter_by(property_id=p.id).first()
    v = int(appr.total_value) if appr and appr.total_value else None
    print(f'  {p.property_serial} | {p.property_type} | 감정={v}')

print()
# KB 감정가 현황
kb_deals = db.query(Deal).filter_by(financial_institution='KB').all()
for d in kb_deals:
    cnt = db.query(Property).filter_by(deal_id=d.id).count()
    appr_cnt = (db.query(Property)
        .join(Appraisal, Appraisal.property_id == Property.id)
        .filter(Property.deal_id == d.id)
        .count())
    print(f'KB {d.deal_name}: 물건 {cnt} / 감정가 있음 {appr_cnt}')
    if cnt > 0:
        sample = db.query(Property).filter_by(deal_id=d.id).limit(2).all()
        for p in sample:
            appr = db.query(Appraisal).filter_by(property_id=p.id).first()
            v = int(appr.total_value) if appr and appr.total_value else None
            print(f'  샘플: {p.property_serial} | {p.property_type} | {p.address_sido} {p.address_sigungu} | 감정={v}')

db.close()
