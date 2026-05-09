from __future__ import annotations

import builtins
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from guardian.pi.contracts import (
    PiCommandBusLinkage,
    PiGuardianBoundary,
    PiHarnessResult,
    PiInvocationArtifact,
    PiInvocationEnvelope,
    PiInvocationReceipt,
    PiPermissionGrant,
    PiProviderLane,
)
from guardian.pi.tokens import (
    PiHarnessResultClass,
    PiInvocationEnvelopeStatus,
    PiInvocationReceiptStatus,
    PiInvocationValidationOutcome,
)
from guardian.pi.validation import (
    validate_harness_result_against_receipt,
    validate_invocation_envelope,
    validate_receipt_against_envelope,
)


def _boundary(account_id: str = "acct-123") -> PiGuardianBoundary:
    return PiGuardianBoundary(owner_account_id=account_id)


def _permissions() -> tuple[PiPermissionGrant, ...]:
    return (
        PiPermissionGrant(
            permission="files.read",
            resource="/workspace/project",
            reason="read the target file",
            metadata={"scope": "workspace"},
        ),
        PiPermissionGrant(
            permission="files.write",
            resource="/workspace/project/src",
            reason="narrow patch scope",
            metadata={"scope": "workspace"},
        ),
    )


def _provider_lane(
    *,
    lane_class: str = "local",
    metadata: dict[str, Any] | None = None,
) -> PiProviderLane:
    return PiProviderLane(
        provider_lane_class=lane_class,
        provider_name="guardian",
        model_id="pi-test-model",
        metadata=metadata or {},
    )


def _command_bus_linkage() -> PiCommandBusLinkage:
    return PiCommandBusLinkage(
        command_run_id="run-123",
        command_request_id="request-456",
        dispatch_id="dispatch-789",
        metadata={"source": "pi-boundary-test"},
    )


def _artifact() -> PiInvocationArtifact:
    return PiInvocationArtifact(
        artifact_id="artifact-123",
        artifact_ref="artifact://pi/test/123",
        artifact_class="patch",
        metadata={"files_changed": ["guardian/pi/contracts.py"]},
    )


def _envelope(
    *,
    provider_lane: PiProviderLane | None = None,
    requested_permissions: tuple[PiPermissionGrant, ...] | None = None,
    granted_permissions: tuple[PiPermissionGrant, ...] | None = None,
    command_bus_linkage: PiCommandBusLinkage | None = None,
    boundary: PiGuardianBoundary | None = None,
) -> PiInvocationEnvelope:
    return PiInvocationEnvelope(
        guardian_boundary=boundary or _boundary(),
        source_thread_id="thread-123",
        source_message_id="message-456",
        authored_request_id="request-789",
        attempt_id="attempt-321",
        invocation_id="invocation-abc",
        harness_id="pi-harness",
        harness_version="1.0.0",
        provider_lane=provider_lane or _provider_lane(),
        requested_permissions=requested_permissions or _permissions(),
        granted_permissions=granted_permissions or _permissions(),
        command_bus_linkage=command_bus_linkage or _command_bus_linkage(),
        status=PiInvocationEnvelopeStatus.PREPARED.value,
        validation_metadata={"source": "test"},
    )


def _receipt(
    envelope: PiInvocationEnvelope,
    *,
    receipt_status: str = PiInvocationReceiptStatus.COMPLETED.value,
    result_artifact_ref: str | None = "artifact://pi/test/123",
    command_bus_linkage: PiCommandBusLinkage | None = None,
) -> PiInvocationReceipt:
    return PiInvocationReceipt(
        receipt_id="receipt-abc",
        guardian_boundary=envelope.guardian_boundary,
        source_thread_id=envelope.source_thread_id,
        source_message_id=envelope.source_message_id,
        authored_request_id=envelope.authored_request_id,
        attempt_id=envelope.attempt_id,
        invocation_id=envelope.invocation_id,
        harness_id=envelope.harness_id,
        harness_version=envelope.harness_version,
        provider_lane=envelope.provider_lane,
        requested_permissions=envelope.requested_permissions,
        granted_permissions=envelope.granted_permissions,
        command_bus_linkage=command_bus_linkage or envelope.command_bus_linkage,
        result_artifact_ref=result_artifact_ref,
        receipt_status=receipt_status,
        validation_metadata={"source": "test"},
    )


def _result(receipt: PiInvocationReceipt) -> PiHarnessResult:
    return PiHarnessResult(
        harness_result_id="result-abc",
        receipt_id=receipt.receipt_id,
        guardian_boundary=receipt.guardian_boundary,
        source_thread_id=receipt.source_thread_id,
        source_message_id=receipt.source_message_id,
        authored_request_id=receipt.authored_request_id,
        attempt_id=receipt.attempt_id,
        invocation_id=receipt.invocation_id,
        harness_id=receipt.harness_id,
        harness_version=receipt.harness_version,
        provider_lane=receipt.provider_lane,
        requested_permissions=receipt.requested_permissions,
        granted_permissions=receipt.granted_permissions,
        artifact=_artifact(),
        command_bus_linkage=receipt.command_bus_linkage,
        result_class=PiHarnessResultClass.SUCCESS.value,
        failure_classification=None,
        validation_metadata={"source": "test"},
    )


def test_valid_envelope_validation_succeeds() -> None:
    result = validate_invocation_envelope(_envelope())

    assert result.validation_outcome == PiInvocationValidationOutcome.VALID.value
    assert result.failure_reasons == ()


def test_valid_receipt_matches_envelope() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)

    result = validate_receipt_against_envelope(envelope, receipt)

    assert result.validation_outcome == PiInvocationValidationOutcome.VALID.value
    assert result.failure_reasons == ()


