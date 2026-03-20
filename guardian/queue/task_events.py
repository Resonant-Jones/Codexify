"""Redis stream helpers for task event transport."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from guardian.queue.redis_queue import _with_reconnect  # type: ignore

logger = logging.getLogger(__name__)

_STREAM_PREFIX = "codexify:task"
_TERMINAL_EVENT_TYPES = {
    "task.completed",
    "task.failed",
    "task.cancelled",
}
_TERMINAL_EVENT_SCAN_BATCH_SIZE = 100


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stream_key(task_id: str) -> str:
    return f"{_STREAM_PREFIX}:{task_id}:events"


def publish(
    task_id: str, event_type: str, data: dict[str, Any] | None = None
) -> str:
    payload = {
        "type": event_type,
        "task_id": task_id,
        "data": json.dumps(data or {}),
        "created_at": _utc_now_iso(),
    }

    def _add(client) -> str:
        return client.xadd(_stream_key(task_id), payload)

    return _with_reconnect(_add)


def classify_event_visibility(event_type: str) -> str:
    """Classify whether an event is terminal or progress-only visibility."""

    normalized = str(event_type or "").strip()
    if normalized in _TERMINAL_EVENT_TYPES:
        return "terminal"
    return "progress"


def publish_with_visibility(
    task_id: str, event_type: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Publish an event and return a machine-readable visibility result."""

    visibility_scope = classify_event_visibility(event_type)
    result: dict[str, Any] = {
        "ok": False,
        "task_id": task_id,
        "event_type": event_type,
        "visibility_scope": visibility_scope,
        "terminal_visibility": visibility_scope == "terminal",
        "execution_continued": True,
        "event_id": None,
        "failure_class": None,
        "error": None,
    }
    try:
        event_id = publish(task_id, event_type, data)
    except Exception as exc:
        result["failure_class"] = exc.__class__.__name__
        result["error"] = str(exc)
        return result

    result["ok"] = True
    result["event_id"] = event_id
    return result


def read_events(
    task_id: str,
    last_id: str,
    *,
    block_ms: int = 15000,
    count: int = 100,
) -> list[tuple[str, dict[str, Any]]]:
    stream_key = _stream_key(task_id)

    def _read(client) -> list[tuple[str, dict[str, Any]]]:
        result = client.xread(
            {stream_key: last_id}, count=count, block=block_ms
        )
        if not result:
            return []
        _, entries = result[0]
        events: list[tuple[str, dict[str, Any]]] = []
        for event_id, fields in entries:
            data_raw = fields.get("data", "{}")
            try:
                data = json.loads(data_raw)
            except Exception:
                data = {}
            events.append(
                (
                    event_id,
                    {
                        "type": fields.get("type") or "task.event",
                        "task_id": fields.get("task_id") or task_id,
                        "data": data,
                        "created_at": fields.get("created_at"),
                    },
                )
            )
        return events

    return _with_reconnect(_read)


def describe_terminal_state(task_id: str) -> dict[str, Any]:
    """Describe whether a task stream has reached a terminal state."""
    try:
        last_id = "0-0"
        saw_events = False
        while True:
            events = read_events(
                task_id,
                last_id,
                block_ms=1,
                count=_TERMINAL_EVENT_SCAN_BATCH_SIZE,
            )
            if not events:
                break
            saw_events = True
            for event_id, event in events:
                last_id = event_id
                event_type = str(event.get("type") or "").strip()
                if event_type in _TERMINAL_EVENT_TYPES:
                    return {
                        "task_id": task_id,
                        "state": "terminal",
                        "event_id": event_id,
                        "event": event,
                        "event_type": event_type,
                        "reason": "terminal_event_found",
                    }
            if len(events) < _TERMINAL_EVENT_SCAN_BATCH_SIZE:
                break
        if saw_events:
            return {
                "task_id": task_id,
                "state": "nonterminal",
                "event_id": None,
                "event": None,
                "event_type": None,
                "reason": "terminal_event_not_found",
            }
        return {
            "task_id": task_id,
            "state": "unknown",
            "event_id": None,
            "event": None,
            "event_type": None,
            "reason": "task_events_missing",
        }
    except Exception as exc:
        logger.debug(
            "[task-events] terminal-state probe failed task_id=%s err=%s",
            task_id,
            exc,
            exc_info=True,
        )
        return {
            "task_id": task_id,
            "state": "unknown",
            "event_id": None,
            "event": None,
            "event_type": None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
