from __future__ import annotations

import inspect

from guardian.pi.contracts import (
    PiHarnessResult,
    PiInvocationArtifact,
    PiInvocationEnvelope,
    PiInvocationReceipt,
)
from guardian.pi.tokens import PiValidationFailureReason
from guardian.pi.validation import (
    validate_harness_result_against_receipt,
    validate_invocation_envelope,
    validate_receipt_against_envelope,
)


def _valid_envelope() -> PiInvocationEnvelope:
    return PiInvocationEnvelope(
        owner_account_id="acct_1",
        source_thread_id="thread_1",
        source_message_id="msg_1",
        authored_request_id="req_1",
        execution_attempt_id="attempt_1",
        invocation_id="inv_1",
        harness_id="pi_harness",
        harness_version="v1",
        provider_lane="remote",
        provider_lane_metadata={
            "minimax": {"model": "optional-ref", "requires_minimax": False}
        },
        requested_permissions=("read_workspace", "write_workspace"),
        granted_permissions=("read_workspace",),
        command_bus_linkage={
            "command_run_id": "run_1",
            "source": "pi_boundary",
        },
        provenance={"owner": "guardian"},
    )


def _valid_receipt() -> PiInvocationReceipt:
    return PiInvocationReceipt(
        owner_account_id="acct_1",
        invocation_id="inv_1",
        receipt_id="receipt_1",
        receipt_status="accepted",
        harness_id="pi_harness",
        execution_attempt_id="attempt_1",
        granted_permissions=("read_workspace",),
        command_bus_linkage={
            "command_run_id": "run_1",
            "source": "pi_boundary",
        },
    )


def _valid_result() -> PiHarnessResult:
    return PiHarnessResult(
        owner_account_id="acct_1",
        invocation_id="inv_1",
        receipt_id="receipt_1",
        harness_result_id="result_1",
        harness_result_class="success",
        artifacts=(
            PiInvocationArtifact(
                artifact_id="art_1",
                artifact_type="diff",
                uri="memory://artifact/1",
                digest="sha256:abc",
            ),
        ),
        command_bus_linkage={
            "command_run_id": "run_1",
            "source": "pi_boundary",
        },
    )


def test_valid_envelope_validation_succeeds() -> None:
    result = validate_invocation_envelope(_valid_envelope())
    assert result.ok


def test_valid_receipt_matches_envelope() -> None:
    result = validate_receipt_against_envelope(
        _valid_envelope(), _valid_receipt()
    )
    assert result.ok


def test_valid_harness_result_matches_receipt() -> None:
    result = validate_harness_result_against_receipt(
        _valid_receipt(), _valid_result()
    )
    assert result.ok


def test_owner_account_mismatch_fails_closed() -> None:
    envelope = _valid_envelope()
    receipt = _valid_receipt()
    bad = PiInvocationReceipt(
        **{**receipt.to_payload(), "owner_account_id": "acct_x"}
    )
    result = validate_receipt_against_envelope(envelope, bad)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.OWNER_ACCOUNT_MISMATCH.value
    )


def test_missing_source_lineage_fails_closed() -> None:
    envelope = PiInvocationEnvelope(
        **{
            **_valid_envelope().to_payload(),
            "source_thread_id": "",
            "source_message_id": "",
        }
    )
    result = validate_invocation_envelope(envelope)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.MISSING_SOURCE_LINEAGE.value
    )


def test_missing_invocation_id_fails_closed() -> None:
    envelope = PiInvocationEnvelope(
        **{**_valid_envelope().to_payload(), "invocation_id": ""}
    )
    result = validate_invocation_envelope(envelope)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.MISSING_INVOCATION_ID.value
    )


def test_receipt_envelope_invocation_mismatch_fails_closed() -> None:
    receipt = PiInvocationReceipt(
        **{**_valid_receipt().to_payload(), "invocation_id": "inv_other"}
    )
    result = validate_receipt_against_envelope(_valid_envelope(), receipt)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.RECEIPT_ENVELOPE_MISMATCH.value
    )


def test_harness_result_receipt_mismatch_fails_closed() -> None:
    result_payload = _valid_result().to_payload()
    bad = PiHarnessResult(**{**result_payload, "receipt_id": "receipt_other"})
    validation = validate_harness_result_against_receipt(_valid_receipt(), bad)
    assert not validation.ok
    assert (
        validation.failure_reason
        == PiValidationFailureReason.RESULT_RECEIPT_MISMATCH.value
    )


def test_invalid_provider_lane_fails_closed() -> None:
    envelope = PiInvocationEnvelope(
        **{**_valid_envelope().to_payload(), "provider_lane": "invalid_lane"}
    )
    result = validate_invocation_envelope(envelope)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.INVALID_PROVIDER_LANE.value
    )


def test_minimax_metadata_optional_not_required() -> None:
    ok = validate_invocation_envelope(_valid_envelope())
    assert ok.ok

    bad = PiInvocationEnvelope(
        **{
            **_valid_envelope().to_payload(),
            "provider_lane_metadata": {"minimax": {"requires_minimax": True}},
        }
    )
    bad_result = validate_invocation_envelope(bad)
    assert not bad_result.ok
    assert (
        bad_result.failure_reason
        == PiValidationFailureReason.MINIMAX_METADATA_REQUIRES_PROVIDER.value
    )


def test_permission_posture_mismatch_fails_closed() -> None:
    envelope = PiInvocationEnvelope(
        **{
            **_valid_envelope().to_payload(),
            "requested_permissions": ("read_workspace",),
            "granted_permissions": ("write_workspace",),
        }
    )
    result = validate_invocation_envelope(envelope)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.PERMISSION_POSTURE_MISMATCH.value
    )


def test_malformed_command_bus_linkage_fails_closed() -> None:
    envelope = PiInvocationEnvelope(
        **{
            **_valid_envelope().to_payload(),
            "command_bus_linkage": {"source": "pi_boundary"},
        }
    )
    result = validate_invocation_envelope(envelope)
    assert not result.ok
    assert (
        result.failure_reason
        == PiValidationFailureReason.MALFORMED_COMMAND_BUS_LINKAGE.value
    )


def test_validation_helpers_deterministic() -> None:
    envelope = _valid_envelope()
    first = validate_invocation_envelope(envelope)
    second = validate_invocation_envelope(envelope)
    assert first == second


def test_validation_helpers_side_effect_free() -> None:
    envelope = _valid_envelope()
    before = envelope.to_payload()
    _ = validate_invocation_envelope(envelope)
    after = envelope.to_payload()
    assert before == after


def test_serialization_round_trip_preserves_contracts() -> None:
    envelope = _valid_envelope()
    receipt = _valid_receipt()
    result = _valid_result()

    envelope_rt = PiInvocationEnvelope.from_payload(envelope.to_payload())
    receipt_rt = PiInvocationReceipt.from_payload(receipt.to_payload())
    result_rt = PiHarnessResult.from_payload(result.to_payload())

    assert envelope_rt.to_payload() == envelope.to_payload()
    assert receipt_rt.to_payload() == receipt.to_payload()
    assert result_rt.to_payload() == result.to_payload()


def test_seam_does_not_require_runtime_clients() -> None:
    import guardian.pi.contracts as contracts_module
    import guardian.pi.validation as validation_module

    contracts_source = inspect.getsource(contracts_module)
    validation_source = inspect.getsource(validation_module)
    banned_tokens = (
        "pi_sdk",
        "minimax_provider",
        "ai_router",
        "command_bus.invoke",
        "redis",
        "sqlalchemy",
        "worker",
    )
    for token in banned_tokens:
        assert token not in contracts_source
        assert token not in validation_source
