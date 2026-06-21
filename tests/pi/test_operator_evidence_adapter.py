"""Tests for the Pi/Coder operator evidence adapter."""

from __future__ import annotations

from typing import Any

import pytest

from guardian.pi.contracts import PiInvocationOperatorEvidence
from guardian.pi.evidence import (
    build_operator_evidence_from_dry_run_response,
    FORBIDDEN_RESPONSE_KEYS,
)


def _accepted_response(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "dry_run": True,
        "accepted": True,
        "state": "validated",
        "validation_status": "valid",
        "errors": [],
        "warnings": [],
        "redaction_state": "clean",
        "release_support": "unsupported",
        "execution_performed": False,
        "persistence_performed": False,
        "invocation_id": "inv-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "harness_id": "harness-1",
        "permission_posture": "files.read",
        "result_summary": "envelope valid",
    }
    base.update(overrides)
    return base


def _rejected_response() -> dict[str, Any]:
    return _accepted_response(
        accepted=False,
        state="validation_failed",
        validation_status="failed_closed",
        errors=["missing_source_lineage"],
        result_summary="",
    )


class TestStateMapping:
    def test_accepted_maps_to_available(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(),
        )
        assert isinstance(evidence, PiInvocationOperatorEvidence)
        assert evidence.evidence_state == "available"

    def test_rejected_maps_to_validation_failed(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_rejected_response(),
        )
        assert evidence.evidence_state == "validation_failed"

    def test_none_response_maps_to_unavailable(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=None,
            safe_invocation_id="inv-1",
        )
        assert evidence.evidence_state == "unavailable"

    def test_execution_performed_maps_to_blocked(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(execution_performed=True),
        )
        assert evidence.evidence_state == "blocked"

    def test_persistence_performed_maps_to_blocked(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(persistence_performed=True),
        )
        assert evidence.evidence_state == "blocked"

    def test_non_unsupported_release_maps_to_blocked(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(release_support="beta"),
        )
        assert evidence.evidence_state == "blocked"

    def test_no_references_maps_to_partial(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(
                invocation_id="",
                source_thread_id="",
                source_message_id="",
                harness_id="",
                result_summary="",
            ),
        )
        assert evidence.evidence_state == "partial"


class TestSafeFiltering:
    def test_forbidden_keys_excluded_from_metadata(self) -> None:
        response = _accepted_response()
        response["raw_args"] = "SECRET"
        response["extra_meta"] = {"secret": "BAD"}
        evidence = build_operator_evidence_from_dry_run_response(
            response=response,
        )
        assert "raw_args" not in evidence.metadata
        assert "extra_meta" not in evidence.metadata

    def test_forbidden_keys_not_in_evidence_fields(self) -> None:
        response = _accepted_response()
        response["stack_trace"] = "TRACEBACK_DATA"
        evidence = build_operator_evidence_from_dry_run_response(
            response=response,
        )
        payload = evidence.to_payload()
        assert "stack_trace" not in payload

    def test_evidence_has_no_completion_verdict(self) -> None:
        evidence = build_operator_evidence_from_dry_run_response(
            response=_accepted_response(),
        )
        payload = evidence.to_payload()
        assert "completed" not in payload
        assert "completion_status" not in payload
        assert "execution_success" not in payload


class TestDeterminism:
    def test_same_input_gives_same_output(self) -> None:
        resp = _accepted_response()
        e1 = build_operator_evidence_from_dry_run_response(response=resp)
        e2 = build_operator_evidence_from_dry_run_response(response=resp)
        assert e1.to_payload() == e2.to_payload()

    def test_does_not_mutate_input(self) -> None:
        resp = _accepted_response()
        orig = dict(resp)
        build_operator_evidence_from_dry_run_response(response=resp)
        assert resp == orig


class TestModuleExports:
    def test_no_forbidden_execution_exports(self) -> None:
        import guardian.pi.evidence as ev
        forbidden = [
            "execute_pi_coder", "run_pi_coder", "dispatch_pi_coder",
            "invoke_pi_coder", "create_pi_coder_receipt",
            "create_pi_coder_artifact", "complete_pi_coder",
        ]
        for name in forbidden:
            assert not hasattr(ev, name)
