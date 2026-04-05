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
    TASK_EVENT_TYPES,
    AcceptanceStatus,
    DelegationEventType,
    DelegationExecutorName,
    DelegationJobStatus,
    EmbeddingLifecycleStatus,
    ErrorCode,
    TaskEventType,
)


def test_acceptance_status_tokens() -> None:
    assert AcceptanceStatus.ACCEPTED.value == "accepted"
    assert AcceptanceStatus.ACCEPTED_DEGRADED.value == "accepted_degraded"
    assert ACCEPTANCE_STATUSES == {"accepted", "accepted_degraded"}


def test_task_event_tokens() -> None:
    assert TaskEventType.TASK_CREATED.value == "task.created"
    assert TaskEventType.TASK_CREATED.value in TASK_EVENT_TYPES


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
