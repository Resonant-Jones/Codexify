from __future__ import annotations

import copy
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional, cast

from guardian.core.types.candidate_trace import CandidateTrace

_DEFAULT_TTL_SECONDS = 600
_MIN_TTL_SECONDS = 300
_MAX_TTL_SECONDS = 900


@dataclass(slots=True)
class _StoredCandidateTrace:
    trace: CandidateTrace
    stored_at: float
    expires_at: float


_candidate_traces: dict[tuple[str, str], _StoredCandidateTrace] = {}
_candidate_trace_lock = threading.Lock()


def _candidate_trace_ttl_seconds() -> int:
    raw = os.getenv("CANDIDATE_TRACE_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        value = int(raw)
    except Exception:
        value = _DEFAULT_TTL_SECONDS
    return max(_MIN_TTL_SECONDS, min(_MAX_TTL_SECONDS, value))


def _normalize_trace(trace: CandidateTrace) -> CandidateTrace | None:
    payload = copy.deepcopy(dict(trace))
    thread_id = str(payload.get("thread_id") or "").strip()
    request_id = str(payload.get("request_id") or "").strip()
    if not thread_id or not request_id:
        return None
    payload["thread_id"] = thread_id
    payload["request_id"] = request_id
    candidates: Any = payload.get("candidates") or []
    payload["candidates"] = cast(list[dict[str, Any]], list(candidates))
    payload["selection_strategy"] = str(payload.get("selection_strategy") or "")
    payload["created_at"] = str(payload.get("created_at") or "")
    return payload  # type: ignore[return-value]


def _prune_expired_locked(now: float | None = None) -> None:
    current = now if now is not None else time.monotonic()
    expired = [
        key
        for key, record in _candidate_traces.items()
        if record.expires_at <= current
    ]
    for key in expired:
        _candidate_traces.pop(key, None)


def store_candidate_trace(trace: CandidateTrace) -> None:
    normalized = _normalize_trace(trace)
    if normalized is None:
        return
    now = time.monotonic()
    record = _StoredCandidateTrace(
        trace=normalized,
        stored_at=now,
        expires_at=now + _candidate_trace_ttl_seconds(),
    )
    key = (normalized["thread_id"], normalized["request_id"])
    with _candidate_trace_lock:
        _prune_expired_locked(now)
        _candidate_traces[key] = record


def get_latest_candidate_trace(thread_id: str) -> CandidateTrace | None:
    normalized_thread_id = str(thread_id or "").strip()
    if not normalized_thread_id:
        return None

    now = time.monotonic()
    with _candidate_trace_lock:
        _prune_expired_locked(now)
        latest: _StoredCandidateTrace | None = None
        for (
            stored_thread_id,
            _request_id,
        ), record in _candidate_traces.items():
            if stored_thread_id != normalized_thread_id:
                continue
            if latest is None or record.stored_at > latest.stored_at:
                latest = record

    if latest is None:
        return None

    return copy.deepcopy(latest.trace)
