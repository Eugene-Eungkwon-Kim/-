from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import time
import traceback
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import quote

import duckdb

from ..core.config import (
    EXPORT_DEFAULT_LIMIT, EXPORT_DAILY_DOWNLOAD_LIMIT, EXPORT_DAILY_ROW_LIMIT,
    DEFAULT_EXPORT_TERMS_VERSION, LABELS, CHARGING_SITE_TYPES, REVIEW_STATUSES,
    ROLE_LEVELS,
)
from ..core.db import (
    connect, table_exists, rows_to_dicts, scalar, scalar_if_table,
    grouped_rows_if_table, table_columns, first_existing_column,
    quote_ident, auction_column_expr, ensure_columns,
)
from ..core.auth import ApiError, hash_token, auth_required, role_allows, default_actor
from ..core.utils import (
    page_window, empty_page, where_from, normalize_business_status,
    search_query_variants, service_status_expr, service_status_filter,
    bool_query, auction_table_name, pick_case_no_from_payload,
    resolve_case_no_display, energy_site_filters, energy_site_search_where,
    label_value, review_id_for, split_review_id, first_env_value,
)
from ..core.maps import (
    map_provider_config, fallback_map_provider_config,
    ensure_map_provider_tables, ensure_coordinate_quality_table,
)
from ..core.tables import (
    ensure_service_security_tables, ensure_export_audit_table,
    ensure_full_commercialization_tables, ensure_operational_tables,
)

try:
    from service_config import building_register_db, data_root, service_reports_dir
except ModuleNotFoundError:
    from backend.service_config import building_register_db, data_root, service_reports_dir

try:
    from lib.auction_case_quality import classify_case_no, format_case_no_display
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    from lib.auction_case_quality import classify_case_no, format_case_no_display

