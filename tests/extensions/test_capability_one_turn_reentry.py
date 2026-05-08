"""Focused tests for the one-turn assistant reentry seam."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.command_bus.contracts import CapabilityManualDispatchResult
from guardian.db.models import (
    AgentExtensionInstallBinding,
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
    Base,
)
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
    CapabilityAssistantContinuationPayload,
    CapabilityAssistantReentryResult,
    CapabilityResultReinjectionResult,
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.reentry import (
    reentry_from_failed_reinjection,
    reentry_from_reinjection_result,
    reentry_from_successful_reinjection,
)
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityAssistantReentryFailureReason,
    CapabilityAssistantReentryOutcome,
    CapabilityReinjectionResultShape,
    CapabilityReinjectionSource,
    CapabilityResultReinjectionOutcome,
    ExtensionInstallBindingScope,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)


@pytest.fixture()
def reentry_store():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            AgentExtensionProposal.__table__,
            AgentExtensionInstallGateDecision.__table__,
            AgentExtensionRegistryEntry.__table__,
            AgentExtensionInstallBinding.__table__,
        ],
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    class _DB:
        def get_session(self):
            return Session()

    store = ExtensionProposalStore(_DB())
    registry = CapabilityRegistry(store)
    gate = InstallGate(store, registry)
    bindings = ExtensionInstallBindings(store, registry)
    return store, gate, registry, bindings


def _manifest(
    *,
    target_surface: str,
    scope: str,
    project_id: int | None = None,
    profile_id: str | None = None,
) -> ExtensionProposalManifest:
    return ExtensionProposalManifest(
        target_surface=target_surface,
        scope=scope,
        project_id=project_id,
        profile_id=profile_id,
        source_thread_id=41,
        source_message_id=42,
        summary="Generate a bounded tool plugin",
        description="Draft a tool proposal without executing it.",
        requested_permissions=(
            ExtensionRequestedPermission(
                permission="alpha.read",
                resource="command_bus",
                reason="read capability",
            ),
            ExtensionRequestedPermission(
                permission="zeta.write",
                resource="command_bus",
                reason="write capability",
            ),
        ),
        declared_dependencies=(
            ExtensionDeclaredDependency(
                name="httpx",
                version_spec=">=0.28",
                source="pypi",
            ),
        ),
        rollback_metadata=ExtensionRollbackMetadata(
            strategy="disable_and_revert",
            rollback_ref="ticket-123",
        ),
        test_evidence_metadata=ExtensionTestEvidenceMetadata(
            status="passing",
            summary="reentry coverage",
            artifacts=("tests/extensions/test_capability_one_turn_reentry.py",),
        ),
    )


def _approved_registry_entry(
    store: ExtensionProposalStore,
    gate: InstallGate,
    *,
    account_id: str,
    manifest: ExtensionProposalManifest,
):
    proposal = store.create_proposal(account_id=account_id, manifest=manifest)
    decision, registry_entry = gate.approve_proposal(
        account_id=account_id,
        proposal_id=proposal.proposal_id,
        reason="manual approval",
        notes={"reviewer": "alice"},
    )
    return proposal, decision, registry_entry


def _bound_registry_entry(
    bindings: ExtensionInstallBindings,
    *,
    account_id: str,
    registry_entry,
    project_id: int,
):
    return bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id=account_id,
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=project_id,
            bind_reason="manual install binding",
            bind_notes={"reviewer": "alice"},
            bind_metadata={"source": "unit-test"},
        )
    )


def _manual_dispatch_result(
    *,
    account_id: str,
    proposal,
    registry_entry,
    binding,
    status: str,
    run_id: str = "run-123",
    inline_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> CapabilityManualDispatchResult:
    result_payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "invoke_version": "1.0",
        "manifest_version": "1.0",
        "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
        "policy_warnings": [],
    }
    if inline_result is not None:
        result_payload["inline_result"] = inline_result
    if error is not None:
        result_payload["error"] = error

    approved_permissions = [
        permission.to_payload()
        for permission in registry_entry.approved_permissions
    ]
    if not approved_permissions:
        approved_permissions = [
            permission.to_payload()
            for permission in proposal.requested_permissions
        ]

    return CapabilityManualDispatchResult(
        manual_dispatch_id="dispatch-123",
        account_id=account_id,
        proposal_id=proposal.proposal_id,
        registry_entry_id=registry_entry.registry_id,
        effective_binding_id=binding.binding_id,
        resolved_from_scope_token=binding.scope_token,
        command_bus_run_id=run_id,
        command_bus_result_json=result_payload,
        manifest_snapshot_json=proposal.manifest.to_payload(),
        approved_permissions_json=approved_permissions,
        dispatch_metadata_json={
            "source": "unit-test",
            "proposal_id": proposal.proposal_id,
            "registry_entry_id": registry_entry.registry_id,
            "binding_id": binding.binding_id,
        },
    )


def _simulate_successful_reinjection(
    manual_result: CapabilityManualDispatchResult,
) -> CapabilityResultReinjectionResult:
    """Simulate what reinject_successful_manual_capability_dispatch_result returns."""
    from guardian.extensions.reinjection import (
        reinject_successful_manual_capability_dispatch_result,
    )

    return reinject_successful_manual_capability_dispatch_result(
        account_id=manual_result.account_id,
        manual_dispatch_result=manual_result,
    )


def _simulate_failed_reinjection(
    manual_result: CapabilityManualDispatchResult,
) -> CapabilityResultReinjectionResult:
    """Simulate what reinject_failed_manual_capability_dispatch_result returns."""
    from guardian.extensions.reinjection import (
        reinject_failed_manual_capability_dispatch_result,
    )

    return reinject_failed_manual_capability_dispatch_result(
        account_id=manual_result.account_id,
        manual_dispatch_result=manual_result,
    )


# ---------------------------------------------------------------------------
# Successful reinjection → normalized assistant continuation
# ---------------------------------------------------------------------------


def test_successful_reinjection_produces_normalized_continuation_payload(
    reentry_store,
):
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={
            "summary": "command result",
            "details": {"z": 2, "a": 1},
        },
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_successful_reinjection(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    assert isinstance(result, CapabilityAssistantReentryResult)
    assert result.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.SUCCESS.value
    )
    assert result.reentry_failure_reason_token is None
    assert result.is_success
    assert not result.is_failure
    assert not result.is_failed_closed

    payload = result.continuation_payload
    assert isinstance(payload, CapabilityAssistantContinuationPayload)
    assert payload.account_id == "acct-1"
    assert payload.proposal_id == proposal.proposal_id
    assert payload.registry_entry_id == registry_entry.registry_id
    assert payload.effective_binding_id == binding.binding_id
    assert payload.resolved_from_scope_token == binding.scope_token
    assert payload.manual_dispatch_id == "dispatch-123"
    assert payload.command_bus_run_id == "run-123"
    assert payload.manifest_snapshot_json is not None
    assert payload.manifest_snapshot_json["target_surface"] == (
        ExtensionTargetSurface.COMMAND_BUS.value
    )
    assert isinstance(payload.approved_permissions_json, list)
    assert payload.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.SUCCESS.value
    )
    assert payload.normalized_command_result_payload is not None
    assert payload.normalized_command_result_payload["status"] == "completed"
    assert payload.normalized_command_failure_payload is None

    # One reinjection → exactly one continuation payload
    assert result.continuation_payload is not None


def test_successful_reinjection_payload_is_structurally_ready_for_handoff(
    reentry_store,
):
    """The continuation payload is bounded and explicit, ready for completion lane."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "tool output"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_successful_reinjection(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    # Required fields are present
    p = result.continuation_payload
    assert p.account_id
    assert p.proposal_id
    assert p.registry_entry_id
    assert p.effective_binding_id
    assert p.manual_dispatch_id
    assert p.resolved_from_scope_token

    # No second dispatch implied
    assert p.continuation_metadata.get("reinjection_outcome") == "success"

    # Serializable
    serialized = p.to_payload()
    assert isinstance(serialized, dict)
    assert "account_id" in serialized
    assert "proposal_id" in serialized
    assert "manifest_snapshot_json" in serialized
    assert "continuation_metadata_json" in serialized


