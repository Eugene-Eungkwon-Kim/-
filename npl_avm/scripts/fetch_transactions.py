"""
국토부 실거래가 공공API → DB 적재 스크립트

사용 예시:
    # 특정 월 전국 수집
    python scripts/fetch_transactions.py --year 2026 --month 5

    # 특정 지역만
    python scripts/fetch_transactions.py --year 2026 --month 5 --sido 경기도

    # 특정 시군구
    python scripts/fetch_transactions.py --year 2026 --month 5 --sgg 41590

    # 아파트만
    python scripts/fetch_transactions.py --year 2026 --month 5 --type 아파트

    # 최근 12개월 전국 (주의: 대용량)
    python scripts/fetch_transactions.py --months 12

설정:
    환경변수 KOREA_API_KEY 또는 .env 파일에 API 키 설정 필요
    API 키 신청: https://www.data.go.kr/
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, timedelta

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.db.database import SessionLocal, init_db
from app.integrations.korea_api import KoreaLandAPI
from app.integrations.db_ingest import bulk_ingest_transactions
from app.integrations.sgg_codes import SGG_CODES, get_all_sgg_codes

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/fetch_transactions.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

PROPERTY_TYPES = ["아파트", "다세대", "오피스텔"]


def get_sido_sgg_codes(sido: str) -> list[str]:
    """시도명으로 해당 SGG 코드 목록 반환"""
    codes = []
    for code, name in SGG_CODES.items():
        if sido in name:
            codes.append(code)
    return codes


def fetch_month(api: KoreaLandAPI, session, sgg_code: str,
                year: int, month: int,
                property_types: list[str]) -> dict:
    """단일 시군구+월 거래 수집"""

    total_stats = {"inserted": 0, "skipped": 0, "errors": 0}

    for ptype in property_types:
        try:
            if ptype == "아파트":
                records = api.fetch_apt_transactions(sgg_code, year, month)
            elif ptype in ("다세대", "연립"):
                records = api.fetch_multi_transactions(sgg_code, year, month)
            elif ptype == "오피스텔":
                records = api.fetch_office_transactions(sgg_code, year, month)
            else:
                continue

            if records:
                stats = bulk_ingest_transactions(session, records)
                total_stats["inserted"] += stats["inserted"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]

                logger.debug(
                    f"  [{ptype}] {sgg_code} {year}-{month:02d}: "
                    f"{len(records)}건 조회 / "
                    f"삽입 {stats['inserted']} / 중복 {stats['skipped']}"
                )

            time.sleep(0.3)  # API rate limit

        except Exception as e:
            logger.warning(f"[{ptype}] {sgg_code} 오류: {e}")
            total_stats["errors"] += 1

    return total_stats


def run(args):
    """메인 실행"""

    # API 키 확인
    api_key = os.getenv("KOREA_API_KEY", "")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        logger.error("KOREA_API_KEY 환경변수가 설정되지 않았습니다.")
        logger.error("API 신청: https://www.data.go.kr/ → '아파트매매 실거래자료' 검색")
        logger.error(".env 파일에 KOREA_API_KEY=발급받은키 를 추가하세요.")
        sys.exit(1)

    # DB 초기화
    init_db()

    api = KoreaLandAPI(api_key=api_key)

    # 수집 대상 SGG 코드 결정
    if args.sgg:
        sgg_codes = [args.sgg]
    elif args.sido:
        sgg_codes = get_sido_sgg_codes(args.sido)
        if not sgg_codes:
            logger.error(f"시도명을 찾을 수 없습니다: {args.sido}")
            sys.exit(1)
        logger.info(f"{args.sido}: {len(sgg_codes)}개 시군구")
    else:
        sgg_codes = get_all_sgg_codes()
        logger.info(f"전국 {len(sgg_codes)}개 시군구")

    # 수집 기간 결정
    if args.months:
        today = date.today()
        target_months = []
        for m in range(args.months):
            d = today - timedelta(days=30 * m)
            target_months.append((d.year, d.month))
        target_months.reverse()
    else:
        target_months = [(args.year, args.month)]

    # 수집 유형
    if args.type:
        property_types = [args.type]
    else:
        property_types = PROPERTY_TYPES

    # 실행
    grand_total = {"inserted": 0, "skipped": 0, "errors": 0}
    session = SessionLocal()

    try:
        for year, month in target_months:
            logger.info(f"\n{'='*50}")
            logger.info(f"▶ {year}-{month:02d} 수집 시작 "
                        f"(SGG: {len(sgg_codes)}개, 유형: {property_types})")

            month_total = {"inserted": 0, "skipped": 0, "errors": 0}

            for i, sgg_code in enumerate(sgg_codes):
                sgg_name = SGG_CODES.get(sgg_code, sgg_code)
                stats = fetch_month(api, session, sgg_code, year, month, property_types)

                for k in month_total:
                    month_total[k] += stats.get(k, 0)

                # 진도 표시 (10개마다)
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"  진도: {i+1}/{len(sgg_codes)} | "
                        f"삽입 {month_total['inserted']:,} / "
                        f"중복 {month_total['skipped']:,}"
                    )

            logger.info(
                f"✓ {year}-{month:02d} 완료: "
                f"삽입 {month_total['inserted']:,} / "
                f"중복 {month_total['skipped']:,} / "
                f"오류 {month_total['errors']:,}"
            )

            for k in grand_total:
                grand_total[k] += month_total.get(k, 0)

    finally:
        session.close()

    logger.info(f"\n{'='*50}")
    logger.info("▶ 전체 완료")
    logger.info(f"  삽입: {grand_total['inserted']:,}건")
    logger.info(f"  중복: {grand_total['skipped']:,}건")
    logger.info(f"  오류: {grand_total['errors']:,}건")


def main():
    parser = argparse.ArgumentParser(
        description="국토부 실거래가 공공API → DB 적재"
    )

    # 기간 옵션 (둘 중 하나)
    period_group = parser.add_mutually_exclusive_group(required=True)
    period_group.add_argument("--months", type=int,
                              help="최근 N개월 수집 (예: --months 12)")
    period_group.add_argument("--year", type=int,
                              help="수집 연도 (--month 와 함께)")

    parser.add_argument("--month", type=int, default=None,
                        help="수집 월 (1~12, --year 와 함께)")

    # 지역 옵션 (선택)
    region_group = parser.add_mutually_exclusive_group()
    region_group.add_argument("--sido", type=str,
                              help="시도 (예: 경기도, 서울특별시)")
    region_group.add_argument("--sgg", type=str,
                              help="시군구 코드 (예: 41590)")

    # 유형 옵션 (선택)
    parser.add_argument("--type", type=str, choices=PROPERTY_TYPES,
                        default=None,
                        help="수집 유형 (기본: 전 유형)")

    args = parser.parse_args()

    # 유효성 검사
    if args.year and not args.month:
        today = date.today()
        args.month = today.month
        logger.info(f"--month 미지정: 현재 월({args.month}) 사용")

    if args.year and not (1 <= args.month <= 12):
        parser.error("--month 는 1~12 사이 값이어야 합니다.")

    run(args)


if __name__ == "__main__":
    main()
