"""파일명 정리 및 타임스탬프 부여."""

import re
from datetime import datetime
from pathlib import Path

_ILLEGAL = re.compile(r'[\\/:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")
_REPEATED_UNDERSCORE = re.compile(r"_+")

# 이미 날짜가 앞에 붙은 이름: 20240115_ 또는 20240115_143022_
ALREADY_DATED = re.compile(r"^\d{8}(_\d{6})?_")


def safe_name(name: str) -> str:
    """파일명에서 파일시스템 예약 문자와 공백을 제거한다."""
    name = _ILLEGAL.sub("_", name)
    name = _WHITESPACE.sub("_", name.strip())
    name = _REPEATED_UNDERSCORE.sub("_", name)
    return name.strip("_") or "unnamed"


def new_filename(path: Path, date: datetime) -> str:
    """`YYYYMMDD_HHMMSS_원본이름.확장자` 형식의 새 파일명을 만든다.

    이미 날짜 접두사가 있는 이름은 그대로 둔다. 정리된 폴더를 다시 정리해도
    접두사가 중첩되지 않는다(멱등).
    """
    stem = safe_name(path.stem)
    if ALREADY_DATED.match(stem):
        return f"{stem}{path.suffix.lower()}"
    return f"{date:%Y%m%d_%H%M%S}_{stem}{path.suffix.lower()}"