# ---------------------------------------------------------------------------
# Failed reinjection → bounded assistant continuation with explicit failure
# ---------------------------------------------------------------------------


def test_failed_reinjection_produces_bounded_continuation_payload_with_failure(
    reentry_store,
):
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="failed",
        error="command bus unavailable",
    )
    reinjection = _simulate_failed_reinjection(manual_result)

    result = reentry_from_failed_reinjection(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    assert result.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.FAILURE.value
    )
    assert result.reentry_failure_reason_token is None
    assert result.is_failure
    assert not result.is_success

    payload = result.continuation_payload
    assert isinstance(payload, CapabilityAssistantContinuationPayload)
    assert payload.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.FAILURE.value
    )
    assert payload.normalized_command_failure_payload is not None
    assert payload.normalized_command_failure_payload["error"] == (
        "command bus unavailable"
    )
    assert payload.normalized_command_result_payload is None


def test_failed_reinjection_preserves_lineage_in_continuation_payload(
    reentry_store,
):
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="failed",
        error="service unavailable",
    )
    reinjection = _simulate_failed_reinjection(manual_result)

    result = reentry_from_failed_reinjection(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    p = result.continuation_payload
    assert p.proposal_id == proposal.proposal_id
    assert p.registry_entry_id == registry_entry.registry_id
    assert p.effective_binding_id == binding.binding_id
    assert p.resolved_from_scope_token == binding.scope_token
    assert p.manual_dispatch_id == "dispatch-123"
    assert p.command_bus_run_id == "run-123"


# ---------------------------------------------------------------------------
# Owner / account isolation
# ---------------------------------------------------------------------------


def test_reentry_owner_account_isolation(
    reentry_store,
):
    """Owner mismatch triggers explicit failure, not silent fallback."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "command result"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-2",  # Wrong account
        reinjection_result=reinjection,
    )

    assert result.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
    )
    assert result.reentry_failure_reason_token == (
        CapabilityAssistantReentryFailureReason.OWNER_MISMATCH.value
    )
    assert result.is_failed_closed
    assert result.continuation_payload is not None
    assert result.continuation_payload.is_failed_closed


# ---------------------------------------------------------------------------
# Lineage preservation
# ---------------------------------------------------------------------------


def test_reinjection_lineage_preserved_in_reentry_result(
    reentry_store,
):
    """Proposal / registry / binding / manual-dispatch / command-bus linkage preserved."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "tool executed"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    # Proposal lineage
    assert result.proposal_id == proposal.proposal_id
    # Registry lineage
    assert result.registry_entry_id == registry_entry.registry_id
    # Binding lineage
    assert result.effective_binding_id == binding.binding_id

    p = result.continuation_payload
    assert p.manual_dispatch_id == "dispatch-123"
    assert p.command_bus_run_id == "run-123"
    # Manual dispatch linkage preserved in metadata
    assert p.manifest_snapshot_json is not None


def test_reinjection_source_preserved_through_reentry(
    reentry_store,
):
    """Reinjection source token is preserved in continuation metadata."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "ok"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    p = result.continuation_payload
    assert p.continuation_metadata.get("reinjection_source") == (
        CapabilityReinjectionSource.MANUAL_DISPATCH.value
    )


# ---------------------------------------------------------------------------
# Inconsistent provenance → fail closed
# ---------------------------------------------------------------------------


def test_inconsistent_reinjection_provenance_fails_closed(
    reentry_store,
):
    """Ambiguous / inconsistent reinjection provenance fails closed with explicit reason."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "ok"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    # Simulate an inconsistent reinjection: shape says success but outcome says unusable
    from guardian.extensions.contracts import CapabilityResultReinjectionResult

    # Create an inconsistent payload that won't match our expected patterns
    inconsistent_payload = {
        "request": reinjection.request.to_payload(),
        "reinjection_outcome_token": "unusable",
        "result_shape_token": CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value,
        "reinjection_source_token": CapabilityReinjectionSource.MANUAL_DISPATCH.value,
        "reinjection_failure_reason_token": None,
        "reinjected_output": reinjection.reinjected_output.to_payload(),
    }
    inconsistent_reinjection = CapabilityResultReinjectionResult.from_payload(
        inconsistent_payload
    )

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=inconsistent_reinjection,
    )

    assert result.reentry_outcome_token == (
        CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
    )
    assert result.reentry_failure_reason_token == (
        CapabilityAssistantReentryFailureReason.REINJECTION_RESULT_INCONSISTENT.value
    )
    assert result.is_failed_closed


