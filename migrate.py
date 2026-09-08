#!/usr/bin/env python3
"""모바일 기기 데이터 마이그레이션 — Android(ADB) 또는 로컬 폴더."""

import argparse
import sys
from pathlib import Path

from phonesort import adb
from phonesort.cli import (common_options, organizer_kwargs, print_preamble,
                           print_summary, save_report)
from phonesort.organizer import Organizer, PathValidationError

REPORT_NAME = "migration_report.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="모바일 기기 데이터 마이그레이션",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # Android 기기에서 직접 마이그레이션 (ADB 필요)
  python migrate.py --android ./마이그레이션결과

  # 로컬 폴더 정리
  python migrate.py --source ~/Downloads/phone_backup ./마이그레이션결과

  # 미리보기
  python migrate.py --source ./test_phone ./output --dry-run
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--android", action="store_true",
                       help="ADB로 Android 기기에서 직접 가져오기")
    group.add_argument("--source", metavar="폴더", help="정리할 로컬 폴더 경로")
    parser.add_argument("dest", help="결과물을 저장할 폴더")
    return common_options(parser)


def resolve_source(args: argparse.Namespace, dest: Path) -> tuple[Path, str] | None:
    """정리 대상 폴더와 소스 설명을 정한다. 실패하면 None."""
    if not args.android:
        return Path(args.source).expanduser().resolve(), str(Path(args.source).expanduser())

    print("=== Android 기기 데이터 추출 ===")
    device, problem = adb.find_device()
    if device is None:
        print(problem)
        return None
    print(f"기기 감지: {device}")

    raw_root, pulled = adb.pull_all(dest, args.dry_run)
    if pulled == 0:
        print("가져올 수 있는 폴더가 없습니다.")
        return None
    if args.dry_run:
        print("(미리보기 모드라 실제로 받지 않았습니다)")
        return None
    return raw_root, f"Android({device})"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dest = Path(args.dest).expanduser().resolve()

    resolved = resolve_source(args, dest)
    if resolved is None:
        return 1
    source, source_label = resolved

    print_preamble(source, dest, args)

    organizer = Organizer(source, dest, **organizer_kwargs(args))
    try:
        stats = organizer.run()
    except PathValidationError as exc:
        print(f"오류: {exc}")
        return 1

    # ADB로 받은 원본 폴더는 정리 후 껍데기만 남으므로 항상 치운다
    if args.android or args.prune_empty_dirs:
        removed = organizer.prune_empty_dirs()
        if removed:
            print(f"\n빈 폴더 {removed}개 삭제")

    if not args.dry_run:
        save_report(dest, stats, REPORT_NAME, 소스유형=source_label)

    print_summary(stats, args.dry_run)
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
