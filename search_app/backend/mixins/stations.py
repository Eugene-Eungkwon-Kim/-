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

class StationsMixin:
    def station_search(self, query: dict[str, str]) -> dict[str, Any]:
        page = max(int(query.get("page", "1")), 1)
        page_size = min(max(int(query.get("page_size", "50")), 1), 200)
        offset = (page - 1) * page_size
        filters = []
        params: list[Any] = []
        if query.get("q"):
            filters.append("(station_name ILIKE ? OR address_raw ILIKE ?)")
            params.extend([f"%{query['q']}%", f"%{query['q']}%"])
        if query.get("pnu"):
            filters.append("pnu = ?")
            params.append(query["pnu"])
        if query.get("sido"):
            filters.append("sido = ?")
            params.append(query["sido"])
        if query.get("sigungu"):
            filters.append("sigungu = ?")
            params.append(query["sigungu"])
        if query.get("business_status"):
            filters.append("business_status = ?")
            params.append(query["business_status"])
        if query.get("matched"):
            if query["matched"].lower() in {"1", "true", "yes", "y"}:
                filters.append("building_review_status IN ('AUTO_CONFIRMED', 'CONFIRMED')")
            elif query["matched"].lower() in {"0", "false", "no", "n"}:
                filters.append("(building_review_status IS NULL OR building_review_status NOT IN ('AUTO_CONFIRMED', 'CONFIRMED'))")
        if query.get("min_confidence"):
            filters.append("match_confidence >= ?")
            params.append(float(query["min_confidence"]))
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_search_mart"):
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "STATION_MART_NOT_BUILT",
                    "station_search_mart is not built because station source tables are not loaded yet",
                    {"required": ["station_master", "station_building_link_candidate", "station_permit_link_candidate"]},
                )
            total = con.execute(f"SELECT COUNT(*) FROM station_search_mart {where}", params).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT *
                FROM station_search_mart
                {where}
                ORDER BY station_name
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "page": page, "page_size": page_size, "count": len(items), "total": total}
        finally:
            con.close()


    def station_summary(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_summary_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_summary_mart is not built")
            cursor = con.execute(
                """
                SELECT metric, value
                FROM station_summary_mart
                ORDER BY metric
                """
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "metrics": {item["metric"]: item["value"] for item in items}}
        finally:
            con.close()


    def station_regions(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 1000)
        filters = []
        params: list[Any] = []
        if query.get("sido"):
            filters.append("sido = ?")
            params.append(query["sido"])
        if query.get("sigungu"):
            filters.append("sigungu = ?")
            params.append(query["sigungu"])
        if query.get("business_status"):
            filters.append("business_status = ?")
            params.append(query["business_status"])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_region_status_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_region_status_mart is not built")
            cursor = con.execute(
                f"""
                SELECT *
                FROM station_region_status_mart
                {where}
                ORDER BY station_count DESC, sido, sigungu, business_status
                LIMIT ?
                """,
                [*params, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def station_unmatched(self, query: dict[str, str]) -> dict[str, Any]:
        page = max(int(query.get("page", "1")), 1)
        page_size = min(max(int(query.get("page_size", "50")), 1), 200)
        offset = (page - 1) * page_size
        filters = []
        params: list[Any] = []
        if query.get("sido"):
            filters.append("sido = ?")
            params.append(query["sido"])
        if query.get("sigungu"):
            filters.append("sigungu = ?")
            params.append(query["sigungu"])
        if query.get("business_status"):
            filters.append("business_status = ?")
            params.append(query["business_status"])
        if query.get("gap_reason"):
            filters.append("gap_reason = ?")
            params.append(query["gap_reason"])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_match_gap_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_match_gap_mart is not built")
            total = con.execute(f"SELECT COUNT(*) FROM station_match_gap_mart {where}", params).fetchone()[0]
            cursor = con.execute(
                f"""
                SELECT *
                FROM station_match_gap_mart
                {where}
                ORDER BY sido, sigungu, station_name
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "page": page, "page_size": page_size, "count": len(items), "total": total}
        finally:
            con.close()


    def station_route(self, path: str, query: dict[str, str]) -> dict[str, Any]:
        parts = [part for part in path.removeprefix("/api/stations/").split("/") if part]
        if not parts:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_STATION_ID", "station_id is required")
        station_id = parts[0]
        child = parts[1] if len(parts) > 1 else None
        if child == "status-events":
            return self.station_status_events(station_id, query)
        if child == "building-links":
            return self.station_building_links(station_id, query)
        if child == "permit-links":
            return self.station_permit_links(station_id, query)
        if child == "precision":
            return self.station_precision(station_id, query)
        if child:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "station child endpoint not found")
        return self.station_detail(station_id)


    def station_precision_quality(self) -> dict[str, Any]:
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_precision_quality_result"):
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "PRECISION_QUALITY_NOT_RUN",
                    "station_precision_quality_result is not built",
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
                FROM station_precision_quality_result
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
                FROM station_precision_quality_result
                GROUP BY severity, status
                ORDER BY severity, status
                """
            )
            summary_items = rows_to_dicts(summary_cursor)
            return {"items": items, "summary": summary_items, "count": len(items)}
        finally:
            con.close()


    def station_detail(self, station_id: str) -> dict[str, Any]:
        if not station_id:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_STATION_ID", "station_id is required")
        con = connect(read_only=True)
        try:
            source = "station_detail_mart" if table_exists(con, "station_detail_mart") else "station_search_mart"
            if not table_exists(con, source):
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "STATION_MART_NOT_BUILT",
                    f"{source} is not built because station source tables are not loaded yet",
                )
            cursor = con.execute(f"SELECT * FROM {source} WHERE station_id = ?", [station_id])
            rows = rows_to_dicts(cursor)
            if not rows:
                raise ApiError(HTTPStatus.NOT_FOUND, "STATION_NOT_FOUND", "station not found")
            return rows[0]
        finally:
            con.close()


    def station_status_events(self, station_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_status_event_mart"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_status_event_mart is not built")
            cursor = con.execute(
                """
                SELECT
                    station_id,
                    status_event_id,
                    source_row_number,
                    event_date,
                    event_year,
                    event_type_raw,
                    event_type_normalized,
                    business_type,
                    address_raw,
                    loaded_at
                FROM station_status_event_mart
                WHERE station_id = ?
                ORDER BY event_date DESC NULLS LAST, status_event_id DESC
                LIMIT ?
                """,
                [station_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def station_building_links(self, station_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_building_link_candidate"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_building_link_candidate is not built")
            cursor = con.execute(
                """
                SELECT
                    station_id,
                    pnu,
                    building_register_pk,
                    hub_table,
                    hub_address,
                    match_method,
                    match_confidence,
                    is_primary,
                    review_status,
                    CAST(matched_at AS VARCHAR) AS matched_at
                FROM station_building_link_candidate
                WHERE station_id = ?
                ORDER BY is_primary DESC, match_confidence DESC, hub_table, building_register_pk
                LIMIT ?
                """,
                [station_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def station_permit_links(self, station_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "100")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "station_permit_link_candidate"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "MART_NOT_BUILT", "station_permit_link_candidate is not built")
            cursor = con.execute(
                """
                SELECT
                    station_id,
                    permit_register_pk,
                    hub_table,
                    hub_address,
                    permit_date,
                    match_method,
                    match_confidence,
                    is_primary,
                    review_status,
                    CAST(matched_at AS VARCHAR) AS matched_at
                FROM station_permit_link_candidate
                WHERE station_id = ?
                ORDER BY is_primary DESC, match_confidence DESC, hub_table, permit_register_pk
                LIMIT ?
                """,
                [station_id, limit],
            )
            items = rows_to_dicts(cursor)
            return {"items": items, "count": len(items)}
        finally:
            con.close()


    def station_precision(self, station_id: str, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        con = connect(read_only=True)
        try:
            profile: dict[str, Any] | None = None
            pnu_candidates: list[dict[str, Any]] = []
            geocode_requests: list[dict[str, Any]] = []

            if table_exists(con, "station_address_precision_profile"):
                cursor = con.execute(
                    """
                    SELECT *
                    FROM station_address_precision_profile
                    WHERE station_id = ?
                    """,
                    [station_id],
                )
                rows = rows_to_dicts(cursor)
                profile = rows[0] if rows else None

            if table_exists(con, "station_pnu_candidate"):
                cursor = con.execute(
                    """
                    SELECT
                        station_id,
                        pnu,
                        match_method,
                        confidence,
                        is_primary,
                        candidate_rank,
                        source_provider,
                        hub_table,
                        hub_pk,
                        legal_dong_code,
                        land_type_code,
                        main_lot_no,
                        sub_lot_no,
                        confidence_band,
                        review_status,
                        created_at
                    FROM station_pnu_candidate
                    WHERE station_id = ?
                    ORDER BY is_primary DESC, candidate_rank, confidence DESC
                    LIMIT ?
                    """,
                    [station_id, limit],
                )
                pnu_candidates = rows_to_dicts(cursor)

            if table_exists(con, "station_geocode_request"):
                cursor = con.execute(
                    """
                    SELECT
                        request_id,
                        provider,
                        request_type,
                        request_keyword,
                        request_status,
                        http_status,
                        provider_error_code,
                        created_at,
                        completed_at
                    FROM station_geocode_request
                    WHERE station_id = ?
                    ORDER BY request_type, request_keyword
                    LIMIT ?
                    """,
                    [station_id, limit],
                )
                geocode_requests = rows_to_dicts(cursor)

            return {
                "profile": profile,
                "pnu_candidates": pnu_candidates,
                "geocode_requests": geocode_requests,
                "pnu_candidate_count": len(pnu_candidates),
                "geocode_request_count": len(geocode_requests),
            }
        finally:
            con.close()