# ---------------------------------------------------------------------------
# Deterministic normalization and payload shape
# ---------------------------------------------------------------------------


def test_reentry_deterministic_normalization(
    reentry_store,
):
    """Reentry produces deterministic output for the same input."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "deterministic", "value": 42},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result1 = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )
    result2 = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    # Same inputs → same outputs
    assert result1.to_payload() == result2.to_payload()
    assert result1.continuation_payload.to_payload() == (
        result2.continuation_payload.to_payload()
    )


def test_continuation_payload_shape_is_bounded(
    reentry_store,
):
    """Continuation payload is explicit and bounded."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "bounded"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    p = result.continuation_payload
    payload = p.to_payload()
    expected_keys = {
        "account_id",
        "proposal_id",
        "registry_entry_id",
        "effective_binding_id",
        "resolved_from_scope_token",
        "manual_dispatch_id",
        "command_bus_run_id",
        "requested_command_id",
        "manifest_snapshot_json",
        "approved_permissions_json",
        "reentry_outcome_token",
        "reentry_failure_reason_token",
        "normalized_command_result_payload",
        "normalized_command_failure_payload",
        "continuation_metadata_json",
    }
    assert set(payload.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Side-effect free
# ---------------------------------------------------------------------------


def test_reentry_is_side_effect_free_and_does_not_mutate_state(
    reentry_store,
    monkeypatch: pytest.MonkeyPatch,
):
    """Reentry does not call command bus, does not invoke provider, does not persist."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "side-effect check"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    # Capture state before reentry
    before_state = {
        "proposal": store.get_proposal_by_id(
            account_id="acct-1", proposal_id=proposal.proposal_id
        ),
        "decision": store.get_install_gate_decision_by_id(
            account_id="acct-1", decision_id=_decision.decision_id
        ),
        "registry": store.get_registry_entry_by_id(
            account_id="acct-1", registry_id=registry_entry.registry_id
        ),
        "binding": store.get_binding_by_id(
            account_id="acct-1", binding_id=binding.binding_id
        ),
    }

    # Block command bus
    fake_command_bus_invoke = types.SimpleNamespace(
        execute_invoke=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("command bus must not be called in reentry")
        )
    )
    monkeypatch.setitem(
        sys.modules, "guardian.command_bus.invoke", fake_command_bus_invoke
    )

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    # State unchanged
    after_state = {
        "proposal": store.get_proposal_by_id(
            account_id="acct-1", proposal_id=proposal.proposal_id
        ),
        "decision": store.get_install_gate_decision_by_id(
            account_id="acct-1", decision_id=_decision.decision_id
        ),
        "registry": store.get_registry_entry_by_id(
            account_id="acct-1", registry_id=registry_entry.registry_id
        ),
        "binding": store.get_binding_by_id(
            account_id="acct-1", binding_id=binding.binding_id
        ),
    }

    assert before_state == after_state
    assert result.proposal_id == proposal.proposal_id
    assert result.registry_entry_id == registry_entry.registry_id
    assert result.effective_binding_id == binding.binding_id


# ---------------------------------------------------------------------------
# General entry point (handles both success and failure)
# ---------------------------------------------------------------------------


def test_general_reentry_entry_point_handles_success(
    reentry_store,
):
    """reentry_from_reinjection_result handles successful reinjection correctly."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "general success"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    assert result.is_success
    assert result.continuation_payload.is_success


def test_general_reentry_entry_point_handles_failure(
    reentry_store,
):
    """reentry_from_reinjection_result handles failed reinjection correctly."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="failed",
        error="service error",
    )
    reinjection = _simulate_failed_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    assert result.is_failure
    assert result.continuation_payload.is_failure


# ---------------------------------------------------------------------------
# One reinjection → exactly one continuation payload
# ---------------------------------------------------------------------------


def test_one_reinjection_yields_exactly_one_continuation_payload(
    reentry_store,
):
    """The seam produces exactly one continuation payload, never more."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "one payload"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_successful_reinjection(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    # Exactly one continuation payload
    assert result.continuation_payload is not None
    # Cannot call reentry again on the result and expect two payloads
    # (this is enforced by the dataclass invariant - one result object)
    result_payload = result.to_payload()
    assert result_payload["continuation_payload_json"] is not None
    # The continuation payload itself cannot contain a list of payloads
    assert not isinstance(result.continuation_payload, list)


def test_reentry_result_serialization_round_trips(
    reentry_store,
):
    """Reentry result round-trips through to_payload / from_payload."""
    store, gate, registry, bindings = reentry_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store, gate, account_id="acct-1", manifest=manifest
    )
    binding = _bound_registry_entry(
        bindings,
        account_id="acct-1",
        registry_entry=registry_entry,
        project_id=17,
    )
    manual_result = _manual_dispatch_result(
        account_id="acct-1",
        proposal=proposal,
        registry_entry=registry_entry,
        binding=binding,
        status="completed",
        inline_result={"summary": "round trip"},
    )
    reinjection = _simulate_successful_reinjection(manual_result)

    result = reentry_from_reinjection_result(
        account_id="acct-1",
        reinjection_result=reinjection,
    )

    payload = result.to_payload()
    restored = CapabilityAssistantReentryResult.from_payload(payload)

    assert restored.account_id == result.account_id
    assert restored.proposal_id == result.proposal_id
    assert restored.registry_entry_id == result.registry_entry_id
    assert restored.effective_binding_id == result.effective_binding_id
    assert restored.reentry_outcome_token == result.reentry_outcome_token
    assert restored.continuation_payload is not None
