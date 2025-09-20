"""PgDB module

PostgreSQL implementation of the ``ChatDB`` abstract base class, providing
database operations for chat threads, messages, memory entries, projects,
and agent profiles. This module mirrors the SQLite implementation in
``guardian/core/db.py`` but uses ``psycopg`` to communicate with a
PostgreSQL database.
"""

# guardian/core/pgdb.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row

from .chat_db import ChatDB


class PgDB(ChatDB):
    def __init__(self, dsn: str):
        self.dsn = dsn

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    # ---- chat_threads --------------------------------------------------
    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
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
                return dict(row)

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
        with self._connect() as conn:
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
            return dict(row)
        raise RuntimeError("Failed to ensure chat thread")

    # ---- threads helpers -------------------------------------------------
    def get_recent_thread(self, user_id: str):
        """Return the most recently‑updated thread for a user (or None)."""
        with self._connect() as conn:
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
                thread = dict(row)

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
                return dict(row) if row else None

    def list_chat_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return a list of thread rows, newest first, with optional filters."""
        clauses: List[str] = []
        params: List[Any] = []
        if user_id is not None:
            clauses.append("user_id = %s")
            params.append(user_id)
        if project_id is not None:
            clauses.append("project_id = %s")
            params.append(project_id)

        query = (
            "SELECT id, user_id, title, summary, project_id, created_at, updated_at "
            "FROM chat_threads"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

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
    ):
        """Patch fields on a thread and return the updated row."""
        fields: List[str] = []
        params: List[Any] = []
        if title is not None:
            fields.append("title = %s")
            params.append(title)
        if summary is not None:
            fields.append("summary = %s")
            params.append(summary)
        if project_id is not None:
            fields.append("project_id = %s")
            params.append(project_id)

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

    def delete_thread(self, thread_id: int):
        """Hard‑delete a thread and cascade messages."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_messages WHERE thread_id = %s", (thread_id,)
                )
                cur.execute("DELETE FROM chat_threads WHERE id = %s", (thread_id,))

    def create_thread(
        self,
        parent_thread_id: Optional[int],
        session_id: str,
        summary: str,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        created_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor(row_factory=None) as cur:
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

    def get_thread(self, thread_id: int) -> Optional[Tuple[Any, ...]]:
        with self._connect() as conn:
            with conn.cursor(row_factory=None) as cur:
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
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT thread_id, parent_thread_id, session_id, summary, created_at, user_id, project_id "
            "FROM threads WHERE 1=1"
        )
        params: List[Any] = []
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
        """Set project_id=NULL for all threads in a project (called before project delete)."""
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

    def list_projects(self) -> List[Dict[str, Any]]:
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
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        fields: List[str] = []
        params: List[Any] = []
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
        """Return threads whose parent_id = given id (stub for future hierarchy)."""
        with self._connect() as conn:
            with conn.cursor(row_factory=None) as cur:
                cur.execute(
                    """
                    SELECT thread_id, session_id, summary, created_at, user_id, project_id
                    FROM threads
                    WHERE parent_thread_id = %s
                    """,
                    (parent_id,),
                )
                return cur.fetchall()

    def get_thread_summary(self, thread_id: int):
        """Return only the summary field for a thread (or None)."""
        with self._connect() as conn:
            with conn.cursor(row_factory=None) as cur:
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
        created_at: Optional[str] = None,
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
        self, thread_id: int, *, limit: int | None = None, offset: int | None = None
    ):
        """Return messages for a thread ordered by created_at ASC."""
        limit_val = limit if limit is not None else 50
        offset_val = offset if offset is not None else 0
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, thread_id, role, content, created_at
                    FROM chat_messages
                    WHERE thread_id = %s
                    ORDER BY created_at ASC, id ASC
                    LIMIT %s OFFSET %s
                    """,
                    (thread_id, limit_val, offset_val),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

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
        session_id: Optional[str] = None,
        user_id: str = "default",
        limit: int = 20,
        offset: int = 0,
        order: str = "desc",
        role: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra "
            "FROM chat_log WHERE 1=1"
        )
        params: List[Any] = []
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
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
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
        tag: Optional[str],
        agent: str,
        type_: str,
        parent_id: Optional[int] = None,
    ) -> int:
        tags_parts: List[str] = []
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
        fields: List[str] = []
        params: List[Any] = []
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
                cur.execute("DELETE FROM memory_entries WHERE id = %s", (entry_id,))

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
    ) -> List[Dict[str, Any]]:
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

    def history_entries(
        self, *, limit: int = 50, tag: str | None = None, agent: str | None = None
    ):
        clauses: List[str] = []
        params: List[Any] = []
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
                    "summarization_frequency": row.get("summarization_frequency"),
                    "last_summarized_at": last_summarized_val,
                }

    def upsert_agent_profile(self, agent_id: str, **fields):
        if not fields:
            return

        columns = ["agent_id"]
        placeholders = ["%s"]
        values: List[Any] = [agent_id]
        updates_clause: List[str] = []

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
            updates_clause.append("last_summarized_at = EXCLUDED.last_summarized_at")

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

        delta_minutes = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
        if delta_minutes >= freq:
            return True, ""
        remaining = max(int(freq - delta_minutes), 0)
        return False, f"Next summarization available in {remaining} min"
