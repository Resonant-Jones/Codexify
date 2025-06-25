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
