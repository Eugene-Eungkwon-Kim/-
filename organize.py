#!/usr/bin/env python3
"""휴대폰 파일 정리 — 종류별/날짜별 분류, 이름 정리, 중복 처리."""

import argparse
import sys
from pathlib import Path

from phonesort.cli import common_options, organizer_kwargs, print_preamble, print_summary
from phonesort.organizer import Organizer, PathValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="휴대폰 파일 정리: 종류별/날짜별 분류, 이름 정리, 중복 처리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python organize.py /Volumes/Phone/DCIM ./정리된파일
  python organize.py ~/Downloads/phone_backup ./output --dry-run
  python organize.py ~/backup ./output --delete-duplicates
""",
    )
    parser.add_argument("source", help="정리할 원본 폴더 경로")
    parser.add_argument("dest", help="정리된 파일을 저장할 폴더 경로")
    return common_options(parser)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()

    print_preamble(source, dest, args)

    organizer = Organizer(source, dest, **organizer_kwargs(args))
    try:
        stats = organizer.run()
    except PathValidationError as exc:
        print(f"오류: {exc}")
        return 1

    if args.prune_empty_dirs:
        removed = organizer.prune_empty_dirs()
        if removed:
            print(f"\n빈 폴더 {removed}개 삭제")

    print_summary(stats, args.dry_run)
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
