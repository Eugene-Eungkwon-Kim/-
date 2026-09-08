#!/usr/bin/env python3
"""상업업무용 부동산 매매 실거래가 수집.

Endpoint: RTMSDataSvcNrgTrade (웹 검색으로 확인 — 서비스 코드 확정 근거는
app/integrations/korea_api_commercial.py 모듈 docstring 참고). 필드
태그명은 미검증이므로 네트워크가 열린 환경에서 처음 실행할 때는 --debug
를 켜서 원본 XML을 먼저 확인할 것을 권장한다.

사용 예:
    python scripts/fetch_commercial_transactions.py --sgg 11680 --year 2025 --month 12
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.db.database import SessionLocal, init_db
from app.integrations.db_ingest import bulk_ingest_commercial_transactions
from app.integrations.korea_api_commercial import KoreaCommercialTradeAPI


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sgg", required=True, help="법정동코드 5자리 (예: 강남구=11680)")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--debug", action="store_true", help="원본 XML 응답을 로그로 남긴다")
    args = parser.parse_args()

    api_key = os.environ.get("DATAGOVKR_DECODING_KEY", "")
    if not api_key:
        print("오류: DATAGOVKR_DECODING_KEY 환경변수가 필요합니다 (.env 확인).")
        return 1

    init_db()
    api = KoreaCommercialTradeAPI(api_key=api_key)

    print(f"조회: {args.sgg} {args.year}-{args.month:02d} [상업업무용]")
    try:
        records = api.fetch(args.sgg, args.year, args.month, debug=args.debug)
    except Exception as e:
        print(f"API 오류: {e}")
        return 1

    print(f"응답: {len(records)}건")

    db = SessionLocal()
    try:
        stats = bulk_ingest_commercial_transactions(db, records)
    finally:
        db.close()

    print(f"적재: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
