#!/usr/bin/env python3
"""OnBid(온비드) 경매 결과를 app/db 로 가져온다.

이 저장소에는 실제 경매 데이터가 없다 — scripts/phase7_grounded_avm.py 등을
조사해 보니, 실 데이터는 외장하드의 로컬 SQLite(F:/NPL전례/avm_project/data/
npl_avm.db, 테이블 onbid_auction_results, 124건+ 실제 낙찰가 보유)에 있고
이 세션은 그 하드웨어에 물리적으로 접근할 수 없다.

이 스크립트는 그 데이터가 "도착했을 때" 즉시 꽂을 수 있는 반대쪽 소켓이다.
외장하드가 연결된 PC에서 아래 쿼리로 CSV를 뽑아 이 스크립트에 넘기면 된다:

    sqlite3 -header -csv F:/NPL전례/avm_project/data/npl_avm.db \\
        "SELECT id, address_sido, address_sigungu, address_raw, \\
                building_area_sqm, appraisal_amount, hammer_price, \\
                hammer_rate, asset_type_norm FROM onbid_auction_results" \\
        > onbid_export.csv

    python scripts/import_onbid_csv.py onbid_export.csv

가져온 행은 Property/Appraisal/Auction 에 들어가므로, 기존 AVM 비교사례
검색(app/avm/engine.estimate)과 RAG 벡터 색인(app/avm/vector_index)이
별도 연결 작업 없이 곧바로 이 데이터를 인식한다.
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# onbid asset_type_norm -> 이 프로젝트의 property_type 분류.
# phase7_d_hammer_rate_model.py 의 매핑을 그대로 따른다(주거용건물->주거).
ASSET_TYPE_MAP = {
    "주거용건물": "주거",
    "상업용건물": "상가",
    "공장": "공장창고",
    "토지": "토지",
}

ONBID_DEAL_NAME = "OnBid 공매/경매 (외부 가져오기)"


def _to_float(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def import_rows(db, rows: list[dict]) -> dict:
    from app.db.models import Appraisal, Auction, Deal, Property

    deal = db.query(Deal).filter(Deal.deal_name == ONBID_DEAL_NAME).first()
    if deal is None:
        deal = Deal(deal_name=ONBID_DEAL_NAME, financial_institution="OnBid")
        db.add(deal)
        db.flush()

    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    for row in rows:
        try:
            onbid_id = row.get("id", "").strip()
            if not onbid_id:
                stats["errors"] += 1
                continue

            serial = f"onbid-{onbid_id}"
            exists = db.query(Property.id).filter(
                Property.property_serial == serial
            ).first()
            if exists:
                stats["skipped"] += 1
                continue

            appraisal_amount = _to_float(row.get("appraisal_amount"))
            hammer_price = _to_float(row.get("hammer_price"))
            if not appraisal_amount or appraisal_amount <= 0:
                stats["skipped"] += 1
                continue

            raw_type = (row.get("asset_type_norm") or "").strip()
            property_type = ASSET_TYPE_MAP.get(raw_type, raw_type or "기타")

            prop = Property(
                property_serial=serial, deal_id=deal.id,
                address_full=row.get("address_raw", ""),
                address_sido=row.get("address_sido", ""),
                address_sigungu=row.get("address_sigungu", ""),
                property_type=property_type,
                building_area=_to_float(row.get("building_area_sqm")),
            )
            db.add(prop)
            db.flush()

            # onbid_auction_results 에는 감정일자 컬럼이 없다. NULL로 두면
            # _find_comparables 의 "최신 감정가" 조인(appraisal_date ==
            # MAX(appraisal_date))이 SQL의 NULL 비교 규칙 때문에 항상
            # 실패해 비교사례 검색에서 조용히 빠진다 — 가져온 시점을
            # 감정일자로 대신 채워 그 조인이 성립하게 한다.
            db.add(Appraisal(property_id=prop.id, total_value=appraisal_amount,
                             appraisal_date=date.today()))
            if hammer_price:
                db.add(Auction(property_id=prop.id, hammer_price=hammer_price,
                               final_result="낙찰"))

            stats["inserted"] += 1
        except Exception as e:
            print(f"  [오류] id={row.get('id')}: {e}")
            stats["errors"] += 1

    db.commit()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", help="onbid_auction_results 를 내보낸 CSV 파일")
    args = parser.parse_args()

    from app.db.database import SessionLocal, init_db
    init_db()

    with open(args.csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    required = {"id", "address_sido", "address_sigungu", "address_raw",
               "appraisal_amount", "asset_type_norm"}
    missing = required - set(rows[0].keys()) if rows else required
    if missing:
        print(f"오류: CSV에 필요한 컬럼이 없습니다: {sorted(missing)}")
        return 1

    print(f"CSV 읽음: {len(rows)}행")

    db = SessionLocal()
    try:
        stats = import_rows(db, rows)
    finally:
        db.close()

    print(f"결과: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
