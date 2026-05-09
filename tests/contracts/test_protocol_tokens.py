from guardian.pi.tokens import (
    PI_HARNESS_RESULT_CLASSES,
    PI_INVOCATION_ENVELOPE_STATUSES,
    PI_INVOCATION_RECEIPT_STATUSES,
    PI_INVOCATION_RECEIPT_TERMINAL_STATUSES,
    PI_INVOCATION_VALIDATION_OUTCOMES,
    PI_PROVIDER_LANE_CLASSES,
    PI_VALIDATION_FAILURE_REASONS,
    PiHarnessResultClass,
    PiInvocationEnvelopeStatus,
    PiInvocationReceiptStatus,
    PiInvocationValidationOutcome,
    PiProviderLaneClass,
    PiValidationFailureReason,
)
from guardian.protocol_tokens import (
    ACCEPTANCE_STATUSES,
    CONTEXT_REQUEST_STATUSES,
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
    IMAGE_ROUTING_PATHS,
    LOOP_STOP_REASONS,
    TASK_EVENT_TYPES,
    TEST_RESULT_STATUSES,
    TOOL_LOOP_STOP_REASONS,
    TOOL_TURN_STATES,
    TRACE_SNAPSHOT_ABSENCE_REASONS,
    TRACE_SUPPRESSION_REASONS,
    AcceptanceStatus,
    ContextRequestStatus,
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
    ImageRoutingPath,
    LoopStopReason,
    TaskEventType,
    TestResultStatus,
    ToolLoopStopReason,
    ToolTurnState,
    TraceSnapshotAbsenceReason,
    TraceSuppressionReason,
)


def test_acceptance_status_tokens() -> None:
    assert AcceptanceStatus.ACCEPTED.value == "accepted"
    assert AcceptanceStatus.ACCEPTED_DEGRADED.value == "accepted_degraded"
    assert ACCEPTANCE_STATUSES == {"accepted", "accepted_degraded"}


def test_context_request_status_tokens() -> None:
    assert ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value == (
        "accepted_not_executed"
    )
    assert ContextRequestStatus.EXECUTED.value == "executed"
    assert ContextRequestStatus.NO_RESULTS.value == "no_results"
    assert ContextRequestStatus.FAILED.value == "failed"
    assert CONTEXT_REQUEST_STATUSES == {
        "accepted_not_executed",
        "executed",
        "no_results",
        "failed",
    }


def test_task_event_tokens() -> None:
    assert TaskEventType.TASK_CREATED.value == "task.created"
    assert TaskEventType.TASK_CREATED.value in TASK_EVENT_TYPES
    assert TaskEventType.TASK_ATTEMPT_STARTED.value == "task.attempt_started"
    assert TaskEventType.TASK_VALIDATION_FAILED.value == (
        "task.validation_failed"
    )
    assert TaskEventType.TASK_RETRYING.value == "task.retrying"
    assert TASK_EVENT_TYPES.issuperset(
        {
            "task.created",
            "task.attempt_started",
            "task.validation_failed",
            "task.retrying",
        }
    )


def test_test_result_status_tokens() -> None:
    assert TestResultStatus.PASSED.value == "passed"
    assert TestResultStatus.FAILED.value == "failed"
    assert TestResultStatus.ERROR.value == "error"
    assert TestResultStatus.NOT_RUN.value == "not_run"
    assert TEST_RESULT_STATUSES == {
        "passed",
        "failed",
        "error",
        "not_run",
    }


def test_trace_suppression_tokens() -> None:
    assert (
        TraceSuppressionReason.ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN.value
        == "assistant_vision_refusal_on_image_turn"
    )
    assert TRACE_SUPPRESSION_REASONS == {
        "assistant_vision_refusal_on_image_turn",
    }


