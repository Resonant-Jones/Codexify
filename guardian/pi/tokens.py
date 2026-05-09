"""Canonical tokens for the Pi invocation boundary contract."""

from __future__ import annotations

from enum import Enum


class PiInvocationEnvelopeStatus(str, Enum):
    PREPARED = "prepared"
    VALIDATED = "validated"
    REJECTED = "rejected"


class PiInvocationReceiptStatus(str, Enum):
    ISSUED = "issued"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class PiHarnessResultClass(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"


class PiProviderLaneClass(str, Enum):
    LOCAL = "local"
    EXTERNAL = "external"
    MINIMAX = "minimax"


class PiInvocationValidationOutcome(str, Enum):
    VALID = "valid"
    FAILED_CLOSED = "failed_closed"


class PiValidationFailureReason(str, Enum):
    MISSING_OWNER_ACCOUNT_IDENTITY = "missing_owner_account_identity"
    OWNER_ACCOUNT_MISMATCH = "owner_account_mismatch"
    GUARDIAN_OWNERSHIP_MISMATCH = "guardian_ownership_mismatch"
    MISSING_SOURCE_LINEAGE = "missing_source_lineage"
    MISSING_INVOCATION_ID = "missing_invocation_id"
    INCONSISTENT_INVOCATION_ID = "inconsistent_invocation_id"
    MISSING_HARNESS_ID = "missing_harness_id"
    MISSING_HARNESS_VERSION = "missing_harness_version"
    INVALID_ENVELOPE_STATUS = "invalid_envelope_status"
    INVALID_RECEIPT_STATUS = "invalid_receipt_status"
    INVALID_HARNESS_RESULT_CLASS = "invalid_harness_result_class"
    INVALID_PROVIDER_LANE = "invalid_provider_lane"
    MINIMAX_METADATA_REQUIRED = "minimax_metadata_required"
    PERMISSION_POSTURE_INCONSISTENT = "permission_posture_inconsistent"
    RECEIPT_MISMATCH = "receipt_mismatch"
    HARNESS_RESULT_MISMATCH = "harness_result_mismatch"
    MISSING_RECEIPT_ID = "missing_receipt_id"
    MISSING_HARNESS_RESULT_ID = "missing_harness_result_id"
    MISSING_ARTIFACT_REFERENCE = "missing_artifact_reference"
    MALFORMED_COMMAND_BUS_LINKAGE = "malformed_command_bus_linkage"


PI_INVOCATION_ENVELOPE_STATUSES: frozenset[str] = frozenset(
    status.value for status in PiInvocationEnvelopeStatus
)
PI_INVOCATION_RECEIPT_STATUSES: frozenset[str] = frozenset(
    status.value for status in PiInvocationReceiptStatus
)
PI_INVOCATION_RECEIPT_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        PiInvocationReceiptStatus.COMPLETED.value,
        PiInvocationReceiptStatus.FAILED.value,
        PiInvocationReceiptStatus.REJECTED.value,
    }
)
PI_HARNESS_RESULT_CLASSES: frozenset[str] = frozenset(
    result_class.value for result_class in PiHarnessResultClass
)
PI_PROVIDER_LANE_CLASSES: frozenset[str] = frozenset(
    lane_class.value for lane_class in PiProviderLaneClass
)
PI_INVOCATION_VALIDATION_OUTCOMES: frozenset[str] = frozenset(
    outcome.value for outcome in PiInvocationValidationOutcome
)
PI_VALIDATION_FAILURE_REASONS: frozenset[str] = frozenset(
    reason.value for reason in PiValidationFailureReason
)
