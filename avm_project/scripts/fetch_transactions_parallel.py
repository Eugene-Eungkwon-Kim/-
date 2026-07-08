"""
국토부 실거래가 공공API → DB 적재 스크립트 (병렬 처리 버전)

사용 예시:
    # 최근 12개월 전국 (병렬 처리, 3개 워커)
    python scripts/fetch_transactions_parallel.py --months 12 --workers 3

    # 경기도, 특정 기간 (병렬 처리)
    python scripts/fetch_transactions_parallel.py \
      --year 2026 --month 6 --sido 경기도 --workers 3

    # 체크포인트에서 재개
    python scripts/fetch_transactions_parallel.py \
      --months 12 --workers 3 --checkpoint data/collection_checkpoint.json

특징:
    - 멀티프로세싱: 지역별 병렬 처리
    - 체크포인트: 중단 시 마지막 위치에서 재개
    - 진도 추적: tqdm으로 실시간 진도 표시
    - 오류 복구: 자동 재시도 (최대 3회)

설정:
    환경변수 KOREA_API_KEY 또는 .env 파일에 API 키 설정 필요
    API 키 신청: https://www.data.go.kr/
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, timedelta
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List, Tuple

from tqdm import tqdm

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
        logging.FileHandler("data/fetch_transactions_parallel.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

PROPERTY_TYPES = ["아파트", "다세대", "오피스텔"]
MAX_RETRIES = 3
API_KEY_PLACEHOLDERS = {
    "YOUR_API_KEY_HERE",
    "your_api_key_here",
    "발급받은_키",
    "<발급받은 키>",
    "",
}


def has_valid_api_key(api_key: str) -> bool:
    """환경변수/API 키 placeholder를 실제 키로 오인하지 않도록 검사한다."""
    return bool(api_key and api_key.strip() not in API_KEY_PLACEHOLDERS)


def get_api_key() -> str:
    """RTMS/data.go.kr 계열 환경변수 이름을 순서대로 확인한다."""
    for name in ("KOREA_API_KEY", "RTMS_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY", "PUBLIC_DATA_SERVICE_KEY"):
        value = os.getenv(name, "").strip()
        if has_valid_api_key(value):
            return value
    return ""


class CheckpointManager:
    """체크포인트 관리 (완료된 작업 추적)"""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data = self._load()

    def _load(self) -> Dict:
        """체크포인트 파일에서 로드"""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✓ 체크포인트 로드: {len(data['completed'])}개 완료된 작업")
                    return data
            except Exception as e:
                logger.warning(f"체크포인트 로드 실패: {e}")

        return {
            "started_at": date.today().isoformat(),
            "completed": {},
            "stats": {"inserted": 0, "skipped": 0, "errors": 0}
        }

    def is_completed(self, sgg_code: str, year: int, month: int) -> bool:
        """작업이 완료되었는지 확인"""
        key = f"{sgg_code}_{year}_{month:02d}"
        return key in self.data["completed"]

    def mark_completed(self, sgg_code: str, year: int, month: int, stats: Dict):
        """작업을 완료된 것으로 표시"""
        key = f"{sgg_code}_{year}_{month:02d}"
        self.data["completed"][key] = {
            "timestamp": date.today().isoformat(),
            "stats": stats
        }
        # 누적 통계 업데이트
        for k in ["inserted", "skipped", "errors"]:
            self.data["stats"][k] += stats.get(k, 0)
        self._save()

    def _save(self):
        """체크포인트 파일에 저장"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"체크포인트 저장 실패: {e}")

    def get_stats(self) -> Dict:
        """누적 통계 반환"""
        return self.data["stats"]


def fetch_region_month(task: Tuple) -> Dict:
    """
    단일 지역+월 거래 수집 (워커 프로세스에서 실행)

    Args:
        task: (sgg_code, year, month, property_types, checkpoint_dict)

    Returns:
        {'sgg_code': ..., 'year': ..., 'month': ..., 'stats': {...}}
    """
    sgg_code, year, month, property_types, checkpoint_file = task

    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    # 워커 프로세스마다 새로운 DB 세션 생성
    session = SessionLocal()

    try:
        # 체크포인트 확인
        checkpoint = CheckpointManager(checkpoint_file) if checkpoint_file else None
        if checkpoint and checkpoint.is_completed(sgg_code, year, month):
            logger.debug(f"[SKIP] {sgg_code} {year}-{month:02d} (이미 완료)")
            return {
                'sgg_code': sgg_code,
                'year': year,
                'month': month,
                'stats': stats,
                'skipped': True
            }

        # API 클라이언트 생성
        api_key = get_api_key()
        api = KoreaLandAPI(api_key=api_key)

        # 각 물건 유형별 수집
        had_failure = False
        for ptype in property_types:
            try:
                records = []

                if ptype == "아파트":
                    records = api.fetch_apt_transactions(sgg_code, year, month)
                elif ptype in ("다세대", "연립"):
                    records = api.fetch_multi_transactions(sgg_code, year, month)
                elif ptype == "오피스텔":
                    records = api.fetch_office_transactions(sgg_code, year, month)

                if records:
                    ingest_stats = bulk_ingest_transactions(session, records)
                    stats["inserted"] += ingest_stats.get("inserted", 0)
                    stats["skipped"] += ingest_stats.get("skipped", 0)
                    stats["errors"] += ingest_stats.get("errors", 0)

                time.sleep(0.5)  # Rate limit 준수

            except Exception as e:
                had_failure = True
                logger.error(f"[FAIL] {sgg_code} {year}-{month:02d} [{ptype}]: {e}")
                stats["errors"] += 1

        if checkpoint and not had_failure:
            checkpoint.mark_completed(sgg_code, year, month, stats)
        elif checkpoint and had_failure:
            logger.warning(
                f"체크포인트 미저장: {sgg_code} {year}-{month:02d} API 실패가 있어 재시도 필요"
            )

        return {
            'sgg_code': sgg_code,
            'year': year,
            'month': month,
            'stats': stats,
            'skipped': False
        }

    except Exception as e:
        logger.error(f"[FATAL] {sgg_code} {year}-{month:02d}: {e}")
        stats["errors"] += 1
        return {
            'sgg_code': sgg_code,
            'year': year,
            'month': month,
            'stats': stats,
            'skipped': False,
            'error': str(e)
        }

    finally:
        session.close()


