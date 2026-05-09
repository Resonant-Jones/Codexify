"""Pure validation helpers for the Pi invocation boundary."""

from __future__ import annotations

import json
from typing import Any, Mapping

from guardian.pi.contracts import (
    PiCommandBusLinkage,
    PiGuardianBoundary,
    PiHarnessResult,
    PiInvocationEnvelope,
    PiInvocationReceipt,
    PiInvocationValidationResult,
    PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.tokens import (
    PI_HARNESS_RESULT_CLASSES,
    PI_INVOCATION_ENVELOPE_STATUSES,
    PI_INVOCATION_RECEIPT_STATUSES,
    PI_INVOCATION_RECEIPT_TERMINAL_STATUSES,
    PI_PROVIDER_LANE_CLASSES,
    PiHarnessResultClass,
    PiInvocationValidationOutcome,
    PiValidationFailureReason,
)

_REQUIRED_COMMAND_BUS_LINKAGE_KEYS = frozenset({"command_run_id", "source"})
GUARDIAN_OWNERSHIP_LABEL = "guardian"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    )


def _permission_signature(permission: PiPermissionGrant) -> str:
    return _canonical_json(permission.to_payload())


def _permission_signatures(
    permissions: tuple[PiPermissionGrant, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(_permission_signature(permission) for permission in permissions)
    )


def _invalid_reason(value: PiValidationFailureReason) -> str:
    return value.value


def _result(
    *, reasons: list[str], metadata: dict[str, Any]
) -> PiInvocationValidationResult:
    outcome = (
        PiInvocationValidationOutcome.VALID.value
        if not reasons
        else PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    metadata = dict(metadata)
    metadata["failure_count"] = len(reasons)
    metadata["failure_reasons"] = list(sorted(set(reasons)))
    return PiInvocationValidationResult(
        validation_outcome=outcome,
        failure_reasons=tuple(sorted(set(reasons))),
        validation_metadata=metadata,
    )


def _fail(
    reason: PiValidationFailureReason, *, message: str
) -> PiInvocationValidationResult:
    return PiInvocationValidationResult(
        outcome=PiInvocationValidationOutcome.FAILED_CLOSED.value,
        failure_reason=reason.value,
        message=message,
    )


def _validate_guardian_boundary(
    boundary: PiGuardianBoundary,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    metadata = {
        "owner_account_id": boundary.owner_account_id,
        "ownership_labels": {
            "request_policy_owner": boundary.request_policy_owner,
            "transcript_lineage_owner": boundary.transcript_lineage_owner,
            "provenance_owner": boundary.provenance_owner,
            "command_authority_owner": boundary.command_authority_owner,
            "result_return_owner": boundary.result_return_owner,
        },
    }
    if not boundary.owner_account_id:
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.MISSING_OWNER_ACCOUNT_IDENTITY
            )
        )
    if (
        boundary.request_policy_owner != GUARDIAN_OWNERSHIP_LABEL
        or boundary.transcript_lineage_owner != GUARDIAN_OWNERSHIP_LABEL
        or boundary.provenance_owner != GUARDIAN_OWNERSHIP_LABEL
        or boundary.command_authority_owner != GUARDIAN_OWNERSHIP_LABEL
        or boundary.result_return_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )
    return reasons, metadata


def _validate_provider_lane(
    provider_lane: PiProviderLane,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    metadata = provider_lane.to_payload()
    if provider_lane.provider_lane_class not in PI_PROVIDER_LANE_CLASSES:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.INVALID_PROVIDER_LANE)
        )
    if _metadata_requires_minimax(provider_lane.metadata):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MINIMAX_METADATA_REQUIRED)
        )
    return reasons, metadata


def _metadata_requires_minimax(metadata: Mapping[str, Any]) -> bool:
    if metadata.get("requires_minimax") is True:
        return True
    if metadata.get("minimax_required") is True:
        return True
    minimax = metadata.get("minimax")
    if isinstance(minimax, Mapping):
        if minimax.get("requires_minimax") is True:
            return True
        if minimax.get("required") is True:
            return True
    return False


