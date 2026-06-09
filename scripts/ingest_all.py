#!/usr/bin/env python3
"""모든 데이터 소스 일괄 수집 및 적재 스크립트"""

import asyncio
import logging
import sys

import aiohttp

from app.db.database import create_tables
from app.db.ingest import ingest_complexes
from app.integrations.rtech_crawler import RtechCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run():
    create_tables()

    async with aiohttp.ClientSession() as session:
        crawler = RtechCrawler(session)
        logger.info("rtech 단지 마스터 수집 시작")
        complexes_raw = await crawler.fetch_complex_masters()
        logger.info("수집 완료: %d개", len(complexes_raw))

        data = [
            {
                "code": c.code,
                "name": c.name,
                "address": c.address,
                "build_year": c.build_year,
                "units": c.total_units,
                "source": c.source,
            }
            for c in complexes_raw
        ]

        saved = ingest_complexes(data)
        logger.info("DB 적재 완료: %d건", saved)


if __name__ == "__main__":
    asyncio.run(run())
