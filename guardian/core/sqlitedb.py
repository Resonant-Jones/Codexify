"""SqliteChatLogDB: SQLite implementation of ChatDB for testing and local development."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .chat_db import ChatDB


class SqliteChatLogDB(ChatDB):
    """SQLite implementation of the ChatDB interface."""

    def __init__(self, db_path: str = "guardian.db") -> None:
        if db_path in {"__DISABLE_SQLITE__", "DISABLE_SQLITE"}:
            raise RuntimeError("SQLite has been disabled via GUARDIAN_DB_PATH")
        self.db_path = db_path
        self._events_outbox_ready = False
        self._connector_tables_ready = False
        self._init_schema()

    def _connect(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        """Initialize database schema."""
        with self._connect() as conn:
            c = conn.cursor()
            # Projects table
            c.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    icon TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Chat threads table
            c.execute("""
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    title TEXT DEFAULT 'New Chat',
                    summary TEXT DEFAULT '',
                    project_id INTEGER,
                    parent_id INTEGER,
                    archived_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (parent_id) REFERENCES chat_threads(id)
                )
            """)
            # Chat messages table
            c.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                )
            """)
            # Memory entries table
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    silo TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Audit log table
            c.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # ---- Projects ----
    def create_project(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return c.lastrowid

    def ensure_project(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM projects WHERE name = ?", (name,))
            row = c.fetchone()
            if row:
                return row[0]
            c.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return c.lastrowid

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM projects ORDER BY created_at DESC")
            return [dict(row) for row in c.fetchall()]

    def delete_project(self, project_id: int) -> bool:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return c.rowcount > 0

    def update_project(
        self, project_id: int, name: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if not updates:
            return
        params.append(project_id)
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                f"UPDATE projects SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )
            conn.commit()

    def eject_threads_from_project(self, project_id: int) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE chat_threads SET project_id = 1 WHERE project_id = ?", (project_id,))
            conn.commit()

    # ---- Chat Threads ----
    def create_chat_thread(
        self,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO chat_threads (user_id, title, summary, project_id, parent_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, title, summary, project_id, parent_id)
            )
            conn.commit()
            thread_id = c.lastrowid
            c.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
            return dict(c.fetchone())

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
            row = c.fetchone()
            if row:
                return dict(row)
            c.execute(
                """INSERT INTO chat_threads (id, user_id, title, summary, project_id, parent_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (thread_id, user_id, title, summary, project_id, parent_id)
            )
            conn.commit()
            c.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
            return dict(c.fetchone())

    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_recent_thread(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM chat_threads WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            row = c.fetchone()
            return dict(row) if row else None

    def list_chat_threads(
        self, *, limit: int = 50, offset: int = 0, user_id: Optional[str] = None, project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            query = "SELECT * FROM chat_threads WHERE archived_at IS NULL"
            params = []
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if project_id is not None:
                query += " AND project_id = ?"
                params.append(project_id)
            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]

    def count_chat_threads(self) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM chat_threads")
            return c.fetchone()[0]

    def update_thread(
        self,
        thread_id: int,
        *,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> bool:
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if project_id is not None:
            updates.append("project_id = ?")
            params.append(project_id)
        if not updates:
            return False
        params.append(thread_id)
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                f"UPDATE chat_threads SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )
            conn.commit()
            return c.rowcount > 0

    def archive_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            c.execute("UPDATE chat_threads SET archived_at = ? WHERE id = ?", (now, thread_id))
            conn.commit()
            if c.rowcount > 0:
                return self.get_chat_thread(thread_id)
            return None

    def unarchive_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE chat_threads SET archived_at = NULL WHERE id = ?", (thread_id,))
            conn.commit()
            if c.rowcount > 0:
                return self.get_chat_thread(thread_id)
            return None

    def delete_thread(self, thread_id: int, force: bool = False) -> bool:
        with self._connect() as conn:
            c = conn.cursor()
            if not force:
                c.execute("SELECT archived_at FROM chat_threads WHERE id = ?", (thread_id,))
                row = c.fetchone()
                if not row or row[0] is None:
                    return False
            c.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
            conn.commit()
            return c.rowcount > 0

    # ---- Chat Messages ----
    def create_message(
        self, thread_id: int, role: str, content: str, created_at: Optional[str] = None
    ) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            if created_at:
                c.execute(
                    "INSERT INTO chat_messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (thread_id, role, content, created_at)
                )
            else:
                c.execute(
                    "INSERT INTO chat_messages (thread_id, role, content) VALUES (?, ?, ?)",
                    (thread_id, role, content)
                )
            conn.commit()
            return c.lastrowid

    def list_messages(
        self, thread_id: int, *, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """SELECT * FROM chat_messages
                   WHERE thread_id = ?
                   ORDER BY id ASC
                   LIMIT ? OFFSET ?""",
                (thread_id, limit, offset)
            )
            return [dict(row) for row in c.fetchall()]

    def count_messages(self, thread_id: int) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM chat_messages WHERE thread_id = ?", (thread_id,))
            return c.fetchone()[0]

    def count_all_messages(self) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM chat_messages")
            return c.fetchone()[0]

    def delete_message(self, thread_id: int, message_id: int) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chat_messages WHERE id = ? AND thread_id = ?", (message_id, thread_id))
            conn.commit()

    # ---- Memory ----
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
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), COALESCE(?, CURRENT_TIMESTAMP))""",
                (user_id, silo, content, tags, 1 if pinned else 0, created_at, updated_at)
            )
            conn.commit()
            return c.lastrowid

    def list_memories(
        self, silo: str, *, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM memory_entries WHERE silo = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (silo, limit, offset)
            )
            return [dict(row) for row in c.fetchall()]

    def count_memories(self, silo: str) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memory_entries WHERE silo = ?", (silo,))
            return c.fetchone()[0]

    def update_memory(
        self,
        entry_id: int,
        *,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        pinned: Optional[bool] = None,
    ) -> None:
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        if pinned is not None:
            updates.append("pinned = ?")
            params.append(1 if pinned else 0)
        if not updates:
            return
        params.append(entry_id)
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                f"UPDATE memory_entries SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )
            conn.commit()

    def delete_memory(self, entry_id: int) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            conn.commit()

    def prune_midterm(self, older_than_iso: str) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM memory_entries WHERE silo = 'midterm' AND updated_at < ?",
                (older_than_iso,)
            )
            conn.commit()
            return c.rowcount

    def search_memory(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM memory_entries WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            return [dict(row) for row in c.fetchall()]

    # ---- Legacy thread methods ----
    def create_thread(
        self,
        parent_thread_id: Optional[int],
        session_id: str,
        summary: str,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        proj_id = int(project_id) if project_id else None
        thread = self.create_chat_thread(
            user_id=user_id,
            title="New Chat",
            summary=summary,
            project_id=proj_id,
            parent_id=parent_thread_id,
        )
        return thread["id"]

    def get_thread(self, thread_id: int) -> Optional[Tuple[Any, ...]]:
        thread = self.get_chat_thread(thread_id)
        if not thread:
            return None
        return (
            thread["id"],
            thread.get("parent_id"),
            None,  # session_id
            thread.get("summary"),
            thread.get("created_at"),
            thread.get("user_id"),
            thread.get("project_id"),
        )

    def list_threads(
        self, *, user_id: Optional[str] = None, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        proj_id = int(project_id) if project_id else None
        return self.list_chat_threads(user_id=user_id, project_id=proj_id)

    def get_child_threads(self, parent_thread_id: int) -> List[Tuple[Any, ...]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM chat_threads WHERE parent_id = ?", (parent_thread_id,))
            return [dict(row) for row in c.fetchall()]

    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        thread = self.get_chat_thread(thread_id)
        return thread.get("summary") if thread else None

    def get_chat_history(
        self, *, session_id: Optional[str] = None, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        # Simplified implementation
        return []

    # ---- Audit log ----
    def write_audit_log(
        self, event: str, entity: str, entity_id: str, user_id: str
    ) -> None:
        try:
            with self._connect() as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO audit_log (event, entity, entity_id, user_id) VALUES (?, ?, ?, ?)",
                    (event, entity, entity_id, user_id)
                )
                conn.commit()
        except Exception:
            pass

    # ---- Stubs for unimplemented methods ----
    def insert_memory_event(
        self, *, content: str, tag: Optional[str], agent: str, type_: str, parent_id: Optional[int] = None
    ) -> int:
        return 0

    def history_entries(
        self, *, limit: int = 50, tag: Optional[str] = None, agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return []

    def ensure_sync_job_support(self) -> None:
        pass

    def create_sync_job(
        self, connector_id: str, *, status: str = "queued", metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {}

    def update_sync_job(
        self,
        job_id: int,
        *,
        status: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        attempts: Optional[int] = None,
        last_error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {}

    def list_recent_sync_jobs(
        self, *, connector_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        return []

    def get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return None

    def upsert_agent_profile(self, agent_id: str, **updates: Any) -> None:
        pass

    def check_summarization_allowed(
        self, agent_id: str, requested_by: str
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def create_connector_config(
        self, name: str, type_: str, config: Dict[str, Any], schedule: Optional[str] = None
    ) -> Dict[str, Any]:
        return {}

    def update_connector_config(
        self, name: str, *, config: Optional[Dict[str, Any]] = None, schedule: Optional[str] = None
    ) -> Dict[str, Any]:
        return {}

    def list_connector_configs(self, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def list_connector_configs_with_last_run(self) -> List[Dict[str, Any]]:
        return []

    def get_connector_config(self, name: str) -> Optional[Dict[str, Any]]:
        return None

    def create_connector_run(
        self, config_id: int, *, status: str, started_at: str, error: Optional[str] = None
    ) -> Dict[str, Any]:
        return {}

    def complete_connector_run(
        self, run_id: int, *, status: str, finished_at: str, error: Optional[str] = None
    ) -> Dict[str, Any]:
        return {}

    def get_last_connector_run(self, config_id: int) -> Optional[Dict[str, Any]]:
        return None

    def upsert_raw_documents(self, config_id: int, docs: List[Dict[str, Any]]) -> None:
        pass

    def list_raw_documents_for_config(
        self, config_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return []

    def ensure_event_outbox(self) -> None:
        pass

    def append_event(
        self, topic: str, payload: Dict[str, Any], tenant_id: str = "default"
    ) -> None:
        pass

    def list_events_after(self, last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return []

    def delete_events_through(self, last_id: int, tenant_id: Optional[str] = None) -> None:
        pass

    def table_exists(self, table_name: str) -> bool:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return c.fetchone() is not None
