"""
SQLite-backed ChatLog database adapter.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lightweight SQLite implementation providing the subset of chat/memory
operations needed by the Guardian/Codexify API and tests.

This adapter is intentionally minimal and focused on:
- chat_threads / chat_messages for chat APIs
- memory_entries for memory APIs and pruning tests
- a simple events_outbox table for the durable event bus
- basic projects and legacy threads tables used by tests
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SqliteChatLogDB:
    """
    Minimal SQLite-backed chat log store.

    This class does not aim to be a full ORM; it just provides the small
    surface area used by the FastAPI routes and tests.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create core tables if they do not already exist."""
        with self._connect() as conn:
            cur = conn.cursor()
            # Chat threads
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    summary TEXT DEFAULT '',
                    project_id INTEGER,
                    parent_id INTEGER,
                    archived_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Chat messages
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                )
                """
            )
            # Memory entries
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    silo TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Events outbox
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL
                )
                """
            )
            # Projects
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    created_at TEXT
                )
                """
            )
            # Legacy threads table (for thread lineage helpers)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_thread_id INTEGER,
                    session_id TEXT,
                    summary TEXT,
                    created_at TEXT,
                    user_id TEXT,
                    project_id TEXT
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Events outbox (used by event_bus)
    # ------------------------------------------------------------------

    def ensure_event_outbox(self) -> None:
        """Ensure events_outbox table exists (created in ensure_schema)."""
        self.ensure_schema()

    def append_event(self, topic: str, payload: Dict[str, Any], *, tenant_id: str = "default") -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events_outbox (topic, payload, tenant_id, created_at) VALUES (?, ?, ?, ?)",
                (topic, json.dumps(payload), tenant_id, now),
            )
            conn.commit()

    def list_events_after(self, last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, topic, payload, tenant_id, created_at "
                "FROM events_outbox WHERE id > ? ORDER BY id ASC LIMIT ?",
                (last_id, limit),
            )
            rows = cur.fetchall()
        events: List[Dict[str, Any]] = []
        for r in rows:
            try:
                payload = json.loads(r["payload"])
            except Exception:
                payload = {}
            events.append(
                {
                    "id": r["id"],
                    "topic": r["topic"],
                    "payload": payload,
                    "tenant_id": r["tenant_id"],
                    "created_at": r["created_at"],
                }
            )
        return events

    def delete_events_through(self, last_id: int, tenant_id: Optional[str] = None) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            if tenant_id:
                cur.execute(
                    "DELETE FROM events_outbox WHERE id <= ? AND tenant_id = ?",
                    (last_id, tenant_id),
                )
            else:
                cur.execute("DELETE FROM events_outbox WHERE id <= ?", (last_id,))
            conn.commit()

    # ------------------------------------------------------------------
    # Chat threads (chat_threads)
    # ------------------------------------------------------------------

    def create_chat_thread(
        self,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO chat_threads (user_id, title, summary, project_id, parent_id, archived_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (user_id, title, summary, project_id, parent_id, now, now),
            )
            tid = cur.lastrowid
            conn.commit()
        return self.get_chat_thread(tid)  # type: ignore[arg-type]

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM chat_threads WHERE id = ?", (thread_id,))
            row = cur.fetchone()
            if row:
                return
            now = datetime.utcnow().isoformat()
            cur.execute(
                """
                INSERT INTO chat_threads (id, user_id, title, summary, project_id, parent_id, archived_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (thread_id, user_id, title, summary, project_id, now, now),
            )
            conn.commit()

    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "summary": row["summary"],
            "project_id": row["project_id"],
            "parent_id": row["parent_id"],
            "archived_at": row["archived_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_recent_thread(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM chat_threads WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "summary": row["summary"],
            "project_id": row["project_id"],
            "parent_id": row["parent_id"],
            "archived_at": row["archived_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_chat_threads(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM chat_threads WHERE archived_at IS NULL ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "title": r["title"],
                "summary": r["summary"],
                "project_id": r["project_id"],
                "parent_id": r["parent_id"],
                "archived_at": r["archived_at"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def count_chat_threads(self) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM chat_threads")
            (count,) = cur.fetchone()
        return int(count or 0)

    # ------------------------------------------------------------------
    # Chat messages (chat_messages)
    # ------------------------------------------------------------------

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: Optional[str] = None,
    ) -> int:
        ts = created_at or datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO chat_messages (thread_id, user_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (thread_id, "default", role, content, ts),
            )
            mid = cur.lastrowid
            conn.commit()
        return int(mid)

    def list_messages(
        self,
        thread_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, thread_id, user_id, role, content, created_at
                FROM chat_messages
                WHERE thread_id = ?
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                (thread_id, limit, offset),
            )
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "thread_id": r["thread_id"],
                "user_id": r["user_id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def count_messages(self, thread_id: int) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE thread_id = ?", (thread_id,))
            (count,) = cur.fetchone()
        return int(count or 0)

    def delete_message(self, thread_id: int, message_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM chat_messages WHERE id = ? AND thread_id = ?",
                (message_id, thread_id),
            )
            conn.commit()

    def count_all_messages(self) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM chat_messages")
            (count,) = cur.fetchone()
        return int(count or 0)

    # ------------------------------------------------------------------
    # Memory entries (memory_entries)
    # ------------------------------------------------------------------

    def add_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        *,
        tags: str = "",
        pinned: bool = False,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        created = created_at or now
        updated = updated_at or now
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, silo, content, tags, int(pinned), created, updated),
            )
            mid = cur.lastrowid
            conn.commit()
        return int(mid)

    def list_memories(
        self,
        silo: str,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id:
                cur.execute(
                    """
                    SELECT * FROM memory_entries
                    WHERE silo = ? AND user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (silo, user_id, limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM memory_entries
                    WHERE silo = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (silo, limit, offset),
                )
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "silo": r["silo"],
                "content": r["content"],
                "tags": r["tags"],
                "pinned": bool(r["pinned"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def count_memories(self, silo: str, user_id: Optional[str] = None) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id:
                cur.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE silo = ? AND user_id = ?",
                    (silo, user_id),
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE silo = ?",
                    (silo,),
                )
            (count,) = cur.fetchone()
        return int(count or 0)

    def get_memory(self, entry_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM memory_entries WHERE id = ?", (entry_id,))
            r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "user_id": r["user_id"],
            "silo": r["silo"],
            "content": r["content"],
            "tags": r["tags"],
            "pinned": bool(r["pinned"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    def update_memory(
        self,
        entry_id: int,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        pinned: Optional[bool] = None,
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            fields = []
            params: List[Any] = []
            if content is not None:
                fields.append("content = ?")
                params.append(content)
            if tags is not None:
                fields.append("tags = ?")
                params.append(tags)
            if pinned is not None:
                fields.append("pinned = ?")
                params.append(int(pinned))
            if not fields:
                return
            fields.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(entry_id)
            cur.execute(
                f"UPDATE memory_entries SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            conn.commit()

    def delete_memory(self, entry_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            conn.commit()

    def prune_midterm(self, cutoff: str) -> int:
        """Prune midterm memories older than cutoff (by updated_at)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM memory_entries WHERE silo = 'midterm' AND updated_at < ?",
                (cutoff,),
            )
            count = cur.rowcount
            conn.commit()
        return int(count or 0)

    # ------------------------------------------------------------------
    # Projects & legacy threads (minimal subset for tests)
    # ------------------------------------------------------------------

    def create_project(self, name: str, description: str = "") -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
                (name, description, now),
            )
            pid = cur.lastrowid
            conn.commit()
        return int(pid)

    def ensure_project(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return int(row["id"])
            now = datetime.utcnow().isoformat()
            cur.execute(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
                (name, description, now),
            )
            pid = cur.lastrowid
            conn.commit()
        return int(pid)

    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            fields = []
            params: List[Any] = []
            if name is not None:
                fields.append("name = ?")
                params.append(name)
            if description is not None:
                fields.append("description = ?")
                params.append(description)
            if not fields:
                return
            params.append(project_id)
            cur.execute(
                f"UPDATE projects SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            conn.commit()

    def delete_project(self, project_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def eject_threads_from_project(self, project_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE chat_threads SET project_id = NULL WHERE project_id = ?",
                (project_id,),
            )
            conn.commit()

    # Legacy threads helpers (used by thread lineage endpoints)

    def create_thread(
        self,
        parent_thread_id: Optional[int],
        session_id: str,
        summary: str,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO threads (parent_thread_id, session_id, summary, created_at, user_id, project_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (parent_thread_id, session_id, summary, now, user_id, project_id),
            )
            tid = cur.lastrowid
            conn.commit()
        return int(tid)

    def get_thread(self, thread_id: int) -> Optional[Tuple[Any, ...]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM threads WHERE id = ?", (thread_id,))
            row = cur.fetchone()
        return tuple(row) if row else None  # type: ignore[arg-type]

    def list_threads(
        self,
        *,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM threads"
            params: List[Any] = []
            clauses: List[str] = []
            if user_id:
                clauses.append("user_id = ?")
                params.append(user_id)
            if project_id:
                clauses.append("project_id = ?")
                params.append(project_id)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_child_threads(self, parent_thread_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM threads WHERE parent_thread_id = ?", (parent_thread_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT summary FROM threads WHERE id = ?", (thread_id,))
            row = cur.fetchone()
        return row["summary"] if row else None  # type: ignore[index]

    # ------------------------------------------------------------------
    # Audit log (no-op for tests)
    # ------------------------------------------------------------------

    def write_audit_log(
        self,
        event: str,
        entity: str,
        entity_id: str,
        user_id: str,
    ) -> None:
        """Tests do not currently assert on audit log contents; log only."""
        logger.debug(
            "[audit] event=%s entity=%s id=%s user=%s", event, entity, entity_id, user_id
        )

