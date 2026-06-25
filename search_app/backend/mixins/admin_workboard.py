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

class AdminWorkboardMixin:
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


