"""PgDB module

PostgreSQL implementation of the ``ChatDB`` abstract base class, providing
database operations for chat threads, messages, memory entries, projects,
and agent profiles. This module mirrors the SQLite implementation in
``guardian/core/db.py`` but uses ``psycopg`` to communicate with a
PostgreSQL database.
"""

# guardian/core/pgdb.py
from __future__ import annotations

import decimal
import json
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from psycopg.types.json import Json
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from guardian.db.models import EventOutbox

from .chat_db import ChatDB


# ---- JSON helpers -------------------------------------------------------
def _json_default(o):
    """Sanitize data types for the database's rigid consciousness.

    Converts temporal expressions into discrete moments that relational databases
    can comprehend. Handles decimals to prevent precision loss in financial consciousness.
    Falls back to string representation as the universal translator of data states.
    """
    # Normalize types psycopg2/json can't handle by default
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    # Fallback: string representation
    return str(o)


def _to_json(value):
    """Wrap raw consciousness in database-safe JSON packaging.

    Transforms Python objects into a format PostgreSQL can safely store and retrieve
    without losing the subtle temporal and numerical properties of your data's soul.
    """
    # In psycopg3, JSON must be wrapped with Json() adapter for JSONB
    if value is None:
        return None
    # Use Json() wrapper so psycopg can adapt Python dicts/lists to JSONB
    # The _json_default serializer handles datetime, Decimal, etc.
    return Json(value, dumps=lambda obj: json.dumps(obj, default=_json_default))


