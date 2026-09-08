#!/usr/bin/env python3
"""휴대폰 저장공간 정리 — 용량 분석, 중복·캐시 정리로 공간 회수

기본은 '분석만' 수행하는 읽기 전용 모드입니다.
실제 삭제는 --apply 를 명시해야 실행됩니다.

사용 예:
  python cleanup.py ~/Desktop/iPhone_내보내기                 # 분석만
  python cleanup.py ~/Desktop/iPhone_내보내기 --apply         # 중복·캐시·빈폴더 삭제
  python cleanup.py --android                                 # 기기 용량 리포트 (읽기 전용)
"""

import os
import re
import sys
import json
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

FILE_CATEGORIES = {
    "사진":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
               ".heic", ".heif", ".webp", ".raw", ".cr2", ".nef", ".arw"},
    "동영상":  {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv",
               ".flv", ".webm", ".ts", ".mts"},
    "음악":    {".mp3", ".flac", ".aac", ".wav", ".ogg", ".m4a", ".wma", ".opus"},
    "문서":    {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
               ".txt", ".hwp", ".hwpx", ".odt", ".rtf", ".csv"},
    "압축파일": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "APK":    {".apk", ".xapk"},
    "기타":   set(),
}

# 삭제해도 안전한 캐시·썸네일 디렉토리 이름 (소문자 비교)
CACHE_DIR_NAMES = {
    ".thumbnails", ".thumbnail", "cache", "caches", ".cache",
    ".trashed", "thumbdata", "lost.dir", ".temp", "tmp",
}

# 캐시성 파일 이름 접두어
CACHE_FILE_PREFIXES = ("thumbdata", ".trashed-")

# 사본으로 보이는 파일명 패턴 (중복 그룹에서 먼저 삭제 후보가 됨)
COPY_MARKERS = re.compile(
    r"(\(\d+\)|_copy|-copy|\bcopy\b|사본|복사본|_\d+$|-\d+$|_dup)",
    re.IGNORECASE,
)

# 원본이 있을 가능성이 높은 디렉토리 (중복 그룹에서 유지 우선순위가 높음)
ORIGINAL_DIRS = ("dcim", "camera", "100apple", "raw")

# ADB 로 용량을 조회할 기기 경로
ANDROID_PATHS = [
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Movies",
    "/sdcard/Music",
    "/sdcard/Download",
    "/sdcard/Documents",
    "/sdcard/WhatsApp",
    "/sdcard/Telegram",
    "/sdcard/KakaoTalk",
    "/sdcard/Android/data",
]


# ── 유틸리티 ────────────────────────────────────────────────────────────────

def human(n: int) -> str:
    """바이트를 읽기 쉬운 단위로 변환."""
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < step:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= step
    return f"{n:.1f}PB"


def parse_size(text: str) -> int:
    """'100MB', '1.5G', '2048' 같은 표기를 바이트로 변환."""
    s = text.strip().upper().replace("IB", "B")
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix in ("TB", "GB", "MB", "KB", "B"):
        if s.endswith(suffix):
            num = s[: -len(suffix)].strip()
            return int(float(num or 0) * units[suffix])
    for suffix, mult in (("T", units["TB"]), ("G", units["GB"]),
                         ("M", units["MB"]), ("K", units["KB"])):
        if s.endswith(suffix):
            return int(float(s[:-1].strip() or 0) * mult)
    return int(float(s))


