"""Explicit table mappings and row-based validation for evaluation inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import pandas as pd

try:
    from .exceptions import DataValidationError
except ImportError:
    from exceptions import DataValidationError

Rule = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class Violation:
    rule: str
    column: str
    count: int
    sample_index: list[int]


@dataclass(frozen=True)
class ValidationReport:
    rows: int
    violations: list[Violation]
    invalid_positions: tuple[int, ...] = field(default_factory=tuple)

    @property
    def error_rate(self) -> float:
        return len(self.invalid_positions) / self.rows if self.rows else 0.0


@dataclass(frozen=True)
class TableSpec:
    name: str
    path: Path
    columns: dict[str, str]
    dtypes: dict[str, str] = field(default_factory=dict)


def load_manifest(path: Path) -> list[TableSpec]:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "avm.real-data.manifest.v1":
        raise DataValidationError("UNSUPPORTED_MANIFEST_SCHEMA: actual source mapping required")
    tables = manifest.get("tables")
    if not isinstance(tables, list) or not tables:
        raise DataValidationError("Manifest requires a nonempty tables array")
    specs = [_parse_table(item, path.parent) for item in tables]
    if len({spec.name for spec in specs}) != len(specs):
        raise DataValidationError("Duplicate table names")
    return specs


def _parse_table(item: dict, base: Path) -> TableSpec:
    if not isinstance(item, dict) or not all(item.get(key) for key in ("name", "path", "columns")):
        raise DataValidationError("Table requires name, path and columns")
    columns = item["columns"]
    if not isinstance(columns, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in columns.items()):
        raise DataValidationError("Column mappings must contain string names")
    if len(set(columns.values())) != len(columns):
        raise DataValidationError("Column mappings must not merge different source columns")
    target = Path(item["path"])
    if not target.is_absolute():
        target = base / target
    dtypes = item.get("dtypes", {})
    if not isinstance(dtypes, dict) or not set(dtypes).issubset(set(columns.values())):
        raise DataValidationError("dtypes must reference mapped output columns")
    if any(dtype not in {"numeric", "datetime", "string"} for dtype in dtypes.values()):
        raise DataValidationError("Supported dtypes: numeric, datetime, string")
    return TableSpec(str(item["name"]), target, columns, dtypes)


def to_model_frame(spec: TableSpec) -> pd.DataFrame:
    if spec.path.suffix.lower() != ".csv":
        raise DataValidationError("UNSUPPORTED_TABLE_FORMAT: supply a reviewed CSV export")
    frame = pd.read_csv(spec.path, dtype="string")
    missing = set(spec.columns) - set(frame.columns)
    if missing:
        raise DataValidationError(f"Missing source columns: {sorted(missing)}")
    frame = frame[list(spec.columns)].rename(columns=spec.columns)
    for column, dtype in spec.dtypes.items():
        if dtype == "numeric":
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        elif dtype == "datetime":
            frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)
    return frame


def validate_transactions(frame: pd.DataFrame, rules: Sequence[Rule]) -> ValidationReport:
    invalid = np.zeros(len(frame), dtype=bool)
    violations = []
    for rule in rules:
        mask = rule(frame)
        if not isinstance(mask, pd.Series) or not mask.index.equals(frame.index):
            raise DataValidationError("Rule mask must match the frame index")
        if not pd.api.types.is_bool_dtype(mask):
            raise DataValidationError("Rule mask must be boolean")
        positions = np.flatnonzero(mask.fillna(True).to_numpy(dtype=bool))
        invalid[positions] = True
        if len(positions):
            violations.append(Violation(rule.__name__, getattr(rule, "column", ""),
                                        len(positions), positions[:5].tolist()))
    return ValidationReport(len(frame), violations, tuple(np.flatnonzero(invalid).tolist()))


def enforce(report: ValidationReport, max_error_rate: float = 0.05) -> None:
    if not 0 <= max_error_rate <= 1:
        raise ValueError("max_error_rate must be in [0, 1]")
    if report.rows == 0 or report.error_rate > max_error_rate:
        raise DataValidationError(f"Validation rejected {len(report.invalid_positions)}/{report.rows} rows")


def _named_rule(name: str, column: str, check: Rule) -> Rule:
    check.__name__ = name
    check.column = column
    return check


def development_rules(target: str, time_col: str, key_cols: Sequence[str],
                      area_col: str | None = None, year_col: str | None = None,
                      cancellation_col: str | None = None) -> list[Rule]:
    rules = [
        _named_rule("positive_price", target, lambda df: ~np.isfinite(pd.to_numeric(df[target], errors="coerce")) | (pd.to_numeric(df[target], errors="coerce") <= 0)),
        _named_rule("valid_date", time_col, lambda df: pd.to_datetime(df[time_col], errors="coerce", utc=True).isna() | (pd.to_datetime(df[time_col], errors="coerce", utc=True).dt.normalize() > pd.Timestamp.now(tz="UTC").normalize())),
    ]
    for column in key_cols:
        rules.append(_named_rule("missing_group_key", column, lambda df, col=column: df[col].isna() | df[col].astype("string").str.strip().eq("")))
    if area_col:
        rules.append(_named_rule("area_range", area_col, lambda df: ~pd.to_numeric(df[area_col], errors="coerce").between(5, 2000)))
    if year_col:
        rules.append(_named_rule("build_year", year_col, lambda df: pd.to_numeric(df[year_col], errors="coerce").isna() | (pd.to_numeric(df[year_col], errors="coerce") > pd.to_datetime(df[time_col], errors="coerce", utc=True).dt.year)))
    if cancellation_col:
        rules.append(_named_rule("cancelled_trade", cancellation_col, lambda df: df[cancellation_col].fillna("").astype("string").str.strip().ne("")))
    return rules
