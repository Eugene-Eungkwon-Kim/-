from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import secrets
import re
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

import duckdb

try:
    from service_config import building_register_db, data_root, service_reports_dir
except ModuleNotFoundError:
    from backend.service_config import building_register_db, data_root, service_reports_dir

DEFAULT_DB_PATH = building_register_db()
ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = ROOT_DIR / "frontend" / "index.html"
DEFAULT_SERVICE_REPORTS_DIR = service_reports_dir()
try:
    from lib.auction_case_quality import classify_case_no, format_case_no_display
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    from lib.auction_case_quality import classify_case_no, format_case_no_display

VWORLD_MAP_KEY_ENV_NAMES = ("VWORLD_MAP_KEY", "VWORLD_API_KEY", "VWORLD_MAP_API_KEY")
MAP_LIBRARY_URLS = {
    "openlayers_script_url": "https://unpkg.com/ol/dist/ol.js",
    "openlayers_style_url": "https://unpkg.com/ol/ol.css",
    "openfree_olms_script_url": "https://unpkg.com/ol-mapbox-style/dist/olms.js",
}
DEFAULT_MAP_PROVIDERS = [
    (
        "VWORLD",
        True,
        10,
        "VWorld",
        "https://api.vworld.kr/req/wmts/1.0.0/{key}/Base/{z}/{y}/{x}.png",
        None,
        "VWorld",
        True,
        "VWORLD_MAP_KEY",
        "OPENFREEMAP",
    ),
    (
        "OPENFREEMAP",
        True,
        20,
        "OpenFreeMap",
        None,
        "https://tiles.openfreemap.org/styles/liberty",
        "OpenFreeMap",
        False,
        None,
        "INTERNAL",
    ),
    (
        "INTERNAL",
        True,
        90,
        "내부 좌표지도",
        None,
        None,
        "내부 좌표지도",
        False,
        None,
        None,
    ),
]


LABELS = {
    "site_category": {
        "OIL_STATION": "주유소",
        "CHARGING_STATION": "충전소",
        "HYBRID_FUEL_SITE": "복합시설",
        "LPG_CHARGING_STATION": "LPG 충전소",
        "CNG_CHARGING_STATION": "CNG 충전소",
        "LNG_CHARGING_STATION": "LNG 충전소",
        "LCNG_CHARGING_STATION": "LCNG 충전소",
        "HYDROGEN_CHARGING_STATION": "수소 충전소",
    },
    "business_status": {
        "ACTIVE_SOURCE_LISTED": "운영중",
        "READY": "확인 대기",
        "OPEN": "확인 필요",
        "IN_PROGRESS": "처리 중",
        "RESOLVED": "처리 완료",
    },
    "provider": {
        "OPINET": "오피넷",
        "KGS": "한국가스안전공사",
        "HUB": "건축HUB",
    },
}

CHARGING_SITE_TYPES = (
    "LPG_CHARGING_STATION",
    "CNG_CHARGING_STATION",
    "LNG_CHARGING_STATION",
    "LCNG_CHARGING_STATION",
    "HYDROGEN_CHARGING_STATION",
)

REVIEW_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED"}
ROLE_LEVELS = {"VIEWER": 10, "EXPORTER": 20, "OPERATOR": 30, "AUDITOR": 40, "ADMIN": 50}
EXPORT_DEFAULT_LIMIT = 5000
EXPORT_DAILY_DOWNLOAD_LIMIT = 20
EXPORT_DAILY_ROW_LIMIT = 50000
DEFAULT_EXPORT_TERMS_VERSION = "export-20260603-v1"
DEFAULT_ALLOWED_CORS_ORIGINS = {
    "http://127.0.0.1:8055",
    "http://localhost:8055",
    "null",
}