def get_category(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "기타"


def get_hash(path: Path, block: int = 65536) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def is_cache_path(path: Path, root: Path) -> bool:
    """캐시·썸네일 경로인지 판별."""
    if path.name.lower().startswith(CACHE_FILE_PREFIXES):
        return True
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    return any(p.lower() in CACHE_DIR_NAMES for p in parts[:-1])


def inside(path: Path, root: Path) -> bool:
    """path 가 root 안에 있는지 확인 (루트 밖 삭제 방지)."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# ── 스캔 ────────────────────────────────────────────────────────────────────

def scan(root: Path) -> dict:
    """디렉토리를 훑어 용량 정보를 수집."""
    files: list[tuple[Path, int]] = []
    by_category: dict[str, list[int]] = defaultdict(list)
    by_folder: dict[Path, int] = defaultdict(int)
    cache_files: list[tuple[Path, int]] = []
    errors = 0

    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        for name in filenames:
            p = d / name
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                size = p.stat().st_size
            except OSError:
                errors += 1
                continue

            files.append((p, size))
            by_category[get_category(p)].append(size)
            by_folder[d] += size
            if is_cache_path(p, root):
                cache_files.append((p, size))

    empty_dirs = count_empty_dirs(root)

    return {
        "files": files,
        "by_category": by_category,
        "by_folder": by_folder,
        "cache_files": cache_files,
        "empty_dirs": empty_dirs,
        "errors": errors,
    }


def keep_priority(path: Path) -> tuple:
    """중복 그룹 정렬 키 — 값이 작을수록 '유지할 원본'에 가깝다.

    카메라 원본(DCIM 등)을 우선 유지하고, 사본처럼 보이는 이름을
    먼저 삭제 후보로 돌린다. 그다음 오래된 파일을 원본으로 본다.
    """
    lower_parts = [p.lower() for p in path.parts[:-1]]
    in_original_dir = any(
        any(d in part for d in ORIGINAL_DIRS) for part in lower_parts
    )
    looks_like_copy = bool(COPY_MARKERS.search(path.stem))
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = float("inf")

    return (
        looks_like_copy,        # 사본처럼 보이면 뒤로
        not in_original_dir,    # 카메라 폴더면 앞으로
        mtime,                  # 오래된 파일이 원본
        len(path.parts),
        str(path),
    )


def count_empty_dirs(root: Path) -> list[Path]:
    """하위까지 비어 있는(파일이 하나도 없는) 폴더를 모두 찾는다."""
    empty: list[Path] = []
    has_file: dict[Path, bool] = {}

    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        d = Path(dirpath)
        child_has = any(has_file.get(d / name, False) for name in dirnames)
        has_file[d] = bool(filenames) or child_has
        if d != root and not has_file[d]:
            empty.append(d)

    return empty


def find_duplicates(files: list[tuple[Path, int]]) -> tuple[list[list[Path]], int]:
    """중복 파일 그룹과 회수 가능 용량을 반환.

    같은 크기의 파일만 해시하므로 전체 해시보다 훨씬 빠릅니다.
    """
    by_size: dict[int, list[Path]] = defaultdict(list)
    for p, size in files:
        if size > 0:
            by_size[size].append(p)

    groups: list[list[Path]] = []
    reclaimable = 0

    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for p in paths:
            try:
                by_hash[get_hash(p)].append(p)
            except OSError:
                continue
        for same in by_hash.values():
            if len(same) > 1:
                same.sort(key=keep_priority)
                groups.append(same)
                reclaimable += size * (len(same) - 1)

    groups.sort(key=lambda g: -g[0].stat().st_size * (len(g) - 1))
    return groups, reclaimable


# ── 리포트 ──────────────────────────────────────────────────────────────────

def print_report(root: Path, data: dict, dup_groups, dup_bytes, top: int, min_size: int):
    files = data["files"]
    total = sum(s for _, s in files)

    print(f"\n{'=' * 52}")
    print(f"  저장공간 분석: {root}")
    print(f"{'=' * 52}")
    print(f"  전체 {len(files):,}개 파일 · {human(total)}")
    if data["errors"]:
        print(f"  (읽지 못한 항목 {data['errors']}개)")

    # 카테고리별
    print(f"\n── 카테고리별 용량 ──")
    cats = sorted(data["by_category"].items(), key=lambda kv: -sum(kv[1]))
    for cat, sizes in cats:
        s = sum(sizes)
        pct = (s / total * 100) if total else 0
        bar = "█" * max(1, round(pct / 4)) if s else ""
        print(f"  {cat:<8} {human(s):>9}  {pct:5.1f}%  {bar}")

    # 폴더별 top
    print(f"\n── 용량 상위 폴더 (최대 {top}개) ──")
    folders = sorted(data["by_folder"].items(), key=lambda kv: -kv[1])[:top]
    for d, s in folders:
        try:
            rel = d.relative_to(root)
        except ValueError:
            rel = d
        label = str(rel) if str(rel) != "." else "(루트)"
        print(f"  {human(s):>9}  {label}")

    # 대용량 파일
    big = sorted((f for f in files if f[1] >= min_size), key=lambda f: -f[1])[:top]
    print(f"\n── {human(min_size)} 이상 대용량 파일 (최대 {top}개) ──")
    if big:
        for p, s in big:
            try:
                rel = p.relative_to(root)
            except ValueError:
                rel = p
            print(f"  {human(s):>9}  {rel}")
        print(f"  → 이 파일들은 자동 삭제하지 않습니다. 직접 확인하세요.")
    else:
        print(f"  없음")

    # 회수 가능 항목
    cache_bytes = sum(s for _, s in data["cache_files"])
    print(f"\n── 회수 가능 항목 ──")
    print(f"  중복 파일   {len(dup_groups):>5}개 그룹   {human(dup_bytes):>9}")
    print(f"  캐시·썸네일 {len(data['cache_files']):>5}개 파일   {human(cache_bytes):>9}")
    print(f"  빈 폴더     {len(data['empty_dirs']):>5}개")
    print(f"  {'-' * 40}")
    print(f"  회수 예상 총량            {human(dup_bytes + cache_bytes):>9}")
    if total:
        print(f"  전체 대비                     {(dup_bytes + cache_bytes) / total * 100:5.1f}%")

    if dup_groups:
        print(f"\n── 중복 상위 (최대 {min(top, len(dup_groups))}개 그룹) ──")
        for g in dup_groups[:top]:
            size = g[0].stat().st_size
            print(f"  {human(size):>9} × {len(g)}개")
            for p in g:
                mark = "유지" if p is g[0] else "삭제"
                try:
                    rel = p.relative_to(root)
                except ValueError:
                    rel = p
                print(f"            [{mark}] {rel}")


def apply_cleanup(root: Path, data: dict, dup_groups) -> dict:
    """중복·캐시·빈폴더를 실제로 삭제."""
    freed = 0
    removed = {"중복": 0, "캐시": 0, "빈폴더": 0}

    print(f"\n{'=' * 52}")
    print(f"  삭제 실행 (--apply)")
    print(f"{'=' * 52}")

    for g in dup_groups:
        for p in g[1:]:
            if not inside(p, root):
                continue
            try:
                size = p.stat().st_size
                p.unlink()
                freed += size
                removed["중복"] += 1
            except OSError as e:
                print(f"  [오류] {p}: {e}")

    for p, size in data["cache_files"]:
        if not inside(p, root) or not p.exists():
            continue
        try:
            p.unlink()
            freed += size
            removed["캐시"] += 1
        except OSError as e:
            print(f"  [오류] {p}: {e}")

    # 삭제 후 새로 빈 폴더가 될 수 있으므로 다시 훑는다
    for dirpath, _, _ in os.walk(root, topdown=False):
        d = Path(dirpath)
        if d == root or not inside(d, root):
            continue
        try:
            if not any(d.iterdir()):
                d.rmdir()
                removed["빈폴더"] += 1
        except OSError:
            pass

    print(f"  중복 {removed['중복']}개 · 캐시 {removed['캐시']}개 · 빈폴더 {removed['빈폴더']}개 삭제")
    print(f"  회수한 용량: {human(freed)}")
    return {"회수용량": freed, "삭제": removed}


def save_report(root: Path, data: dict, dup_groups, dup_bytes, applied: dict | None, out: Path):
    files = data["files"]
    total = sum(s for _, s in files)
    cache_bytes = sum(s for _, s in data["cache_files"])

    report = {
        "실행일시": datetime.now().isoformat(),
        "대상경로": str(root),
        "전체파일수": len(files),
        "전체용량": total,
        "전체용량표시": human(total),
        "카테고리별": {
            cat: {"파일수": len(sizes), "용량": sum(sizes), "용량표시": human(sum(sizes))}
            for cat, sizes in sorted(data["by_category"].items(), key=lambda kv: -sum(kv[1]))
        },
        "회수가능": {
            "중복그룹수": len(dup_groups),
            "중복용량": dup_bytes,
            "캐시파일수": len(data["cache_files"]),
            "캐시용량": cache_bytes,
            "빈폴더수": len(data["empty_dirs"]),
            "합계": dup_bytes + cache_bytes,
            "합계표시": human(dup_bytes + cache_bytes),
        },
        "실제삭제": applied,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  보고서: {out}")


# ── ADB (기기 용량 리포트, 읽기 전용) ───────────────────────────────────────

def adb(*args, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return -1, "adb 명령을 찾을 수 없습니다. Android SDK를 설치하세요."
    except subprocess.TimeoutExpired:
        return -1, "ADB 명령 시간 초과"


def android_report() -> int:
    code, out = adb("devices")
    if code != 0:
        print(f"ADB 오류: {out}")
        return 1
    devices = [l for l in out.splitlines()[1:] if l.strip() and "device" in l]
    if not devices:
        print("연결된 Android 기기가 없습니다.")
        print("  1. 설정 → 개발자 옵션에서 USB 디버깅 활성화")
        print("  2. USB 케이블 연결 후 기기에서 '허용' 선택")
        return 1

    print(f"기기: {devices[0]}")

    code, out = adb("shell", "df", "-h", "/sdcard")
    if code == 0 and out:
        print(f"\n── 내부 저장소 ──")
        for line in out.splitlines():
            print(f"  {line}")

    print(f"\n── 폴더별 사용량 ──")
    rows = []
    for remote in ANDROID_PATHS:
        code, out = adb("shell", "du", "-sk", remote, timeout=120)
        if code != 0 or not out:
            continue
        first = out.splitlines()[0].split(None, 1)
        if not first or not first[0].isdigit():
            continue
        rows.append((int(first[0]) * 1024, remote))

    if not rows:
        print("  조회된 폴더가 없습니다.")
        return 0

    for size, remote in sorted(rows, key=lambda r: -r[0]):
        print(f"  {human(size):>9}  {remote}")

    print(f"\n  합계 {human(sum(s for s, _ in rows))}")
    print("\n  ※ 기기 파일은 삭제하지 않습니다.")
    print("     먼저 `python migrate.py --android <대상폴더>` 로 내려받은 뒤")
    print("     `python cleanup.py <대상폴더> --apply` 로 정리하세요.")
    return 0


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="휴대폰 저장공간 정리 — 용량 분석 및 중복·캐시 정리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 분석만 (파일 변경 없음)
  python cleanup.py ~/Desktop/iPhone_내보내기

  # 100MB 이상 파일까지 함께 보기
  python cleanup.py ~/Desktop/iPhone_내보내기 --min-size 100MB --top 30

  # 중복·캐시·빈폴더 실제 삭제
  python cleanup.py ~/Desktop/iPhone_내보내기 --apply

  # Android 기기 용량 리포트 (읽기 전용)
  python cleanup.py --android

주의: --apply 는 중복 파일의 사본, 캐시·썸네일, 빈 폴더만 삭제합니다.
      대용량 파일은 목록만 보여주며 절대 자동 삭제하지 않습니다.
""",
    )
    parser.add_argument("path", nargs="?", help="분석할 폴더 경로")
    parser.add_argument("--android", action="store_true",
                        help="ADB로 기기 용량 리포트만 출력 (읽기 전용)")
    parser.add_argument("--apply", action="store_true",
                        help="중복·캐시·빈폴더를 실제로 삭제 (기본은 분석만)")
    parser.add_argument("--top", type=int, default=15,
                        help="상위 목록 개수 (기본: 15)")
    parser.add_argument("--min-size", default="50MB",
                        help="대용량 파일 기준 (기본: 50MB)")
    parser.add_argument("--report", help="JSON 보고서 저장 경로 (기본: 대상폴더/cleanup_report.json)")
    args = parser.parse_args()

    if args.android:
        if args.apply:
            print("오류: --android 는 읽기 전용입니다. --apply 와 함께 쓸 수 없습니다.")
            sys.exit(1)
        sys.exit(android_report())

    if not args.path:
        parser.print_help()
        sys.exit(1)

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"오류: 폴더를 찾을 수 없습니다 — {root}")
        sys.exit(1)
    if not root.is_dir():
        print(f"오류: 폴더가 아닙니다 — {root}")
        sys.exit(1)

    try:
        min_size = parse_size(args.min_size)
    except ValueError:
        print(f"오류: --min-size 값을 해석할 수 없습니다 — {args.min_size}")
        sys.exit(1)

    if not args.apply:
        print("*** 분석 모드: 파일은 변경되지 않습니다 (삭제하려면 --apply) ***")

    print(f"스캔 중: {root}")
    data = scan(root)
    if not data["files"]:
        print("파일이 없습니다.")
        sys.exit(0)

    print(f"중복 검사 중: {len(data['files']):,}개 파일")
    dup_groups, dup_bytes = find_duplicates(data["files"])

    print_report(root, data, dup_groups, dup_bytes, args.top, min_size)

    applied = None
    if args.apply:
        applied = apply_cleanup(root, data, dup_groups)
    else:
        total_reclaim = dup_bytes + sum(s for _, s in data["cache_files"])
        if total_reclaim:
            print(f"\n  → {human(total_reclaim)} 를 회수하려면 --apply 를 추가하세요.")
        else:
            print(f"\n  → 회수할 항목이 없습니다.")

    out = Path(args.report).resolve() if args.report else root / "cleanup_report.json"
    save_report(root, data, dup_groups, dup_bytes, applied, out)


if __name__ == "__main__":
    main()
