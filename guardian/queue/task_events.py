"""Redis stream helpers for task event transport."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from guardian.queue.redis_queue import _with_reconnect  # type: ignore

logger = logging.getLogger(__name__)

_STREAM_PREFIX = "codexify:task"


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
