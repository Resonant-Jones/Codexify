"""
Seed default data into the database if missing (idempotent).

This script is intentionally dependency-light:
- It does NOT import guardian.models or codexify.guardian_api.
- It talks directly to the DB (Postgres via psycopg; SQLite fallback).
- It is safe to run multiple times.

Run order assumption:
  Alembic migrations have already created base tables (including 'projects').

Environment:
  - DATABASE_URL (postgres://... or postgresql://...)
  - If DATABASE_URL is not set, falls back to SQLite at GUARDIAN_DB_PATH or ./guardian.db
"""

from __future__ import annotations

import os
import sys
import time
import logging
from contextlib import contextmanager

logger = logging.getLogger("seed_defaults")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- DB connect helpers ------------------------------------------------------

def _is_pg(dsn: str | None) -> bool:
    return bool(dsn and (dsn.startswith("postgres://") or dsn.startswith("postgresql://")))

def _connect_pg(dsn: str):
    import psycopg
    conn = psycopg.connect(dsn)
    return conn

def _connect_sqlite(path: str):
    import sqlite3
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def _cursor(conn):
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

# --- Introspection utilities -------------------------------------------------

def table_exists(conn, table: str, schema: str = "public") -> bool:
    """Return True if table exists; supports Postgres and SQLite."""
    mod = conn.__class__.__module__
    if "psycopg" in mod and "psycopg2" not in mod:
        with _cursor(conn) as cur:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema = %s AND table_name = %s
                )
                """,
                (schema, table),
            )
            return bool(cur.fetchone()[0])
    else:
        # SQLite
        with _cursor(conn) as cur:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            return cur.fetchone() is not None

def wait_for_table(conn, table: str, timeout_sec: int = 20) -> bool:
    """Poll until `table` exists or timeout elapses."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if table_exists(conn, table):
            return True
        time.sleep(0.5)
    return table_exists(conn, table)

# --- Idempotent upserts ------------------------------------------------------

def ensure_project(conn, name: str, description: str = "") -> None:
    """Insert a project row if one with the same name isn't present."""
    mod = conn.__class__.__module__
    if "psycopg" in mod and "psycopg2" not in mod:
        with _cursor(conn) as cur:
            # Use INSERT ... WHERE NOT EXISTS for maximum compatibility (no need for unique index).
            cur.execute(
                """
                INSERT INTO projects (name, description)
                SELECT %s, %s
                WHERE NOT EXISTS (
                  SELECT 1 FROM projects WHERE name = %s
                )
                """,
                (name, description, name),
            )
    else:
        # SQLite
        with _cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO projects (name, description)
                SELECT ?, ?
                WHERE NOT EXISTS (
                  SELECT 1 FROM projects WHERE name = ?
                )
                """,
                (name, description, name),
            )

# --- Main --------------------------------------------------------------------

def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if _is_pg(dsn):
        logger.info("[Seed] Connecting to Postgres...")
        try:
            conn = _connect_pg(dsn)  # type: ignore[arg-type]
        except Exception as e:
            logger.error("[Seed] Failed to connect to Postgres: %s", e)
            return 1
    else:
        db_path = os.getenv("GUARDIAN_DB_PATH", "guardian.db")
        logger.info("[Seed] Connecting to SQLite at %s ...", db_path)
        try:
            conn = _connect_sqlite(db_path)
        except Exception as e:
            logger.error("[Seed] Failed to connect to SQLite: %s", e)
            return 1

    try:
        # Ensure Alembic created 'projects' before we try to seed it
        if not wait_for_table(conn, "projects", timeout_sec=20):
            logger.warning("[Seed] 'projects' table not found after wait; skipping seeding.")
            return 0

        # Seed: default “Loose Threads” project (idempotent)
        logger.info("[Seed] Ensuring default project exists...")
        ensure_project(conn, "Loose Threads", "Default bucket for unassigned threads")
        logger.info("[Seed] Default project ensured.")

        # You can add more idempotent ensures here (e.g., initial connectors) as needed.

        logger.info("[Seed] Seeding complete.")
        return 0
    except Exception as e:
        logger.exception("[Seed] Unhandled error during seeding: %s", e)
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(main())