"""
guardian.core.db
================

GuardianDB: Handles all low-level memory persistence in SQLite for Guardian.

Usage:
    db = GuardianDB("guardian.db")
    db.init_db()
    db.insert_log(...)
    history = db.get_history(...)
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class GuardianDB:
    """Handles all low-level memory persistence in SQLite for Guardian."""

    def __init__(self, db_path: str = "guardian.db") -> None:
        self.db_path = db_path
        self.upgrade_db_schema()  # <-- Add this line so table always exists

    def __enter__(self):
        # Allow: with GuardianDB(...) as db:
        return self

    def __exit__(self, exc_type, exc, tb):
        # Best-effort close; do not suppress exceptions
        try:
            self.close()
        except Exception:
            pass
        return False

    def close(self):
        """
        Safely close underlying connection if present.
        Note: This class uses per-operation sqlite3.connect(...) so there may be
        no persistent connection to close; this is a no-op in that case.
        """
        try:
            conn = getattr(self, "conn", None)
            if conn is not None:
                conn.close()
        except Exception:
            # Do not raise on close during context manager exit
            pass

    def init_db(self) -> None:
        """Initializes the database schema for memory storage (legacy) and calls upgrade_db_schema for chat_log."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    command TEXT,
                    tag TEXT,
                    agent TEXT,
                    user_id TEXT
                )
                """
            )
            conn.commit()
        self.upgrade_db_schema()

    def upgrade_db_schema(self) -> None:
        """
        Ensures the chat_log table exists and is up to date.
        Adds missing columns if needed. This is the new canonical chat history table.
        """
        schema_columns = [
            ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            ("timestamp", "TEXT"),
            ("session_id", "TEXT"),
            ("user_id", "TEXT"),
            ("role", "TEXT"),
            ("message", "TEXT"),
            ("response", "TEXT"),
            ("backend", "TEXT"),
            ("model", "TEXT"),
            ("agent", "TEXT"),
            ("tag", "TEXT"),
            ("extra", "TEXT"),
        ]
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Check if table exists
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_log'"
            )
            exists = c.fetchone()
            if not exists:
                # Create the full table if missing
                columns_def = ",\n    ".join(
                    [f"{col} {ctype}" for col, ctype in schema_columns]
                )
                c.execute(
                    f"CREATE TABLE IF NOT EXISTS chat_log (\n    {columns_def}\n)"
                )
                conn.commit()
                return
            # Table exists, check for missing columns
            c.execute("PRAGMA table_info(chat_log)")
            existing_cols = {row[1] for row in c.fetchall()}
            for col, ctype in schema_columns:
                if col not in existing_cols:
                    # Add missing column
                    c.execute(f"ALTER TABLE chat_log ADD COLUMN {col} {ctype}")
            conn.commit()

        # Add threads table for lineage and summary support
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # New tables for chat persistence, memory entries, and audit log
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # chat_threads: lightweight thread registry
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    title TEXT,
                    summary TEXT,
                    project_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            # Ensure project_id exists if table pre-dates this column
            try:
                c.execute("PRAGMA table_info(chat_threads)")
                cols = {row[1] for row in c.fetchall()}
                if "summary" not in cols:
                    c.execute("ALTER TABLE chat_threads ADD COLUMN summary TEXT")
                if "project_id" not in cols:
                    c.execute("ALTER TABLE chat_threads ADD COLUMN project_id INTEGER")
            except Exception:
                pass
            # chat_messages: per-thread chat messages
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT,
                    FOREIGN KEY(thread_id) REFERENCES chat_threads(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_id ON chat_messages(thread_id)")

            # memory_entries: unified memory table with silos
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    silo TEXT CHECK(silo IN ('ephemeral','midterm','longterm')),
                    content TEXT,
                    tags TEXT,
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_memory_entries_silo ON memory_entries(silo)")

            # audit_log: generic audit trail
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT,
                    entity TEXT,
                    entity_id TEXT,
                    user_id TEXT,
                    timestamp TEXT
                )
                """
            )
            conn.commit()

    def insert_log(
        self,
        command: str,
        tag: Optional[str] = None,
        agent: Optional[str] = None,
        timestamp: Optional[str] = None,
        user_id: str = "default",
    ) -> None:
        """
        Insert a log entry into the legacy memory table.
        NOTE: The new canonical table for chat history is 'chat_log'.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO memory (timestamp, command, tag, agent, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, command, tag, agent, user_id),
            )
            conn.commit()

    def get_history(
        self, limit: int = 10, user_id: Optional[str] = None
    ) -> List[Tuple[Any, ...]]:
        """
        Retrieve memory rows (most recent first) from the legacy memory table.
        NOTE: The new canonical table for chat history is 'chat_log'.
        If user_id is set, filter to that user.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if user_id:
                c.execute(
                    """
                    SELECT id, timestamp, command, tag, agent, user_id
                    FROM memory
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                )
            else:
                c.execute(
                    """
                    SELECT id, timestamp, command, tag, agent, user_id
                    FROM memory
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            return c.fetchall()

    def insert_chat_log(
        self,
        timestamp: str,
        session_id: str,
        user_id: str,
        role: str,
        message: str,
        response: str,
        backend: str,
        model: str,
        agent: Optional[str] = None,
        tag: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> None:
        """
        Insert a chat log entry into the canonical 'chat_log' table.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO chat_log (
                    timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    session_id,
                    user_id,
                    role,
                    message,
                    response,
                    backend,
                    model,
                    agent,
                    tag,
                    extra,
                ),
            )
            conn.commit()

    def get_chat_history(
        self,
        session_id: str,
        user_id: str = "default",
        limit: int = 20,
        offset: int = 0,
        order: str = "desc",
        role: Optional[str] = None,
        after: Optional[str] = None,  # Expects ISO8601 string
        before: Optional[str] = None,  # Expects ISO8601 string
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chat history from the canonical 'chat_log' table, with advanced options.
        - Pagination: limit, offset
        - Order: "desc" (default, newest first) or "asc"
        - Filtering: by role, timestamp range, keyword in message/response
        Returns a list of dicts with column names as keys.
        """
        query = """
            SELECT id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
            FROM chat_log
            WHERE session_id = ? AND user_id = ?
        """
        params = [session_id, user_id]
        if role:
            query += " AND role = ?"
            params.append(role)
        if after:
            query += " AND timestamp > ?"
            params.append(after)
        if before:
            query += " AND timestamp < ?"
            params.append(before)
        if keyword:
            query += " AND (message LIKE ? OR response LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw])
        order_by = "DESC" if order == "desc" else "ASC"
        query += f" ORDER BY id {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(query, params)
            rows = c.fetchall()
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in rows]

    # ---- Memory helpers ----
    def add_memory(self, user_id: str, silo: str, content: str, tags: str = "", pinned: bool = False) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, silo, content, tags, 1 if pinned else 0, now, now),
            )
            conn.commit()
            return c.lastrowid

    def list_memories(self, silo: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, user_id, silo, content, tags, pinned, created_at, updated_at FROM memory_entries WHERE silo = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (silo, limit, offset),
            )
            rows = c.fetchall()
            cols = [d[0] for d in c.description]
            return [dict(zip(cols, r)) for r in rows]

    def count_memories(self, silo: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memory_entries WHERE silo = ?", (silo,))
            return int(c.fetchone()[0])

    def update_memory(self, entry_id: int, content: Optional[str] = None, tags: Optional[str] = None, pinned: Optional[bool] = None) -> None:
        fields = []
        params = []
        if content is not None:
            fields.append("content = ?")
            params.append(content)
        if tags is not None:
            fields.append("tags = ?")
            params.append(tags)
        if pinned is not None:
            fields.append("pinned = ?")
            params.append(1 if pinned else 0)
        fields.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(entry_id)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(f"UPDATE memory_entries SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()

    def delete_memory(self, entry_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            conn.commit()

    # ---- Audit log ----
    def write_audit_log(self, event: str, entity: str, entity_id: str, user_id: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO audit_log (event, entity, entity_id, user_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                (event, entity, entity_id, user_id, ts),
            )
            conn.commit()

    # ---- Retention ----
    def prune_midterm(self, older_than_iso: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM memory_entries WHERE silo = 'midterm' AND updated_at < ?", (older_than_iso,))
            deleted = c.rowcount
            conn.commit()
            return deleted

    # ---- Thread & Project helpers ----
    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, user_id, title, summary, project_id, created_at, updated_at FROM chat_threads WHERE id = ?",
                (thread_id,),
            )
            row = c.fetchone()
            if not row:
                return None
            cols = [d[0] for d in c.description]
            return dict(zip(cols, row))

    def list_chat_threads(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, user_id, title, summary, project_id, created_at, updated_at FROM chat_threads ORDER BY updated_at DESC, id DESC"
            )
            rows = c.fetchall()
            cols = [d[0] for d in c.description]
            return [dict(zip(cols, r)) for r in rows]

    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: Optional[int] = None,
        preset_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if preset_id is None:
                c.execute(
                    "INSERT INTO chat_threads (user_id, title, summary, project_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, title, summary, project_id, now, now),
                )
            else:
                c.execute(
                    "INSERT INTO chat_threads (id, user_id, title, summary, project_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (preset_id, user_id, title, summary, project_id, now, now),
                )
            conn.commit()
            thread_id = preset_id if preset_id is not None else c.lastrowid
        return {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
        }

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        existing = self.get_chat_thread(thread_id)
        if existing:
            return existing
        return self.create_chat_thread(
            user_id=user_id,
            title=title,
            summary=summary,
            project_id=project_id,
            preset_id=thread_id,
        )

    def update_thread(
        self,
        thread_id: int,
        title: Optional[str] = None,
        project_id: Optional[Optional[int]] = None,
        summary: Optional[str] = None,
    ) -> bool:
        fields = []
        params = []
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if summary is not None:
            fields.append("summary = ?")
            params.append(summary)
        if project_id is not None:
            fields.append("project_id = ?")
            params.append(project_id)
        fields.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(thread_id)
        if not fields:
            return False
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(f"UPDATE chat_threads SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
            return c.rowcount > 0

    def delete_thread(self, thread_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Manual cascade for SQLite compatibility
            c.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
            c.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
            conn.commit()

    def update_project(self, project_id: int, name: Optional[str] = None, description: Optional[str] = None) -> None:
        fields = []
        params = []
        if name is not None:
            fields.append("name = ?")
            params.append(name)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if not fields:
            return
        params.append(project_id)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()

    def eject_threads_from_project(self, project_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE chat_threads SET project_id = NULL WHERE project_id = ?", (project_id,))
            conn.commit()

    def create_thread(
        self,
        parent_thread_id: Optional[int],
        session_id: str,
        summary: str,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        """
        Create a new thread with optional parent and summary.
        Returns the new thread_id.
        """
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO threads (parent_thread_id, session_id, summary, created_at, user_id, project_id)
                VALUES (?, ?, ?, ?, ?, ?)
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
            conn.commit()
            return c.lastrowid

    def get_thread(self, thread_id: int) -> Optional[Tuple[Any, ...]]:
        """
        Get a thread by thread_id.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT thread_id, parent_thread_id, session_id, summary, created_at, user_id, project_id FROM threads WHERE thread_id = ?",
                (thread_id,),
            )
            return c.fetchone()

    def get_child_threads(self, parent_thread_id: int) -> List[Tuple[Any, ...]]:
        """
        Get all threads with a given parent_thread_id.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT thread_id, session_id, summary, created_at, user_id, project_id FROM threads WHERE parent_thread_id = ?",
                (parent_thread_id,),
            )
            return c.fetchall()

    def insert_summary(self, thread_id: int, summary: str) -> None:
        """
        Update a thread's summary (latest rollup).
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE threads SET summary = ? WHERE thread_id = ?",
                (summary, thread_id),
            )
            conn.commit()

    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        """
        Get the summary for a thread.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT summary FROM threads WHERE thread_id = ?", (thread_id,))
            row = c.fetchone()
            return row[0] if row else None

    def add_chat_log(
        self,
        session_id: str,
        user_id: str,
        role: str,
        message: str,
        response: Optional[str] = None,
        backend: Optional[str] = None,
        model: str = "test-model",
        timestamp: Optional[str] = None,
        agent: Optional[str] = None,
        tag: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> None:
        """
        Insert a chat log entry into the canonical 'chat_log' table. Fills missing fields with defaults.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        if model is None:
            model = "test-model"
        return self.insert_chat_log(
            timestamp=timestamp,
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
            response=response,
            backend=backend,
            model=model,
            agent=agent,
            tag=tag,
            extra=extra,
        )

    # ---- Chat message helpers ----
    def create_message(self, thread_id: int, role: str, content: str, created_at: Optional[str] = None) -> int:
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO chat_messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (thread_id, role, content, created_at),
            )
            conn.commit()
            return c.lastrowid

    def list_messages(self, thread_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, thread_id, role, content, created_at FROM chat_messages WHERE thread_id = ? ORDER BY id ASC LIMIT ? OFFSET ?",
                (thread_id, limit, offset),
            )
            rows = c.fetchall()
            cols = [d[0] for d in c.description]
            return [dict(zip(cols, r)) for r in rows]

    def count_messages(self, thread_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM chat_messages WHERE thread_id = ?", (thread_id,))
            return int(c.fetchone()[0])

    def delete_message(self, thread_id: int, message_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chat_messages WHERE id = ? AND thread_id = ?", (message_id, thread_id))
            conn.commit()
