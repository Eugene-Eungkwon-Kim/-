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

class EnergySitesMixin:
    def energy_site_search(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_search_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_search_mart is not built")
            auction_table = auction_table_name(con)
            if bool_query(query.get("has_auction", "")) is True and not auction_table:
                return empty_page(page, page_size, auction_source_status="SOURCE_NOT_LOADED")
            where, params = energy_site_search_where(query, "m", auction_table, con=con)
            has_coordinate_quality = table_exists(con, "energy_site_coordinate_quality")
            coordinate_columns = (
                """
                    COALESCE(
                        q.coordinate_status,
                        CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN 'NO_COORDINATE' ELSE 'UNCHECKED' END
                    ) AS coordinate_status,
                    COALESCE(q.quality_score, CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN 0 ELSE 0.5 END) AS coordinate_quality_score,
                    q.issue_code AS coordinate_issue_code,
                    q.issue_message AS coordinate_issue_message,
                    CASE
                        WHEN COALESCE(q.coordinate_status, CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN 'NO_COORDINATE' ELSE 'UNCHECKED' END)
                             IN ('VALID', 'UNCHECKED', 'DUPLICATE_COORDINATE')
                        THEN TRUE
                        ELSE FALSE
                    END AS map_display_allowed
                """
                if has_coordinate_quality
                else """
                    CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN 'NO_COORDINATE' ELSE 'UNCHECKED' END AS coordinate_status,
                    CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN 0 ELSE 0.5 END AS coordinate_quality_score,
                    NULL AS coordinate_issue_code,
                    NULL AS coordinate_issue_message,
                    CASE WHEN m.lat IS NULL OR m.lon IS NULL THEN FALSE ELSE TRUE END AS map_display_allowed
                """
            )
            coordinate_join = "LEFT JOIN energy_site_coordinate_quality q ON m.energy_site_id = q.energy_site_id" if has_coordinate_quality else ""
            auction_date_expr, auction_date_col = auction_column_expr(
                con,
                auction_table,
                ["event_date", "auction_date", "sale_date", "bid_date", "award_date", "collected_at", "경매일자", "매각기일", "낙찰일자"],
            ) if auction_table else ("NULL", None)
            auction_status_expr, auction_status_col = auction_column_expr(
                con,
                auction_table,
                ["event_status", "auction_status", "sale_status", "bid_status", "result_status", "case_status", "진행상태", "낙찰상태"],
            ) if auction_table else ("NULL", None)
            auction_case_no_expr, auction_case_no_col = auction_column_expr(
                con,
                auction_table,
                ["case_no", "case_number", "auction_case_no", "court_case_no", "사건번호"],
            ) if auction_table else ("NULL", None)
            auction_provider_expr, auction_provider_col = auction_column_expr(
                con,
                auction_table,
                ["source_provider", "provider", "source", "출처", "검색처"],
            ) if auction_table else ("NULL", None)
            latest_date_expr = f"MAX({auction_date_expr}) AS latest_auction_date" if auction_date_col else "NULL AS latest_auction_date"
            if auction_status_col and auction_date_col:
                latest_status_expr = f"arg_max({auction_status_expr}, {auction_date_expr}) AS latest_auction_status"
            elif auction_status_col:
                latest_status_expr = f"MAX({auction_status_expr}) AS latest_auction_status"
            else:
                latest_status_expr = "NULL AS latest_auction_status"
            if auction_provider_col and auction_date_col:
                latest_provider_expr = f"arg_max({auction_provider_expr}, {auction_date_expr}) AS latest_auction_source_provider"
            elif auction_provider_col:
                latest_provider_expr = f"MAX({auction_provider_expr}) AS latest_auction_source_provider"
            else:
                latest_provider_expr = "NULL AS latest_auction_source_provider"
            if auction_case_no_col:
                latest_case_no_expr = f"arg_max({auction_case_no_expr}, {auction_date_expr}) AS latest_auction_case_no" if auction_date_col else f"MAX({auction_case_no_expr}) AS latest_auction_case_no"
                valid_case_count_expr = f"""
                        SUM(
                            CASE
                                WHEN regexp_matches(regexp_replace(CAST({auction_case_no_expr} AS VARCHAR), '\\s+', '', 'g'), '^\\d{{4}}(타경|타채|타기|카경|본)\\d{{1,10}}$')
                                THEN 1 ELSE 0
                            END
                        ) AS auction_valid_case_no_count
                """
                provider_ref_count_expr = f"""
                        SUM(
                            CASE
                                WHEN TRIM(CAST({auction_case_no_expr} AS VARCHAR)) <> ''
                                 AND NOT regexp_matches(regexp_replace(CAST({auction_case_no_expr} AS VARCHAR), '\\s+', '', 'g'), '^\\d{{4}}(타경|타채|타기|카경|본)\\d{{1,10}}$')
                                THEN 1 ELSE 0
                            END
                        ) AS auction_provider_reference_count
                """
            else:
                latest_case_no_expr = "NULL AS latest_auction_case_no"
                valid_case_count_expr = "0 AS auction_valid_case_no_count"
                provider_ref_count_expr = "0 AS auction_provider_reference_count"
            auction_select = (
                """
                    COALESCE(a.auction_event_count, 0) AS auction_event_count,
                    COALESCE(a.auction_valid_case_no_count, 0) AS auction_valid_case_no_count,
                    COALESCE(a.auction_provider_reference_count, 0) AS auction_provider_reference_count,
                    a.latest_auction_case_no,
                    a.latest_auction_source_provider,
                    CASE
                        WHEN COALESCE(a.auction_event_count, 0) > 0 AND COALESCE(a.auction_valid_case_no_count, 0) > 0 THEN 'HAS_HISTORY'
                        WHEN COALESCE(a.auction_event_count, 0) > 0 THEN 'AUCTION_REVIEW_REQUIRED'
                        ELSE 'NO_HISTORY'
                    END AS auction_status,
                    a.latest_auction_date,
                    a.latest_auction_status
                """
                if auction_table
                else """
                    0 AS auction_event_count,
                    0 AS auction_valid_case_no_count,
                    0 AS auction_provider_reference_count,
                    NULL AS latest_auction_case_no,
                    NULL AS latest_auction_source_provider,
                    'SOURCE_NOT_LOADED' AS auction_status,
                    NULL AS latest_auction_date,
                    NULL AS latest_auction_status
                """
            )
            auction_join = (
                f"""
                LEFT JOIN (
                    SELECT
                        energy_site_id,
                        COUNT(*) AS auction_event_count,
                        {valid_case_count_expr},
                        {provider_ref_count_expr},
                        {latest_case_no_expr},
                        {latest_provider_expr},
                        {latest_date_expr},
                        {latest_status_expr}
                    FROM {quote_ident(auction_table)}
                    GROUP BY energy_site_id
                ) a ON m.energy_site_id = a.energy_site_id
                """
                if auction_table
                else ""
            )
            total = con.execute(f"SELECT COUNT(*) FROM energy_site_search_mart m {where}", params).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT
                    m.*,
                    {service_status_expr("m.business_status")} AS service_status,
                    COALESCE(st.storage_item_count, 0) AS storage_item_count,
                    COALESCE(eq.equipment_item_count, 0) AS equipment_item_count,
                    COALESCE(fc.facility_item_count, 0) AS facility_item_count,
                    COALESCE(st.storage_item_count, 0) > 0 AS has_storage,
                    COALESCE(eq.equipment_item_count, 0) > 0 AS has_equipment,
                    COALESCE(fc.facility_item_count, 0) > 0 AS has_facility,
                    {auction_select},
                    {coordinate_columns}
                FROM energy_site_search_mart m
                {coordinate_join}
                LEFT JOIN (
                    SELECT energy_site_id, COUNT(*) AS storage_item_count
                    FROM energy_site_storage_capacity
                    GROUP BY energy_site_id
                ) st ON m.energy_site_id = st.energy_site_id
                LEFT JOIN (
                    SELECT energy_site_id, COUNT(*) AS equipment_item_count
                    FROM energy_site_equipment
                    GROUP BY energy_site_id
                ) eq ON m.energy_site_id = eq.energy_site_id
                LEFT JOIN (
                    SELECT energy_site_id, COUNT(*) AS facility_item_count
                    FROM energy_site_facility_summary
                    GROUP BY energy_site_id
                ) fc ON m.energy_site_id = fc.energy_site_id
                {auction_join}
                {where}
                ORDER BY
                    CASE
                        WHEN m.building_review_status IN ('AUTO_CONFIRMED', 'CONFIRMED')
                          OR m.facility_class IS NOT NULL
                          OR COALESCE(m.pnu, '') <> ''
                        THEN 0
                        ELSE 1
                    END,
                    CASE m.site_category WHEN 'OIL_STATION' THEN 0 ELSE 1 END,
                    m.site_name
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            for item in items:
                case_no_kind, case_no_valid, case_no_issue = classify_case_no(item.get("latest_auction_case_no"))
                item["latest_auction_case_no_display"] = resolve_case_no_display(
                    item.get("latest_auction_case_no"),
                    item.get("latest_auction_source_provider"),
                    None,
                )
                item["latest_auction_case_no_kind"] = case_no_kind
                item["latest_auction_case_no_valid"] = case_no_valid
                item["latest_auction_case_no_issue"] = case_no_issue
            return {"items": items, "page": page, "page_size": page_size, "count": len(items), "total": total}
        finally:
            con.close()


    def energy_site_coordinate_quality(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query)
        filters: list[str] = []
        params: list[Any] = []
        if query.get("coordinate_status"):
            filters.append("q.coordinate_status = ?")
            params.append(query["coordinate_status"])
        if query.get("issue_code"):
            filters.append("q.issue_code = ?")
            params.append(query["issue_code"])
        if query.get("site_category"):
            filters.append("m.site_category = ?")
            params.append(query["site_category"])
        if query.get("q"):
            filters.append("(m.site_name ILIKE ? OR m.address_raw ILIKE ?)")
            params.extend([f"%{query['q']}%", f"%{query['q']}%"])
        where = where_from(filters)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_search_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_search_mart is not built")
            if not table_exists(con, "energy_site_coordinate_quality"):
                return empty_page(page, page_size, summary=[])
            total = con.execute(
                f"""
                SELECT COUNT(*)
                FROM energy_site_coordinate_quality q
                LEFT JOIN energy_site_search_mart m ON q.energy_site_id = m.energy_site_id
                {where}
                """,
                params,
            ).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT
                    q.energy_site_id,
                    m.site_name,
                    m.site_category,
                    m.address_raw,
                    m.sido,
                    m.sigungu,
                    q.latitude,
                    q.longitude,
                    q.coordinate_status,
                    q.quality_score,
                    q.issue_code,
                    q.issue_message,
                    q.source_provider,
                    CAST(q.checked_at AS VARCHAR) AS checked_at
                FROM energy_site_coordinate_quality q
                LEFT JOIN energy_site_search_mart m ON q.energy_site_id = m.energy_site_id
                {where}
                ORDER BY
                    CASE q.coordinate_status WHEN 'VALID' THEN 5 WHEN 'UNCHECKED' THEN 4 ELSE 1 END,
                    q.quality_score,
                    m.site_name
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT coordinate_status, issue_code, COUNT(*) AS count
                    FROM energy_site_coordinate_quality
                    GROUP BY coordinate_status, issue_code
                    ORDER BY coordinate_status, issue_code
                    """
                )
            )
            return {
                "items": items,
                "summary": summary,
                "page": page,
                "page_size": page_size,
                "count": min(page_size, total - offset) if total > offset else 0,
                "total": total,
            }
        finally:
            con.close()


    def energy_site_summary(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_summary_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_summary_mart is not built")
            cursor = con.execute("SELECT metric, value FROM energy_site_summary_mart ORDER BY metric")
            items = rows_to_dicts(cursor)
            return {"items": items, "metrics": {item["metric"]: item["value"] for item in items}}
        finally:
            con.close()


    def energy_site_regions(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 1000)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_search_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_search_mart is not built")
            auction_table = auction_table_name(con)
            if bool_query(query.get("has_auction", "")) is True and not auction_table:
                return {"items": [], "count": 0, "auction_source_status": "SOURCE_NOT_LOADED"}
            where, params = energy_site_search_where(query, "m", auction_table, con=con)
            auction_count_expr = (
                """
                COUNT(DISTINCT CASE WHEN a.energy_site_id IS NOT NULL THEN m.energy_site_id END) AS auction_site_count
                """
                if auction_table
                else "0 AS auction_site_count"
            )
            auction_join = (
                f"""
                LEFT JOIN (
                    SELECT DISTINCT energy_site_id
                    FROM {quote_ident(auction_table)}
                ) a ON m.energy_site_id = a.energy_site_id
                """
                if auction_table
                else ""
            )
            cursor = con.execute(
                f"""
                SELECT
                    m.site_category,
                    m.site_type,
                    m.sido,
                    m.sigungu,
                    {service_status_expr("m.business_status")} AS service_status,
                    COUNT(DISTINCT m.energy_site_id) AS site_count,
                    COUNT(DISTINCT CASE WHEN {service_status_expr("m.business_status")} = 'OPERATING' THEN m.energy_site_id END) AS operating_count,
                    COUNT(DISTINCT CASE WHEN {service_status_expr("m.business_status")} = 'SUSPENDED' THEN m.energy_site_id END) AS suspended_count,
                    COUNT(DISTINCT CASE WHEN {service_status_expr("m.business_status")} = 'CLOSED' THEN m.energy_site_id END) AS closed_count,
                    COUNT(DISTINCT CASE WHEN m.pnu IS NOT NULL THEN m.energy_site_id END) AS pnu_filled_count,
                    COUNT(DISTINCT CASE WHEN m.building_review_status IN ('AUTO_CONFIRMED', 'CONFIRMED') THEN m.energy_site_id END) AS building_matched_count,
                    COUNT(DISTINCT st.energy_site_id) AS storage_site_count,
                    COUNT(DISTINCT eq.energy_site_id) AS equipment_site_count,
                    {auction_count_expr}
                FROM energy_site_search_mart m
                LEFT JOIN energy_site_storage_capacity st ON m.energy_site_id = st.energy_site_id
                LEFT JOIN energy_site_equipment eq ON m.energy_site_id = eq.energy_site_id
                {auction_join}
                {where}
                GROUP BY m.site_category, m.site_type, m.sido, m.sigungu, service_status
                ORDER BY site_count DESC, m.site_category, m.site_type, m.sido, m.sigungu, service_status
                LIMIT ?
                """,
                [*params, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items), "auction_source_status": "READY" if auction_table else "SOURCE_NOT_LOADED"}
        finally:
            con.close()


    def energy_site_quality(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_quality_result"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "QUALITY_NOT_RUN", "energy_site_quality_result is not built")
            cursor = con.execute(
                """
                SELECT run_id, check_name, target_table, severity, status, failed_count, details, executed_at
                FROM energy_site_quality_result
                ORDER BY
                    CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END,
                    CASE status WHEN 'FAIL' THEN 1 ELSE 2 END,
                    check_name
                """
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_precision_quality(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_precision_quality_result"):
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "PRECISION_QUALITY_NOT_RUN",
                    "energy_site_precision_quality_result is not built",
                )
            cursor = con.execute(
                """
                SELECT
                    run_id,
                    check_group,
                    check_name,
                    severity,
                    status,
                    measured_value,
                    threshold_value,
                    failed_count,
                    detail,
                    checked_at
                FROM energy_site_precision_quality_result
                ORDER BY
                    CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END,
                    CASE status WHEN 'FAIL' THEN 1 ELSE 2 END,
                    check_group,
                    check_name
                """
            )
            items = rows_to_dicts(cursor)
            summary_cursor = con.execute(
                """
                SELECT severity, status, COUNT(*) AS count
                FROM energy_site_precision_quality_result
                GROUP BY severity, status
                ORDER BY severity, status
                """
            )
            return {"items": items, "summary": rows_to_dicts(summary_cursor), "count": len(items)}
        finally:
            con.close()


    def energy_site_review_queue(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query)
        where, params = energy_site_filters(
            query,
            {
                "issue_type": "q.issue_type",
                "priority": "q.priority",
                "review_status": "q.review_status",
                "site_category": "m.site_category",
            },
        )
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_manual_review_queue"):
                return empty_page(page, page_size)
            total = con.execute(
                f"""
                SELECT COUNT(*)
                FROM energy_site_manual_review_queue q
                LEFT JOIN energy_site_master m ON q.energy_site_id = m.energy_site_id
                {where}
                """,
                params,
            ).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT
                    q.energy_site_id,
                    m.site_name,
                    m.site_category,
                    m.site_type,
                    m.address_raw,
                    q.issue_type,
                    q.priority,
                    q.reason,
                    q.candidate_count,
                    q.review_status,
                    q.created_at,
                    (
                        SELECT COUNT(*)
                        FROM energy_site_pnu_candidate p
                        WHERE p.energy_site_id = q.energy_site_id
                    ) AS pnu_candidate_count,
                    (
                        SELECT MAX(confidence)
                        FROM energy_site_pnu_candidate p
                        WHERE p.energy_site_id = q.energy_site_id
                    ) AS best_pnu_confidence
                FROM energy_site_manual_review_queue q
                LEFT JOIN energy_site_master m ON q.energy_site_id = m.energy_site_id
                {where}
                ORDER BY
                    CASE q.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                    CASE q.review_status WHEN 'OPEN' THEN 1 WHEN 'IN_PROGRESS' THEN 2 ELSE 3 END,
                    q.created_at DESC,
                    q.energy_site_id
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            for item in items:
                item["review_id"] = review_id_for(item)
            return {"items": items, "page": page, "page_size": page_size, "count": len(items), "total": total}
        finally:
            con.close()


    def admin_update_review_item(
        self,
        review_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        review_status = str(payload.get("review_status") or "RESOLVED").upper()
        if review_status not in REVIEW_STATUSES:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_REVIEW_STATUS",
                "review_status must be one of OPEN, IN_PROGRESS, RESOLVED, REJECTED",
            )
        energy_site_id, issue_type, priority = split_review_id(review_id, payload)
        if not energy_site_id or not issue_type:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_REVIEW_ID", "review_id must include energy_site_id and issue_type")

        if payload.get("dry_run"):
            con = connect(read_only=True)
            try:
                if not table_exists(con, "energy_site_manual_review_queue"):
                    raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_manual_review_queue is not built")
                filters = ["energy_site_id = ?", "issue_type = ?"]
                params: list[Any] = [energy_site_id, issue_type]
                if priority:
                    filters.append("priority = ?")
                    params.append(priority)
                matched_count = con.execute(
                    f"SELECT COUNT(*) FROM energy_site_manual_review_queue WHERE {' AND '.join(filters)}",
                    params,
                ).fetchone()[0]
                return {
                    "review_id": review_id,
                    "energy_site_id": energy_site_id,
                    "issue_type": issue_type,
                    "priority": priority,
                    "review_status": review_status,
                    "dry_run": True,
                    "matched_count": matched_count,
                }
            finally:
                con.close()

        con = connect(read_only=False)
        try:
            if not table_exists(con, "energy_site_manual_review_queue"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_manual_review_queue is not built")
            reviewer = str(actor.get("display_name") or payload.get("reviewer") or "local-admin")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS energy_site_review_action (
                    action_id VARCHAR,
                    review_id VARCHAR,
                    energy_site_id VARCHAR,
                    issue_type VARCHAR,
                    priority VARCHAR,
                    review_status VARCHAR,
                    review_note VARCHAR,
                    reviewer VARCHAR,
                    acted_at TIMESTAMP DEFAULT current_timestamp
                )
                """
            )
            filters = ["energy_site_id = ?", "issue_type = ?"]
            params: list[Any] = [energy_site_id, issue_type]
            if priority:
                filters.append("priority = ?")
                params.append(priority)
            where = " AND ".join(filters)
            con.execute(f"UPDATE energy_site_manual_review_queue SET review_status = ? WHERE {where}", [review_status, *params])
            con.execute(
                """
                INSERT INTO energy_site_review_action (
                    action_id,
                    review_id,
                    energy_site_id,
                    issue_type,
                    priority,
                    review_status,
                    review_note,
                    reviewer
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(uuid.uuid4()),
                    review_id,
                    energy_site_id,
                    issue_type,
                    priority,
                    review_status,
                    str(payload.get("review_note") or ""),
                    reviewer,
                ],
            )
            self.insert_audit_event(
                con,
                actor,
                "REVIEW_STATUS_UPDATE",
                "energy_site_manual_review_queue",
                review_id,
                "SUCCESS",
                request_id,
                {"review_status": review_status, "issue_type": issue_type, "priority": priority},
            )
            return {
                "review_id": review_id,
                "energy_site_id": energy_site_id,
                "issue_type": issue_type,
                "priority": priority,
                "review_status": review_status,
                "reviewer": reviewer,
            }
        finally:
            con.close()


    def energy_site_geocode_requests(self, query: dict[str, str]) -> dict[str, Any]:
        page, page_size, offset = page_window(query)
        where, params = energy_site_filters(
            query,
            {
                "request_status": "r.request_status",
                "provider": "r.provider",
                "site_category": "m.site_category",
            },
        )
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_geocode_request"):
                return empty_page(page, page_size, summary=[])
            total = con.execute(
                f"""
                SELECT COUNT(*)
                FROM energy_site_geocode_request r
                LEFT JOIN energy_site_master m ON r.energy_site_id = m.energy_site_id
                {where}
                """,
                params,
            ).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT
                    r.request_id,
                    r.energy_site_id,
                    m.site_name,
                    m.site_category,
                    m.site_type,
                    m.address_raw,
                    r.provider,
                    r.request_type,
                    r.request_keyword,
                    r.request_status,
                    r.http_status,
                    r.provider_error_code,
                    r.provider_error_message,
                    r.attempted_at,
                    r.created_at,
                    r.completed_at,
                    (
                        SELECT COUNT(*)
                        FROM energy_site_geocode_result gr
                        WHERE gr.request_id = r.request_id
                    ) AS result_count
                FROM energy_site_geocode_request r
                LEFT JOIN energy_site_master m ON r.energy_site_id = m.energy_site_id
                {where}
                ORDER BY
                    CASE r.request_status
                        WHEN 'READY' THEN 1
                        WHEN 'IN_PROGRESS' THEN 2
                        WHEN 'ERROR' THEN 3
                        WHEN 'NO_RESULT' THEN 4
                        ELSE 5
                    END,
                    r.energy_site_id,
                    r.request_type
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            summary_cursor = con.execute(
                """
                SELECT provider, request_status, COUNT(*) AS count
                FROM energy_site_geocode_request
                GROUP BY provider, request_status
                ORDER BY provider, request_status
                """
            )
            return {
                "items": items,
                "summary": rows_to_dicts(summary_cursor),
                "page": page,
                "page_size": page_size,
                "count": len(items),
                "total": total,
            }
        finally:
            con.close()


    def energy_site_hub_match_stats(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            total_sites = scalar_if_table(con, "energy_site_master", "SELECT COUNT(*) FROM energy_site_master")
            charging_sites = scalar(con, "SELECT COUNT(*) FROM energy_site_master WHERE site_category = 'CHARGING_STATION'") if total_sites else 0
            primary_pnu_sites = scalar_if_table(con, "energy_site_pnu_candidate", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_pnu_candidate WHERE is_primary")
            charging_primary_pnu_sites = (
                scalar(
                    con,
                    """
                    SELECT COUNT(DISTINCT p.energy_site_id)
                    FROM energy_site_pnu_candidate p
                    JOIN energy_site_master m ON p.energy_site_id = m.energy_site_id
                    WHERE p.is_primary
                      AND m.site_category = 'CHARGING_STATION'
                    """,
                )
                if table_exists(con, "energy_site_pnu_candidate") and table_exists(con, "energy_site_master")
                else 0
            )
            building_candidate_sites = scalar_if_table(con, "energy_site_building_link_candidate", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_building_link_candidate")
            building_link_sites = scalar_if_table(con, "energy_site_building_link", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_building_link")
            land_area_available_sites = scalar_if_table(con, "energy_site_land_area_summary", "SELECT COUNT(*) FROM energy_site_land_area_summary WHERE total_land_area_m2 IS NOT NULL")
            operating_sites = scalar_if_table(con, "energy_site_master", f"SELECT COUNT(*) FROM energy_site_master WHERE {service_status_expr('business_status')} = 'OPERATING'")
            operating_oil_sites = scalar_if_table(con, "energy_site_master", f"SELECT COUNT(*) FROM energy_site_master WHERE site_category = 'OIL_STATION' AND {service_status_expr('business_status')} = 'OPERATING'")
            operating_charging_sites = scalar_if_table(con, "energy_site_master", f"SELECT COUNT(*) FROM energy_site_master WHERE site_category = 'CHARGING_STATION' AND {service_status_expr('business_status')} = 'OPERATING'")
            storage_site_count = scalar_if_table(con, "energy_site_storage_capacity", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_storage_capacity")
            equipment_site_count = scalar_if_table(con, "energy_site_equipment", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_equipment")
            auction_table = auction_table_name(con)
            auction_history_site_count = scalar_if_table(con, auction_table, f"SELECT COUNT(DISTINCT energy_site_id) FROM {quote_ident(auction_table)}") if auction_table else 0
            review_open_count = scalar_if_table(con, "energy_site_manual_review_queue", "SELECT COUNT(*) FROM energy_site_manual_review_queue WHERE review_status = 'OPEN'")
            quality_error_fail_count = scalar_if_table(con, "energy_site_precision_quality_result", "SELECT COUNT(*) FROM energy_site_precision_quality_result WHERE severity = 'ERROR' AND status = 'FAIL'", None)
            quality_warn_fail_count = scalar_if_table(con, "energy_site_precision_quality_result", "SELECT COUNT(*) FROM energy_site_precision_quality_result WHERE severity = 'WARN' AND status = 'FAIL'", None)
            geocode_summary = grouped_rows_if_table(
                con,
                "energy_site_geocode_request",
                """
                SELECT provider, request_status, COUNT(*) AS count
                FROM energy_site_geocode_request
                GROUP BY provider, request_status
                ORDER BY provider, request_status
                """,
            )
            review_summary = grouped_rows_if_table(
                con,
                "energy_site_manual_review_queue",
                """
                SELECT issue_type, priority, review_status, COUNT(*) AS count
                FROM energy_site_manual_review_queue
                GROUP BY issue_type, priority, review_status
                ORDER BY issue_type, priority, review_status
                """,
            )
            metrics = {
                "total_sites": total_sites,
                "charging_sites": charging_sites,
                "primary_pnu_sites": primary_pnu_sites,
                "primary_pnu_coverage": round(primary_pnu_sites / total_sites, 4) if total_sites else 0,
                "charging_primary_pnu_sites": charging_primary_pnu_sites,
                "charging_primary_pnu_coverage": round(charging_primary_pnu_sites / charging_sites, 4) if charging_sites else 0,
                "building_candidate_sites": building_candidate_sites,
                "building_link_sites": building_link_sites,
                "land_area_available_sites": land_area_available_sites,
                "operating_sites": operating_sites,
                "operating_oil_sites": operating_oil_sites,
                "operating_charging_sites": operating_charging_sites,
                "storage_site_count": storage_site_count,
                "equipment_site_count": equipment_site_count,
                "auction_history_site_count": auction_history_site_count,
                "review_open_count": review_open_count,
                "quality_error_fail_count": quality_error_fail_count,
                "quality_warn_fail_count": quality_warn_fail_count,
            }
            return {
                "metrics": metrics,
                "geocode_summary": geocode_summary,
                "review_summary": review_summary,
                "auction_source_status": "READY" if auction_table else "SOURCE_NOT_LOADED",
            }
        finally:
            con.close()


    def energy_site_route(self, path: str, query: dict[str, str]) -> dict[str, Any]:
        parts = [part for part in path.removeprefix("/api/energy-sites/").split("/") if part]
        if not parts:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_ENERGY_SITE_ID", "energy_site_id is required")
        energy_site_id = parts[0]
        child = parts[1] if len(parts) > 1 else None
        if child == "land":
            return self.energy_site_land(energy_site_id, query)
        if child == "pnu-candidates":
            return self.energy_site_pnu_candidates(energy_site_id, query)
        if child == "land-area":
            return self.energy_site_land_area(energy_site_id)
        if child == "buildings":
            return self.energy_site_buildings(energy_site_id, query)
        if child == "facility-summary":
            return self.energy_site_facility_summary(energy_site_id, query)
        if child == "equipment":
            return self.energy_site_equipment(energy_site_id, query)
        if child == "storage":
            return self.energy_site_storage(energy_site_id, query)
        if child == "storage-candidates":
            return self.energy_site_storage_candidates(energy_site_id, query)
        if child == "blank-reasons":
            return self.energy_site_blank_reasons(energy_site_id, query)
        if child == "auction-search-terms":
            return self.energy_site_auction_search_terms(energy_site_id, query)
        if child == "auction-history":
            return self.energy_site_auction_history(energy_site_id, query)
        if child == "auction-candidates":
            return self.energy_site_auction_candidates(energy_site_id, query)
        if child == "current-auction":
            return self.energy_site_current_auction(energy_site_id, query)
        if child == "card-payments":
            return self.energy_site_card_payments(energy_site_id, query)
        if child == "financials":
            return self.energy_site_financials(energy_site_id, query)
        if child == "valuation":
            return self.energy_site_valuation(energy_site_id, query)
        if child == "planning-events":
            return self.energy_site_planning_events(energy_site_id, query)
        if child == "prediction":
            return self.energy_site_prediction(energy_site_id, query)
        if child == "precision":
            return self.energy_site_precision(energy_site_id, query)
        if child:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "energy site child endpoint not found")
        return self.energy_site_detail(energy_site_id)


    def energy_site_detail(self, energy_site_id: str) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_search_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_search_mart is not built")
            cursor = con.execute(
                f"""
                SELECT *,
                       {service_status_expr("business_status")} AS service_status
                FROM energy_site_search_mart
                WHERE energy_site_id = ?
                """,
                [energy_site_id],
            )
            rows = rows_to_dicts(cursor)
            if not rows:
                raise ApiError(HTTPStatus.NOT_FOUND, "ENERGY_SITE_NOT_FOUND", "energy site not found")
            item = rows[0]
            if table_exists(con, "energy_site_auction_event"):
                auction_cursor = con.execute(
                    """
                    SELECT event_date, event_status, case_no, court_name, source_provider,
                           successful_bid_value, appraisal_value, minimum_bid_value,
                           bidder_count, source_document_id, confidence, checked_at, special_notes
                    FROM energy_site_auction_event
                    WHERE energy_site_id = ?
                    ORDER BY event_date DESC NULLS LAST, created_at DESC NULLS LAST
                    LIMIT 20
                    """,
                    [energy_site_id],
                )
                item["auction_events"] = rows_to_dicts(auction_cursor)
                item["auction_event_count"] = len(item["auction_events"])
            else:
                item["auction_events"] = []
                item["auction_event_count"] = 0
            if table_exists(con, "energy_site_current_auction_status"):
                current_cursor = con.execute(
                    """
                    SELECT case_no, court_name, case_status, bid_due_date, appraisal_value,
                           minimum_bid_value, bidder_count, auction_url, source_provider,
                           source_document_id, confidence, checked_at, result_note
                    FROM energy_site_current_auction_status
                    WHERE energy_site_id = ?
                    ORDER BY checked_at DESC NULLS LAST, created_at DESC NULLS LAST
                    LIMIT 10
                    """,
                    [energy_site_id],
                )
                item["current_auction_status"] = rows_to_dicts(current_cursor)
                item["current_auction_status_count"] = len(item["current_auction_status"])
            else:
                item["current_auction_status"] = []
                item["current_auction_status_count"] = 0
            return item
        finally:
            con.close()


    def energy_site_land(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_land_link"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_land_link is not built")
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_land_link
                WHERE energy_site_id = ?
                ORDER BY is_primary DESC, link_confidence DESC, pnu
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_pnu_candidates(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "50")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_pnu_candidate"):
                return {"items": [], "count": 0}
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_pnu_candidate
                WHERE energy_site_id = ?
                ORDER BY is_primary DESC, candidate_rank, confidence DESC
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def land_area_from_building_register(
        self,
        con: duckdb.DuckDBPyConnection,
        energy_site_id: str,
        existing_item: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not table_exists(con, "energy_site_building_link"):
            return None
        preferred_sources = ["bldrg_total_title", "bldrg_title", "permit_202603_basic", "permit_basic"]
        selects: list[str] = []
        params: list[Any] = []
        for rank, table_name in enumerate(preferred_sources, start=1):
            if not table_exists(con, table_name):
                continue
            pk_col = semantic_column(con, table_name, "building_register_pk")
            area_col = land_area_column(con, table_name)
            if not pk_col or not area_col:
                continue
            selects.append(
                f"""
                SELECT
                    b.energy_site_id,
                    b.pnu,
                    TRY_CAST(h.{quote_ident(area_col)} AS DOUBLE) AS land_area_m2,
                    {rank} AS source_rank,
                    '{table_name}' AS source_table
                FROM energy_site_building_link b
                JOIN {quote_ident(table_name)} h
                  ON CAST(h.{quote_ident(pk_col)} AS VARCHAR) = b.building_register_pk
                WHERE b.energy_site_id = ?
                  AND b.hub_table = ?
                  AND TRY_CAST(h.{quote_ident(area_col)} AS DOUBLE) > 0
                """
            )
            params.extend([energy_site_id, table_name])
        if not selects:
            return None
        row = con.execute(
            f"""
            WITH candidate AS (
                {" UNION ALL ".join(selects)}
            ),
            ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY pnu
                           ORDER BY source_rank, land_area_m2 DESC, source_table
                       ) AS rn
                FROM candidate
                WHERE pnu IS NOT NULL
            ),
            picked AS (
                SELECT *
                FROM ranked
                WHERE rn = 1
            )
            SELECT
                COUNT(*) AS pnu_count,
                string_agg(pnu, ',' ORDER BY pnu) AS pnu_list,
                SUM(land_area_m2) AS total_land_area_m2,
                string_agg(DISTINCT source_table, ',' ORDER BY source_table) AS source_tables
            FROM picked
            """,
            params,
        ).fetchone()
        if not row or row[2] is None:
            return None
        confidence = existing_item.get("confidence") if existing_item else None
        return {
            "energy_site_id": energy_site_id,
            "pnu_count": row[0],
            "pnu_list": row[1],
            "total_land_area_m2": row[2],
            "area_source": f"BUILDING_REGISTER_LAND_AREA:{row[3]}",
            "confidence": max(float(confidence or 0), 0.75),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


    def energy_site_land_area(self, energy_site_id: str) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            item = None
            if table_exists(con, "energy_site_land_area_summary"):
                cursor = con.execute(
                    """
                    SELECT *
                    FROM energy_site_land_area_summary
                    WHERE energy_site_id = ?
                    """,
                    [energy_site_id],
                )
                rows = rows_to_dicts(cursor)
                item = rows[0] if rows else None
            if item and item.get("total_land_area_m2") is not None:
                return {"item": item}
            fallback = self.land_area_from_building_register(con, energy_site_id, item)
            return {"item": fallback or item}
        finally:
            con.close()


    def energy_site_buildings(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_building_link"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "energy_site_building_link is not built")
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_building_link
                WHERE energy_site_id = ?
                ORDER BY is_primary DESC, link_confidence DESC, facility_class, building_register_pk
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_facility_summary(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_facility_summary"):
                return {"items": [], "count": 0}
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_facility_summary
                WHERE energy_site_id = ?
                ORDER BY facility_type, facility_name, source_table, source_pk
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_equipment(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_equipment"):
                return {"items": [], "count": 0}
            cursor = con.execute("SELECT * FROM energy_site_equipment WHERE energy_site_id = ? ORDER BY equipment_type, equipment_name", [energy_site_id])
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_storage(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_storage_capacity"):
                return {"items": [], "count": 0}
            cursor = con.execute("SELECT * FROM energy_site_storage_capacity WHERE energy_site_id = ? ORDER BY storage_type, material_type", [energy_site_id])
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def energy_site_storage_candidates(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "80")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_storage_uplift_candidate"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED"}
            cursor = con.execute(
                """
                SELECT
                  candidate_status,
                  candidate_kind,
                  storage_type,
                  material_type,
                  capacity_value,
                  capacity_unit,
                  capacity_raw,
                  tank_count,
                  equipment_type,
                  equipment_name,
                  equipment_count,
                  source_table,
                  match_method,
                  confidence,
                  issue_message
                FROM energy_site_storage_uplift_candidate
                WHERE energy_site_id = ?
                ORDER BY candidate_rank, candidate_status, candidate_kind, source_table
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items), "source_status": "READY"}
        finally:
            con.close()


    def energy_site_blank_reasons(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "80")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_blank_reason_status"):
                return {
                    "items": [],
                    "count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "blank_reason_status": "SOURCE_NOT_LOADED",
                }
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_blank_reason_status
                WHERE energy_site_id = ?
                ORDER BY display_order, check_group
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {
                "items": items,
                "count": len(items),
                "source_status": "READY",
                "blank_reason_status": "READY" if items else "NO_REASON_STATUS",
            }
        finally:
            con.close()


    def energy_site_auction_search_terms(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            site_rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT energy_site_id, site_name, address_raw, pnu
                    FROM energy_site_search_mart
                    WHERE energy_site_id = ?
                    """,
                    [energy_site_id],
                )
            ) if table_exists(con, "energy_site_search_mart") else []
            site = site_rows[0] if site_rows else {"energy_site_id": energy_site_id}
            candidates: list[dict[str, Any]] = []
            if table_exists(con, "energy_site_land_link"):
                candidates.extend(
                    rows_to_dicts(
                        con.execute(
                            """
                            SELECT
                                energy_site_id,
                                pnu,
                                NULL AS building_register_pk,
                                'energy_site_land_link' AS source_table,
                                NULL AS main_use,
                                NULL AS facility_class,
                                is_primary,
                                link_confidence,
                                NULL AS jibun_address,
                                NULL AS road_address
                            FROM energy_site_land_link
                            WHERE energy_site_id = ?
                            ORDER BY is_primary DESC, link_confidence DESC, pnu
                            """,
                            [energy_site_id],
                        )
                    )
                )
            if table_exists(con, "energy_site_building_link"):
                hub_tables = [
                    row[0]
                    for row in con.execute(
                        """
                        SELECT DISTINCT hub_table
                        FROM energy_site_building_link
                        WHERE energy_site_id = ?
                          AND hub_table IS NOT NULL
                        ORDER BY hub_table
                        """,
                        [energy_site_id],
                    ).fetchall()
                ]
                for table_name in hub_tables:
                    if not table_exists(con, table_name):
                        continue
                    pk_col = semantic_column(con, table_name, "building_register_pk")
                    if not pk_col:
                        continue
                    jibun_col = semantic_column(con, table_name, "jibun_address")
                    road_col = semantic_column(con, table_name, "road_address")
                    jibun_expr = f"CAST(h.{quote_ident(jibun_col)} AS VARCHAR)" if jibun_col else "NULL"
                    road_expr = f"CAST(h.{quote_ident(road_col)} AS VARCHAR)" if road_col else "NULL"
                    candidates.extend(
                        rows_to_dicts(
                            con.execute(
                                f"""
                                SELECT DISTINCT
                                    b.energy_site_id,
                                    b.pnu,
                                    b.building_register_pk,
                                    b.hub_table AS source_table,
                                    b.main_use,
                                    b.facility_class,
                                    b.is_primary,
                                    b.link_confidence,
                                    {jibun_expr} AS jibun_address,
                                    {road_expr} AS road_address
                                FROM energy_site_building_link b
                                LEFT JOIN {quote_ident(table_name)} h
                                  ON CAST(h.{quote_ident(pk_col)} AS VARCHAR) = b.building_register_pk
                                WHERE b.energy_site_id = ?
                                  AND b.hub_table = ?
                                ORDER BY b.is_primary DESC, b.link_confidence DESC, b.building_register_pk
                                """,
                                [energy_site_id, table_name],
                            )
                        )
                    )
            if not candidates:
                candidates.append(
                    {
                        "energy_site_id": energy_site_id,
                        "pnu": site.get("pnu"),
                        "building_register_pk": None,
                        "source_table": "energy_site_search_mart",
                        "main_use": None,
                        "facility_class": None,
                        "is_primary": True,
                        "link_confidence": None,
                        "jibun_address": None,
                        "road_address": site.get("address_raw"),
                    }
                )
            seen: set[tuple[str, str, str]] = set()
            items: list[dict[str, Any]] = []
            for candidate in candidates:
                search_keyword = (
                    candidate.get("jibun_address")
                    or candidate.get("road_address")
                    or site.get("address_raw")
                    or candidate.get("pnu")
                    or site.get("site_name")
                    or energy_site_id
                )
                key = (str(candidate.get("pnu") or ""), str(candidate.get("building_register_pk") or ""), str(search_keyword or ""))
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        **candidate,
                        "site_name": site.get("site_name"),
                        "address_raw": site.get("address_raw"),
                        "search_keyword": search_keyword,
                        "search_providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION"],
                        "search_period_years": 20,
                        "search_status": "READY_FOR_EXTERNAL_PROVIDER",
                    }
                )
            if table_exists(con, "energy_site_auction_search_queue"):
                queue_items = rows_to_dicts(
                    con.execute(
                        """
                        SELECT
                            energy_site_id,
                            pnu,
                            building_register_pk,
                            source_table,
                            NULL AS main_use,
                            NULL AS facility_class,
                            TRUE AS is_primary,
                            NULL AS link_confidence,
                            jibun_address,
                            road_address,
                            search_keyword,
                            provider AS search_provider,
                            provider AS search_providers,
                            search_period_years,
                            search_status,
                            priority,
                            reason
                        FROM energy_site_auction_search_queue
                        WHERE energy_site_id = ?
                        ORDER BY
                            CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                            provider,
                            source_table,
                            search_keyword
                        LIMIT 300
                        """,
                        [energy_site_id],
                    )
                )
                if queue_items:
                    items = queue_items
            return {
                "items": items,
                "count": len(items),
                "providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION"],
                "period_years": 20,
                "source_status": "READY_FOR_EXTERNAL_PROVIDER",
            }
        finally:
            con.close()


    def energy_site_auction_history(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            table_name = auction_table_name(con)
            if not table_name:
                return {
                    "items": [],
                    "count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION"],
                    "period_years": 20,
                }
            event_date_expr, event_date_col = auction_column_expr(
                con,
                table_name,
                ["event_date", "auction_date", "sale_date", "bid_date", "award_date", "collected_at", "경매일자", "매각기일", "낙찰일자"],
                "a",
            )
            event_status_expr, _ = auction_column_expr(
                con,
                table_name,
                ["event_status", "auction_status", "sale_status", "bid_status", "result_status", "case_status", "진행상태", "낙찰상태"],
                "a",
            )
            valuation_date_expr, _ = auction_column_expr(
                con,
                table_name,
                ["valuation_date", "appraisal_date", "assessment_date", "감정가일", "감정일시"],
                "a",
                "NULL",
            )
            award_date_expr, _ = auction_column_expr(
                con,
                table_name,
                ["award_date", "낙찰일", "낙찰일자", "매각일", "매각기일", "매각일자", "sale_date"],
                "a",
                "NULL",
            )
            case_no_expr, _ = auction_column_expr(
                con,
                table_name,
                ["case_no", "case_number", "auction_case_no", "court_case_no", "사건번호"],
                "a",
            )
            provider_expr, _ = auction_column_expr(
                con,
                table_name,
                ["source_provider", "provider", "source_system", "data_provider", "원천"],
                "a",
                "'INFOCARE_AUCTION_ONE'",
            )
            result_price_expr, _ = auction_column_expr(
                con,
                table_name,
                ["successful_bid_value", "award_price", "sale_price", "bid_price", "result_price", "낙찰가", "매각가"],
                "a",
            )
            appraisal_value_expr, _ = auction_column_expr(
                con,
                table_name,
                ["appraisal_value", "appraised_value", "감정가", "감정평가액"],
                "a",
            )
            bidder_count_expr, _ = auction_column_expr(
                con,
                table_name,
                ["bidder_count", "biddercount", "입찰자 수", "응찰자수", "응찰자 수", "입찰인원", "응찰인원"],
                "a",
            )
            order_col = event_date_col or first_existing_column(con, table_name, ["collected_at", "created_at", "updated_at"])
            order_sql = f"ORDER BY {quote_ident(order_col)} DESC" if order_col else ""
            cursor = con.execute(
                f"""
                SELECT
                    a.*,
                    {event_date_expr} AS event_date,
                    {event_status_expr} AS event_status,
                    {valuation_date_expr} AS valuation_date,
                    {award_date_expr} AS award_date,
                    {case_no_expr} AS case_no,
                    {provider_expr} AS provider,
                    {appraisal_value_expr} AS appraised_value,
                    {bidder_count_expr} AS bidder_count,
                    {result_price_expr} AS successful_bid_value
                FROM {quote_ident(table_name)} a
                WHERE energy_site_id = ?
                {order_sql}
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            for item in items:
                case_no_kind, case_no_valid, case_no_issue = classify_case_no(item.get("case_no"))
                item["case_no_display"] = resolve_case_no_display(
                    item.get("case_no"),
                    item.get("provider"),
                    item.get("raw_payload"),
                )
                item["case_no_kind"] = case_no_kind
                item["case_no_valid"] = case_no_valid
                item["case_no_issue"] = case_no_issue
            return {
                "items": items,
                "count": len(items),
                "source_status": "READY",
                "providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION"],
                "period_years": 20,
            }
        finally:
            con.close()


    def energy_site_auction_candidates(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "50")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_candidate_review"):
                return {
                    "items": [],
                    "count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "candidate_status": "SOURCE_NOT_LOADED",
                }
            items = rows_to_dicts(
                con.execute(
                    """
                    SELECT *
                    FROM energy_site_auction_candidate_review
                    WHERE energy_site_id = ?
                    ORDER BY
                      CASE review_status WHEN 'REVIEW_REQUIRED' THEN 1 WHEN 'CONFIRMED' THEN 2 ELSE 3 END,
                      candidate_confidence DESC,
                      COALESCE(event_date, '') DESC,
                      provider_reference_no
                    LIMIT ?
                    """,
                    [energy_site_id, limit],
                )
            )
            return {
                "items": items,
                "count": len(items),
                "source_status": "READY",
                "candidate_status": "REVIEW_REQUIRED" if items else "NO_CANDIDATE",
            }
        finally:
            con.close()


    def energy_site_current_auction(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_current_auction_status"):
                return {
                    "items": [],
                    "count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "current_status": "SOURCE_NOT_LOADED",
                    "providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION", "ONBID"],
                }
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_current_auction_status
                WHERE energy_site_id = ?
                ORDER BY
                    TRY_CAST(bid_due_date AS TIMESTAMP) ASC NULLS LAST,
                    TRY_CAST(checked_at AS TIMESTAMP) DESC NULLS LAST,
                    case_no
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            seen_current_keys = {
                str(item.get("source_document_id") or item.get("case_no") or "").strip()
                for item in items
                if str(item.get("source_document_id") or item.get("case_no") or "").strip()
            }
            if table_exists(con, "energy_site_auction_event"):
                event_items = rows_to_dicts(
                    con.execute(
                        """
                        SELECT
                            energy_site_id,
                            case_no,
                            court_name,
                            event_status AS case_status,
                            event_date AS bid_due_date,
                            appraisal_value,
                            minimum_bid_value,
                            NULL AS previous_failed_count,
                            bidder_count,
                            NULL AS current_round,
                            auction_url,
                            source_provider,
                            source_document_id,
                            confidence,
                            checked_at,
                            created_at,
                            special_notes AS result_note,
                            raw_payload
                        FROM energy_site_auction_event
                        WHERE energy_site_id = ?
                          AND event_status IN ('IN_PROGRESS', 'CURRENT_AUCTION', 'BID_OPEN')
                        ORDER BY
                            TRY_CAST(event_date AS TIMESTAMP) ASC NULLS LAST,
                            TRY_CAST(checked_at AS TIMESTAMP) DESC NULLS LAST,
                            case_no
                        LIMIT ?
                        """,
                        [energy_site_id, limit],
                    )
                )
                for event_item in event_items:
                    dedupe_key = str(event_item.get("source_document_id") or event_item.get("case_no") or "").strip()
                    if dedupe_key and dedupe_key in seen_current_keys:
                        continue
                    items.append(event_item)
                    if dedupe_key:
                        seen_current_keys.add(dedupe_key)
            items.sort(
                key=lambda item: (
                    1
                    if item.get("case_status") == "UNVERIFIED_PROVIDER_SEARCH_REQUIRED"
                    or item.get("source_provider") == "CURRENT_AUCTION_PROVIDER_SEARCH_QUEUE"
                    else 0,
                    str(item.get("bid_due_date") or "9999-12-31"),
                    str(item.get("checked_at") or ""),
                    str(item.get("case_no") or ""),
                )
            )
            items = items[:limit]
            for item in items:
                case_no_kind, case_no_valid, case_no_issue = classify_case_no(item.get("case_no"))
                item["case_no_display"] = resolve_case_no_display(
                    item.get("case_no"),
                    item.get("source_provider"),
                    item.get("raw_payload"),
                )
                item["case_no_kind"] = case_no_kind
                item["case_no_valid"] = case_no_valid
                item["case_no_issue"] = case_no_issue
            verified_items = [
                item
                for item in items
                if item.get("case_status") != "UNVERIFIED_PROVIDER_SEARCH_REQUIRED"
                and item.get("source_provider") != "CURRENT_AUCTION_PROVIDER_SEARCH_QUEUE"
            ]
            active_items = [
                item
                for item in verified_items
                if item.get("case_status") not in {"NO_CURRENT_CASE", "NO_CASE", "NOT_FOUND"}
            ]
            no_case_items = [
                item
                for item in verified_items
                if item.get("case_status") in {"NO_CURRENT_CASE", "NO_CASE", "NOT_FOUND"}
            ]
            if active_items:
                current_status = "HAS_CURRENT_CASE"
                source_status = "READY"
            elif no_case_items:
                current_status = "NO_CURRENT_CASE"
                source_status = "READY"
            elif items:
                current_status = "CURRENT_AUCTION_SEARCH_REQUIRED"
                source_status = "SEARCH_REQUIRED"
            else:
                current_status = "NO_CURRENT_CASE"
                source_status = "READY"
            return {
                "items": items,
                "count": len(items),
                "source_status": source_status,
                "current_status": current_status,
                "providers": ["INFOCARE", "AUCTION_ONE", "SUPREME_COURT_AUCTION", "ONBID"],
            }
        finally:
            con.close()


    def energy_site_card_payments(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "24")), 1), 120)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_card_payment_monthly"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED"}
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_card_payment_monthly
                WHERE energy_site_id = ?
                ORDER BY sales_month DESC, source_provider
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items), "source_status": "READY"}
        finally:
            con.close()


    def energy_site_financials(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "12")), 1), 60)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_financial_statement"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED"}
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_financial_statement
                WHERE energy_site_id = ?
                ORDER BY fiscal_period DESC, period_type
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items), "source_status": "READY"}
        finally:
            con.close()


    def energy_site_valuation(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_revenue_value_assessment"):
                return {
                    "item": None,
                    "source_status": "SOURCE_NOT_LOADED",
                    "valuation_status": "SOURCE_NOT_LOADED",
                    "card_payment_count": scalar(con, "SELECT COUNT(*) FROM energy_site_card_payment_monthly WHERE energy_site_id = ?", [energy_site_id], 0)
                    if table_exists(con, "energy_site_card_payment_monthly") else 0,
                    "financial_count": scalar(con, "SELECT COUNT(*) FROM energy_site_financial_statement WHERE energy_site_id = ?", [energy_site_id], 0)
                    if table_exists(con, "energy_site_financial_statement") else 0,
                }
            run_join = ""
            select_run = "NULL AS model_name, NULL AS model_version, NULL AS assumption_json"
            if table_exists(con, "energy_site_revenue_value_model_run"):
                run_join = "LEFT JOIN energy_site_revenue_value_model_run r ON r.model_run_id = a.model_run_id"
                select_run = "r.model_name, r.model_version, r.assumption_json"
            cursor = con.execute(
                f"""
                SELECT
                    a.*,
                    {select_run}
                FROM energy_site_revenue_value_assessment a
                {run_join}
                WHERE a.energy_site_id = ?
                ORDER BY a.created_at DESC, a.base_month DESC
                LIMIT 1
                """,
                [energy_site_id],
            )
            rows = rows_to_dicts(cursor)
            item = rows[0] if rows else None
            if not item:
                valuation_status = "NO_VALUATION"
            elif item.get("recommended_value_mid") is not None and item.get("has_card_input") and item.get("has_financial_input"):
                valuation_status = "READY"
            else:
                valuation_status = "PARTIAL_INPUT"
            return {
                "item": item,
                "source_status": "READY",
                "valuation_status": valuation_status,
                "completion_ready": valuation_status == "READY",
                "card_payment_count": scalar(con, "SELECT COUNT(*) FROM energy_site_card_payment_monthly WHERE energy_site_id = ?", [energy_site_id], 0)
                if table_exists(con, "energy_site_card_payment_monthly") else 0,
                "financial_count": scalar(con, "SELECT COUNT(*) FROM energy_site_financial_statement WHERE energy_site_id = ?", [energy_site_id], 0)
                if table_exists(con, "energy_site_financial_statement") else 0,
            }
        finally:
            con.close()


    def energy_site_planning_events(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "50")), 1), 200)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_urban_planning_event"):
                return {
                    "items": [],
                    "count": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                    "planning_status": "SOURCE_NOT_LOADED",
                }
            cursor = con.execute(
                """
                SELECT *
                FROM energy_site_urban_planning_event
                WHERE energy_site_id = ?
                ORDER BY
                  COALESCE(effective_date, '') DESC,
                  COALESCE(announcement_date, '') DESC,
                  COALESCE(created_at, '') DESC
                LIMIT ?
                """,
                [energy_site_id, limit],
            )
            items = rows_to_dicts(cursor)
            positive_count = sum(1 for item in items if str(item.get("impact_direction") or "").upper() == "POSITIVE")
            negative_count = sum(1 for item in items if str(item.get("impact_direction") or "").upper() == "NEGATIVE")
            return {
                "items": items,
                "count": len(items),
                "source_status": "READY",
                "planning_status": "READY" if items else "NO_PLANNING_EVENT",
                "positive_count": positive_count,
                "negative_count": negative_count,
            }
        finally:
            con.close()


    def energy_site_prediction(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        review_limit = min(max(int(query.get("review_limit", "20")), 1), 100)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_profitability_prediction"):
                return {
                    "item": None,
                    "feature_snapshot": None,
                    "review_items": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "prediction_status": "SOURCE_NOT_LOADED",
                    "feature_status": "SOURCE_NOT_LOADED",
                }
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT *
                    FROM energy_site_profitability_prediction
                    WHERE energy_site_id = ?
                    ORDER BY
                      COALESCE(prediction_date, '') DESC,
                      COALESCE(created_at, '') DESC
                    LIMIT 1
                    """,
                    [energy_site_id],
                )
            )
            item = rows[0] if rows else None
            feature_snapshot = None
            feature_status = "SOURCE_NOT_LOADED"
            if table_exists(con, "energy_site_future_feature_snapshot"):
                feature_rows = rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_future_feature_snapshot
                        WHERE energy_site_id = ?
                        ORDER BY
                          COALESCE(snapshot_date, '') DESC,
                          COALESCE(created_at, '') DESC
                        LIMIT 1
                        """,
                        [energy_site_id],
                    )
                )
                feature_snapshot = feature_rows[0] if feature_rows else None
                feature_status = "READY" if feature_snapshot else "NO_FEATURE_SNAPSHOT"
            review_items: list[dict[str, Any]] = []
            if table_exists(con, "energy_site_prediction_review_queue"):
                review_items = rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_prediction_review_queue
                        WHERE energy_site_id = ?
                        ORDER BY
                          CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                          COALESCE(created_at, '') DESC
                        LIMIT ?
                        """,
                        [energy_site_id, review_limit],
                    )
                )
            return {
                "item": item,
                "feature_snapshot": feature_snapshot,
                "review_items": review_items,
                "source_status": "READY",
                "prediction_status": "READY" if item else "NO_PREDICTION",
                "feature_status": feature_status,
                "review_count": len(review_items),
            }
        finally:
            con.close()


    def energy_site_precision(self, energy_site_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        con = connect(read_only=True)
        try:
            profile: dict[str, Any] | None = None
            pnu_candidates: list[dict[str, Any]] = []
            review_items: list[dict[str, Any]] = []
            if table_exists(con, "energy_site_address_precision_profile"):
                rows = rows_to_dicts(
                    con.execute(
                        "SELECT * FROM energy_site_address_precision_profile WHERE energy_site_id = ?",
                        [energy_site_id],
                    )
                )
                profile = rows[0] if rows else None
            if table_exists(con, "energy_site_pnu_candidate"):
                pnu_candidates = rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_pnu_candidate
                        WHERE energy_site_id = ?
                        ORDER BY is_primary DESC, candidate_rank, confidence DESC
                        LIMIT ?
                        """,
                        [energy_site_id, limit],
                    )
                )
            if table_exists(con, "energy_site_manual_review_queue"):
                review_items = rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_manual_review_queue
                        WHERE energy_site_id = ?
                        ORDER BY
                            CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                            issue_type,
                            reason
                        LIMIT ?
                        """,
                        [energy_site_id, limit],
                    )
                )
            return {
                "profile": profile,
                "pnu_candidates": pnu_candidates,
                "review_items": review_items,
                "pnu_candidate_count": len(pnu_candidates),
                "review_count": len(review_items),
            }
        finally:
            con.close()


