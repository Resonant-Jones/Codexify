from guardian.protocol_tokens import (
    ACCEPTANCE_STATUSES,
    DELEGATION_EVENT_TYPES,
    DELEGATION_EXECUTOR_NAMES,
    DELEGATION_JOB_STATUSES,
    DELEGATION_SUMMARY_OUTCOME_TYPE,
    DELEGATION_TERMINAL_EVENT_TYPES,
    DELEGATION_TERMINAL_STATUSES,
    EMBEDDING_LIFECYCLE_STATUSES,
    ERROR_CODES,
    EXECUTOR_AUTH_MODES,
    EXECUTOR_AUTH_STATES,
    EXECUTOR_AVAILABILITY_STATES,
    EXECUTOR_ESCALATION_KINDS,
    EXECUTOR_EVENT_TYPES,
    EXECUTOR_IDS,
    EXECUTOR_RELEASE_POSTURES,
    TASK_EVENT_TYPES,
    TOOL_LOOP_STOP_REASONS,
    TOOL_TURN_STATES,
    AcceptanceStatus,
    DelegationEventType,
    DelegationExecutorName,
    DelegationJobStatus,
    EmbeddingLifecycleStatus,
    ErrorCode,
    ExecutorAuthMode,
    ExecutorAuthState,
    ExecutorAvailabilityState,
    ExecutorEscalationKind,
    ExecutorEventType,
    ExecutorId,
    ExecutorReleasePosture,
    TaskEventType,
    ToolLoopStopReason,
    ToolTurnState,
)


def test_acceptance_status_tokens() -> None:
    assert AcceptanceStatus.ACCEPTED.value == "accepted"
    assert AcceptanceStatus.ACCEPTED_DEGRADED.value == "accepted_degraded"
    assert ACCEPTANCE_STATUSES == {"accepted", "accepted_degraded"}


def test_task_event_tokens() -> None:
    assert TaskEventType.TASK_CREATED.value == "task.created"
    assert TaskEventType.TASK_CREATED.value in TASK_EVENT_TYPES


def test_tool_loop_tokens() -> None:
    assert ToolTurnState.IDLE.value == "idle"
    assert ToolTurnState.DECISION_RECEIVED.value == "decision_received"
    assert ToolTurnState.COMMAND_DISPATCHED.value == "command_dispatched"
    assert ToolTurnState.RESULT_REINJECTED.value == "result_reinjected"
    assert ToolTurnState.COMPLETED.value == "completed"
    assert ToolTurnState.FAILED.value == "failed"
    assert ToolTurnState.LIMIT_REACHED.value == "limit_reached"
    assert TOOL_TURN_STATES == {
        "idle",
        "decision_received",
        "command_dispatched",
        "result_reinjected",
        "completed",
        "failed",
        "limit_reached",
    }

    assert ToolLoopStopReason.PLAIN_ANSWER.value == "plain_answer"
    assert ToolLoopStopReason.TOOL_TURN_COMPLETED.value == "tool_turn_completed"
    assert (
        ToolLoopStopReason.TOOL_DECISION_INVALID.value
        == "tool_decision_invalid"
    )
    assert ToolLoopStopReason.TOOL_COMMAND_FAILED.value == "tool_command_failed"
    assert (
        ToolLoopStopReason.TOOL_COMMAND_BLOCKED.value == "tool_command_blocked"
    )
    assert (
        ToolLoopStopReason.TOOL_TURN_LIMIT_REACHED.value
        == "tool_turn_limit_reached"
    )
    assert ToolLoopStopReason.CANCELLED.value == "cancelled"
    assert TOOL_LOOP_STOP_REASONS == {
        "plain_answer",
        "tool_turn_completed",
        "tool_decision_invalid",
        "tool_command_failed",
        "tool_command_blocked",
        "tool_turn_limit_reached",
        "cancelled",
    }


def test_delegation_status_tokens() -> None:
    assert DelegationJobStatus.DRAFT.value == "draft"
    assert DelegationJobStatus.APPROVED.value == "approved"
    assert DelegationJobStatus.QUEUED.value == "queued"
    assert DelegationJobStatus.RUNNING.value == "running"
    assert DelegationJobStatus.COMPLETED.value == "completed"
    assert DelegationJobStatus.FAILED.value == "failed"
    assert DelegationJobStatus.CANCELLED.value == "cancelled"
    assert DELEGATION_JOB_STATUSES == {
        "draft",
        "approved",
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
    }
    assert DELEGATION_TERMINAL_STATUSES == {
        "completed",
        "failed",
        "cancelled",
    }


