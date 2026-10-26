"""Offline evaluation with explicit features, temporal splits and leakage gates."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.tree import DecisionTreeRegressor

try:
    from .data_locator import resolve_data_root
    from .exceptions import DataValidationError
    from .leakage_audit import audit_correlations, audit_feature_dependence, audit_group_overlap, audit_split_gap
    from .prediction_metrics import relative_errors_pct
    from .real_data_contract import development_rules, enforce, load_manifest, to_model_frame, validate_transactions
    from .temporal_split import temporal_split
except ImportError:
    from data_locator import resolve_data_root
    from exceptions import DataValidationError
    from leakage_audit import audit_correlations, audit_feature_dependence, audit_group_overlap, audit_split_gap
    from prediction_metrics import relative_errors_pct
    from real_data_contract import development_rules, enforce, load_manifest, to_model_frame, validate_transactions
    from temporal_split import temporal_split


def gate(metrics: dict[str, float]) -> list[str]:
    reasons = []
    if not math.isfinite(metrics.get("r2", float("nan"))) or metrics["r2"] <= 0.84:
        reasons.append("r2_must_exceed_0.84")
    if not math.isfinite(metrics.get("mape", float("nan"))) or metrics["mape"] >= 10.5:
        reasons.append("mape_must_be_below_10.5_percent")
    return reasons


def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    predictions = model.predict(X_test)
    error = relative_errors_pct(y_test, predictions)
    return {"r2": float(r2_score(y_test, predictions)), "mape": float(error.mean()),
            "mae": float(mean_absolute_error(y_test, predictions)),
            "discrepancy": float(error.mean()), "median_discrepancy": float(np.median(error))}


def model_registry() -> dict[str, Any]:
    from lightgbm import LGBMRegressor
    from xgboost import XGBRegressor

    models = {
        "linear": LinearRegression(),
        "decision_tree": DecisionTreeRegressor(max_depth=10, random_state=42),
        "random_forest": RandomForestRegressor(n_estimators=100, max_depth=15, n_jobs=1, random_state=42),
        "gradient_boosting": GradientBoostingRegressor(random_state=42),
        "xgboost": XGBRegressor(n_estimators=100, n_jobs=1, random_state=42),
        "lightgbm": LGBMRegressor(n_estimators=100, n_jobs=1, random_state=42, verbosity=-1),
    }
    models["voting"] = VotingRegressor([(name, clone(model)) for name, model in models.items()], n_jobs=1)
    return models


def _partition(frame: pd.DataFrame, time_col: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, val, test = temporal_split(frame, time_col)
    if min(len(train), len(val), len(test)) < 2:
        raise DataValidationError("Every split needs at least two rows")
    if train[time_col].max() >= val[time_col].min() or val[time_col].max() >= test[time_col].min():
        raise DataValidationError("Temporal split crosses equal timestamps; choose reviewed date boundaries")
    return train, val, test


def _feature_frames(parts: Sequence[pd.DataFrame], features: Sequence[str]) -> list[pd.DataFrame]:
    numeric = [part[list(features)].apply(pd.to_numeric, errors="coerce") for part in parts]
    if any(np.isinf(part.to_numpy(dtype=float, na_value=np.nan)).any() for part in numeric):
        raise DataValidationError("Infinite feature values")
    if numeric[0].isna().all().any():
        raise DataValidationError("Training feature has no finite observations")
    imputer = SimpleImputer(strategy="median").fit(numeric[0])
    return [pd.DataFrame(imputer.transform(part), columns=features, index=part.index) for part in numeric]


def _leakage(parts: Sequence[pd.DataFrame], features: Sequence[str], target: str,
             time_col: str, keys: Sequence[str]) -> list[dict]:
    train, val, test = parts
    development = pd.concat([train, val], ignore_index=True)
    X = development[list(features)].apply(pd.to_numeric, errors="coerce")
    # Fit audit imputations within each CV fold rather than exposing validation values.
    if X.isna().any().any():
        raise DataValidationError("Leakage audits require complete development features")
    if len(X.columns) < 2 or len(X) < 10:
        raise DataValidationError("Leakage audits need two features and ten development rows")
    with contextlib.redirect_stdout(io.StringIO()):
        flags = audit_correlations(development[[*features, target]], target)
        flags += audit_feature_dependence(X, development[target])
        flags += audit_split_gap(development, X, development[target], time_col)
    for left, right, label in ((train, val, "train_val"), (train, test, "train_test"), (val, test, "val_test")):
        for flag in audit_group_overlap(left, right, keys, threshold=0.0):
            flags.append({**flag, "split": label})
    return flags


def evaluate_frame(frame: pd.DataFrame, target: str, time_col: str, key_cols: Sequence[str],
                   features: Sequence[str], models: dict[str, Any] | None = None) -> dict[str, Any]:
    excluded = {target, time_col, *key_cols}
    if not features or excluded.intersection(features) or len(set(features)) != len(features):
        raise DataValidationError("Features must be explicit, unique and exclude target, time and group keys")
    required = {target, time_col, *key_cols, *features}
    if required - set(frame.columns):
        raise DataValidationError(f"Missing columns: {sorted(required - set(frame.columns))}")
    frame = frame.copy().reset_index(drop=True)
    frame[target] = pd.to_numeric(frame[target], errors="coerce")
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce", utc=True)
    validation = validate_transactions(frame, development_rules(target, time_col, key_cols))
    enforce(validation)
    frame = frame.drop(index=list(validation.invalid_positions)).reset_index(drop=True)
    parts = _partition(frame, time_col)
    flags = _leakage(parts, features, target, time_col, key_cols)
    report = {"data": {"rows": len(frame), "date_range": [str(frame[time_col].min()), str(frame[time_col].max())]},
              "validation": asdict(validation), "rules_source": "DEVELOPMENT_DEFAULTS_NOT_RUNBOOK",
              "leakage": {"flags": flags}, "models": {}, "operational_validation": False}
    if flags:
        report["gate"] = {"passed": False, "reasons": ["LEAKAGE_SUSPECTED"], "test_opened": False}
        return report
    X_train, X_val, X_test = _feature_frames(parts, features)
    scores = {}
    for name, model in (model_registry() if models is None else models).items():
        fitted = clone(model).fit(X_train, parts[0][target])
        scores[name] = {"validation": evaluate_model(fitted, X_val, parts[1][target]),
                        "test": evaluate_model(fitted, X_test, parts[2][target])}
        scores[name]["gate_reasons"] = gate(scores[name]["test"])
    report["models"] = scores
    report["gate"] = {"passed": bool(scores) and all(not value["gate_reasons"] for value in scores.values()),
                      "reasons": [name for name, value in scores.items() if value["gate_reasons"]], "test_opened": True}
    return report


def run(data_root: Path, target: str, time_col: str, key_cols: Sequence[str], *,
        manifest: Path, table: str, features: Sequence[str]) -> dict[str, Any]:
    # This CLI has no central operational admission provider yet.
    import sys
    if sys.platform == "win32":
        raise DataValidationError("BLOCKED_OPERATIONAL_ADMISSION_REQUIRED: real-data execution not connected")
    root = resolve_data_root(str(data_root)).root.resolve()
    specs = [spec for spec in load_manifest(manifest) if spec.name == table]
    if len(specs) != 1 or not specs[0].path.resolve().is_relative_to(root):
        raise DataValidationError("Requested table must exist in the manifest and remain under the data root")
    return evaluate_frame(to_model_frame(specs[0]), target, time_col, key_cols, features)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--time-col", required=True)
    parser.add_argument("--key-cols", nargs="+", required=True)
    parser.add_argument("--features", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(Path(args.data_root), args.target, args.time_col, args.key_cols,
                     manifest=args.manifest, table=args.table, features=args.features)
    except DataValidationError as exc:
        print(str(exc))
        return 75
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return 0 if report["gate"]["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