def _validate_permission_posture(
    *,
    requested_permissions: tuple[PiPermissionGrant, ...],
    granted_permissions: tuple[PiPermissionGrant, ...],
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    requested_signatures = _permission_signatures(requested_permissions)
    granted_signatures = _permission_signatures(granted_permissions)

    if any(not permission.permission for permission in requested_permissions):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT
            )
        )
    if any(not permission.permission for permission in granted_permissions):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT
            )
        )
    if any(
        signature not in requested_signatures
        for signature in granted_signatures
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT
            )
        )

    metadata = {
        "requested_permissions": [
            permission.to_payload() for permission in requested_permissions
        ],
        "granted_permissions": [
            permission.to_payload() for permission in granted_permissions
        ],
        "requested_permission_signatures": list(requested_signatures),
        "granted_permission_signatures": list(granted_signatures),
    }
    return reasons, metadata


def _validate_command_bus_linkage(
    command_bus_linkage: PiCommandBusLinkage | None,
) -> tuple[list[str], dict[str, Any]]:
    metadata = {
        "present": command_bus_linkage is not None,
        "command_bus_linkage": (
            command_bus_linkage.to_payload()
            if command_bus_linkage is not None
            else None
        ),
    }
    if command_bus_linkage is None:
        return [], metadata
    if not command_bus_linkage.command_run_id:
        return [
            _invalid_reason(
                PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE
            )
        ], metadata
    return [], metadata


def _validate_envelope_core(
    envelope: PiInvocationEnvelope,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    guardian_reasons, guardian_metadata = _validate_guardian_boundary(
        envelope.guardian_boundary
    )
    reasons.extend(guardian_reasons)

    if not envelope.source_thread_id or not envelope.source_message_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_SOURCE_LINEAGE)
        )
    if not envelope.invocation_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_INVOCATION_ID)
        )
    if not envelope.harness_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_ID)
        )
    if not envelope.harness_version:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_VERSION)
        )
    if envelope.status not in PI_INVOCATION_ENVELOPE_STATUSES:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.INVALID_ENVELOPE_STATUS)
        )

    provider_lane_reasons, provider_lane_metadata = _validate_provider_lane(
        envelope.provider_lane
    )
    reasons.extend(provider_lane_reasons)

    permission_reasons, permission_metadata = _validate_permission_posture(
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
    )
    reasons.extend(permission_reasons)

    linkage_reasons, linkage_metadata = _validate_command_bus_linkage(
        envelope.command_bus_linkage
    )
    reasons.extend(linkage_reasons)

    metadata = {
        "validator": "invocation_envelope",
        "guardian_boundary": guardian_metadata,
        "source_lineage": {
            "source_thread_id": envelope.source_thread_id,
            "source_message_id": envelope.source_message_id,
            "authored_request_id": envelope.authored_request_id,
            "attempt_id": envelope.attempt_id,
        },
        "invocation_id": envelope.invocation_id,
        "harness_id": envelope.harness_id,
        "harness_version": envelope.harness_version,
        "status": envelope.status,
        "provider_lane": provider_lane_metadata,
        "permission_posture": permission_metadata,
        "command_bus_linkage": linkage_metadata,
    }
    return reasons, metadata


def _validate_receipt_core(
    receipt: PiInvocationReceipt,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    guardian_reasons, guardian_metadata = _validate_guardian_boundary(
        receipt.guardian_boundary
    )
    reasons.extend(guardian_reasons)

    if not receipt.receipt_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_RECEIPT_ID)
        )
    if not receipt.source_thread_id or not receipt.source_message_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_SOURCE_LINEAGE)
        )
    if not receipt.invocation_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_INVOCATION_ID)
        )
    if not receipt.harness_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_ID)
        )
    if not receipt.harness_version:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_VERSION)
        )
    if receipt.receipt_status not in PI_INVOCATION_RECEIPT_STATUSES:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.INVALID_RECEIPT_STATUS)
        )

    provider_lane_reasons, provider_lane_metadata = _validate_provider_lane(
        receipt.provider_lane
    )
    reasons.extend(provider_lane_reasons)

    permission_reasons, permission_metadata = _validate_permission_posture(
        requested_permissions=receipt.requested_permissions,
        granted_permissions=receipt.granted_permissions,
    )
    reasons.extend(permission_reasons)

    linkage_reasons, linkage_metadata = _validate_command_bus_linkage(
        receipt.command_bus_linkage
    )
    reasons.extend(linkage_reasons)

    metadata = {
        "validator": "invocation_receipt",
        "guardian_boundary": guardian_metadata,
        "receipt_id": receipt.receipt_id,
        "source_lineage": {
            "source_thread_id": receipt.source_thread_id,
            "source_message_id": receipt.source_message_id,
            "authored_request_id": receipt.authored_request_id,
            "attempt_id": receipt.attempt_id,
        },
        "invocation_id": receipt.invocation_id,
        "harness_id": receipt.harness_id,
        "harness_version": receipt.harness_version,
        "receipt_status": receipt.receipt_status,
        "provider_lane": provider_lane_metadata,
        "permission_posture": permission_metadata,
        "command_bus_linkage": linkage_metadata,
        "result_artifact_ref": receipt.result_artifact_ref,
    }
    return reasons, metadata