def test_delegation_executor_tokens() -> None:
    assert DelegationExecutorName.CODEX.value == "codex"
    assert DELEGATION_EXECUTOR_NAMES == {"codex"}


def test_executor_protocol_tokens() -> None:
    assert ExecutorId.CODEX.value == "codex"
    assert ExecutorId.CLAUDE_CODE.value == "claude_code"
    assert ExecutorId.OPENCODE.value == "opencode"
    assert EXECUTOR_IDS == {"codex", "claude_code", "opencode"}

    assert ExecutorReleasePosture.OFFICIAL.value == "official"
    assert ExecutorReleasePosture.OPTIONAL.value == "optional"
    assert ExecutorReleasePosture.USER_CONFIGURED.value == "user_configured"
    assert EXECUTOR_RELEASE_POSTURES == {
        "official",
        "optional",
        "user_configured",
    }

    assert ExecutorAuthMode.DIRECT_PROVIDER.value == "direct_provider"
    assert ExecutorAuthMode.LOCAL_MODEL.value == "local_model"
    assert ExecutorAuthMode.GATEWAY_BASE_URL.value == "gateway_base_url"
    assert EXECUTOR_AUTH_MODES == {
        "direct_provider",
        "local_model",
        "gateway_base_url",
    }

    assert ExecutorAvailabilityState.READY.value == "ready"
    assert ExecutorAvailabilityState.DEGRADED.value == "degraded"
    assert ExecutorAvailabilityState.UNAVAILABLE.value == "unavailable"
    assert ExecutorAvailabilityState.NOT_INSTALLED.value == "not_installed"
    assert EXECUTOR_AVAILABILITY_STATES == {
        "ready",
        "degraded",
        "unavailable",
        "not_installed",
    }

    assert ExecutorAuthState.AUTHENTICATED.value == "authenticated"
    assert ExecutorAuthState.UNAUTHENTICATED.value == "unauthenticated"
    assert ExecutorAuthState.UNKNOWN.value == "unknown"
    assert EXECUTOR_AUTH_STATES == {
        "authenticated",
        "unauthenticated",
        "unknown",
    }

    assert ExecutorEventType.PROGRESS.value == "executor.progress"
    assert ExecutorEventType.ESCALATION.value == "executor.escalation"
    assert ExecutorEventType.COMPLETED.value == "executor.completed"
    assert ExecutorEventType.FAILED.value == "executor.failed"
    assert ExecutorEventType.CANCELLED.value == "executor.cancelled"
    assert EXECUTOR_EVENT_TYPES == {
        "executor.progress",
        "executor.escalation",
        "executor.completed",
        "executor.failed",
        "executor.cancelled",
    }

    assert (
        ExecutorEscalationKind.NEEDS_CLARIFICATION.value
        == "needs_clarification"
    )
    assert ExecutorEscalationKind.NEEDS_PERMISSION.value == "needs_permission"
    assert ExecutorEscalationKind.BLOCKED.value == "blocked"
    assert ExecutorEscalationKind.NEEDS_REVIEW.value == "needs_review"
    assert ExecutorEscalationKind.TOOLING_LIMIT.value == "tooling_limit"
    assert EXECUTOR_ESCALATION_KINDS == {
        "needs_clarification",
        "needs_permission",
        "blocked",
        "needs_review",
        "tooling_limit",
    }

    assert ExecutorAuthMode.DIRECT_PROVIDER.value == "direct_provider"
    assert ExecutorAuthMode.LOCAL_MODEL.value == "local_model"
    assert ExecutorAuthMode.GATEWAY_BASE_URL.value == "gateway_base_url"
    assert EXECUTOR_AUTH_MODES == {
        "direct_provider",
        "local_model",
        "gateway_base_url",
    }

    assert ExecutorEventType.PROGRESS.value == "executor.progress"
    assert ExecutorEventType.ESCALATION.value == "executor.escalation"
    assert ExecutorEventType.COMPLETED.value == "executor.completed"
    assert ExecutorEventType.FAILED.value == "executor.failed"
    assert ExecutorEventType.CANCELLED.value == "executor.cancelled"
    assert EXECUTOR_EVENT_TYPES == {
        "executor.progress",
        "executor.escalation",
        "executor.completed",
        "executor.failed",
        "executor.cancelled",
    }

    assert (
        ExecutorEscalationKind.NEEDS_CLARIFICATION.value
        == "needs_clarification"
    )
    assert ExecutorEscalationKind.NEEDS_PERMISSION.value == "needs_permission"
    assert ExecutorEscalationKind.BLOCKED.value == "blocked"
    assert ExecutorEscalationKind.NEEDS_REVIEW.value == "needs_review"
    assert ExecutorEscalationKind.TOOLING_LIMIT.value == "tooling_limit"
    assert EXECUTOR_ESCALATION_KINDS == {
        "needs_clarification",
        "needs_permission",
        "blocked",
        "needs_review",
        "tooling_limit",
    }


