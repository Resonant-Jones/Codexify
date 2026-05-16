"""Runtime protocol tokens for core chat-loop contracts."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class AcceptanceStatus(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_DEGRADED = "accepted_degraded"


class ContextRequestStatus(str, Enum):
    ACCEPTED_NOT_EXECUTED = "accepted_not_executed"
    EXECUTED = "executed"
    NO_RESULTS = "no_results"
    FAILED = "failed"


class TaskEventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_EVENT = "task.event"
    TASK_WORKTREE_CREATED = "task.worktree_created"
    TASK_ATTEMPT_STARTED = "task.attempt_started"
    TASK_VALIDATION_STARTED = "task.validation_started"
    TASK_VALIDATION_FAILED = "task.validation_failed"
    TASK_VALIDATION_PASSED = "task.validation_passed"
    TASK_VALIDATION_RETRYING = "task.validation_retrying"
    TASK_RETRYING = "task.retrying"
    TASK_PATCH_ARTIFACT_CREATED = "task.patch_artifact_created"


class ToolTurnState(str, Enum):
    IDLE = "idle"
    DECISION_RECEIVED = "decision_received"
    COMMAND_DISPATCHED = "command_dispatched"
    RESULT_REINJECTED = "result_reinjected"
    COMPLETED = "completed"
    FAILED = "failed"
    LIMIT_REACHED = "limit_reached"


class LoopStopReason(str, Enum):
    MODEL_FINAL_ANSWER = "model_final_answer"
    TOOL_TURN_COMPLETED = "tool_turn_completed"
    TOOL_TURN_BLOCKED = "tool_turn_blocked"
    TOOL_TURN_FAILED = "tool_turn_failed"
    TOOL_TURN_MALFORMED = "tool_turn_malformed"
    TOOL_TURN_LIMIT_REACHED = "tool_turn_limit_reached"


class ToolLoopStopReason(str, Enum):
    PLAIN_ANSWER = "plain_answer"
    TOOL_TURN_COMPLETED = "tool_turn_completed"
    TOOL_DECISION_INVALID = "tool_decision_invalid"
    TOOL_COMMAND_FAILED = "tool_command_failed"
    TOOL_COMMAND_BLOCKED = "tool_command_blocked"
    TOOL_TURN_LIMIT_REACHED = "tool_turn_limit_reached"
    CANCELLED = "cancelled"


class TestResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    NOT_RUN = "not_run"


class DelegationJobStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PersonalFactStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    ARCHIVED = "archived"


class TraceSuppressionReason(str, Enum):
    ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN = (
        "assistant_vision_refusal_on_image_turn"
    )


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
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DIRTY_WORKTREE_PRECHECK_FAILED = "DIRTY_WORKTREE_PRECHECK_FAILED"
    MUTATION_SCOPE_VIOLATION = "MUTATION_SCOPE_VIOLATION"
    MUTATION_SCOPE_UNVERIFIED = "MUTATION_SCOPE_UNVERIFIED"
    CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED = (
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED"
    )
    CODING_ADAPTER_NOT_FOUND = "CODING_ADAPTER_NOT_FOUND"
    CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED = (
        "CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED"
    )
    CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING = "CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING"
    DELEGATION_EXECUTOR_UNSUPPORTED = "DELEGATION_EXECUTOR_UNSUPPORTED"
    DELEGATION_EXECUTOR_NOT_FOUND = "DELEGATION_EXECUTOR_NOT_FOUND"
    DELEGATION_EXECUTOR_TIMEOUT = "DELEGATION_EXECUTOR_TIMEOUT"
    DELEGATION_EXECUTOR_NONZERO_EXIT = "DELEGATION_EXECUTOR_NONZERO_EXIT"
    DELEGATION_EXECUTOR_SPAWN_FAILED = "DELEGATION_EXECUTOR_SPAWN_FAILED"
    WORKTREE_LEASE_REQUIRED = "WORKTREE_LEASE_REQUIRED"
    WORKTREE_LEASE_NOT_FOUND = "WORKTREE_LEASE_NOT_FOUND"
    WORKTREE_LEASE_NOT_ACTIVE = "WORKTREE_LEASE_NOT_ACTIVE"
    WORKTREE_LEASE_INVALID = "WORKTREE_LEASE_INVALID"
    WORKTREE_LEASE_PATH_UNAVAILABLE = "WORKTREE_LEASE_PATH_UNAVAILABLE"
    WORKTREE_LEASE_HEARTBEAT_FAILED = "WORKTREE_LEASE_HEARTBEAT_FAILED"
    WORKTREE_ISOLATION_UNAVAILABLE = "WORKTREE_ISOLATION_UNAVAILABLE"
    WORKTREE_CREATE_FAILED = "WORKTREE_CREATE_FAILED"
    WORKTREE_CLEANUP_FAILED = "WORKTREE_CLEANUP_FAILED"
    PATCH_ARTIFACT_GENERATION_FAILED = "PATCH_ARTIFACT_GENERATION_FAILED"
    PATCH_ARTIFACT_WRITE_FAILED = "PATCH_ARTIFACT_WRITE_FAILED"
    GIT_WORKTREE_REQUIRED = "GIT_WORKTREE_REQUIRED"
    GIT_WORKTREE_INVALID = "GIT_WORKTREE_INVALID"
    GIT_NO_CHANGES_TO_COMMIT = "GIT_NO_CHANGES_TO_COMMIT"
    GIT_COMMIT_FAILED = "GIT_COMMIT_FAILED"
    GIT_COMMIT_CREATED = "GIT_COMMIT_CREATED"
    WORK_ORDER_NOT_FOUND = "WORK_ORDER_NOT_FOUND"
    WORK_ORDER_INVALID = "WORK_ORDER_INVALID"
    WORK_ORDER_INVALID_STATUS = "WORK_ORDER_INVALID_STATUS"
    WORK_ORDER_INVALID_TRANSITION = "WORK_ORDER_INVALID_TRANSITION"
    CAMPAIGN_GOAL_NOT_FOUND = "CAMPAIGN_GOAL_NOT_FOUND"
    CAMPAIGN_GOAL_INVALID = "CAMPAIGN_GOAL_INVALID"
    CAMPAIGN_NOT_FOUND = "CAMPAIGN_NOT_FOUND"
    CAMPAIGN_INVALID = "CAMPAIGN_INVALID"
    CAMPAIGN_EXECUTION_ATTEMPT_INVALID = "CAMPAIGN_EXECUTION_ATTEMPT_INVALID"


class OrchestratorDecisionToken(str, Enum):
    RECOMMEND = "recommend"
    SKIP = "skip"
    BLOCKED = "blocked"
    RECOMMENDATION_ONLY = "recommendation_only"


class OrchestratorReasonCode(str, Enum):
    DEPENDENCY_NOT_SATISFIED = "DEPENDENCY_NOT_SATISFIED"
    ACTIVE_LEASE_CONFLICT = "ACTIVE_LEASE_CONFLICT"
    FILE_SCOPE_CONFLICT = "FILE_SCOPE_CONFLICT"
    STATUS_NOT_READY = "STATUS_NOT_READY"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    AMBIGUOUS_STATE = "AMBIGUOUS_STATE"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"


class EmbeddingLifecycleStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class CampaignGoalStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignExecutionAttemptStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TraceSnapshotAbsenceReason(str, Enum):
    TRACE_SOURCE_UNAVAILABLE = "trace_source_unavailable"
    TRACE_SNAPSHOT_MISSING = "trace_snapshot_missing"
    IMAGE_ROUTING_NOT_EVALUATED = "image_routing_not_evaluated"
    VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED = (
        "vision_model_selected_but_image_payload_not_routed"
    )
    LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL = (
        "local_model_substitution_selected_nonvision_model"
    )
    RETRIEVAL_NOT_EXECUTED = "retrieval_not_executed"
    RETRIEVAL_NO_CANDIDATES = "retrieval_no_candidates"


class ImageRoutingPath(str, Enum):
    NATIVE_MULTIMODAL_VISION = "native_multimodal_vision"
    INTERPRETER = "interpreter"


ACCEPTANCE_STATUSES: frozenset[str] = frozenset(
    {status.value for status in AcceptanceStatus}
)
CONTEXT_REQUEST_STATUSES: frozenset[str] = frozenset(
    {status.value for status in ContextRequestStatus}
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
TOOL_LOOP_STOP_REASONS: frozenset[str] = frozenset(
    {reason.value for reason in ToolLoopStopReason}
)
TEST_RESULT_STATUSES: frozenset[str] = frozenset(
    {status.value for status in TestResultStatus}
)
DELEGATION_JOB_STATUSES: frozenset[str] = frozenset(
    {status.value for status in DelegationJobStatus}
)
PERSONAL_FACT_STATUSES: frozenset[str] = frozenset(
    {status.value for status in PersonalFactStatus}
)
TRACE_SUPPRESSION_REASONS: frozenset[str] = frozenset(
    {reason.value for reason in TraceSuppressionReason}
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
ORCHESTRATOR_DECISION_TOKENS: frozenset[str] = frozenset(
    {token.value for token in OrchestratorDecisionToken}
)
ORCHESTRATOR_REASON_CODES: frozenset[str] = frozenset(
    {reason.value for reason in OrchestratorReasonCode}
)
EMBEDDING_LIFECYCLE_STATUSES: frozenset[str] = frozenset(
    {status.value for status in EmbeddingLifecycleStatus}
)
CAMPAIGN_GOAL_STATUSES: frozenset[str] = frozenset(
    {status.value for status in CampaignGoalStatus}
)
CAMPAIGN_STATUSES: frozenset[str] = frozenset(
    {status.value for status in CampaignStatus}
)
CAMPAIGN_EXECUTION_ATTEMPT_STATUSES: frozenset[str] = frozenset(
    {status.value for status in CampaignExecutionAttemptStatus}
)
TRACE_SNAPSHOT_ABSENCE_REASONS: frozenset[str] = frozenset(
    {reason.value for reason in TraceSnapshotAbsenceReason}
)
IMAGE_ROUTING_PATHS: frozenset[str] = frozenset(
    {path.value for path in ImageRoutingPath}
)

__all__ = [
    "AcceptanceStatus",
    "ContextRequestStatus",
    "TaskEventType",
    "ToolTurnState",
    "LoopStopReason",
    "ToolLoopStopReason",
    "TestResultStatus",
    "DelegationJobStatus",
    "PersonalFactStatus",
    "TraceSuppressionReason",
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
    "OrchestratorDecisionToken",
    "OrchestratorReasonCode",
    "EmbeddingLifecycleStatus",
    "CampaignGoalStatus",
    "CampaignStatus",
    "CampaignExecutionAttemptStatus",
    "ImageRoutingPath",
    "TraceSnapshotAbsenceReason",
    "ACCEPTANCE_STATUSES",
    "TASK_EVENT_TYPES",
    "TOOL_TURN_STATES",
    "LOOP_STOP_REASONS",
    "TOOL_LOOP_STOP_REASONS",
    "TEST_RESULT_STATUSES",
    "DELEGATION_JOB_STATUSES",
    "PERSONAL_FACT_STATUSES",
    "TRACE_SUPPRESSION_REASONS",
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
    "ORCHESTRATOR_DECISION_TOKENS",
    "ORCHESTRATOR_REASON_CODES",
    "EMBEDDING_LIFECYCLE_STATUSES",
    "CAMPAIGN_GOAL_STATUSES",
    "CAMPAIGN_STATUSES",
    "CAMPAIGN_EXECUTION_ATTEMPT_STATUSES",
    "CONTEXT_REQUEST_STATUSES",
    "IMAGE_ROUTING_PATHS",
    "TRACE_SNAPSHOT_ABSENCE_REASONS",
]