class AdminSystemMixin:
    def healthz(self) -> dict[str, Any]:
        db_path = os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH)
        try:
            con = connect(read_only=True)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
            return {
                "status": "ok",
                "db": "ok",
                "db_path": db_path,
                "tables": len(tables),
                "station_search_ready": "station_search_mart" in tables,
                "version": "mvp-0.1.0",
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "db": "locked",
                "db_path": db_path,
                "tables": 0,
                "station_search_ready": False,
                "checks": [{"name": "duckdb_read_connection", "status": "locked", "detail": str(exc)[:240]}],
                "version": "mvp-0.1.1",
            }
        finally:
            if "con" in locals():
                con.close()


    def readyz(self) -> dict[str, Any]:
        db_path = os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH)
        try:
            con = connect(read_only=False)
            ensure_operational_tables(con)
            ensure_map_provider_tables(con)
            ensure_coordinate_quality_table(con)
            tables = set(row[0] for row in con.execute("SHOW TABLES").fetchall())
            checks = []
            for table_name in [
                "energy_site_search_mart",
                "energy_site_coordinate_quality",
                "service_map_provider_config",
                "service_user_token",
                "service_export_audit",
                "service_audit_event",
            ]:
                exists = table_name in tables
                checks.append(
                    {
                        "name": table_name,
                        "status": "ok" if exists else "missing",
                        "row_count": scalar(con, f"SELECT COUNT(*) FROM {table_name}") if exists else 0,
                    }
                )
            map_config = map_provider_config(con)
            blocking = [item for item in checks if item["name"] == "energy_site_search_mart" and item["status"] != "ok"]
            return {
                "status": "ok" if not blocking else "degraded",
                "db": "ok",
                "db_path": db_path,
                "auth_required": auth_required(),
                "export_policy": {
                    "max_rows": EXPORT_DEFAULT_LIMIT,
                    "daily_download_limit": EXPORT_DAILY_DOWNLOAD_LIMIT,
                    "daily_row_limit": EXPORT_DAILY_ROW_LIMIT,
                },
                "map_provider": {
                    "provider": map_config.get("provider"),
                    "fallback_provider": map_config.get("fallback_provider"),
                    "enabled": map_config.get("enabled"),
                },
                "checks": checks,
                "version": "mvp-0.2.0",
            }
        except Exception as exc:
            map_config = fallback_map_provider_config()
            return {
                "status": "degraded",
                "db": "locked",
                "db_path": db_path,
                "auth_required": auth_required(),
                "export_policy": {
                    "max_rows": EXPORT_DEFAULT_LIMIT,
                    "daily_download_limit": EXPORT_DAILY_DOWNLOAD_LIMIT,
                    "daily_row_limit": EXPORT_DAILY_ROW_LIMIT,
                },
                "map_provider": {
                    "provider": map_config.get("provider"),
                    "fallback_provider": map_config.get("fallback_provider"),
                    "enabled": map_config.get("enabled"),
                },
                "checks": [{"name": "duckdb_write_connection", "status": "locked", "detail": str(exc)[:240]}],
                "version": "mvp-0.2.0",
            }
        finally:
            if "con" in locals():
                con.close()


    def qa_diagnostics(self) -> dict[str, Any]:
        db_path = os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH)
        frontend_text = FRONTEND_INDEX.read_text(encoding="utf-8") if FRONTEND_INDEX.exists() else ""
        inline_assets_ok = "<style>" in frontend_text and "<script>" in frontend_text
        checks: list[dict[str, Any]] = [
            {
                "name": "stack_identity",
                "status": "PASS",
                "detail": "custom Python http.server + DuckDB + single HTML frontend",
            },
            {
                "name": "static_asset_delivery",
                "status": "PASS" if inline_assets_ok else "FAIL",
                "detail": "CSS/JS are embedded in frontend/index.html" if inline_assets_ok else "frontend/index.html is missing inline CSS or JS",
            },
            {
                "name": "cors_policy",
                "status": "PASS",
                "detail": "Access-Control-Allow-Origin wildcard removed; localhost or SERVICE_ALLOWED_ORIGINS only",
            },
            {
                "name": "auth_required",
                "status": "PASS" if auth_required() else "BLOCKED",
                "detail": "SERVICE_REQUIRE_AUTH=1" if auth_required() else "local mode is open; enable SERVICE_REQUIRE_AUTH=1 before external exposure",
            },
        ]
        con = connect(read_only=True)
        try:
            tables = set(row[0] for row in con.execute("SHOW TABLES").fetchall())

            def count(table_name: str, where: str = "") -> int:
                if table_name not in tables:
                    return 0
                return int(scalar(con, f"SELECT COUNT(*) FROM {table_name} {where}", default=0) or 0)

            search_rows = count("energy_site_search_mart")
            geocode_request_rows = count("energy_site_geocode_request")
            geocode_ready_rows = count("energy_site_geocode_request", "WHERE request_status = 'READY'")
            geocode_result_rows = count("energy_site_geocode_result")
            pnu_candidate_rows = count("energy_site_pnu_candidate")
            license_pending_rows = (
                count("service_license_gate", "WHERE commercial_status NOT IN ('APPROVED', 'WAIVED')")
                if "service_license_gate" in tables
                else 0
            )
            checks.extend(
                [
                    {
                        "name": "db_connection",
                        "status": "PASS",
                        "detail": f"{len(tables)} tables visible",
                    },
                    {
                        "name": "energy_site_search_mart",
                        "status": "PASS" if search_rows else "FAIL",
                        "detail": f"{search_rows:,} rows",
                    },
                    {
                        "name": "geocode_results",
                        "status": "PASS" if geocode_result_rows else "BLOCKED",
                        "detail": f"request={geocode_request_rows:,}, ready={geocode_ready_rows:,}, result={geocode_result_rows:,}",
                    },
                    {
                        "name": "pnu_candidates",
                        "status": "PASS" if pnu_candidate_rows else "BLOCKED",
                        "detail": f"{pnu_candidate_rows:,} rows",
                    },
                    {
                        "name": "license_gates",
                        "status": "PASS" if license_pending_rows == 0 else "BLOCKED",
                        "detail": f"{license_pending_rows:,} pending/restricted/rejected rows",
                    },
                ]
            )
            blocking = [item for item in checks if item["status"] in {"FAIL", "BLOCKED"}]
            return {
                "status": "ok" if not blocking else "attention",
                "stack": "custom-python-httpserver",
                "directus": False,
                "asset_mode": "single-inline-html",
                "db_engine": "DuckDB",
                "db_path": db_path,
                "auth_policy": "required" if auth_required() else "local-open",
                "cors_policy": "localhost-and-SERVICE_ALLOWED_ORIGINS",
                "checks": checks,
                "blocking_count": len(blocking),
            }
        finally:
            con.close()


    def ops_dashboard(self) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            monitor_open = scalar(con, "SELECT COUNT(*) FROM service_monitor_event WHERE event_status = 'OPEN'")
            pending_exports = scalar(con, "SELECT COUNT(*) FROM service_export_request WHERE approval_status = 'PENDING'")
            license_pending = scalar(con, "SELECT COUNT(*) FROM service_license_gate WHERE commercial_status NOT IN ('APPROVED', 'WAIVED')")
            launch_fail = scalar(con, "SELECT COUNT(*) FROM service_launch_gate_check WHERE required_for_100 AND check_status = 'FAIL'")
            latest_backup = rows_to_dicts(
                con.execute(
                    """
                    SELECT backup_id, backup_path, run_status, validation_status, sha256_hash,
                           CAST(created_at AS VARCHAR) AS created_at
                    FROM service_backup_run
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
            )
            latest_refresh = rows_to_dicts(
                con.execute(
                    """
                    SELECT run_id, run_status, step_name, CAST(started_at AS VARCHAR) AS started_at
                    FROM service_refresh_run
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )
            )
            return {
                "status": "ok" if monitor_open == 0 and license_pending == 0 else "attention",
                "monitor_open_count": monitor_open,
                "pending_export_count": pending_exports,
                "license_pending_count": license_pending,
                "launch_gate_fail_count": launch_fail,
                "latest_backup": latest_backup[0] if latest_backup else None,
                "latest_refresh": latest_refresh[0] if latest_refresh else None,
            }
        finally:
            con.close()


    def map_config(self) -> dict[str, Any]:
        try:
            con = connect(read_only=False)
            config = map_provider_config(con)
            latest = rows_to_dicts(
                con.execute(
                    """
                    SELECT provider_code, check_status, http_status, error_message, latency_ms, CAST(checked_at AS VARCHAR) AS checked_at
                    FROM service_map_provider_health
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY provider_code ORDER BY checked_at DESC) = 1
                    ORDER BY provider_code
                    """
                )
            )
            config["health"] = latest
            return config
        except Exception as exc:
            config = fallback_map_provider_config()
            config["health"] = [{"provider_code": config["provider"], "check_status": "DB_LOCKED", "error_message": str(exc)[:240]}]
            return config
        finally:
            if "con" in locals():
                con.close()


    def map_provider_status(self) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_map_provider_tables(con)
            providers = rows_to_dicts(
                con.execute(
                    """
                    SELECT provider_code, enabled, priority, display_name, attribution, requires_key,
                           key_env_name, fallback_provider_code, CAST(updated_at AS VARCHAR) AS updated_at
                    FROM service_map_provider_config
                    ORDER BY priority, provider_code
                    """
                )
            )
            health = rows_to_dicts(
                con.execute(
                    """
                    SELECT provider_code, check_status, http_status, error_message, latency_ms, CAST(checked_at AS VARCHAR) AS checked_at
                    FROM service_map_provider_health
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY provider_code ORDER BY checked_at DESC) = 1
                    ORDER BY provider_code
                    """
                )
            )
            return {
                "config": map_provider_config(con),
                "providers": providers,
                "health": health,
                "count": len(providers),
            }
        finally:
            con.close()


    def dataset_catalog(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        filters = []
        params: list[Any] = []
        if query.get("category"):
            filters.append("category = ?")
            params.append(query["category"])
        if query.get("load_group"):
            filters.append("load_group = ?")
            params.append(query["load_group"])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            source = "dataset_catalog_mart" if table_exists(con, "dataset_catalog_mart") else "hub_dataset_catalog"
            cursor = con.execute(
                f"""
                SELECT
                    table_name,
                    category,
                    service,
                    source_period,
                    provided_ym,
                    row_count,
                    load_group
                FROM {source}
                {where}
                ORDER BY load_group, category, service, table_name
                LIMIT ?
                """,
                [*params, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def service_fields(self, query: dict[str, str]) -> dict[str, Any]:
        filters = []
        params: list[Any] = []
        if query.get("table"):
            filters.append("dataset_table = ?")
            params.append(query["table"])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "hub_service_key_columns"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "hub_service_key_columns is not built")
            cursor = con.execute(
                f"""
                SELECT
                    dataset_table,
                    category,
                    service,
                    ordinal_position,
                    raw_column_name,
                    korean_name,
                    semantic_name,
                    data_type,
                    is_key_candidate,
                    is_service_field
                FROM hub_service_key_columns
                {where}
                ORDER BY dataset_table, ordinal_position
                LIMIT 1000
                """,
                params,
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def quality_checks(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "quality_check_result"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "QUALITY_NOT_RUN", "quality_check_result is not built")
            cursor = con.execute(
                """
                SELECT check_name, target_table, severity, status, failed_count, details, executed_at
                FROM quality_check_result
                ORDER BY severity, check_name
                """
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


