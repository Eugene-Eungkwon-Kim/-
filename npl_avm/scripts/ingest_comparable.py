"""
거래사례 정밀 시트 일괄 적재
Usage:
  python scripts/ingest_comparable.py --dirs "D:\\NPL 폴더\\IBK 2026-2 Program\\IBK 거래사례" "D:\\NPL 폴더\\HANA 2026-2 Program\\HANA 거래사례"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, SessionLocal
from app.db.ingest import upsert_comparable_sale
from app.parsers.comparable_parser import parse_comparable_sheet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirs", nargs="+", required=True, help="거래사례 폴더 경로들")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    total_ok = 0
    total_err = 0

    try:
        for folder in args.dirs:
            p = Path(folder)
            if not p.exists():
                print(f"[SKIP] 폴더 없음: {folder}")
                continue

            xlsx_files = sorted(p.glob("*.xlsx"))
            xlsx_files = [f for f in xlsx_files if not f.name.startswith("~$")]
            print(f"\n[{p.name}] {len(xlsx_files)}개 파일")

            for f in xlsx_files:
                records = parse_comparable_sheet(str(f))
                if not records:
                    print(f"  [SKIP] 정밀 시트 없음: {f.name}")
                    continue

                ok = 0
                for rec in records:
                    try:
                        upsert_comparable_sale(db, rec)
                        ok += 1
                    except Exception as e:
                        db.rollback()
                        print(f"  [ERROR] {f.name} case{rec.case_index}: {e}")
                        total_err += 1

                db.commit()
                total_ok += ok
                # 사례 수만 표시 (본건 제외)
                cases = [r for r in records if r.case_index > 0]
                print(f"  {f.name}: 본건 1개 + 거래사례 {len(cases)}개 저장")

    finally:
        db.close()

    print(f"\n완료: 총 {total_ok}건 저장 / 오류 {total_err}건")


if __name__ == "__main__":
    main()