def _validate_harness_result_core(
    harness_result: PiHarnessResult,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    guardian_reasons, guardian_metadata = _validate_guardian_boundary(
        harness_result.guardian_boundary
    )
    reasons.extend(guardian_reasons)

    if not harness_result.harness_result_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_RESULT_ID)
        )
    if not harness_result.receipt_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_RECEIPT_ID)
        )
    if (
        not harness_result.source_thread_id
        or not harness_result.source_message_id
    ):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_SOURCE_LINEAGE)
        )
    if not harness_result.invocation_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_INVOCATION_ID)
        )
    if not harness_result.harness_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_ID)
        )
    if not harness_result.harness_version:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.MISSING_HARNESS_VERSION)
        )
    if harness_result.result_class not in PI_HARNESS_RESULT_CLASSES:
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.INVALID_HARNESS_RESULT_CLASS
            )
        )

    provider_lane_reasons, provider_lane_metadata = _validate_provider_lane(
        harness_result.provider_lane
    )
    reasons.extend(provider_lane_reasons)

    permission_reasons, permission_metadata = _validate_permission_posture(
        requested_permissions=harness_result.requested_permissions,
        granted_permissions=harness_result.granted_permissions,
    )
    reasons.extend(permission_reasons)

    artifact_metadata = (
        harness_result.artifact.to_payload()
        if harness_result.artifact
        else None
    )
    if (
        harness_result.artifact is None
        or not harness_result.artifact.artifact_id
        or not harness_result.artifact.artifact_ref
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.MISSING_ARTIFACT_REFERENCE
            )
        )

    linkage_reasons, linkage_metadata = _validate_command_bus_linkage(
        harness_result.command_bus_linkage
    )
    reasons.extend(linkage_reasons)

    metadata = {
        "validator": "harness_result",
        "guardian_boundary": guardian_metadata,
        "harness_result_id": harness_result.harness_result_id,
        "receipt_id": harness_result.receipt_id,
        "source_lineage": {
            "source_thread_id": harness_result.source_thread_id,
            "source_message_id": harness_result.source_message_id,
            "authored_request_id": harness_result.authored_request_id,
            "attempt_id": harness_result.attempt_id,
        },
        "invocation_id": harness_result.invocation_id,
        "harness_id": harness_result.harness_id,
        "harness_version": harness_result.harness_version,
        "result_class": harness_result.result_class,
        "failure_classification": harness_result.failure_classification,
        "provider_lane": provider_lane_metadata,
        "permission_posture": permission_metadata,
        "artifact": artifact_metadata,
        "command_bus_linkage": linkage_metadata,
    }
    return reasons, metadata


def _compare_boundary(
    envelope_boundary: PiGuardianBoundary,
    other_boundary: PiGuardianBoundary,
    *,
    reasons: list[str],
) -> None:
    if (
        not envelope_boundary.owner_account_id
        or not other_boundary.owner_account_id
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.MISSING_OWNER_ACCOUNT_IDENTITY
            )
        )
    elif envelope_boundary.owner_account_id != other_boundary.owner_account_id:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.OWNER_ACCOUNT_MISMATCH)
        )

    if (
        envelope_boundary.request_policy_owner != GUARDIAN_OWNERSHIP_LABEL
        or other_boundary.request_policy_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )
    if (
        envelope_boundary.transcript_lineage_owner != GUARDIAN_OWNERSHIP_LABEL
        or other_boundary.transcript_lineage_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )
    if (
        envelope_boundary.provenance_owner != GUARDIAN_OWNERSHIP_LABEL
        or other_boundary.provenance_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )
    if (
        envelope_boundary.command_authority_owner != GUARDIAN_OWNERSHIP_LABEL
        or other_boundary.command_authority_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )
    if (
        envelope_boundary.result_return_owner != GUARDIAN_OWNERSHIP_LABEL
        or other_boundary.result_return_owner != GUARDIAN_OWNERSHIP_LABEL
    ):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.GUARDIAN_OWNERSHIP_MISMATCH
            )
        )


