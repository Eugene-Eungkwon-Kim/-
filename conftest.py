"""테스트가 저장소 루트의 모듈과 tests/helpers.py 를 모두 임포트할 수 있게 한다."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
for candidate in (ROOT, ROOT / "tests"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
