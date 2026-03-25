"""Runtime protocol tokens for core chat-loop contracts."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class AcceptanceStatus(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_DEGRADED = "accepted_degraded"


class TaskEventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_EVENT = "task.event"


class ErrorCode(str, Enum):
    QUEUE_ENQUEUE_FAILED = "QUEUE_ENQUEUE_FAILED"
    CHAT_COMPLETE_ENQUEUE_FAILED = "CHAT_COMPLETE_ENQUEUE_FAILED"
    TASK_EVENT_PUBLISH_FAILED = "TASK_EVENT_PUBLISH_FAILED"
    CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED = (
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED"
    )


class EmbeddingLifecycleStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


ACCEPTANCE_STATUSES: frozenset[str] = frozenset(
    {status.value for status in AcceptanceStatus}
)
TASK_EVENT_TYPES: frozenset[str] = frozenset(
    {event_type.value for event_type in TaskEventType}
)
ERROR_CODES: frozenset[str] = frozenset(
    {error_code.value for error_code in ErrorCode}
)
EMBEDDING_LIFECYCLE_STATUSES: frozenset[str] = frozenset(
    {status.value for status in EmbeddingLifecycleStatus}
)

__all__ = [
    "AcceptanceStatus",
    "TaskEventType",
    "ErrorCode",
    "EmbeddingLifecycleStatus",
    "ACCEPTANCE_STATUSES",
    "TASK_EVENT_TYPES",
    "ERROR_CODES",
    "EMBEDDING_LIFECYCLE_STATUSES",
]
