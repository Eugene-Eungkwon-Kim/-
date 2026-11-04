"""VWorld 레이어 수집기들이 공유하는 데이터 저장 경로.

layer1/2_3/8_10/11_14 수집기가 각자 동일한 SQLite DB·원장 경로를 중복
정의하고 있었고, 그마저도 특정 Windows 개발 PC의 절대경로(D:\\...)로
하드코딩되어 있어 다른 환경에서는 실행할 수 없었다.

환경변수 `AVM_DATA_PATH` 로 데이터 루트를 재정의할 수 있게 하고,
지정하지 않으면 기존 개발 환경의 경로를 기본값으로 유지해 하위 호환을
지킨다. `AVM_DATA_PATH`도 없으면 `data_locator`로 외장하드를 스캔해
`loan4u_avm_data` 하위의 `vworld_wfs_multi_layer` 폴더를 찾는다(DEV-1,
드라이브 문자가 세션마다 바뀌는 문제 대응) — 그마저 실패하면 기존
기본값으로 폴백한다.
"""

import os
from pathlib import Path

from data_locator import DataRootNotFoundError, resolve_data_root

_DEFAULT_ROOT = r"D:\loan4u_avm_data\vworld_wfs_multi_layer"
_VWORLD_SUBDIR = "vworld_wfs_multi_layer"


def _resolve_default_root() -> Path:
    """임포트 시점에 실행되므로 예외를 던지면 안 된다 — 실패 시 기존 기본값으로 폴백."""
    explicit = os.environ.get("AVM_DATA_PATH")
    if explicit:
        return Path(explicit)

    try:
        candidate = resolve_data_root().root / _VWORLD_SUBDIR
    except DataRootNotFoundError:
        return Path(_DEFAULT_ROOT)

    return candidate if candidate.exists() else Path(_DEFAULT_ROOT)


DATA_ROOT = _resolve_default_root()
DB_PATH = DATA_ROOT / "db" / "vworld_wfs_multi_layer.sqlite"
LEDGER_PATH = DATA_ROOT / "ledger"
