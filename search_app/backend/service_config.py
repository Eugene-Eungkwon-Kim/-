from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DATA_ROOT = Path("D:/loan4u_avm_data")
DEFAULT_BUILDING_REGISTER_DB = Path("D:/hub_building_register/db/hub_building_register.duckdb")


def data_root() -> Path:
    return Path(os.environ.get("LOAN4U_DATA_ROOT", str(DEFAULT_DATA_ROOT)))


def building_register_db() -> str:
    return os.environ.get("LOAN4U_BUILDING_REGISTER_DB") or os.environ.get("DUCKDB_PATH") or str(DEFAULT_BUILDING_REGISTER_DB)


def service_reports_dir() -> Path:
    return Path(os.environ.get("LOAN4U_SERVICE_REPORTS_DIR", str(data_root() / "service_reports")))


def service_logs_dir() -> Path:
    return Path(os.environ.get("LOAN4U_SERVICE_LOG_DIR", str(data_root() / "service_logs")))
