from __future__ import annotations

import json
import math
import os
import re
from typing import Any

import duckdb

from .config import LABELS, CHARGING_SITE_TYPES
from .db import table_exists, table_columns, first_existing_column, quote_ident


def first_env_value(names: tuple[str, ...]) -> str:
    return next((os.environ.get(name, "").strip() for name in names if os.environ.get(name, "").strip()), "")


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
    from lib.auction_case_quality import format_case_no_display  # type: ignore[import]
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
