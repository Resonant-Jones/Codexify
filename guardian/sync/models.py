import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DB_PATH = os.getenv("GUARDIAN_DB_PATH", "guardian.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def _init():
    with _conn() as conn:
        c = conn.cursor()
        # EventLog with unique event_id for idempotency
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_event_log (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        # Thread state (upsert by thread_id)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_thread_state (
                thread_id TEXT PRIMARY KEY,
                state TEXT,
                updated_at TEXT
            )
            """
        )
        # Persona selection (upsert by user_id)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_persona_selection (
                user_id TEXT PRIMARY KEY,
                persona TEXT,
                updated_at TEXT
            )
            """
        )
        # Codex results (upsert by result_id)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_codex_result (
                result_id TEXT PRIMARY KEY,
                content TEXT,
                meta TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()


_init()


def record_event(event_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """Returns True if this is a new event, False if duplicate."""
    created = datetime.now(timezone.utc).isoformat()
    data = json.dumps(payload, ensure_ascii=False)
    with _conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO sync_event_log (event_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (event_id, event_type, data, created),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def upsert_thread_state(thread_id: str, state: Dict[str, Any]) -> None:
    updated = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "REPLACE INTO sync_thread_state (thread_id, state, updated_at) VALUES (?, ?, ?)",
            (thread_id, json.dumps(state, ensure_ascii=False), updated),
        )
        conn.commit()


def upsert_persona(user_id: str, persona: str) -> None:
    updated = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "REPLACE INTO sync_persona_selection (user_id, persona, updated_at) VALUES (?, ?, ?)",
            (user_id, persona, updated),
        )
        conn.commit()


def upsert_codex_result(result_id: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
    updated = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "REPLACE INTO sync_codex_result (result_id, content, meta, updated_at) VALUES (?, ?, ?, ?)",
            (result_id, content, json.dumps(meta or {}, ensure_ascii=False), updated),
        )
        conn.commit()

