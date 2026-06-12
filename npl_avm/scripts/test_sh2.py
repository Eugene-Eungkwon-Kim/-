import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.parsers.sh_parser import SHParser
from pathlib import Path

files = list(Path(r"D:\NPL전례\★ 과거 NPL 데이터").rglob("*SH*Datadisk*Clean*.xlsx"))
if not files:
    files = list(Path(r"D:\NPL전례\★ 과거 NPL 데이터").rglob("*SH*Datadisk*.xlsx"))

for f in files[:1]:
    print(f"파일: {f.name}")
    p = SHParser()
    deal = p.parse(str(f))
    print(f"Deal: {deal.deal_name}")
    total_props = sum(len(d.properties) for d in deal.debtors)
    print(f"Debtors: {len(deal.debtors)}, Properties: {total_props}")
    for d in deal.debtors[:3]:
        for prop in d.properties[:2]:
            print(f"  {prop.property_serial} | {prop.address_sido} {prop.address_sigungu} | {prop.property_type} | total={prop.total_value} | appraiser={prop.appraiser}")
    hammered = sum(1 for d in deal.debtors for pr in d.properties if pr.hammer_price)
    filed = sum(1 for d in deal.debtors for pr in d.properties if pr.is_filed)
    print(f"낙찰 건수: {hammered}, 경매개시: {filed}")
