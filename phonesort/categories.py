"""파일 분류 규칙.

일반 기기용 규칙과, Live Photo/슬로모션 같은 아이폰 고유 형식을 다루는
규칙을 따로 둔다.
"""

import re
from pathlib import Path

OTHER = "기타"
DUPLICATES = "중복"

DEFAULT_CATEGORIES: dict[str, set[str]] = {
    "사진": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".heic",
             ".heif", ".webp", ".raw", ".cr2", ".nef", ".arw", ".dng"},
    "동영상": {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv", ".flv",
              ".webm", ".ts", ".mts"},
    "음악": {".mp3", ".flac", ".aac", ".wav", ".ogg", ".m4a", ".wma", ".opus"},
    "문서": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
            ".hwp", ".hwpx", ".odt", ".rtf", ".csv"},
    "압축파일": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "APK": {".apk", ".xapk"},
    OTHER: set(),
}

IPHONE_CATEGORIES: dict[str, set[str]] = {
    "사진": {".jpg", ".jpeg", ".heic", ".heif", ".png", ".gif", ".bmp", ".tiff",
             ".webp", ".raw", ".dng"},
    "라이브포토": set(),  # HEIC + MOV 쌍으로 판별
    "동영상": {".mp4", ".m4v", ".mov", ".avi", ".mkv"},
    "슬로모션": set(),  # 파일명 패턴
    "타임랩스": set(),
    "편집본": set(),  # IMG_Exxxx (아이폰이 편집본에 쓰는 이름 규칙)
    "음악": {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"},
    "문서": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
            ".hwp", ".hwpx", ".pages", ".numbers", ".key", ".rtf", ".csv"},
    "압축파일": {".zip", ".rar", ".7z", ".tar", ".gz"},
    OTHER: set(),
}

SLO_MO_PATTERN = re.compile(r"slo.?mo|slow", re.IGNORECASE)
TIMELAPSE_PATTERN = re.compile(r"time.?lapse", re.IGNORECASE)
# IMG_E1234 는 타임랩스가 아니라 "편집본(Edited)" 이다.
EDITED_PATTERN = re.compile(r"^IMG_E\d+$", re.IGNORECASE)

LIVE_PHOTO_STILL = {".heic", ".heif", ".jpg", ".jpeg"}
LIVE_PHOTO_MOTION = {".mov"}


def by_extension(path: Path, categories: dict[str, set[str]]) -> str:
    ext = path.suffix.lower()
    for category, extensions in categories.items():
        if ext in extensions:
            return category
    return OTHER


def live_photo_keys(files: list[Path]) -> set[tuple[Path, str]]:
    """Live Photo 쌍의 키 집합.

    같은 폴더에 있는 같은 이름의 정지 이미지 + MOV 만 쌍으로 본다.
    폴더를 무시하고 이름만 맞춰보면 `100APPLE/IMG_0001.HEIC` 와 무관한
    `Download/IMG_0001.MOV` 가 한 쌍으로 잘못 묶인다.
    """
    stills = {(p.parent, p.stem) for p in files if p.suffix.lower() in LIVE_PHOTO_STILL}
    motions = {(p.parent, p.stem) for p in files if p.suffix.lower() in LIVE_PHOTO_MOTION}
    return stills & motions


def iphone_category(path: Path, live_keys: set[tuple[Path, str]]) -> str:
    """아이폰 파일 하나의 카테고리.

    Live Photo 는 정지 이미지와 MOV 를 모두 `라이브포토` 로 보내 쌍을 유지한다.
    """
    ext = path.suffix.lower()
    stem = path.stem

    if (path.parent, stem) in live_keys and ext in (LIVE_PHOTO_STILL | LIVE_PHOTO_MOTION):
        return "라이브포토"

    if ext in {".mov", ".mp4", ".m4v"}:
        if SLO_MO_PATTERN.search(stem):
            return "슬로모션"
        if TIMELAPSE_PATTERN.search(stem):
            return "타임랩스"

    if EDITED_PATTERN.match(stem):
        return "편집본"

    return by_extension(path, IPHONE_CATEGORIES)
