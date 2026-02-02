"""Event coherence contracts for SSE and in-process event payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

MESSAGE_CREATED_TOPIC = "message.created"


def _coerce_int(value: Any) -> int | None:
    """Return an integer when possible; otherwise None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_text(value: Any) -> str:
    """Normalize a text payload into a trimmed string."""
    if value is None:
        return ""
    return str(value)


def _coerce_timestamp(value: Any) -> str | None:
    """Normalize timestamps to ISO-8601 strings when possible."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _normalize_message_payload(
    payload: dict[str, Any]
) -> dict[str, Any] | None:
    """Return a canonical message payload or None when it has no semantic delta."""
    # Accept both top-level and nested message payloads.
    message = payload.get("message")
    message_dict = message if isinstance(message, dict) else {}

    thread_id = _coerce_int(
        payload.get("thread_id")
        or payload.get("threadId")
        or message_dict.get("thread_id")
        or message_dict.get("threadId")
    )
    message_id = _coerce_int(
        payload.get("message_id")
        or payload.get("messageId")
        or payload.get("id")
        or message_dict.get("message_id")
        or message_dict.get("messageId")
        or message_dict.get("id")
    )
    role = _coerce_text(payload.get("role") or message_dict.get("role")).strip()
    content = _coerce_text(
        payload.get("content") or message_dict.get("content")
    )
    created_at = _coerce_timestamp(
        payload.get("created_at")
        or payload.get("createdAt")
        or message_dict.get("created_at")
        or message_dict.get("createdAt")
    )

    # Drop no-op or malformed payloads that do not affect the UI.
    if thread_id is None or message_id is None:
        return None
    if not role:
        return None
    if not content or not content.strip():
        return None

    normalized_message = {
        "id": message_id,
        "thread_id": thread_id,
        "role": role,
        "content": content,
        "created_at": created_at,
    }

    normalized = dict(payload)
    normalized.update(
        {
            "thread_id": thread_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "created_at": created_at,
            "message": normalized_message,
        }
    )
    return normalized


def coerce_event_payload(
    topic: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    """Normalize payloads based on the event topic."""
    if topic == MESSAGE_CREATED_TOPIC:
        return _normalize_message_payload(payload)
    return payload
