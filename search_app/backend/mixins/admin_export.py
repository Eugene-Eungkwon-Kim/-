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

class AdminExportMixin:
    def latest_export_terms(self, con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
        ensure_full_commercialization_tables(con)
        rows = rows_to_dicts(
            con.execute(
                """
                SELECT terms_version, terms_type, title, body_md,
                       CAST(effective_from AS VARCHAR) AS effective_from,
                       enabled
                FROM service_terms_version
                WHERE terms_type = 'EXPORT' AND enabled
                ORDER BY effective_from DESC, created_at DESC
                LIMIT 1
                """
            )
        )
        if not rows:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "TERMS_NOT_READY", "Export terms are not configured")
        return rows[0]


    def current_export_terms(self, actor: dict[str, Any]) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            terms = self.latest_export_terms(con)
            accepted = (
                scalar(
                    con,
                    """
                    SELECT COUNT(*)
                    FROM service_terms_acceptance
                    WHERE actor_id = ? AND terms_version = ?
                    """,
                    [actor.get("actor_id", ""), terms["terms_version"]],
                )
                > 0
            )
            return {"item": terms, "accepted": accepted}
        finally:
            con.close()


    def accepted_export_terms_version(self, con: duckdb.DuckDBPyConnection, actor: dict[str, Any]) -> str:
        terms = self.latest_export_terms(con)
        if not auth_required():
            return str(terms["terms_version"])
        accepted = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_terms_acceptance
            WHERE actor_id = ? AND terms_version = ?
            """,
            [actor.get("actor_id", ""), terms["terms_version"]],
        )
        if not accepted:
            raise ApiError(
                HTTPStatus.PRECONDITION_REQUIRED,
                "EXPORT_TERMS_REQUIRED",
                "Export terms acceptance is required",
                {"terms_version": terms["terms_version"], "title": terms["title"], "body_md": terms["body_md"]},
            )
        return str(terms["terms_version"])


    def accept_export_terms(self, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            terms = self.latest_export_terms(con)
            terms_version = str(payload.get("terms_version") or terms["terms_version"])
            con.execute(
                """
                INSERT INTO service_terms_acceptance (
                    acceptance_id, actor_id, terms_version, ip_address, user_agent
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    str(uuid.uuid4()),
                    actor.get("actor_id", ""),
                    terms_version,
                    self.client_address[0] if self.client_address else "",
                    self.headers.get("User-Agent", ""),
                ],
            )
            self.insert_audit_event(con, actor, "TERMS_ACCEPT", "service_terms_version", terms_version, "SUCCESS", request_id)
            return {"terms_version": terms_version, "accepted": True}
        finally:
            con.close()


    def terms_acceptance_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=30, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_terms_acceptance")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT acceptance_id, actor_id, terms_version, ip_address, user_agent,
                           CAST(accepted_at AS VARCHAR) AS accepted_at
                    FROM service_terms_acceptance
                    ORDER BY accepted_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def export_request_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=30, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_export_request")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT approval_id, request_id, actor_id, export_type, requested_row_count,
                           request_reason, approval_status, approved_by,
                           CAST(approved_at AS VARCHAR) AS approved_at,
                           CAST(expires_at AS VARCHAR) AS expires_at,
                           CAST(created_at AS VARCHAR) AS created_at,
                           query_json
                    FROM service_export_request
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def create_export_request(self, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
        query = {str(key): str(value) for key, value in query.items() if value is not None}
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            where, params = energy_site_search_where(query, con=con)
            requested_row_count = scalar(con, f"SELECT COUNT(*) FROM energy_site_search_mart {where}", params, 0) if table_exists(con, "energy_site_search_mart") else 0
            approval_id = str(uuid.uuid4())
            con.execute(
                """
                INSERT INTO service_export_request (
                    approval_id, request_id, actor_id, export_type, query_json,
                    requested_row_count, request_reason, approval_status
                )
                VALUES (?, ?, ?, 'energy_site_search_csv', ?, ?, ?, 'PENDING')
                """,
                [
                    approval_id,
                    request_id,
                    actor.get("actor_id", ""),
                    json.dumps(query, ensure_ascii=False, sort_keys=True),
                    requested_row_count,
                    str(payload.get("request_reason") or ""),
                ],
            )
            self.insert_audit_event(con, actor, "EXPORT_REQUEST_CREATE", "service_export_request", approval_id, "SUCCESS", request_id, {"requested_row_count": requested_row_count})
            return {"approval_id": approval_id, "approval_status": "PENDING", "requested_row_count": requested_row_count}
        finally:
            con.close()


    def approve_export_request(self, approval_id: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        expires_at = (datetime.now() + timedelta(days=int(payload.get("expires_days") or 7))).strftime("%Y-%m-%d %H:%M:%S")
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            row = con.execute(
                """
                UPDATE service_export_request
                SET approval_status = 'APPROVED', approved_by = ?, approved_at = CURRENT_TIMESTAMP,
                    expires_at = ?::TIMESTAMP
                WHERE approval_id = ?
                RETURNING approval_id
                """,
                [actor.get("actor_id", ""), expires_at, approval_id],
            ).fetchone()
            if not row:
                raise ApiError(HTTPStatus.NOT_FOUND, "EXPORT_REQUEST_NOT_FOUND", "Export request not found")
            self.insert_audit_event(con, actor, "EXPORT_REQUEST_APPROVE", "service_export_request", approval_id, "SUCCESS", request_id)
            return {"approval_id": approval_id, "approval_status": "APPROVED", "expires_at": expires_at}
        finally:
            con.close()


    def reject_export_request(self, approval_id: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            row = con.execute(
                """
                UPDATE service_export_request
                SET approval_status = 'REJECTED', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                WHERE approval_id = ?
                RETURNING approval_id
                """,
                [actor.get("actor_id", ""), approval_id],
            ).fetchone()
            if not row:
                raise ApiError(HTTPStatus.NOT_FOUND, "EXPORT_REQUEST_NOT_FOUND", "Export request not found")
            self.insert_audit_event(con, actor, "EXPORT_REQUEST_REJECT", "service_export_request", approval_id, "SUCCESS", request_id, {"reason": str(payload.get("reason") or "")})
            return {"approval_id": approval_id, "approval_status": "REJECTED"}
        finally:
            con.close()


    def validate_export_approval(self, con: duckdb.DuckDBPyConnection, actor: dict[str, Any], approval_id: str, query: dict[str, str]) -> str:
        if not approval_id:
            raise ApiError(
                HTTPStatus.PRECONDITION_REQUIRED,
                "EXPORT_APPROVAL_REQUIRED",
                "Large export approval is required",
                {"max_without_approval": EXPORT_DEFAULT_LIMIT},
            )
        row = con.execute(
            """
            SELECT approval_status, actor_id, CAST(expires_at AS VARCHAR) AS expires_at
            FROM service_export_request
            WHERE approval_id = ?
            """,
            [approval_id],
        ).fetchone()
        if not row:
            raise ApiError(HTTPStatus.FORBIDDEN, "INVALID_EXPORT_APPROVAL", "Export approval not found")
        if row[0] != "APPROVED" or (row[1] and row[1] != actor.get("actor_id", "")):
            raise ApiError(HTTPStatus.FORBIDDEN, "INVALID_EXPORT_APPROVAL", "Export approval is not usable")
        expired = scalar(con, "SELECT ?::TIMESTAMP < CURRENT_TIMESTAMP", [str(row[2] or "1970-01-01 00:00:00")], True)
        if expired:
            raise ApiError(HTTPStatus.FORBIDDEN, "EXPORT_APPROVAL_EXPIRED", "Export approval expired")
        return approval_id


    def mark_export_approval_used(self, con: duckdb.DuckDBPyConnection, approval_id: str) -> None:
        if approval_id:
            con.execute(
                """
                UPDATE service_export_request
                SET approval_status = 'USED'
                WHERE approval_id = ? AND approval_status = 'APPROVED'
                """,
                [approval_id],
            )


    def monitor_event_items(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query, default_size=30, max_size=100)
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            total = scalar(con, "SELECT COUNT(*) FROM service_monitor_event")
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT event_id, check_name, severity, event_status, message, detail_json,
                           CAST(created_at AS VARCHAR) AS created_at,
                           CAST(resolved_at AS VARCHAR) AS resolved_at
                    FROM service_monitor_event
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    [page_size, offset],
                )
            )
            return {"items": rows, "page": page, "page_size": page_size, "count": len(rows), "total": total}
        finally:
            con.close()


    def update_monitor_event(self, event_id: str, status: str, actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            row = con.execute(
                """
                UPDATE service_monitor_event
                SET event_status = ?, resolved_at = CASE WHEN ? = 'RESOLVED' THEN CURRENT_TIMESTAMP ELSE resolved_at END
                WHERE event_id = ?
                RETURNING event_id, event_status
                """,
                [status, status, event_id],
            ).fetchone()
            if not row:
                raise ApiError(HTTPStatus.NOT_FOUND, "MONITOR_EVENT_NOT_FOUND", "Monitor event not found")
            self.insert_audit_event(con, actor, f"MONITOR_{status}", "service_monitor_event", event_id, "SUCCESS", request_id)
            return {"event_id": event_id, "event_status": status}
        finally:
            con.close()


    def energy_site_export_csv(self, query: dict[str, str], request_id: str, actor: dict[str, Any]) -> None:
        requested_limit = min(max(int(query.get("limit", str(EXPORT_DEFAULT_LIMIT))), 1), EXPORT_DAILY_ROW_LIMIT)
        con = connect(read_only=False)
        try:
            if not table_exists(con, "energy_site_search_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_search_mart is not built")
            where, params = energy_site_search_where(query, con=con)
            terms_version = self.accepted_export_terms_version(con, actor)
            limit = self.export_allowed_limit(con, actor, requested_limit, query, request_id)
            approval_id = query.get("approval_id", "").strip()
            cursor = con.execute(
                f"""
                SELECT
                    energy_site_id,
                    site_name,
                    site_category,
                    site_type,
                    fuel_types,
                    business_status,
                    {service_status_expr("business_status")} AS service_status,
                    address_raw,
                    sido,
                    sigungu,
                    pnu,
                    station_site_area_m2,
                    building_review_status,
                    source_provider
                FROM energy_site_search_mart
                {where}
                ORDER BY site_category, site_name
                LIMIT ?
                """,
                [*params, limit],
            )
            items = rows_to_dicts(cursor)
            rows = [self.export_row(item) for item in items]
            watermark = (
                "반출고지: 본 파일은 허가된 사용자에게만 제공되며 재배포/재판매는 "
                f"계약과 원천 데이터 라이선스 범위 내에서만 가능합니다. request_id={request_id}"
            )
            if rows:
                rows[0]["반출고지"] = watermark
            file_manifest_id = self.insert_export_manifest(con, rows, request_id, actor, watermark)
            self.mark_export_approval_used(con, approval_id)
            self.insert_export_audit(
                con,
                "energy_site_search_csv",
                query,
                len(rows),
                request_id,
                actor,
                "SUCCESS",
                "",
                terms_version,
                approval_id,
                file_manifest_id,
            )
        finally:
            con.close()

        self.csv_response(
            "energy_sites_export.csv",
            rows,
            ["관리번호", "시설명", "구분", "시설유형", "연료", "운영상태", "주소", "시도", "시군구", "토지번호", "총토지면적_m2", "건물정보상태", "자료출처", "반출고지"],
        )


    def export_row(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "관리번호": item.get("energy_site_id") or "",
            "시설명": item.get("site_name") or "",
            "구분": label_value("site_category", item.get("site_category")),
            "시설유형": item.get("site_type") or "",
            "연료": item.get("fuel_types") or "",
            "운영상태": label_value("service_status", item.get("service_status") or item.get("business_status")),
            "주소": item.get("address_raw") or "",
            "시도": item.get("sido") or "",
            "시군구": item.get("sigungu") or "",
            "토지번호": item.get("pnu") or "",
            "총토지면적_m2": item.get("station_site_area_m2") or "",
            "건물정보상태": label_value("business_status", item.get("building_review_status")) or item.get("building_review_status") or "",
            "자료출처": label_value("provider", item.get("source_provider")),
        }


    def export_allowed_limit(
        self,
        con: duckdb.DuckDBPyConnection,
        actor: dict[str, Any],
        requested_limit: int,
        query: dict[str, str],
        request_id: str,
    ) -> int:
        ensure_export_audit_table(con)
        ensure_full_commercialization_tables(con)
        if requested_limit > EXPORT_DEFAULT_LIMIT:
            self.validate_export_approval(con, actor, query.get("approval_id", "").strip(), query)
        actor_id = actor.get("actor_id", "")
        exported_count, exported_rows = con.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(row_count), 0)
            FROM service_export_audit
            WHERE COALESCE(actor_id, '') = ?
              AND export_status = 'SUCCESS'
              AND CAST(created_at AS DATE) = CURRENT_DATE
            """,
            [actor_id],
        ).fetchone()
        exported_count = int(exported_count or 0)
        exported_rows = int(exported_rows or 0)
        if exported_count >= EXPORT_DAILY_DOWNLOAD_LIMIT:
            self.insert_export_audit(
                con,
                "energy_site_search_csv",
                query,
                0,
                request_id,
                actor,
                "BLOCKED",
                "daily_download_limit_exceeded",
            )
            raise ApiError(
                HTTPStatus.TOO_MANY_REQUESTS,
                "EXPORT_LIMIT_EXCEEDED",
                "Daily export download limit exceeded",
                {"daily_download_limit": EXPORT_DAILY_DOWNLOAD_LIMIT},
            )
        remaining_rows = EXPORT_DAILY_ROW_LIMIT - exported_rows
        if remaining_rows <= 0:
            self.insert_export_audit(
                con,
                "energy_site_search_csv",
                query,
                0,
                request_id,
                actor,
                "BLOCKED",
                "daily_row_limit_exceeded",
            )
            raise ApiError(
                HTTPStatus.TOO_MANY_REQUESTS,
                "EXPORT_LIMIT_EXCEEDED",
                "Daily export row limit exceeded",
                {"daily_row_limit": EXPORT_DAILY_ROW_LIMIT},
            )
        return min(requested_limit, remaining_rows)


    def insert_export_manifest(
        self,
        con: duckdb.DuckDBPyConnection,
        rows: list[dict[str, Any]],
        request_id: str,
        actor: dict[str, Any],
        watermark: str,
    ) -> str:
        ensure_full_commercialization_tables(con)
        file_manifest_id = str(uuid.uuid4())
        digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        con.execute(
            """
            INSERT INTO service_export_file_manifest (
                file_manifest_id, request_id, actor_id, export_type,
                row_count, sha256_hash, watermark_text
            )
            VALUES (?, ?, ?, 'energy_site_search_csv', ?, ?, ?)
            """,
            [file_manifest_id, request_id, actor.get("actor_id", ""), len(rows), digest, watermark],
        )
        return file_manifest_id


    def insert_export_audit(
        self,
        con: duckdb.DuckDBPyConnection,
        export_type: str,
        query: dict[str, str],
        row_count: int,
        request_id: str,
        actor: dict[str, Any],
        export_status: str,
        blocked_reason: str,
        terms_version: str = "",
        approval_id: str = "",
        file_manifest_id: str = "",
    ) -> None:
        ensure_export_audit_table(con)
        con.execute(
            """
            INSERT INTO service_export_audit (
                request_id, export_type, query_json, row_count, created_at,
                actor_id, actor_role, ip_address, user_agent, export_status, blocked_reason,
                terms_version, approval_id, file_manifest_id
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                request_id,
                export_type,
                json.dumps(query, ensure_ascii=False, sort_keys=True),
                row_count,
                actor.get("actor_id", ""),
                actor.get("role_code", ""),
                self.client_address[0] if self.client_address else "",
                self.headers.get("User-Agent", ""),
                export_status,
                blocked_reason,
                terms_version,
                approval_id,
                file_manifest_id,
            ],
        )
        self.insert_audit_event(
            con,
            actor,
            "EXPORT_CSV",
            "energy_site_search_mart",
            "",
            export_status,
            request_id,
            {"row_count": row_count, "blocked_reason": blocked_reason},
        )


    def log_export_audit(
        self,
        export_type: str,
        query: dict[str, str],
        row_count: int,
        request_id: str,
        actor: dict[str, Any] | None = None,
        export_status: str = "SUCCESS",
        blocked_reason: str = "",
    ) -> None:
        try:
            con = connect(read_only=False)
            try:
                self.insert_export_audit(
                    con,
                    export_type,
                    query,
                    row_count,
                    request_id,
                    actor or default_actor(),
                    export_status,
                    blocked_reason,
                )
            finally:
                con.close()
        except Exception:
            pass


