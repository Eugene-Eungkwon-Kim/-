"""scripts/real_data_eval.py 검증 (DEV-3, 합성 데이터 범위).

`run()`은 DEV-2(Manifest 로딩)가 막혀 있어 구현되지 않았다 — 여기서는
실데이터 없이도 테스트 가능한 evaluate_model/gate만 검증한다.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from real_data_eval import MAPE_TARGET, R2_TARGET, evaluate_model, gate


class _PerfectModel:
    def predict(self, X):
        return X["y_hint"].to_numpy()


class _ConstantModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value)


class TestEvaluateModel:
    def test_perfect_prediction_gives_r2_one_and_zero_error(self):
        X_test = pd.DataFrame({"y_hint": [100.0, 200.0, 300.0]})
        y_test = pd.Series([100.0, 200.0, 300.0])

        metrics = evaluate_model(_PerfectModel(), X_test, y_test)

        assert metrics["r2"] == 1.0
        assert metrics["mape"] == 0.0
        assert metrics["mae"] == 0.0

    def test_constant_prediction_has_nonzero_error(self):
        X_test = pd.DataFrame({"y_hint": [0, 0, 0]})
        y_test = pd.Series([100.0, 200.0, 300.0])

        metrics = evaluate_model(_ConstantModel(200.0), X_test, y_test)

        assert metrics["mae"] > 0
        assert metrics["mape"] > 0


class TestGate:
    def test_passing_metrics_return_no_reasons(self):
        reasons = gate({"r2": 0.90, "mape": 0.05})
        assert reasons == []

    def test_low_r2_is_a_reason(self):
        reasons = gate({"r2": 0.50, "mape": 0.05})
        assert any("R²" in r for r in reasons)

    def test_high_mape_is_a_reason(self):
        reasons = gate({"r2": 0.90, "mape": 0.20})
        assert any("MAPE" in r for r in reasons)

    def test_boundary_r2_exactly_at_target_fails(self):
        reasons = gate({"r2": R2_TARGET, "mape": 0.05})
        assert any("R²" in r for r in reasons)

    def test_boundary_mape_exactly_at_target_fails(self):
        reasons = gate({"r2": 0.90, "mape": MAPE_TARGET})
        assert any("MAPE" in r for r in reasons)

    def test_both_fail_returns_two_reasons(self):
        reasons = gate({"r2": 0.50, "mape": 0.20})
        assert len(reasons) == 2
