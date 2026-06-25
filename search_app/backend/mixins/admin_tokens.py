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

class AdminTokensMixin:
    def token_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=30, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_user_token")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT token_id, display_name, role_code, enabled,
                           CAST(expires_at AS VARCHAR) AS expires_at,
                           CAST(created_at AS VARCHAR) AS created_at,
                           CAST(last_used_at AS VARCHAR) AS last_used_at,
                           CAST(revoked_at AS VARCHAR) AS revoked_at,
                           created_by, revoked_by, note
                    FROM service_user_token
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def create_token(self, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        role_code = str(payload.get("role_code") or payload.get("role") or "VIEWER").upper()
        if role_code not in ROLE_LEVELS:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_ROLE", "Unsupported role_code")
        token = str(payload.get("token") or secrets.token_urlsafe(32))
        token_id = str(uuid.uuid4())
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            con.execute(
                """
                INSERT INTO service_user_token (
                    token_id, token_hash, display_name, role_code, enabled,
                    expires_at, created_by, note
                )
                VALUES (?, ?, ?, ?, TRUE, NULLIF(?, '')::TIMESTAMP, ?, ?)
                """,
                [
                    token_id,
                    hash_token(token),
                    str(payload.get("display_name") or payload.get("name") or "Service User"),
                    role_code,
                    str(payload.get("expires_at") or ""),
                    actor.get("actor_id", ""),
                    str(payload.get("note") or ""),
                ],
            )
            self.insert_audit_event(con, actor, "TOKEN_CREATE", "service_user_token", token_id, "SUCCESS", request_id, {"role_code": role_code})
        finally:
            con.close()
        return {"token_id": token_id, "role_code": role_code, "token": token}


    def update_token(self, token_id: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            row = con.execute(
                """
                SELECT display_name, role_code, enabled, CAST(expires_at AS VARCHAR), note
                FROM service_user_token
                WHERE token_id = ?
                """,
                [token_id],
            ).fetchone()
            if not row:
                raise ApiError(HTTPStatus.NOT_FOUND, "TOKEN_NOT_FOUND", "Token not found")
            role_code = str(payload.get("role_code") or row[1]).upper()
            if role_code not in ROLE_LEVELS:
                raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_ROLE", "Unsupported role_code")
            enabled = bool(payload["enabled"]) if "enabled" in payload else bool(row[2])
            expires_at = str(payload.get("expires_at") if "expires_at" in payload else (row[3] or ""))
            con.execute(
                """
                UPDATE service_user_token
                SET display_name = ?, role_code = ?, enabled = ?,
                    expires_at = NULLIF(?, '')::TIMESTAMP, note = ?
                WHERE token_id = ?
                """,
                [
                    str(payload.get("display_name") or row[0]),
                    role_code,
                    enabled,
                    expires_at,
                    str(payload.get("note") if "note" in payload else (row[4] or "")),
                    token_id,
                ],
            )
            self.insert_audit_event(con, actor, "TOKEN_UPDATE", "service_user_token", token_id, "SUCCESS", request_id, {"role_code": role_code, "enabled": enabled})
            return {"token_id": token_id, "role_code": role_code, "enabled": enabled}
        finally:
            con.close()


    def rotate_token(self, token_id: str, actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            row = con.execute("SELECT role_code FROM service_user_token WHERE token_id = ?", [token_id]).fetchone()
            if not row:
                raise ApiError(HTTPStatus.NOT_FOUND, "TOKEN_NOT_FOUND", "Token not found")
            con.execute(
                """
                UPDATE service_user_token
                SET token_hash = ?, enabled = TRUE, last_rotated_at = CURRENT_TIMESTAMP,
                    revoked_at = NULL, revoked_by = NULL
                WHERE token_id = ?
                """,
                [hash_token(token), token_id],
            )
            self.insert_audit_event(con, actor, "TOKEN_ROTATE", "service_user_token", token_id, "SUCCESS", request_id)
            return {"token_id": token_id, "role_code": str(row[0]), "token": token}
        finally:
            con.close()


    def revoke_token(self, token_id: str, actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_service_security_tables(con)
            exists = scalar(con, "SELECT COUNT(*) FROM service_user_token WHERE token_id = ?", [token_id], 0)
            if not exists:
                raise ApiError(HTTPStatus.NOT_FOUND, "TOKEN_NOT_FOUND", "Token not found")
            con.execute(
                """
                UPDATE service_user_token
                SET enabled = FALSE, revoked_at = CURRENT_TIMESTAMP, revoked_by = ?
                WHERE token_id = ?
                """,
                [actor.get("actor_id", ""), token_id],
            )
            self.insert_audit_event(con, actor, "TOKEN_REVOKE", "service_user_token", token_id, "SUCCESS", request_id)
            return {"token_id": token_id, "enabled": False}
        finally:
            con.close()


