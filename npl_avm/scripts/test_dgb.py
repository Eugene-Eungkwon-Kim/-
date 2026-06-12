import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from app.parsers.dgb_parser import DGBParser

p = DGBParser()
dgb_file = r"D:\NPL전례\★ 과거 NPL 데이터\'23.05 우리FNI(농협)\_Excel\DGB 2023-2 Program_Datadisk_1st Distiribution.xlsx"
deal = p.parse(dgb_file)
print(f"Deal: {deal.deal_name}")
total_props = sum(len(d.properties) for d in deal.debtors)
print(f"Debtors: {len(deal.debtors)}, Properties: {total_props}")
for d in deal.debtors[:3]:
    for prop in d.properties[:2]:
        print(f"  {prop.property_serial} | {prop.address_sido} {prop.address_sigungu} | type={prop.property_type} | total={prop.total_value} | result={prop.final_result} | hammer={prop.hammer_price}")
hammered = sum(1 for d in deal.debtors for pr in d.properties if pr.hammer_price)
print(f"낙찰 건수: {hammered}")

# col_map 확인
col_map = p._build_col_map(__import__('openpyxl').load_workbook(dgb_file, data_only=True, read_only=True)["Sheet C-1"])
for k in ['address_sido','appraisal_date','total_value','final_result','hammer_price']:
    print(f"  col_map[{k}] = {col_map.get(k)}")
