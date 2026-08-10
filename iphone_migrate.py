#!/usr/bin/env python3
"""iPhone 데이터 정리 — Live Photo / 슬로모션 / 타임랩스 / 편집본 구분."""

import argparse
import sys
from pathlib import Path

from phonesort.categories import iphone_category, live_photo_keys
from phonesort.cli import (common_options, organizer_kwargs, print_preamble,
                           print_summary, save_report)
from phonesort.organizer import Organizer, PathValidationError

REPORT_NAME = "iphone_migration_report.json"


def iphone_classifier_factory(files: list[Path]):
    """파일 목록 전체를 봐야 Live Photo 쌍을 알 수 있다."""
    keys = live_photo_keys(files)
    print(f"Live Photo 쌍 {len(keys)}개 감지")
    return lambda path: iphone_category(path, keys)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="iPhone 데이터 정리 (HEIC / Live Photo 지원)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예:
  # 미리보기
  python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과 --dry-run

  # 실제 실행
  python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과

HEIC 촬영일을 제대로 읽으려면: pip install Pillow pillow-heif
""",
    )
    parser.add_argument("source", help="iPhone에서 내보낸 폴더 경로")
    parser.add_argument("dest", help="정리된 파일을 저장할 폴더")
    return common_options(parser)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()

    print_preamble(source, dest, args)

    organizer = Organizer(
        source, dest,
        classifier_factory=iphone_classifier_factory,
        **organizer_kwargs(args),
    )
    try:
        stats = organizer.run()
    except PathValidationError as exc:
        print(f"오류: {exc}")
        return 1

    if args.prune_empty_dirs:
        removed = organizer.prune_empty_dirs()
        if removed:
            print(f"\n빈 폴더 {removed}개 삭제")

    if not args.dry_run:
        save_report(dest, stats, REPORT_NAME, 기기="iPhone")

    print_summary(stats, args.dry_run)
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
