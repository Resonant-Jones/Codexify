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

import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Iterable

from guardian.core.default_project import (
    DEFAULT_PROJECT_DESCRIPTION,
    DEFAULT_PROJECT_NAME,
    LEGACY_DEFAULT_PROJECT_ALIASES,
)
from guardian.core.project_lifecycle import PROJECT_SYSTEM_ROLE_GENERAL

logger = logging.getLogger("seed_defaults")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DEFAULT_PROJECT_ALIASES = (
    DEFAULT_PROJECT_NAME,
    *LEGACY_DEFAULT_PROJECT_ALIASES,
)
LEGACY_LOCAL_USER_ID = "local"

# Reuse the accepted account-Project provisioning error vocabulary without
# importing the ORM-backed provisioning module into this dependency-light
# migrator helper.
CANONICAL_USER_ID_REQUIRED = "canonical_user_id_required"
ACCOUNT_GENERAL_PROJECT_DUPLICATE = "account_general_project_duplicate"

# --- DB connect helpers ------------------------------------------------------


def _is_pg(dsn: str | None) -> bool:
    return bool(
        dsn and (dsn.startswith("postgres://") or dsn.startswith("postgresql://"))
    )


def _connect_pg(dsn: str):
    """
    Connect to Postgres using whatever driver is available.

    Prefer the modern ``psycopg`` v3 driver when installed, but gracefully
    fall back to ``psycopg2`` so containers or environments that only ship
    the legacy driver can still run the seed script.
    """
    try:
        import psycopg  # type: ignore[import]

        return psycopg.connect(dsn)
    except Exception:
        # Fallback path for environments that only have psycopg2-binary.
        import psycopg2  # type: ignore[import]

        return psycopg2.connect(dsn)


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
    # Treat both psycopg v3 and psycopg2 connections as Postgres.
    if "psycopg" in mod:
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


def _is_pg_conn(conn) -> bool:
    """Return True when this connection points at PostgreSQL."""
    return "psycopg" in conn.__class__.__module__


def _param(is_pg: bool) -> str:
    return "%s" if is_pg else "?"


def _in_placeholders(count: int, is_pg: bool) -> str:
    return ", ".join([_param(is_pg)] * count)


def _qualified_table_name(table: str, *, schema: str | None = None, is_pg: bool) -> str:
    def _quote(ident: str) -> str:
        return '"' + ident.replace('"', '""') + '"'

    if is_pg and schema:
        return f"{_quote(schema)}.{_quote(table)}"
    return _quote(table)


