"""Pure validation helpers for Pi invocation boundary contracts."""

from __future__ import annotations

from collections.abc import Mapping

from guardian.pi.contracts import (
    PiHarnessResult,
    PiInvocationEnvelope,
    PiInvocationReceipt,
    PiInvocationValidationResult,
)
from guardian.pi.tokens import (
    PI_PROVIDER_LANE_CLASSES,
    PiInvocationValidationOutcome,
    PiValidationFailureReason,
)

_REQUIRED_COMMAND_BUS_LINKAGE_KEYS = frozenset({"command_run_id", "source"})


def _fail(
    reason: PiValidationFailureReason, *, message: str
) -> PiInvocationValidationResult:
    return PiInvocationValidationResult(
        outcome=PiInvocationValidationOutcome.INVALID.value,
        failure_reason=reason.value,
        message=message,
    )


def _validate_command_bus_linkage(linkage: Mapping[str, object] | None) -> bool:
    if linkage is None:
        return True
    if not isinstance(linkage, Mapping):
        return False
    for key in _REQUIRED_COMMAND_BUS_LINKAGE_KEYS:
        value = str(linkage.get(key) or "").strip()
        if not value:
            return False
    return True


def validate_invocation_envelope(
    envelope: PiInvocationEnvelope,
) -> PiInvocationValidationResult:
    if not envelope.owner_account_id:
        return _fail(
            PiValidationFailureReason.MISSING_OWNER,
            message="owner_account_id is required",
        )
    if not envelope.source_thread_id or not envelope.source_message_id:
        return _fail(
            PiValidationFailureReason.MISSING_SOURCE_LINEAGE,
            message="source_thread_id and source_message_id are required",
        )
    if not envelope.invocation_id:
        return _fail(
            PiValidationFailureReason.MISSING_INVOCATION_ID,
            message="invocation_id is required",
        )
    if not envelope.harness_id:
        return _fail(
            PiValidationFailureReason.MISSING_HARNESS_ID,
            message="harness_id is required",
        )
    if envelope.provider_lane not in PI_PROVIDER_LANE_CLASSES:
        return _fail(
            PiValidationFailureReason.INVALID_PROVIDER_LANE,
            message="provider_lane is not an allowed Pi boundary lane",
        )
    minimax_meta = envelope.provider_lane_metadata.get("minimax")
    if isinstance(minimax_meta, Mapping) and bool(
        minimax_meta.get("requires_minimax")
    ):
        return _fail(
            PiValidationFailureReason.MINIMAX_METADATA_REQUIRES_PROVIDER,
            message="minimax metadata must be optional and non-authoritative",
        )
    if not set(envelope.granted_permissions).issubset(
        set(envelope.requested_permissions)
    ):
        return _fail(
            PiValidationFailureReason.PERMISSION_POSTURE_MISMATCH,
            message="granted_permissions must be a subset of requested_permissions",
        )
    if not _validate_command_bus_linkage(envelope.command_bus_linkage):
        return _fail(
            PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE,
            message="command_bus_linkage is malformed",
        )
    return PiInvocationValidationResult(
        outcome=PiInvocationValidationOutcome.VALID.value,
        metadata={"scope": "invocation_envelope"},
    )


def validate_receipt_against_envelope(
    envelope: PiInvocationEnvelope,
    receipt: PiInvocationReceipt,
) -> PiInvocationValidationResult:
    envelope_check = validate_invocation_envelope(envelope)
    if not envelope_check.ok:
        return envelope_check
    if receipt.owner_account_id != envelope.owner_account_id:
        return _fail(
            PiValidationFailureReason.OWNER_ACCOUNT_MISMATCH,
            message="receipt owner_account_id does not match envelope",
        )
    if receipt.invocation_id != envelope.invocation_id:
        return _fail(
            PiValidationFailureReason.RECEIPT_ENVELOPE_MISMATCH,
            message="receipt invocation_id does not match envelope",
        )
    if receipt.harness_id != envelope.harness_id:
        return _fail(
            PiValidationFailureReason.RECEIPT_ENVELOPE_MISMATCH,
            message="receipt harness_id does not match envelope",
        )
    if (
        envelope.execution_attempt_id
        and receipt.execution_attempt_id
        and (envelope.execution_attempt_id != receipt.execution_attempt_id)
    ):
        return _fail(
            PiValidationFailureReason.RECEIPT_ENVELOPE_MISMATCH,
            message="receipt execution_attempt_id does not match envelope",
        )
    if not set(receipt.granted_permissions).issubset(
        set(envelope.requested_permissions)
    ):
        return _fail(
            PiValidationFailureReason.PERMISSION_POSTURE_MISMATCH,
            message="receipt granted_permissions exceed envelope requested_permissions",
        )
    if not _validate_command_bus_linkage(receipt.command_bus_linkage):
        return _fail(
            PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE,
            message="receipt command_bus_linkage is malformed",
        )
    return PiInvocationValidationResult(
        outcome=PiInvocationValidationOutcome.VALID.value,
        metadata={"scope": "receipt"},
    )


def validate_harness_result_against_receipt(
    receipt: PiInvocationReceipt,
    result: PiHarnessResult,
) -> PiInvocationValidationResult:
    if result.owner_account_id != receipt.owner_account_id:
        return _fail(
            PiValidationFailureReason.OWNER_ACCOUNT_MISMATCH,
            message="result owner_account_id does not match receipt",
        )
    if result.invocation_id != receipt.invocation_id:
        return _fail(
            PiValidationFailureReason.RESULT_RECEIPT_MISMATCH,
            message="result invocation_id does not match receipt",
        )
    if result.receipt_id != receipt.receipt_id:
        return _fail(
            PiValidationFailureReason.RESULT_RECEIPT_MISMATCH,
            message="result receipt_id does not match receipt",
        )
    if not _validate_command_bus_linkage(result.command_bus_linkage):
        return _fail(
            PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE,
            message="result command_bus_linkage is malformed",
        )
    return PiInvocationValidationResult(
        outcome=PiInvocationValidationOutcome.VALID.value,
        metadata={"scope": "harness_result"},
    )


__all__ = [
    "validate_invocation_envelope",
    "validate_receipt_against_envelope",
    "validate_harness_result_against_receipt",
]
