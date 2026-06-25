from __future__ import annotations

import hashlib
import os
from http import HTTPStatus
from typing import Any

import duckdb

from .config import ROLE_LEVELS
from .db import scalar, table_exists


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
