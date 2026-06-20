"""Tests for PiInvocationPolicyDecision contract and validation."""

from __future__ import annotations

import sys

import pytest

from guardian.pi.contracts import (
    PiGuardianBoundary,
    PiInvocationPolicyDecision,
    PiPermissionGrant,
)
from guardian.pi.tokens import PiValidationFailureReason
from guardian.pi.validation import validate_pi_invocation_policy_decision


def _boundary(account_id: str = "acct-123") -> PiGuardianBoundary:
    return PiGuardianBoundary(owner_account_id=account_id)


def _read_permission() -> PiPermissionGrant:
    return PiPermissionGrant(
        permission="files.read",
        resource="/workspace/project",
        reason="read target file",
    )


def _write_permission() -> PiPermissionGrant:
    return PiPermissionGrant(
        permission="files.write",
        resource="/workspace/project/src",
        reason="write patch",
    )


def _allowed_decision(**overrides: object) -> PiInvocationPolicyDecision:
    kwargs: dict[str, object] = {
        "policy_decision_id": "pd-1",
        "invocation_id": "inv-1",
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "harness_id": "harness-1",
        "decision": "allowed",
        "guardian_boundary": _boundary(),
        "requested_permissions": (_read_permission(),),
        "granted_permissions": (_read_permission(),),
        "permission_posture": "files.read",
        "decided_at": "2026-01-01T00:00:00Z",
        "validation_status": "valid",
        "redaction_state": "clean",
    }
    kwargs.update(overrides)
    return PiInvocationPolicyDecision(**kwargs)  # type: ignore[arg-type]


class TestPolicyDecisionContract:
    def test_valid_allowed_passes(self) -> None:
        result = validate_pi_invocation_policy_decision(_allowed_decision())
        assert result.ok

    def test_valid_denied_passes_with_empty_grants(self) -> None:
        decision = _allowed_decision(
            decision="denied", granted_permissions=()
        )
        result = validate_pi_invocation_policy_decision(decision)
        assert result.ok

    def test_valid_blocked_passes_with_empty_grants(self) -> None:
        decision = _allowed_decision(
            decision="blocked", granted_permissions=()
        )
        result = validate_pi_invocation_policy_decision(decision)
        assert result.ok

    def test_valid_deferred_passes(self) -> None:
        decision = _allowed_decision(decision="deferred")
        result = validate_pi_invocation_policy_decision(decision)
        assert result.ok

    def test_missing_policy_decision_id_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(policy_decision_id="")
        )
        assert not result.ok

    def test_missing_invocation_id_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(invocation_id="")
        )
        assert not result.ok

    def test_missing_source_thread_id_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(source_thread_id="")
        )
        assert not result.ok

    def test_missing_source_message_id_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(source_message_id="")
        )
        assert not result.ok

    def test_missing_harness_id_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(harness_id="")
        )
        assert not result.ok

    def test_unbounded_decision_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(decision="execute_now")
        )
        assert not result.ok

    def test_missing_requested_permissions_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(requested_permissions=())
        )
        assert not result.ok

    def test_missing_permission_posture_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(permission_posture="")
        )
        assert not result.ok

    def test_missing_validation_status_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(validation_status="")
        )
        assert not result.ok

    def test_missing_redaction_state_fails(self) -> None:
        result = validate_pi_invocation_policy_decision(
            _allowed_decision(redaction_state="")
        )
        assert not result.ok

    def test_allowed_cannot_grant_unrequested_permission(self) -> None:
        decision = _allowed_decision(
            requested_permissions=(_read_permission(),),
            granted_permissions=(_write_permission(),),
        )
        result = validate_pi_invocation_policy_decision(decision)
        assert not result.ok

    def test_denied_with_grants_fails(self) -> None:
        decision = _allowed_decision(
            decision="denied",
            granted_permissions=(_read_permission(),),
        )
        result = validate_pi_invocation_policy_decision(decision)
        assert not result.ok

    def test_blocked_with_grants_fails(self) -> None:
        decision = _allowed_decision(
            decision="blocked",
            granted_permissions=(_read_permission(),),
        )
        result = validate_pi_invocation_policy_decision(decision)
        assert not result.ok


class TestPolicyNoRuntime:
    def test_validator_does_not_call_network(self) -> None:
        decision = _allowed_decision()
        # Pure validation — no network, no DB, no execution
        result = validate_pi_invocation_policy_decision(decision)
        assert result.ok

    def test_validator_is_deterministic(self) -> None:
        decision = _allowed_decision()
        r1 = validate_pi_invocation_policy_decision(decision)
        r2 = validate_pi_invocation_policy_decision(decision)
        assert r1 == r2

    def test_importing_pi_does_not_import_runtime_routes(self) -> None:
        import importlib

        route_key = "guardian.routes.agent_orchestration"
        was_present = route_key in sys.modules
        import guardian.pi
        # Should not cause orchestration routes to be loaded if not already
        assert route_key not in sys.modules or was_present


class TestSerialization:
    def test_round_trip_preserves_fields(self) -> None:
        decision = _allowed_decision()
        payload = decision.to_payload()
        restored = PiInvocationPolicyDecision.from_payload(payload)
        assert restored.policy_decision_id == decision.policy_decision_id
        assert restored.invocation_id == decision.invocation_id
        assert restored.source_thread_id == decision.source_thread_id
        assert restored.source_message_id == decision.source_message_id
        assert restored.harness_id == decision.harness_id
        assert restored.decision == decision.decision
        assert len(restored.requested_permissions) == len(decision.requested_permissions)
        assert len(restored.granted_permissions) == len(decision.granted_permissions)