def _compare_required_text(
    *,
    expected: str,
    observed: str,
    missing_reason: PiValidationFailureReason,
    mismatch_reason: PiValidationFailureReason,
    reasons: list[str],
) -> None:
    if not expected or not observed:
        reasons.append(_invalid_reason(missing_reason))
    elif expected != observed:
        reasons.append(_invalid_reason(mismatch_reason))


def _compare_optional_text(
    *,
    expected: str | None,
    observed: str | None,
    mismatch_reason: PiValidationFailureReason,
    reasons: list[str],
) -> None:
    if expected is None and observed is None:
        return
    if expected != observed:
        reasons.append(_invalid_reason(mismatch_reason))


def _compare_signature_sets(
    *,
    expected: tuple[PiPermissionGrant, ...],
    observed: tuple[PiPermissionGrant, ...],
    reasons: list[str],
) -> None:
    if _permission_signatures(expected) != _permission_signatures(observed):
        reasons.append(
            _invalid_reason(
                PiValidationFailureReason.PERMISSION_POSTURE_INCONSISTENT
            )
        )


def _compare_linkage(
    *,
    expected: PiCommandBusLinkage | None,
    observed: PiCommandBusLinkage | None,
    reasons: list[str],
    mismatch_reason: PiValidationFailureReason,
) -> None:
    if expected is None and observed is None:
        return
    if expected is None or observed is None:
        reasons.append(_invalid_reason(mismatch_reason))
        return
    if expected.to_payload() != observed.to_payload():
        reasons.append(_invalid_reason(mismatch_reason))


def validate_invocation_envelope(
    envelope: PiInvocationEnvelope,
) -> PiInvocationValidationResult:
    reasons, metadata = _validate_envelope_core(envelope)
    return _result(reasons=reasons, metadata=metadata)


def validate_receipt_against_envelope(
    envelope: PiInvocationEnvelope,
    receipt: PiInvocationReceipt,
) -> PiInvocationValidationResult:
    reasons, metadata = _validate_envelope_core(envelope)
    receipt_reasons, receipt_metadata = _validate_receipt_core(receipt)
    reasons.extend(receipt_reasons)

    _compare_boundary(
        envelope.guardian_boundary, receipt.guardian_boundary, reasons=reasons
    )
    _compare_required_text(
        expected=envelope.source_thread_id,
        observed=receipt.source_thread_id,
        missing_reason=PiValidationFailureReason.MISSING_SOURCE_LINEAGE,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=envelope.source_message_id,
        observed=receipt.source_message_id,
        missing_reason=PiValidationFailureReason.MISSING_SOURCE_LINEAGE,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_optional_text(
        expected=envelope.authored_request_id,
        observed=receipt.authored_request_id,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_optional_text(
        expected=envelope.attempt_id,
        observed=receipt.attempt_id,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=envelope.invocation_id,
        observed=receipt.invocation_id,
        missing_reason=PiValidationFailureReason.MISSING_INVOCATION_ID,
        mismatch_reason=PiValidationFailureReason.INCONSISTENT_INVOCATION_ID,
        reasons=reasons,
    )
    _compare_required_text(
        expected=envelope.harness_id,
        observed=receipt.harness_id,
        missing_reason=PiValidationFailureReason.MISSING_HARNESS_ID,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=envelope.harness_version,
        observed=receipt.harness_version,
        missing_reason=PiValidationFailureReason.MISSING_HARNESS_VERSION,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
        reasons=reasons,
    )
    if (
        envelope.provider_lane.to_payload()
        != receipt.provider_lane.to_payload()
    ):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.RECEIPT_MISMATCH)
        )
    _compare_signature_sets(
        expected=envelope.requested_permissions,
        observed=receipt.requested_permissions,
        reasons=reasons,
    )
    _compare_signature_sets(
        expected=envelope.granted_permissions,
        observed=receipt.granted_permissions,
        reasons=reasons,
    )
    _compare_linkage(
        expected=envelope.command_bus_linkage,
        observed=receipt.command_bus_linkage,
        reasons=reasons,
        mismatch_reason=PiValidationFailureReason.RECEIPT_MISMATCH,
    )

    metadata.update(
        {
            "validator": "receipt_against_envelope",
            "receipt": receipt_metadata,
            "comparison": {
                "owner_account_id": receipt.guardian_boundary.owner_account_id,
                "source_thread_id": receipt.source_thread_id,
                "source_message_id": receipt.source_message_id,
                "invocation_id": receipt.invocation_id,
                "harness_id": receipt.harness_id,
                "harness_version": receipt.harness_version,
                "provider_lane_class": receipt.provider_lane.provider_lane_class,
            },
        }
    )
    return _result(reasons=reasons, metadata=metadata)


