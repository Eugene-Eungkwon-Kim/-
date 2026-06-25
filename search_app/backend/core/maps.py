from __future__ import annotations

from typing import Any

import duckdb

from .config import DEFAULT_MAP_PROVIDERS, VWORLD_MAP_KEY_ENV_NAMES, MAP_LIBRARY_URLS
from .db import rows_to_dicts
from .utils import first_env_value


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
