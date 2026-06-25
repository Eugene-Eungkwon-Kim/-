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

class AdminGatesMixin:
    def license_gate_items(self, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, source_name, source_type, commercial_status,
                           evidence_path, reviewer, CAST(reviewed_at AS VARCHAR) AS reviewed_at,
                           note, CAST(updated_at AS VARCHAR) AS updated_at
                    FROM service_license_gate
                    ORDER BY
                        CASE commercial_status WHEN 'REJECTED' THEN 1 WHEN 'RESTRICTED' THEN 2 WHEN 'PENDING' THEN 3 ELSE 4 END,
                        source_type, source_name
                    """
                )
            )
            return {
                "items": rows,
                "count": len(rows),
                "approved": all(item.get("commercial_status") in {"APPROVED", "WAIVED"} for item in rows),
            }
        finally:
            con.close()


    def update_license_gate(self, gate_id: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        status = str(payload.get("commercial_status") or "").upper()
        if status not in {"APPROVED", "PENDING", "RESTRICTED", "REJECTED", "WAIVED"}:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_LICENSE_STATUS", "Invalid commercial_status")
        con = connect(read_only=False)
        try:
            ensure_full_commercialization_tables(con)
            exists = con.execute(
                "SELECT gate_id FROM service_license_gate WHERE gate_id = ?",
                [gate_id],
            ).fetchone()
            if not exists:
                raise ApiError(HTTPStatus.NOT_FOUND, "LICENSE_GATE_NOT_FOUND", "License gate not found")
            con.execute(
                """
                UPDATE service_license_gate
                SET commercial_status = ?, evidence_path = COALESCE(NULLIF(?, ''), evidence_path),
                    reviewer = ?, reviewed_at = CURRENT_TIMESTAMP,
                    note = COALESCE(NULLIF(?, ''), note), updated_at = CURRENT_TIMESTAMP
                WHERE gate_id = ?
                """,
                [status, str(payload.get("evidence_path") or ""), actor.get("display_name", ""), str(payload.get("note") or ""), gate_id],
            )
            self.insert_audit_event(con, actor, "LICENSE_GATE_UPDATE", "service_license_gate", gate_id, "SUCCESS", request_id, {"commercial_status": status})
            return {"gate_id": gate_id, "commercial_status": status}
        finally:
            con.close()


    def launch_gate_definitions(self, con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        now = datetime.now()
        backup_cutoff = (now - timedelta(hours=26)).strftime("%Y-%m-%d %H:%M:%S")
        restore_cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        reports_dir = DEFAULT_SERVICE_REPORTS_DIR
        desktop = sorted(reports_dir.glob("service_desktop_*.png")) if reports_dir.exists() else []
        mobile = sorted(reports_dir.glob("service_mobile_*.png")) if reports_dir.exists() else []
        license_blockers = scalar(
            con,
            "SELECT COUNT(*) FROM service_license_gate WHERE commercial_status NOT IN ('APPROVED', 'WAIVED')",
            default=0,
        )
        active_admin = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_user_token
            WHERE enabled AND role_code = 'ADMIN' AND revoked_at IS NULL
            """,
            default=0,
        )
        recent_backup = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_backup_run
            WHERE run_status = 'SUCCESS'
              AND validation_status = 'SUCCESS'
              AND created_at >= ?::TIMESTAMP
            """,
            [backup_cutoff],
            0,
        )
        recent_restore = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_restore_rehearsal
            WHERE run_status = 'SUCCESS'
              AND readyz_status = 'ok'
              AND created_at >= ?::TIMESTAMP
            """,
            [restore_cutoff],
            0,
        )
        open_errors = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_monitor_event
            WHERE event_status = 'OPEN' AND severity IN ('ERROR', 'CRITICAL')
            """,
            default=0,
        )
        export_terms = scalar(
            con,
            "SELECT COUNT(*) FROM service_terms_version WHERE terms_type = 'EXPORT' AND enabled",
            default=0,
        )
        csv_audit_ready = table_exists(con, "service_export_audit")
        readyz_ok = table_exists(con, "energy_site_search_mart") and table_exists(con, "energy_site_coordinate_quality")
        screenshots_ok = bool(desktop and mobile)
        checks = [
            ("LICENSE", "license_all_approved", license_blockers == 0, {"blocking_count": license_blockers}),
            ("SECURITY", "auth_required_mode_ready", auth_required(), {"auth_required": auth_required()}),
            ("SECURITY", "admin_token_exists", active_admin > 0, {"active_admin_count": active_admin}),
            ("BACKUP", "recent_backup_success", recent_backup > 0, {"since": backup_cutoff, "success_count": recent_backup}),
            ("BACKUP", "restore_rehearsal_success", recent_restore > 0, {"since": restore_cutoff, "success_count": recent_restore}),
            ("MONITOR", "monitor_no_open_error", open_errors == 0, {"open_error_count": open_errors}),
            ("TERMS", "export_terms_enabled", export_terms > 0, {"enabled_export_terms": export_terms}),
            ("OPS", "csv_audit_enabled", csv_audit_ready, {"table_exists": csv_audit_ready}),
            ("OPS", "readyz_ok", readyz_ok, {"energy_site_search_mart": table_exists(con, "energy_site_search_mart"), "energy_site_coordinate_quality": table_exists(con, "energy_site_coordinate_quality")}),
            ("OPS", "service_screenshots_exist", screenshots_ok, {"desktop_count": len(desktop), "mobile_count": len(mobile)}),
        ]
        return [
            {
                "check_id": name,
                "check_group": group,
                "check_name": name,
                "check_status": "PASS" if passed else "FAIL",
                "required_for_100": True,
                "detail_json": json.dumps(detail, ensure_ascii=False, sort_keys=True),
            }
            for group, name, passed, detail in checks
        ]


    def upsert_launch_gate_check(self, con: duckdb.DuckDBPyConnection, item: dict[str, Any], actor: dict[str, Any]) -> None:
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            """
            INSERT INTO service_launch_gate_check (
                check_id, check_group, check_name, check_status, required_for_100,
                checked_by, checked_at, detail_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?::TIMESTAMP, ?)
            ON CONFLICT(check_id) DO UPDATE SET
                check_group = excluded.check_group,
                check_name = excluded.check_name,
                check_status = excluded.check_status,
                required_for_100 = excluded.required_for_100,
                checked_by = excluded.checked_by,
                checked_at = excluded.checked_at,
                detail_json = excluded.detail_json
            """,
            [
                item["check_id"],
                item["check_group"],
                item["check_name"],
                item["check_status"],
                item["required_for_100"],
                actor.get("actor_id", ""),
                checked_at,
                item["detail_json"],
            ],
        )


    def run_launch_gate_checks(self, actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            checks = self.launch_gate_definitions(con)
            for item in checks:
                self.upsert_launch_gate_check(con, item, actor)
            pass_count = sum(1 for item in checks if item["check_status"] == "PASS")
            fail_count = len(checks) - pass_count
            self.insert_audit_event(con, actor, "LAUNCH_GATE_RUN", "service_launch_gate_check", "", "SUCCESS", request_id, {"pass_count": pass_count, "fail_count": fail_count})
            return {"items": checks, "count": len(checks), "pass_count": pass_count, "fail_count": fail_count, "launch_ready": fail_count == 0}
        finally:
            con.close()


    def launch_gate_items(self, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT check_id, check_group, check_name, check_status, required_for_100,
                           evidence_path, waiver_reason, checked_by,
                           CAST(checked_at AS VARCHAR) AS checked_at, detail_json
                    FROM service_launch_gate_check
                    ORDER BY
                        CASE check_status WHEN 'FAIL' THEN 1 WHEN 'WAIVED' THEN 2 ELSE 3 END,
                        check_group, check_name
                    """
                )
            )
            fail_count = sum(1 for item in rows if item.get("required_for_100") and item.get("check_status") == "FAIL")
            return {"items": rows, "count": len(rows), "fail_count": fail_count, "launch_ready": fail_count == 0 and bool(rows)}
        finally:
            con.close()


    def platform_completion_gate_items(self, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_platform_completion_gate"):
                return {"items": [], "count": 0, "fail_count": 0, "platform_ready": False, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, gate_group, gate_name, gate_status, required_for_100,
                           current_metric, target_metric, evidence_path, blocker_summary,
                           detail_json, checked_by, checked_at
                    FROM energy_site_platform_completion_gate
                    ORDER BY
                        CASE gate_status WHEN 'FAIL' THEN 1 WHEN 'WAIVED' THEN 2 ELSE 3 END,
                        gate_id
                    """
                )
            )
            fail_count = sum(1 for item in rows if item.get("required_for_100") and item.get("gate_status") == "FAIL")
            pass_count = sum(1 for item in rows if item.get("gate_status") == "PASS")
            return {
                "items": rows,
                "count": len(rows),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "platform_ready": fail_count == 0 and bool(rows),
                "source_status": "READY",
            }
        finally:
            con.close()


    def update_launch_gate_check(self, check_id: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        status = str(payload.get("check_status") or "").upper()
        if status not in {"PASS", "FAIL", "WAIVED"}:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_LAUNCH_GATE_STATUS", "Invalid check_status")
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            exists = con.execute(
                "SELECT check_id FROM service_launch_gate_check WHERE check_id = ?",
                [check_id],
            ).fetchone()
            if not exists:
                raise ApiError(HTTPStatus.NOT_FOUND, "LAUNCH_GATE_NOT_FOUND", "Launch gate check not found")
            con.execute(
                """
                UPDATE service_launch_gate_check
                SET check_status = ?, evidence_path = COALESCE(NULLIF(?, ''), evidence_path),
                    waiver_reason = COALESCE(NULLIF(?, ''), waiver_reason),
                    checked_by = ?, checked_at = CURRENT_TIMESTAMP
                WHERE check_id = ?
                """,
                [
                    status,
                    str(payload.get("evidence_path") or ""),
                    str(payload.get("waiver_reason") or ""),
                    actor.get("actor_id", ""),
                    check_id,
                ],
            )
            self.insert_audit_event(con, actor, "LAUNCH_GATE_UPDATE", "service_launch_gate_check", check_id, "SUCCESS", request_id, {"check_status": status})
            return {"check_id": check_id, "check_status": status}
        finally:
            con.close()


    def launch_approval_items(self, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT approval_id, approval_status, target_version, approved_by,
                           CAST(approved_at AS VARCHAR) AS approved_at,
                           go_live_window, rollback_plan_path, approval_note,
                           CAST(created_at AS VARCHAR) AS created_at
                    FROM service_launch_approval
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                )
            )
            return {"items": rows, "count": len(rows), "current": rows[0] if rows else None}
        finally:
            con.close()


    def create_launch_approval(self, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        approval_id = str(uuid.uuid4())
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            con.execute(
                """
                INSERT INTO service_launch_approval (
                    approval_id, approval_status, target_version, go_live_window,
                    rollback_plan_path, approval_note
                )
                VALUES (?, 'DRAFT', ?, ?, ?, ?)
                """,
                [
                    approval_id,
                    str(payload.get("target_version") or "commercial-1.0"),
                    str(payload.get("go_live_window") or ""),
                    str(payload.get("rollback_plan_path") or "docs/102_final_commercial_launch_approval_pack_20260603.md"),
                    str(payload.get("approval_note") or ""),
                ],
            )
            self.insert_audit_event(con, actor, "LAUNCH_APPROVAL_CREATE", "service_launch_approval", approval_id, "SUCCESS", request_id)
            return {"approval_id": approval_id, "approval_status": "DRAFT"}
        finally:
            con.close()


    def update_launch_approval(self, approval_id: str, status: str, payload: dict[str, Any], actor: dict[str, Any], request_id: str) -> dict[str, Any]:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            if status == "APPROVED":
                fail_count = scalar(con, "SELECT COUNT(*) FROM service_launch_gate_check WHERE required_for_100 AND check_status = 'FAIL'", default=0)
                if fail_count:
                    raise ApiError(HTTPStatus.CONFLICT, "LAUNCH_GATE_FAILED", "Launch approval cannot be approved while required gates fail", {"fail_count": fail_count})
            exists = con.execute(
                "SELECT approval_id FROM service_launch_approval WHERE approval_id = ?",
                [approval_id],
            ).fetchone()
            if not exists:
                raise ApiError(HTTPStatus.NOT_FOUND, "LAUNCH_APPROVAL_NOT_FOUND", "Launch approval not found")
            con.execute(
                """
                UPDATE service_launch_approval
                SET approval_status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP,
                    approval_note = COALESCE(NULLIF(?, ''), approval_note)
                WHERE approval_id = ?
                """,
                [status, actor.get("actor_id", ""), str(payload.get("approval_note") or ""), approval_id],
            )
            self.insert_audit_event(con, actor, f"LAUNCH_APPROVAL_{status}", "service_launch_approval", approval_id, "SUCCESS", request_id)
            return {"approval_id": approval_id, "approval_status": status}
        finally:
            con.close()