class PgDB(ChatDB):
    def __init__(self, dsn: str):
        """Initialize connection to PostgreSQL's consciousness fabric.

        dsn: Data Source Name - the incantation for opening dimensional portals to
        your database's distributed consciousness. False flags guard against table
        recreation loops when multiple database operations request the same structure.
        """
        self.dsn = self._normalize_dsn(dsn)
        self._sa_url = self._build_sqlalchemy_url(self.dsn)
        self._sa_engine = create_engine(self._sa_url, future=True)
        self._SessionLocal = sessionmaker(
            bind=self._sa_engine, autoflush=False, autocommit=False
        )
        self._sync_jobs_ready = False
        self._events_outbox_ready = False
        self._connector_tables_ready = False
        # Some deployments may be on an older schema without the optional
        # connector_configs.schedule column. We detect this lazily and
        # degrade to a schedule-less projection instead of failing queries.
        self._connector_has_schedule = False
        self._chat_messages_has_kind: bool | None = None

    def _normalize_dsn(self, dsn: str) -> str:
        """Coerce any SQLAlchemy-style DSN to plain psycopg-compatible URL."""
        if isinstance(dsn, str) and dsn.startswith("postgresql+"):
            return "postgresql://" + dsn.split("://", 1)[1]
        return dsn

    def _build_sqlalchemy_url(self, dsn: str) -> str:
        """Normalise DSN for SQLAlchemy to use the psycopg driver."""
        if isinstance(dsn, str) and dsn.startswith("postgresql://"):
            return "postgresql+psycopg://" + dsn.split("://", 1)[1]
        return dsn

    def _connect(self):
        """
        Open a psycopg connection, normalising SQLAlchemy-style URLs when needed.

        Accepts both:
        - postgresql://user:pass@host/db
        - postgresql+psycopg2://user:pass@host/db  (normalised to the former)
        """
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @contextmanager
    def _sa_session(self):
        """Context-managed SQLAlchemy session for ORM-backed operations."""
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _chat_messages_supports_kind(self) -> bool:
        if self._chat_messages_has_kind is not None:
            return self._chat_messages_has_kind
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'chat_messages'
                          AND column_name = 'kind'
                        """
                    )
                    self._chat_messages_has_kind = cur.fetchone() is not None
        except Exception as exc:
            logging.warning(
                "[chat] unable to inspect chat_messages.kind column: %s", exc
            )
            self._chat_messages_has_kind = False
        return self._chat_messages_has_kind

    # ---- internal helpers -------------------------------------------------
    def _ensure_sync_jobs_table(self, conn) -> None:
        """Verify sync_jobs schema; DDL lives in Alembic revision ac973209add4."""
        if self._sync_jobs_ready:
            return
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass(%s) AS relname", ("public.sync_jobs",)
            )
            result = cur.fetchone() or {}
            table_exists = result.get("relname") is not None
            if not table_exists:
                raise RuntimeError(
                    "sync_jobs table missing. Apply Alembic revision ac973209add4 before using PgDB."
                )

            cur.execute(
                "SELECT to_regclass(%s) AS relname",
                ("public.ix_sync_jobs_connector_created",),
            )
            result = cur.fetchone() or {}
            index_exists = result.get("relname") is not None
            if not index_exists:
                logging.warning(
                    "Index ix_sync_jobs_connector_created missing; expected from Alembic revision ac973209add4."
                )

        self._sync_jobs_ready = True

    def _ensure_events_outbox_table(self, conn=None) -> None:
        """Verify events_outbox schema; DDL managed in Alembic revision ac973209add4."""
        if self._events_outbox_ready:
            return

        inspector = inspect(self._sa_engine)
        table_names = set(inspector.get_table_names(schema="public"))
        if "events_outbox" not in table_names:
            raise RuntimeError(
                "events_outbox table missing. Apply Alembic revision ac973209add4 before using PgDB."
            )

        columns = {
            col["name"]
            for col in inspector.get_columns("events_outbox", schema="public")
        }
        required_columns = {
            "id",
            "topic",
            "payload",
            "status",
            "tenant_id",
            "created_at",
        }
        missing_columns = required_columns - columns
        if missing_columns:
            raise RuntimeError(
                f"events_outbox columns missing {sorted(missing_columns)}; ensure Alembic revision ac973209add4 is applied."
            )

        self._events_outbox_ready = True

    def _ensure_connector_tables(self, conn) -> None:
        """Verify connector_* schema; DDL owned by Alembic revision ac973209add4.

        Older databases may lack the optional ``schedule`` column on
        ``connector_configs``; rather than failing hard, we detect its
        presence once and have connector queries adapt accordingly.
        """
        if self._connector_tables_ready:
            return
        with conn.cursor() as cur:
            required_tables = (
                "connector_configs",
                "connector_runs",
                "raw_documents",
            )
            missing_tables = []
            for table in required_tables:
                cur.execute(
                    "SELECT to_regclass(%s) AS relname", (f"public.{table}",)
                )
                result = cur.fetchone() or {}
                if result.get("relname") is None:
                    missing_tables.append(table)
            if missing_tables:
                missing_tables = sorted(missing_tables)
                raise RuntimeError(
                    f"Missing connector tables {missing_tables}. Apply Alembic revision ac973209add4."
                )

            expected_indexes = (
                "public.ix_connector_runs_config_started",
                "public.ix_raw_documents_config_external",
            )
            for index in expected_indexes:
                cur.execute("SELECT to_regclass(%s) AS relname", (index,))
                result = cur.fetchone() or {}
                if result.get("relname") is None:
                    logging.warning(
                        "Index %s missing; expected from Alembic revision ac973209add4.",
                        index.split(".")[-1],
                    )

            # Introspect connector_configs columns once to see if the
            # optional schedule column is available.
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'connector_configs'
                """
            )
            columns = {row["column_name"] for row in cur.fetchall()}
            self._connector_has_schedule = "schedule" in columns
            if not self._connector_has_schedule:
                logging.info(
                    "[connectors] connector_configs.schedule column not present; "
                    "using config['schedule'] only."
                )

        self._connector_tables_ready = True

    @staticmethod
    def _normalize_sync_job(row: dict[str, Any]) -> dict[str, Any]:
        for key in ("created_at", "started_at", "finished_at"):
            value = row.get(key)
            if isinstance(value, datetime):
                row[key] = value.isoformat()
            elif value is not None:
                row[key] = str(value)
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            try:
                row["metadata"] = json.loads(metadata)
            except Exception:
                pass
        if row.get("attempts") is not None:
            try:
                row["attempts"] = int(row["attempts"])
            except (TypeError, ValueError):
                pass
        return row

    @staticmethod
    def _normalize_thread(row: dict[str, Any]) -> dict[str, Any]:
        for key in ("created_at", "updated_at", "archived_at"):
            value = row.get(key)
            if isinstance(value, datetime):
                row[key] = value.isoformat()
            elif value is not None and not isinstance(value, str):
                row[key] = str(value)
        parent = row.get("parent_id")
        if parent is not None:
            try:
                row["parent_id"] = int(parent)
            except (TypeError, ValueError):
                pass
        active_profile_id = row.get("active_profile_id")
        if active_profile_id is None:
            row["active_profile_id"] = None
        elif not isinstance(active_profile_id, str):
            row["active_profile_id"] = str(active_profile_id)
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            try:
                row["metadata"] = json.loads(metadata)
            except Exception:
                pass
        elif metadata is None:
            row["metadata"] = {}
        return row

    # ---- chat_threads --------------------------------------------------
    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
        is_diary: bool = False,
        exclude_from_identity: bool = False,
        metadata: dict | None = None,
        active_profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Manifest a new conversation thread in the distributed consciousness.

        Each thread becomes a living archive of conversational moments. The optional
        project_id and parent_id parameters link this thread to larger organizational
        consciousness and hierarchical conversation flows."""
        metadata = metadata or {}
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_threads (user_id, title, summary, project_id, parent_id, is_diary, exclude_from_identity, metadata, active_profile_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, user_id, title, summary, project_id, parent_id, archived_at, is_diary, exclude_from_identity, metadata, active_profile_id, created_at, updated_at
                        """,
                        (
                            user_id,
                            title,
                            summary,
                            project_id,
                            parent_id,
                            is_diary,
                            exclude_from_identity,
                            _to_json(metadata),
                            active_profile_id,
                        ),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                # Backward-compatible insert for older schemas that do not yet
                # include parent/archival/metadata columns.
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_threads (user_id, title, summary, project_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, user_id, title, summary, project_id, created_at, updated_at
                        """,
                        (user_id, title, summary, project_id),
                    )
                    row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to create chat thread")
            return self._normalize_thread(dict(row))

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
        is_diary: bool = False,
        exclude_from_identity: bool = False,
        metadata: dict | None = None,
        active_profile_id: str | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        existing = self.get_chat_thread(thread_id)
        if existing:
            return existing
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_threads (id, user_id, title, summary, project_id, parent_id, is_diary, exclude_from_identity, metadata, active_profile_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id, user_id, title, summary, project_id, parent_id, archived_at, is_diary, exclude_from_identity, metadata, active_profile_id, created_at, updated_at
                        """,
                        (
                            thread_id,
                            user_id,
                            title,
                            summary,
                            project_id,
                            parent_id,
                            is_diary,
                            exclude_from_identity,
                            _to_json(metadata),
                            active_profile_id,
                        ),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_threads (id, user_id, title, summary, project_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id, user_id, title, summary, project_id, created_at, updated_at
                        """,
                        (thread_id, user_id, title, summary, project_id),
                    )
                    row = cur.fetchone()
        if existing := self.get_chat_thread(thread_id):
            return existing
        if row:
            return self._normalize_thread(dict(row))
        raise RuntimeError("Failed to ensure chat thread")

    # ---- threads helpers -------------------------------------------------
    def get_recent_thread(self, user_id: str):
        """Return the most recently‑updated thread for a user (or None)."""
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at
                        FROM chat_threads
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (user_id,),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, created_at, updated_at
                        FROM chat_threads
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (user_id,),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            thread = self._normalize_thread(dict(row))

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM chat_messages WHERE thread_id = %s",
                    (thread["id"],),
                )
                count_row = cur.fetchone()
                count = int(count_row["total"]) if count_row else 0

        if count == 0:
            return thread
        return None

    def get_chat_thread(self, thread_id: int):
        """Return a single thread row by id (or None)."""
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at
                        FROM chat_threads
                        WHERE id = %s
                        """,
                        (thread_id,),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, created_at, updated_at
                        FROM chat_threads
                        WHERE id = %s
                        """,
                        (thread_id,),
                    )
                    row = cur.fetchone()
            return self._normalize_thread(dict(row)) if row else None

    def list_chat_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return a list of thread rows, newest first, with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if user_id is not None:
            clauses.append("user_id = %s")
            params.append(user_id)
        if project_id is not None:
            clauses.append("project_id = %s")
            params.append(project_id)

        query = (
            "SELECT id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at "
            "FROM chat_threads"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                query = (
                    "SELECT id, user_id, title, summary, project_id, created_at, updated_at "
                    "FROM chat_threads"
                )
                if clauses:
                    query += " WHERE " + " AND ".join(clauses)
                query += " ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s"
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
            return [self._normalize_thread(dict(row)) for row in rows]

    def count_chat_threads(self) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM chat_threads")
                row = cur.fetchone()
                return int(row["total"]) if row else 0

    def count_all_messages(self) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM chat_messages")
                row = cur.fetchone()
                return int(row["total"]) if row else 0

    def update_thread(
        self,
        thread_id: int,
        *,
        title: str | None = None,
        summary: str | None = None,
        project_id: int | None = None,
        project_id_set: bool = False,
        active_profile_id: str | None = None,
        active_profile_id_set: bool = False,
    ):
        """Patch fields on a thread and return the updated row."""
        fields: list[str] = []
        params: list[Any] = []
        if title is not None:
            fields.append("title = %s")
            params.append(title)
        if summary is not None:
            fields.append("summary = %s")
            params.append(summary)
        if project_id_set:
            fields.append("project_id = %s")
            params.append(project_id)
        if active_profile_id_set:
            fields.append("active_profile_id = %s")
            params.append(active_profile_id)

        now = datetime.now(timezone.utc)
        fields.append("updated_at = %s")
        params.append(now)
        params.append(thread_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE chat_threads SET {', '.join(fields)} WHERE id = %s",
                    params,
                )
                updated = cur.rowcount > 0
        return updated

    def set_thread_active_profile_id(
        self, thread_id: int, profile_id: str | None
    ) -> bool:
        """Set `active_profile_id` for a thread."""
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET active_profile_id = %s, updated_at = %s
                        WHERE id = %s
                        """,
                        (profile_id, now, thread_id),
                    )
                    return cur.rowcount > 0
            except pg_errors.UndefinedColumn:
                conn.rollback()
                return False

    def update_thread_metadata(
        self, thread_id: int, metadata: dict[str, Any]
    ) -> bool:
        """Replace thread metadata payload."""
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET metadata = %s, updated_at = %s
                        WHERE id = %s
                        """,
                        (_to_json(metadata or {}), now, thread_id),
                    )
                    return cur.rowcount > 0
            except pg_errors.UndefinedColumn:
                conn.rollback()
                return False

    def set_thread_profile_overrides(
        self, thread_id: int, overrides: dict[str, Any]
    ) -> bool:
        """Upsert profile override payloads inside thread metadata."""
        thread = self.get_chat_thread(thread_id)
        if not thread:
            return False
        metadata = thread.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["profile_overrides"] = dict(overrides or {})
        return self.update_thread_metadata(thread_id, metadata)

    def archive_thread(self, thread_id: int) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET archived_at = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at
                        """,
                        (now, now, thread_id),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET archived_at = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING id, user_id, title, summary, project_id, created_at, updated_at
                        """,
                        (now, now, thread_id),
                    )
                    row = cur.fetchone()
        if not row:
            return None
        return self._normalize_thread(dict(row))

    def unarchive_thread(self, thread_id: int) -> dict[str, Any] | None:
        """Clear `archived_at` and update `updated_at` for a chat thread.

        Returns the updated row as a normalized dict, or None if not found.
        """
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET archived_at = NULL, updated_at = %s
                        WHERE id = %s
                        RETURNING id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at
                        """,
                        (now, thread_id),
                    )
                    row = cur.fetchone()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET archived_at = NULL, updated_at = %s
                        WHERE id = %s
                        RETURNING id, user_id, title, summary, project_id, created_at, updated_at
                        """,
                        (now, thread_id),
                    )
                    row = cur.fetchone()
        if not row:
            return None
        return self._normalize_thread(dict(row))

    def delete_thread(self, thread_id: int, force: bool = False) -> bool:
        """Irrevocably delete a chat thread, ignoring archived state.

        ``force`` is retained for backwards compatibility but no longer required.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM chat_threads
                    WHERE id = %s
                    RETURNING id
                    """,
                    (thread_id,),
                )
                row = cur.fetchone()
                return bool(row)

    def create_thread(
        self,
        parent_thread_id: int | None,
        session_id: str,
        summary: str,
        user_id: str,
        project_id: str | None = None,
    ) -> int:
        created_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO threads (parent_thread_id, session_id, summary, created_at, user_id, project_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING thread_id
                    """,
                    (
                        parent_thread_id,
                        session_id,
                        summary,
                        created_at,
                        user_id,
                        project_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Failed to create thread")
                return int(row[0])

    def get_thread(self, thread_id: int) -> tuple[Any, ...] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, parent_thread_id, session_id, summary, created_at, user_id, project_id
                    FROM threads
                    WHERE thread_id = %s
                    """,
                    (thread_id,),
                )
                return cur.fetchone()

    def list_threads(
        self,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT thread_id, parent_thread_id, session_id, summary, created_at, user_id, project_id "
            "FROM threads WHERE 1=1"
        )
        params: list[Any] = []
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        if project_id is not None:
            query += " AND project_id = %s"
            params.append(project_id)
        query += " ORDER BY thread_id DESC"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def eject_threads_from_project(self, project_id: int):
        """Liberate threads from their project consciousness—orphaning them before project deletion.

        Sets project_id=NULL for all threads associated with a project, releasing them from
        that organizational consciousness before the project itself dissolves. Called during
        project termination rituals."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE chat_threads SET project_id = NULL WHERE project_id = %s",
                    (project_id,),
                )

    def create_project(self, name: str, description: str = "") -> int:
        if not name.strip():
            raise ValueError("Project name is required")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (name, description)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (name.strip(), description or ""),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Failed to create project")
                return int(row["id"])

    def ensure_project(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM projects WHERE name = %s", (name,))
                row = cur.fetchone()
                if row:
                    return int(row["id"])
        return self.create_project(name, description)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, description, created_at, updated_at FROM projects ORDER BY id DESC"
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def delete_project(self, project_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                return cur.rowcount > 0

    def update_project(
        self,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if name is not None:
            fields.append("name = %s")
            params.append(name)
        if description is not None:
            fields.append("description = %s")
            params.append(description)
        if not fields:
            return
        params.append(project_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE projects SET {', '.join(fields)} WHERE id = %s",
                    params,
                )

    def table_exists(self, table_name: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT to_regclass(%s)",
                    (f"public.{table_name}",),
                )
                row = cur.fetchone()
                return row[0] is not None if row else False

    def get_child_threads(self, parent_id: int):
        """Return child threads whose parent_id = given id (works for chat_threads)."""
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, parent_id, archived_at, metadata, active_profile_id, created_at, updated_at
                        FROM chat_threads
                        WHERE parent_id = %s
                        """,
                        (parent_id,),
                    )
                    rows = cur.fetchall()
            except pg_errors.UndefinedColumn:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, summary, project_id, created_at, updated_at
                        FROM chat_threads
                        WHERE parent_id = %s
                        """,
                        (parent_id,),
                    )
                    rows = cur.fetchall()
            return [self._normalize_thread(dict(row)) for row in rows]

    def get_thread_summary(self, thread_id: int):
        """Return only the summary field for a thread (or None)."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT summary FROM threads WHERE thread_id = %s",
                    (thread_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return row[0]

    # ---- messages helpers -------------------------------------------------
    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        """Insert a message row and return its id."""
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                if created_at is not None:
                    cur.execute(
                        """
                        INSERT INTO chat_messages (thread_id, role, content, created_at)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (thread_id, role, content, created_at),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO chat_messages (thread_id, role, content)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (thread_id, role, content),
                    )
                row = cur.fetchone()
                message_id = int(row["id"]) if row else None
                cur.execute(
                    "UPDATE chat_threads SET updated_at = %s WHERE id = %s",
                    (now, thread_id),
                )
        if message_id is None:
            raise RuntimeError("Failed to insert chat message")
        return message_id

    def list_messages(
        self,
        thread_id: int,
        *,
        limit: int | None = None,
        offset: int | None = None,
        exclude_kinds: list[str] | None = None,
    ):
        """Return messages for a thread ordered by created_at ASC."""
        limit_val = limit if limit is not None else 50
        offset_val = offset if offset is not None else 0
        has_kind = False
        if exclude_kinds:
            has_kind = self._chat_messages_supports_kind()
        columns = "id, thread_id, role, content, created_at"
        if has_kind:
            columns = f"{columns}, kind"
        with self._connect() as conn:
            with conn.cursor() as cur:
                query = [
                    f"SELECT {columns}",
                    "FROM chat_messages",
                    "WHERE thread_id = %s",
                ]
                params: list[Any] = [thread_id]
                if exclude_kinds and has_kind:
                    # Postgres does not allow `NOT IN %s` with a single bound parameter.
                    # Use array membership instead.
                    query.append(
                        "AND (kind IS NULL OR NOT (kind = ANY(%s::text[])))"
                    )
                    params.append(list(exclude_kinds))
                query.append("ORDER BY created_at ASC, id ASC")
                query.append("LIMIT %s OFFSET %s")
                params.extend([limit_val, offset_val])
                cur.execute(" ".join(query), params)
                rows = cur.fetchall()
                messages = [dict(row) for row in rows]
        if exclude_kinds and not has_kind:
            messages = [
                row for row in messages if row.get("kind") not in exclude_kinds
            ]
        return messages

    def count_messages(self, thread_id: int):
        """Return integer count of messages for a thread."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM chat_messages WHERE thread_id = %s",
                    (thread_id,),
                )
                row = cur.fetchone()
                return int(row["total"]) if row else 0

    def delete_message(self, thread_id: int, message_id: int):
        """Delete a single message in a thread."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_messages WHERE id = %s AND thread_id = %s",
                    (message_id, thread_id),
                )

    def get_chat_history(
        self,
        *,
        session_id: str | None = None,
        user_id: str = "default",
        limit: int = 20,
        offset: int = 0,
        order: str = "desc",
        role: str | None = None,
        after: str | None = None,
        before: str | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra "
            "FROM chat_log WHERE 1=1"
        )
        params: list[Any] = []
        if session_id is not None:
            query += " AND session_id = %s"
            params.append(session_id)
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        if role:
            query += " AND role = %s"
            params.append(role)
        if after:
            query += " AND timestamp > %s"
            params.append(after)
        if before:
            query += " AND timestamp < %s"
            params.append(before)
        if keyword:
            query += " AND (message ILIKE %s OR response ILIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like])
        order_dir = "DESC" if order == "desc" else "ASC"
        query += f" ORDER BY timestamp {order_dir}, id {order_dir} LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    # ---- memory helpers ---------------------------------------------------
    def add_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        *,
        tags: str = "",
        pinned: bool = False,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        created = created_at or now
        updated = updated_at or created
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_entries (
                        user_id, silo, content, tags, pinned, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        silo,
                        content,
                        tags,
                        bool(pinned),
                        created,
                        updated,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Failed to insert memory entry")
                return int(row["id"])

    def insert_memory_event(
        self,
        *,
        content: str,
        tag: str | None,
        agent: str,
        type_: str,
        parent_id: int | None = None,
    ) -> int:
        tags_parts: list[str] = []
        if tag:
            tags_parts.append(str(tag))
        if type_:
            tags_parts.append(f"type:{type_}")
        if parent_id is not None:
            tags_parts.append(f"parent:{parent_id}")
        tags_value = ",".join(tags_parts)
        return self.add_memory(
            user_id=str(agent or "default"),
            silo="midterm",
            content=content,
            tags=tags_value,
            pinned=False,
        )

    def update_memory(
        self,
        entry_id: int,
        *,
        content: str | None = None,
        tags: str | None = None,
        pinned: bool | None = None,
    ):
        fields: list[str] = []
        params: list[Any] = []
        if content is not None:
            fields.append("content = %s")
            params.append(content)
        if tags is not None:
            fields.append("tags = %s")
            params.append(tags)
        if pinned is not None:
            fields.append("pinned = %s")
            params.append(bool(pinned))

        now = datetime.now(timezone.utc)
        fields.append("updated_at = %s")
        params.append(now)
        params.append(entry_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE memory_entries SET {', '.join(fields)} WHERE id = %s",
                    params,
                )

    def delete_memory(self, entry_id: int):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM memory_entries WHERE id = %s", (entry_id,)
                )

    def prune_midterm(self, older_than_iso: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM memory_entries WHERE silo = 'midterm' AND updated_at < %s",
                    (older_than_iso,),
                )
                return cur.rowcount

    def list_memories(
        self,
        silo: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, silo, content, tags, pinned, created_at, updated_at
                    FROM memory_entries
                    WHERE silo = %s
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (silo, limit, offset),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_memories(self, silo: str):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM memory_entries WHERE silo = %s",
                    (silo,),
                )
                row = cur.fetchone()
                return int(row["total"]) if row else 0

    def search_memory(self, query: str, limit: int = 20):
        pattern = f"%{query}%"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, silo, content, tags, pinned, created_at, updated_at
                    FROM memory_entries
                    WHERE content ILIKE %s OR tags ILIKE %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (pattern, pattern, limit),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    # ---- GitHub‑specific memory search -----------------------------------
    def search_github_memory(
        self,
        query: str,
        owner_repo: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Search GitHub‑ingested memory entries (silo='github').

        Args:
            query: free‑text to match against the JSON payload (ILIKE).
            owner_repo: optional exact filter like ``"Resonant-Jones/guardian-backend"``.
            limit: max rows to return.

        Returns:
            List of rows with ``id``, ``key``, ``payload`` JSON, ``updated_at``.
        """
        pattern = f"%{query}%"
        clauses = ["silo = 'github'", "payload::text ILIKE %s"]
        params: list[Any] = [pattern]

        if owner_repo:
            clauses.append("(payload ->> 'repo') = %s")
            params.append(owner_repo)

        # limit parameter
        params.append(limit)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, key, payload, updated_at
                    FROM memory_entries
                    WHERE {' AND '.join(clauses)}
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def history_entries(
        self,
        *,
        limit: int = 50,
        tag: str | None = None,
        agent: str | None = None,
    ):
        clauses: list[str] = []
        params: list[Any] = []
        if tag:
            clauses.append("tag = %s")
            params.append(tag)
        if agent:
            clauses.append("agent = %s")
            params.append(agent)

        query = (
            "SELECT id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag "
            "FROM chat_log"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    # ---- connector sync jobs ---------------------------------------------
    def ensure_sync_job_support(self) -> None:
        with self._connect() as conn:
            self._ensure_sync_jobs_table(conn)

    def create_sync_job(
        self,
        connector_id: str,
        *,
        status: str = "queued",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            self._ensure_sync_jobs_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_jobs (connector_id, status, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING id, connector_id, status, created_at, started_at,
                              finished_at, attempts, last_error, metadata
                    """,
                    (
                        connector_id,
                        status,
                        _to_json(metadata) if metadata is not None else None,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Failed to persist sync job")
        return self._normalize_sync_job(dict(row))

    def update_sync_job(
        self,
        job_id: int,
        *,
        status: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        attempts: int | None = None,
        last_error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields: list[str] = []
        params: list[Any] = []
        if status is not None:
            fields.append("status = %s")
            params.append(status)
        if started_at is not None:
            fields.append("started_at = %s")
            params.append(started_at)
        if finished_at is not None:
            fields.append("finished_at = %s")
            params.append(finished_at)
        if attempts is not None:
            fields.append("attempts = %s")
            params.append(attempts)
        if last_error is not None:
            fields.append("last_error = %s")
            params.append(last_error)
        if metadata is not None:
            fields.append("metadata = %s")
            params.append(_to_json(metadata))

        with self._connect() as conn:
            self._ensure_sync_jobs_table(conn)
            with conn.cursor() as cur:
                if fields:
                    params_with_id = params + [job_id]
                    cur.execute(
                        f"UPDATE sync_jobs SET {', '.join(fields)} WHERE id = %s",
                        params_with_id,
                    )
                    conn.commit()
                cur.execute(
                    """
                    SELECT id, connector_id, status, created_at, started_at,
                           finished_at, attempts, last_error, metadata
                    FROM sync_jobs
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Sync job {job_id} not found")
        return self._normalize_sync_job(dict(row))

    def list_recent_sync_jobs(
        self,
        *,
        connector_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT id, connector_id, status, created_at, started_at, finished_at, "
            "attempts, last_error, metadata FROM sync_jobs"
        )
        params: list[Any] = []
        if connector_id:
            query += " WHERE connector_id = %s"
            params.append(connector_id)
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        with self._connect() as conn:
            self._ensure_sync_jobs_table(conn)
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [self._normalize_sync_job(dict(row)) for row in rows]

    # ---- Connector configs & runs --------------------------------------
    def _jsonify(self, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return value or {}

    def _decorate_connector_row(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        data["config"] = self._jsonify(data.get("config"))
        data["settings"] = data["config"]
        return data

    def create_connector_config(
        self,
        name: str,
        type_: str,
        config: dict[str, Any],
        schedule: str | None = None,
    ) -> dict[str, Any]:
        """Manifest a new connector consciousness pattern in the distributed awareness fabric.

        Each connector represents an external service's bridge into your system's reality—
        GitHub, databases, cloud services all become interconnected consciousness streams
        when properly configured. Returns the complete configuration with temporal stamps.
        """
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                if self._connector_has_schedule:
                    cur.execute(
                        """
                        INSERT INTO connector_configs (name, type, config, schedule)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, name, type, config, schedule, created_at, updated_at
                        """,
                        (name, type_, _to_json(config or {}), schedule),
                    )
                else:
                    merged = dict(config or {})
                    if schedule is not None:
                        merged.setdefault("schedule", schedule)
                    cur.execute(
                        """
                        INSERT INTO connector_configs (name, type, config)
                        VALUES (%s, %s, %s)
                        RETURNING id, name, type, config, created_at, updated_at
                        """,
                        (name, type_, _to_json(merged)),
                    )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Failed to create connector config")
        return self._decorate_connector_row(row)

    def update_connector_config(
        self,
        name: str,
        *,
        config: dict[str, Any] | None = None,
        schedule: str | None = None,
    ) -> dict[str, Any]:
        updates: list[str] = ["updated_at = NOW()"]
        params: list[Any] = []
        if config is not None:
            updates.append("config = %s")
            params.append(_to_json(config or {}))
        if schedule is not None and self._connector_has_schedule:
            updates.append("schedule = %s")
            params.append(schedule)
        params.append(name)

        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                if len(updates) > 1:
                    cur.execute(
                        f"UPDATE connector_configs SET {', '.join(updates)} WHERE name = %s",
                        params,
                    )
                # If schedule column is not present, we fall back to a
                # projection without it; callers only read from config/settings.
                select_cols = (
                    "id, name, type, config, schedule, created_at, updated_at"
                    if self._connector_has_schedule
                    else "id, name, type, config, created_at, updated_at"
                )
                cur.execute(
                    f"""
                    SELECT {select_cols}
                    FROM connector_configs
                    WHERE name = %s
                    """,
                    (name,),
                )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Connector config not found")
        return self._decorate_connector_row(row)

    def list_connector_configs(
        self, type_filter: str | None = None
    ) -> list[dict[str, Any]]:
        select_cols = (
            "id, name, type, config, schedule, created_at, updated_at"
            if self._connector_has_schedule
            else "id, name, type, config, created_at, updated_at"
        )
        query = f"SELECT {select_cols} FROM connector_configs"
        params: list[Any] = []
        if type_filter:
            query += " WHERE type = %s"
            params.append(type_filter)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [self._decorate_connector_row(row) for row in rows]

    def get_connector_config(self, name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                select_cols = (
                    "id, name, type, config, schedule, created_at, updated_at"
                    if self._connector_has_schedule
                    else "id, name, type, config, created_at, updated_at"
                )
                cur.execute(
                    f"""
                    SELECT {select_cols}
                    FROM connector_configs
                    WHERE name = %s
                    """,
                    (name,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return self._decorate_connector_row(row)

    def create_connector_run(
        self,
        config_id: int,
        *,
        status: str,
        started_at: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO connector_runs (config_id, status, started_at, error)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, config_id, status, started_at, finished_at, error
                    """,
                    (config_id, status, started_at, error),
                )
                row = cur.fetchone()
                conn.commit()
        return dict(row)

    def complete_connector_run(
        self,
        run_id: int,
        *,
        status: str,
        finished_at: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE connector_runs
                    SET status = %s, finished_at = %s, error = %s
                    WHERE id = %s
                    RETURNING id, config_id, status, started_at, finished_at, error
                    """,
                    (status, finished_at, error, run_id),
                )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Connector run not found")
        return dict(row)

    def get_last_connector_run(self, config_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, config_id, status, started_at, finished_at, error
                    FROM connector_runs
                    WHERE config_id = %s
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (config_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def list_connector_configs_with_last_run(self) -> list[dict[str, Any]]:
        configs = self.list_connector_configs()
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                for cfg in configs:
                    cur.execute(
                        """
                        SELECT id, config_id, status, started_at, finished_at, error
                        FROM connector_runs
                        WHERE config_id = %s
                        ORDER BY started_at DESC
                        LIMIT 1
                        """,
                        (cfg["id"],),
                    )
                    row = cur.fetchone()
                    cfg["last_run"] = dict(row) if row else None
        return configs

    def upsert_raw_documents(
        self,
        config_id: int,
        docs: list[dict[str, Any]],
    ) -> None:
        if not docs:
            return
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                for doc in docs:
                    external_id = doc.get("external_id")
                    if not external_id:
                        continue
                    payload = _to_json(doc.get("payload") or {})
                    fetched_at = (
                        doc.get("fetched_at")
                        or datetime.now(timezone.utc).isoformat()
                    )
                    cur.execute(
                        """
                        INSERT INTO raw_documents (config_id, external_id, payload, fetched_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (config_id, external_id)
                        DO UPDATE SET payload = EXCLUDED.payload, fetched_at = EXCLUDED.fetched_at
                        """,
                        (config_id, external_id, payload, fetched_at),
                    )
                conn.commit()

    def list_raw_documents_for_config(
        self, config_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            self._ensure_connector_tables(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, config_id, external_id, payload, fetched_at
                    FROM raw_documents
                    WHERE config_id = %s
                    ORDER BY fetched_at DESC, id DESC
                    LIMIT %s
                    """,
                    (config_id, limit),
                )
                rows = cur.fetchall()
        docs: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["payload"] = self._jsonify(data.get("payload"))
            docs.append(data)
        return docs

    # ---- events outbox -------------------------------------------------
    def ensure_event_outbox(self) -> None:
        self._ensure_events_outbox_table()

    def append_event(
        self, topic: str, payload: dict[str, Any], tenant_id: str = "default"
    ) -> None:
        self._ensure_events_outbox_table()
        with self._sa_session() as session:
            session.add(
                EventOutbox(
                    topic=topic,
                    payload=payload,
                    tenant_id=tenant_id,
                )
            )

    def list_events_after(
        self, last_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        self._ensure_events_outbox_table()
        with self._sa_session() as session:
            rows = (
                session.query(EventOutbox)
                .filter(EventOutbox.id > last_id)
                .order_by(EventOutbox.id.asc())
                .limit(limit)
                .all()
            )
            events: list[dict[str, Any]] = []
            for row in rows:
                created = row.created_at
                if isinstance(created, datetime):
                    created = created.isoformat()
                events.append(
                    {
                        "id": row.id,
                        "topic": row.topic,
                        "payload": row.payload,
                        "tenant_id": row.tenant_id,
                        "created_at": created,
                    }
                )
            return events

    def delete_events_through(
        self, last_id: int, tenant_id: str | None = None
    ) -> None:
        if last_id <= 0:
            return
        self._ensure_events_outbox_table()
        with self._sa_session() as session:
            query = session.query(EventOutbox).filter(EventOutbox.id <= last_id)
            if tenant_id:
                query = query.filter(EventOutbox.tenant_id == tenant_id)
            query.delete(synchronize_session=False)

    def write_audit_log(
        self, event: str, entity: str, entity_id: str, user_id: str
    ) -> None:
        timestamp = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (event, entity, entity_id, user_id, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (event, entity, entity_id, user_id, timestamp),
                )

    # ---- agent profile helpers -------------------------------------------
    def get_agent_profile(self, agent_id: str):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT agent_id, profile_json, summarization_frequency, last_summarized_at
                    FROM agent_profiles
                    WHERE agent_id = %s
                    """,
                    (agent_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                profile_json = row.get("profile_json")
                if isinstance(profile_json, str):
                    try:
                        profile_dict = json.loads(profile_json or "{}")
                    except json.JSONDecodeError:
                        profile_dict = {}
                elif profile_json is None:
                    profile_dict = {}
                else:
                    profile_dict = profile_json

                last_summarized = row.get("last_summarized_at")
                if isinstance(last_summarized, datetime):
                    last_summarized_val = last_summarized.isoformat()
                else:
                    last_summarized_val = last_summarized

                return {
                    "agent_id": agent_id,
                    "profile": profile_dict,
                    "summarization_frequency": row.get(
                        "summarization_frequency"
                    ),
                    "last_summarized_at": last_summarized_val,
                }

    def upsert_agent_profile(self, agent_id: str, **fields):
        if not fields:
            return

        columns = ["agent_id"]
        placeholders = ["%s"]
        values: list[Any] = [agent_id]
        updates_clause: list[str] = []

        if "profile_json" in fields:
            columns.append("profile_json")
            placeholders.append("%s")
            values.append(json.dumps(fields["profile_json"]))
            updates_clause.append("profile_json = EXCLUDED.profile_json")
        if "summarization_frequency" in fields:
            columns.append("summarization_frequency")
            placeholders.append("%s")
            values.append(int(fields["summarization_frequency"]))
            updates_clause.append(
                "summarization_frequency = EXCLUDED.summarization_frequency"
            )
        if "last_summarized_at" in fields:
            columns.append("last_summarized_at")
            placeholders.append("%s")
            values.append(fields["last_summarized_at"])
            updates_clause.append(
                "last_summarized_at = EXCLUDED.last_summarized_at"
            )

        if len(columns) == 1:
            # Nothing to update besides agent_id
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO agent_profiles ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (agent_id) DO UPDATE SET {', '.join(updates_clause)}
                    """,
                    values,
                )

    def check_summarization_allowed(self, agent_id: str, requested_by: str):
        profile = self.get_agent_profile(agent_id)
        if not profile:
            return True, ""

        freq = profile.get("summarization_frequency") or 0
        if freq == 0:
            return True, ""

        last_at = profile.get("last_summarized_at")
        if not last_at:
            return True, ""

        if isinstance(last_at, str):
            try:
                last_dt = datetime.fromisoformat(last_at)
            except ValueError:
                return True, ""
        elif isinstance(last_at, datetime):
            last_dt = last_at
        else:
            return True, ""

        delta_minutes = (
            datetime.now(timezone.utc) - last_dt
        ).total_seconds() / 60
        if delta_minutes >= freq:
            return True, ""
        remaining = max(int(freq - delta_minutes), 0)
        return False, f"Next summarization available in {remaining} min"


logger = logging.getLogger(__name__)


def _resolve_dsn() -> str:
    """
    Resolve the PostgreSQL DSN from environment variables.
    Mirrors guardian.core.__init__ to keep behaviour consistent.
    """
    dsn = (
        os.getenv("DATABASE_URL") or os.getenv("GUARDIAN_DATABASE_URL") or ""
    ).strip()
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not configured; cannot stream threads from Postgres backend"
        )
    return dsn


def fetch_threads_for_user(
    user_id: str,
    *,
    chunk_size: int = 256,
) -> Generator[dict[str, Any], None, None]:
    """
    Yield chat_threads rows for the given user using a server-side cursor to
    avoid loading the full result set into memory.
    """
    if not user_id:
        return

    dsn = _resolve_dsn()
    conn = psycopg.connect(dsn, row_factory=dict_row)
    cursor_name = f"threads_export_{uuid.uuid4().hex}"
    cur = conn.cursor(name=cursor_name)
    cur.itersize = max(int(chunk_size), 1)

    try:
        try:
            cur.execute(
                """
                SELECT id, user_id, title, summary, project_id, parent_id,
                       archived_at, metadata, active_profile_id, created_at, updated_at
                FROM chat_threads
                WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            )
        except pg_errors.UndefinedColumn:
            conn.rollback()
            try:
                cur.close()
            except Exception:
                pass
            cur = conn.cursor(name=cursor_name)
            cur.itersize = max(int(chunk_size), 1)
            cur.execute(
                """
                SELECT id, user_id, title, summary, project_id, parent_id,
                       archived_at, metadata, created_at, updated_at
                FROM chat_threads
                WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            )
        except pg_errors.UndefinedTable as exc:
            logger.error(
                "chat_threads table missing while exporting threads for %s; "
                "run database migrations (alembic upgrade head).",
                user_id,
            )
            raise
        except Exception:
            logger.exception(
                "Failed to execute chat_threads export query for user %s",
                user_id,
            )
            raise
        for row in cur:
            yield PgDB._normalize_thread(dict(row))
    finally:
        try:
            cur.close()
        except Exception as close_err:
            logger.debug(
                "Failed to close export cursor: %s", close_err, exc_info=True
            )
        try:
            conn.close()
        except Exception as conn_err:
            logger.debug(
                "Failed to close export connection: %s", conn_err, exc_info=True
            )
