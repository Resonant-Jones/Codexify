"""
Guardian Event Log
~~~~~~~~~~~~~~~~~~

Utilities for writing Guardian loop events into Postgres.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from psycopg import Connection
from psycopg.types.json import Json


def log_guardian_event(
    conn: Connection,
    *,
    persona_tag: str,
    event_type: str,
    summary: str,
    origin: str,
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> str:
    event_id = str(uuid4())
    payload_value = Json(payload) if payload is not None else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO guardian_event_log (
                id, ts, persona_tag, thread_id, message_id,
                event_type, origin, summary, payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_id,
                datetime.now(UTC),
                persona_tag,
                thread_id,
                message_id,
                event_type,
                origin,
                summary,
                payload_value,
            ),
        )
    return event_id