def test_delegation_event_tokens() -> None:
    assert DelegationEventType.CREATED.value == "delegation.created"
    assert DelegationEventType.RUNNING.value == "delegation.running"
    assert DelegationEventType.PROGRESS.value == "delegation.progress"
    assert DelegationEventType.COMPLETED.value == "delegation.completed"
    assert DelegationEventType.FAILED.value == "delegation.failed"
    assert DelegationEventType.CANCELLED.value == "delegation.cancelled"
    assert DelegationEventType.CREATED.value in DELEGATION_EVENT_TYPES
    assert DELEGATION_TERMINAL_EVENT_TYPES == {
        "delegation.completed",
        "delegation.failed",
        "delegation.cancelled",
    }


def test_error_code_tokens() -> None:
    assert ErrorCode.QUEUE_ENQUEUE_FAILED.value == "QUEUE_ENQUEUE_FAILED"
    assert (
        ErrorCode.CHAT_COMPLETE_ENQUEUE_FAILED.value
        == "CHAT_COMPLETE_ENQUEUE_FAILED"
    )
    assert (
        ErrorCode.TASK_EVENT_PUBLISH_FAILED.value == "TASK_EVENT_PUBLISH_FAILED"
    )
    assert (
        ErrorCode.CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED.value
        == "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED"
    )
    assert (
        ErrorCode.DELEGATION_EXECUTOR_UNSUPPORTED.value
        == "DELEGATION_EXECUTOR_UNSUPPORTED"
    )
    assert (
        ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
        == "DELEGATION_EXECUTOR_NOT_FOUND"
    )
    assert (
        ErrorCode.DELEGATION_EXECUTOR_TIMEOUT.value
        == "DELEGATION_EXECUTOR_TIMEOUT"
    )
    assert (
        ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value
        == "DELEGATION_EXECUTOR_NONZERO_EXIT"
    )
    assert (
        ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value
        == "DELEGATION_EXECUTOR_SPAWN_FAILED"
    )
    assert ERROR_CODES == {
        "QUEUE_ENQUEUE_FAILED",
        "CHAT_COMPLETE_ENQUEUE_FAILED",
        "TASK_EVENT_PUBLISH_FAILED",
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED",
        "DELEGATION_EXECUTOR_UNSUPPORTED",
        "DELEGATION_EXECUTOR_NOT_FOUND",
        "DELEGATION_EXECUTOR_TIMEOUT",
        "DELEGATION_EXECUTOR_NONZERO_EXIT",
        "DELEGATION_EXECUTOR_SPAWN_FAILED",
    }


def test_delegation_summary_outcome_token() -> None:
    assert DELEGATION_SUMMARY_OUTCOME_TYPE == "task_summary"


def test_embedding_lifecycle_tokens() -> None:
    assert EmbeddingLifecycleStatus.PENDING.value == "pending"
    assert EmbeddingLifecycleStatus.PROCESSING.value == "processing"
    assert EmbeddingLifecycleStatus.READY.value == "ready"
    assert EmbeddingLifecycleStatus.FAILED.value == "failed"
    assert EMBEDDING_LIFECYCLE_STATUSES == {
        "pending",
        "processing",
        "ready",
        "failed",
    }
