from guardian.protocol_tokens import (
    ACCEPTANCE_STATUSES,
    ERROR_CODES,
    TASK_EVENT_TYPES,
    AcceptanceStatus,
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
    assert ERROR_CODES == {
        "QUEUE_ENQUEUE_FAILED",
        "CHAT_COMPLETE_ENQUEUE_FAILED",
        "TASK_EVENT_PUBLISH_FAILED",
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED",
    }
