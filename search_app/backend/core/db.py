from __future__ import annotations

import os
import time
from typing import Any

import duckdb

from .config import DB_CONNECT_LOCK

try:
    from service_config import building_register_db
except ModuleNotFoundError:
    from backend.service_config import building_register_db

DEFAULT_DB_PATH = building_register_db()


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