def validate_harness_result_against_receipt(
    receipt: PiInvocationReceipt,
    result: PiHarnessResult,
) -> PiInvocationValidationResult:
    reasons, metadata = _validate_harness_result_core(result)
    receipt_reasons, receipt_metadata = _validate_receipt_core(receipt)
    reasons.extend(receipt_reasons)

    _compare_boundary(
        receipt.guardian_boundary, result.guardian_boundary, reasons=reasons
    )
    _compare_required_text(
        expected=receipt.receipt_id,
        observed=result.receipt_id,
        missing_reason=PiValidationFailureReason.MISSING_RECEIPT_ID,
        mismatch_reason=PiValidationFailureReason.RESULT_RECEIPT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=receipt.source_thread_id,
        observed=result.source_thread_id,
        missing_reason=PiValidationFailureReason.MISSING_SOURCE_LINEAGE,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=receipt.source_message_id,
        observed=result.source_message_id,
        missing_reason=PiValidationFailureReason.MISSING_SOURCE_LINEAGE,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    _compare_optional_text(
        expected=receipt.authored_request_id,
        observed=result.authored_request_id,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    _compare_optional_text(
        expected=receipt.attempt_id,
        observed=result.attempt_id,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=receipt.invocation_id,
        observed=result.invocation_id,
        missing_reason=PiValidationFailureReason.MISSING_INVOCATION_ID,
        mismatch_reason=PiValidationFailureReason.INCONSISTENT_INVOCATION_ID,
        reasons=reasons,
    )
    _compare_required_text(
        expected=receipt.harness_id,
        observed=result.harness_id,
        missing_reason=PiValidationFailureReason.MISSING_HARNESS_ID,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    _compare_required_text(
        expected=receipt.harness_version,
        observed=result.harness_version,
        missing_reason=PiValidationFailureReason.MISSING_HARNESS_VERSION,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
        reasons=reasons,
    )
    if receipt.provider_lane.to_payload() != result.provider_lane.to_payload():
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )
    _compare_signature_sets(
        expected=receipt.requested_permissions,
        observed=result.requested_permissions,
        reasons=reasons,
    )
    _compare_signature_sets(
        expected=receipt.granted_permissions,
        observed=result.granted_permissions,
        reasons=reasons,
    )
    _compare_linkage(
        expected=receipt.command_bus_linkage,
        observed=result.command_bus_linkage,
        reasons=reasons,
        mismatch_reason=PiValidationFailureReason.HARNESS_RESULT_MISMATCH,
    )

    if receipt.receipt_status not in PI_INVOCATION_RECEIPT_TERMINAL_STATUSES:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )

    expected_result_class = {
        "completed": PiHarnessResultClass.SUCCESS.value,
        "failed": PiHarnessResultClass.FAILURE.value,
        "rejected": PiHarnessResultClass.BLOCKED.value,
    }.get(receipt.receipt_status)
    if expected_result_class is None:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )
    elif result.result_class != expected_result_class:
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )

    if (
        result.result_class == PiHarnessResultClass.SUCCESS.value
        and result.failure_classification is not None
    ):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )
    if (
        result.result_class != PiHarnessResultClass.SUCCESS.value
        and result.failure_classification is None
    ):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )

    artifact_ref = result.artifact.artifact_ref if result.artifact else ""
    if (
        receipt.result_artifact_ref is not None
        and artifact_ref != receipt.result_artifact_ref
    ):
        reasons.append(
            _invalid_reason(PiValidationFailureReason.HARNESS_RESULT_MISMATCH)
        )

    metadata.update(
        {
            "validator": "harness_result_against_receipt",
            "receipt": receipt_metadata,
            "comparison": {
                "receipt_id": receipt.receipt_id,
                "source_thread_id": receipt.source_thread_id,
                "source_message_id": receipt.source_message_id,
                "invocation_id": receipt.invocation_id,
                "harness_id": receipt.harness_id,
                "harness_version": receipt.harness_version,
                "provider_lane_class": receipt.provider_lane.provider_lane_class,
                "expected_result_class": expected_result_class,
                "observed_result_class": result.result_class,
                "artifact_ref": artifact_ref,
            },
        }
    )
    return _result(reasons=reasons, metadata=metadata)


__all__ = [
    "validate_invocation_envelope",
    "validate_receipt_against_envelope",
    "validate_harness_result_against_receipt",
]
