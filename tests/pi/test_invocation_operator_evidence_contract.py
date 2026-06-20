"""Tests for PiInvocationOperatorEvidence contract and validation."""

from __future__ import annotations

import sys

import pytest

from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationOperatorEvidence,
)
from guardian.pi.validation import validate_pi_invocation_operator_evidence


def _boundary(account_id: str = "acct-123") -> PiGuardianBoundary:
    return PiGuardianBoundary(owner_account_id=account_id)


def _evidence(**overrides: object) -> PiInvocationOperatorEvidence:
    kwargs: dict[str, object] = {
        "operator_evidence_id": "oe-1",
        "invocation_id": "inv-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "harness_id": "harness-1",
        "evidence_state": "unavailable",
        "policy_decision_summary": "invocation reviewed",
        "permission_posture": "files.read",
        "guardian_boundary": _boundary(),
        "validation_status": "valid",
        "redaction_state": "clean",
        "created_at": "2026-01-01T00:00:00Z",
    }
    kwargs.update(overrides)
    return PiInvocationOperatorEvidence(**kwargs)  # type: ignore[arg-type]


class TestOperatorEvidenceContract:
    def test_unavailable_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(_evidence())
        assert r.ok

    def test_available_with_result_return_id_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="available", result_return_id="rr-1")
        )
        assert r.ok

    def test_available_with_receipt_id_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="available", receipt_id="rec-1")
        )
        assert r.ok

    def test_available_with_artifact_id_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="available", artifact_id="art-1")
        )
        assert r.ok

    def test_available_with_result_summary_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="available", result_summary="done")
        )
        assert r.ok

    def test_blocked_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="blocked")
        )
        assert r.ok

    def test_deferred_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="deferred")
        )
        assert r.ok

    def test_partial_passes_with_summary(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="partial", result_summary="partial output")
        )
        assert r.ok

    def test_validation_failed_with_reason_passes(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="validation_failed", failure_reason="lint errors")
        )
        assert r.ok

    def test_missing_operator_evidence_id_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(operator_evidence_id="")
        )
        assert not r.ok

    def test_missing_invocation_id_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(invocation_id="")
        )
        assert not r.ok

    def test_missing_source_thread_id_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(source_thread_id="")
        )
        assert not r.ok

    def test_missing_source_message_id_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(source_message_id="")
        )
        assert not r.ok

    def test_missing_harness_id_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(harness_id="")
        )
        assert not r.ok

    def test_unbounded_evidence_state_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="complete")
        )
        assert not r.ok

    def test_missing_policy_decision_summary_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(policy_decision_summary="")
        )
        assert not r.ok

    def test_missing_permission_posture_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(permission_posture="")
        )
        assert not r.ok

    def test_missing_validation_status_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(validation_status="")
        )
        assert not r.ok

    def test_missing_redaction_state_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(redaction_state="")
        )
        assert not r.ok

    def test_missing_created_at_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(created_at="")
        )
        assert not r.ok

    def test_available_without_evidence_fails(self) -> None:
        r = validate_pi_invocation_operator_evidence(
            _evidence(evidence_state="available")
        )
        assert not r.ok

    def test_raw_payload_not_required(self) -> None:
        e = _evidence(evidence_state="available", result_summary="ok")
        payload = e.to_payload()
        assert "raw_args" not in payload
        assert "result_json" not in payload
        assert "stack_trace" not in payload


class TestOperatorEvidenceNoRuntime:
    def test_validator_is_deterministic(self) -> None:
        e = _evidence(evidence_state="available", artifact_id="art-1")
        r1 = validate_pi_invocation_operator_evidence(e)
        r2 = validate_pi_invocation_operator_evidence(e)
        assert r1 == r2

    def test_importing_pi_does_not_import_runtime_routes(self) -> None:
        route_key = "guardian.routes.agent_orchestration"
        was_present = route_key in sys.modules
        import guardian.pi
        assert route_key not in sys.modules or was_present
