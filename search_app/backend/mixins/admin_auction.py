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

class AdminAuctionMixin:
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


