#!/usr/bin/env python3
"""외장하드에서 실데이터를 찾아 한 번에 가져온다.

이 프로젝트의 실데이터는 외장하드에 있다는 게 이미 README.md 에
명시된 공식 설정 절차다("외장하드 (LG External Drive)", "D:\\NPL폴더").
문제는 세션마다 드라이브 문자가 D:/E:/F: 로 바뀐다는 것
(scripts/phase_c_step0_read_external_drive.py 가 이미 이 문제를 다룬다).

지금까지는 사용자가 직접 sqlite3 CLI로 쿼리를 짜고 CSV를 뽑아
import_onbid_csv.py 에 넘겨야 했다. 이 스크립트는 그 수작업을
없앤다: 드라이브 문자를 순회하며 알려진 상대경로에서 npl_avm.db 와
학습된 P6 모델 파일을 직접 찾아 자동으로 가져온다.

사용 예:
    python scripts/sync_from_external_drive.py            # 자동 탐색
    python scripts/sync_from_external_drive.py --root F:/  # 특정 드라이브 지정
"""

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# phase7_grounded_avm.py 에서 확인된 실제 경로 — 드라이브 문자만 바뀐다.
NPL_DB_SUFFIX = Path("NPL전례") / "avm_project" / "data" / "npl_avm.db"
MODEL_CANDIDATES = [
    Path("NPL전례") / "avm_project" / "models" / "p6_advanced_hammer_ensemble.pkl",
    Path("loan4u_avm_data") / "models" / "p6_advanced_hammer_ensemble.pkl",
]
CALIBRATION_CANDIDATES = [
    Path("NPL전례") / "avm_project" / "models" / "p6_calibration.pkl",
    Path("loan4u_avm_data") / "models" / "p6_calibration.pkl",
]

ONBID_QUERY = """
    SELECT id, address_sido, address_sigungu, address_raw, building_area_sqm,
           appraisal_amount, hammer_price, hammer_rate, asset_type_norm
    FROM onbid_auction_results
"""


def _candidate_roots(explicit_root: str | None) -> list[Path]:
    if explicit_root:
        return [Path(explicit_root)]
    if sys.platform == "win32":
        return [Path(f"{letter}:/") for letter in "DEFGHIJKLMNOPQRSTUVWXYZ"]
    # macOS/Linux: 일반적인 마운트 위치를 훑는다.
    roots = []
    for base in (Path("/Volumes"), Path("/mnt"), Path("/media")):
        if base.exists():
            roots.extend(p for p in base.iterdir() if p.is_dir())
    return roots


def find_file(roots: list[Path], suffixes: list[Path]) -> Path | None:
    for root in roots:
        for suffix in suffixes:
            candidate = root / suffix
            if candidate.exists():
                return candidate
    return None


def sync_onbid(db_path: Path) -> int:
    from app.db.database import SessionLocal, init_db
    from scripts.import_onbid_csv import import_rows

    print(f"OnBid 데이터 발견: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute(ONBID_QUERY)]
    except sqlite3.OperationalError as e:
        print(f"  쿼리 실패 (테이블이 없거나 스키마가 다름): {e}")
        return 0
    finally:
        conn.close()

    # sqlite3 는 숫자 컬럼을 그대로 주므로 import_rows 가 기대하는
    # 문자열 형태로 맞춘다(import_onbid_csv.py 는 CSV 문자열 입력을 전제).
    str_rows = [{k: ("" if v is None else str(v)) for k, v in row.items()} for row in rows]

    init_db()
    db = SessionLocal()
    try:
        stats = import_rows(db, str_rows)
    finally:
        db.close()

    print(f"  적재: {stats}")
    return stats["inserted"]


def sync_model(model_path: Path | None, calibration_path: Path | None) -> bool:
    dest_dir = Path(__file__).parent.parent / "models"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = False

    if model_path:
        dest = dest_dir / "p6_advanced_hammer_ensemble.pkl"
        shutil.copy2(model_path, dest)
        print(f"P6 모델 복사: {model_path} → {dest}")
        copied = True

    if calibration_path:
        dest = dest_dir / "p6_calibration.pkl"
        shutil.copy2(calibration_path, dest)
        print(f"P6 캘리브레이션 복사: {calibration_path} → {dest}")
        copied = True

    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="드라이브를 직접 지정 (예: F:/ 또는 /Volumes/외장하드)")
    args = parser.parse_args()

    roots = _candidate_roots(args.root)
    print(f"탐색 대상: {len(roots)}개 경로")

    db_path = find_file(roots, [NPL_DB_SUFFIX])
    model_path = find_file(roots, MODEL_CANDIDATES)
    calib_path = find_file(roots, CALIBRATION_CANDIDATES)

    found_anything = False

    if db_path:
        found_anything = True
        sync_onbid(db_path)
    else:
        print("npl_avm.db 를 찾지 못했습니다 — --root 로 드라이브를 직접 지정해보세요.")

    if model_path or calib_path:
        found_anything = True
        sync_model(model_path, calib_path)
    else:
        print("P6 모델 파일을 찾지 못했습니다.")

    if not found_anything:
        print("\n외장하드가 연결되어 있는지, --root 경로가 맞는지 확인하세요.")
        return 1

    print("\n완료. python scripts/export_comparable_sales_excel.py 로 결과를 확인할 수 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
