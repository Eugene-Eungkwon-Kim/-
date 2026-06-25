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

class AdminGeocodeMixin:
    def coordinate_uplift_candidate_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        params: list[Any] = []
        filters: list[str] = []
        if query.get("candidate_status"):
            filters.append("c.candidate_status = ?")
            params.append(query["candidate_status"])
        if query.get("site_category"):
            filters.append("m.site_category = ?")
            params.append(query["site_category"])
        if query.get("q"):
            filters.append("(m.site_name ILIKE ? OR m.address_raw ILIKE ? OR c.request_keyword ILIKE ?)")
            like = f"%{query['q']}%"
            params.extend([like, like, like])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        params.append(limit)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_coordinate_uplift_candidate"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                        c.candidate_id,
                        c.energy_site_id,
                        m.site_name,
                        m.site_category,
                        m.site_type,
                        m.address_raw,
                        m.sido,
                        m.sigungu,
                        c.candidate_rank,
                        c.candidate_status,
                        c.candidate_lat,
                        c.candidate_lon,
                        c.candidate_source,
                        c.match_method,
                        c.request_keyword,
                        c.source_provider,
                        c.confidence,
                        c.issue_message,
                        c.created_at
                    FROM energy_site_coordinate_uplift_candidate c
                    LEFT JOIN energy_site_search_mart m ON m.energy_site_id = c.energy_site_id
                    {where}
                    ORDER BY
                        CASE
                            WHEN c.candidate_status LIKE '%READY' THEN 1
                            WHEN c.candidate_status = 'GEOCODE_REQUEST_READY' THEN 2
                            WHEN c.candidate_status = 'GEOCODE_REQUIRED' THEN 3
                            ELSE 4
                        END,
                        c.candidate_rank,
                        c.energy_site_id
                    LIMIT ?
                    """,
                    params,
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT candidate_status, COUNT(*) AS count
                    FROM energy_site_coordinate_uplift_candidate
                    GROUP BY candidate_status
                    ORDER BY candidate_status
                    """
                )
            )
            return {"items": rows, "count": len(rows), "summary": summary, "source_status": "READY"}
        finally:
            con.close()


    def geocode_api_key_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("provider_code", "validation_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_geocode_api_key_preflight"):
                return {
                    "items": [],
                    "count": 0,
                    "ready_count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "API key 값은 화면/API/DB에 반환하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      preflight_id, provider_code, provider_name, api_profile,
                      address_api_url, coordinate_api_url, key_env_names,
                      key_env_used, key_configured, validation_status,
                      provider_error_code, provider_error_message,
                      probe_keyword, probe_result_rows,
                      pending_missing_coordinate_requests, coordinate_sites,
                      total_sites, accepted_channels, rejected_channels,
                      next_action, checked_at
                    FROM energy_site_geocode_api_key_preflight
                    {where}
                    ORDER BY
                      CASE validation_status
                        WHEN 'INVALID_KEY' THEN 1
                        WHEN 'KEY_NOT_CONFIGURED' THEN 2
                        WHEN 'CHECK_EXCEPTION' THEN 3
                        WHEN 'KEY_VALID' THEN 9
                        ELSE 5
                      END,
                      checked_at DESC
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT validation_status, COUNT(*) AS source_count,
                           SUM(pending_missing_coordinate_requests) AS pending_missing_coordinate_requests
                    FROM energy_site_geocode_api_key_preflight
                    GROUP BY validation_status
                    ORDER BY
                      CASE validation_status
                        WHEN 'INVALID_KEY' THEN 1
                        WHEN 'KEY_NOT_CONFIGURED' THEN 2
                        WHEN 'CHECK_EXCEPTION' THEN 3
                        WHEN 'KEY_VALID' THEN 9
                        ELSE 5
                      END
                    """
                )
            )
            ready_count = con.execute("SELECT COUNT(*) FROM energy_site_geocode_api_key_preflight WHERE validation_status = 'KEY_VALID'").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "ready_count": ready_count,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "API key 값은 반환하지 않습니다. env 이름, 승인 상태, 오류코드만 표시합니다.",
            }
        finally:
            con.close()


    def pnu_geocode_priority_pack_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("priority_group", "site_category", "sido"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_pnu_geocode_priority_pack"):
                return {"items": [], "count": 0, "summary": [], "p0_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      pack_id, priority_rank, priority_group, energy_site_id, site_name,
                      site_category, site_type, fuel_types, sido, sigungu,
                      address_for_search, current_pnu, current_lat, current_lon,
                      pnu_missing, coordinate_missing, building_missing, land_area_missing,
                      recommended_lookup, expected_gate_impact, operator_note, created_at
                    FROM energy_site_pnu_geocode_priority_pack
                    {where}
                    ORDER BY priority_rank
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority_group, COUNT(*) AS row_count,
                           SUM(CASE WHEN pnu_missing THEN 1 ELSE 0 END) AS pnu_missing,
                           SUM(CASE WHEN coordinate_missing THEN 1 ELSE 0 END) AS coordinate_missing,
                           SUM(CASE WHEN land_area_missing THEN 1 ELSE 0 END) AS land_area_missing,
                           SUM(CASE WHEN building_missing THEN 1 ELSE 0 END) AS building_missing
                    FROM energy_site_pnu_geocode_priority_pack
                    GROUP BY priority_group
                    ORDER BY priority_group
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN priority_group = 'P0_PNU_AND_COORDINATE_MISSING' THEN 1 ELSE 0 END)
                FROM energy_site_pnu_geocode_priority_pack
                """
            ).fetchone()
            return {"items": rows, "count": int(totals[0] or 0), "summary": summary, "p0_count": int(totals[1] or 0), "source_status": "READY"}
        finally:
            con.close()


    def pnu_geocode_queue_seed_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_pnu_geocode_priority_queue_seed"):
                return {
                    "items": [],
                    "summary": [],
                    "count": 0,
                    "source_status": "MISSING",
                    "p0_total": 0,
                    "p0_ready_request_sites": 0,
                    "pending_missing_coordinate_requests": 0,
                    "next_action": "Run scripts/seed_geocode_requests_from_pnu_priority_pack.py first.",
                }
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT run_id, provider, priority_group, candidate_rows, inserted_rows,
                           duplicate_rows, skipped_rows, dry_run, created_at, detail_json
                    FROM energy_site_pnu_geocode_priority_queue_seed
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    [limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority_group,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(inserted_rows) AS inserted_rows,
                           SUM(duplicate_rows) AS duplicate_rows,
                           SUM(skipped_rows) AS skipped_rows,
                           MAX(created_at) AS latest_created_at
                    FROM energy_site_pnu_geocode_priority_queue_seed
                    GROUP BY priority_group
                    ORDER BY priority_group
                    """
                )
            )
            p0_total = (
                con.execute(
                    """
                    SELECT COUNT(*)
                    FROM energy_site_pnu_geocode_priority_pack
                    WHERE priority_group = 'P0_PNU_AND_COORDINATE_MISSING'
                    """
                ).fetchone()[0]
                if table_exists(con, "energy_site_pnu_geocode_priority_pack")
                else 0
            )
            p0_ready = (
                con.execute(
                    """
                    SELECT COUNT(DISTINCT p.energy_site_id)
                    FROM energy_site_pnu_geocode_priority_pack p
                    JOIN energy_site_geocode_request r ON r.energy_site_id = p.energy_site_id
                    WHERE p.priority_group = 'P0_PNU_AND_COORDINATE_MISSING'
                      AND r.request_status = 'READY'
                    """
                ).fetchone()[0]
                if table_exists(con, "energy_site_pnu_geocode_priority_pack") and table_exists(con, "energy_site_geocode_request")
                else 0
            )
            pending = (
                con.execute(
                    """
                    SELECT COUNT(*)
                    FROM energy_site_geocode_request r
                    JOIN energy_site_master m ON m.energy_site_id = r.energy_site_id
                    WHERE r.request_status = 'READY'
                      AND (m.lat IS NULL OR m.lon IS NULL)
                    """
                ).fetchone()[0]
                if table_exists(con, "energy_site_geocode_request") and table_exists(con, "energy_site_master")
                else 0
            )
            return {
                "items": rows,
                "summary": summary,
                "count": len(rows),
                "source_status": "READY",
                "p0_total": int(p0_total or 0),
                "p0_ready_request_sites": int(p0_ready or 0),
                "pending_missing_coordinate_requests": int(pending or 0),
                "secret_policy": "API key, cookie, account credentials are not stored.",
                "next_action": "Set JUSO_API_KEY only in the current process, run G3 geocode API batch, then preflight/import results.",
            }
        finally:
            con.close()


    def p0_geocode_execution_monitor_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_p0_geocode_execution_summary") or not table_exists(con, "energy_site_p0_geocode_execution_monitor"):
                return {
                    "items": [],
                    "summary": None,
                    "count": 0,
                    "source_status": "MISSING",
                    "next_action": "Run scripts/build_p0_geocode_execution_monitor.py.",
                }
            latest = con.execute(
                """
                SELECT monitor_id
                FROM energy_site_p0_geocode_execution_summary
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            if not latest:
                return {"items": [], "summary": None, "count": 0, "source_status": "EMPTY"}
            monitor_id = str(latest[0])
            summary_rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT *
                    FROM energy_site_p0_geocode_execution_summary
                    WHERE monitor_id = ?
                    """,
                    [monitor_id],
                )
            )
            items = rows_to_dicts(
                con.execute(
                    """
                    SELECT stage, site_count, request_rows, ready_request_rows,
                           effective_api_call_rows, duplicate_ready_request_rows,
                           result_rows, pnu_candidate_sites, land_link_sites,
                           sample_site_ids, created_at
                    FROM energy_site_p0_geocode_execution_monitor
                    WHERE monitor_id = ?
                    ORDER BY
                      CASE stage
                        WHEN 'COORDINATE_APPLIED' THEN 1
                        WHEN 'RESULT_IMPORTED' THEN 2
                        WHEN 'SUCCESS_REQUEST' THEN 3
                        WHEN 'READY_FOR_API' THEN 4
                        WHEN 'PROVIDER_NO_RESULT' THEN 5
                        WHEN 'PROVIDER_ERROR' THEN 6
                        ELSE 9
                      END
                    LIMIT ?
                    """,
                    [monitor_id, limit],
                )
            )
            summary = summary_rows[0] if summary_rows else {}
            return {
                "items": items,
                "summary": summary,
                "count": len(items),
                "source_status": "READY",
                "monitor_id": monitor_id,
                "next_action": "If READY_FOR_API is high, run the secure P0 geocode pipeline with JUSO_API_KEY.",
            }
        finally:
            con.close()


    def geocode_intake_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("priority", "site_category", "preflight_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if table_exists(con, "energy_site_geocode_intake_preflight"):
                rows = rows_to_dicts(
                    con.execute(
                        f"""
                        SELECT
                          preflight_id, gate_id, gate_name, batch_id, batch_key,
                          priority, site_category, site_type, sido, expected_rows,
                          template_exists, input_rows, importable_rows,
                          pnu_candidate_rows, source_document_rows, rejected_rows,
                          reject_reason_counts_json, preflight_status, next_action,
                          result_template_path, dry_run_command, import_command,
                          apply_command, checked_at
                        FROM energy_site_geocode_intake_preflight
                        {where}
                        ORDER BY
                          CASE priority WHEN 'P0_OIL_COORDINATE' THEN 1 WHEN 'P0_CHARGING_COORDINATE' THEN 2 ELSE 9 END,
                          rejected_rows DESC,
                          expected_rows DESC,
                          batch_id
                        LIMIT ?
                        """,
                        [*params, limit],
                    )
                )
                summary = rows_to_dicts(
                    con.execute(
                        """
                        SELECT priority, site_category, preflight_status,
                               COUNT(*) AS batch_count,
                               SUM(input_rows) AS input_rows,
                               SUM(importable_rows) AS importable_rows,
                               SUM(rejected_rows) AS rejected_rows
                        FROM energy_site_geocode_intake_preflight
                        GROUP BY priority, site_category, preflight_status
                        ORDER BY priority, site_category, preflight_status
                        """
                    )
                )
                total = con.execute("SELECT COUNT(*) FROM energy_site_geocode_intake_preflight").fetchone()[0]
                ready = con.execute("SELECT COUNT(*) FROM energy_site_geocode_intake_preflight WHERE preflight_status = 'READY_FOR_IMPORT'").fetchone()[0]
                return {"items": rows, "count": len(rows), "total": total, "ready_count": ready, "summary": summary, "source_status": "READY"}

            if not table_exists(con, "energy_site_geocode_batch_manifest"):
                return {"items": [], "count": 0, "total": 0, "ready_count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            dynamic_filters: list[str] = []
            dynamic_params: list[Any] = []
            for key in ("priority", "site_category"):
                value = query.get(key, "").strip()
                if value:
                    dynamic_filters.append(f"{key} = ?")
                    dynamic_params.append(value)
            dynamic_where = f"WHERE {' AND '.join(dynamic_filters)}" if dynamic_filters else ""
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      batch_id AS preflight_id, 'G3_LOCATION' AS gate_id,
                      '좌표·주소' AS gate_name, batch_id, batch_key, priority,
                      site_category, site_type, sido, row_count AS expected_rows,
                      TRUE AS template_exists, row_count AS input_rows,
                      0 AS importable_rows, 0 AS pnu_candidate_rows,
                      0 AS source_document_rows, row_count AS rejected_rows,
                      '{{"preflight_not_built": ' || CAST(row_count AS VARCHAR) || '}}' AS reject_reason_counts_json,
                      'WAITING_FOR_REQUIRED_INPUT' AS preflight_status,
                      '지오코딩 결과양식에 좌표와 확인근거를 채운 뒤 preflight를 생성합니다.' AS next_action,
                      result_template_path, dry_run_command, import_command,
                      apply_command, created_at AS checked_at
                    FROM energy_site_geocode_batch_manifest
                    {dynamic_where}
                    ORDER BY
                      CASE priority WHEN 'P0_OIL_COORDINATE' THEN 1 WHEN 'P0_CHARGING_COORDINATE' THEN 2 ELSE 9 END,
                      row_count DESC,
                      batch_id
                    LIMIT ?
                    """,
                    [*dynamic_params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority, site_category, 'WAITING_FOR_REQUIRED_INPUT' AS preflight_status,
                           COUNT(*) AS batch_count,
                           SUM(row_count) AS input_rows,
                           0 AS importable_rows,
                           SUM(row_count) AS rejected_rows
                    FROM energy_site_geocode_batch_manifest
                    GROUP BY priority, site_category
                    ORDER BY priority, site_category
                    """
                )
            )
            total = sum(int(row.get("batch_count") or 0) for row in summary)
            return {"items": rows, "count": len(rows), "total": total, "ready_count": 0, "summary": summary, "source_status": "DYNAMIC_FALLBACK"}
        finally:
            con.close()


