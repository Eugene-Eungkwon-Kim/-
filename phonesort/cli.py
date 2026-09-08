"""세 CLI가 공유하는 인자 정의, 요약 출력, 보고서 저장."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from .dates import missing_dependencies
from .organizer import Stats


def common_options(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--dry-run", action="store_true",
                        help="미리보기. 파일을 하나도 건드리지 않는다")
    parser.add_argument("--delete-duplicates", action="store_true",
                        help="중복 파일을 삭제한다 (기본은 중복/ 폴더로 격리)")
    parser.add_argument("--verify", action="store_true",
                        help="이동 후 내용 해시까지 다시 확인한다 (느림)")
    parser.add_argument("--no-resume", action="store_true",
                        help="저널을 무시하고 처음부터 다시 처리한다")
    parser.add_argument("--workers", type=int, default=None,
                        help="해싱 병렬 스레드 수 (기본: 자동)")
    parser.add_argument("--prune-empty-dirs", action="store_true",
                        help="정리 후 원본에 남은 빈 폴더를 지운다")
    return parser


def organizer_kwargs(args: argparse.Namespace) -> dict:
    return {
        "dry_run": args.dry_run,
        "delete_duplicates": args.delete_duplicates,
        "verify": args.verify,
        "resume": not args.no_resume,
        "workers": args.workers,
    }


def print_preamble(source: Path, dest: Path, args: argparse.Namespace) -> None:
    if args.dry_run:
        print("*** 미리보기 모드 (--dry-run) — 실제 파일은 변경되지 않습니다 ***")
    if args.delete_duplicates:
        print("*** 중복 파일을 삭제합니다 (--delete-duplicates) ***")
    else:
        print("중복 파일은 '중복/' 폴더로 격리됩니다. 삭제하려면 --delete-duplicates")

    for dependency in missing_dependencies():
        print(f"※ 미설치: {dependency} — 파일 수정 시각으로 대체합니다")

    print(f"원본: {source}")
    print(f"대상: {dest}")


def print_summary(stats: Stats, dry_run: bool) -> None:
    print("\n" + "=" * 50)
    line = f"  이동 {stats.moved}개 | 중복 {stats.duplicates}개 | 오류 {stats.errors}개"
    if stats.skipped:
        line += f" | 건너뜀 {stats.skipped}개"
    print(line)
    if stats.by_category:
        print("\n  카테고리별:")
        for category, count in sorted(stats.by_category.items(), key=lambda item: -item[1]):
            print(f"    {category:<10} {count}개")
    if dry_run:
        print("\n  (미리보기 모드 — 실제 변경 없음)")
    print("=" * 50)


def save_report(dest: Path, stats: Stats, filename: str, **extra) -> Path:
    report = {
        "실행일시": datetime.now().isoformat(timespec="seconds"),
        "이동": stats.moved,
        "중복": stats.duplicates,
        "건너뜀": stats.skipped,
        "오류": stats.errors,
        "카테고리별": stats.by_category,
        **extra,
    }
    path = dest / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n보고서: {path}")
    return path
