#!/usr/bin/env python3
"""수집한 실거래(ComparableSale)를 Loan4U 스타일 엑셀로 내보낸다.

실제 "Loan4U 업로드 엑셀" 템플릿 파일은 이 저장소 어디에도 없어(전
브랜치 확인) 그 정확한 시트/컬럼 구조를 그대로 재현할 수는 없다. 대신
같은 프로젝트의 loan4u_phase12_pipeline.py 에 이미 있는 **실제** 가격
부합성 판정 로직(classify_price_conformity_phase12)과 등급 배색
(GRADE_COLORS)을 그대로 재사용해, 지역·자산유형별로 묶은 그룹 내에서
"이 거래가 같은 그룹 평균 대비 적정한가"를 판정한 엑셀을 만든다 —
새로 만든 판정 기준이 아니라 이미 검증된 로직을 다른 데이터에
적용한 것이다.

사용 예:
    python scripts/export_comparable_sales_excel.py --out comparable_sales.xlsx
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from openpyxl import Workbook

from loan4u_phase12_pipeline import (
    GRADE_COLORS, HEADER_FILL, HEADER_FONT,
    autofit_columns, classify_final_action,
    classify_price_conformity_phase12, style_range,
)
from openpyxl.styles import PatternFill

COLUMNS = ["시도", "시군구", "주소", "거래일", "거래금액", "건물면적", "대지면적",
          "㎡당 단가", "가격부합성", "편차율", "최종조치"]


def _per_area_price(trade_amount, area) -> Optional[float]:
    if not trade_amount or not area:
        return None
    # trade_amount 는 SQLAlchemy Numeric 컬럼이라 Decimal 로 온다 —
    # float(area) 와 그대로 나누면 TypeError 가 난다.
    return float(trade_amount) / float(area)


def _basis_area(row: dict) -> Optional[float]:
    # 건물이 있으면 건물면적, 토지처럼 건물이 없으면 대지면적을 단가 기준으로 쓴다.
    return row.get("building_area") or row.get("land_area")


def export(rows: list[dict], out_path: Path) -> int:
    """rows: ComparableSale 를 dict 로 뽑은 목록. property_type 별로 시트를 나눈다."""
    wb = Workbook()
    wb.remove(wb.active)

    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_type[row.get("property_type") or "기타"].append(row)

    total_rows = 0
    for property_type, group_rows in by_type.items():
        ws = wb.create_sheet(property_type[:31])  # 엑셀 시트명 31자 제한

        for col, name in enumerate(COLUMNS, start=1):
            cell = ws.cell(1, col, name)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT

        # 같은 시트 안, 같은 (시도,시군구) 묶음 내에서 평당가 평균을 기준으로 삼는다.
        by_region: dict[tuple, list[dict]] = defaultdict(list)
        for row in group_rows:
            by_region[(row.get("address_sido"), row.get("address_sigungu"))].append(row)

        excel_row = 2
        for region_rows in by_region.values():
            priced = [
                {**r, "_per_area": _per_area_price(r.get("trade_amount"), _basis_area(r))}
                for r in region_rows
            ]
            source_records = [{"price": r["_per_area"]} for r in priced if r["_per_area"]]

            for r in priced:
                per_area = r["_per_area"]
                others = [sr for sr in source_records if sr["price"] != per_area] or source_records
                if per_area:
                    grade, deviation, _ = classify_price_conformity_phase12(
                        old_price=None, new_price=per_area, country="KR",
                        source_records=others,
                    )
                else:
                    grade, deviation = "추가확인", None

                ws.cell(excel_row, 1, r.get("address_sido"))
                ws.cell(excel_row, 2, r.get("address_sigungu"))
                ws.cell(excel_row, 3, r.get("address_full"))
                ws.cell(excel_row, 4, str(r.get("trade_date") or ""))
                ws.cell(excel_row, 5, r.get("trade_amount"))
                ws.cell(excel_row, 6, r.get("building_area"))
                ws.cell(excel_row, 7, r.get("land_area"))
                ws.cell(excel_row, 8, round(per_area) if per_area else None)
                grade_cell = ws.cell(excel_row, 9, grade)
                ws.cell(excel_row, 10, f"{deviation:.2%}" if deviation is not None else "")
                ws.cell(excel_row, 11, classify_final_action(grade))

                grade_cell.fill = PatternFill(fill_type="solid",
                                              fgColor=GRADE_COLORS.get(grade, "FFFFFF"))
                excel_row += 1
                total_rows += 1

        style_range(ws, 2, ws.max_row, 1, len(COLUMNS))
        autofit_columns(ws)

    wb.save(out_path)
    return total_rows


def load_rows(db) -> list[dict]:
    """DB의 비교사례(case_index > 0)를 export() 가 받는 dict 목록으로 뽑는다."""
    from app.db.models import ComparableSale

    sales = db.query(ComparableSale).filter(ComparableSale.case_index > 0).all()
    return [{
        "address_sido": s.address_sido, "address_sigungu": s.address_sigungu,
        "address_full": s.address_full, "property_type": s.property_type,
        "trade_date": s.trade_date, "trade_amount": s.trade_amount,
        "building_area": s.building_area, "land_area": s.land_area,
    } for s in sales]


def export_from_db(out_path: Path) -> int:
    """현재 DB 전체를 엑셀로 내보내고 행 수를 돌려준다 (0이면 파일을 만들지 않는다)."""
    from app.db.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        rows = load_rows(db)
    finally:
        db.close()
    return export(rows, out_path) if rows else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="comparable_sales_export.xlsx")
    args = parser.parse_args()

    from app.db.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        rows = load_rows(db)
    finally:
        db.close()

    if not rows:
        print("내보낼 데이터가 없습니다 — 먼저 수집 스크립트로 데이터를 적재하세요.")
        return 1

    count = export(rows, Path(args.out))
    print(f"내보내기 완료: {count}행 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
