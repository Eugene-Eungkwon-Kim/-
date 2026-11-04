"""외장하드 실데이터 루트(`loan4u_avm_data`)를 드라이브 문자와 무관하게 찾는다.

같은 탐색 로직이 `avm_paths.py`·`sync_from_external_drive.py`·
`phase_c_step0_read_external_drive.py` 세 곳에 흩어져 있었고, 데이터 루트
경로도 파일마다 `D:\\...`와 `F:\\...`로 다르게 하드코딩되어 있었다(실제
드라이브 문자가 세션마다 바뀌기 때문). 이 모듈이 그 탐색을 한 곳으로
모은다 — 인자 > `AVM_DATA_ROOT` 환경변수 > 드라이브 스캔 순으로 찾고,
어느 경로가 왜 선택됐는지 `Resolution`에 남긴다.
"""

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from exceptions import DataRootNotFoundError

MARKER_DIRNAME = "loan4u_avm_data"
ENV_VAR = "AVM_DATA_ROOT"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Resolution:
    root: Path
    source: str  # "arg" | "env" | "scan"
    drive: Optional[str]  # 스캔으로 찾은 경우의 드라이브 문자(Windows), 그 외 None


def candidate_roots(explicit: Optional[str] = None) -> list[Path]:
    """스캔 대상 후보 루트 목록. 존재 여부는 호출부(`_scan`)에서 확인한다."""
    if explicit:
        return [Path(explicit)]
    if sys.platform == "win32":
        return [Path(f"{letter}:/") for letter in "DEFGHIJKLMNOPQRSTUVWXYZ"]
    roots: list[Path] = []
    for base in (Path("/Volumes"), Path("/mnt"), Path("/media")):
        if base.exists():
            roots.extend(p for p in base.iterdir() if p.is_dir())
    return roots


def is_data_root(path: Path) -> bool:
    """`loan4u_avm_data`라는 이름의 비어 있지 않은 디렉터리인지 판정한다."""
    return path.name == MARKER_DIRNAME and path.is_dir() and any(path.iterdir())


def _scan(roots: Iterable[Path]) -> list[Path]:
    found = []
    for root in roots:
        candidate = root / MARKER_DIRNAME
        if is_data_root(candidate):
            found.append(candidate)
    return found


def _pick_newest(found: list[Path]) -> Path:
    """다중 후보 중 최종 수정 시각이 가장 최신인 것을 고르고 나머지는 경고로 남긴다."""
    newest = max(found, key=lambda p: p.stat().st_mtime)
    for path in found:
        if path == newest:
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        log.warning(f"다른 사본 무시 (수정일 {mtime}): {path}")
    return newest


def _drive_letter(root: Path) -> Optional[str]:
    """스캔으로 찾은 루트가 속한 드라이브 문자. Windows 실제 경로와 테스트용

    가짜 경로(`tmp_path / "E"`) 둘 다를 지원하려면 `.drive`(Windows 전용,
    "E:")와 `.name`(그 외 플랫폼에서 디렉터리 이름) 중 있는 쪽을 쓴다.
    """
    return (root.drive.rstrip(":") or root.name) or None


def resolve_data_root(
    explicit: Optional[str] = None,
    roots: Optional[Iterable[Path]] = None,
) -> Resolution:
    """데이터 루트를 인자 > `AVM_DATA_ROOT` 환경변수 > 스캔 순으로 찾는다.

    인자나 환경변수가 주어졌는데 `loan4u_avm_data`가 아니면, 오타가 스캔
    결과에 가려지지 않도록 그 자리에서 바로 예외를 던진다.
    """
    if explicit:
        path = Path(explicit)
        if not is_data_root(path):
            raise DataRootNotFoundError(f"지정한 경로가 {MARKER_DIRNAME} 가 아닙니다: {path}")
        return Resolution(root=path, source="arg", drive=None)

    env_value = os.environ.get(ENV_VAR)
    if env_value:
        path = Path(env_value)
        if not is_data_root(path):
            raise DataRootNotFoundError(f"{ENV_VAR}={path} 가 {MARKER_DIRNAME} 가 아닙니다")
        return Resolution(root=path, source="env", drive=None)

    scan_roots = list(roots) if roots is not None else candidate_roots()
    found = _scan(scan_roots)
    if not found:
        raise DataRootNotFoundError(
            f"{MARKER_DIRNAME} 를 찾지 못했습니다. 시도한 경로: {scan_roots}"
        )
    chosen = found[0] if len(found) == 1 else _pick_newest(found)
    return Resolution(root=chosen, source="scan", drive=_drive_letter(chosen.parent))
