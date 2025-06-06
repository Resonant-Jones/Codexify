

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
from typing import Optional, List, Tuple, Any


class GuardianDB:
    """Handles all low-level memory persistence in SQLite for Guardian."""

    def __init__(self, db_path: str = "guardian.db"):
        self.db_path = db_path

    def init_db(self):
        """Initializes the database schema for memory storage."""
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

    def insert_log(
        self,
        command: str,
        tag: Optional[str] = None,
        agent: Optional[str] = None,
        timestamp: Optional[str] = None,
        user_id: str = "default"
    ):
        """Insert a log entry into the memory table."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO memory (timestamp, command, tag, agent, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, command, tag, agent, user_id)
            )
            conn.commit()

    def get_history(
        self,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Tuple[Any, ...]]:
        """
        Retrieve memory rows (most recent first).
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
                    (user_id, limit)
                )
            else:
                c.execute(
                    """
                    SELECT id, timestamp, command, tag, agent, user_id
                    FROM memory
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            return c.fetchall()