#!/usr/bin/env python3
"""iPhone 데이터 정리 스크립트 — iPhone 13 Pro 최적화"""

import re
import sys
import json
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# iPhone 파일 카테고리
FILE_CATEGORIES = {
    "사진":     {".jpg", ".jpeg", ".heic", ".heif", ".png", ".gif", ".bmp", ".tiff", ".webp", ".raw"},
    "라이브포토": set(),      # get_category()에서 HEIC+MOV 쌍으로 판별
    "동영상":   {".mp4", ".m4v", ".mov", ".avi", ".mkv"},
    "슬로모션":  set(),      # 파일명 패턴으로 구분
    "타임랩스":  set(),
    "음악":     {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"},
    "문서":     {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                ".txt", ".hwp", ".hwpx", ".pages", ".numbers", ".key", ".rtf", ".csv"},
    "압축파일":  {".zip", ".rar", ".7z", ".tar", ".gz"},
    "기타":     set(),
}

SLO_MO_PATTERN    = re.compile(r"slo.?mo|slow", re.IGNORECASE)
TIMELAPSE_PATTERN = re.compile(r"time.?lapse|IMG_E\d+", re.IGNORECASE)


def log(icon: str, msg: str):
    print(f"  {icon} {msg}")


def get_hash(path: Path, block: int = 65536) -> str:
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
        exif = dict(img.getexif())
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


def get_category(path: Path, live_photo_stems: set) -> str:
    ext  = path.suffix.lower()
    stem = path.stem

    if ext == ".mov":
        if stem in live_photo_stems:
            return "라이브포토"
        if SLO_MO_PATTERN.search(stem):
            return "슬로모션"
        if TIMELAPSE_PATTERN.search(stem):
            return "타임랩스"
        return "동영상"

    if SLO_MO_PATTERN.search(stem) and ext in {".mp4", ".m4v"}:
        return "슬로모션"
    if TIMELAPSE_PATTERN.search(stem) and ext in {".mp4", ".m4v"}:
        return "타임랩스"

    for cat, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "기타"


def safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    return re.sub(r"_+", "_", name)


def new_filename(path: Path, date: datetime) -> str:
    ts   = date.strftime("%Y%m%d_%H%M%S")
    stem = safe_name(path.stem)
    if stem.upper().startswith("IMG_") or stem.upper().startswith("VID_"):
        return f"{ts}_{stem}{path.suffix.lower()}"
    if stem.startswith(ts[:8]):
        return f"{stem}{path.suffix.lower()}"
    return f"{ts}_{stem}{path.suffix.lower()}"


def find_live_photo_stems(files: list[Path]) -> set:
    """HEIC 파일과 같은 이름의 MOV → Live Photo 스템 집합"""
    heic_stems = {p.stem for p in files if p.suffix.lower() in {".heic", ".heif"}}
    mov_stems  = {p.stem for p in files if p.suffix.lower() == ".mov"}
    return heic_stems & mov_stems


def organize(src: Path, dest: Path, dry_run: bool) -> dict:
    stats = {"이동": 0, "중복": 0, "오류": 0, "카테고리": {}}
    seen: dict[str, Path] = {}

    files = [p for p in src.rglob("*") if p.is_file() and not p.name.startswith(".")]
    live_photo_stems = find_live_photo_stems(files)
    print(f"\n총 {len(files)}개 파일 | Live Photo 쌍 {len(live_photo_stems)}개 감지\n")

    for path in files:
        try:
            h = get_hash(path)
            if h in seen:
                log("🔁", f"[중복] {path.name}  ←→  {seen[h].name}")
                if not dry_run:
                    path.unlink()
                stats["중복"] += 1
                continue
            seen[h] = path

            date     = get_date(path)
            category = get_category(path, live_photo_stems)
            out_dir  = dest / category / date.strftime("%Y") / date.strftime("%m")
            fname    = new_filename(path, date)
            out      = out_dir / fname

            base = out.stem
            n = 1
            while out.exists() and get_hash(out) != h:
                out = out_dir / f"{base}_{n}{out.suffix}"
                n += 1

            log("→", f"[{category}] {path.name}  →  {date.strftime('%Y/%m')}/{fname}")
            if not dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(out))

            stats["이동"] += 1
            stats["카테고리"][category] = stats["카테고리"].get(category, 0) + 1

        except Exception as e:
            log("✗", f"[오류] {path.name}: {e}")
            stats["오류"] += 1

    return stats


def save_report(dest: Path, stats: dict):
    report = {
        "실행일시":     datetime.now().isoformat(),
        "기기":        "iPhone 13 Pro",
        "이동":        stats["이동"],
        "중복제거":     stats["중복"],
        "오류":        stats["오류"],
        "카테고리별":   stats["카테고리"],
    }
    path = dest / "iphone_migration_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n  보고서: {path}")


def print_summary(stats: dict, dry_run: bool):
    print("\n" + "=" * 50)
    print(f"  이동 {stats['이동']}개 | 중복제거 {stats['중복']}개 | 오류 {stats['오류']}개")
    if stats["카테고리"]:
        print("\n  카테고리별:")
        for cat, n in sorted(stats["카테고리"].items(), key=lambda x: -x[1]):
            print(f"    {cat:<10} {n}개")
    if dry_run:
        print("\n  (미리보기 모드 — 실제 변경 없음)")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="iPhone 13 Pro 데이터 정리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예:
  # 미리보기
  python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과 --dry-run

  # 실제 실행
  python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과
""",
    )
    parser.add_argument("source", help="iPhone에서 내보낸 폴더 경로")
    parser.add_argument("dest",   help="정리된 파일을 저장할 폴더")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (파일 변경 없음)")
    args = parser.parse_args()

    src  = Path(args.source).resolve()
    dest = Path(args.dest).resolve()

    if not src.exists():
        print(f"오류: 폴더를 찾을 수 없습니다 — {src}")
        sys.exit(1)
    if src == dest:
        print("오류: 원본과 대상 폴더가 같습니다.")
        sys.exit(1)

    if args.dry_run:
        print("*** 미리보기 모드 (--dry-run) ***")

    if not PILLOW_AVAILABLE:
        print("※ Pillow 미설치 → 파일 수정일 기준 분류 (pip install Pillow 권장)\n")

    print(f"원본: {src}")
    print(f"대상: {dest}")

    stats = organize(src, dest, args.dry_run)

    if not args.dry_run:
        save_report(dest, stats)

    print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
