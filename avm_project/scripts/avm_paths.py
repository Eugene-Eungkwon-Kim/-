"""VWorld 레이어 수집기들이 공유하는 데이터 저장 경로.

layer1/2_3/8_10/11_14 수집기가 각자 동일한 SQLite DB·원장 경로를 중복
정의하고 있었고, 그마저도 특정 Windows 개발 PC의 절대경로(D:\\...)로
하드코딩되어 있어 다른 환경에서는 실행할 수 없었다.

환경변수 `AVM_DATA_PATH` 로 데이터 루트를 재정의할 수 있게 하고,
지정하지 않으면 기존 개발 환경의 경로를 기본값으로 유지해 하위 호환을
지킨다.
"""

import os
from pathlib import Path

_DEFAULT_ROOT = r"D:\loan4u_avm_data\vworld_wfs_multi_layer"

DATA_ROOT = Path(os.environ.get("AVM_DATA_PATH", _DEFAULT_ROOT))
DB_PATH = DATA_ROOT / "db" / "vworld_wfs_multi_layer.sqlite"
LEDGER_PATH = DATA_ROOT / "ledger"
