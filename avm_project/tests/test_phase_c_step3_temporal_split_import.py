"""phase_c_step3_retrain_models.py 가 더 이상 temporal_split 을 중복
정의하지 않고 scripts/temporal_split.py 의 것을 그대로 쓰는지 검증한다
(DEV-3 정리 작업 — 임포트만 교체, 동작 변경 없음이 기준).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_uses_the_same_function_object_as_temporal_split_module():
    import phase_c_step3_retrain_models as step3
    from temporal_split import temporal_split

    assert step3.temporal_split is temporal_split


def test_split_behaves_the_same_as_before():
    import phase_c_step3_retrain_models as step3

    df = pd.DataFrame({"t": range(10), "v": range(10)})

    train, val, test = step3.temporal_split(df, "t")

    assert len(train) == 7 and len(val) == 1 and len(test) == 2
    assert list(train["t"]) == list(range(7))
