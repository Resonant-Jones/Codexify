"""Tests for PiInvocationResultReturn contract and validation."""

from __future__ import annotations

import sys

import pytest

from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationResultReturn,
)
from guardian.pi.validation import validate_pi_invocation_result_return


def _boundary(account_id: str = "acct-123") -> PiGuardianBoundary:
    return PiGuardianBoundary(owner_account_id=account_id)


def _result_return(**overrides: object) -> PiInvocationResultReturn:
    kwargs: dict[str, object] = {
        "result_return_id": "rr-1",
        "invocation_id": "inv-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "harness_id": "harness-1",
        "return_state": "not_returned",
        "guardian_boundary": _boundary(),
        "validation_status": "valid",
        "redaction_state": "clean",
        "created_at": "2026-01-01T00:00:00Z",
    }
    kwargs.update(overrides)
    return PiInvocationResultReturn(**kwargs)  # type: ignore[arg-type]


class TestResultReturnContract:
    def test_not_returned_passes(self) -> None:
        r = validate_pi_invocation_result_return(_result_return())
        assert r.ok

    def test_returned_with_artifact_id_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="returned", artifact_id="art-1")
        )
        assert r.ok

    def test_returned_with_receipt_id_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="returned", receipt_id="rec-1")
        )
        assert r.ok

    def test_returned_with_result_summary_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="returned", result_summary="done")
        )
        assert r.ok

    def test_blocked_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="blocked")
        )
        assert r.ok

    def test_deferred_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="deferred")
        )
        assert r.ok

    def test_validation_failed_with_reason_passes(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(
                return_state="validation_failed", failure_reason="lint errors"
            )
        )
        assert r.ok

    def test_missing_result_return_id_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(result_return_id="")
        )
        assert not r.ok

    def test_missing_invocation_id_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(invocation_id="")
        )
        assert not r.ok

    def test_missing_source_thread_id_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(source_thread_id="")
        )
        assert not r.ok

    def test_missing_source_message_id_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(source_message_id="")
        )
        assert not r.ok

    def test_missing_harness_id_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(harness_id="")
        )
        assert not r.ok

    def test_unbounded_return_state_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="launched")
        )
        assert not r.ok

    def test_missing_validation_status_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(validation_status="")
        )
        assert not r.ok

    def test_missing_redaction_state_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(redaction_state="")
        )
        assert not r.ok

    def test_missing_created_at_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(created_at="")
        )
        assert not r.ok

    def test_returned_without_evidence_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="returned")
        )
        assert not r.ok

    def test_validation_failed_without_reason_fails(self) -> None:
        r = validate_pi_invocation_result_return(
            _result_return(return_state="validation_failed")
        )
        assert not r.ok

    def test_raw_payload_not_required(self) -> None:
        rr = _result_return(return_state="returned", result_summary="ok")
        payload = rr.to_payload()
        assert "raw_args" not in payload
        assert "result_json" not in payload
        assert "raw_diff" not in payload
        assert "stack_trace" not in payload


class TestResultReturnNoRuntime:
    def test_validator_is_deterministic(self) -> None:
        rr = _result_return(return_state="returned", artifact_id="art-1")
        r1 = validate_pi_invocation_result_return(rr)
        r2 = validate_pi_invocation_result_return(rr)
        assert r1 == r2

    def test_importing_pi_does_not_import_runtime_routes(self) -> None:
        route_key = "guardian.routes.agent_orchestration"
        was_present = route_key in sys.modules
        import guardian.pi
        assert route_key not in sys.modules or was_present


class TestSerialization:
    def test_round_trip_preserves_fields(self) -> None:
        rr = _result_return(
            return_state="returned",
            artifact_id="art-1",
            result_summary="changes applied",
            failure_reason=None,
        )
        payload = rr.to_payload()
        restored = PiInvocationResultReturn.from_payload(payload)
        assert restored.result_return_id == rr.result_return_id
        assert restored.invocation_id == rr.invocation_id
        assert restored.return_state == rr.return_state
        assert restored.artifact_id == rr.artifact_id
        assert restored.result_summary == rr.result_summary