def test_trace_snapshot_absence_reason_tokens() -> None:
    assert TraceSnapshotAbsenceReason.TRACE_SOURCE_UNAVAILABLE.value == (
        "trace_source_unavailable"
    )
    assert TraceSnapshotAbsenceReason.TRACE_SNAPSHOT_MISSING.value == (
        "trace_snapshot_missing"
    )
    assert TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value == (
        "image_routing_not_evaluated"
    )
    assert (
        TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value
        == "vision_model_selected_but_image_payload_not_routed"
    )
    assert (
        TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
        == "local_model_substitution_selected_nonvision_model"
    )
    assert TraceSnapshotAbsenceReason.RETRIEVAL_NOT_EXECUTED.value == (
        "retrieval_not_executed"
    )
    assert TraceSnapshotAbsenceReason.RETRIEVAL_NO_CANDIDATES.value == (
        "retrieval_no_candidates"
    )
    assert TRACE_SNAPSHOT_ABSENCE_REASONS == {
        "trace_source_unavailable",
        "trace_snapshot_missing",
        "image_routing_not_evaluated",
        "vision_model_selected_but_image_payload_not_routed",
        "local_model_substitution_selected_nonvision_model",
        "retrieval_not_executed",
        "retrieval_no_candidates",
    }


def test_image_routing_protocol_tokens() -> None:
    assert ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value == (
        "native_multimodal_vision"
    )
    assert ImageRoutingPath.INTERPRETER.value == "interpreter"
    assert IMAGE_ROUTING_PATHS == {
        "native_multimodal_vision",
        "interpreter",
    }


def test_tool_turn_protocol_tokens() -> None:
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