def _project_id_for_name(conn, name: str) -> int | None:
    """Return project id for a given name if present."""
    is_pg = _is_pg_conn(conn)
    placeholder = _param(is_pg)
    with _cursor(conn) as cur:
        cur.execute(
            f"SELECT id FROM projects WHERE name = {placeholder}",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return int(row[0])


def _select_projects_by_names(conn, names: Iterable[str]) -> list[tuple[int, str]]:
    """Fetch project rows for provided names."""
    name_list = [n for n in names if n]
    if not name_list:
        return []

    is_pg = _is_pg_conn(conn)
    placeholders = _in_placeholders(len(name_list), is_pg)
    with _cursor(conn) as cur:
        cur.execute(
            f"""
            SELECT id, name
            FROM projects
            WHERE name IN ({placeholders})
            ORDER BY id ASC
            """,
            name_list,
        )
        rows = cur.fetchall()
        return [(int(row[0]), str(row[1])) for row in rows]


def _canonical_account_ids(conn) -> list[str]:
    """Return deterministic canonical account IDs, excluding legacy local."""
    is_pg = _is_pg_conn(conn)
    order = 'id COLLATE "C"' if is_pg else "id COLLATE BINARY"
    with _cursor(conn) as cur:
        cur.execute(
            f"SELECT id FROM users WHERE id <> {_param(is_pg)} ORDER BY {order}",
            (LEGACY_LOCAL_USER_ID,),
        )
        account_ids = [str(row[0]) for row in cur.fetchall()]

    if any(not account_id.strip() for account_id in account_ids):
        raise RuntimeError(
            f"{CANONICAL_USER_ID_REQUIRED}: canonical users.id must be nonblank"
        )
    return account_ids


def _lock_account(cur, *, user_id: str, is_pg: bool) -> None:
    suffix = " FOR UPDATE" if is_pg else ""
    cur.execute(
        f"SELECT id FROM users WHERE id = {_param(is_pg)}{suffix}",
        (user_id,),
    )
    if cur.fetchone() is None:
        raise RuntimeError(f"canonical_user_not_found: {user_id!r}")


def _account_general_rows(cur, *, user_id: str, is_pg: bool) -> list[tuple[int, str]]:
    placeholder = _param(is_pg)
    cur.execute(
        f"""
        SELECT id, name
        FROM projects
        WHERE user_id = {placeholder}
          AND system_role = {placeholder}
        ORDER BY id ASC
        """,
        (user_id, PROJECT_SYSTEM_ROLE_GENERAL),
    )
    return [(int(row[0]), str(row[1])) for row in cur.fetchall()]


def _account_legacy_alias_rows(
    cur,
    *,
    user_id: str,
    is_pg: bool,
) -> list[tuple[int, str]]:
    placeholder = _param(is_pg)
    aliases = tuple(dict.fromkeys(DEFAULT_PROJECT_ALIASES))
    alias_placeholders = _in_placeholders(len(aliases), is_pg)
    cur.execute(
        f"""
        SELECT id, name
        FROM projects
        WHERE user_id = {placeholder}
          AND system_role IS NULL
          AND name IN ({alias_placeholders})
        ORDER BY id ASC
        """,
        (user_id, *aliases),
    )
    return [(int(row[0]), str(row[1])) for row in cur.fetchall()]


def seed_account_default_projects(conn) -> dict[str, int]:
    """Converge one structural General per canonical, non-local account.

    The operation is one transaction. Existing structural Generals are left
    byte-for-byte unchanged. A sole same-account legacy alias is promoted in
    place, preserving its Project ID, description, and references. Multiple
    same-account candidates fail closed. No Project reference is reassigned or
    Project row deleted by this seeder.
    """
    if not table_exists(conn, "users"):
        raise RuntimeError("canonical users table is required for default seeding")
    if not _table_has_column(conn, "projects", "user_id") or not _table_has_column(
        conn, "projects", "system_role"
    ):
        raise RuntimeError(
            "account-scoped projects.user_id and projects.system_role are required"
        )

    account_ids = _canonical_account_ids(conn)
    is_pg = _is_pg_conn(conn)
    placeholder = _param(is_pg)
    summary = {
        "accounts": len(account_ids),
        "existing": 0,
        "promoted": 0,
        "created": 0,
    }
    cur = conn.cursor()
    try:
        for user_id in account_ids:
            _lock_account(cur, user_id=user_id, is_pg=is_pg)
            generals = _account_general_rows(
                cur,
                user_id=user_id,
                is_pg=is_pg,
            )
            if len(generals) > 1:
                raise RuntimeError(
                    f"{ACCOUNT_GENERAL_PROJECT_DUPLICATE}: canonical user "
                    f"{user_id!r} has multiple structural General Projects"
                )
            if generals:
                summary["existing"] += 1
                continue

            aliases = _account_legacy_alias_rows(
                cur,
                user_id=user_id,
                is_pg=is_pg,
            )
            if len(aliases) > 1:
                raise RuntimeError(
                    f"{ACCOUNT_GENERAL_PROJECT_DUPLICATE}: canonical user "
                    f"{user_id!r} has multiple legacy default candidates"
                )

            if aliases:
                project_id, _ = aliases[0]
                cur.execute(
                    f"""
                    UPDATE projects
                    SET name = {placeholder}, system_role = {placeholder}
                    WHERE id = {placeholder}
                      AND user_id = {placeholder}
                      AND system_role IS NULL
                    """,
                    (
                        DEFAULT_PROJECT_NAME,
                        PROJECT_SYSTEM_ROLE_GENERAL,
                        project_id,
                        user_id,
                    ),
                )
                if cur.rowcount != 1:
                    raise RuntimeError(
                        "account default Project changed during seed convergence"
                    )
                summary["promoted"] += 1
                continue

            cur.execute(
                f"""
                INSERT INTO projects (user_id, name, description, system_role)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """,
                (
                    user_id,
                    DEFAULT_PROJECT_NAME,
                    DEFAULT_PROJECT_DESCRIPTION,
                    PROJECT_SYSTEM_ROLE_GENERAL,
                ),
            )
            summary["created"] += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    return summary


def _table_has_column(
    conn,
    table: str,
    column: str,
    *,
    schema: str = "public",
) -> bool:
    """Check whether a table has a specific column."""
    is_pg = _is_pg_conn(conn)
    if is_pg:
        with _cursor(conn) as cur:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = %s
                    AND table_name = %s
                    AND column_name = %s
                )
                """,
                (schema, table, column),
            )
            return bool(cur.fetchone()[0])

    with _cursor(conn) as cur:
        cur.execute(f'PRAGMA table_info("{table}")')
        rows = cur.fetchall()
        for row in rows:
            # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
            if str(row[1]) == column:
                return True
    return False


def _discover_project_fk_tables(conn) -> list[tuple[str | None, str]]:
    """
    Discover tables with a project_id foreign key to projects.id.

    Returns tuples of (schema, table). For SQLite, schema is None.
    """
    is_pg = _is_pg_conn(conn)
    discovered: set[tuple[str | None, str]] = set()

    if is_pg:
        with _cursor(conn) as cur:
            cur.execute(
                """
                SELECT kcu.table_schema, kcu.table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                 AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'project_id'
                  AND ccu.table_schema = 'public'
                  AND ccu.table_name = 'projects'
                  AND ccu.column_name = 'id'
                ORDER BY kcu.table_schema, kcu.table_name
                """
            )
            for row in cur.fetchall():
                discovered.add((str(row[0]), str(row[1])))
    else:
        with _cursor(conn) as cur:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [str(row[0]) for row in cur.fetchall()]
        for table in tables:
            with _cursor(conn) as cur:
                cur.execute(f'PRAGMA foreign_key_list("{table}")')
                for row in cur.fetchall():
                    # PRAGMA foreign_key_list columns:
                    # id, seq, table, from, to, on_update, on_delete, match
                    ref_table = str(row[2])
                    from_col = str(row[3])
                    to_col = str(row[4])
                    if (
                        ref_table == "projects"
                        and from_col == "project_id"
                        and to_col == "id"
                    ):
                        discovered.add((None, table))

    # Keep old schemas safe: chat_threads can exist without FK in older DBs.
    if table_exists(conn, "chat_threads") and _table_has_column(
        conn, "chat_threads", "project_id"
    ):
        discovered.add(("public", "chat_threads") if is_pg else (None, "chat_threads"))

    # Never mutate projects directly in reassignment loop.
    discovered.discard(("public", "projects"))
    discovered.discard((None, "projects"))

    return sorted(discovered, key=lambda item: (item[0] or "", item[1]))


def dedupe_default_project_aliases(
    conn,
    *,
    canonical_name: str = DEFAULT_PROJECT_NAME,
    aliases: Iterable[str] = DEFAULT_PROJECT_ALIASES,
) -> tuple[int, list[int], dict[str, int]]:
    """Support pre-account-schema alias tests without modern global mutation.

    Current account-scoped schemas must use ``seed_account_default_projects``;
    that path promotes one same-account alias in place and never reassigns or
    deletes Project-bound rows. This compatibility helper only applies to a
    historical schema that has no ``projects.user_id`` column and therefore
    cannot represent multiple account boundaries. It never creates a Project.
    """
    if _table_has_column(conn, "projects", "user_id"):
        raise RuntimeError(
            "account-scoped default seeding does not deduplicate Project rows"
        )

    alias_names = tuple(dict.fromkeys([canonical_name, *list(aliases)]))
    keep_id = _project_id_for_name(conn, canonical_name)
    if keep_id is None:
        raise RuntimeError(
            "pre-account compatibility alias normalization requires an "
            f"existing canonical project named {canonical_name!r}"
        )

    alias_rows = _select_projects_by_names(conn, alias_names)
    remove_ids = sorted(
        project_id for project_id, _ in alias_rows if project_id != keep_id
    )
    if not remove_ids:
        logger.info("[Seed] Default project aliases already normalized.")
        return keep_id, [], {}

    project_tables = _discover_project_fk_tables(conn)
    is_pg = _is_pg_conn(conn)
    update_counts: dict[str, int] = {}
    keep_placeholder = _param(is_pg)
    in_placeholders = _in_placeholders(len(remove_ids), is_pg)
    params = [keep_id, *remove_ids]

    with _cursor(conn) as cur:
        for schema, table in project_tables:
            target = _qualified_table_name(table, schema=schema, is_pg=is_pg)
            cur.execute(
                f"""
                UPDATE {target}
                SET project_id = {keep_placeholder}
                WHERE project_id IN ({in_placeholders})
                """,
                params,
            )
            update_counts[f"{schema + '.' if schema else ''}{table}"] = (
                cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            )

        cur.execute(
            f"DELETE FROM projects WHERE id IN ({in_placeholders})",
            remove_ids,
        )

    total_rows = sum(update_counts.values())
    logger.info(
        "[Seed] Default project alias dedup keep_id=%s removed=%s reassigned_rows=%s",
        keep_id,
        remove_ids,
        total_rows,
    )
    for table_name, count in update_counts.items():
        if count:
            logger.info("[Seed] Reassigned %s row(s) in %s", count, table_name)
    return keep_id, remove_ids, update_counts


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
            logger.warning(
                "[Seed] 'projects' table not found after wait; skipping seeding."
            )
            return 0

        logger.info("[Seed] Ensuring account-scoped default Projects exist...")
        summary = seed_account_default_projects(conn)
        logger.info(
            "[Seed] Account-scoped defaults ensured: accounts=%s existing=%s "
            "promoted=%s created=%s",
            summary["accounts"],
            summary["existing"],
            summary["promoted"],
            summary["created"],
        )

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
