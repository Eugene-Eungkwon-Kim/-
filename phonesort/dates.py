"""파일의 촬영 날짜 추출.

사진은 EXIF, 동영상은 QuickTime/MP4 컨테이너 메타데이터를 읽고,
둘 다 없으면 파일 수정 시각으로 물러난다.
"""

import re
import struct
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    PILLOW_AVAILABLE = False

try:  # HEIC/HEIF는 Pillow 단독으로 열 수 없다
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    HEIF_AVAILABLE = False

# EXIF 태그. DateTimeOriginal/DateTimeDigitized 는 Exif 서브 IFD 안에 있어서
# getexif() 가 돌려주는 최상위 IFD0 에서는 절대 찾을 수 없다.
EXIF_IFD_POINTER = 0x8769
DATETIME_ORIGINAL = 0x9003
DATETIME_DIGITIZED = 0x9004
DATETIME = 0x0132  # IFD0. 촬영일이 아니라 마지막 편집일에 가깝다

EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"

PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".heic", ".heif",
                  ".gif", ".bmp", ".raw", ".cr2", ".nef", ".arw", ".dng"}
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v", ".3gp", ".qt"}

QUICKTIME_EPOCH = datetime(1904, 1, 1)
_MIN_PLAUSIBLE_YEAR = 1990

_ISO_DATE = re.compile(
    r"(\d{4})[-:](\d{2})[-:](\d{2})[T ](\d{2}):(\d{2}):(\d{2})"
    r"(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?"
)


def _plausible(value: datetime | None) -> datetime | None:
    """0000:00:00 같은 빈 값이나 말도 안 되는 연도를 걸러낸다."""
    if value is None:
        return None
    if value.year < _MIN_PLAUSIBLE_YEAR:
        return None
    if value.year > datetime.now().year + 1:
        return None
    return value


def _parse_exif_datetime(raw) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", "ignore")
    raw = str(raw).strip().rstrip("\x00")
    try:
        return _plausible(datetime.strptime(raw, EXIF_DATE_FORMAT))
    except ValueError:
        return None


def exif_date(path: Path) -> datetime | None:
    """EXIF 촬영일. 촬영일 → 디지털화일 → 편집일 순으로 찾는다."""
    if not PILLOW_AVAILABLE:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            sub_ifd = exif.get_ifd(EXIF_IFD_POINTER) or {}
            for source, tag in (
                (sub_ifd, DATETIME_ORIGINAL),
                (sub_ifd, DATETIME_DIGITIZED),
                (exif, DATETIME),
            ):
                found = _parse_exif_datetime(source.get(tag))
                if found:
                    return found
    except Exception:  # 손상 파일, 미지원 포맷 등은 조용히 넘긴다
        return None
    return None


def _iter_boxes(fp, end: int):
    """ISO base media 컨테이너의 박스를 (타입, 시작, 끝)으로 훑는다."""
    while fp.tell() + 8 <= end:
        start = fp.tell()
        header = fp.read(8)
        if len(header) < 8:
            return
        size, box_type = struct.unpack(">I4s", header)
        if size == 1:
            extended = fp.read(8)
            if len(extended) < 8:
                return
            size = struct.unpack(">Q", extended)[0]
        elif size == 0:
            size = end - start
        if size < 8 or start + size > end:
            return
        yield box_type, fp.tell(), start + size
        fp.seek(start + size)


def _find_box(fp, start: int, end: int, path: tuple[bytes, ...]):
    """중첩 박스를 경로대로 따라가 (payload 시작, 끝)을 돌려준다."""
    fp.seek(start)
    for box_type, body, box_end in _iter_boxes(fp, end):
        if box_type != path[0]:
            continue
        if len(path) == 1:
            return body, box_end
        nested = _find_box(fp, body, box_end, path[1:])
        if nested:
            return nested
    return None


def _mvhd_date(fp, start: int, end: int) -> datetime | None:
    found = _find_box(fp, start, end, (b"moov", b"mvhd"))
    if not found:
        return None
    body, _ = found
    fp.seek(body)
    version_flags = fp.read(4)
    if len(version_flags) < 4:
        return None
    version = version_flags[0]
    raw = fp.read(8 if version == 1 else 4)
    if len(raw) < (8 if version == 1 else 4):
        return None
    seconds = struct.unpack(">Q" if version == 1 else ">I", raw)[0]
    if seconds == 0:
        return None
    try:
        return _plausible(QUICKTIME_EPOCH + timedelta(seconds=seconds))
    except OverflowError:
        return None


def _udta_date(fp, start: int, end: int) -> datetime | None:
    """moov/udta/©day 문자열. 있으면 로컬 시각이라 더 정확하다.

    udta 블록 전체를 정규식으로 훑으면 댓글·저작권 같은 무관한 텍스트
    필드에서 날짜처럼 보이는 문자열을 잘못 집어올 수 있다. `©day` 박스
    안쪽만 본다.
    """
    found = _find_box(fp, start, end, (b"moov", b"udta", b"\xa9day"))
    if not found:
        return None
    body, box_end = found
    fp.seek(body)
    header = fp.read(4)  # 2바이트 길이 + 2바이트 언어 코드
    if len(header) < 4:
        return None
    text_len = struct.unpack(">H", header[:2])[0]
    blob = fp.read(min(text_len, box_end - body - 4))
    match = _ISO_DATE.search(blob.decode("utf-8", "ignore"))
    if not match:
        return None
    year, month, day, hour, minute, second = (int(g) for g in match.groups()[:6])
    try:
        # 기록된 벽시계 시각을 그대로 쓴다. 오프셋은 이미 로컬 시각이라는 표시일 뿐
        # 촬영 당시 사람이 본 시각으로 분류하는 편이 폴더 정리에 맞다.
        return _plausible(datetime(year, month, day, hour, minute, second))
    except ValueError:
        return None


def video_date(path: Path) -> datetime | None:
    """QuickTime/MP4 컨테이너에서 촬영일을 읽는다.

    아이폰이 내보낸 MOV 는 udta 에 오프셋이 포함된 로컬 시각을 남기므로 이를
    우선 쓰고, 없으면 mvhd 의 생성 시각을 쓴다.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as fp:
            return _udta_date(fp, 0, size) or _mvhd_date(fp, 0, size)
    except (OSError, struct.error):
        return None


def capture_date(path: Path) -> datetime | None:
    """확장자에 맞는 방법으로 촬영일을 찾는다. 못 찾으면 None."""
    suffix = path.suffix.lower()
    if suffix in PHOTO_SUFFIXES:
        return exif_date(path)
    if suffix in VIDEO_SUFFIXES:
        return video_date(path)
    return None


def file_date(path: Path) -> datetime:
    """분류 기준 날짜. 촬영일이 없으면 파일 수정 시각을 쓴다."""
    return capture_date(path) or datetime.fromtimestamp(path.stat().st_mtime)


def missing_dependencies() -> list[str]:
    """설치하면 날짜 정확도가 올라가는 선택 의존성 목록."""
    missing = []
    if not PILLOW_AVAILABLE:
        missing.append("Pillow (사진 EXIF 촬영일)")
    if not HEIF_AVAILABLE:
        missing.append("pillow-heif (HEIC/HEIF 촬영일)")
    return missing
