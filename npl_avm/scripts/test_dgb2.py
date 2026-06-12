import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import openpyxl

dgb_file = r"D:\NPL전례\★ 과거 NPL 데이터\'23.05 우리FNI(농협)\_Excel\DGB 2023-2 Program_Datadisk_1st Distiribution.xlsx"
wb = openpyxl.load_workbook(dgb_file, data_only=True, read_only=True)
ws = wb["Sheet C-1"]

# 낙찰 관련 컬럼 값 전체 확인 (col 71=최종경매결과, 72=최저입찰금액, 73=낙찰금액)
print("Row | 최종경매결과(col71) | 최저입찰금액(col72) | 낙찰금액(col73)")
for row_idx, row in enumerate(ws.iter_rows(min_row=12, max_row=90, values_only=True), start=12):
    if not any(row):
        continue
    c70 = row[70] if len(row) > 70 else None  # 0-based: col71
    c71 = row[71] if len(row) > 71 else None  # col72
    c72 = row[72] if len(row) > 72 else None  # col73
    if c70 or c72:
        print(f"  Row{row_idx}: result={repr(c70)} | min_bid={repr(c71)} | hammer={repr(c72)}")

wb.close()
