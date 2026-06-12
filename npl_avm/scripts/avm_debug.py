import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.db.database import SessionLocal
from app.db.models import Property, Appraisal
from sqlalchemy import func

db = SessionLocal()

# 서울 서대문구 근린상가 직접 쿼리
props = (db.query(Property)
    .filter(Property.address_sido == '서울특별시',
            Property.address_sigungu == '서대문구',
            Property.property_type.ilike('%근린%'))
    .all())
print(f'서울 서대문구 근린: {len(props)}건')
for p in props[:3]:
    appr = db.query(Appraisal).filter_by(property_id=p.id).first()
    print(f'  {p.property_serial} | {p.property_type} | appraisal_id={appr.id if appr else None} | total={appr.total_value if appr else None}')

# 전체 주소별 감정가 있는 물건 수 상위 10개
print()
print('감정가 있는 시군구 TOP 10:')
rows = (db.query(Property.address_sido, Property.address_sigungu, func.count(Appraisal.id).label('cnt'))
    .join(Appraisal, Appraisal.property_id == Property.id)
    .filter(Appraisal.total_value.isnot(None))
    .group_by(Property.address_sido, Property.address_sigungu)
    .order_by(func.count(Appraisal.id).desc())
    .limit(10).all())
for sido, sigungu, cnt in rows:
    print(f'  {sido} {sigungu}: {cnt}건')

# latest_appr 서브쿼리 동작 테스트
print()
latest = (db.query(Appraisal.property_id, func.max(Appraisal.appraisal_date).label("max_date"))
    .group_by(Appraisal.property_id)
    .subquery())
from sqlalchemy import and_
q = (db.query(Property, Appraisal)
    .join(latest, latest.c.property_id == Property.id)
    .join(Appraisal, and_(
        Appraisal.property_id == Property.id,
        Appraisal.appraisal_date == latest.c.max_date))
    .filter(Property.address_sido == '서울특별시',
            Property.address_sigungu == '서대문구',
            Property.property_type.ilike('%근린%'),
            Appraisal.total_value.isnot(None))
    .limit(5).all())
print(f'AVM 서브쿼리 결과: {len(q)}건')
for prop, appr in q:
    print(f'  {prop.property_serial} | {appr.total_value}')

db.close()
