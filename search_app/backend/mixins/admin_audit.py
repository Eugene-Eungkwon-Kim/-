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

class AdminAuditMixin:
    def audit_event_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=30, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_audit_event")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT event_id, request_id, actor_id, actor_role, event_type, target_type,
                           target_id, event_status, detail_json, ip_address, user_agent,
                           CAST(created_at AS VARCHAR) AS created_at
                    FROM service_audit_event
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def backup_run_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=20, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_backup_run")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT backup_id, source_db_path, backup_path, file_size_bytes, run_status,
                           error_message, sha256_hash, validation_status, validation_detail_json,
                           duration_ms, CAST(maintenance_started_at AS VARCHAR) AS maintenance_started_at,
                           CAST(maintenance_finished_at AS VARCHAR) AS maintenance_finished_at,
                           CAST(created_at AS VARCHAR) AS created_at
                    FROM service_backup_run
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def export_audit_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=20, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_export_audit_table(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_export_audit")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT request_id, export_type, actor_id, actor_role, row_count,
                           export_status, blocked_reason, terms_version, approval_id,
                           file_manifest_id, query_json, ip_address, user_agent,
                           CAST(created_at AS VARCHAR) AS created_at
                    FROM service_export_audit
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def refresh_run_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=20, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_refresh_run")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT run_id, run_mode, run_status, step_name, detail_json,
                           CAST(started_at AS VARCHAR) AS started_at,
                           CAST(finished_at AS VARCHAR) AS finished_at
                    FROM service_refresh_run
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


