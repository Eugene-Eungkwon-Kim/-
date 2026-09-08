"""파일명 정리 및 타임스탬프 부여."""

import re
from datetime import datetime
from pathlib import Path

_ILLEGAL = re.compile(r'[\\/:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")
_REPEATED_UNDERSCORE = re.compile(r"_+")

# Windows 예약 장치 이름. 확장자를 붙여도 유효하다(CON.jpg 도 막힌다).
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)}

# 이미 날짜가 앞에 붙은 이름: 20240115_ 또는 20240115_143022_
ALREADY_DATED = re.compile(r"^\d{8}(_\d{6})?_")
_DATE_PREFIX = re.compile(r"^(\d{8})(?:_(\d{6}))?_")

# 대부분의 파일시스템(ext4, APFS, NTFS)이 파일명 하나에 허용하는 상한.
# 한글은 UTF-8 로 글자당 3바이트라 85자만 넘어도 걸린다.
MAX_NAME_BYTES = 255


def _truncate(stem: str, budget: int) -> str:
    """UTF-8 바이트 예산에 맞춰 자른다. 글자 중간에서 끊기지 않는다."""
    if budget < 1:
        budget = 1
    encoded = stem.encode("utf-8")
    if len(encoded) <= budget:
        return stem
    return encoded[:budget].decode("utf-8", "ignore").rstrip("_") or "unnamed"


def safe_name(name: str) -> str:
    """파일명에서 파일시스템 예약 문자와 공백을 제거한다."""
    name = _ILLEGAL.sub("_", name)
    name = _WHITESPACE.sub("_", name.strip())
    name = _REPEATED_UNDERSCORE.sub("_", name)
    name = name.strip("_") or "unnamed"
    if name.upper() in _WINDOWS_RESERVED:
        name = f"{name}_file"
    return name


def extract_date(stem: str) -> datetime | None:
    """이름에 이미 붙은 날짜 접두사를 읽는다. 없으면 None.

    폴더 경로와 파일명이 같은 날짜를 쓰도록, 이미 정리된 파일을 재분류할 때
    파일명에 박힌 날짜를 다시 계산하지 않고 그대로 재사용하기 위함이다.
    """
    match = _DATE_PREFIX.match(stem)
    if not match:
        return None
    date_part, time_part = match.groups()
    try:
        return datetime.strptime(date_part + (time_part or "000000"), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def new_filename(path: Path, date: datetime) -> str:
    """`YYYYMMDD_HHMMSS_원본이름.확장자` 형식의 새 파일명을 만든다.

    이미 날짜 접두사가 있는 이름은 그대로 둔다. 정리된 폴더를 다시 정리해도
    접두사가 중첩되지 않는다(멱등).

    전체 길이가 파일시스템 상한을 넘으면 접두사와 확장자를 지킨 채 원본
    이름만 줄인다. 한 번 줄인 이름은 다시 줄지 않으므로 멱등성은 유지된다.
    """
    stem = safe_name(path.stem)
    suffix = path.suffix.lower()
    prefix = "" if ALREADY_DATED.match(stem) else f"{date:%Y%m%d_%H%M%S}_"
    budget = MAX_NAME_BYTES - len(prefix.encode()) - len(suffix.encode())
    return f"{prefix}{_truncate(stem, budget)}{suffix}"
