#!/usr/bin/env python3
"""모바일 기기 데이터 마이그레이션 — Android(ADB) / 로컬 폴더 지원"""

import os
import re
import sys
import json
import shutil
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

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
]


# ── 유틸리티 ────────────────────────────────────────────────────────────────

def log(level: str, msg: str):
    icons = {"INFO": "  ", "MOVE": "  [이동]", "SKIP": "  [중복]",
             "WARN": "  [경고]", "ERR": "  [오류]", "OK": "  [완료]"}
    print(f"{icons.get(level, '  ')}{msg}")


def get_hash(path: Path, block=65536) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def get_exif_date(path: Path) -> datetime | None:
    if not PILLOW_AVAILABLE:
        return None
    try:
        from PIL.ExifTags import TAGS
        img = Image.open(path)
        exif = img._getexif()
        if not exif:
            return None
        for tag_id, val in exif.items():
            if TAGS.get(tag_id) in ("DateTimeOriginal", "DateTime"):
                return datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def get_date(path: Path) -> datetime:
    d = get_exif_date(path)
    return d if d else datetime.fromtimestamp(path.stat().st_mtime)


def get_category(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "기타"


def safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    return re.sub(r"_+", "_", name)


def new_filename(path: Path, date: datetime) -> str:
    ts = date.strftime("%Y%m%d_%H%M%S")
    stem = safe_name(path.stem)
    if stem.startswith(ts[:8]):
        return f"{stem}{path.suffix.lower()}"
    return f"{ts}_{stem}{path.suffix.lower()}"


# ── ADB ─────────────────────────────────────────────────────────────────────

def adb(*args) -> tuple[int, str]:
    try:
        r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return -1, "adb 명령을 찾을 수 없습니다. Android SDK를 설치하세요."
    except subprocess.TimeoutExpired:
        return -1, "ADB 명령 시간 초과"


def check_device() -> bool:
    code, out = adb("devices")
    if code != 0:
        print(f"ADB 오류: {out}")
        return False
    lines = [l for l in out.splitlines()[1:] if l.strip() and "device" in l]
    if not lines:
        print("연결된 Android 기기가 없습니다.")
        print("  1. USB 디버깅을 활성화하세요 (설정 → 개발자 옵션)")
        print("  2. USB 케이블로 기기를 연결하세요")
        print("  3. 기기에서 USB 디버깅 허용을 선택하세요")
        return False
    print(f"기기 감지: {lines[0]}")
    return True


def pull_from_android(dest: Path, dry_run: bool) -> int:
    if not check_device():
        return 0

    total = 0
    for remote_path in ANDROID_PATHS:
        code, _ = adb("shell", "ls", remote_path)
        if code != 0:
            continue
        local_raw = dest / "raw_from_device" / remote_path.lstrip("/")
        print(f"  pulling {remote_path} ...")
        if not dry_run:
            local_raw.mkdir(parents=True, exist_ok=True)
            adb("pull", remote_path, str(local_raw))
        total += 1

    return total


# ── 정리 ────────────────────────────────────────────────────────────────────

def organize(src: Path, dest: Path, dry_run: bool) -> dict:
    stats = {"이동": 0, "중복": 0, "오류": 0}
    seen: dict[str, Path] = {}

    files = [p for p in src.rglob("*") if p.is_file() and not p.name.startswith(".")]
    print(f"\n총 {len(files)}개 파일 처리 시작\n")

    for path in files:
        try:
            h = get_hash(path)
            if h in seen:
                log("SKIP", f"{path.name}  ←→  {seen[h].name} 와 동일")
                if not dry_run:
                    path.unlink()
                stats["중복"] += 1
                continue
            seen[h] = path

            date = get_date(path)
            cat  = get_category(path)
            out_dir = dest / cat / date.strftime("%Y") / date.strftime("%m")
            fname   = new_filename(path, date)
            out     = out_dir / fname

            n = 1
            while out.exists() and get_hash(out) != h:
                out = out_dir / f"{out.stem}_{n}{out.suffix}"
                n += 1

            log("MOVE", f"{path.relative_to(src)}  →  {out.relative_to(dest)}")
            if not dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(out))
            stats["이동"] += 1

        except Exception as e:
            log("ERR", f"{path.name}: {e}")
            stats["오류"] += 1

    return stats


def save_report(dest: Path, stats: dict, source_type: str):
    report = {
        "실행일시": datetime.now().isoformat(),
        "소스유형": source_type,
        "이동": stats["이동"],
        "중복제거": stats["중복"],
        "오류": stats["오류"],
        "카테고리별_파일수": {},
    }
    for cat in FILE_CATEGORIES:
        cat_dir = dest / cat
        if cat_dir.exists():
            count = sum(1 for _ in cat_dir.rglob("*") if _.is_file())
            report["카테고리별_파일수"][cat] = count

    report_path = dest / "migration_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n보고서 저장: {report_path}")


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
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
    group.add_argument("--android", action="store_true", help="ADB로 Android 기기에서 직접 가져오기")
    group.add_argument("--source", metavar="폴더", help="정리할 로컬 폴더 경로")

    parser.add_argument("dest", help="결과물을 저장할 폴더")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 모드 (실제 변경 없음)")

    args = parser.parse_args()
    dest = Path(args.dest).resolve()

    if args.dry_run:
        print("*** 미리보기 모드 (--dry-run) ***\n")

    if not PILLOW_AVAILABLE:
        print("※ Pillow 미설치 → 파일 수정일 기준으로 분류합니다.")
        print("  pip install Pillow  (EXIF 촬영일 사용 시)\n")

    if args.android:
        raw_dest = dest / "raw_from_device"
        print("=== Android 기기 데이터 추출 ===")
        pulled = pull_from_android(dest, args.dry_run)
        if pulled == 0:
            sys.exit(1)
        src = raw_dest
        source_type = "Android(ADB)"
    else:
        src = Path(args.source).resolve()
        if not src.exists():
            print(f"오류: 폴더를 찾을 수 없습니다: {src}")
            sys.exit(1)
        source_type = str(src)

    print(f"\n=== 파일 정리 시작 ===")
    print(f"원본: {src}")
    print(f"대상: {dest}\n")

    stats = organize(src, dest, args.dry_run)

    if not args.dry_run:
        save_report(dest, stats, source_type)

    print("\n" + "=" * 45)
    print(f"완료: 이동 {stats['이동']}개 | 중복제거 {stats['중복']}개 | 오류 {stats['오류']}개")
    if args.dry_run:
        print("(미리보기 모드 — 실제 변경 없음)")


if __name__ == "__main__":
    main()
