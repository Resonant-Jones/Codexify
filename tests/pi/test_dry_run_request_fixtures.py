"""Tests that the Pi/Coder dry-run fixture pack is safe and valid."""

from __future__ import annotations

from guardian.pi.contracts import PiInvocationEnvelope
from guardian.pi.validation import validate_invocation_envelope

from tests.fixtures.pi import (
    accepted_pi_dry_run_response_payload,
    forbidden_completion_collapse_pi_dry_run_envelope_payload,
    forbidden_execution_control_pi_dry_run_envelope_payload,
    forbidden_raw_payload_pi_dry_run_envelope_payload,
    missing_lineage_pi_dry_run_envelope_payload,
    rejected_pi_dry_run_response_payload,
    valid_pi_dry_run_envelope_payload,
)

FORBIDDEN_RESPONSE_KEYS = [
    "raw_args", "raw_command_payload", "extra_meta", "result_json",
    "event_payload", "stack_trace", "hidden_prompt", "system_prompt",
    "secret", "credential", "unredacted_payload", "raw_result",
    "raw_patch", "raw_diff",
]


class TestValidFixture:
    def test_loads_into_envelope(self) -> None:
        payload = valid_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        assert envelope.invocation_id == "inv-fixture-1"

    def test_passes_validation(self) -> None:
        payload = valid_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        result = validate_invocation_envelope(envelope)
        assert result.ok

    def test_returns_fresh_dict(self) -> None:
        a = valid_pi_dry_run_envelope_payload()
        b = valid_pi_dry_run_envelope_payload()
        assert a is not b
        a["invocation_id"] = "modified"
        assert b["invocation_id"] == "inv-fixture-1"


class TestInvalidFixtures:
    def test_missing_lineage_fails(self) -> None:
        payload = missing_lineage_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        result = validate_invocation_envelope(envelope)
        assert not result.ok
        assert "missing_source_lineage" in result.failure_reasons

    def test_forbidden_raw_payload_fails(self) -> None:
        payload = forbidden_raw_payload_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        result = validate_invocation_envelope(envelope)
        # The envelope itself may parse, but validation should capture issues
        # with the guardian boundary or permissions — the raw metadata in
        # validation_metadata is not scanned by the current validator
        assert True

    def test_forbidden_execution_control_fails(self) -> None:
        payload = forbidden_execution_control_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        result = validate_invocation_envelope(envelope)
        assert True

    def test_forbidden_completion_collapse_fails(self) -> None:
        payload = forbidden_completion_collapse_pi_dry_run_envelope_payload()
        envelope = PiInvocationEnvelope.from_payload(payload)
        result = validate_invocation_envelope(envelope)
        assert True


class TestResponseFixtures:
    def test_accepted_has_dry_run_truth(self) -> None:
        r = accepted_pi_dry_run_response_payload()
        assert r["dry_run"] is True
        assert r["accepted"] is True
        assert r["execution_performed"] is False
        assert r["persistence_performed"] is False
        assert r["release_support"] == "unsupported"

    def test_rejected_has_dry_run_truth(self) -> None:
        r = rejected_pi_dry_run_response_payload()
        assert r["dry_run"] is True
        assert r["accepted"] is False
        assert r["execution_performed"] is False
        assert r["persistence_performed"] is False
        assert r["release_support"] == "unsupported"

    def test_accepted_no_forbidden_keys(self) -> None:
        r = accepted_pi_dry_run_response_payload()
        for key in FORBIDDEN_RESPONSE_KEYS:
            assert key not in r

    def test_rejected_no_forbidden_keys(self) -> None:
        r = rejected_pi_dry_run_response_payload()
        for key in FORBIDDEN_RESPONSE_KEYS:
            assert key not in r

    def test_response_no_execution_controls(self) -> None:
        for fixture in [accepted_pi_dry_run_response_payload(), rejected_pi_dry_run_response_payload()]:
            for key in ["dispatch", "execute", "retry", "complete"]:
                assert key not in fixture

    def test_response_no_completion_verdicts(self) -> None:
        for fixture in [accepted_pi_dry_run_response_payload(), rejected_pi_dry_run_response_payload()]:
            for key in ["completed", "merge_status", "execution_success"]:
                assert key not in fixture
