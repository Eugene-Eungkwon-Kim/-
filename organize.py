#!/usr/bin/env python3
"""휴대폰 파일 정리 스크립트 - 종류별/날짜별 분류, 이름 정리, 중복 제거"""

import re
import sys
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

FILE_CATEGORIES = {
    "사진": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".heic", ".heif", ".webp", ".raw", ".cr2", ".nef", ".arw"},
    "동영상": {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv", ".flv", ".webm", ".ts", ".mts"},
    "음악": {".mp3", ".flac", ".aac", ".wav", ".ogg", ".m4a", ".wma", ".opus"},
    "문서": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".hwp", ".hwpx", ".odt", ".rtf"},
    "압축파일": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "APK": {".apk", ".xapk"},
    "기타": set(),
}


def get_file_hash(path: Path, block_size: int = 65536) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()


def get_exif_date(path: Path) -> datetime | None:
    if not PILLOW_AVAILABLE:
        return None
    try:
        img = Image.open(path)
        exif_data = dict(img.getexif())
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTimeOriginal", "DateTime"):
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def get_file_date(path: Path) -> datetime:
    exif = get_exif_date(path)
    if exif:
        return exif
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime)


def get_category(path: Path) -> str:
    ext = path.suffix.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "기타"


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name


def make_new_filename(path: Path, date: datetime) -> str:
    stem = sanitize_filename(path.stem)
    timestamp = date.strftime("%Y%m%d_%H%M%S")
    if stem.startswith(timestamp[:8]):
        return f"{stem}{path.suffix.lower()}"
    return f"{timestamp}_{stem}{path.suffix.lower()}"


def collect_files(source: Path) -> list[Path]:
    files = []
    for p in source.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            files.append(p)
    return files


def organize(source: Path, dest: Path, dry_run: bool = False) -> dict:
    stats = {"이동": 0, "중복제거": 0, "오류": 0}
    seen_hashes: dict[str, Path] = {}
    files = collect_files(source)

    print(f"\n총 {len(files)}개 파일 발견\n")

    for path in files:
        try:
            file_hash = get_file_hash(path)
            if file_hash in seen_hashes:
                original = seen_hashes[file_hash]
                print(f"  [중복] {path.name}  →  {original} 와 동일, 건너뜀")
                if not dry_run:
                    path.unlink()
                stats["중복제거"] += 1
                continue
            seen_hashes[file_hash] = path

            date = get_file_date(path)
            category = get_category(path)
            month_dir = dest / category / date.strftime("%Y") / date.strftime("%m")
            new_name = make_new_filename(path, date)
            new_path = month_dir / new_name

            base_stem = new_path.stem
            counter = 1
            while new_path.exists() and get_file_hash(new_path) != file_hash:
                new_path = month_dir / f"{base_stem}_{counter}{new_path.suffix}"
                counter += 1

            print(f"  [이동] {path.relative_to(source)}  →  {new_path.relative_to(dest)}")

            if not dry_run:
                month_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(new_path))

            stats["이동"] += 1

        except Exception as e:
            print(f"  [오류] {path.name}: {e}")
            stats["오류"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="휴대폰 파일 정리: 종류별/날짜별 분류, 이름 정리, 중복 제거",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python organize.py /Volumes/Phone/DCIM ./정리된파일
  python organize.py ~/Downloads/phone_backup ./output --dry-run
""",
    )
    parser.add_argument("source", help="정리할 원본 폴더 경로")
    parser.add_argument("dest", help="정리된 파일을 저장할 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제로 이동하지 않고 미리보기만 실행")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    dest = Path(args.dest).resolve()

    if not source.exists():
        print(f"오류: 원본 폴더를 찾을 수 없습니다: {source}")
        sys.exit(1)

    if source == dest:
        print("오류: 원본과 대상 폴더가 같을 수 없습니다.")
        sys.exit(1)

    if args.dry_run:
        print("*** 미리보기 모드 (--dry-run): 실제 파일은 변경되지 않습니다 ***")

    print(f"원본: {source}")
    print(f"대상: {dest}")

    if not PILLOW_AVAILABLE:
        print("※ Pillow 미설치 — EXIF 날짜 대신 파일 수정 날짜를 사용합니다.")
        print("  정확한 날짜 정렬을 원하면: pip install Pillow\n")

    stats = organize(source, dest, dry_run=args.dry_run)

    print("\n" + "=" * 40)
    print(f"완료: 이동 {stats['이동']}개 | 중복제거 {stats['중복제거']}개 | 오류 {stats['오류']}개")
    if args.dry_run:
        print("(미리보기 모드였으므로 실제 변경 없음)")


if __name__ == "__main__":
    main()
