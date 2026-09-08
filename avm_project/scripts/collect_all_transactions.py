#!/usr/bin/env python3
"""주거용·공장창고·상업업무용·토지 실거래를 한 번에 수집해 DB에 적재하고,
원하면 바로 Loan4U 스타일 엑셀(export_comparable_sales_excel.py)까지 내보낸다.

유형별 수집기(app/integrations/korea_api*.py)와 적재기(db_ingest.py)를
그대로 묶은 오케스트레이터다 — 한 유형의 API 실패가 나머지 유형 수집을
막지 않고, 결과는 유형별로 집계해 보여준다.

사용 예:
    python scripts/collect_all_transactions.py --sgg 11680 11650 --year 2025 --month 12
    python scripts/collect_all_transactions.py --sgg 11680 --year 2025 --month 12 \
        --types land commercial --export loan4u_upload.xlsx
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from app.integrations import db_ingest
from app.integrations.korea_api import KoreaLandAPI
from app.integrations.korea_api_commercial import KoreaCommercialTradeAPI
from app.integrations.korea_api_industrial import KoreaIndustrialTradeAPI
from app.integrations.korea_api_land import KoreaLandTradeAPI

log = logging.getLogger(__name__)

# 기존 스크립트들이 서로 다른 이름을 써 왔다 — 전부 받아준다.
API_KEY_ENV_VARS = (
    "DATAGOVKR_DECODING_KEY", "KOREA_API_KEY", "RTMS_SERVICE_KEY",
    "DATA_GO_KR_SERVICE_KEY", "PUBLIC_DATA_SERVICE_KEY",
)
STAT_KEYS = ("fetched", "inserted", "skipped", "errors", "failed_calls")


@dataclass(frozen=True)
class Collector:
    label: str
    fetch: Callable[[str, int, int], list]
    ingest: Callable[[object, list], Dict[str, int]]


def build_collectors(api_key: str, debug: bool = False) -> Dict[str, Collector]:
    residential = KoreaLandAPI(api_key=api_key)
    industrial = KoreaIndustrialTradeAPI(api_key=api_key)
    commercial = KoreaCommercialTradeAPI(api_key=api_key)
    land = KoreaLandTradeAPI(api_key=api_key)
    return {
        "residential": Collector("주거용(아파트·다세대·오피스텔)",
                                 residential.fetch_all_types, db_ingest.bulk_ingest_transactions),
        "industrial": Collector("공장/창고", lambda s, y, m: industrial.fetch(s, y, m, debug=debug),
                                db_ingest.bulk_ingest_industrial_transactions),
        "commercial": Collector("상업업무용", lambda s, y, m: commercial.fetch(s, y, m, debug=debug),
                                db_ingest.bulk_ingest_commercial_transactions),
        "land": Collector("토지", lambda s, y, m: land.fetch(s, y, m, debug=debug),
                          db_ingest.bulk_ingest_land_transactions),
    }


def collect(db, collectors: Dict[str, Collector], sgg_codes: Sequence[str],
            year: int, month: int, pause_sec: float = 0.5) -> Dict[str, Dict[str, int]]:
    """유형별 수집·적재 결과를 모은다. 한 유형의 실패가 다른 유형을 막지 않는다."""
    results = {name: dict.fromkeys(STAT_KEYS, 0) for name in collectors}
    for sgg in sgg_codes:
        for name, collector in collectors.items():
            summary = results[name]
            try:
                records = collector.fetch(sgg, year, month)
            except Exception as e:
                log.error(f"[FAIL] {sgg} {year}-{month:02d} [{collector.label}]: {e}")
                summary["failed_calls"] += 1
                continue
            summary["fetched"] += len(records)
            for key, value in collector.ingest(db, records).items():
                summary[key] += value
            time.sleep(pause_sec)
    return results


def _api_key() -> str:
    for name in API_KEY_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _print_summary(collectors: Dict[str, Collector], results: Dict[str, Dict[str, int]]) -> None:
    print(f"\n{'유형':<28}{'응답':>6}{'신규':>6}{'중복':>6}{'오류':>6}{'호출실패':>8}")
    for name, stats in results.items():
        print(f"{collectors[name].label:<28}{stats['fetched']:>6}{stats['inserted']:>6}"
              f"{stats['skipped']:>6}{stats['errors']:>6}{stats['failed_calls']:>8}")


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sgg", nargs="+", required=True, help="법정동코드 5자리 (여러 개 가능)")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--types", nargs="+", default=["residential", "industrial", "commercial", "land"],
                        choices=["residential", "industrial", "commercial", "land"])
    parser.add_argument("--export", help="수집 후 이 경로로 Loan4U 스타일 엑셀을 바로 내보낸다")
    parser.add_argument("--debug", action="store_true", help="원본 XML 응답을 로그로 남긴다")
    args = parser.parse_args(argv)

    api_key = _api_key()
    if not api_key:
        print(f"오류: API 키 환경변수가 필요합니다 ({', '.join(API_KEY_ENV_VARS)} 중 하나, .env 확인).")
        return 1

    from app.db.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        collectors = {name: c for name, c in build_collectors(api_key, args.debug).items()
                      if name in args.types}
        results = collect(db, collectors, args.sgg, args.year, args.month)
    finally:
        db.close()
    _print_summary(collectors, results)

    if args.export:
        from export_comparable_sales_excel import export_from_db
        print(f"\n엑셀 내보내기: {args.export} ({export_from_db(Path(args.export))}행)")

    all_failed = all(s["failed_calls"] and not s["fetched"] for s in results.values())
    return 1 if all_failed else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sys.exit(main())
