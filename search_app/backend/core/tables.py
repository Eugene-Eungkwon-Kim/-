from __future__ import annotations

import os
import uuid

import duckdb

from .config import DEFAULT_EXPORT_TERMS_VERSION
from .db import ensure_columns, table_columns, table_exists, scalar
from .auth import hash_token
from .maps import ensure_map_provider_tables, ensure_coordinate_quality_table


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
