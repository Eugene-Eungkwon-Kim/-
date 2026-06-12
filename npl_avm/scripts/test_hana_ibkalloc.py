import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.parsers.hana_parser import HANAParser
from app.parsers.ibk_alloc_parser import IBKAllocParser

# HANA 테스트
hana_file = r"D:\NPL 폴더\HANA 2026-2 Program\HANA 거래사례\hana-A-R-001_2 주식회사 창평실업.xlsx"
p = HANAParser()
deal = p.parse(hana_file)
total_props = sum(len(d.properties) for d in deal.debtors)
print(f"HANA: {deal.deal_name} | Debtors: {len(deal.debtors)} | Properties: {total_props}")
for d in deal.debtors[:2]:
    for prop in d.properties[:2]:
        print(f"  {prop.property_serial} | {prop.address_sido} {prop.address_sigungu} | {prop.property_type} | total={prop.total_value}")
hammered = sum(1 for d in deal.debtors for pr in d.properties if pr.hammer_price)
filed = sum(1 for d in deal.debtors for pr in d.properties if pr.is_filed)
print(f"  낙찰: {hammered}, 경매개시: {filed}")

print()

# IBK Alloc 테스트
ibk_file = r"D:\NPL 폴더\IBK 2026-2 Program\2026-2P 우리금융(IBK)\★ IBK 2026-2P A Pre Allocation.xlsx"
p2 = IBKAllocParser()
deal2 = p2.parse(ibk_file)
total2 = sum(len(d.properties) for d in deal2.debtors)
print(f"IBK Alloc: {deal2.deal_name} | Debtors: {len(deal2.debtors)} | Properties: {total2}")
for d in deal2.debtors[:2]:
    for prop in d.properties[:2]:
        print(f"  {prop.property_serial} | {prop.address_sido} {prop.address_sigungu} | {prop.property_type} | total={prop.total_value}")
hammered2 = sum(1 for d in deal2.debtors for pr in d.properties if pr.hammer_price)
filed2 = sum(1 for d in deal2.debtors for pr in d.properties if pr.is_filed)
print(f"  낙찰: {hammered2}, 경매개시: {filed2}")

# col_map 확인
cm = p2._build_col_map(__import__('openpyxl').load_workbook(ibk_file, data_only=True, read_only=True)["4. 담보(물건)"])
print(f"\nIBK Alloc col_map 주요 필드:")
for k in ['address_sido','total_value','land_value','appraisal_date','final_result','hammer_price']:
    print(f"  {k} = {cm.get(k)}")
