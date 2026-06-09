"""
rtech 단지 마스터 크롤러 실행 스크립트

사용 예시:
    # 전국 단지 수집
    python scripts/crawl_complexes.py

    # 특정 시도만
    python scripts/crawl_complexes.py --sido 경기도

    # 테스트 (10페이지만)
    python scripts/crawl_complexes.py --sido 서울특별시 --max-pages 10

주의:
    - rtech 이용약관 확인 후 사용
    - 실제 크롤링 전 HTML 구조 분석 필요
    - 대안: K-apt (공동주택관리정보시스템) 활용
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, init_db
from app.integrations.rtech_crawler import RtechCrawler
from app.integrations.db_ingest import bulk_upsert_complexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/crawl_complexes.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run(args):
    """메인 실행"""

    init_db()
    crawler = RtechCrawler(sleep_sec=1.0)

    logger.info("▶ rtech 단지 마스터 수집 시작")
    if args.sido:
        logger.info(f"  대상 시도: {args.sido}")

    # 수집
    masters = crawler.fetch_complex_masters(
        sido=args.sido,
        max_pages=args.max_pages,
    )

    if not masters:
        logger.warning("수집된 단지가 없습니다. HTML 구조를 확인하세요.")
        logger.warning("대안: scripts/fetch_transactions.py 를 먼저 실행하면")
        logger.warning("       거래 데이터에서 단지 정보를 자동 생성합니다.")
        return

    logger.info(f"▶ 수집 완료: {len(masters):,}개 단지")

    # DB 적재
    session = SessionLocal()
    try:
        stats = bulk_upsert_complexes(session, masters)
        logger.info(f"✓ DB 적재 완료:")
        logger.info(f"  신규 삽입: {stats['inserted']:,}")
        logger.info(f"  업데이트:  {stats['updated']:,}")
        logger.info(f"  오류:      {stats['errors']:,}")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="rtech 단지 마스터 크롤러")
    parser.add_argument("--sido", type=str, default=None,
                        help="시도 (미입력 시 전국)")
    parser.add_argument("--max-pages", type=int, default=9999,
                        help="최대 페이지 수 (테스트용, 기본=전체)")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
