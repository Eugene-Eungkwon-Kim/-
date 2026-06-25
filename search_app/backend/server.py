from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import secrets
import time
import traceback
import uuid
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

from .core.config import (
    DEFAULT_ALLOWED_CORS_ORIGINS, EXPORT_DEFAULT_LIMIT,
    EXPORT_DAILY_DOWNLOAD_LIMIT, EXPORT_DAILY_ROW_LIMIT,
)
from .core.db import connect, table_exists, scalar
from .core.auth import (
    ApiError, auth_required, default_actor, role_allows,
    hash_token, has_enabled_admin_token,
)
from .core.tables import ensure_service_security_tables, ensure_operational_tables
from .core.maps import (
    map_provider_config, fallback_map_provider_config,
    ensure_map_provider_tables, ensure_coordinate_quality_table,
)
from .mixins.admin_system import AdminSystemMixin
from .mixins.admin_audit import AdminAuditMixin
from .mixins.admin_tokens import AdminTokensMixin
from .mixins.admin_export import AdminExportMixin
from .mixins.admin_gates import AdminGatesMixin
from .mixins.admin_geocode import AdminGeocodeMixin
from .mixins.admin_auction import AdminAuctionMixin
from .mixins.admin_workboard import AdminWorkboardMixin
from .mixins.energy_sites import EnergySitesMixin
from .mixins.stations import StationsMixin

ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = ROOT_DIR / "frontend" / "index.html"

try:
    from lib.auction_case_quality import classify_case_no, format_case_no_display
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    from lib.auction_case_quality import classify_case_no, format_case_no_display


class MvpHandler(
    AdminSystemMixin,
    AdminAuditMixin,
    AdminTokensMixin,
    AdminExportMixin,
    AdminGatesMixin,
    AdminGeocodeMixin,
    AdminAuctionMixin,
    AdminWorkboardMixin,
    EnergySitesMixin,
    StationsMixin,
    BaseHTTPRequestHandler,
):
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
