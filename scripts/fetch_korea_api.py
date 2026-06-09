#!/usr/bin/env python3
"""국토부 실거래가 API 월별 수집 스크립트

Usage:
    python scripts/fetch_korea_api.py --year 2026 --month 5
"""

import argparse
import logging
import time

from app.config import settings
from app.db.database import init_db as create_tables
from app.db.ingest import ingest_transactions
from app.integrations.korea_api import KoreaLandAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 주요 시군구 코드 (샘플)
SGG_CODES = [
    "11110",  # 서울 종로구
    "11140",  # 서울 중구
    "11170",  # 서울 용산구
    "41590",  # 경기 화성시
    "41210",  # 경기 성남시 분당구
]


def fetch_all(year: int, month: int):
    create_tables()

    if not settings.KOREA_API_KEY:
        logger.error("KOREA_API_KEY 미설정")
        return

    api = KoreaLandAPI(settings.KOREA_API_KEY)
    total = 0

    for sgg in SGG_CODES:
        for fetch_fn, ptype in [
            (api.fetch_apt_transactions, "아파트"),
            (api.fetch_multi_transactions, "다세대"),
            (api.fetch_office_transactions, "오피스텔"),
        ]:
            records = fetch_fn(sgg, year, month)
            if not records:
                continue

            import pandas as pd
            rows = [
                {
                    "거래금액": r.price_manwon,
                    "전용면적": r.exclusive_area,
                    "contract_date": r.contract_date,
                    "transaction_id": r.transaction_key,
                }
                for r in records
            ]
            df = pd.DataFrame(rows)
            saved = ingest_transactions(df, ptype)
            total += saved
            logger.info("%s %s %d-%02d: %d건 적재", ptype, sgg, year, month, saved)
            time.sleep(0.5)

    logger.info("전체 적재 완료: %d건", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    args = parser.parse_args()
    fetch_all(args.year, args.month)