def test_valid_harness_result_matches_receipt() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    harness_result = _result(receipt)

    result = validate_harness_result_against_receipt(receipt, harness_result)

    assert result.validation_outcome == PiInvocationValidationOutcome.VALID.value
    assert result.failure_reasons == ()


def test_owner_account_mismatch_fails_closed() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    receipt = replace(
        receipt,
        guardian_boundary=replace(
            receipt.guardian_boundary, owner_account_id="acct-999"
        ),
    )

    result = validate_receipt_against_envelope(envelope, receipt)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "owner_account_mismatch" in result.failure_reasons


def test_missing_source_lineage_fails_closed() -> None:
    envelope = replace(
        _envelope(),
        source_thread_id="",
        source_message_id="",
    )

    result = validate_invocation_envelope(envelope)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "missing_source_lineage" in result.failure_reasons


def test_missing_invocation_id_fails_closed() -> None:
    envelope = replace(_envelope(), invocation_id="")

    result = validate_invocation_envelope(envelope)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "missing_invocation_id" in result.failure_reasons


def test_receipt_envelope_invocation_mismatch_fails_closed() -> None:
    envelope = _envelope()
    receipt = replace(_receipt(envelope), invocation_id="different-invocation")

    result = validate_receipt_against_envelope(envelope, receipt)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "inconsistent_invocation_id" in result.failure_reasons


def test_harness_result_receipt_mismatch_fails_closed() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    harness_result = replace(_result(receipt), receipt_id="different-receipt")

    result = validate_harness_result_against_receipt(receipt, harness_result)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "harness_result_mismatch" in result.failure_reasons


def test_invalid_provider_lane_fails_closed() -> None:
    envelope = _envelope(provider_lane=_provider_lane(lane_class="bogus"))

    result = validate_invocation_envelope(envelope)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "invalid_provider_lane" in result.failure_reasons


def test_minimax_metadata_is_optional_and_not_required() -> None:
    with_minimax = _envelope(
        provider_lane=_provider_lane(
            metadata={
                "minimax": {
                    "model_id": "MiniMax-M1",
                    "region": "us-east-1",
                }
            }
        )
    )
    without_minimax = _envelope(provider_lane=_provider_lane(metadata={}))

    assert (
        validate_invocation_envelope(with_minimax).validation_outcome
        == PiInvocationValidationOutcome.VALID.value
    )
    assert (
        validate_invocation_envelope(without_minimax).validation_outcome
        == PiInvocationValidationOutcome.VALID.value
    )

    required_minimax = _envelope(
        provider_lane=_provider_lane(
            metadata={
                "minimax": {
                    "required": True,
                    "model_id": "MiniMax-M1",
                }
            }
        )
    )

    result = validate_invocation_envelope(required_minimax)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "minimax_metadata_required" in result.failure_reasons


def test_permission_posture_mismatch_fails_closed() -> None:
    envelope = _envelope()
    receipt = _receipt(
        envelope,
        command_bus_linkage=_command_bus_linkage(),
    )
    receipt = replace(
        receipt,
        granted_permissions=receipt.granted_permissions[:-1],
    )

    result = validate_receipt_against_envelope(envelope, receipt)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "permission_posture_inconsistent" in result.failure_reasons


def test_malformed_command_bus_linkage_fails_closed() -> None:
    envelope = _envelope(command_bus_linkage=PiCommandBusLinkage(command_run_id="   "))

    result = validate_invocation_envelope(envelope)

    assert (
        result.validation_outcome == PiInvocationValidationOutcome.FAILED_CLOSED.value
    )
    assert "malformed_command_bus_linkage" in result.failure_reasons


def test_validation_helpers_are_deterministic() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    result = _result(receipt)

    envelope_first = validate_invocation_envelope(envelope)
    envelope_second = validate_invocation_envelope(envelope)

    receipt_first = validate_receipt_against_envelope(envelope, receipt)
    receipt_second = validate_receipt_against_envelope(envelope, receipt)

    result_first = validate_harness_result_against_receipt(receipt, result)
    result_second = validate_harness_result_against_receipt(receipt, result)

    assert envelope_first == envelope_second
    assert receipt_first == receipt_second
    assert result_first == result_second


def test_validation_helpers_are_side_effect_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    result = _result(receipt)

    imports: list[str] = []
    real_import = builtins.__import__

    def tracking_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] | list[str] = (),
        level: int = 0,
    ) -> Any:
        imports.append(name)
        return real_import(name, globals, locals, fromlist, level)

    envelope_before = deepcopy(envelope)
    receipt_before = deepcopy(receipt)
    result_before = deepcopy(result)

    monkeypatch.setattr(builtins, "__import__", tracking_import)

    validate_invocation_envelope(envelope)
    validate_receipt_against_envelope(envelope, receipt)
    validate_harness_result_against_receipt(receipt, result)

    assert envelope == envelope_before
    assert receipt == receipt_before
    assert result == result_before
    assert not any(
        name.startswith(
            (
                "guardian.core.ai_router",
                "guardian.command_bus",
                "guardian.db",
                "guardian.workers",
                "redis",
                "pi_sdk",
            )
        )
        for name in imports
    )


def test_serialization_round_trip_preserves_contract_fields() -> None:
    envelope = _envelope()
    receipt = _receipt(envelope)
    result = _result(receipt)
    validation = validate_harness_result_against_receipt(receipt, result)

    assert PiInvocationEnvelope.from_payload(envelope.to_payload()) == envelope
    assert PiInvocationReceipt.from_payload(receipt.to_payload()) == receipt
    assert (
        PiInvocationArtifact.from_payload(result.artifact.to_payload())
        == result.artifact
    )
    assert PiHarnessResult.from_payload(result.to_payload()) == result
    assert validation.__class__.from_payload(validation.to_payload()) == validation
