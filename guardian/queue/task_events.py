"""Redis stream helpers for task event transport."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from guardian.protocol_tokens import (
    DELEGATION_TERMINAL_EVENT_TYPES,
    ErrorCode,
    ExecutorEventType,
    TaskEventType,
)
from guardian.queue.redis_queue import _with_reconnect  # type: ignore
from guardian.queue.redis_queue import get_queue_redis_client

logger = logging.getLogger(__name__)

_STREAM_PREFIX = "codexify:task"
_TERMINAL_EVENT_TYPES = {
    TaskEventType.TASK_COMPLETED.value,
    TaskEventType.TASK_FAILED.value,
    TaskEventType.TASK_CANCELLED.value,
    ExecutorEventType.COMPLETED.value,
    ExecutorEventType.FAILED.value,
    ExecutorEventType.CANCELLED.value,
    *DELEGATION_TERMINAL_EVENT_TYPES,
}
_TERMINAL_EVENT_SCAN_BATCH_SIZE = 100
_TASK_EVENT_FALLBACK_TYPE = TaskEventType.TASK_EVENT.value
_TASK_EVENT_PUBLISH_ERROR_CODE = ErrorCode.TASK_EVENT_PUBLISH_FAILED.value
_READ_EVENTS_BLOCK_MS = 5000
_READ_EVENTS_BATCH_SIZE = 50
_READ_EVENTS_INITIAL_BACKOFF_SECONDS = 0.5
_READ_EVENTS_MAX_BACKOFF_SECONDS = 2.0


class TaskEventPublishError(RuntimeError):
    """Typed failure raised when task-event publish cannot complete."""

    error_code = "TASK_EVENT_PUBLISH_FAILED"

    def __init__(
        self,
        task_id: str | None,
        event_type: str,
        *,
        cause: BaseException | None = None,
        visibility_scope: str | None = None,
        execution_continued: bool = True,
        failure_class: str | None = None,
        error: str | None = None,
    ):
        normalized_task_id = (
            str(task_id).strip() if task_id is not None else None
        )
        if normalized_task_id == "":
            normalized_task_id = None
        normalized_event_type = str(event_type or "").strip() or "task.event"
        normalized_visibility_scope = str(
            visibility_scope or ""
        ).strip() or classify_event_visibility(normalized_event_type)
        self.task_id = normalized_task_id
        self.event_type = normalized_event_type
        self.visibility_scope = normalized_visibility_scope
        self.terminal_visibility = normalized_visibility_scope == "terminal"
        self.execution_continued = execution_continued
        self.cause_class = cause.__class__.__name__ if cause else None
        self.failure_class = (
            str(failure_class or "").strip()
            or self.cause_class
            or self.__class__.__name__
        )
        self.error = str(error or "").strip() or (
            str(cause) if cause is not None else ""
        )
        message = (
            f"{self.error_code} task_id={self.task_id or 'unknown'} "
            f"event_type={self.event_type} "
            f"visibility_scope={self.visibility_scope} "
            f"failure_class={self.failure_class}"
        )
        if self.error:
            message = f"{message} error={self.error}"
        super().__init__(message)

    def to_publish_result(self) -> dict[str, Any]:
        return {
            "ok": False,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "visibility_scope": self.visibility_scope,
            "terminal_visibility": self.terminal_visibility,
            "execution_continued": self.execution_continued,
            "event_id": None,
            "failure_class": self.failure_class,
            "error_code": self.error_code,
            "error": self.error,
        }

    @classmethod
    def from_publish_result(
        cls, result: dict[str, Any]
    ) -> TaskEventPublishError:
        raw_exception = result.get("exception")
        cause = (
            raw_exception if isinstance(raw_exception, BaseException) else None
        )
        event_type = str(result.get("event_type") or "").strip() or "task.event"
        visibility_scope = str(
            result.get("visibility_scope") or ""
        ).strip() or classify_event_visibility(event_type)
        task_id = result.get("task_id")
        normalized_task_id = (
            str(task_id).strip() if task_id is not None else None
        )
        if normalized_task_id == "":
            normalized_task_id = None
        return cls(
            normalized_task_id,
            event_type,
            cause=cause,
            visibility_scope=visibility_scope,
            execution_continued=bool(result.get("execution_continued", True)),
            failure_class=(
                str(result.get("failure_class") or "").strip() or None
            ),
            error=str(result.get("error") or "").strip() or None,
        )


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
        "error_code": None,
        "failure_class": None,
        "error": None,
    }
    try:
        event_id = publish(task_id, event_type, data)
    except Exception as exc:
        result["error_code"] = _TASK_EVENT_PUBLISH_ERROR_CODE
        result["failure_class"] = exc.__class__.__name__
        result["error"] = str(exc)
        result["error_code"] = TaskEventPublishError.error_code
        result["exception"] = exc
        return result

    result["ok"] = True
    result["event_id"] = event_id
    return result


def read_events(
    task_id: str,
    last_id: str,
    *,
    block_ms: int = _READ_EVENTS_BLOCK_MS,
    count: int = _READ_EVENTS_BATCH_SIZE,
) -> list[tuple[str, dict[str, Any]]]:
    stream_key = _stream_key(task_id)
    backoff = _READ_EVENTS_INITIAL_BACKOFF_SECONDS

    while True:
        try:
            redis = get_queue_redis_client()
            result = redis.xread(
                streams={stream_key: last_id},
                block=block_ms,
                count=count,
            )
            backoff = _READ_EVENTS_INITIAL_BACKOFF_SECONDS
            break
        except Exception as exc:
            logger.warning("[task-events] read failed: %s", str(exc))
            time.sleep(backoff)
            backoff = min(
                backoff * 2,
                _READ_EVENTS_MAX_BACKOFF_SECONDS,
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
                    "type": fields.get("type") or _TASK_EVENT_FALLBACK_TYPE,
                    "task_id": fields.get("task_id") or task_id,
                    "data": data,
                    "created_at": fields.get("created_at"),
                },
            )
        )
    return events


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
