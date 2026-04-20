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


class ToolTurnState(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class LoopStopReason(str, Enum):
    MODEL_FINAL_ANSWER = "model_final_answer"
    TOOL_TURN_COMPLETED = "tool_turn_completed"
    TOOL_TURN_BLOCKED = "tool_turn_blocked"
    TOOL_TURN_FAILED = "tool_turn_failed"
    TOOL_TURN_MALFORMED = "tool_turn_malformed"
    TOOL_TURN_LIMIT_REACHED = "tool_turn_limit_reached"


class DelegationJobStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


DELEGATION_SUMMARY_OUTCOME_TYPE = "task_summary"


class DelegationExecutorName(str, Enum):
    CODEX = "codex"


class ExecutorId(str, Enum):
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    OPENCODE = "opencode"


class ExecutorReleasePosture(str, Enum):
    OFFICIAL = "official"
    OPTIONAL = "optional"
    USER_CONFIGURED = "user_configured"


class ExecutorAuthMode(str, Enum):
    DIRECT_PROVIDER = "direct_provider"
    LOCAL_MODEL = "local_model"
    GATEWAY_BASE_URL = "gateway_base_url"


class ExecutorAvailabilityState(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_INSTALLED = "not_installed"


class ExecutorAuthState(str, Enum):
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    UNKNOWN = "unknown"


class ExecutorEventType(str, Enum):
    PROGRESS = "executor.progress"
    ESCALATION = "executor.escalation"
    COMPLETED = "executor.completed"
    FAILED = "executor.failed"
    CANCELLED = "executor.cancelled"


class ExecutorEscalationKind(str, Enum):
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_PERMISSION = "needs_permission"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    TOOLING_LIMIT = "tooling_limit"


class DelegationEventType(str, Enum):
    CREATED = "delegation.created"
    RUNNING = "delegation.running"
    PROGRESS = "delegation.progress"
    COMPLETED = "delegation.completed"
    FAILED = "delegation.failed"
    CANCELLED = "delegation.cancelled"


class ErrorCode(str, Enum):
    QUEUE_ENQUEUE_FAILED = "QUEUE_ENQUEUE_FAILED"
    CHAT_COMPLETE_ENQUEUE_FAILED = "CHAT_COMPLETE_ENQUEUE_FAILED"
    TASK_EVENT_PUBLISH_FAILED = "TASK_EVENT_PUBLISH_FAILED"
    CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED = (
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED"
    )
    DELEGATION_EXECUTOR_UNSUPPORTED = "DELEGATION_EXECUTOR_UNSUPPORTED"
    DELEGATION_EXECUTOR_NOT_FOUND = "DELEGATION_EXECUTOR_NOT_FOUND"
    DELEGATION_EXECUTOR_TIMEOUT = "DELEGATION_EXECUTOR_TIMEOUT"
    DELEGATION_EXECUTOR_NONZERO_EXIT = "DELEGATION_EXECUTOR_NONZERO_EXIT"
    DELEGATION_EXECUTOR_SPAWN_FAILED = "DELEGATION_EXECUTOR_SPAWN_FAILED"


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
TOOL_TURN_STATES: frozenset[str] = frozenset(
    {state.value for state in ToolTurnState}
)
LOOP_STOP_REASONS: frozenset[str] = frozenset(
    {reason.value for reason in LoopStopReason}
)
DELEGATION_JOB_STATUSES: frozenset[str] = frozenset(
    {status.value for status in DelegationJobStatus}
)
DELEGATION_EXECUTOR_NAMES: frozenset[str] = frozenset(
    {executor.value for executor in DelegationExecutorName}
)
EXECUTOR_IDS: frozenset[str] = frozenset(
    {executor.value for executor in ExecutorId}
)
EXECUTOR_RELEASE_POSTURES: frozenset[str] = frozenset(
    {posture.value for posture in ExecutorReleasePosture}
)
EXECUTOR_AUTH_MODES: frozenset[str] = frozenset(
    {auth_mode.value for auth_mode in ExecutorAuthMode}
)
EXECUTOR_AVAILABILITY_STATES: frozenset[str] = frozenset(
    {state.value for state in ExecutorAvailabilityState}
)
EXECUTOR_AUTH_STATES: frozenset[str] = frozenset(
    {state.value for state in ExecutorAuthState}
)
EXECUTOR_EVENT_TYPES: frozenset[str] = frozenset(
    {event_type.value for event_type in ExecutorEventType}
)
EXECUTOR_ESCALATION_KINDS: frozenset[str] = frozenset(
    {kind.value for kind in ExecutorEscalationKind}
)
DELEGATION_EVENT_TYPES: frozenset[str] = frozenset(
    {event_type.value for event_type in DelegationEventType}
)
DELEGATION_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        DelegationJobStatus.COMPLETED.value,
        DelegationJobStatus.FAILED.value,
        DelegationJobStatus.CANCELLED.value,
    }
)
DELEGATION_TERMINAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        DelegationEventType.COMPLETED.value,
        DelegationEventType.FAILED.value,
        DelegationEventType.CANCELLED.value,
    }
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
    "ToolTurnState",
    "LoopStopReason",
    "DelegationJobStatus",
    "DELEGATION_SUMMARY_OUTCOME_TYPE",
    "DelegationExecutorName",
    "ExecutorId",
    "ExecutorReleasePosture",
    "ExecutorAuthMode",
    "ExecutorAvailabilityState",
    "ExecutorAuthState",
    "ExecutorEventType",
    "ExecutorEscalationKind",
    "DelegationEventType",
    "ErrorCode",
    "EmbeddingLifecycleStatus",
    "ACCEPTANCE_STATUSES",
    "TASK_EVENT_TYPES",
    "TOOL_TURN_STATES",
    "LOOP_STOP_REASONS",
    "DELEGATION_JOB_STATUSES",
    "DELEGATION_EXECUTOR_NAMES",
    "EXECUTOR_IDS",
    "EXECUTOR_RELEASE_POSTURES",
    "EXECUTOR_AUTH_MODES",
    "EXECUTOR_AVAILABILITY_STATES",
    "EXECUTOR_AUTH_STATES",
    "EXECUTOR_EVENT_TYPES",
    "EXECUTOR_ESCALATION_KINDS",
    "DELEGATION_EVENT_TYPES",
    "DELEGATION_TERMINAL_STATUSES",
    "DELEGATION_TERMINAL_EVENT_TYPES",
    "ERROR_CODES",
    "EMBEDDING_LIFECYCLE_STATUSES",
]
