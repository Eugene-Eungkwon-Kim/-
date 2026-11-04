"""scripts/leakage_audit.py 의 audit_group_overlap 검증 (DEV-3).

같은 단지/필지 키가 시간순 분할의 train/test 양쪽에 모두 나오면,
모델이 "동네를 외운" 결과일 수 있다 — 이 중복 비율을 재는 함수만
검증한다(기존 3종 검사는 이번 작업 범위 밖).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from leakage_audit import audit_group_overlap


def _df(keys: list) -> pd.DataFrame:
    return pd.DataFrame({"complex_id": keys})


class TestAuditGroupOverlap:
    def test_zero_overlap_raises_no_flag(self):
        train = _df(["A", "B", "C"])
        test = _df(["D", "E"])

        flags = audit_group_overlap(train, test, key_cols=["complex_id"])

        assert flags == []

    def test_full_overlap_flags_with_ratio_one(self):
        train = _df(["A", "B"])
        test = _df(["A", "B"])

        flags = audit_group_overlap(train, test, key_cols=["complex_id"])

        assert len(flags) == 1
        assert flags[0]["check"] == "group_overlap"
        assert flags[0]["ratio"] == 1.0

    def test_boundary_at_threshold_is_not_flagged(self):
        train = _df(["A"])
        test = _df(["A", "B", "C"])  # overlap ratio == 1/3, threshold 0.3

        flags = audit_group_overlap(train, test, key_cols=["complex_id"], threshold=1 / 3)

        assert flags == []

    def test_just_above_threshold_is_flagged(self):
        train = _df(["A"])
        test = _df(["A", "B", "C"])

        flags = audit_group_overlap(train, test, key_cols=["complex_id"], threshold=0.3)

        assert len(flags) == 1

    def test_missing_key_column_skips_without_error(self):
        train = _df(["A"])
        test = _df(["A"])

        flags = audit_group_overlap(train, test, key_cols=["no_such_column"])

        assert flags == []

    def test_empty_test_set_skips_without_error(self):
        train = _df(["A"])
        test = _df([])

        flags = audit_group_overlap(train, test, key_cols=["complex_id"])

        assert flags == []

    def test_multi_column_key(self):
        train = pd.DataFrame({"sigungu": ["강남구"], "jibun": ["1"]})
        test = pd.DataFrame({"sigungu": ["강남구", "서초구"], "jibun": ["1", "1"]})

        flags = audit_group_overlap(train, test, key_cols=["sigungu", "jibun"], threshold=0.0)

        assert len(flags) == 1
        assert flags[0]["overlap_count"] == 1
