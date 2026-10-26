import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

from scripts.exceptions import DataValidationError
from scripts.leakage_audit import audit_group_overlap
from scripts.prediction_metrics import relative_errors_pct
from scripts.real_data_contract import (ValidationReport, development_rules, enforce,
                                        load_manifest, to_model_frame, validate_transactions)
from scripts import real_data_eval as evaluation


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(413)
    return pd.DataFrame({"price": rng.uniform(100, 200, 80),
                         "time": pd.date_range("2020-01-01", periods=80),
                         "key": [f"unit-{i}" for i in range(80)],
                         "a": rng.normal(size=80), "b": rng.normal(size=80)})


@pytest.mark.parametrize("overlap,threshold,flagged", [(0, .3, False), (3, .3, False), (4, .3, True), (10, .3, True)])
def test_group_overlap_boundary(overlap: int, threshold: float, flagged: bool) -> None:
    train = pd.DataFrame({"key": list(range(10))})
    test = pd.DataFrame({"key": list(range(overlap)) + list(range(10, 20 - overlap))})
    assert bool(audit_group_overlap(train, test, ["key"], threshold)) is flagged


def test_missing_group_key_is_not_a_clean_audit() -> None:
    with pytest.raises(ValueError, match="missing"):
        audit_group_overlap(pd.DataFrame({"key": [None]}), pd.DataFrame({"key": [1]}), ["key"])


def test_validation_counts_overlapping_violations_once() -> None:
    frame = pd.DataFrame({"price": [-1, 10, 20], "area": [1, 30, 50],
                          "time": ["2020-01-01"] * 3, "key": ["a", "b", "c"]}, index=[8, 8, 3])
    result = validate_transactions(frame, development_rules("price", "time", ["key"], area_col="area"))
    assert sum(item.count for item in result.violations) == 2
    assert result.error_rate == pytest.approx(1 / 3)
    assert result.invalid_positions == (0,)


@pytest.mark.parametrize("invalid,allowed", [(1, True), (2, False)])
def test_validation_five_percent_boundary(invalid: int, allowed: bool) -> None:
    report = ValidationReport(20, [], tuple(range(invalid)))
    if allowed:
        enforce(report)
    else:
        with pytest.raises(DataValidationError):
            enforce(report)


def test_empty_input_is_rejected() -> None:
    with pytest.raises(DataValidationError):
        enforce(ValidationReport(0, []))


def test_manifest_preserves_group_identifiers(tmp_path: Path) -> None:
    (tmp_path / "source.csv").write_text("amount,parcel\n100,00123\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": "avm.real-data.manifest.v1", "tables": [{
        "name": "trades", "path": "source.csv", "columns": {"amount": "price", "parcel": "key"},
        "dtypes": {"price": "numeric"}}]}), encoding="utf-8")
    result = to_model_frame(load_manifest(manifest)[0])
    assert result.loc[0, "key"] == "00123"
    assert result.loc[0, "price"] == 100


def test_unknown_manifest_does_not_invent_mapping(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"files": ["anything.db"]}', encoding="utf-8")
    with pytest.raises(DataValidationError, match="UNSUPPORTED_MANIFEST"):
        load_manifest(path)


@pytest.mark.parametrize("metrics", [{"r2": .84, "mape": 1}, {"r2": .9, "mape": 10.5},
                                     {"r2": float("nan"), "mape": 1}])
def test_metric_gate_is_strict(metrics: dict[str, float]) -> None:
    assert evaluation.gate(metrics)


def test_discrepancy_uses_existing_relative_error_definition() -> None:
    assert relative_errors_pct([100, 200], [90, 240]).tolist() == [10, 20]
    assert not evaluation.gate({"r2": .85, "mape": 10.49})


def test_group_overlap_keeps_final_test_closed() -> None:
    frame = _frame()
    frame["key"] = "same-complex"
    result = evaluation.evaluate_frame(frame, "price", "time", ["key"], ["a", "b"],
                                       {"baseline": DummyRegressor()})
    assert result["gate"] == {"passed": False, "reasons": ["LEAKAGE_SUSPECTED"], "test_opened": False}
    assert result["models"] == {}


def test_target_copy_is_flagged_before_final_test() -> None:
    frame = _frame()
    frame["a"] = frame["price"]
    result = evaluation.evaluate_frame(frame, "price", "time", ["key"], ["a", "b"],
                                       {"baseline": DummyRegressor()})
    assert any(flag["check"] == "correlation" for flag in result["leakage"]["flags"])
    assert not result["gate"]["test_opened"]


def test_equal_dates_cannot_cross_split_boundaries() -> None:
    frame = _frame()
    frame["time"] = "2020-01-01"
    with pytest.raises(DataValidationError, match="equal timestamps"):
        evaluation.evaluate_frame(frame, "price", "time", ["key"], ["a", "b"])


def test_explicit_identifiers_cannot_be_features() -> None:
    with pytest.raises(DataValidationError, match="exclude"):
        evaluation.evaluate_frame(_frame(), "price", "time", ["key"], ["key"])


def test_passing_development_audit_evaluates_without_claiming_live_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluation, "audit_correlations", lambda *_: [])
    monkeypatch.setattr(evaluation, "audit_feature_dependence", lambda *_: [])
    monkeypatch.setattr(evaluation, "audit_split_gap", lambda *_: [])
    result = evaluation.evaluate_frame(_frame(), "price", "time", ["key"], ["a", "b"],
                                       {"baseline": DummyRegressor()})
    assert result["gate"]["test_opened"]
    assert len(result["models"]) == 1
    assert result["operational_validation"] is False


def test_windows_real_data_path_stops_before_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sys
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(evaluation, "resolve_data_root", lambda *_: pytest.fail("opened primary"))
    with pytest.raises(DataValidationError, match="ADMISSION_REQUIRED"):
        evaluation.run(tmp_path, "price", "time", ["key"], manifest=tmp_path / "none", table="x", features=["a"])


def test_seven_models_synthetic_roundtrip(tmp_path: Path) -> None:
    rng = np.random.default_rng(413)
    count = 400
    frame = pd.DataFrame({"price": rng.uniform(100, 200, count),
                          "time": pd.date_range("2018-01-01", periods=count),
                          "key": [f"synthetic-{i}" for i in range(count)],
                          "a": rng.normal(size=count), "b": rng.normal(size=count)})
    frame.to_csv(tmp_path / "synthetic.csv", index=False)
    manifest = tmp_path / "synthetic-manifest.json"
    manifest.write_text(json.dumps({"schema": "avm.real-data.manifest.v1", "tables": [{
        "name": "synthetic-only", "path": "synthetic.csv", "columns": {col: col for col in frame.columns},
        "dtypes": {"price": "numeric", "a": "numeric", "b": "numeric", "time": "datetime"}}]}), encoding="utf-8")
    mapped = to_model_frame(load_manifest(manifest)[0])
    report = evaluation.evaluate_frame(mapped, "price", "time", ["key"], ["a", "b"])
    report["data_origin"] = "SYNTHETIC_TEST_ONLY"
    path = tmp_path / "synthetic-evaluation.json"
    path.write_text(json.dumps(report, allow_nan=False), encoding="utf-8")
    restored = json.loads(path.read_text(encoding="utf-8"))
    assert len(restored["models"]) == 7
    assert restored["gate"]["test_opened"]
    assert not restored["gate"]["passed"]
    assert not restored["operational_validation"]