DB_CONNECT_LOCK = threading.RLock()


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    db_path = os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH)
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with DB_CONNECT_LOCK:
                # DuckDB rejects mixed read_only/read_write connections to the same file in one process.
                return duckdb.connect(db_path, read_only=read_only)
        except Exception as exc:
            last_error = exc
            time.sleep(0.12 * (attempt + 1))
    raise last_error or RuntimeError("DuckDB connection failed")


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    return (
        con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?
            """,
            [table_name],
        ).fetchone()[0]
        > 0
    )


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def semantic_column(con: duckdb.DuckDBPyConnection, table_name: str, semantic_name: str) -> str | None:
    if not table_exists(con, "column_dictionary"):
        return None
    row = con.execute(
        """
        SELECT raw_column_name
        FROM column_dictionary
        WHERE dataset_table = ?
          AND semantic_name = ?
        ORDER BY ordinal_position
        LIMIT 1
        """,
        [table_name, semantic_name],
    ).fetchone()
    return row[0] if row else None


def land_area_column(con: duckdb.DuckDBPyConnection, table_name: str) -> str | None:
    if not table_exists(con, "column_dictionary"):
        return None
    row = con.execute(
        """
        SELECT raw_column_name
        FROM column_dictionary
        WHERE dataset_table = ?
          AND (
            semantic_name IN ('land_area', '대지_면적')
            OR korean_name LIKE '%대지_면적%'
            OR korean_name LIKE '%대지 면적%'
          )
        ORDER BY
          CASE
            WHEN semantic_name = 'land_area' THEN 1
            WHEN semantic_name = '대지_면적' THEN 2
            ELSE 3
          END,
          ordinal_position
        LIMIT 1
        """,
        [table_name],
    ).fetchone()
    return row[0] if row else None


def rows_to_dicts(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def scalar(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None, default: Any = 0) -> Any:
    try:
        row = con.execute(sql, params or []).fetchone()
        return row[0] if row else default
    except Exception:
        return default


def scalar_if_table(con: duckdb.DuckDBPyConnection, table_name: str, sql: str, default: Any = 0) -> Any:
    return scalar(con, sql, default=default) if table_exists(con, table_name) else default


def grouped_rows_if_table(con: duckdb.DuckDBPyConnection, table_name: str, sql: str) -> list[dict[str, Any]]:
    return rows_to_dicts(con.execute(sql)) if table_exists(con, table_name) else []


def first_env_value(names: tuple[str, ...]) -> str:
    return next((os.environ.get(name, "").strip() for name in names if os.environ.get(name, "").strip()), "")


def ensure_map_provider_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_map_provider_config (
            provider_code VARCHAR PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            priority INTEGER NOT NULL DEFAULT 100,
            display_name VARCHAR NOT NULL,
            tile_url_template VARCHAR,
            style_url VARCHAR,
            attribution VARCHAR,
            requires_key BOOLEAN NOT NULL DEFAULT FALSE,
            key_env_name VARCHAR,
            fallback_provider_code VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_map_provider_health (
            check_id VARCHAR PRIMARY KEY,
            provider_code VARCHAR NOT NULL,
            check_status VARCHAR NOT NULL,
            http_status INTEGER,
            error_message VARCHAR,
            latency_ms DOUBLE,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    for provider in DEFAULT_MAP_PROVIDERS:
        con.execute(
            """
            INSERT INTO service_map_provider_config (
                provider_code, enabled, priority, display_name, tile_url_template,
                style_url, attribution, requires_key, key_env_name, fallback_provider_code
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM service_map_provider_config WHERE provider_code = ?
            )
            """,
            [*provider, provider[0]],
        )


def ensure_coordinate_quality_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS energy_site_coordinate_quality (
            energy_site_id VARCHAR PRIMARY KEY,
            latitude DOUBLE,
            longitude DOUBLE,
            coordinate_status VARCHAR NOT NULL,
            quality_score DOUBLE NOT NULL,
            issue_code VARCHAR,
            issue_message VARCHAR,
            source_provider VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def map_provider_config(con: duckdb.DuckDBPyConnection, requested_provider: str | None = None) -> dict[str, Any]:
    ensure_map_provider_tables(con)
    vworld_key = first_env_value(VWORLD_MAP_KEY_ENV_NAMES)
    provider_code = (requested_provider or "").strip().upper()
    if not provider_code:
        provider_code = "VWORLD" if vworld_key else "OPENFREEMAP"
    row = con.execute(
        """
        SELECT *
        FROM service_map_provider_config
        WHERE provider_code = ? AND enabled
        LIMIT 1
        """,
        [provider_code],
    ).fetchone()
    if not row:
        provider_code = "OPENFREEMAP"
        row = con.execute(
            """
            SELECT *
            FROM service_map_provider_config
            WHERE provider_code = 'OPENFREEMAP' AND enabled
            LIMIT 1
            """
        ).fetchone()
    columns = [item[0] for item in con.description]
    config = dict(zip(columns, row)) if row else {}
    requires_key = bool(config.get("requires_key"))
    key_configured = bool(vworld_key) if provider_code == "VWORLD" else not requires_key
    return {
        "provider": provider_code,
        "enabled": bool(config.get("enabled", True)),
        "library": "OPENLAYERS",
        "display_name": config.get("display_name") or provider_code,
        "attribution": config.get("attribution") or config.get("display_name") or provider_code,
        "tile_mode": "WMTS" if provider_code == "VWORLD" else "STYLE",
        "requires_key": requires_key,
        "key_configured": key_configured,
        "health_check_required": provider_code != "INTERNAL",
        "fallback": config.get("fallback_provider_code") or "INTERNAL",
        "fallback_provider": config.get("fallback_provider_code") or "INTERNAL",
        "vworld_key": vworld_key,
        "vworld_tile_url_template": config.get("tile_url_template") or DEFAULT_MAP_PROVIDERS[0][4],
        "openfree_style_url": config.get("style_url") or DEFAULT_MAP_PROVIDERS[1][5],
        **MAP_LIBRARY_URLS,
    }


def fallback_map_provider_config(requested_provider: str | None = None) -> dict[str, Any]:
    vworld_key = first_env_value(VWORLD_MAP_KEY_ENV_NAMES)
    provider_code = (requested_provider or "").strip().upper() or ("VWORLD" if vworld_key else "OPENFREEMAP")
    provider = next((item for item in DEFAULT_MAP_PROVIDERS if item[0] == provider_code), DEFAULT_MAP_PROVIDERS[1])
    requires_key = bool(provider[7])
    return {
        "provider": provider[0],
        "enabled": bool(provider[1]),
        "library": "OPENLAYERS",
        "display_name": provider[3],
        "attribution": provider[6],
        "tile_mode": "WMTS" if provider[0] == "VWORLD" else "STYLE",
        "requires_key": requires_key,
        "key_configured": bool(vworld_key) if provider[0] == "VWORLD" else not requires_key,
        "health_check_required": provider[0] != "INTERNAL",
        "fallback": provider[9] or "INTERNAL",
        "fallback_provider": provider[9] or "INTERNAL",
        "vworld_key": vworld_key,
        "vworld_tile_url_template": provider[4] or DEFAULT_MAP_PROVIDERS[0][4],
        "openfree_style_url": provider[5] or DEFAULT_MAP_PROVIDERS[1][5],
        "source_status": "DB_LOCKED_FALLBACK",
        **MAP_LIBRARY_URLS,
    }


def page_window(query: dict[str, str], default_size: int = 50, max_size: int = 200) -> tuple[int, int, int]:
    page = max(int(query.get("page", "1")), 1)
    page_size = min(max(int(query.get("page_size", str(default_size))), 1), max_size)
    return page, page_size, (page - 1) * page_size


def empty_page(page: int, page_size: int, **extra: Any) -> dict[str, Any]:
    return {"items": [], "page": page, "page_size": page_size, "count": 0, "total": 0, **extra}


def where_from(filters: list[str]) -> str:
    return "WHERE " + " AND ".join(filters) if filters else ""


def normalize_business_status(value: str) -> str:
    status = value.strip()
    return {
        "영업": "ACTIVE_SOURCE_LISTED",
        "운영중": "ACTIVE_SOURCE_LISTED",
        "운영": "ACTIVE_SOURCE_LISTED",
    }.get(status, status)


REGION_QUERY_ALIASES = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def search_query_variants(value: str) -> list[str]:
    base = " ".join(str(value or "").split())
    if not base:
        return []
    variants = [base]
    compact = re.sub(r"\s+", "", base)
    if compact != base:
        variants.append(compact)
    tokens = base.split()
    if tokens and tokens[0] in REGION_QUERY_ALIASES:
        expanded = " ".join([REGION_QUERY_ALIASES[tokens[0]], *tokens[1:]])
        variants.append(expanded)
        variants.append(re.sub(r"\s+", "", expanded))
    return list(dict.fromkeys(item for item in variants if item))


def service_status_expr(column: str = "business_status") -> str:
    return f"""
        CASE
            WHEN {column} IN ('ACTIVE_SOURCE_LISTED', '신규등록', '영업', '영업중', '운영중') THEN 'OPERATING'
            WHEN {column} = '휴업' THEN 'SUSPENDED'
            WHEN {column} IN ('폐업', '등록취소') THEN 'CLOSED'
            ELSE 'UNKNOWN'
        END
    """


def service_status_filter(value: str, column: str = "business_status") -> str | None:
    status = value.strip().upper()
    expr = service_status_expr(column)
    if status in {"OPERATING", "ACTIVE", "영업", "영업중", "운영", "운영중"}:
        return f"{expr} = 'OPERATING'"
    if status in {"SUSPENDED", "PAUSED", "휴업"}:
        return f"{expr} = 'SUSPENDED'"
    if status in {"CLOSED", "INACTIVE", "폐업", "등록취소"}:
        return f"{expr} = 'CLOSED'"
    if status in {"UNKNOWN", "확인필요"}:
        return f"{expr} = 'UNKNOWN'"
    return None


def bool_query(value: str) -> bool | None:
    token = value.strip().lower()
    if token in {"1", "true", "yes", "y", "있음", "연결됨"}:
        return True
    if token in {"0", "false", "no", "n", "없음", "미연결"}:
        return False
    return None


def auction_table_name(con: duckdb.DuckDBPyConnection) -> str | None:
    for table_name in (
        "energy_site_auction_event",
        "energy_site_auction_history_confirmation",
        "energy_site_auction_history",
        "energy_site_current_auction_status",
        "onbid_energy_site_event",
        "auction_event",
    ):
        if table_exists(con, table_name) and "energy_site_id" in table_columns(con, table_name):
            return table_name
    return None


def pick_case_no_from_payload(raw_payload: Any) -> str:
    if not raw_payload:
        return ""
    try:
        payload = json.loads(str(raw_payload)) if isinstance(raw_payload, str) else dict(raw_payload)
    except Exception:
        return ""
    keys = [
        "case_no",
        "case_number",
        "auction_case_no",
        "court_case_no",
        "사건번호",
        "caseNo",
        "caseNumber",
        "courtCaseNo",
        "pbctNo",
        "pbct_no",
        "pbctNsq",
        "onbidPbancNo",
        "auctionNo",
        "case_id",
        "case_seq_no",
    ]
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else None
        if not value:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def resolve_case_no_display(case_no: Any, source_provider: Any, raw_payload: Any) -> str:
    resolved = format_case_no_display(case_no, source_provider)
    if resolved:
        return resolved
    payload_case_no = pick_case_no_from_payload(raw_payload)
    if payload_case_no:
        return format_case_no_display(payload_case_no, source_provider)
    return ""


def energy_site_filters(query: dict[str, str], column_map: dict[str, str], site_alias: str = "m") -> tuple[str, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    for key, column in column_map.items():
        if query.get(key):
            filters.append(f"{column} = ?")
            params.append(normalize_business_status(query[key]) if key == "business_status" else query[key])
    if query.get("fuel_type"):
        filters.append(
            f"""
            EXISTS (
                SELECT 1
                FROM energy_site_fuel_type f
                WHERE f.energy_site_id = {site_alias}.energy_site_id
                  AND f.fuel_type = ?
            )
            """
        )
        params.append(query["fuel_type"])
    return where_from(filters), params


def energy_site_search_where(
    query: dict[str, str],
    alias: str = "",
    auction_table: str | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> tuple[str, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    prefix = f"{alias}." if alias else ""
    site_id_col = f"{prefix}energy_site_id"
    business_col = f"{prefix}business_status"
    if query.get("q"):
        q_filters = []
        for variant in search_query_variants(query["q"]):
            q_filters.append(
                f"""(
                    {prefix}site_name ILIKE ?
                    OR {prefix}address_raw ILIKE ?
                    OR regexp_replace(coalesce({prefix}address_raw, ''), '\\s+', '', 'g') ILIKE ?
                )"""
            )
            params.extend([f"%{variant}%", f"%{variant}%", f"%{variant}%"])
        if q_filters:
            filters.append("(" + " OR ".join(q_filters) + ")")
    if query.get("site_category"):
        category = query["site_category"].strip()
        if category == "CHARGING_STATION":
            placeholders = ",".join(["?"] * len(CHARGING_SITE_TYPES))
            filters.append(
                f"({prefix}site_category = ? OR {prefix}site_type IN ({placeholders}))"
            )
            params.extend([category, *CHARGING_SITE_TYPES])
        elif category in CHARGING_SITE_TYPES:
            filters.append(f"{prefix}site_type = ?")
            params.append(category)
        else:
            filters.append(f"{prefix}site_category = ?")
            params.append(category)
    if query.get("site_type"):
        filters.append(f"{prefix}site_type = ?")
        params.append(query["site_type"])
    for key in ["pnu", "sido", "sigungu"]:
        if query.get(key):
            filters.append(f"{prefix}{key} = ?")
            params.append(query[key])
    if query.get("business_status"):
        filters.append(f"{business_col} = ?")
        params.append(normalize_business_status(query["business_status"]))
    # Accept both canonical `case_no` and front-end UI name `auction_case_no`.
    raw_case_no = (query.get("case_no") or query.get("auction_case_no") or "").strip()
    if raw_case_no:
        case_no = raw_case_no.replace(" ", "")
        if auction_table and con:
            candidate_cols = []
            for candidate in [
                "case_no",
                "case_number",
                "auction_case_no",
                "court_case_no",
                "사건번호",
                "caseId",
                "case_id",
            ]:
                column = first_existing_column(con, auction_table, [candidate])
                if column and column not in candidate_cols:
                    candidate_cols.append(column)
            if candidate_cols:
                or_expr = " OR ".join(
                    f"(TRIM(CAST(a.{quote_ident(column)} AS VARCHAR)) = ? OR REPLACE(TRIM(CAST(a.{quote_ident(column)} AS VARCHAR)), ' ', '') = ?)" for column in candidate_cols
                )
                filters.append(
                    f"EXISTS (SELECT 1 FROM {quote_ident(auction_table)} a WHERE a.energy_site_id = {site_id_col} AND ({or_expr}))"
                )
                case_no_candidates = [case_no] * len(candidate_cols)
                # Keep both original and whitespace-stripped variants for resilient matching.
                params.extend([item for pair in zip(case_no_candidates, case_no_candidates) for item in pair])
            else:
                filters.append("1 = 0")
        else:
            filters.append("1 = 0")
    if query.get("service_status"):
        service_filter = service_status_filter(query["service_status"], business_col)
        if service_filter:
            filters.append(service_filter)
    if query.get("fuel_type"):
        filters.append(f"{prefix}fuel_types ILIKE ?")
        params.append(f"%{query['fuel_type']}%")
    if query.get("matched"):
        matched = query["matched"].lower()
        if matched in {"1", "true", "yes", "y"}:
            filters.append(f"{prefix}building_review_status IN ('AUTO_CONFIRMED', 'CONFIRMED')")
        elif matched in {"0", "false", "no", "n"}:
            filters.append(f"({prefix}building_review_status IS NULL OR {prefix}building_review_status NOT IN ('AUTO_CONFIRMED', 'CONFIRMED'))")
    related_tables = {
        "has_storage": "energy_site_storage_capacity",
        "has_equipment": "energy_site_equipment",
        "has_facility": "energy_site_facility_summary",
        "has_land": "energy_site_land_link",
    }
    for key, table_name in related_tables.items():
        requested = bool_query(query.get(key, "")) if query.get(key) else None
        if requested is True:
            filters.append(f"EXISTS (SELECT 1 FROM {table_name} x WHERE x.energy_site_id = {site_id_col})")
        elif requested is False:
            filters.append(f"NOT EXISTS (SELECT 1 FROM {table_name} x WHERE x.energy_site_id = {site_id_col})")
    if query.get("has_auction") is not None:
        requested = bool_query(query["has_auction"])
        if requested is True:
            if auction_table:
                filters.append(f"EXISTS (SELECT 1 FROM {quote_ident(auction_table)} a WHERE a.energy_site_id = {site_id_col})")
            else:
                filters.append("1 = 0")
        elif requested is False:
            if auction_table:
                filters.append(f"NOT EXISTS (SELECT 1 FROM {quote_ident(auction_table)} a WHERE a.energy_site_id = {site_id_col})")
    if query.get("has_current_auction") is not None:
        requested_current = bool_query(query["has_current_auction"])
        has_current_table = bool(con) and table_exists(con, "energy_site_current_auction_status")
        if requested_current is True:
            if has_current_table:
                filters.append(
                    (
                        "EXISTS (SELECT 1 FROM energy_site_current_auction_status c "
                        "WHERE c.energy_site_id = {site_id_col} AND COALESCE(c.case_status, '') NOT IN "
                        "('', 'NO_CURRENT_CASE', 'NO_CASE', 'NONE', 'NOT_FOUND', 'UNVERIFIED_PROVIDER_SEARCH_REQUIRED') )"
                    ).format(site_id_col=site_id_col)
                )
            else:
                filters.append("1 = 0")
        elif requested_current is False:
            if has_current_table:
                filters.append(
                    (
                        "NOT EXISTS (SELECT 1 FROM energy_site_current_auction_status c "
                        "WHERE c.energy_site_id = {site_id_col} AND COALESCE(c.case_status, '') NOT IN "
                        "('', 'NO_CURRENT_CASE', 'NO_CASE', 'NONE', 'NOT_FOUND', 'UNVERIFIED_PROVIDER_SEARCH_REQUIRED') )"
                    ).format(site_id_col=site_id_col)
                )
    return where_from(filters), params


def label_value(group: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    return LABELS.get(group, {}).get(str(value), str(value))


def review_id_for(item: dict[str, Any]) -> str:
    return "::".join(str(item.get(key) or "") for key in ["energy_site_id", "issue_type", "priority"])


def split_review_id(review_id: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    parts = review_id.split("::", 2)
    energy_site_id = payload.get("energy_site_id") or (parts[0] if parts else "")
    issue_type = payload.get("issue_type") or (parts[1] if len(parts) > 1 else "")
    priority = payload.get("priority") or (parts[2] if len(parts) > 2 else "")
    return str(energy_site_id), str(issue_type), str(priority)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def auth_required() -> bool:
    configured = os.environ.get("SERVICE_REQUIRE_AUTH", "").strip().lower()
    if configured:
        return configured in {"1", "true", "yes", "y"}
    bind_host = os.environ.get("SERVICE_BIND_HOST", "127.0.0.1").strip().lower()
    return bind_host not in {"127.0.0.1", "localhost", "::1"}


def has_enabled_admin_token(con: duckdb.DuckDBPyConnection) -> bool:
    if not table_exists(con, "service_user_token"):
        return False
    return bool(
        scalar(
            con,
            """
            SELECT COUNT(*)
            FROM service_user_token
            WHERE enabled
              AND role_code = 'ADMIN'
              AND revoked_at IS NULL
            """,
        )
    )


def role_allows(role_code: str, required_role: str) -> bool:
    return ROLE_LEVELS.get(role_code.upper(), 0) >= ROLE_LEVELS.get(required_role.upper(), 999)


def default_actor() -> dict[str, Any]:
    return {
        "actor_id": "local-admin",
        "role_code": "ADMIN",
        "display_name": "Local Admin",
        "auth_required": False,
    }


def table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    if not table_exists(con, table_name):
        return set()
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchall()
    return {str(row[0]) for row in rows}


def first_existing_column(con: duckdb.DuckDBPyConnection, table_name: str, candidates: list[str]) -> str | None:
    columns = table_columns(con, table_name)
    by_lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in columns:
            return candidate
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]
    return None


def auction_column_expr(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    candidates: list[str],
    alias: str = "",
    default: str = "NULL",
) -> tuple[str, str | None]:
    column = first_existing_column(con, table_name, candidates)
    if not column:
        return default, None
    prefix = f"{alias}." if alias else ""
    return f"CAST({prefix}{quote_ident(column)} AS VARCHAR)", column


def ensure_columns(con: duckdb.DuckDBPyConnection, table_name: str, columns: dict[str, str]) -> None:
    existing = table_columns(con, table_name)
    for column_name, column_type in columns.items():
        if column_name not in existing:
            con.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            existing.add(column_name)


def ensure_service_security_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_user_token (
            token_id VARCHAR PRIMARY KEY,
            token_hash VARCHAR NOT NULL UNIQUE,
            display_name VARCHAR NOT NULL,
            role_code VARCHAR NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )
        """
    )
    ensure_columns(
        con,
        "service_user_token",
        {
            "created_by": "VARCHAR",
            "revoked_at": "TIMESTAMP",
            "revoked_by": "VARCHAR",
            "last_rotated_at": "TIMESTAMP",
            "note": "VARCHAR",
        },
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_audit_event (
            event_id VARCHAR PRIMARY KEY,
            request_id VARCHAR,
            actor_id VARCHAR,
            actor_role VARCHAR,
            event_type VARCHAR NOT NULL,
            target_type VARCHAR,
            target_id VARCHAR,
            event_status VARCHAR NOT NULL,
            detail_json VARCHAR,
            ip_address VARCHAR,
            user_agent VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    admin_token = os.environ.get("SERVICE_ADMIN_TOKEN", "").strip()
    if admin_token:
        con.execute(
            """
            INSERT INTO service_user_token (token_id, token_hash, display_name, role_code)
            SELECT ?, ?, '환경변수 관리자', 'ADMIN'
            WHERE NOT EXISTS (
                SELECT 1 FROM service_user_token WHERE token_hash = ?
            )
            """,
            [str(uuid.uuid4()), hash_token(admin_token), hash_token(admin_token)],
        )


def ensure_export_audit_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_export_audit (
            request_id VARCHAR PRIMARY KEY,
            export_type VARCHAR NOT NULL,
            query_json VARCHAR,
            row_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_columns(
        con,
        "service_export_audit",
        {
            "created_at": "TIMESTAMP",
            "actor_id": "VARCHAR",
            "actor_role": "VARCHAR",
            "ip_address": "VARCHAR",
            "user_agent": "VARCHAR",
            "export_status": "VARCHAR",
            "blocked_reason": "VARCHAR",
            "terms_version": "VARCHAR",
            "approval_id": "VARCHAR",
            "file_manifest_id": "VARCHAR",
        },
    )
    columns = table_columns(con, "service_export_audit")
    if "exported_at" in columns:
        con.execute("UPDATE service_export_audit SET created_at = COALESCE(created_at, exported_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")
    else:
        con.execute("UPDATE service_export_audit SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")


def ensure_full_commercialization_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_terms_version (
            terms_version VARCHAR PRIMARY KEY,
            terms_type VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            body_md VARCHAR NOT NULL,
            effective_from TIMESTAMP NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        INSERT INTO service_terms_version (
            terms_version, terms_type, title, body_md, effective_from, enabled
        )
        SELECT ?, 'EXPORT', 'CSV 반출 및 데이터 사용 약관',
               'CSV 반출 자료는 허가된 사용자에게만 제공되며 재배포, 재판매, 제3자 제공은 계약과 원천 데이터 라이선스 범위 내에서만 가능합니다.',
               TIMESTAMP '2026-06-03 00:00:00', TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM service_terms_version WHERE terms_version = ?
        )
        """,
        [DEFAULT_EXPORT_TERMS_VERSION, DEFAULT_EXPORT_TERMS_VERSION],
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_terms_acceptance (
            acceptance_id VARCHAR PRIMARY KEY,
            actor_id VARCHAR NOT NULL,
            terms_version VARCHAR NOT NULL,
            accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR,
            user_agent VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_export_request (
            approval_id VARCHAR PRIMARY KEY,
            request_id VARCHAR NOT NULL,
            actor_id VARCHAR NOT NULL,
            export_type VARCHAR NOT NULL,
            query_json VARCHAR NOT NULL,
            requested_row_count BIGINT,
            request_reason VARCHAR,
            approval_status VARCHAR NOT NULL,
            approved_by VARCHAR,
            approved_at TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_export_file_manifest (
            file_manifest_id VARCHAR PRIMARY KEY,
            request_id VARCHAR NOT NULL,
            actor_id VARCHAR NOT NULL,
            export_type VARCHAR NOT NULL,
            row_count BIGINT NOT NULL,
            sha256_hash VARCHAR,
            watermark_text VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_monitor_event (
            event_id VARCHAR PRIMARY KEY,
            check_name VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            event_status VARCHAR NOT NULL,
            message VARCHAR NOT NULL,
            detail_json VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_restore_rehearsal (
            rehearsal_id VARCHAR PRIMARY KEY,
            source_backup_path VARCHAR NOT NULL,
            target_db_path VARCHAR NOT NULL,
            run_status VARCHAR NOT NULL,
            readyz_status VARCHAR,
            elapsed_ms DOUBLE,
            error_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_license_gate (
            gate_id VARCHAR PRIMARY KEY,
            source_name VARCHAR NOT NULL,
            source_type VARCHAR NOT NULL,
            commercial_status VARCHAR NOT NULL,
            evidence_path VARCHAR,
            reviewer VARCHAR,
            reviewed_at TIMESTAMP,
            note VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_launch_gate_check (
            check_id VARCHAR PRIMARY KEY,
            check_group VARCHAR NOT NULL,
            check_name VARCHAR NOT NULL,
            check_status VARCHAR NOT NULL,
            required_for_100 BOOLEAN NOT NULL DEFAULT TRUE,
            evidence_path VARCHAR,
            waiver_reason VARCHAR,
            checked_by VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detail_json VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_launch_approval (
            approval_id VARCHAR PRIMARY KEY,
            approval_status VARCHAR NOT NULL,
            target_version VARCHAR,
            approved_by VARCHAR,
            approved_at TIMESTAMP,
            go_live_window VARCHAR,
            rollback_plan_path VARCHAR,
            approval_note VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    for source_name, source_type, status, note in [
        ("공공데이터포털 주유소/충전소 원천", "DATA", "PENDING", "상용 제공 범위 최종 확인 필요"),
        ("건축HUB 건축물관리대장", "DATA", "PENDING", "재가공/서비스 제공 범위 확인 필요"),
        ("OpenFreeMap/OpenStreetMap 지도", "MAP", "APPROVED", "attribution 표시 조건 유지"),
        ("VWorld 지도/주소 API", "API", "PENDING", "운영키와 이용조건 확인 필요"),
        ("CSV 반출 약관", "TERMS", "APPROVED", DEFAULT_EXPORT_TERMS_VERSION),
    ]:
        con.execute(
            """
            INSERT INTO service_license_gate (
                gate_id, source_name, source_type, commercial_status, note
            )
            SELECT ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM service_license_gate WHERE source_name = ?
            )
            """,
            [str(uuid.uuid4()), source_name, source_type, status, note, source_name],
        )


def ensure_operational_tables(con: duckdb.DuckDBPyConnection) -> None:
    ensure_service_security_tables(con)
    ensure_export_audit_table(con)
    ensure_full_commercialization_tables(con)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_backup_run (
            backup_id VARCHAR PRIMARY KEY,
            source_db_path VARCHAR NOT NULL,
            backup_path VARCHAR NOT NULL,
            file_size_bytes BIGINT,
            run_status VARCHAR NOT NULL,
            error_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_columns(
        con,
        "service_backup_run",
        {
            "sha256_hash": "VARCHAR",
            "validation_status": "VARCHAR",
            "validation_detail_json": "VARCHAR",
            "duration_ms": "DOUBLE",
            "maintenance_started_at": "TIMESTAMP",
            "maintenance_finished_at": "TIMESTAMP",
        },
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS service_refresh_run (
            run_id VARCHAR PRIMARY KEY,
            run_mode VARCHAR NOT NULL,
            run_status VARCHAR NOT NULL,
            step_name VARCHAR,
            detail_json VARCHAR,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
        """
    )


class MvpHandler(BaseHTTPRequestHandler):
    server_version = "GasStationMvpApi/0.1"

    def do_GET(self) -> None:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        try:
            parsed = urlparse(self.path)
            query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
            if parsed.path == "/":
                self.serve_index()
                return
            actor = self.authenticate("GET", parsed.path, request_id)
            if parsed.path == "/api/energy-sites/export.csv":
                self.energy_site_export_csv(query, request_id, actor)
                return
            if parsed.path == "/api/admin/platform-action-queue/file.csv":
                self.platform_action_queue_file_csv(query, request_id, actor)
                return
            if parsed.path == "/api/admin/g3-g5-workpack-index/file.csv":
                self.g3_g5_workpack_file_csv(query, request_id, actor)
                return
            if parsed.path == "/api/admin/revenue-workboard-result-preflight/file.csv":
                self.revenue_workboard_result_preflight_csv(query)
                return
            if parsed.path == "/api/admin/planning-workboard-result-preflight/file.csv":
                self.planning_workboard_result_preflight_csv(query)
                return
            if parsed.path == "/api/admin/minimum-batch-operator-preflight/file.csv":
                self.minimum_batch_operator_preflight_csv(query)
                return
            if parsed.path == "/api/admin/auction-first-run-priority-pack/file.csv":
                self.auction_first_run_priority_pack_file_csv(query, request_id, actor)
                return
            if parsed.path == "/api/admin/auction-next-priority-result-pack/file.csv":
                self.auction_next_priority_result_pack_file_csv(query, request_id, actor)
                return
            routes = {
                "/api/healthz": lambda: self.healthz(),
                "/api/readyz": lambda: self.readyz(),
                "/api/qa/diagnostics": lambda: self.qa_diagnostics(),
                "/api/config/maps": lambda: self.map_config(),
                "/api/datasets/catalog": lambda: self.dataset_catalog(query),
                "/api/columns/service-fields": lambda: self.service_fields(query),
                "/api/quality/checks": lambda: self.quality_checks(),
                "/api/admin/auth/me": lambda: {"actor": self.actor_public(actor)},
                "/api/admin/audit-events": lambda: self.audit_event_items(query),
                "/api/admin/backup-runs": lambda: self.backup_run_items(query),
                "/api/admin/export-audits": lambda: self.export_audit_items(query),
                "/api/admin/export-requests": lambda: self.export_request_items(query),
                "/api/admin/license-gates": lambda: self.license_gate_items(query),
                "/api/admin/launch-approval": lambda: self.launch_approval_items(query),
                "/api/admin/launch-gates": lambda: self.launch_gate_items(query),
                "/api/admin/coordinate-uplift-candidates": lambda: self.coordinate_uplift_candidate_items(query),
                "/api/admin/auction-case-resolution-queue": lambda: self.auction_case_resolution_queue_items(query),
                "/api/admin/current-auction-search-queue": lambda: self.current_auction_search_queue_items(query),
                "/api/admin/current-auction-reference-candidates": lambda: self.current_auction_reference_candidate_items(query),
                "/api/admin/platform-action-queue": lambda: self.platform_action_queue_items(query),
                "/api/admin/completion-execution-board": lambda: self.completion_execution_board_items(query),
                "/api/admin/threshold-execution-board": lambda: self.threshold_execution_board_items(query),
                "/api/admin/threshold-gate-runner-plan": lambda: self.threshold_gate_runner_plan_items(query),
                "/api/admin/threshold-result-workpack": lambda: self.threshold_result_workpack_items(query),
                "/api/admin/external-impact-priority": lambda: self.external_impact_priority_items(query),
                "/api/admin/completion-execution-ledger": lambda: self.completion_execution_ledger_items(query),
                "/api/admin/completion-input-gap": lambda: self.completion_input_gap_items(query),
                "/api/admin/location-land-building-gap": lambda: self.location_land_building_gap_items(query),
                "/api/admin/g3-g5-workpack-index": lambda: self.g3_g5_workpack_index_items(query),
                "/api/admin/external-dependency-blockers": lambda: self.external_dependency_blocker_items(query),
                "/api/admin/external-source-readiness": lambda: self.external_source_readiness(),
                "/api/admin/external-provider-session-plan": lambda: self.external_provider_session_plan_items(query),
                "/api/admin/auction-provider-access-preflight": lambda: self.auction_provider_access_preflight_items(query),
                "/api/admin/auction-provider-session-launcher": lambda: self.auction_provider_session_launcher_items(query),
                "/api/admin/auction-provider-browser-workboard": lambda: self.auction_provider_browser_workboard_items(query),
                "/api/admin/auction-first-run-priority-pack": lambda: self.auction_first_run_priority_pack_items(query),
                "/api/admin/auction-first-run-result-status": lambda: self.auction_first_run_result_status(query),
                "/api/admin/auction-next-priority-result-pack": lambda: self.auction_next_priority_result_pack_items(query),
                "/api/admin/auction-next-priority-result-status": lambda: self.auction_next_priority_result_status(query),
                "/api/admin/revenue-input-workboard": lambda: self.revenue_input_workboard_items(query),
                "/api/admin/revenue-workboard-result-preflight": lambda: self.revenue_workboard_result_preflight_items(query),
                "/api/admin/planning-input-workboard": lambda: self.planning_input_workboard_items(query),
                "/api/admin/planning-workboard-result-preflight": lambda: self.planning_workboard_result_preflight_items(query),
                "/api/admin/geocode-api-key-preflight": lambda: self.geocode_api_key_preflight_items(query),
                "/api/admin/pnu-geocode-priority-pack": lambda: self.pnu_geocode_priority_pack_items(query),
                "/api/admin/pnu-geocode-queue-seed": lambda: self.pnu_geocode_queue_seed_items(query),
                "/api/admin/p0-geocode-execution-monitor": lambda: self.p0_geocode_execution_monitor_items(query),
                "/api/admin/auction-provider-workbench": lambda: self.auction_provider_workbench_items(query),
                "/api/admin/auction-provider-intake-preflight": lambda: self.auction_provider_intake_preflight_items(query),
                "/api/admin/geocode-intake-preflight": lambda: self.geocode_intake_preflight_items(query),
                "/api/admin/external-workpack-manifest": lambda: self.external_workpack_manifest_items(query),
                "/api/admin/external-intake-status": lambda: self.external_intake_status_items(query),
                "/api/admin/external-result-file-scan": lambda: self.external_result_file_scan_items(query),
                "/api/admin/result-file-execution-plan": lambda: self.result_file_execution_plan_items(query),
                "/api/admin/external-result-contract-audit": lambda: self.external_result_contract_audit_items(query),
                "/api/admin/next-input-operator-brief": lambda: self.next_input_operator_brief_items(query),
                "/api/admin/100pct-control-tower": lambda: self.control_tower_100pct_items(query),
                "/api/admin/gate-pass-gap-projection": lambda: self.gate_pass_gap_projection_items(query),
                "/api/admin/gate-pass-minimum-batch-queue": lambda: self.gate_pass_minimum_batch_queue_items(query),
                "/api/admin/next-execution-priority-pack": lambda: self.next_execution_priority_pack_items(query),
                "/api/admin/minimum-batch-operator-preflight": lambda: self.minimum_batch_operator_preflight_items(query),
                "/api/admin/minimum-batch-execution-plan": lambda: self.minimum_batch_execution_plan_items(query),
                "/api/admin/unsafe-db-readers": lambda: self.unsafe_db_reader_process_items(query),
                "/api/admin/platform-completion-gates": lambda: self.platform_completion_gate_items(query),
                "/api/admin/platform-coverage-snapshots": lambda: self.platform_coverage_snapshot_items(query),
                "/api/admin/map-provider-status": lambda: self.map_provider_status(),
                "/api/admin/monitor-events": lambda: self.monitor_event_items(query),
                "/api/admin/ops-dashboard": lambda: self.ops_dashboard(),
                "/api/admin/refresh-runs": lambda: self.refresh_run_items(query),
                "/api/admin/review-items": lambda: self.energy_site_review_queue(query),
                "/api/admin/terms/acceptances": lambda: self.terms_acceptance_items(query),
                "/api/admin/tokens": lambda: self.token_items(query),
                "/api/terms/export/current": lambda: self.current_export_terms(actor),
                "/api/energy-sites/summary": lambda: self.energy_site_summary(),
                "/api/energy-sites/regions": lambda: self.energy_site_regions(query),
                "/api/energy-sites/search": lambda: self.energy_site_search(query),
                "/api/energy-sites/coordinate-quality": lambda: self.energy_site_coordinate_quality(query),
                "/api/energy-sites/quality": lambda: self.energy_site_quality(),
                "/api/energy-sites/precision-quality": lambda: self.energy_site_precision_quality(),
                "/api/energy-sites/review-queue": lambda: self.energy_site_review_queue(query),
                "/api/energy-sites/geocode-requests": lambda: self.energy_site_geocode_requests(query),
                "/api/energy-sites/hub-match-stats": lambda: self.energy_site_hub_match_stats(),
                "/api/stations/precision-quality": lambda: self.station_precision_quality(),
                "/api/stations/summary": lambda: self.station_summary(),
                "/api/stations/regions": lambda: self.station_regions(query),
                "/api/stations/unmatched": lambda: self.station_unmatched(query),
                "/api/stations/search": lambda: self.station_search(query),
            }
            if parsed.path in routes:
                payload = routes[parsed.path]()
            elif parsed.path.startswith("/api/energy-sites/"):
                payload = self.energy_site_route(parsed.path, query)
            elif parsed.path.startswith("/api/stations/"):
                payload = self.station_route(parsed.path, query)
            else:
                raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")
            self.json_response(
                HTTPStatus.OK,
                {
                    "data": payload,
                    "meta": {
                        "request_id": request_id,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "actor": self.actor_public(actor),
                    },
                },
            )
        except ApiError as exc:
            self.json_response(
                exc.status,
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    },
                    "meta": {"request_id": request_id},
                },
            )
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            self.internal_error_response(request_id, exc)

    def do_POST(self) -> None:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        try:
            parsed = urlparse(self.path)
            actor = self.authenticate("POST", parsed.path, request_id)
            body = self.read_json_body()
            payload: dict[str, Any]
            if parsed.path == "/api/admin/tokens":
                payload = self.create_token(body, actor, request_id)
            elif parsed.path.startswith("/api/admin/tokens/") and parsed.path.endswith("/rotate"):
                token_id = unquote(parsed.path.split("/")[-2])
                payload = self.rotate_token(token_id, actor, request_id)
            elif parsed.path.startswith("/api/admin/tokens/") and parsed.path.endswith("/revoke"):
                token_id = unquote(parsed.path.split("/")[-2])
                payload = self.revoke_token(token_id, actor, request_id)
            elif parsed.path == "/api/terms/export/accept":
                payload = self.accept_export_terms(body, actor, request_id)
            elif parsed.path == "/api/export-requests":
                payload = self.create_export_request(body, actor, request_id)
            elif parsed.path.startswith("/api/admin/export-requests/") and parsed.path.endswith("/approve"):
                approval_id = unquote(parsed.path.split("/")[-2])
                payload = self.approve_export_request(approval_id, body, actor, request_id)
            elif parsed.path.startswith("/api/admin/export-requests/") and parsed.path.endswith("/reject"):
                approval_id = unquote(parsed.path.split("/")[-2])
                payload = self.reject_export_request(approval_id, body, actor, request_id)
            elif parsed.path == "/api/admin/launch-gates/run":
                payload = self.run_launch_gate_checks(actor, request_id)
            elif parsed.path == "/api/admin/launch-approval":
                payload = self.create_launch_approval(body, actor, request_id)
            elif parsed.path.startswith("/api/admin/launch-approval/") and parsed.path.endswith("/approve"):
                approval_id = unquote(parsed.path.split("/")[-2])
                payload = self.update_launch_approval(approval_id, "APPROVED", body, actor, request_id)
            elif parsed.path.startswith("/api/admin/launch-approval/") and parsed.path.endswith("/reject"):
                approval_id = unquote(parsed.path.split("/")[-2])
                payload = self.update_launch_approval(approval_id, "REJECTED", body, actor, request_id)
            elif parsed.path.startswith("/api/admin/monitor-events/") and parsed.path.endswith("/ack"):
                event_id = unquote(parsed.path.split("/")[-2])
                payload = self.update_monitor_event(event_id, "ACKED", actor, request_id)
            elif parsed.path.startswith("/api/admin/monitor-events/") and parsed.path.endswith("/resolve"):
                event_id = unquote(parsed.path.split("/")[-2])
                payload = self.update_monitor_event(event_id, "RESOLVED", actor, request_id)
            else:
                raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")
            self.json_response(
                HTTPStatus.OK,
                {
                    "data": payload,
                    "meta": {
                        "request_id": request_id,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "actor": self.actor_public(actor),
                    },
                },
            )
        except ApiError as exc:
            self.json_response(
                exc.status,
                {
                    "error": {"code": exc.code, "message": exc.message, "details": exc.details},
                    "meta": {"request_id": request_id},
                },
            )
        except Exception as exc:  # pragma: no cover
            self.internal_error_response(request_id, exc)

    def do_PATCH(self) -> None:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        try:
            parsed = urlparse(self.path)
            actor = self.authenticate("PATCH", parsed.path, request_id)
            body = self.read_json_body()
            if parsed.path.startswith("/api/admin/review-items/"):
                review_id = unquote(parsed.path.rsplit("/", 1)[-1])
                payload = self.admin_update_review_item(review_id, body, actor, request_id)
            elif parsed.path.startswith("/api/admin/tokens/"):
                token_id = unquote(parsed.path.rsplit("/", 1)[-1])
                payload = self.update_token(token_id, body, actor, request_id)
            elif parsed.path.startswith("/api/admin/license-gates/"):
                gate_id = unquote(parsed.path.rsplit("/", 1)[-1])
                payload = self.update_license_gate(gate_id, body, actor, request_id)
            elif parsed.path.startswith("/api/admin/launch-gates/"):
                check_id = unquote(parsed.path.rsplit("/", 1)[-1])
                payload = self.update_launch_gate_check(check_id, body, actor, request_id)
            else:
                raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")
            self.json_response(
                HTTPStatus.OK,
                {
                    "data": payload,
                    "meta": {
                        "request_id": request_id,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "actor": self.actor_public(actor),
                    },
                },
            )
        except ApiError as exc:
            self.json_response(
                exc.status,
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    },
                    "meta": {"request_id": request_id},
                },
            )
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            self.internal_error_response(request_id, exc)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.send_security_headers()
        self.end_headers()

    def allowed_cors_origin(self) -> str:
        origin = self.headers.get("Origin", "").strip()
        if not origin:
            return ""
        configured = {
            item.strip()
            for item in os.environ.get("SERVICE_ALLOWED_ORIGINS", "").split(",")
            if item.strip()
        }
        allowed = DEFAULT_ALLOWED_CORS_ORIGINS | configured
        host = self.headers.get("Host", "").strip()
        if host:
            allowed |= {f"http://{host}", f"https://{host}"}
        return origin if origin in allowed else ""

    def send_cors_headers(self) -> None:
        origin = self.allowed_cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, X-Service-Token")

    def send_security_headers(self, html: bool = False) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        if html:
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com; "
                "img-src 'self' data: https://api.vworld.kr https://tiles.openfreemap.org https://*.openfreemap.org; "
                "connect-src 'self' https://api.vworld.kr https://tiles.openfreemap.org https://*.openfreemap.org https://unpkg.com; "
                "frame-ancestors 'none'",
            )

    def internal_error_response(self, request_id: str, exc: Exception | None = None) -> None:
        if exc is not None:
            print(f"request_id={request_id} internal_error={exc}", flush=True)
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.json_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error. Use request_id for server-side diagnostics.",
                    "details": {},
                },
                "meta": {"request_id": request_id},
            },
        )

    def required_role(self, method: str, path: str) -> str:
        if not auth_required():
            return ""
        if path in {"/api/healthz", "/api/readyz", "/api/config/maps"}:
            return ""
        if path == "/api/energy-sites/export.csv":
            return "EXPORTER"
        if path == "/api/terms/export/current":
            return "VIEWER"
        if path == "/api/terms/export/accept" or path == "/api/export-requests":
            return "EXPORTER"
        if path.startswith("/api/admin/tokens/") or path == "/api/admin/tokens":
            return "ADMIN"
        if path.startswith("/api/admin/export-requests/"):
            return "ADMIN"
        if path.startswith("/api/admin/launch-approval/"):
            return "ADMIN"
        if path.startswith("/api/admin/launch-gates/") and method == "PATCH":
            return "ADMIN"
        if path == "/api/admin/launch-approval" and method == "POST":
            return "ADMIN"
        if path == "/api/admin/launch-gates/run":
            return "OPERATOR"
        if path in {"/api/admin/audit-events", "/api/admin/export-audits", "/api/admin/export-requests", "/api/admin/license-gates", "/api/admin/launch-approval", "/api/admin/launch-gates", "/api/admin/coordinate-uplift-candidates", "/api/admin/auction-case-resolution-queue", "/api/admin/current-auction-search-queue", "/api/admin/current-auction-reference-candidates", "/api/admin/platform-action-queue", "/api/admin/platform-action-queue/file.csv", "/api/admin/completion-execution-board", "/api/admin/threshold-execution-board", "/api/admin/threshold-gate-runner-plan", "/api/admin/threshold-result-workpack", "/api/admin/external-impact-priority", "/api/admin/completion-execution-ledger", "/api/admin/completion-input-gap", "/api/admin/location-land-building-gap", "/api/admin/g3-g5-workpack-index", "/api/admin/g3-g5-workpack-index/file.csv", "/api/admin/external-dependency-blockers", "/api/admin/external-source-readiness", "/api/admin/external-provider-session-plan", "/api/admin/auction-provider-access-preflight", "/api/admin/auction-provider-session-launcher", "/api/admin/auction-provider-browser-workboard", "/api/admin/auction-first-run-priority-pack", "/api/admin/auction-first-run-priority-pack/file.csv", "/api/admin/auction-first-run-result-status", "/api/admin/auction-next-priority-result-pack", "/api/admin/auction-next-priority-result-pack/file.csv", "/api/admin/auction-next-priority-result-status", "/api/admin/revenue-input-workboard", "/api/admin/revenue-workboard-result-preflight", "/api/admin/revenue-workboard-result-preflight/file.csv", "/api/admin/planning-input-workboard", "/api/admin/planning-workboard-result-preflight", "/api/admin/planning-workboard-result-preflight/file.csv", "/api/admin/geocode-api-key-preflight", "/api/admin/pnu-geocode-priority-pack", "/api/admin/pnu-geocode-queue-seed", "/api/admin/p0-geocode-execution-monitor", "/api/admin/auction-provider-workbench", "/api/admin/auction-provider-intake-preflight", "/api/admin/geocode-intake-preflight", "/api/admin/external-workpack-manifest", "/api/admin/external-intake-status", "/api/admin/external-result-file-scan", "/api/admin/result-file-execution-plan", "/api/admin/external-result-contract-audit", "/api/admin/next-input-operator-brief", "/api/admin/100pct-control-tower", "/api/admin/gate-pass-gap-projection", "/api/admin/gate-pass-minimum-batch-queue", "/api/admin/next-execution-priority-pack", "/api/admin/minimum-batch-operator-preflight", "/api/admin/minimum-batch-operator-preflight/file.csv", "/api/admin/minimum-batch-execution-plan", "/api/admin/platform-completion-gates", "/api/admin/platform-coverage-snapshots", "/api/admin/terms/acceptances"}:
            return "AUDITOR"
        if path in {"/api/admin/backup-runs", "/api/admin/refresh-runs", "/api/admin/monitor-events", "/api/admin/ops-dashboard"}:
            return "OPERATOR"
        if path.startswith("/api/admin/monitor-events/"):
            return "OPERATOR"
        if path.startswith("/api/admin/license-gates/"):
            return "ADMIN"
        if path == "/api/admin/auth/me":
            return "VIEWER"
        if method == "PATCH" or path.startswith("/api/admin/"):
            return "OPERATOR"
        if path.startswith("/api/"):
            return "VIEWER"
        return ""

    def authenticate(self, method: str, path: str, request_id: str) -> dict[str, Any]:
        required = self.required_role(method, path)
        if not auth_required():
            return default_actor()
        if not required:
            actor = default_actor()
            actor["auth_required"] = True
            return actor

        token = self.headers.get("X-Service-Token", "").strip()
        if not token:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "AUTH_REQUIRED", "X-Service-Token header is required")

        token_hash = hash_token(token)
        bootstrap_token = os.environ.get("SERVICE_ADMIN_TOKEN", "").strip()
        if bootstrap_token and secrets.compare_digest(hash_token(bootstrap_token), token_hash):
            actor = {
                "actor_id": "bootstrap-admin",
                "display_name": "Bootstrap Admin",
                "role_code": "ADMIN",
                "auth_required": True,
            }
            if role_allows(actor["role_code"], required):
                return actor
        con = connect(read_only=True)
        try:
            if not table_exists(con, "service_user_token"):
                raise ApiError(HTTPStatus.UNAUTHORIZED, "INVALID_TOKEN", "Token table is not initialized")
            row = con.execute(
                """
                SELECT token_id, display_name, role_code
                FROM service_user_token
                WHERE token_hash = ?
                  AND enabled
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                LIMIT 1
                """,
                [token_hash],
            ).fetchone()
        finally:
            con.close()
        if not row:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "INVALID_TOKEN", "Token is invalid, disabled, or expired")
        try:
            con = connect(read_only=False)
            try:
                con.execute("UPDATE service_user_token SET last_used_at = CURRENT_TIMESTAMP WHERE token_id = ?", [row[0]])
            finally:
                con.close()
        except Exception:
            pass

        actor = {
            "actor_id": str(row[0]),
            "display_name": str(row[1]),
            "role_code": str(row[2]).upper(),
            "auth_required": True,
        }
        if not role_allows(actor["role_code"], required):
            self.log_audit_event(
                actor,
                "AUTH_FORBIDDEN",
                "endpoint",
                path,
                "DENIED",
                request_id,
                {"required_role": required, "method": method},
            )
            raise ApiError(
                HTTPStatus.FORBIDDEN,
                "FORBIDDEN",
                f"{required} role or higher is required",
                {"required_role": required, "actor_role": actor["role_code"]},
            )
        return actor

    def actor_public(self, actor: dict[str, Any]) -> dict[str, Any]:
        return {
            "actor_id": actor.get("actor_id", ""),
            "display_name": actor.get("display_name", ""),
            "role_code": actor.get("role_code", ""),
            "auth_required": bool(actor.get("auth_required")),
        }

    def insert_audit_event(
        self,
        con: duckdb.DuckDBPyConnection,
        actor: dict[str, Any],
        event_type: str,
        target_type: str,
        target_id: str,
        event_status: str,
        request_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        ensure_service_security_tables(con)
        con.execute(
            """
            INSERT INTO service_audit_event (
                event_id, request_id, actor_id, actor_role, event_type,
                target_type, target_id, event_status, detail_json,
                ip_address, user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(uuid.uuid4()),
                request_id,
                actor.get("actor_id", ""),
                actor.get("role_code", ""),
                event_type,
                target_type,
                target_id,
                event_status,
                json.dumps(details or {}, ensure_ascii=False),
                self.client_address[0] if self.client_address else "",
                self.headers.get("User-Agent", ""),
            ],
        )

    def log_audit_event(
        self,
        actor: dict[str, Any],
        event_type: str,
        target_type: str,
        target_id: str,
        event_status: str,
        request_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            con = connect()
            try:
                self.insert_audit_event(con, actor, event_type, target_type, target_id, event_status, request_id, details)
            finally:
                con.close()
        except Exception:
            return

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_JSON", "request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_JSON", "request body must be a JSON object")
        return payload

    def serve_index(self) -> None:
        if not FRONTEND_INDEX.exists():
            raise ApiError(HTTPStatus.NOT_FOUND, "FRONTEND_NOT_FOUND", "frontend/index.html not found")
        content = FRONTEND_INDEX.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers(html=True)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.send_security_headers()
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def csv_response(self, filename: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        content = ("\ufeff" + output.getvalue()).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_cors_headers()
        self.send_security_headers()
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def file_response(self, path: Path, filename: str, content_type: str = "text/csv; charset=utf-8") -> None:
        content = path.read_bytes()
        ascii_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename).strip("._") or "download.csv"
        encoded_name = quote(filename)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}")
        self.send_cors_headers()
        self.send_security_headers()
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def allowed_action_file_roots(self) -> list[Path]:
        roots = []
        for raw in [os.environ.get("LOAN4U_DATA_ROOT", r"D:\loan4u_avm_data")]:
            if raw:
                roots.append((Path(raw) / "exports").resolve())
        return roots

    def is_allowed_action_file(self, path: Path) -> bool:
        resolved = path.resolve()
        for root in self.allowed_action_file_roots():
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

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

    def external_dependency_blocker_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "blocker_group", "blocker_type"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_dependency_blocker"):
                return {"items": [], "count": 0, "summary": [], "total_open_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      gate_id, blocker_group, blocker_type, required_source,
                      current_count, required_count, open_count,
                      workpack_file, result_template,
                      secondary_workpack_file, secondary_result_template,
                      operator_note, next_action, created_at
                    FROM energy_site_external_dependency_blocker
                    {where}
                    ORDER BY
                      CASE blocker_group
                        WHEN 'LOCATION' THEN 1
                        WHEN 'LAND' THEN 2
                        WHEN 'BUILDING' THEN 3
                        WHEN 'STORAGE' THEN 4
                        WHEN 'AUCTION' THEN 5
                        WHEN 'REVENUE' THEN 6
                        WHEN 'PLANNING' THEN 7
                        WHEN 'PREDICTION' THEN 8
                        ELSE 99
                      END,
                      open_count DESC,
                      gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT blocker_group, COUNT(*) AS gate_count, SUM(open_count) AS open_count
                    FROM energy_site_external_dependency_blocker
                    GROUP BY blocker_group
                    ORDER BY
                      CASE blocker_group
                        WHEN 'LOCATION' THEN 1
                        WHEN 'LAND' THEN 2
                        WHEN 'BUILDING' THEN 3
                        WHEN 'STORAGE' THEN 4
                        WHEN 'AUCTION' THEN 5
                        WHEN 'REVENUE' THEN 6
                        WHEN 'PLANNING' THEN 7
                        WHEN 'PREDICTION' THEN 8
                        ELSE 99
                      END
                    """
                )
            )
            total_open = con.execute("SELECT COALESCE(SUM(open_count), 0) FROM energy_site_external_dependency_blocker").fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "total_open_count": total_open, "source_status": "READY"}
        finally:
            con.close()

    def external_source_readiness(self) -> dict[str, Any]:
        def configured(*names: str) -> bool:
            return any(bool(os.getenv(name, "").strip()) for name in names)

        def access_status(is_configured: bool, fallback: str) -> str:
            return "CONFIGURED" if is_configured else fallback

        con = connect(read_only=True)
        try:
            total_sites = scalar_if_table(con, "energy_site_search_mart", "SELECT COUNT(*) FROM energy_site_search_mart")
            geocode_rows = scalar_if_table(con, "energy_site_geocode_result", "SELECT COUNT(*) FROM energy_site_geocode_result")
            geocode_ready = scalar_if_table(con, "energy_site_geocode_request", "SELECT COUNT(*) FROM energy_site_geocode_request WHERE request_status = 'READY'")
            auction_open = scalar_if_table(con, "energy_site_auction_search_queue", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_auction_search_queue WHERE search_status = 'READY_FOR_EXTERNAL_PROVIDER'")
            auction_valid = scalar_if_table(con, "energy_site_auction_case_quality", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_auction_case_quality WHERE case_no_valid")
            current_open = scalar_if_table(con, "energy_site_current_auction_search_queue", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_current_auction_search_queue WHERE search_status = 'READY_FOR_EXTERNAL_PROVIDER'")
            current_verified = scalar_if_table(
                con,
                "energy_site_current_auction_status",
                """
                SELECT COUNT(DISTINCT energy_site_id)
                FROM energy_site_current_auction_status
                WHERE COALESCE(case_status, '') <> 'UNVERIFIED_PROVIDER_SEARCH_REQUIRED'
                  AND COALESCE(source_provider, '') <> 'CURRENT_AUCTION_PROVIDER_SEARCH_QUEUE'
                """,
            )
            card_12m = scalar_if_table(
                con,
                "energy_site_card_payment_monthly",
                """
                SELECT COUNT(*)
                FROM (
                  SELECT energy_site_id
                  FROM energy_site_card_payment_monthly
                  GROUP BY energy_site_id
                  HAVING COUNT(DISTINCT sales_month) >= 12
                )
                """,
            )
            financial_sites = scalar_if_table(con, "energy_site_financial_statement", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_financial_statement")
            planning_sites = scalar_if_table(con, "energy_site_urban_planning_event", "SELECT COUNT(DISTINCT energy_site_id) FROM energy_site_urban_planning_event")
            rows = [
                {
                    "source_code": "JUSO_GEOCODE",
                    "source_name": "주소 API",
                    "purpose": "주유소 좌표, 도로명주소, PNU 후보 보강",
                    "required_gates": "G3, G4",
                    "access_status": access_status(configured("JUSO_API_KEY", "ROAD_NAME_ADDRESS_API_KEY"), "RESULT_OR_API_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if geocode_rows else "NO_DATA",
                    "evidence_count": geocode_rows,
                    "open_count": max(int(total_sites or 0) - scalar_if_table(con, "energy_site_search_mart", "SELECT COUNT(*) FROM energy_site_search_mart WHERE lat IS NOT NULL AND lon IS NOT NULL"), 0),
                    "env_names": "JUSO_API_KEY / ROAD_NAME_ADDRESS_API_KEY",
                    "next_action": "API 키를 환경변수로만 설정하거나 geocode 결과 CSV를 import합니다.",
                },
                {
                    "source_code": "INFOCARE_AUCTION",
                    "source_name": "인포케어",
                    "purpose": "최근 20년 경매이력, 감정가, 낙찰가, 응찰자 수 확인",
                    "required_gates": "G7, G8",
                    "access_status": access_status(configured("INFOCARE_BROWSER_SESSION_READY", "INFOCARE_BROWSER_PROFILE"), "USER_BROWSER_SESSION_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if auction_valid else "NO_DATA",
                    "evidence_count": auction_valid,
                    "open_count": auction_open,
                    "env_names": "INFOCARE_BROWSER_SESSION_READY / INFOCARE_BROWSER_PROFILE",
                    "next_action": "사용자 브라우저에서 로그인 세션을 열고 사건번호·평가·낙찰 결과양식을 채웁니다.",
                },
                {
                    "source_code": "AUCTIONONE_AUCTION",
                    "source_name": "옥션원",
                    "purpose": "경매이력 교차검증과 현재 경매 진행 여부 확인",
                    "required_gates": "G7, G8",
                    "access_status": access_status(configured("AUCTIONONE_BROWSER_SESSION_READY", "AUCTIONONE_BROWSER_PROFILE"), "USER_BROWSER_SESSION_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if auction_valid or current_verified else "NO_DATA",
                    "evidence_count": auction_valid + current_verified,
                    "open_count": auction_open + current_open,
                    "env_names": "AUCTIONONE_BROWSER_SESSION_READY / AUCTIONONE_BROWSER_PROFILE",
                    "next_action": "사용자 브라우저에서 로그인 후 주소/PNU 기준 검색 결과를 결과양식으로 주입합니다.",
                },
                {
                    "source_code": "COURT_AUCTION",
                    "source_name": "대법원 경매정보",
                    "purpose": "법원 사건번호와 현재 진행/종결 여부 검증",
                    "required_gates": "G7, G8",
                    "access_status": access_status(configured("COURT_AUCTION_BROWSER_READY"), "RESULT_FILE_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if current_verified else "NO_DATA",
                    "evidence_count": current_verified,
                    "open_count": current_open,
                    "env_names": "COURT_AUCTION_BROWSER_READY",
                    "next_action": "사건번호 또는 진행 없음 증빙을 결과양식으로 import합니다.",
                },
                {
                    "source_code": "CARD_PAYMENT",
                    "source_name": "카드·VAN 매출",
                    "purpose": "최근 12개월 카드결제 기반 수익성 입력",
                    "required_gates": "G9, G10",
                    "access_status": access_status(configured("CARD_REVENUE_SOURCE_READY"), "RESULT_FILE_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if card_12m else "NO_DATA",
                    "evidence_count": card_12m,
                    "open_count": max(int(total_sites or 0) - int(card_12m or 0), 0),
                    "env_names": "CARD_REVENUE_SOURCE_READY",
                    "next_action": "권한 증빙이 있는 12개월 카드/POS/VAN 자료를 strict import합니다.",
                },
                {
                    "source_code": "FINANCIAL_STATEMENT",
                    "source_name": "재무자료",
                    "purpose": "손익·원가·영업이익 기반 수익가치 모델 입력",
                    "required_gates": "G9, G10",
                    "access_status": access_status(configured("FINANCIAL_SOURCE_READY"), "RESULT_FILE_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if financial_sites else "NO_DATA",
                    "evidence_count": financial_sites,
                    "open_count": max(int(total_sites or 0) - int(financial_sites or 0), 0),
                    "env_names": "FINANCIAL_SOURCE_READY",
                    "next_action": "권한 증빙이 있는 재무제표 또는 사업자 제공 손익자료를 import합니다.",
                },
                {
                    "source_code": "URBAN_PLANNING",
                    "source_name": "도시계획·도로 고시",
                    "purpose": "도로개설, 용도지역, 계획시설 영향 입력",
                    "required_gates": "G11, G12",
                    "access_status": access_status(configured("URBAN_PLANNING_SOURCE_READY"), "RESULT_FILE_REQUIRED"),
                    "data_status": "DATA_IMPORTED" if planning_sites else "NO_DATA",
                    "evidence_count": planning_sites,
                    "open_count": max(int(total_sites or 0) - int(planning_sites or 0), 0),
                    "env_names": "URBAN_PLANNING_SOURCE_READY",
                    "next_action": "공식 고시 원천을 PNU/주소 기준으로 연결해 import합니다.",
                },
            ]
            ready_count = sum(1 for row in rows if row["access_status"] == "CONFIGURED" or row["data_status"] == "DATA_IMPORTED")
            return {
                "items": rows,
                "count": len(rows),
                "ready_count": ready_count,
                "waiting_count": len(rows) - ready_count,
                "source_status": "READY",
                "secret_policy": "환경변수 설정 여부만 표시하며 키/비밀번호 값은 반환하지 않습니다.",
                "geocode_ready_request_count": geocode_ready,
            }
        finally:
            con.close()

    def external_provider_session_plan_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("source_code", "session_status", "access_type"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("gate_id"):
            filters.append("required_gates ILIKE ?")
            params.append(f"%{query['gate_id'].strip()}%")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_provider_session_plan"):
                source_rows = self.external_source_readiness().get("items", [])
                rows = [
                    {
                        "session_plan_id": f"SESSION_{item.get('source_code', '')}",
                        "source_code": item.get("source_code", ""),
                        "source_name": item.get("source_name", ""),
                        "required_gates": item.get("required_gates", ""),
                        "access_type": item.get("access_status", ""),
                        "session_status": item.get("access_status", ""),
                        "credential_policy": "NOT_HELD_BY_CODEX",
                        "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
                        "env_names": item.get("env_names", ""),
                        "search_key": "주소/PNU/사건번호 또는 권한 있는 원천키",
                        "evidence_count": item.get("evidence_count", 0),
                        "open_count": item.get("open_count", 0),
                        "workpack_file": "",
                        "result_template_path": "",
                        "secondary_workpack_file": "",
                        "secondary_result_template_path": "",
                        "required_result_fields": "사건번호, 금액, 일자, 권한 증빙 등 gate별 필수 결과값",
                        "dry_run_command": "",
                        "import_command": "",
                        "secondary_dry_run_command": "",
                        "secondary_import_command": "",
                        "next_action": item.get("next_action", ""),
                        "created_at": "",
                    }
                    for item in source_rows[:limit]
                ]
                status_counts: dict[str, dict[str, Any]] = {}
                for row in rows:
                    status = str(row.get("session_status") or "")
                    current = status_counts.setdefault(status, {"session_status": status, "source_count": 0, "open_count": 0})
                    current["source_count"] += 1
                    current["open_count"] += int(row.get("open_count") or 0)
                return {
                    "items": rows,
                    "count": len(rows),
                    "summary": list(status_counts.values()),
                    "ready_count": sum(1 for row in rows if row.get("session_status") == "CONFIGURED"),
                    "waiting_count": sum(1 for row in rows if row.get("session_status") != "CONFIGURED"),
                    "total_open_count": sum(int(row.get("open_count") or 0) for row in rows),
                    "source_status": "DYNAMIC_FALLBACK",
                    "secret_policy": "계정과 키 값은 화면에 표시하지 않습니다. 테이블 생성 전에는 원천 준비상태에서 동적으로 표시합니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      session_plan_id, source_code, source_name, required_gates,
                      access_type, session_status, credential_policy, secret_policy,
                      env_names, search_key, evidence_count, open_count,
                      workpack_file, result_template_path, secondary_workpack_file,
                      secondary_result_template_path, required_result_fields,
                      dry_run_command, import_command, secondary_dry_run_command,
                      secondary_import_command, next_action, created_at
                    FROM energy_site_external_provider_session_plan
                    {where}
                    ORDER BY
                      CASE session_status
                        WHEN 'USER_BROWSER_SESSION_REQUIRED' THEN 1
                        WHEN 'API_OR_RESULT_IMPORT_REQUIRED' THEN 2
                        WHEN 'RESULT_FILE_REQUIRED' THEN 3
                        WHEN 'SESSION_READY' THEN 9
                        ELSE 5
                      END,
                      open_count DESC,
                      source_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT session_status, COUNT(*) AS source_count, SUM(open_count) AS open_count
                    FROM energy_site_external_provider_session_plan
                    GROUP BY session_status
                    ORDER BY
                      CASE session_status
                        WHEN 'USER_BROWSER_SESSION_REQUIRED' THEN 1
                        WHEN 'API_OR_RESULT_IMPORT_REQUIRED' THEN 2
                        WHEN 'RESULT_FILE_REQUIRED' THEN 3
                        WHEN 'SESSION_READY' THEN 9
                        ELSE 5
                      END
                    """
                )
            )
            ready_count = con.execute(
                """
                SELECT COUNT(*)
                FROM energy_site_external_provider_session_plan
                WHERE session_status = 'SESSION_READY'
                """
            ).fetchone()[0]
            total_open = con.execute(
                "SELECT COALESCE(SUM(open_count), 0) FROM energy_site_external_provider_session_plan"
            ).fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "summary": summary,
                "ready_count": ready_count,
                "waiting_count": max(len(rows) - int(ready_count or 0), 0),
                "total_open_count": total_open,
                "source_status": "READY",
                "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
            }
        finally:
            con.close()

    def auction_provider_access_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("provider_code", "access_status", "credential_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_provider_secure_access_preflight"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "ready_count": 0,
                    "codex_has_id_password_count": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      provider_code, provider_name, access_status, credential_status,
                      codex_has_id_password, session_env_names, account_env_names,
                      accepted_channels, rejected_channels, login_target,
                      open_workbench_batches, open_search_rows, open_site_count,
                      filled_result_rows, missing_items, next_action, checked_at
                    FROM energy_site_auction_provider_secure_access_preflight
                    {where}
                    ORDER BY
                      CASE access_status
                        WHEN 'USER_LOGIN_REQUIRED' THEN 1
                        WHEN 'SECRET_CHANNEL_REJECTED' THEN 2
                        WHEN 'RESULT_FILE_OR_PUBLIC_CHECK_REQUIRED' THEN 3
                        WHEN 'READY_TO_SEARCH' THEN 9
                        ELSE 5
                      END,
                      open_search_rows DESC,
                      provider_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT access_status, credential_status,
                           COUNT(*) AS provider_count,
                           SUM(open_search_rows) AS open_search_rows,
                           SUM(filled_result_rows) AS filled_result_rows
                    FROM energy_site_auction_provider_secure_access_preflight
                    GROUP BY access_status, credential_status
                    ORDER BY
                      CASE access_status
                        WHEN 'USER_LOGIN_REQUIRED' THEN 1
                        WHEN 'SECRET_CHANNEL_REJECTED' THEN 2
                        WHEN 'RESULT_FILE_OR_PUBLIC_CHECK_REQUIRED' THEN 3
                        WHEN 'READY_TO_SEARCH' THEN 9
                        ELSE 5
                      END
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_secure_access_preflight").fetchone()[0]
            ready = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_secure_access_preflight WHERE access_status = 'READY_TO_SEARCH'").fetchone()[0]
            held = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_secure_access_preflight WHERE codex_has_id_password").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "ready_count": ready,
                "codex_has_id_password_count": held,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "계정값은 반환하지 않습니다. Codex 보유 여부와 세션 준비 여부만 표시합니다.",
            }
        finally:
            con.close()

    def auction_provider_session_launcher_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("provider_code", "gate_id", "launcher_status", "preflight_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_provider_session_launcher"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "ready_count": 0,
                    "search_ready_count": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      launcher_id, launcher_status, provider_code, provider_name,
                      gate_id, gate_name, batch_id, batch_priority, sido,
                      site_category, site_type, row_count, site_count,
                      result_template_rows, filled_result_rows, input_rows,
                      importable_rows, rejected_rows, access_status,
                      credential_status, preflight_status, search_pack_path,
                      result_template_path, required_result_fields_ko,
                      safe_session_marker_command, dry_run_command,
                      import_command, post_command, operator_instruction,
                      credential_instruction, blocking_reason, secret_policy,
                      checked_at
                    FROM energy_site_auction_provider_session_launcher
                    {where}
                    ORDER BY
                      CASE launcher_status
                        WHEN 'READY_FOR_IMPORT' THEN 1
                        WHEN 'READY_TO_SEARCH' THEN 2
                        WHEN 'BROWSER_LOGIN_REQUIRED' THEN 3
                        WHEN 'RESULT_CSV_REQUIRED' THEN 4
                        WHEN 'RESULT_OR_PUBLIC_SEARCH_REQUIRED' THEN 5
                        WHEN 'SECRET_ENV_REMOVE_REQUIRED' THEN 9
                        ELSE 8
                      END,
                      row_count DESC,
                      provider_name,
                      batch_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT launcher_status, provider_name,
                           COUNT(*) AS batch_count,
                           SUM(row_count) AS row_count,
                           SUM(site_count) AS site_count,
                           SUM(importable_rows) AS importable_rows,
                           SUM(rejected_rows) AS rejected_rows
                    FROM energy_site_auction_provider_session_launcher
                    GROUP BY launcher_status, provider_name
                    ORDER BY
                      CASE launcher_status
                        WHEN 'READY_FOR_IMPORT' THEN 1
                        WHEN 'READY_TO_SEARCH' THEN 2
                        WHEN 'BROWSER_LOGIN_REQUIRED' THEN 3
                        WHEN 'RESULT_CSV_REQUIRED' THEN 4
                        WHEN 'RESULT_OR_PUBLIC_SEARCH_REQUIRED' THEN 5
                        WHEN 'SECRET_ENV_REMOVE_REQUIRED' THEN 9
                        ELSE 8
                      END,
                      provider_name
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_session_launcher").fetchone()[0]
            ready = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_session_launcher WHERE launcher_status = 'READY_FOR_IMPORT'").fetchone()[0]
            search_ready = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_session_launcher WHERE launcher_status = 'READY_TO_SEARCH'").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "ready_count": ready,
                "search_ready_count": search_ready,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "계정값은 반환하지 않습니다. 브라우저 세션 마커, 검색팩, 결과양식, dry-run/import 명령만 표시합니다.",
            }
        finally:
            con.close()

    def auction_provider_browser_workboard_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("provider_code", "gate_id", "launcher_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            filters.append("(site_name ILIKE ? OR search_keyword ILIKE ? OR road_address ILIKE ? OR jibun_address ILIKE ?)")
            keyword = f"%{query['q'].strip()}%"
            params.extend([keyword, keyword, keyword, keyword])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_provider_browser_workboard"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    WITH ranked AS (
                      SELECT
                        work_id, launcher_id, launcher_status, provider_code,
                        provider_name, gate_id, gate_name, batch_id, batch_row_no,
                        energy_site_id, site_name, site_type, business_status,
                        search_keyword, jibun_address, road_address, provider_lookup_keyword,
                        court_case_lookup_keyword, no_history_keyword, provider_search_url,
                        court_search_url, no_history_search_url,
                        COALESCE(provider_portal_url, '') AS provider_portal_url,
                        COALESCE(provider_direct_url, '') AS provider_direct_url,
                        COALESCE(provider_query_instruction, '') AS provider_query_instruction,
                        COALESCE(court_portal_url, '') AS court_portal_url,
                        required_result_fields_ko,
                        result_template_path, dry_run_command, import_command,
                        blocking_reason, operator_instruction, checked_at,
                        CASE launcher_status
                          WHEN 'READY_FOR_IMPORT' THEN 1
                          WHEN 'READY_TO_SEARCH' THEN 2
                          WHEN 'BROWSER_LOGIN_REQUIRED' THEN 3
                          WHEN 'RESULT_CSV_REQUIRED' THEN 4
                          ELSE 8
                        END AS status_rank,
                        CASE gate_id
                          WHEN 'G7_AUCTION_HISTORY' THEN 1
                          WHEN 'G8_CURRENT_AUCTION' THEN 2
                          ELSE 9
                        END AS gate_rank,
                        ROW_NUMBER() OVER (
                          PARTITION BY gate_id
                          ORDER BY
                            CASE launcher_status
                              WHEN 'READY_FOR_IMPORT' THEN 1
                              WHEN 'READY_TO_SEARCH' THEN 2
                              WHEN 'BROWSER_LOGIN_REQUIRED' THEN 3
                              WHEN 'RESULT_CSV_REQUIRED' THEN 4
                              ELSE 8
                            END,
                            provider_name,
                            batch_id,
                            batch_row_no
                        ) AS gate_row_no
                      FROM energy_site_auction_provider_browser_workboard
                      {where}
                    )
                    SELECT
                      work_id, launcher_id, launcher_status, provider_code,
                      provider_name, gate_id, gate_name, batch_id, batch_row_no,
                      energy_site_id, site_name, site_type, business_status,
                      search_keyword, jibun_address, road_address, provider_lookup_keyword,
                      court_case_lookup_keyword, no_history_keyword, provider_search_url,
                      court_search_url, no_history_search_url,
                      provider_portal_url, provider_direct_url,
                      provider_query_instruction, court_portal_url,
                      required_result_fields_ko,
                      result_template_path, dry_run_command, import_command,
                      blocking_reason, operator_instruction, checked_at
                    FROM ranked
                    ORDER BY
                      status_rank,
                      gate_row_no,
                      gate_rank,
                      provider_name,
                      batch_id,
                      batch_row_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT launcher_status, provider_name, gate_id,
                           COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_auction_provider_browser_workboard
                    GROUP BY launcher_status, provider_name, gate_id
                    ORDER BY launcher_status, provider_name, gate_id
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_browser_workboard").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "계정값은 반환하지 않습니다. 검색 키와 결과양식 경로만 표시합니다.",
            }
        finally:
            con.close()

    def auction_first_run_priority_pack_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("task_type", "gate_id", "provider_code"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            keyword = f"%{query['q'].strip()}%"
            filters.append("(site_name ILIKE ? OR address_raw ILIKE ? OR road_address ILIKE ? OR provider_reference_no ILIKE ?)")
            params.extend([keyword, keyword, keyword, keyword])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_first_run_priority_pack"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "아이디, 비밀번호, 쿠키, API key 값은 코드·문서·DB·화면에 저장하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      priority_rank, task_id, task_type, gate_id, provider_code,
                      provider_name, energy_site_id, site_name, site_type,
                      business_status, sido, sigungu, address_raw, road_address,
                      provider_reference_no, provider_portal_url, court_portal_url,
                      provider_query_instruction, court_case_lookup_keyword,
                      required_result_fields_ko, result_template_path,
                      dry_run_command, import_command, blocking_reason, checked_at
                    FROM energy_site_auction_first_run_priority_pack
                    {where}
                    ORDER BY priority_rank, task_type, provider_name, site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT task_type, gate_id, provider_name,
                           COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_auction_first_run_priority_pack
                    GROUP BY task_type, gate_id, provider_name
                    ORDER BY task_type, gate_id, provider_name
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_auction_first_run_priority_pack").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "계정값은 반환하지 않습니다. 1차 조회 우선순위, 검색 안내, 결과양식 경로만 표시합니다.",
            }
        finally:
            con.close()

    def auction_first_run_priority_pack_file_csv(self, query: dict[str, str], request_id: str, actor: dict[str, Any]) -> None:
        file_kind = query.get("file", "template").strip().lower() or "template"
        pattern_by_kind = {
            "search": "auction_first_run_priority_pack_*.csv",
            "workpack": "auction_first_run_priority_pack_*.csv",
            "template": "auction_first_run_priority_result_template_*.csv",
            "result": "auction_first_run_priority_result_template_*.csv",
        }
        pattern = pattern_by_kind.get(file_kind)
        if not pattern:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_AUCTION_FIRST_RUN_FILE_REQUEST", "file=search|template is required")
        root = Path(os.environ.get("LOAN4U_DATA_ROOT", r"D:\loan4u_avm_data")) / "exports" / "auction_first_run_priority_pack"
        candidates = [path for path in root.glob(f"*/{pattern}") if path.is_file()]
        if not candidates:
            raise ApiError(HTTPStatus.NOT_FOUND, "AUCTION_FIRST_RUN_FILE_NOT_FOUND", "auction first-run priority file is missing", {"file_kind": file_kind})
        resolved = max(candidates, key=lambda path: path.stat().st_mtime).resolve()
        if resolved.suffix.lower() != ".csv" or not self.is_allowed_action_file(resolved):
            raise ApiError(HTTPStatus.FORBIDDEN, "AUCTION_FIRST_RUN_FILE_FORBIDDEN", "requested file is outside the allowed export area")

        self.log_audit_event(
            actor,
            "DOWNLOAD_AUCTION_FIRST_RUN_PRIORITY_PACK",
            "energy_site_auction_first_run_priority_pack",
            file_kind,
            "SUCCESS",
            request_id,
            {"file_kind": file_kind, "filename": resolved.name},
        )
        self.file_response(resolved, f"auction_first_run_priority_{file_kind}_{resolved.name}")

    def auction_first_run_result_status(self, query: dict[str, str]) -> dict[str, Any]:
        root = Path(os.environ.get("LOAN4U_DATA_ROOT", r"D:\loan4u_avm_data")) / "exports" / "auction_first_run_priority_pack"
        matches = [path for path in root.glob("*/auction_first_run_priority_result_template_*.csv") if path.is_file()]
        if not matches:
            return {
                "source_status": "SOURCE_NOT_LOADED",
                "pipeline_status": "TEMPLATE_NOT_FOUND",
                "input_rows": 0,
                "candidate_rows": 0,
                "blank_rows": 0,
                "items": [],
                "summary": [],
                "data_policy": "결과 템플릿이 아직 생성되지 않았습니다.",
            }
        input_path = max(matches, key=lambda path: path.stat().st_mtime).resolve()
        result_fields = [
            "검색결과", "현재경매상태", "사건번호", "법원", "매각기일", "낙찰일", "감정평가일", "감정가",
            "최저가", "낙찰가", "응찰자수", "유찰횟수", "회차", "유치권여부", "특이사항", "증빙URL",
            "문서ID", "결과확인일", "정확도", "결과메모",
        ]
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        candidates = []
        gate_counts: dict[str, int] = {}
        for row in rows:
            gate = str(row.get("gate_id") or "").strip() or "UNKNOWN"
            gate_counts[gate] = gate_counts.get(gate, 0) + 1
            filled = [field for field in result_fields if str(row.get(field) or "").strip()]
            if filled:
                candidates.append(
                    {
                        "priority_rank": row.get("priority_rank", ""),
                        "task_type": row.get("task_type", ""),
                        "gate_id": gate,
                        "provider_name": row.get("provider_name", ""),
                        "energy_site_id": row.get("energy_site_id", ""),
                        "site_name": row.get("site_name", ""),
                        "case_no": row.get("사건번호", ""),
                        "result_status": row.get("검색결과", "") or row.get("현재경매상태", ""),
                        "filled_fields": ", ".join(filled),
                    }
                )
        candidate_rows = len(candidates)
        status = "INPUT_WAITING" if candidate_rows == 0 else "RUN_DRY_RUN_REQUIRED"
        py = r"C:\Users\eungk\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        dry_run_command = (
            f'{py} scripts\\run_auction_first_run_result_pipeline.py '
            f'--db "{DEFAULT_DB_PATH}" --input "{input_path}" --mode dry-run '
            f'--report docs\\auction_first_run_result_pipeline_after_fill_YYYYMMDD.md'
        )
        summary = [{"gate_id": gate, "row_count": count} for gate, count in sorted(gate_counts.items())]
        return {
            "source_status": "READY",
            "pipeline_status": status,
            "input_path": str(input_path),
            "input_filename": input_path.name,
            "input_updated_at": datetime.fromtimestamp(input_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "input_rows": len(rows),
            "candidate_rows": candidate_rows,
            "blank_rows": len(rows) - candidate_rows,
            "items": candidates[: min(max(int(query.get("limit", "20")), 1), 200)],
            "summary": summary,
            "dry_run_command": dry_run_command,
            "next_action": "결과 입력값이 있으면 dry-run을 실행해 READY/REJECTED를 판정합니다. 입력값이 없으면 Provider 조회 후 결과 템플릿을 채웁니다.",
            "data_policy": "이 상태판은 파일 입력 여부만 감지합니다. 실제 import 가능 여부는 strict dry-run이 판정합니다.",
        }

    def auction_next_priority_result_pack_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "source_provider", "input_status", "sido"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            keyword = f"%{query['q'].strip()}%"
            filters.append("(site_name ILIKE ? OR search_keyword ILIKE ? OR energy_site_id ILIKE ? OR case_no ILIKE ?)")
            params.extend([keyword, keyword, keyword, keyword])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_next_priority_result_pack"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "site_count": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "secret_policy": "계정값은 저장하지 않습니다. 경매 결과 입력팩을 먼저 생성해야 합니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      pack_id, priority_rank, gate_id, gate_name, batch_id,
                      template_row_no, queue_id, energy_site_id, site_name,
                      site_type, business_status, sido, source_provider,
                      provider_name, provider_portal_url, court_portal_url,
                      search_keyword, pnu, jibun_address, road_address,
                      provider_lookup_keyword, court_case_lookup_keyword,
                      no_result_keyword, status_options, case_no_format_rule,
                      required_evidence, required_result_fields_ko,
                      operator_instruction, provider_result_status, case_status,
                      case_no, court_name, event_status, event_date, bid_due_date,
                      award_date, valuation_date, appraisal_value, minimum_bid_value,
                      successful_bid_value, bidder_count, previous_failed_count,
                      current_round, lien_status, special_notes, auction_url,
                      source_document_id, source_url, checked_at, confidence,
                      note, input_status, input_guide, dry_run_command, import_command
                    FROM energy_site_auction_next_priority_result_pack
                    {where}
                    ORDER BY try_cast(priority_rank AS BIGINT), try_cast(template_row_no AS BIGINT)
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, input_status, COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_auction_next_priority_result_pack
                    GROUP BY gate_id, input_status
                    ORDER BY gate_id, input_status
                    """
                )
            )
            total, site_count = con.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT energy_site_id)
                FROM energy_site_auction_next_priority_result_pack
                """
            ).fetchone()
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "site_count": site_count,
                "summary": summary,
                "source_status": "READY",
                "secret_policy": "인포케어·옥션원·대법원 로그인 정보는 반환하지 않습니다. 사건번호와 증빙 결과 입력 상태만 표시합니다.",
                "next_action": "CSV를 내려받아 Provider 확인값을 채운 뒤 strict dry-run을 실행합니다.",
            }
        finally:
            con.close()

    def auction_next_priority_result_pack_file_csv(self, query: dict[str, str], request_id: str, actor: dict[str, Any]) -> None:
        root = Path(os.environ.get("LOAN4U_DATA_ROOT", r"D:\loan4u_avm_data")) / "exports" / "auction_next_priority_result_pack"
        candidates = [path for path in root.glob("*/auction_next_priority_result_pack_*.csv") if path.is_file()]
        if not candidates:
            raise ApiError(HTTPStatus.NOT_FOUND, "AUCTION_NEXT_PRIORITY_RESULT_PACK_FILE_NOT_FOUND", "auction next-priority result pack file is missing")
        resolved = max(candidates, key=lambda path: path.stat().st_mtime).resolve()
        if resolved.suffix.lower() != ".csv" or not self.is_allowed_action_file(resolved):
            raise ApiError(HTTPStatus.FORBIDDEN, "AUCTION_NEXT_PRIORITY_RESULT_PACK_FILE_FORBIDDEN", "requested file is outside the allowed export area")
        self.log_audit_event(
            actor,
            "DOWNLOAD_AUCTION_NEXT_PRIORITY_RESULT_PACK",
            "energy_site_auction_next_priority_result_pack",
            resolved.name,
            "SUCCESS",
            request_id,
            {"filename": resolved.name},
        )
        self.file_response(resolved, f"auction_next_priority_result_pack_{resolved.name}")

    def auction_next_priority_result_status(self, query: dict[str, str]) -> dict[str, Any]:
        root = Path(os.environ.get("LOAN4U_DATA_ROOT", r"D:\loan4u_avm_data")) / "exports" / "auction_next_priority_result_pack"
        matches = [path for path in root.glob("*/auction_next_priority_result_pack_*.csv") if path.is_file()]
        if not matches:
            return {
                "source_status": "SOURCE_NOT_LOADED",
                "pipeline_status": "PACK_NOT_FOUND",
                "input_rows": 0,
                "candidate_rows": 0,
                "blank_rows": 0,
                "items": [],
                "summary": [],
                "data_policy": "경매 다음 우선순위 입력팩이 아직 생성되지 않았습니다.",
            }
        input_path = max(matches, key=lambda path: path.stat().st_mtime).resolve()
        result_fields = [
            "provider_result_status", "case_status", "case_no", "court_name", "event_status", "event_date",
            "bid_due_date", "award_date", "valuation_date", "appraisal_value", "minimum_bid_value",
            "successful_bid_value", "bidder_count", "previous_failed_count", "current_round", "lien_status",
            "special_notes", "auction_url", "source_document_id", "source_url", "checked_at", "confidence", "note",
            "검색결과", "현재경매상태", "사건번호", "법원", "매각기일", "낙찰일", "감정평가일", "감정가",
            "최저가", "낙찰가", "응찰자수", "유찰횟수", "회차", "유치권여부", "특이사항", "증빙URL",
            "문서ID", "결과확인일", "정확도", "결과메모",
        ]
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        candidates = []
        gate_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for row in rows:
            gate = str(row.get("gate_id") or "").strip() or "UNKNOWN"
            input_status = str(row.get("input_status") or "").strip() or "UNKNOWN"
            gate_counts[gate] = gate_counts.get(gate, 0) + 1
            status_counts[input_status] = status_counts.get(input_status, 0) + 1
            filled = [field for field in result_fields if str(row.get(field) or "").strip()]
            if filled:
                candidates.append(
                    {
                        "priority_rank": row.get("priority_rank", ""),
                        "gate_id": gate,
                        "input_status": input_status,
                        "energy_site_id": row.get("energy_site_id", ""),
                        "site_name": row.get("site_name", ""),
                        "case_no": row.get("case_no", "") or row.get("사건번호", ""),
                        "result_status": row.get("provider_result_status", "") or row.get("case_status", "") or row.get("검색결과", "") or row.get("현재경매상태", ""),
                        "filled_fields": ", ".join(filled),
                    }
                )
        candidate_rows = len(candidates)
        status = "INPUT_WAITING" if candidate_rows == 0 else "RUN_DRY_RUN_REQUIRED"
        py = r"C:\Users\eungk\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        dry_run_command = (
            f'{py} scripts\\run_auction_next_priority_result_pipeline.py '
            f'--db "{DEFAULT_DB_PATH}" --input "{input_path}" --mode dry-run '
            f'--report docs\\auction_next_priority_result_pipeline_after_fill_YYYYMMDD.md'
        )
        summary = [{"gate_id": gate, "row_count": count} for gate, count in sorted(gate_counts.items())]
        input_summary = [{"input_status": key, "row_count": count} for key, count in sorted(status_counts.items())]
        return {
            "source_status": "READY",
            "pipeline_status": status,
            "input_path": str(input_path),
            "input_filename": input_path.name,
            "input_updated_at": datetime.fromtimestamp(input_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "input_rows": len(rows),
            "candidate_rows": candidate_rows,
            "blank_rows": len(rows) - candidate_rows,
            "items": candidates[: min(max(int(query.get("limit", "20")), 1), 200)],
            "summary": summary,
            "input_summary": input_summary,
            "dry_run_command": dry_run_command,
            "next_action": "결과 입력값이 있으면 strict dry-run을 실행해 READY/REJECTED를 판정합니다. 입력값이 없으면 Provider 조회 후 사건번호와 증빙을 채웁니다.",
            "data_policy": "이 상태판은 파일 입력 여부만 감지합니다. 실제 import 가능 여부는 strict dry-run이 판정합니다.",
        }

    def revenue_input_workboard_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("input_kind", "site_category", "sido", "revenue_confirmation_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            filters.append("(site_name ILIKE ? OR provider_lookup_keyword ILIKE ? OR address_raw ILIKE ? OR energy_site_id ILIKE ?)")
            keyword = f"%{query['q'].strip()}%"
            params.extend([keyword, keyword, keyword, keyword])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_revenue_input_workboard"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "data_policy": "권한 있는 카드·재무 자료와 증빙이 있는 행만 import합니다. 임의 매출은 생성하지 않습니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    WITH ranked AS (
                      SELECT
                        work_id, gate_id, gate_name, input_kind, batch_id, batch_priority,
                        target_period, batch_row_no, energy_site_id, site_name, site_category,
                        site_type, business_status, sido, sigungu, address_raw, pnu,
                        current_card_months, current_financial_periods,
                        revenue_confirmation_status, provider_lookup_keyword,
                        required_result_fields_ko, source_provider_options,
                        rights_status_options, required_evidence, result_template_path,
                        dry_run_command, import_command, value_model_command,
                        operator_instruction, not_synthetic_warning, input_quality_gate,
                        blocking_reason, checked_at,
                        CASE input_kind WHEN 'CARD' THEN 1 WHEN 'FINANCIAL' THEN 2 ELSE 9 END AS kind_rank,
                        ROW_NUMBER() OVER (
                          PARTITION BY input_kind
                          ORDER BY batch_row_no, sido, site_category, site_name, batch_id
                        ) AS kind_row_no
                      FROM energy_site_revenue_input_workboard
                      {where}
                    )
                    SELECT
                      work_id, gate_id, gate_name, input_kind, batch_id, batch_priority,
                      target_period, batch_row_no, energy_site_id, site_name, site_category,
                      site_type, business_status, sido, sigungu, address_raw, pnu,
                      current_card_months, current_financial_periods,
                      revenue_confirmation_status, provider_lookup_keyword,
                      required_result_fields_ko, source_provider_options,
                      rights_status_options, required_evidence, result_template_path,
                      dry_run_command, import_command, value_model_command,
                      operator_instruction, not_synthetic_warning, input_quality_gate,
                      blocking_reason, checked_at
                    FROM ranked
                    ORDER BY kind_row_no, kind_rank, sido, site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT input_kind, revenue_confirmation_status,
                           COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_revenue_input_workboard
                    GROUP BY input_kind, revenue_confirmation_status
                    ORDER BY input_kind, revenue_confirmation_status
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_revenue_input_workboard").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "summary": summary,
                "source_status": "READY",
                "data_policy": "권한 있는 카드·재무 자료와 증빙이 있는 행만 strict import합니다. 임의 매출은 생성하지 않습니다.",
            }
        finally:
            con.close()

    def planning_input_workboard_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("batch_priority", "site_category", "sido", "planning_confirmation_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            filters.append("(site_name ILIKE ? OR planning_lookup_keyword ILIKE ? OR address_raw ILIKE ? OR energy_site_id ILIKE ?)")
            keyword = f"%{query['q'].strip()}%"
            params.extend([keyword, keyword, keyword, keyword])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_planning_input_workboard"):
                return {
                    "items": [],
                    "count": 0,
                    "total": 0,
                    "summary": [],
                    "source_status": "SOURCE_NOT_LOADED",
                    "data_policy": "공식 고시 증빙이 있는 도시계획·도로 영향만 strict import합니다.",
                }
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      work_id, gate_id, gate_name, batch_priority, batch_row_no,
                      energy_site_id, site_name, site_category, site_type,
                      business_status, sido, sigungu, address_raw, pnu, lat, lon,
                      current_planning_event_count, planning_confirmation_status,
                      planning_lookup_keyword, source_target_options,
                      required_result_fields_ko, evidence_status_options,
                      rights_status_options, required_evidence, result_template_path,
                      dry_run_command, import_command, prediction_command,
                      operator_instruction, input_quality_gate, blocking_reason,
                      checked_at
                    FROM energy_site_planning_input_workboard
                    {where}
                    ORDER BY
                      CASE batch_priority
                        WHEN 'P1_PLANNING_PNU_COORD' THEN 1
                        WHEN 'P1_PLANNING_PNU_ONLY' THEN 2
                        WHEN 'P1_PLANNING_COORD_ONLY' THEN 3
                        ELSE 4
                      END,
                      batch_row_no,
                      sido,
                      site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT batch_priority, planning_confirmation_status,
                           COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_planning_input_workboard
                    GROUP BY batch_priority, planning_confirmation_status
                    ORDER BY batch_priority, planning_confirmation_status
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_planning_input_workboard").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "summary": summary,
                "source_status": "READY",
                "data_policy": "공식 고시, 공공 포털, 원문 파일 등 증빙이 있는 도시계획·도로 영향만 strict import합니다.",
            }
        finally:
            con.close()

    def revenue_workboard_result_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        return self.workboard_result_preflight_items(
            query,
            "energy_site_revenue_input_workboard_result_preflight",
            [
                "result_row_id",
                "work_id",
                "input_kind",
                "energy_site_id",
                "site_name",
                "target_period",
                "source_provider",
                "rights_status",
                "preflight_status",
                "reject_reason",
                "ready_output_path",
                "checked_at",
            ],
            ("input_kind", "preflight_status", "rights_status"),
            ("site_name", "energy_site_id", "source_provider", "reject_reason"),
            "매출·재무 결과 preflight가 아직 생성되지 않았습니다.",
        )

    def revenue_workboard_result_preflight_csv(self, query: dict[str, str]) -> None:
        self.workboard_result_preflight_csv(
            query,
            "energy_site_revenue_input_workboard_result_preflight",
            [
                "result_row_id",
                "work_id",
                "input_kind",
                "energy_site_id",
                "site_name",
                "target_period",
                "source_provider",
                "rights_status",
                "preflight_status",
                "reject_reason",
                "ready_output_path",
                "checked_at",
            ],
            "revenue_workboard_result_preflight.csv",
        )

    def planning_workboard_result_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        return self.workboard_result_preflight_items(
            query,
            "energy_site_planning_input_workboard_result_preflight",
            [
                "result_row_id",
                "work_id",
                "energy_site_id",
                "site_name",
                "event_type",
                "plan_name",
                "source_provider",
                "evidence_status",
                "rights_status",
                "preflight_status",
                "reject_reason",
                "ready_output_path",
                "checked_at",
            ],
            ("preflight_status", "evidence_status", "rights_status"),
            ("site_name", "energy_site_id", "event_type", "plan_name", "source_provider", "reject_reason"),
            "도시계획·도로 결과 preflight가 아직 생성되지 않았습니다.",
        )

    def planning_workboard_result_preflight_csv(self, query: dict[str, str]) -> None:
        self.workboard_result_preflight_csv(
            query,
            "energy_site_planning_input_workboard_result_preflight",
            [
                "result_row_id",
                "work_id",
                "energy_site_id",
                "site_name",
                "event_type",
                "plan_name",
                "source_provider",
                "evidence_status",
                "rights_status",
                "preflight_status",
                "reject_reason",
                "ready_output_path",
                "checked_at",
            ],
            "planning_workboard_result_preflight.csv",
        )

    def workboard_result_preflight_csv(self, query: dict[str, str], table: str, fields: list[str], filename: str) -> None:
        filters: list[str] = []
        params: list[Any] = []
        status = query.get("preflight_status", "").strip()
        if status:
            filters.append("preflight_status = ?")
            params.append(status)
            filename = filename.replace(".csv", f"_{status.lower()}.csv")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, table):
                raise ApiError(HTTPStatus.NOT_FOUND, "SOURCE_NOT_LOADED", f"{table} is not available")
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT {', '.join(fields)}
                    FROM {table}
                    {where}
                    ORDER BY
                      CASE preflight_status
                        WHEN 'READY_FOR_IMPORT' THEN 1
                        WHEN 'REJECTED' THEN 2
                        WHEN 'BLANK_RESULT_INPUT' THEN 3
                        ELSE 9
                      END,
                      checked_at DESC,
                      site_name,
                      energy_site_id
                    """,
                    params,
                )
            )
        finally:
            con.close()
        self.csv_response(filename, rows, fields)

    def workboard_result_preflight_items(
        self,
        query: dict[str, str],
        table: str,
        fields: list[str],
        filter_fields: tuple[str, ...],
        search_fields: tuple[str, ...],
        missing_message: str,
    ) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in filter_fields:
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        if query.get("q"):
            filters.append("(" + " OR ".join(f"{field} ILIKE ?" for field in search_fields) + ")")
            params.extend([f"%{query['q'].strip()}%"] * len(search_fields))
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, table):
                return {"items": [], "count": 0, "total": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED", "data_policy": missing_message}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT {', '.join(fields)}
                    FROM {table}
                    {where}
                    ORDER BY
                      CASE preflight_status
                        WHEN 'READY_FOR_IMPORT' THEN 1
                        WHEN 'REJECTED' THEN 2
                        WHEN 'BLANK_RESULT_INPUT' THEN 3
                        ELSE 9
                      END,
                      checked_at DESC,
                      site_name,
                      energy_site_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT preflight_status,
                           COUNT(*) AS row_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM {table}
                    GROUP BY preflight_status
                    ORDER BY
                      CASE preflight_status
                        WHEN 'READY_FOR_IMPORT' THEN 1
                        WHEN 'REJECTED' THEN 2
                        WHEN 'BLANK_RESULT_INPUT' THEN 3
                        ELSE 9
                      END
                    """
                )
            )
            total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            ready = con.execute(f"SELECT COUNT(*) FROM {table} WHERE preflight_status = 'READY_FOR_IMPORT'").fetchone()[0]
            rejected = con.execute(f"SELECT COUNT(*) FROM {table} WHERE preflight_status = 'REJECTED'").fetchone()[0]
            blank = con.execute(f"SELECT COUNT(*) FROM {table} WHERE preflight_status = 'BLANK_RESULT_INPUT'").fetchone()[0]
            return {
                "items": rows,
                "count": len(rows),
                "total": total,
                "ready_count": ready,
                "rejected_count": rejected,
                "blank_count": blank,
                "summary": summary,
                "source_status": "READY",
                "data_policy": "증빙·권한·필수값을 통과한 행만 READY_FOR_IMPORT로 표시합니다. 빈 결과는 import하지 않습니다.",
            }
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

    def auction_provider_workbench_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "provider", "session_status", "readiness_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if table_exists(con, "energy_site_auction_provider_workbench"):
                rows = rows_to_dicts(
                    con.execute(
                        f"""
                        SELECT
                          workbench_id, gate_id, gate_name, provider, source_code,
                          source_name, access_type, session_status, credential_policy,
                          batch_id, batch_priority, site_category, site_type, sido,
                          row_count, site_count, template_exists, result_template_rows,
                          filled_result_rows, readiness_status, search_pack_path,
                          result_template_path, required_result_fields, dry_run_command,
                          import_command, post_command, operator_instruction, checked_at
                        FROM energy_site_auction_provider_workbench
                        {where}
                        ORDER BY
                          CASE gate_id WHEN 'G8_CURRENT_AUCTION' THEN 1 ELSE 2 END,
                          CASE provider WHEN 'SUPREME_COURT_AUCTION' THEN 1 WHEN 'INFOCARE' THEN 2 WHEN 'AUCTION_ONE' THEN 3 WHEN 'ONBID' THEN 4 ELSE 9 END,
                          row_count DESC,
                          batch_id
                        LIMIT ?
                        """,
                        [*params, limit],
                    )
                )
                summary = rows_to_dicts(
                    con.execute(
                        """
                        SELECT gate_id, provider, readiness_status,
                               COUNT(*) AS batch_count,
                               SUM(row_count) AS row_count,
                               SUM(site_count) AS site_count
                        FROM energy_site_auction_provider_workbench
                        GROUP BY gate_id, provider, readiness_status
                        ORDER BY gate_id, provider, readiness_status
                        """
                    )
                )
                total = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_workbench").fetchone()[0]
                ready = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_workbench WHERE readiness_status = 'READY_FOR_DRY_RUN'").fetchone()[0]
                return {"items": rows, "count": len(rows), "total": total, "ready_count": ready, "summary": summary, "source_status": "READY"}

            if not table_exists(con, "energy_site_auction_history_batch_manifest") and not table_exists(con, "energy_site_current_auction_batch_manifest"):
                return {"items": [], "count": 0, "total": 0, "ready_count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            dynamic_filters: list[str] = []
            dynamic_params: list[Any] = []
            dynamic_filter_expr = {
                "gate_id": "s.gate_id",
                "provider": "s.provider",
                "session_status": "COALESCE(p.session_status, 'RESULT_FILE_REQUIRED')",
            }
            for key, expr in dynamic_filter_expr.items():
                value = query.get(key, "").strip()
                if value:
                    dynamic_filters.append(f"{expr} = ?")
                    dynamic_params.append(value)
            dynamic_where = f"WHERE {' AND '.join(dynamic_filters)}" if dynamic_filters else ""
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    WITH source AS (
                      SELECT
                        'G7_AUCTION_HISTORY' AS gate_id,
                        '과거 경매 이력' AS gate_name,
                        source_provider AS provider,
                        batch_id, batch_priority, site_category, site_type, sido,
                        row_count, site_count, search_pack_path, result_template_path,
                        dry_run_command, import_command, case_quality_command AS post_command,
                        'INPUT_WAITING' AS readiness_status
                      FROM energy_site_auction_history_batch_manifest
                      UNION ALL
                      SELECT
                        'G8_CURRENT_AUCTION' AS gate_id,
                        '현재 경매 진행 여부' AS gate_name,
                        provider,
                        batch_id, batch_priority, site_category, site_type, sido,
                        row_count, site_count, search_pack_path, result_template_path,
                        dry_run_command, import_command, review_refresh_command AS post_command,
                        'INPUT_WAITING' AS readiness_status
                      FROM energy_site_current_auction_batch_manifest
                    ),
                    shaped AS (
                      SELECT
                        s.*,
                        CASE s.provider
                          WHEN 'INFOCARE' THEN 'INFOCARE_AUCTION'
                          WHEN 'AUCTION_ONE' THEN 'AUCTIONONE_AUCTION'
                          WHEN 'SUPREME_COURT_AUCTION' THEN 'COURT_AUCTION'
                          WHEN 'ONBID' THEN 'ONBID'
                          ELSE s.provider
                        END AS source_code
                      FROM source s
                    )
                    SELECT
                      gate_id || '_' || batch_id AS workbench_id,
                      gate_id, gate_name, provider, source_code,
                      COALESCE(p.source_name, provider) AS source_name,
                      COALESCE(p.access_type, '') AS access_type,
                      COALESCE(p.session_status, 'RESULT_FILE_REQUIRED') AS session_status,
                      COALESCE(p.credential_policy, 'NOT_HELD_BY_CODEX') AS credential_policy,
                      batch_id, batch_priority, site_category, site_type, sido,
                      row_count, site_count,
                      TRUE AS template_exists,
                      row_count AS result_template_rows,
                      0 AS filled_result_rows,
                      readiness_status,
                      search_pack_path, result_template_path,
                      CASE
                        WHEN gate_id = 'G8_CURRENT_AUCTION' THEN 'case_status, case_no, court_name, bid_due_date, appraisal_value, minimum_bid_value, checked_at, evidence_url'
                        ELSE 'provider_result_status, case_no, court_name, event_status, appraisal_value, successful_bid_value, award_date, bidder_count, checked_at, evidence_url'
                      END AS required_result_fields,
                      dry_run_command, import_command, post_command,
                      CASE
                        WHEN gate_id = 'G8_CURRENT_AUCTION' THEN '현재 경매 진행/없음 상태와 증빙을 먼저 입력합니다.'
                        ELSE '최근 20년 경매 이력 또는 이력 없음 증빙을 입력합니다.'
                      END AS operator_instruction,
                      '' AS checked_at
                    FROM shaped s
                    LEFT JOIN energy_site_external_provider_session_plan p ON p.source_code = s.source_code
                    {dynamic_where}
                    ORDER BY
                      CASE gate_id WHEN 'G8_CURRENT_AUCTION' THEN 1 ELSE 2 END,
                      CASE provider WHEN 'SUPREME_COURT_AUCTION' THEN 1 WHEN 'INFOCARE' THEN 2 WHEN 'AUCTION_ONE' THEN 3 WHEN 'ONBID' THEN 4 ELSE 9 END,
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
                    WITH source AS (
                      SELECT 'G7_AUCTION_HISTORY' AS gate_id, source_provider AS provider, row_count, site_count FROM energy_site_auction_history_batch_manifest
                      UNION ALL
                      SELECT 'G8_CURRENT_AUCTION' AS gate_id, provider, row_count, site_count FROM energy_site_current_auction_batch_manifest
                    )
                    SELECT gate_id, provider, 'INPUT_WAITING' AS readiness_status,
                           COUNT(*) AS batch_count, SUM(row_count) AS row_count, SUM(site_count) AS site_count
                    FROM source
                    GROUP BY gate_id, provider
                    ORDER BY gate_id, provider
                    """
                )
            )
            total = sum(int(row.get("batch_count") or 0) for row in summary)
            return {"items": rows, "count": len(rows), "total": total, "ready_count": 0, "summary": summary, "source_status": "DYNAMIC_FALLBACK"}
        finally:
            con.close()

    def auction_provider_intake_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "provider", "preflight_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_provider_intake_preflight"):
                return {"items": [], "count": 0, "total": 0, "ready_count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      workbench_id, gate_id, gate_name, provider, batch_id,
                      batch_priority, site_category, site_type, sido,
                      expected_rows, site_count, template_exists, input_rows,
                      importable_rows, rejected_rows, reject_reason_counts_json,
                      preflight_status, next_action, result_template_path,
                      dry_run_command, import_command, post_command, checked_at
                    FROM energy_site_auction_provider_intake_preflight
                    {where}
                    ORDER BY
                      CASE gate_id WHEN 'G8_CURRENT_AUCTION' THEN 1 ELSE 2 END,
                      CASE provider WHEN 'SUPREME_COURT_AUCTION' THEN 1 WHEN 'INFOCARE' THEN 2 WHEN 'AUCTION_ONE' THEN 3 WHEN 'ONBID' THEN 4 ELSE 9 END,
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
                    SELECT gate_id, provider, preflight_status,
                           COUNT(*) AS batch_count,
                           SUM(input_rows) AS input_rows,
                           SUM(importable_rows) AS importable_rows,
                           SUM(rejected_rows) AS rejected_rows
                    FROM energy_site_auction_provider_intake_preflight
                    GROUP BY gate_id, provider, preflight_status
                    ORDER BY gate_id, provider, preflight_status
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_intake_preflight").fetchone()[0]
            ready = con.execute("SELECT COUNT(*) FROM energy_site_auction_provider_intake_preflight WHERE preflight_status = 'READY_FOR_IMPORT'").fetchone()[0]
            return {"items": rows, "count": len(rows), "total": total, "ready_count": ready, "summary": summary, "source_status": "READY"}
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

    def external_workpack_manifest_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "priority", "readiness_status", "owner_role"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_workpack_manifest"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      manifest_id, action_id, gate_id, gate_name, priority, owner_role,
                      issue_count, readiness_status, preflight_status, candidate_rows,
                      missing_required_rows, secondary_preflight_status, secondary_candidate_rows,
                      search_workpack_path, search_workpack_exists, search_workpack_rows,
                      result_template_path, result_template_exists, result_template_rows,
                      result_template_sha256, result_template_columns_json,
                      secondary_workpack_path, secondary_workpack_exists, secondary_workpack_rows,
                      secondary_result_template_path, secondary_result_template_exists, secondary_result_template_rows,
                      required_fields_json, dry_run_command, import_command,
                      secondary_dry_run_command, secondary_import_command,
                      post_import_command, completion_command, completion_condition,
                      operator_note, created_at
                    FROM energy_site_external_workpack_manifest
                    {where}
                    ORDER BY
                      CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 9 END,
                      gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority, readiness_status, COUNT(*) AS count,
                           SUM(issue_count) AS issue_count,
                           SUM(candidate_rows) AS candidate_rows
                    FROM energy_site_external_workpack_manifest
                    GROUP BY 1, 2
                    ORDER BY CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 9 END, readiness_status
                    """
                )
            )
            return {"items": rows, "count": len(rows), "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def external_intake_status_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "priority", "template_role", "intake_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_intake_status"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      intake_id, action_id, gate_id, gate_name, priority, owner_role,
                      template_role, issue_count, result_template_path,
                      row_count, candidate_rows, reject_rows, intake_status,
                      required_fields_json, reject_sample_json,
                      dry_run_command, import_command, post_import_command,
                      completion_command, completion_condition, created_at
                    FROM energy_site_external_intake_status
                    {where}
                    ORDER BY
                      CASE intake_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'INPUT_REQUIRED' THEN 2
                        WHEN 'MODEL_INPUT_WAITING' THEN 3
                        WHEN 'TEMPLATE_MISSING' THEN 4
                        ELSE 9
                      END,
                      CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 9 END,
                      gate_id,
                      template_role
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority, intake_status, COUNT(*) AS count,
                           SUM(row_count) AS row_count,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(reject_rows) AS reject_rows
                    FROM energy_site_external_intake_status
                    GROUP BY 1, 2
                    ORDER BY CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 9 END, intake_status
                    """
                )
            )
            ready_count = con.execute(
                "SELECT COUNT(*) FROM energy_site_external_intake_status WHERE intake_status = 'READY_FOR_DRY_RUN'"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "ready_count": ready_count, "source_status": "READY"}
        finally:
            con.close()

    def external_result_file_scan_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "file_status", "matched_by"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_result_file_scan"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      scan_id, gate_id, gate_name, file_status, result_file_path,
                      file_name, file_bytes, file_mtime, sha256_hash, matched_by,
                      row_count, candidate_rows, reject_rows, header_json,
                      reject_sample_json, dry_run_command, import_command,
                      post_import_command, completion_command, next_action, created_at
                    FROM energy_site_external_result_file_scan
                    {where}
                    ORDER BY
                      CASE file_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'INVALID_OR_UNFILLED_RESULT' THEN 2
                        WHEN 'UNFILLED_RESULT_TEMPLATE' THEN 3
                        WHEN 'EMPTY_RESULT_FILE' THEN 4
                        WHEN 'INPUT_REQUIRED' THEN 5
                        WHEN 'UNCLASSIFIED' THEN 6
                        ELSE 9
                      END,
                      candidate_rows DESC,
                      file_mtime DESC,
                      gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, file_status, COUNT(*) AS file_count,
                           SUM(row_count) AS row_count,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(reject_rows) AS reject_rows
                    FROM energy_site_external_result_file_scan
                    GROUP BY 1, 2
                    ORDER BY gate_id, file_status
                    """
                )
            )
            ready_count = con.execute(
                "SELECT COUNT(*) FROM energy_site_external_result_file_scan WHERE file_status = 'READY_FOR_DRY_RUN'"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "ready_count": ready_count, "source_status": "READY"}
        finally:
            con.close()

    def result_file_execution_plan_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "execution_status", "file_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_result_file_execution_plan"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      plan_id, scan_id, gate_id, gate_name, file_status, execution_status,
                      result_file_path, file_name, file_mtime, row_count, candidate_rows,
                      reject_rows, dry_run_enabled, import_enabled, post_import_enabled,
                      completion_enabled, dry_run_command, import_command, post_import_command,
                      completion_command, next_command_kind, next_command, command_lock_reason,
                      next_action, created_at
                    FROM energy_site_result_file_execution_plan
                    {where}
                    ORDER BY
                      CASE execution_status WHEN 'READY_FOR_DRY_RUN' THEN 1 WHEN 'WAIT_INPUT' THEN 2 ELSE 9 END,
                      candidate_rows DESC,
                      file_mtime DESC,
                      gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, execution_status, COUNT(*) AS file_count,
                           SUM(row_count) AS row_count,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(reject_rows) AS reject_rows
                    FROM energy_site_result_file_execution_plan
                    GROUP BY 1, 2
                    ORDER BY gate_id, execution_status
                    """
                )
            )
            ready_count = con.execute(
                "SELECT COUNT(*) FROM energy_site_result_file_execution_plan WHERE execution_status = 'READY_FOR_DRY_RUN'"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "ready_count": ready_count, "source_status": "READY"}
        finally:
            con.close()

    def external_result_contract_audit_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "contract_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_external_result_contract_audit"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "candidate_rows": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      gate_id, gate_name, contract_status, template_rows, template_sites,
                      scanned_files, scanned_candidate_rows, intake_candidate_rows,
                      intake_reject_rows, ready_execution_files, required_contract_json,
                      primary_result_template_path, latest_result_file_path,
                      next_action, created_at
                    FROM energy_site_external_result_contract_audit
                    {where}
                    ORDER BY
                      CASE contract_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'INPUT_REQUIRED' THEN 2
                        WHEN 'MODEL_INPUT_WAITING' THEN 3
                        WHEN 'TEMPLATE_REQUIRED' THEN 4
                        ELSE 9
                      END,
                      gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT contract_status, COUNT(*) AS gate_count,
                           SUM(template_rows) AS template_rows,
                           SUM(scanned_candidate_rows + intake_candidate_rows) AS candidate_rows,
                           SUM(ready_execution_files) AS ready_execution_files
                    FROM energy_site_external_result_contract_audit
                    GROUP BY contract_status
                    ORDER BY contract_status
                    """
                )
            )
            ready = con.execute(
                "SELECT COUNT(*) FROM energy_site_external_result_contract_audit WHERE contract_status = 'READY_FOR_DRY_RUN'"
            ).fetchone()[0]
            candidate_rows = con.execute(
                "SELECT COALESCE(SUM(scanned_candidate_rows + intake_candidate_rows), 0) FROM energy_site_external_result_contract_audit"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "ready_count": ready, "candidate_rows": candidate_rows, "source_status": "READY"}
        finally:
            con.close()

    def next_input_operator_brief_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "gate_status", "contract_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_next_input_operator_brief"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "result_rows": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_status, current_metric,
                      target_metric, selected_site_count, selected_result_row_count,
                      template_rows, template_sites, contract_status,
                      result_template_path, required_fields_json,
                      dry_run_command, import_command, post_command,
                      source_guide, next_action, created_at
                    FROM energy_site_next_input_operator_brief
                    {where}
                    ORDER BY rank_no, gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT contract_status, COUNT(*) AS gate_count,
                           SUM(template_rows) AS template_rows,
                           SUM(template_sites) AS template_sites,
                           SUM(selected_site_count) AS selected_site_count,
                           SUM(selected_result_row_count) AS selected_result_row_count
                    FROM energy_site_next_input_operator_brief
                    GROUP BY contract_status
                    ORDER BY contract_status
                    """
                )
            )
            ready = con.execute(
                "SELECT COUNT(*) FROM energy_site_next_input_operator_brief WHERE contract_status = 'READY_FOR_DRY_RUN'"
            ).fetchone()[0]
            result_rows = con.execute(
                "SELECT COALESCE(SUM(selected_result_row_count), 0) FROM energy_site_next_input_operator_brief"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "ready_count": ready, "result_rows": result_rows, "source_status": "READY"}
        finally:
            con.close()

    def control_tower_100pct_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "contract_status", "next_command_kind"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_100pct_control_tower"):
                return {
                    "items": [],
                    "count": 0,
                    "summary": [],
                    "ready_plan_count": 0,
                    "waiting_plan_count": 0,
                    "missing_sites_to_pass": 0,
                    "source_status": "SOURCE_NOT_LOADED",
                }
            items = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_status, current_metric,
                      target_metric, missing_sites_to_pass, pass_threshold_coverable,
                      contract_status, required_fields_json, top_batch_id, top_sido,
                      top_site_count, top_result_template_path, ready_plan_count,
                      waiting_plan_count, candidate_rows, missing_required_rows,
                      next_command_kind, next_command, command_lock_reason,
                      source_guide, operator_next_action, created_at
                    FROM energy_site_100pct_control_tower
                    {where}
                    ORDER BY
                      CASE next_command_kind
                        WHEN 'DRY_RUN' THEN 1
                        WHEN 'FILL_TEMPLATE' THEN 2
                        WHEN 'MODEL_WAIT' THEN 3
                        ELSE 9
                      END,
                      rank_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT next_command_kind, contract_status, COUNT(*) AS gate_count,
                           SUM(missing_sites_to_pass) AS missing_sites_to_pass,
                           SUM(ready_plan_count) AS ready_plan_count,
                           SUM(waiting_plan_count) AS waiting_plan_count,
                           SUM(missing_required_rows) AS missing_required_rows
                    FROM energy_site_100pct_control_tower
                    GROUP BY next_command_kind, contract_status
                    ORDER BY next_command_kind, contract_status
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(ready_plan_count), 0),
                       COALESCE(SUM(waiting_plan_count), 0),
                       COALESCE(SUM(missing_sites_to_pass), 0)
                FROM energy_site_100pct_control_tower
                """
            ).fetchone()
            return {
                "items": items,
                "count": int(totals[0] or 0),
                "summary": summary,
                "ready_plan_count": int(totals[1] or 0),
                "waiting_plan_count": int(totals[2] or 0),
                "missing_sites_to_pass": int(totals[3] or 0),
                "source_status": "READY",
            }
        finally:
            con.close()

    def gate_pass_gap_projection_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "gate_status", "next_input_contract_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_gate_pass_gap_projection"):
                return {"items": [], "count": 0, "summary": [], "missing_sites_total": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      gate_id, gate_group, gate_name, gate_status, current_metric,
                      target_metric, total_sites, current_site_metric, current_sites,
                      target_sites, missing_sites_to_pass, completion_board_batches,
                      minimum_batches_to_pass_estimate, estimated_sites_in_minimum_batches,
                      first_batch_id, first_result_template_path,
                      threshold_selected_site_count, threshold_result_row_count,
                      next_input_contract_status, next_input_result_template_path,
                      source_guide, blocker_summary, checked_at
                    FROM energy_site_gate_pass_gap_projection
                    {where}
                    ORDER BY missing_sites_to_pass DESC, gate_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT next_input_contract_status, COUNT(*) AS gate_count,
                           SUM(missing_sites_to_pass) AS missing_sites_to_pass,
                           SUM(minimum_batches_to_pass_estimate) AS minimum_batches_to_pass_estimate
                    FROM energy_site_gate_pass_gap_projection
                    GROUP BY next_input_contract_status
                    ORDER BY next_input_contract_status
                    """
                )
            )
            missing_sites_total = con.execute(
                "SELECT COALESCE(SUM(missing_sites_to_pass), 0) FROM energy_site_gate_pass_gap_projection"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "missing_sites_total": missing_sites_total, "source_status": "READY"}
        finally:
            con.close()

    def gate_pass_minimum_batch_queue_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "next_input_contract_status", "sido", "pass_threshold_coverable"):
            value = query.get(key, "").strip()
            if not value:
                continue
            if key == "pass_threshold_coverable":
                filters.append("pass_threshold_coverable = ?")
                params.append(value.lower() in {"1", "true", "yes", "y", "가능"})
            else:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_gate_pass_minimum_batch_queue"):
                return {"items": [], "count": 0, "summary": [], "batch_count": 0, "coverable_gate_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      queue_rank, gate_order, gate_sequence, gate_id, gate_name,
                      gate_status, next_input_contract_status, batch_id, batch_priority,
                      source_table, site_category, site_type, sido, provider_hint,
                      row_count, site_count, cumulative_site_count, missing_sites_to_pass,
                      available_board_batch_count, available_board_site_count,
                      pass_threshold_coverable, remaining_after_batch, covers_pass_threshold,
                      search_pack_path, result_template_path, dry_run_command, import_command,
                      post_command AS post_import_command, completion_command,
                      command_enabled AS dry_run_enabled, command_enabled AS import_enabled,
                      command_enabled AS post_import_enabled, command_enabled AS completion_enabled,
                      command_lock_reason, operator_note AS next_action, checked_at
                    FROM energy_site_gate_pass_minimum_batch_queue
                    {where}
                    ORDER BY queue_rank
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, next_input_contract_status, pass_threshold_coverable,
                           COUNT(*) AS batch_count,
                           SUM(row_count) AS row_count,
                           SUM(site_count) AS site_count,
                           MAX(cumulative_site_count) AS cumulative_site_count,
                           MAX(missing_sites_to_pass) AS missing_sites_to_pass
                    FROM energy_site_gate_pass_minimum_batch_queue
                    GROUP BY gate_id, next_input_contract_status, pass_threshold_coverable
                    ORDER BY MIN(queue_rank)
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       COUNT(DISTINCT gate_id),
                       COUNT(DISTINCT CASE WHEN pass_threshold_coverable THEN gate_id END)
                FROM energy_site_gate_pass_minimum_batch_queue
                """
            ).fetchone()
            return {
                "items": rows,
                "count": len(rows),
                "summary": summary,
                "batch_count": totals[0],
                "gate_count": totals[1],
                "coverable_gate_count": totals[2],
                "source_status": "READY",
            }
        finally:
            con.close()

    def next_execution_priority_pack_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "80")), 1), 200)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("priority_lane", "gate_id", "sido", "command_enabled", "result_template_exists"):
            value = query.get(key, "").strip()
            if not value:
                continue
            if key in {"command_enabled", "result_template_exists"}:
                filters.append(f"{key} = ?")
                params.append(value.lower() in {"1", "true", "yes", "y", "가능", "있음"})
            else:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_next_execution_priority_pack"):
                return {"items": [], "count": 0, "summary": [], "lane_summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      priority_rank, priority_lane, gate_id, gate_name, current_metric,
                      target_metric, missing_sites_to_pass, batch_id, sido,
                      site_category, site_type, site_count, row_count,
                      covers_pass_threshold, pass_threshold_coverable,
                      result_template_path, result_template_exists,
                      search_pack_path, search_pack_exists,
                      command_enabled AS dry_run_enabled,
                      command_enabled AS import_enabled,
                      FALSE AS post_import_enabled,
                      command_enabled AS completion_enabled,
                      command_lock_reason,
                      dry_run_command, import_command,
                      post_command AS post_import_command,
                      completion_command,
                      required_fields_json, source_guide,
                      operator_action AS next_action, created_at
                    FROM energy_site_next_execution_priority_pack
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
                    SELECT priority_lane, gate_id, COUNT(*) AS row_count,
                           SUM(site_count) AS site_count,
                           SUM(CASE WHEN command_enabled THEN 1 ELSE 0 END) AS command_enabled_count,
                           SUM(CASE WHEN result_template_exists THEN 1 ELSE 0 END) AS template_exists_count
                    FROM energy_site_next_execution_priority_pack
                    GROUP BY priority_lane, gate_id
                    ORDER BY MIN(priority_rank)
                    """
                )
            )
            lane_summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority_lane, COUNT(*) AS row_count,
                           COUNT(DISTINCT gate_id) AS gate_count,
                           SUM(site_count) AS site_count
                    FROM energy_site_next_execution_priority_pack
                    GROUP BY priority_lane
                    ORDER BY MIN(priority_rank)
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       COUNT(DISTINCT priority_lane),
                       COUNT(DISTINCT gate_id),
                       COALESCE(SUM(site_count), 0),
                       COALESCE(SUM(CASE WHEN command_enabled THEN 1 ELSE 0 END), 0)
                FROM energy_site_next_execution_priority_pack
                """
            ).fetchone()
            return {
                "items": rows,
                "count": int(totals[0] or 0),
                "lane_count": int(totals[1] or 0),
                "gate_count": int(totals[2] or 0),
                "site_count": int(totals[3] or 0),
                "command_enabled_count": int(totals[4] or 0),
                "summary": summary,
                "lane_summary": lane_summary,
                "source_status": "READY",
            }
        finally:
            con.close()

    def minimum_batch_operator_preflight_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "preflight_status", "sido"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_minimum_batch_operator_preflight"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      bundle_id, queue_rank, gate_id, gate_name, batch_id, sido, site_count,
                      result_template_path, template_exists, total_rows, candidate_rows,
                      missing_required_rows, preflight_status, required_fields_json,
                      sample_missing_json, dry_run_command, import_command,
                      post_command AS post_import_command, '' AS completion_command,
                      next_action, checked_at,
                      preflight_status = 'READY_FOR_DRY_RUN' AS dry_run_enabled,
                      preflight_status = 'READY_FOR_DRY_RUN' AS import_enabled,
                      preflight_status IN ('READY_FOR_DRY_RUN', 'MODEL_INPUT_WAITING') AS post_import_enabled,
                      preflight_status = 'MODEL_INPUT_WAITING' AS completion_enabled,
                      CASE
                        WHEN preflight_status = 'READY_FOR_DRY_RUN' THEN ''
                        WHEN preflight_status = 'PARTIAL_CANDIDATE' THEN '필수값 누락 행 보완 또는 부분 import 승인 필요'
                        WHEN preflight_status = 'MODEL_INPUT_WAITING' THEN '선행 Gate strict import 후 모델 실행'
                        ELSE '결과양식 필수 원천값 입력 필요'
                      END AS command_lock_reason
                    FROM energy_site_minimum_batch_operator_preflight
                    {where}
                    ORDER BY
                      CASE preflight_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'PARTIAL_CANDIDATE' THEN 2
                        WHEN 'INPUT_WAITING' THEN 3
                        WHEN 'MODEL_INPUT_WAITING' THEN 4
                        ELSE 9
                      END,
                      queue_rank
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT preflight_status, gate_id,
                           COUNT(*) AS batch_count,
                           SUM(total_rows) AS total_rows,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(missing_required_rows) AS missing_required_rows
                    FROM energy_site_minimum_batch_operator_preflight
                    GROUP BY preflight_status, gate_id
                    ORDER BY preflight_status, gate_id
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       COUNT(DISTINCT gate_id),
                       COALESCE(SUM(total_rows), 0),
                       COALESCE(SUM(candidate_rows), 0),
                       SUM(CASE WHEN preflight_status = 'READY_FOR_DRY_RUN' THEN 1 ELSE 0 END)
                FROM energy_site_minimum_batch_operator_preflight
                """
            ).fetchone()
            return {
                "items": rows,
                "count": totals[0],
                "gate_count": totals[1],
                "total_rows": totals[2],
                "candidate_rows": totals[3],
                "ready_count": totals[4],
                "summary": summary,
                "source_status": "READY",
            }
        finally:
            con.close()

    def minimum_batch_operator_preflight_csv(self, query: dict[str, str]) -> None:
        fields = [
            "bundle_id",
            "queue_rank",
            "gate_id",
            "gate_name",
            "batch_id",
            "sido",
            "site_count",
            "preflight_status",
            "total_rows",
            "candidate_rows",
            "missing_required_rows",
            "result_template_path",
            "dry_run_command",
            "import_command",
            "post_command",
            "next_action",
            "checked_at",
        ]
        filters: list[str] = []
        params: list[Any] = []
        status = query.get("preflight_status", "").strip()
        gate_id = query.get("gate_id", "").strip()
        if status:
            filters.append("preflight_status = ?")
            params.append(status)
        if gate_id:
            filters.append("gate_id = ?")
            params.append(gate_id)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_minimum_batch_operator_preflight"):
                raise ApiError(HTTPStatus.NOT_FOUND, "SOURCE_NOT_LOADED", "minimum batch operator preflight is not available")
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT {', '.join(fields)}
                    FROM energy_site_minimum_batch_operator_preflight
                    {where}
                    ORDER BY queue_rank
                    """,
                    params,
                )
            )
        finally:
            con.close()
        suffix = f"_{status.lower()}" if status else ""
        self.csv_response(f"minimum_batch_operator_preflight{suffix}.csv", rows, fields)

    def minimum_batch_execution_plan_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "execution_status", "sido"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_minimum_batch_execution_plan"):
                return {"items": [], "count": 0, "summary": [], "ready_count": 0, "candidate_rows": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      plan_id, bundle_id, queue_rank, gate_id, gate_name, batch_id, sido,
                      site_count, preflight_status, execution_status, result_template_path,
                      total_rows, candidate_rows, missing_required_rows,
                      dry_run_enabled, import_enabled, post_import_enabled, completion_enabled,
                      dry_run_command, import_command, post_import_command, completion_command,
                      next_command_kind, next_command, command_lock_reason, next_action, created_at
                    FROM energy_site_minimum_batch_execution_plan
                    {where}
                    ORDER BY
                      CASE execution_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'WAIT_INPUT' THEN 2
                        WHEN 'WAIT_MODEL_INPUT' THEN 3
                        ELSE 9
                      END,
                      queue_rank
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, execution_status, COUNT(*) AS plan_count,
                           SUM(site_count) AS site_count,
                           SUM(total_rows) AS total_rows,
                           SUM(candidate_rows) AS candidate_rows,
                           SUM(missing_required_rows) AS missing_required_rows
                    FROM energy_site_minimum_batch_execution_plan
                    GROUP BY gate_id, execution_status
                    ORDER BY gate_id, execution_status
                    """
                )
            )
            totals = con.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(candidate_rows), 0),
                       SUM(CASE WHEN execution_status = 'READY_FOR_DRY_RUN' THEN 1 ELSE 0 END)
                FROM energy_site_minimum_batch_execution_plan
                """
            ).fetchone()
            return {
                "items": rows,
                "count": int(totals[0]),
                "summary": summary,
                "ready_count": int(totals[2] or 0),
                "candidate_rows": int(totals[1] or 0),
                "source_status": "READY",
            }
        finally:
            con.close()

    def unsafe_db_reader_process_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("severity", "risk_status", "reader_kind"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_unsafe_db_reader_process"):
                return {"items": [], "count": 0, "summary": [], "unsafe_count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      audit_id, process_id, process_name, reader_kind, source_db_path,
                      snapshot_safe, severity, risk_status, next_action,
                      command_line, checked_at
                    FROM energy_site_unsafe_db_reader_process
                    {where}
                    ORDER BY
                      CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARN' THEN 2 ELSE 9 END,
                      process_id
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT severity, risk_status, COUNT(*) AS process_count
                    FROM energy_site_unsafe_db_reader_process
                    GROUP BY 1, 2
                    ORDER BY CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARN' THEN 2 ELSE 9 END, risk_status
                    """
                )
            )
            unsafe_count = con.execute(
                "SELECT COUNT(*) FROM energy_site_unsafe_db_reader_process WHERE risk_status = 'UNSAFE_OPERATIONAL_DB_READER'"
            ).fetchone()[0]
            return {"items": rows, "count": len(rows), "summary": summary, "unsafe_count": unsafe_count, "source_status": "READY"}
        finally:
            con.close()

    def auction_case_resolution_queue_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("source_provider", "resolution_status", "priority"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_auction_case_resolution_queue"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            queue_columns = table_columns(con, "energy_site_auction_case_resolution_queue")

            def optional_column(column_name: str, default: str = "NULL") -> str:
                return quote_ident(column_name) if column_name in queue_columns else default

            total = con.execute(f"SELECT COUNT(*) FROM energy_site_auction_case_resolution_queue {where}", params).fetchone()[0]
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      queue_id, energy_site_id, source_provider, provider_reference_no,
                      site_name, site_category, site_type, business_status, sido, sigungu,
                      address_raw, pnu, event_count, latest_event_date, latest_event_status,
                      provider_subject, appraisal_value, successful_bid_value, bidder_count,
                      search_keyword, resolution_status, priority, reason, created_at
                      , {optional_column("resolved_case_no")} AS resolved_case_no
                      , {optional_column("resolved_at")} AS resolved_at
                      , {optional_column("resolved_import_run_id")} AS resolved_import_run_id
                      , {optional_column("resolution_note")} AS resolution_note
                    FROM energy_site_auction_case_resolution_queue
                    {where}
                    ORDER BY
                      CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 9 END,
                      sido, sigungu, site_name, source_provider, provider_reference_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT resolution_status, priority, source_provider, COUNT(*) AS queue_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_auction_case_resolution_queue
                    GROUP BY 1, 2, 3
                    ORDER BY queue_count DESC, resolution_status, source_provider
                    """
                )
            )
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def current_auction_search_queue_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("provider", "search_status", "priority"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"q.{quote_ident(key)} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_current_auction_search_queue"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            queue_columns = table_columns(con, "energy_site_current_auction_search_queue")

            def optional_column(column_name: str, default: str = "NULL") -> str:
                return f"q.{quote_ident(column_name)}" if column_name in queue_columns else default

            total = con.execute(f"SELECT COUNT(*) FROM energy_site_current_auction_search_queue q {where}", params).fetchone()[0]
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      q.queue_id, q.energy_site_id, q.provider, q.search_keyword, q.pnu,
                      q.road_address, q.jibun_address, q.site_name, q.priority,
                      q.search_status, q.reason, q.created_at,
                      {optional_column("imported_at")} AS imported_at,
                      {optional_column("import_run_id")} AS import_run_id,
                      {optional_column("result_case_status")} AS result_case_status,
                      {optional_column("result_case_no")} AS result_case_no,
                      {optional_column("result_note")} AS result_note,
                      m.site_category, m.site_type, m.business_status, m.sido, m.sigungu, m.address_raw
                    FROM energy_site_current_auction_search_queue q
                    LEFT JOIN energy_site_search_mart m ON m.energy_site_id = q.energy_site_id
                    {where}
                    ORDER BY
                      CASE q.search_status WHEN 'READY_FOR_EXTERNAL_PROVIDER' THEN 1 WHEN 'IMPORTED' THEN 2 ELSE 9 END,
                      CASE q.priority WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 9 END,
                      m.sido, m.sigungu, q.provider, q.site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT provider, search_status, priority, COUNT(*) AS queue_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_current_auction_search_queue
                    GROUP BY 1, 2, 3
                    ORDER BY queue_count DESC, provider, search_status
                    """
                )
            )
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def current_auction_reference_candidate_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("source_provider", "current_candidate_status", "sido", "sigungu"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{quote_ident(key)} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_current_auction_reference_candidate"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            total = con.execute(f"SELECT COUNT(*) FROM energy_site_current_auction_reference_candidate {where}", params).fetchone()[0]
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      candidate_id, energy_site_id, source_provider, provider_reference_no,
                      site_name, site_category, site_type, business_status, sido, sigungu,
                      address_raw, pnu, event_date, event_status, appraisal_value,
                      minimum_bid_value, successful_bid_value, bidder_count,
                      current_candidate_status, reason, required_action, created_at
                    FROM energy_site_current_auction_reference_candidate
                    {where}
                    ORDER BY
                      CASE current_candidate_status WHEN 'CURRENT_AUCTION_CASE_LOOKUP_REQUIRED' THEN 1 ELSE 9 END,
                      event_date,
                      sido,
                      sigungu,
                      site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT source_provider, current_candidate_status, COUNT(*) AS candidate_count,
                           COUNT(DISTINCT energy_site_id) AS site_count
                    FROM energy_site_current_auction_reference_candidate
                    GROUP BY 1, 2
                    ORDER BY candidate_count DESC, source_provider, current_candidate_status
                    """
                )
            )
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def platform_action_queue_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "priority", "action_status", "owner_role"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"q.{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_platform_action_queue"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            action_columns = table_columns(con, "energy_site_platform_action_queue")
            preflight_ready = table_exists(con, "energy_site_platform_action_preflight")
            preflight_columns = table_columns(con, "energy_site_platform_action_preflight") if preflight_ready else set()

            def optional_column(column_name: str) -> str:
                return f"q.{quote_ident(column_name)}" if column_name in action_columns else "''"

            def optional_preflight_column(column_name: str, default: str = "''") -> str:
                return f"p.{quote_ident(column_name)}" if column_name in preflight_columns else default

            preflight_select = (
                f"""
                      p.preflight_status,
                      p.total_rows AS preflight_total_rows,
                      p.candidate_rows AS preflight_candidate_rows,
                      p.missing_required_rows AS preflight_missing_required_rows,
                      {optional_preflight_column('secondary_preflight_status')} AS secondary_preflight_status,
                      {optional_preflight_column('secondary_total_rows', '0')} AS secondary_preflight_total_rows,
                      {optional_preflight_column('secondary_candidate_rows', '0')} AS secondary_preflight_candidate_rows,
                      {optional_preflight_column('secondary_missing_required_rows', '0')} AS secondary_preflight_missing_required_rows,
                      p.checked_at AS preflight_checked_at,
                """
                if preflight_ready
                else """
                      '' AS preflight_status,
                      0 AS preflight_total_rows,
                      0 AS preflight_candidate_rows,
                      0 AS preflight_missing_required_rows,
                      '' AS secondary_preflight_status,
                      0 AS secondary_preflight_total_rows,
                      0 AS secondary_preflight_candidate_rows,
                      0 AS secondary_preflight_missing_required_rows,
                      '' AS preflight_checked_at,
                """
            )
            preflight_join = "LEFT JOIN energy_site_platform_action_preflight p ON p.action_id = q.action_id" if preflight_ready else ""
            params.append(limit)
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      q.action_id, q.gate_id, q.gate_group, q.gate_name, q.priority,
                      q.action_status, q.issue_count, q.total_sites, q.current_metric,
                      q.target_metric, q.blocker_summary, q.workpack_dir,
                      q.workpack_template,
                      {optional_column('workpack_file')} AS workpack_file,
                      {optional_column('secondary_workpack_dir')} AS secondary_workpack_dir,
                      {optional_column('secondary_workpack_template')} AS secondary_workpack_template,
                      {optional_column('secondary_workpack_file')} AS secondary_workpack_file,
                      {optional_column('secondary_note')} AS secondary_note,
                      q.workpack_report, q.import_script,
                      q.verify_script, q.completion_condition, q.next_command,
                      {optional_column('dry_run_command')} AS dry_run_command,
                      {optional_column('import_command')} AS import_command,
                      {optional_column('secondary_dry_run_command')} AS secondary_dry_run_command,
                      {optional_column('secondary_import_command')} AS secondary_import_command,
                      {optional_column('post_import_command')} AS post_import_command,
                      {optional_column('completion_command')} AS completion_command,
                      {optional_column('command_note')} AS command_note,
                      {preflight_select}
                      q.owner_role, q.detail_json, q.created_at, q.updated_at
                    FROM energy_site_platform_action_queue q
                    {preflight_join}
                    {where}
                    ORDER BY
                      CASE q.priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 ELSE 9 END,
                      q.issue_count DESC,
                      q.gate_id
                    LIMIT ?
                    """,
                    params,
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT priority, action_status, COUNT(*) AS count, SUM(issue_count) AS issue_count
                    FROM energy_site_platform_action_queue
                    GROUP BY priority, action_status
                    ORDER BY
                      CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 ELSE 9 END,
                      action_status
                    """
                )
            )
            return {"items": rows, "count": len(rows), "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def completion_execution_board_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "gate_priority", "dependency_group", "readiness_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_completion_execution_board"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_priority, dependency_group,
                      batch_id, batch_priority, source_table, source_filter,
                      site_category, site_type, sido, provider_hint,
                      row_count, site_count, current_metric, target_metric,
                      search_pack_path, result_template_path,
                      dry_run_command, import_command, post_command,
                      completion_command, readiness_status, execution_score,
                      execution_reason, created_at
                    FROM energy_site_completion_execution_board
                    {where}
                    ORDER BY rank_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT
                      gate_id, gate_name, gate_priority, dependency_group,
                      COUNT(*) AS batch_count,
                      SUM(row_count) AS row_count,
                      SUM(site_count) AS site_count,
                      MIN(rank_no) AS first_rank
                    FROM energy_site_completion_execution_board
                    GROUP BY gate_id, gate_name, gate_priority, dependency_group
                    ORDER BY first_rank
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_completion_execution_board").fetchone()[0]
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def threshold_execution_board_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 100)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "gate_status", "result_file_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_threshold_execution_board"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_status, current_metric, target_metric,
                      selected_site_count, selected_result_row_count, threshold_pack_table,
                      threshold_pack_csv, result_file_status, importer_script, input_argument,
                      dry_run_command, import_command, post_import_command, completion_command,
                      blocker_summary, operator_instruction, created_at
                    FROM energy_site_threshold_execution_board
                    {where}
                    ORDER BY rank_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT
                      gate_status, result_file_status,
                      COUNT(*) AS gate_count,
                      SUM(selected_site_count) AS selected_site_count,
                      SUM(selected_result_row_count) AS selected_result_row_count
                    FROM energy_site_threshold_execution_board
                    GROUP BY gate_status, result_file_status
                    ORDER BY gate_status, result_file_status
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_threshold_execution_board").fetchone()[0]
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def threshold_gate_runner_plan_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        requested_gate = query.get("gate_id", "").strip()
        requested_input = query.get("input", "").strip()
        db_path = os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH)
        root = data_root()

        def quoted(value: str) -> str:
            return '"' + str(value).replace('"', '\\"') + '"'

        def input_status(gate_id: str) -> dict[str, Any]:
            model_gate = gate_id in {"G10_VALUATION", "G12_PREDICTION"}
            if model_gate:
                return {"input_required": False, "input_status": "MODEL_READY", "input_file_exists": False, "input_inside_data_root": True}
            if not requested_input:
                return {"input_required": True, "input_status": "INPUT_REQUIRED", "input_file_exists": False, "input_inside_data_root": False}
            if "FILLED_RESULT_CSV" in requested_input:
                return {"input_required": True, "input_status": "PLACEHOLDER_BLOCKED", "input_file_exists": False, "input_inside_data_root": False}
            path = Path(requested_input)
            exists = path.exists() and path.is_file()
            try:
                inside_root = exists and path.resolve().is_relative_to(root.resolve())
            except OSError:
                inside_root = False
            if not exists:
                status = "FILE_NOT_FOUND"
            elif not inside_root:
                status = "OUTSIDE_DATA_ROOT"
            else:
                status = "READY_FOR_DRY_RUN"
            return {"input_required": True, "input_status": status, "input_file_exists": exists, "input_inside_data_root": inside_root}

        def command(gate_id: str, mode: str, input_path: str = "") -> str:
            parts = [
                "python scripts/run_energy_site_threshold_gate.py",
                "--db",
                quoted(db_path),
                "--gate-id",
                gate_id,
                "--mode",
                mode,
            ]
            if input_path:
                parts.extend(["--input", quoted(input_path)])
            return " ".join(parts)

        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_threshold_execution_board"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED", "data_root": str(root)}
            filters: list[str] = []
            params: list[Any] = []
            if requested_gate:
                filters.append("gate_id = ?")
                params.append(requested_gate)
            where = f"WHERE {' AND '.join(filters)}" if filters else ""
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_status, selected_site_count,
                      selected_result_row_count, threshold_pack_csv, result_file_status,
                      blocker_summary, operator_instruction
                    FROM energy_site_threshold_execution_board
                    {where}
                    ORDER BY rank_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            items: list[dict[str, Any]] = []
            for row in rows:
                gate_id = str(row.get("gate_id") or "")
                status = input_status(gate_id)
                has_ready_input = status["input_status"] == "READY_FOR_DRY_RUN"
                model_gate = gate_id in {"G10_VALUATION", "G12_PREDICTION"}
                plan_input = requested_input if requested_input else ""
                items.append(
                    {
                        **row,
                        **status,
                        "input_path": requested_input,
                        "data_root": str(root),
                        "plan_command": command(gate_id, "plan", plan_input),
                        "safe_dry_run_command": "" if model_gate else command(gate_id, "dry-run", requested_input if has_ready_input else "{FILLED_RESULT_CSV}"),
                        "safe_import_command": command(gate_id, "import", requested_input if (has_ready_input and not model_gate) else ("{FILLED_RESULT_CSV}" if not model_gate else "")),
                        "safe_post_command": command(gate_id, "post"),
                        "command_lock_reason": "" if has_ready_input or model_gate else status["input_status"],
                        "dry_run_enabled": has_ready_input,
                        "import_enabled": has_ready_input or model_gate,
                        "post_enabled": True,
                        "safety_policy": "실행 전 filled result CSV는 LOAN4U_DATA_ROOT 아래 실제 파일이어야 하며 placeholder는 차단됩니다.",
                    }
                )
            summary: dict[str, int] = {}
            for item in items:
                key = str(item.get("input_status") or "UNKNOWN")
                summary[key] = summary.get(key, 0) + 1
            total = con.execute("SELECT COUNT(*) FROM energy_site_threshold_execution_board").fetchone()[0]
            return {"items": items, "count": total, "summary": summary, "source_status": "READY", "data_root": str(root)}
        finally:
            con.close()

    def threshold_result_workpack_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        requested_gate = query.get("gate_id", "").strip()
        filters: list[str] = []
        params: list[Any] = []
        if requested_gate:
            filters.append("gate_id = ?")
            params.append(requested_gate)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_threshold_result_workpack"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      gate_id, gate_name, workpack_type, search_pack_path, result_template_path,
                      required_fields_json, row_count, site_count, input_status,
                      plan_command, dry_run_command, import_command, post_command,
                      operator_instruction, created_at
                    FROM energy_site_threshold_result_workpack
                    {where}
                    ORDER BY CASE gate_id
                      WHEN 'G3_LOCATION' THEN 3
                      WHEN 'G4_LAND' THEN 4
                      WHEN 'G5_BUILDING' THEN 5
                      WHEN 'G6_STORAGE' THEN 6
                      WHEN 'G7_AUCTION_HISTORY' THEN 7
                      WHEN 'G8_CURRENT_AUCTION' THEN 8
                      WHEN 'G9_CARD_FINANCIAL' THEN 9
                      WHEN 'G10_VALUATION' THEN 10
                      WHEN 'G11_PLANNING' THEN 11
                      WHEN 'G12_PREDICTION' THEN 12
                      ELSE 99
                    END
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT input_status, workpack_type, COUNT(*) AS gate_count,
                           SUM(row_count) AS row_count, SUM(site_count) AS site_count
                    FROM energy_site_threshold_result_workpack
                    GROUP BY input_status, workpack_type
                    ORDER BY input_status, workpack_type
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_threshold_result_workpack").fetchone()[0]
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def external_impact_priority_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filter_keys = ("gate_id", "gate_priority", "dependency_group", "readiness_status")
        requested = {key: query.get(key, "").strip() for key in filter_keys}
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_platform_completion_gate") or not table_exists(con, "energy_site_search_mart"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}

            board_ready = table_exists(con, "energy_site_completion_execution_board")
            blocker_ready = table_exists(con, "energy_site_external_dependency_blocker")
            total_sites = int(scalar(con, "SELECT COUNT(*) FROM energy_site_search_mart"))
            gates = rows_to_dicts(
                con.execute(
                    """
                    SELECT gate_id, gate_group, gate_name, gate_status, current_metric, target_metric
                    FROM energy_site_platform_completion_gate
                    WHERE required_for_100 = true
                      AND gate_status = 'FAIL'
                    ORDER BY gate_id
                    """
                )
            )
            blockers = {
                item["gate_id"]: item
                for item in rows_to_dicts(
                    con.execute(
                        """
                        SELECT
                          gate_id,
                          max(blocker_group) AS blocker_group,
                          string_agg(DISTINCT blocker_type, ', ' ORDER BY blocker_type) AS blocker_type,
                          string_agg(DISTINCT required_source, ', ' ORDER BY required_source) AS required_source,
                          max(current_count) AS current_count,
                          max(required_count) AS required_count,
                          sum(open_count) AS open_count,
                          string_agg(DISTINCT next_action, ' / ' ORDER BY next_action) AS next_action
                        FROM energy_site_external_dependency_blocker
                        GROUP BY gate_id
                        """
                    )
                )
            } if blocker_ready else {}
            top_batches: dict[str, dict[str, Any]] = {}
            if board_ready:
                for item in rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_completion_execution_board
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY gate_id ORDER BY rank_no) = 1
                        """
                    )
                ):
                    top_batches[item["gate_id"]] = item
                for item in rows_to_dicts(
                    con.execute(
                        """
                        SELECT gate_id, COUNT(*) AS batch_count, SUM(row_count) AS total_batch_rows,
                               SUM(site_count) AS total_batch_sites
                        FROM energy_site_completion_execution_board
                        GROUP BY gate_id
                        """
                    )
                ):
                    top_batches.setdefault(item["gate_id"], {}).update(item)

            rows: list[dict[str, Any]] = []
            gate_order = {
                "G3_LOCATION": 10,
                "G4_LAND": 20,
                "G5_BUILDING": 30,
                "G6_STORAGE": 40,
                "G7_AUCTION_HISTORY": 50,
                "G8_CURRENT_AUCTION": 60,
                "G9_CARD_FINANCIAL": 70,
                "G10_VALUATION": 80,
                "G11_PLANNING": 90,
                "G12_PREDICTION": 100,
            }
            for gate in gates:
                gate_id = gate.get("gate_id")
                batch = top_batches.get(gate_id, {})
                blocker = blockers.get(gate_id, {})
                current_metric = float(gate.get("current_metric") or 0)
                target_metric = float(gate.get("target_metric") or 0)
                threshold_gap = max(math.ceil((target_metric - current_metric) * total_sites), 0)
                open_count = int(blocker.get("open_count") or threshold_gap)
                top_sites = int(batch.get("site_count") or batch.get("row_count") or 0)
                estimated_done = min(top_sites, open_count)
                priority = batch.get("gate_priority") or ("P0" if str(gate_id) in {"G3_LOCATION", "G4_LAND", "G5_BUILDING", "G6_STORAGE", "G7_AUCTION_HISTORY", "G8_CURRENT_AUCTION"} else "P1")
                impact_score = (
                    {"P0": 1_000_000, "P1": 500_000}.get(str(priority), 100_000)
                    - gate_order.get(str(gate_id), 999) * 1000
                    + open_count
                    + min(top_sites, 1000) * 0.1
                )
                rows.append(
                    {
                        "gate_id": gate_id,
                        "gate_name": gate.get("gate_name") or gate_id,
                        "gate_priority": priority,
                        "dependency_group": batch.get("dependency_group") or blocker.get("blocker_group") or gate.get("gate_group") or "",
                        "gate_status": gate.get("gate_status"),
                        "current_metric": current_metric,
                        "target_metric": target_metric,
                        "total_sites": total_sites,
                        "current_count": int(blocker.get("current_count") or round(current_metric * total_sites)),
                        "required_count": int(blocker.get("required_count") or round(target_metric * total_sites)),
                        "open_count": open_count,
                        "threshold_gap_sites": threshold_gap,
                        "batch_count": int(batch.get("batch_count") or 0),
                        "top_batch_id": batch.get("batch_id") or "",
                        "top_batch_rows": int(batch.get("row_count") or 0),
                        "top_batch_sites": top_sites,
                        "top_batch_priority": batch.get("batch_priority") or "",
                        "readiness_status": batch.get("readiness_status") or "INPUT_WAITING",
                        "result_template_path": batch.get("result_template_path") or "",
                        "dry_run_command": batch.get("dry_run_command") or "",
                        "import_command": batch.get("import_command") or "",
                        "post_command": batch.get("post_command") or "",
                        "completion_command": batch.get("completion_command") or "",
                        "required_source": blocker.get("required_source") or "",
                        "blocker_type": blocker.get("blocker_type") or "",
                        "next_action": blocker.get("next_action") or batch.get("execution_reason") or "",
                        "estimated_metric_gain": round(estimated_done / total_sites, 6) if total_sites else 0,
                        "estimated_remaining_after_top_batch": max(open_count - estimated_done, 0),
                        "impact_score": round(impact_score, 3),
                    }
                )

            for key, value in requested.items():
                if value:
                    rows = [item for item in rows if str(item.get(key) or "") == value]
            rows.sort(key=lambda item: (-float(item.get("impact_score") or 0), str(item.get("gate_id") or "")))
            for index, item in enumerate(rows, 1):
                item["rank_no"] = index

            summary_map: dict[tuple[str, str], dict[str, Any]] = {}
            for item in rows:
                key = (str(item.get("gate_priority") or ""), str(item.get("readiness_status") or ""))
                bucket = summary_map.setdefault(
                    key,
                    {"gate_priority": key[0], "readiness_status": key[1], "gate_count": 0, "open_count": 0, "top_batch_sites": 0, "estimated_metric_gain": 0.0},
                )
                bucket["gate_count"] += 1
                bucket["open_count"] += int(item.get("open_count") or 0)
                bucket["top_batch_sites"] += int(item.get("top_batch_sites") or 0)
                bucket["estimated_metric_gain"] = round(float(bucket["estimated_metric_gain"]) + float(item.get("estimated_metric_gain") or 0), 6)
            return {
                "items": rows[:limit],
                "count": len(rows),
                "summary": list(summary_map.values()),
                "top_gate": rows[0]["gate_id"] if rows else "",
                "top_batch": rows[0]["top_batch_id"] if rows else "",
                "source_status": "READY" if board_ready else "DYNAMIC_FALLBACK",
                "calculation_mode": "LIVE_READ_ONLY",
                "db_persisted": table_exists(con, "energy_site_external_impact_priority"),
            }
        finally:
            con.close()

    def completion_execution_ledger_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        filters: list[str] = []
        params: list[Any] = []
        for key in ("gate_id", "gate_priority", "dependency_group", "execution_status"):
            value = query.get(key, "").strip()
            if value:
                filters.append(f"{key} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_completion_execution_ledger"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      rank_no, gate_id, gate_name, gate_priority, dependency_group,
                      batch_id, batch_priority, row_count, site_count,
                      result_template_path, search_pack_path,
                      result_file_exists, result_row_count, filled_result_rows,
                      signal_columns_json, execution_status, readiness_status,
                      assigned_to, started_at, completed_at, blocked_reason,
                      evidence_report_path, import_report_path,
                      dry_run_command, import_command, post_command,
                      completion_command, operator_note, last_checked_at,
                      updated_at
                    FROM energy_site_completion_execution_ledger
                    {where}
                    ORDER BY
                      CASE execution_status
                        WHEN 'READY_FOR_DRY_RUN' THEN 1
                        WHEN 'IN_PROGRESS' THEN 2
                        WHEN 'BLOCKED' THEN 3
                        WHEN 'INPUT_WAITING' THEN 4
                        ELSE 9
                      END,
                      rank_no
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT
                      gate_id, gate_name, gate_priority, dependency_group,
                      execution_status,
                      COUNT(*) AS batch_count,
                      SUM(row_count) AS row_count,
                      SUM(site_count) AS site_count,
                      MIN(rank_no) AS first_rank
                    FROM energy_site_completion_execution_ledger
                    GROUP BY gate_id, gate_name, gate_priority, dependency_group, execution_status
                    ORDER BY first_rank, execution_status
                    """
                )
            )
            status_summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT execution_status, COUNT(*) AS batch_count, SUM(row_count) AS row_count
                    FROM energy_site_completion_execution_ledger
                    GROUP BY execution_status
                    ORDER BY batch_count DESC, execution_status
                    """
                )
            )
            total = con.execute("SELECT COUNT(*) FROM energy_site_completion_execution_ledger").fetchone()[0]
            return {"items": rows, "count": total, "summary": summary, "status_summary": status_summary, "source_status": "READY"}
        finally:
            con.close()

    def completion_input_gap_items(self, query: dict[str, str]) -> dict[str, Any]:
        required_columns = {
            "G3_LOCATION": ["coord_x", "coord_y"],
            "G4_LAND": ["land_area_m2"],
            "G5_BUILDING": ["building_area_m2", "building_name", "building_register_pk", "gross_floor_area_m2", "main_use"],
            "G6_STORAGE": ["capacity_value", "tank_count"],
            "G7_AUCTION_HISTORY": [
                "appraisal_value",
                "award_date",
                "bidder_count",
                "case_no",
                "court_name",
                "event_date",
                "event_status",
                "minimum_bid_value",
                "provider_result_status",
                "successful_bid_value",
                "valuation_date",
            ],
            "G8_CURRENT_AUCTION": ["appraisal_value", "bid_due_date", "case_no", "case_status", "court_name", "current_round", "minimum_bid_value", "previous_failed_count"],
            "G9_CARD_FINANCIAL": ["average_ticket_amount", "card_sales_amount", "card_transaction_count", "estimated_total_sales_amount", "fuel_sales_amount", "nonfuel_sales_amount"],
            "G10_VALUATION": [
                "debt_amount",
                "ebitda_amount",
                "gross_profit_amount",
                "interest_expense_amount",
                "labor_expense_amount",
                "operating_profit_amount",
                "rent_expense_amount",
                "revenue_amount",
                "utility_expense_amount",
            ],
            "G11_PLANNING": ["announcement_date", "announcement_no", "authority_name", "effective_date", "event_id", "event_type", "impact_score", "plan_name", "road_name"],
            "G12_PREDICTION": [],
        }
        limit = min(max(int(query.get("limit", "20")), 1), 100)
        con = connect(read_only=True)
        try:
            if table_exists(con, "energy_site_completion_input_gap"):
                rows = rows_to_dicts(
                    con.execute(
                        """
                        SELECT *
                        FROM energy_site_completion_input_gap
                        ORDER BY first_rank
                        LIMIT ?
                        """,
                        [limit],
                    )
                )
                total = con.execute("SELECT COUNT(*) FROM energy_site_completion_input_gap").fetchone()[0]
                return {"items": rows, "count": total, "source_status": "READY"}
            if not table_exists(con, "energy_site_completion_execution_ledger"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    """
                    SELECT
                      gate_id, gate_name, gate_priority, dependency_group,
                      COUNT(*) AS batch_count,
                      SUM(COALESCE(result_row_count, row_count, 0)) AS result_rows,
                      SUM(COALESCE(filled_result_rows, 0)) AS filled_rows,
                      SUM(COALESCE(result_row_count, row_count, 0) - COALESCE(filled_result_rows, 0)) AS missing_rows,
                      SUM(CASE WHEN execution_status = 'READY_FOR_DRY_RUN' THEN 1 ELSE 0 END) AS ready_batch_count,
                      SUM(CASE WHEN execution_status = 'INPUT_WAITING' THEN 1 ELSE 0 END) AS input_waiting_batch_count,
                      MIN(rank_no) AS first_rank,
                      arg_min(batch_id, rank_no) AS top_batch_id,
                      arg_min(result_template_path, rank_no) AS top_result_template_path
                    FROM energy_site_completion_execution_ledger
                    GROUP BY gate_id, gate_name, gate_priority, dependency_group
                    ORDER BY first_rank
                    LIMIT ?
                    """,
                    [limit],
                )
            )
            for row in rows:
                columns = required_columns.get(str(row.get("gate_id") or ""), [])
                row["required_columns_json"] = json.dumps(columns, ensure_ascii=False)
                row["recommended_next_action"] = " / ".join(columns) + " 입력 후 해당 importer dry-run 실행" if columns else "선행 입력 완료 후 모델 재실행"
            total = con.execute("SELECT COUNT(DISTINCT gate_id) FROM energy_site_completion_execution_ledger").fetchone()[0]
            return {"items": rows, "count": total, "source_status": "DYNAMIC_FROM_LEDGER"}
        finally:
            con.close()

    def location_land_building_gap_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 200)
        filters: list[str] = []
        params: list[Any] = []
        if query.get("gap_level"):
            filters.append("gap_level = ?")
            params.append(query["gap_level"])
        if query.get("sido"):
            filters.append("sido = ?")
            params.append(query["sido"])
        if query.get("site_category"):
            filters.append("site_category = ?")
            params.append(query["site_category"])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_g3_g5_gap"):
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT
                      energy_site_id, site_name, site_category, site_type, fuel_types,
                      business_status, sido, sigungu, address_raw,
                      latitude, longitude, coordinate_status,
                      representative_lot_no, linked_lot_count, total_land_area_m2,
                      building_link_count, primary_building_use,
                      primary_building_area_m2, primary_gross_floor_area_m2,
                      gap_level, gap_reason_codes, recommended_next_action
                    FROM energy_site_g3_g5_gap
                    {where}
                    ORDER BY
                      CASE gap_level WHEN 'P0_CRITICAL' THEN 1 WHEN 'P1_HIGH' THEN 2 WHEN 'P2_MEDIUM' THEN 3 ELSE 4 END,
                      sido,
                      sigungu,
                      site_category,
                      site_name
                    LIMIT ?
                    """,
                    [*params, limit],
                )
            )
            total = con.execute(f"SELECT COUNT(*) FROM energy_site_g3_g5_gap {where}", params).fetchone()[0]
            summary = rows_to_dicts(
                con.execute(
                    """
                    SELECT
                      gap_level,
                      COUNT(*) AS site_count,
                      SUM(CASE WHEN missing_coordinate THEN 1 ELSE 0 END) AS missing_coordinate_sites,
                      SUM(CASE WHEN missing_pnu THEN 1 ELSE 0 END) AS missing_pnu_sites,
                      SUM(CASE WHEN missing_land_area THEN 1 ELSE 0 END) AS missing_land_area_sites,
                      SUM(CASE WHEN missing_building THEN 1 ELSE 0 END) AS missing_building_sites
                    FROM energy_site_g3_g5_gap
                    GROUP BY gap_level
                    ORDER BY CASE gap_level WHEN 'P0_CRITICAL' THEN 1 WHEN 'P1_HIGH' THEN 2 WHEN 'P2_MEDIUM' THEN 3 ELSE 4 END
                    """
                )
            )
            return {"items": rows, "count": total, "summary": summary, "source_status": "READY"}
        finally:
            con.close()

    def g3_g5_workpack_source(self, con: duckdb.DuckDBPyConnection) -> tuple[str, str] | None:
        if table_exists(con, "energy_site_g3_g5_workpack_index"):
            return "SELECT * FROM energy_site_g3_g5_workpack_index", "READY"
        parts: list[str] = []
        if table_exists(con, "energy_site_geocode_batch_manifest"):
            parts.append(
                """
                SELECT
                  batch_id AS workpack_id, 'G3_LOCATION' AS gate_id, 10 AS work_order,
                  '좌표 확인' AS workpack_kind, priority, site_category, site_type, sido,
                  row_count, readiness_status, search_pack_path, result_template_path,
                  dry_run_command, import_command, NULL AS post_import_command, apply_command,
                  '좌표가 확정되어야 지도, PNU 후보, 토지·건물 매칭 정확도가 올라갑니다.' AS dependency_rule,
                  created_at
                FROM energy_site_geocode_batch_manifest
                """
            )
        if table_exists(con, "energy_site_land_area_batch_manifest"):
            parts.append(
                """
                SELECT
                  batch_id AS workpack_id, 'G4_LAND' AS gate_id, 20 AS work_order,
                  '토지 지번·면적 확인' AS workpack_kind, priority, site_category, site_type, sido,
                  row_count, readiness_status, search_pack_path, result_template_path,
                  dry_run_command, import_command, post_import_command, NULL AS apply_command,
                  '대표 토지 지번과 연결 토지 면적이 확정되어야 총 토지면적과 경매 주소 검증이 가능합니다.' AS dependency_rule,
                  created_at
                FROM energy_site_land_area_batch_manifest
                """
            )
        if table_exists(con, "energy_site_building_batch_manifest"):
            parts.append(
                """
                SELECT
                  batch_id AS workpack_id, 'G5_BUILDING' AS gate_id, 30 AS work_order,
                  '건축물대장 건물 확인' AS workpack_kind, priority, site_category, site_type, sido,
                  row_count, readiness_status, search_pack_path, result_template_path,
                  dry_run_command, import_command, post_import_command, NULL AS apply_command,
                  'PNU 또는 주소 기준으로 건축물대장 링크를 확정해야 건물면적, 시설 현황, 위험물 시설 추정이 가능합니다.' AS dependency_rule,
                  created_at
                FROM energy_site_building_batch_manifest
                """
            )
        if not parts:
            return None
        return " UNION ALL ".join(parts), "DYNAMIC_FROM_GATE_MANIFEST"

    def g3_g5_workpack_index_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "20")), 1), 200)
        con = connect(read_only=True)
        try:
            source = self.g3_g5_workpack_source(con)
            if not source:
                return {"items": [], "count": 0, "summary": [], "source_status": "SOURCE_NOT_LOADED"}
            source_sql, source_status = source
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT *
                    FROM ({source_sql}) AS w
                    ORDER BY work_order, priority, site_category, site_type, sido, workpack_id
                    LIMIT ?
                    """,
                    [limit],
                )
            )
            total = con.execute(f"SELECT COUNT(*) FROM ({source_sql}) AS w").fetchone()[0]
            summary = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT gate_id, workpack_kind, COUNT(*) AS workpack_count, SUM(row_count) AS row_count
                    FROM ({source_sql}) AS w
                    GROUP BY gate_id, workpack_kind
                    ORDER BY MIN(work_order)
                    """
                )
            )
            return {"items": rows, "count": total, "summary": summary, "source_status": source_status}
        finally:
            con.close()

    def g3_g5_workpack_file_csv(self, query: dict[str, str], request_id: str, actor: dict[str, Any]) -> None:
        workpack_id = query.get("workpack_id", "").strip()
        file_kind = query.get("file", "template").strip().lower() or "template"
        column_by_kind = {"search": "search_pack_path", "workpack": "search_pack_path", "template": "result_template_path", "result": "result_template_path"}
        column = column_by_kind.get(file_kind)
        if not workpack_id or not column:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_G3_G5_WORKPACK_FILE_REQUEST", "workpack_id and file=search|template are required")

        con = connect(read_only=True)
        try:
            source = self.g3_g5_workpack_source(con)
            if not source:
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "G3_G5_WORKPACK_NOT_READY", "G3~G5 workpack index is not ready")
            source_sql, _ = source
            row = con.execute(
                f"""
                SELECT workpack_id, gate_id, {quote_ident(column)} AS file_path
                FROM ({source_sql}) AS w
                WHERE workpack_id = ?
                LIMIT 1
                """,
                [workpack_id],
            ).fetchone()
        finally:
            con.close()

        if not row:
            raise ApiError(HTTPStatus.NOT_FOUND, "G3_G5_WORKPACK_NOT_FOUND", "G3~G5 workpack was not found")
        raw_path = str(row[2] or "").strip()
        if not raw_path:
            raise ApiError(HTTPStatus.NOT_FOUND, "G3_G5_WORKPACK_FILE_NOT_READY", "requested workpack file is not registered")
        path = Path(raw_path)
        if not path.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, "G3_G5_WORKPACK_FILE_NOT_FOUND", "requested workpack file is missing", {"path": path.name})
        resolved = path.resolve()
        if resolved.suffix.lower() != ".csv" or not self.is_allowed_action_file(resolved):
            raise ApiError(HTTPStatus.FORBIDDEN, "G3_G5_WORKPACK_FILE_FORBIDDEN", "requested workpack file is outside the allowed export area")

        self.log_audit_event(
            actor,
            "DOWNLOAD_G3_G5_WORKPACK",
            "energy_site_g3_g5_workpack_index",
            workpack_id,
            "SUCCESS",
            request_id,
            {"file_kind": file_kind, "gate_id": row[1], "filename": resolved.name},
        )
        self.file_response(resolved, f"{row[1]}_{file_kind}_{resolved.name}")

    def platform_action_queue_file_csv(self, query: dict[str, str], request_id: str, actor: dict[str, Any]) -> None:
        action_id = query.get("action_id", "").strip()
        file_kind = query.get("file", "template").strip().lower() or "template"
        column_by_kind = {
            "template": "workpack_template",
            "workpack": "workpack_file",
            "secondary_template": "secondary_workpack_template",
            "secondary_workpack": "secondary_workpack_file",
        }
        column = column_by_kind.get(file_kind)
        if not action_id or not column:
            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_ACTION_FILE_REQUEST", "action_id and file=workpack|template|secondary_workpack|secondary_template are required")

        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_platform_action_queue"):
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "ACTION_QUEUE_NOT_READY", "platform action queue is not built")
            if column not in table_columns(con, "energy_site_platform_action_queue"):
                raise ApiError(HTTPStatus.NOT_FOUND, "ACTION_FILE_NOT_READY", "requested action file column is not ready")
            row = con.execute(
                f"""
                SELECT action_id, gate_id, {quote_ident(column)} AS file_path
                FROM energy_site_platform_action_queue
                WHERE action_id = ?
                LIMIT 1
                """,
                [action_id],
            ).fetchone()
        finally:
            con.close()

        if not row:
            raise ApiError(HTTPStatus.NOT_FOUND, "ACTION_NOT_FOUND", "platform action was not found")
        raw_path = str(row[2] or "").strip()
        if not raw_path:
            raise ApiError(HTTPStatus.NOT_FOUND, "ACTION_FILE_NOT_READY", "requested action file is not registered")
        path = Path(raw_path)
        if not path.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, "ACTION_FILE_NOT_FOUND", "requested action file is missing", {"path": path.name})
        resolved = path.resolve()
        if resolved.suffix.lower() != ".csv" or not self.is_allowed_action_file(resolved):
            raise ApiError(HTTPStatus.FORBIDDEN, "ACTION_FILE_FORBIDDEN", "requested action file is outside the allowed workpack area")

        self.log_audit_event(
            actor,
            "DOWNLOAD_ACTION_WORKPACK",
            "energy_site_platform_action_queue",
            action_id,
            "SUCCESS",
            request_id,
            {"file_kind": file_kind, "gate_id": row[1], "filename": resolved.name},
        )
        self.file_response(resolved, f"{row[1]}_{file_kind}_{resolved.name}")

    def platform_coverage_snapshot_items(self, query: dict[str, str]) -> dict[str, Any]:
        limit = min(max(int(query.get("limit", "120")), 1), 500)
        con = connect(read_only=True)
        try:
            if not table_exists(con, "energy_site_platform_coverage_snapshot"):
                return {"items": [], "count": 0, "source_status": "SOURCE_NOT_LOADED"}
            snapshot_id = query.get("snapshot_id", "").strip()
            params: list[Any] = []
            where = ""
            if snapshot_id:
                where = "WHERE snapshot_id = ?"
                params.append(snapshot_id)
            params.append(limit)
            rows = rows_to_dicts(
                con.execute(
                    f"""
                    SELECT snapshot_id, metric_group, metric_name, metric_value,
                           denominator_value, coverage_ratio, metric_status,
                           detail_json, created_at
                    FROM energy_site_platform_coverage_snapshot
                    {where}
                    ORDER BY created_at DESC, metric_group, metric_name
                    LIMIT ?
                    """,
                    params,
                )
            )
            return {"items": rows, "count": len(rows), "source_status": "READY"}
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

    def log_message(self, format: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), format % args), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8055)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--vworld-map-key", default="")
    parser.add_argument("--naver-map-key-id", default="", help=argparse.SUPPRESS)
    parser.add_argument("--require-auth", action="store_true")
    parser.add_argument("--admin-token", default="")
    args = parser.parse_args()

    os.environ["DUCKDB_PATH"] = args.db
    os.environ["SERVICE_BIND_HOST"] = args.host
    if args.vworld_map_key:
        os.environ["VWORLD_MAP_KEY"] = args.vworld_map_key
    if args.require_auth:
        os.environ["SERVICE_REQUIRE_AUTH"] = "1"
    if args.admin_token:
        os.environ["SERVICE_ADMIN_TOKEN"] = args.admin_token
    try:
        con = connect(read_only=False)
        try:
            ensure_operational_tables(con)
            if auth_required() and not has_enabled_admin_token(con):
                raise SystemExit(
                    "SERVICE_REQUIRE_AUTH is enabled, but no enabled ADMIN token exists. "
                    "Set --admin-token or SERVICE_ADMIN_TOKEN before external exposure."
                )
        finally:
            con.close()
    except Exception as exc:
        print(f"startup_db_init=deferred reason={str(exc)[:240]}", flush=True)
    server = ThreadingHTTPServer((args.host, args.port), MvpHandler)
    print(f"Serving on http://{args.host}:{args.port}", flush=True)
    print(f"DUCKDB_PATH={args.db}", flush=True)
    print(f"SERVICE_REQUIRE_AUTH={auth_required()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
