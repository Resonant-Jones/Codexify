"""Ephemeral latest-per-thread inspection snapshots for graph-write outcomes."""

from __future__ import annotations

import copy
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any

from guardian.queue.redis_queue import get_redis_connection

GRAPH_WRITE_INSPECTION_KEY_PREFIX = "codexify:graph-write:inspection"
GRAPH_WRITE_INSPECTION_TTL_SECONDS = 3600
GRAPH_WRITE_INSPECTION_STATUS_CLAIMED = "claimed"
GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED = "duplicate_skipped"
MAX_ADAPTER_FAILURE_MESSAGE_CHARS = 240

_FALLBACK_LOCK = threading.Lock()
_FALLBACK_LATEST: dict[str, dict[str, Any]] = {}
_FALLBACK_EXPIRES_AT: dict[str, float] = {}

_SNAPSHOT_FIELDS = (
    "thread_id",
    "request_id",
    "candidate_trace_id",
    "graph_write_id",
    "idempotency_key",
    "receipt_status",
    "adapter_failure_message",
    "node_count",
    "edge_count",
    "warning_count",
    "node_types",
    "edge_types",
    "created_at",
)


def _inspection_key(thread_id: str | int) -> str:
    return f"{GRAPH_WRITE_INSPECTION_KEY_PREFIX}:{str(thread_id).strip()}"


def _normalize_thread_id(thread_id: str | int) -> str | int | None:
    if thread_id is None:
        return None
    value = str(thread_id).strip()
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _coerce_int(raw: Any) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _coerce_text_list(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple, set)):
        return []
    result: list[str] = []
    for item in raw:
        value = str(item).strip()
        if value:
            result.append(value)
    return result


def _sanitize_adapter_failure_message(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:MAX_ADAPTER_FAILURE_MESSAGE_CHARS]


def _normalize_snapshot(
    thread_id: str | int,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized_thread_id = _normalize_thread_id(thread_id)
    if normalized_thread_id is None:
        return None

    payload = dict(snapshot or {})
    created_at = str(payload.get("created_at") or "").strip()
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    normalized = {
        "thread_id": normalized_thread_id,
        "request_id": str(payload.get("request_id") or "").strip(),
        "candidate_trace_id": str(
            payload.get("candidate_trace_id") or ""
        ).strip(),
        "graph_write_id": str(payload.get("graph_write_id") or "").strip(),
        "idempotency_key": str(payload.get("idempotency_key") or "").strip(),
        "receipt_status": str(payload.get("receipt_status") or "").strip(),
        "adapter_failure_message": _sanitize_adapter_failure_message(
            payload.get("adapter_failure_message")
        ),
        "node_count": _coerce_int(payload.get("node_count")),
        "edge_count": _coerce_int(payload.get("edge_count")),
        "warning_count": _coerce_int(payload.get("warning_count")),
        "node_types": _coerce_text_list(payload.get("node_types")),
        "edge_types": _coerce_text_list(payload.get("edge_types")),
        "created_at": created_at,
    }
    return {
        field: copy.deepcopy(normalized[field]) for field in _SNAPSHOT_FIELDS
    }


def _store_fallback_snapshot(
    thread_id: str | int,
    snapshot: dict[str, Any],
    *,
    ttl_seconds: int = GRAPH_WRITE_INSPECTION_TTL_SECONDS,
) -> None:
    key = str(_normalize_thread_id(thread_id))
    if key == "None":
        return
    expires_at = time.time() + max(1, int(ttl_seconds))
    with _FALLBACK_LOCK:
        _FALLBACK_LATEST[key] = copy.deepcopy(snapshot)
        _FALLBACK_EXPIRES_AT[key] = expires_at


def _get_fallback_snapshot(thread_id: str | int) -> dict[str, Any] | None:
    key = str(_normalize_thread_id(thread_id))
    if key == "None":
        return None
    now = time.time()
    with _FALLBACK_LOCK:
        expires_at = _FALLBACK_EXPIRES_AT.get(key)
        if expires_at is not None and expires_at <= now:
            _FALLBACK_EXPIRES_AT.pop(key, None)
            _FALLBACK_LATEST.pop(key, None)
            return None
        snapshot = _FALLBACK_LATEST.get(key)
        return copy.deepcopy(snapshot) if snapshot is not None else None


def _store_redis_snapshot(
    thread_id: str | int,
    snapshot: dict[str, Any],
    *,
    ttl_seconds: int = GRAPH_WRITE_INSPECTION_TTL_SECONDS,
) -> None:
    client = get_redis_connection()
    client.set(
        _inspection_key(thread_id),
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")),
        ex=max(1, int(ttl_seconds)),
    )


def _get_redis_snapshot(thread_id: str | int) -> dict[str, Any] | None:
    client = get_redis_connection()
    raw = client.get(_inspection_key(thread_id))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    elif not isinstance(raw, str):
        raw = str(raw)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return None
    return _normalize_snapshot(thread_id, payload)


def store_graph_write_inspection_snapshot(
    thread_id: str | int, snapshot: dict[str, Any]
) -> None:
    normalized = _normalize_snapshot(thread_id, snapshot)
    if normalized is None:
        return

    try:
        _store_redis_snapshot(thread_id, normalized)
    except Exception:
        _store_fallback_snapshot(thread_id, normalized)
        # The worker treats this as advisory inspection state only.
        return


def get_latest_graph_write_inspection(
    thread_id: str | int,
) -> dict[str, Any] | None:
    try:
        snapshot = _get_redis_snapshot(thread_id)
        if snapshot is not None:
            return snapshot
    except Exception:
        pass
    return _get_fallback_snapshot(thread_id)


__all__ = [
    "GRAPH_WRITE_INSPECTION_KEY_PREFIX",
    "GRAPH_WRITE_INSPECTION_STATUS_CLAIMED",
    "GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED",
    "GRAPH_WRITE_INSPECTION_TTL_SECONDS",
    "MAX_ADAPTER_FAILURE_MESSAGE_CHARS",
    "get_latest_graph_write_inspection",
    "store_graph_write_inspection_snapshot",
]
