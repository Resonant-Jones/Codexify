"""Canonical tokens for Pi invocation boundary contracts."""

from __future__ import annotations

from enum import Enum


class PiInvocationValidationOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class PiReceiptStatus(str, Enum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"


class PiHarnessResultClass(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNUSABLE = "unusable"


class PiProviderLaneClass(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class PiValidationFailureReason(str, Enum):
    MISSING_OWNER = "missing_owner"
    MISSING_SOURCE_LINEAGE = "missing_source_lineage"
    MISSING_INVOCATION_ID = "missing_invocation_id"
    INVOCATION_ID_MISMATCH = "invocation_id_mismatch"
    OWNER_ACCOUNT_MISMATCH = "owner_account_mismatch"
    MISSING_HARNESS_ID = "missing_harness_id"
    INVALID_PROVIDER_LANE = "invalid_provider_lane"
    MINIMAX_METADATA_REQUIRES_PROVIDER = "minimax_metadata_requires_provider"
    PERMISSION_POSTURE_MISMATCH = "permission_posture_mismatch"
    RECEIPT_ENVELOPE_MISMATCH = "receipt_envelope_mismatch"
    RESULT_RECEIPT_MISMATCH = "result_receipt_mismatch"
    MALFORMED_COMMAND_BUS_LINKAGE = "malformed_command_bus_linkage"


PI_INVOCATION_VALIDATION_OUTCOMES: frozenset[str] = frozenset(
    token.value for token in PiInvocationValidationOutcome
)
PI_RECEIPT_STATUSES: frozenset[str] = frozenset(
    token.value for token in PiReceiptStatus
)
PI_HARNESS_RESULT_CLASSES: frozenset[str] = frozenset(
    token.value for token in PiHarnessResultClass
)
PI_PROVIDER_LANE_CLASSES: frozenset[str] = frozenset(
    token.value for token in PiProviderLaneClass
)
PI_VALIDATION_FAILURE_REASONS: frozenset[str] = frozenset(
    token.value for token in PiValidationFailureReason
)


class PiTokenError(ValueError):
    """Raised when a caller supplies an invalid Pi boundary token."""


def _normalize_token(
    value: str | None, *, allowed: frozenset[str], kind: str
) -> str:
    token = str(value or "").strip()
    if token not in allowed:
        raise PiTokenError(f"Invalid {kind}: {value!r}")
    return token


def normalize_pi_validation_outcome(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=PI_INVOCATION_VALIDATION_OUTCOMES,
        kind="pi_validation_outcome",
    )


def normalize_pi_receipt_status(value: str | None) -> str:
    return _normalize_token(
        value, allowed=PI_RECEIPT_STATUSES, kind="pi_receipt_status"
    )


def normalize_pi_harness_result_class(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=PI_HARNESS_RESULT_CLASSES,
        kind="pi_harness_result_class",
    )


def normalize_pi_provider_lane_class(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=PI_PROVIDER_LANE_CLASSES,
        kind="pi_provider_lane_class",
    )


__all__ = [
    "PiInvocationValidationOutcome",
    "PiReceiptStatus",
    "PiHarnessResultClass",
    "PiProviderLaneClass",
    "PiValidationFailureReason",
    "PI_INVOCATION_VALIDATION_OUTCOMES",
    "PI_RECEIPT_STATUSES",
    "PI_HARNESS_RESULT_CLASSES",
    "PI_PROVIDER_LANE_CLASSES",
    "PI_VALIDATION_FAILURE_REASONS",
    "PiTokenError",
    "normalize_pi_validation_outcome",
    "normalize_pi_receipt_status",
    "normalize_pi_harness_result_class",
    "normalize_pi_provider_lane_class",
]
