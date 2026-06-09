"""
Usage:
  python scripts/ingest_all.py [--root "D:\\NPL전례\\★ 과거 NPL 데이터"]

NPL 데이터 폴더 전체를 스캔해서 DB에 적재
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, SessionLocal
from app.db.ingest import upsert_deal
from app.parsers.loader import find_data_disk_files, parse_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=r"D:\NPL전례\★ 과거 NPL 데이터",
        help="NPL 데이터 루트 폴더",
    )
    parser.add_argument(
        "--institution",
        default=None,
        help="특정 금융기관만 처리 (IBK, KB, HANA, IBK_ALLOC, ...)",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="특정 파일 직접 지정 (--institution 과 함께 사용)",
    )
    args = parser.parse_args()

    init_db()

    if args.file:
        # 단일 파일 직접 처리
        if not args.institution:
            print("--file 사용 시 --institution 필수")
            return
        files = [{"file": args.file, "institution": args.institution,
                  "folder": Path(args.file).parent.name}]
    else:
        files = find_data_disk_files(args.root)
        if args.institution:
            files = [f for f in files if f["institution"] == args.institution]

    print(f"발견된 Data Disk 파일: {len(files)}개\n")

    ok, skip, err = 0, 0, 0
    db = SessionLocal()
    try:
        for info in files:
            print(f"[{info['institution']}] {info['folder']}")
            print(f"  파일: {Path(info['file']).name}")

            record = parse_file(info["file"], info["institution"])
            if record is None:
                skip += 1
                continue

            try:
                deal = upsert_deal(db, record)
                props = sum(len(d.properties) for d in record.debtors)
                print(f"  → 딜: {deal.deal_name} | 물건: {props}개 저장")
                ok += 1
            except Exception as e:
                db.rollback()
                print(f"  [ERROR] DB 저장 실패: {e}")
                err += 1
    finally:
        db.close()

    print(f"\n완료: 성공 {ok} / 스킵 {skip} / 오류 {err}")


if __name__ == "__main__":
    main()