def test_pi_invocation_boundary_tokens() -> None:
    assert PiInvocationEnvelopeStatus.PREPARED.value == "prepared"
    assert PiInvocationEnvelopeStatus.VALIDATED.value == "validated"
    assert PiInvocationEnvelopeStatus.REJECTED.value == "rejected"
    assert PI_INVOCATION_ENVELOPE_STATUSES == {
        "prepared",
        "validated",
        "rejected",
    }

    assert PiInvocationReceiptStatus.ISSUED.value == "issued"
    assert PiInvocationReceiptStatus.ACCEPTED.value == "accepted"
    assert PiInvocationReceiptStatus.COMPLETED.value == "completed"
    assert PiInvocationReceiptStatus.FAILED.value == "failed"
    assert PiInvocationReceiptStatus.REJECTED.value == "rejected"
    assert PI_INVOCATION_RECEIPT_STATUSES == {
        "issued",
        "accepted",
        "completed",
        "failed",
        "rejected",
    }
    assert PI_INVOCATION_RECEIPT_TERMINAL_STATUSES == {
        "completed",
        "failed",
        "rejected",
    }

    assert PiHarnessResultClass.SUCCESS.value == "success"
    assert PiHarnessResultClass.FAILURE.value == "failure"
    assert PiHarnessResultClass.BLOCKED.value == "blocked"
    assert PI_HARNESS_RESULT_CLASSES == {"success", "failure", "blocked"}

    assert PiProviderLaneClass.LOCAL.value == "local"
    assert PiProviderLaneClass.EXTERNAL.value == "external"
    assert PiProviderLaneClass.MINIMAX.value == "minimax"
    assert PI_PROVIDER_LANE_CLASSES == {"local", "external", "minimax"}

    assert PiInvocationValidationOutcome.VALID.value == "valid"
    assert PiInvocationValidationOutcome.FAILED_CLOSED.value == "failed_closed"
    assert PI_INVOCATION_VALIDATION_OUTCOMES == {"valid", "failed_closed"}

    assert PiValidationFailureReason.MISSING_OWNER_ACCOUNT_IDENTITY.value == (
        "missing_owner_account_identity"
    )
    assert PiValidationFailureReason.OWNER_ACCOUNT_MISMATCH.value == (
        "owner_account_mismatch"
    )
    assert PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH.value == (
        "guardian_ownership_mismatch"
    )
    assert PiValidationFailureReason.MISSING_SOURCE_LINEAGE.value == (
        "missing_source_lineage"
    )
    assert PiValidationFailureReason.MISSING_INVOCATION_ID.value == (
        "missing_invocation_id"
    )
    assert PiValidationFailureReason.INCONSISTENT_INVOCATION_ID.value == (
        "inconsistent_invocation_id"
    )
    assert PiValidationFailureReason.MISSING_HARNESS_ID.value == (
        "missing_harness_id"
    )
    assert PiValidationFailureReason.MISSING_HARNESS_VERSION.value == (
        "missing_harness_version"
    )
    assert PiValidationFailureReason.INVALID_ENVELOPE_STATUS.value == (
        "invalid_envelope_status"
    )
    assert PiValidationFailureReason.INVALID_RECEIPT_STATUS.value == (
        "invalid_receipt_status"
    )
    assert PiValidationFailureReason.INVALID_HARNESS_RESULT_CLASS.value == (
        "invalid_harness_result_class"
    )
    assert PiValidationFailureReason.INVALID_PROVIDER_LANE.value == (
        "invalid_provider_lane"
    )
    assert PiValidationFailureReason.MINIMAX_METADATA_REQUIRED.value == (
        "minimax_metadata_required"
    )
    assert PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT.value == (
        "permission_posture_inconsistent"
    )
    assert (
        PiValidationFailureReason.RECEIPT_MISMATCH.value == "receipt_mismatch"
    )
    assert PiValidationFailureReason.HARNESS_RESULT_MISMATCH.value == (
        "harness_result_mismatch"
    )
    assert (
        PiValidationFailureReason.MISSING_RECEIPT_ID.value
        == "missing_receipt_id"
    )
    assert PiValidationFailureReason.MISSING_HARNESS_RESULT_ID.value == (
        "missing_harness_result_id"
    )
    assert PiValidationFailureReason.MISSING_ARTIFACT_REFERENCE.value == (
        "missing_artifact_reference"
    )
    assert PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE.value == (
        "malformed_command_bus_linkage"
    )
    assert PI_VALIDATION_FAILURE_REASONS == {
        "missing_owner_account_identity",
        "owner_account_mismatch",
        "guardian_ownership_mismatch",
        "missing_source_lineage",
        "missing_invocation_id",
        "inconsistent_invocation_id",
        "missing_harness_id",
        "missing_harness_version",
        "invalid_envelope_status",
        "invalid_receipt_status",
        "invalid_harness_result_class",
        "invalid_provider_lane",
        "minimax_metadata_required",
        "permission_posture_inconsistent",
        "receipt_mismatch",
        "result_receipt_mismatch",
        "harness_result_mismatch",
        "missing_receipt_id",
        "missing_harness_result_id",
        "missing_artifact_reference",
        "malformed_command_bus_linkage",
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
    assert ErrorCode.VALIDATION_FAILED.value == "VALIDATION_FAILED"
    assert (
        ErrorCode.TASK_EVENT_PUBLISH_FAILED.value == "TASK_EVENT_PUBLISH_FAILED"
    )
    assert (
        ErrorCode.CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED.value
        == "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED"
    )
    assert (
        ErrorCode.CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED.value
        == "CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED"
    )
    assert (
        ErrorCode.CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING.value
        == "CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING"
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
        "VALIDATION_FAILED",
        "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED",
        "CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED",
        "CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING",
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


def test_legacy_loop_stop_tokens() -> None:
    assert LoopStopReason.MODEL_FINAL_ANSWER.value == "model_final_answer"
    assert LoopStopReason.TOOL_TURN_COMPLETED.value == "tool_turn_completed"
    assert LoopStopReason.TOOL_TURN_BLOCKED.value == "tool_turn_blocked"
    assert LoopStopReason.TOOL_TURN_FAILED.value == "tool_turn_failed"
    assert LoopStopReason.TOOL_TURN_MALFORMED.value == "tool_turn_malformed"
    assert (
        LoopStopReason.TOOL_TURN_LIMIT_REACHED.value
        == "tool_turn_limit_reached"
    )
    assert LOOP_STOP_REASONS == {
        "model_final_answer",
        "tool_turn_completed",
        "tool_turn_blocked",
        "tool_turn_failed",
        "tool_turn_malformed",
        "tool_turn_limit_reached",
    }