def get_sido_sgg_codes(sido: str) -> List[str]:
    """시도명으로 해당 SGG 코드 목록 반환"""
    codes = []
    for code, name in SGG_CODES.items():
        if sido in name:
            codes.append(code)
    return codes


def run_parallel(args):
    """메인 실행 (병렬 처리)"""

    # API 키 확인
    api_key = get_api_key()
    if not has_valid_api_key(api_key):
        logger.error("KOREA_API_KEY 환경변수가 설정되지 않았습니다.")
        logger.error("API 신청: https://www.data.go.kr/ → '아파트매매 실거래자료' 검색")
        logger.error(".env 파일 또는 런타임 환경변수에 KOREA_API_KEY/RTMS_SERVICE_KEY/DATA_GO_KR_SERVICE_KEY 중 하나를 설정하세요.")
        sys.exit(1)

    # DB 초기화
    init_db()

    # 체크포인트 관리자
    checkpoint_file = args.checkpoint if hasattr(args, 'checkpoint') and args.checkpoint else None
    checkpoint = CheckpointManager(checkpoint_file) if checkpoint_file else None

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

    # 작업 큐 생성
    tasks = []
    for year, month in target_months:
        for sgg_code in sgg_codes:
            # 이미 완료된 작업 스킵
            if checkpoint and checkpoint.is_completed(sgg_code, year, month):
                continue
            tasks.append((sgg_code, year, month, property_types, checkpoint_file))

    logger.info(f"\n{'='*60}")
    logger.info(f"▶ 병렬 수집 시작")
    logger.info(f"  기간: {target_months[0]} ~ {target_months[-1]}")
    logger.info(f"  지역: {len(sgg_codes)}개 시군구")
    logger.info(f"  유형: {property_types}")
    logger.info(f"  작업: {len(tasks)}개 (이미 완료: {len(sgg_codes) * len(target_months) - len(tasks)})")
    logger.info(f"  워커: {args.workers}개 프로세스")
    logger.info(f"{'='*60}\n")

    # 병렬 처리
    grand_total = {"inserted": 0, "skipped": 0, "errors": 0}

    try:
        with Pool(args.workers) as pool:
            results = []
            for result in tqdm(
                pool.imap_unordered(fetch_region_month, tasks),
                total=len(tasks),
                desc="데이터 수집",
                unit="작업",
                ncols=80
            ):
                results.append(result)

                # 통계 누적
                for k in grand_total:
                    grand_total[k] += result['stats'].get(k, 0)

                # 주기적 진도 보고
                if len(results) % max(1, len(tasks) // 10) == 0:
                    logger.info(
                        f"진도: {len(results)}/{len(tasks)} | "
                        f"삽입 {grand_total['inserted']:,} / "
                        f"중복 {grand_total['skipped']:,} / "
                        f"오류 {grand_total['errors']:,}"
                    )

    except KeyboardInterrupt:
        logger.warning("\n! 사용자 중단 (Ctrl+C)")
        logger.info(f"진행 중 누적: 삽입 {grand_total['inserted']:,} / 중복 {grand_total['skipped']:,}")
        logger.info(f"체크포인트: {checkpoint_file}")
        logger.info("다시 실행 시 위 체크포인트 옵션으로 재개 가능합니다.")
        sys.exit(0)

    # 최종 보고
    logger.info(f"\n{'='*60}")
    logger.info("✓ 병렬 수집 완료")
    logger.info(f"  삽입: {grand_total['inserted']:,}건")
    logger.info(f"  중복: {grand_total['skipped']:,}건")
    logger.info(f"  오류: {grand_total['errors']:,}건")
    attempted_total = grand_total["inserted"] + grand_total["skipped"] + grand_total["errors"]
    success_rate = 100 * (grand_total["inserted"] + grand_total["skipped"]) / max(1, attempted_total)
    logger.info(f"  성공률: {success_rate:.1f}%")
    logger.info(f"{'='*60}")

    # 최종 통계 저장
    if checkpoint and Path(checkpoint_file).exists():
        logger.info(f"✓ 체크포인트 저장: {checkpoint_file}")
    elif checkpoint:
        logger.info("체크포인트 미생성: 완료된 작업이 없거나 API 실패로 재시도가 필요합니다.")


def main():
    parser = argparse.ArgumentParser(
        description="국토부 실거래가 공공API → DB 적재 (병렬 처리 버전)"
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

    # 병렬 처리 옵션
    parser.add_argument("--workers", type=int, default=3,
                        help="병렬 워커 수 (기본: 3, 권장: 2~5)")

    # 체크포인트 옵션
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="체크포인트 파일 경로 (재개 시 사용)")

    args = parser.parse_args()

    # 유효성 검사
    if args.year and not args.month:
        today = date.today()
        args.month = today.month
        logger.info(f"--month 미지정: 현재 월({args.month}) 사용")

    if args.year and not (1 <= args.month <= 12):
        parser.error("--month 는 1~12 사이 값이어야 합니다.")

    # 워커 수 검증
    if not (1 <= args.workers <= 10):
        parser.error("--workers 는 1~10 사이 값이어야 합니다.")

    run_parallel(args)


if __name__ == "__main__":
    main()

