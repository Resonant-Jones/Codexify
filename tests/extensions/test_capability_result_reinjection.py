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
    CapabilityResultReinjectionResult,
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.reinjection import (
    reinject_capability_manual_dispatch_result,
    reinject_failed_manual_capability_dispatch_result,
    reinject_successful_manual_capability_dispatch_result,
)
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityReinjectionFailureReason,
    CapabilityReinjectionResultShape,
    CapabilityResultReinjectionOutcome,
    CapabilityReinjectionSource,
    ExtensionInstallBindingScope,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)


@pytest.fixture()
def reinjection_store():
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
                permission="zeta.write",
                resource="command_bus",
                reason="second permission to test sorting",
            ),
            ExtensionRequestedPermission(
                permission="alpha.read",
                resource="command_bus",
                reason="first permission to test sorting",
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
            summary="reinjection coverage",
            artifacts=(
                "tests/extensions/test_capability_result_reinjection.py",
            ),
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
    command_bus_overrides: dict[str, Any] | None = None,
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
    if command_bus_overrides:
        result_payload.update(command_bus_overrides)

    approved_permissions = [
        permission.to_payload()
        for permission in reversed(registry_entry.approved_permissions)
    ]
    if not approved_permissions:
        approved_permissions = [
            permission.to_payload()
            for permission in reversed(proposal.requested_permissions)
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


def test_successful_manual_dispatch_result_reinjects_into_normalized_success_output(
    reinjection_store,
):
    store, gate, registry, bindings = reinjection_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=manifest,
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
        inline_result={"summary": "command result", "details": {"z": 2, "a": 1}},
    )

    result = reinject_successful_manual_capability_dispatch_result(
        account_id="acct-1",
        manual_dispatch_result=manual_result,
    )

    assert isinstance(result, CapabilityResultReinjectionResult)
    assert result.reinjection_outcome_token == (
        CapabilityResultReinjectionOutcome.SUCCESS.value
    )
    assert result.result_shape_token == (
        CapabilityReinjectionResultShape.NORMALIZED_SUCCESS.value
    )
    assert result.reinjection_source_token == (
        CapabilityReinjectionSource.MANUAL_DISPATCH.value
    )
    assert result.reinjection_failure_reason_token is None
    assert result.proposal_id == proposal.proposal_id
    assert result.registry_entry_id == registry_entry.registry_id
    assert result.effective_binding_id == binding.binding_id
    assert result.resolved_from_scope_token == binding.scope_token
    assert result.manual_dispatch_id == "dispatch-123"
    assert result.command_bus_run_id == "run-123"
    assert result.manifest_snapshot == manifest
    assert [perm.permission for perm in result.approved_permissions] == [
        "alpha.read",
        "zeta.write",
    ]
    assert result.normalized_command_result_payload["status"] == "completed"
    assert (
        result.normalized_command_result_payload["inline_result"]["details"][
            "a"
        ]
        == 1
    )
    assert result.normalized_command_failure_payload is None

    payload = result.to_payload()
    assert list(payload.keys()) == [
        "request",
        "reinjection_outcome_token",
        "result_shape_token",
        "reinjection_source_token",
        "reinjection_failure_reason_token",
        "reinjected_output",
    ]
    assert list(payload["reinjected_output"].keys()) == [
        "account_id",
        "proposal_id",
        "registry_entry_id",
        "effective_binding_id",
        "resolved_from_scope_token",
        "manual_dispatch_id",
        "command_bus_run_id",
        "manifest_snapshot_json",
        "approved_permissions_json",
        "reinjection_source_token",
        "reinjection_outcome_token",
        "result_shape_token",
        "normalized_command_result_payload",
        "normalized_command_failure_payload",
        "reinjection_failure_reason_token",
    ]


def test_failed_manual_dispatch_result_reinjects_into_normalized_failure_output(
    reinjection_store,
):
    store, gate, registry, bindings = reinjection_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=manifest,
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

    result = reinject_failed_manual_capability_dispatch_result(
        account_id="acct-1",
        manual_dispatch_result=manual_result,
    )

    assert result.reinjection_outcome_token == (
        CapabilityResultReinjectionOutcome.FAILURE.value
    )
    assert result.result_shape_token == (
        CapabilityReinjectionResultShape.NORMALIZED_FAILURE.value
    )
    assert result.reinjection_source_token == (
        CapabilityReinjectionSource.MANUAL_DISPATCH.value
    )
    assert result.reinjection_failure_reason_token is None
    assert result.normalized_command_result_payload is None
    assert result.normalized_command_failure_payload["status"] == "failed"
    assert result.normalized_command_failure_payload["error"] == (
        "command bus unavailable"
    )


def test_reinjection_owner_account_isolation(
    reinjection_store,
):
    store, gate, registry, bindings = reinjection_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=manifest,
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

    result = reinject_capability_manual_dispatch_result(
        account_id="acct-2",
        manual_dispatch_result=manual_result,
    )

    assert result.reinjection_outcome_token == (
        CapabilityResultReinjectionOutcome.UNUSABLE.value
    )
    assert result.result_shape_token == (
        CapabilityReinjectionResultShape.FAILED_CLOSED.value
    )
    assert result.reinjection_failure_reason_token == (
        CapabilityReinjectionFailureReason.OWNER_MISMATCH.value
    )
    assert result.reinjected_output.normalized_command_result_payload is None
    assert result.reinjected_output.normalized_command_failure_payload is None


def test_reinjection_preserves_lineage_and_is_side_effect_free(
    reinjection_store,
    monkeypatch: pytest.MonkeyPatch,
):
    store, gate, registry, bindings = reinjection_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=manifest,
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

    fake_command_bus_invoke = types.SimpleNamespace(
        execute_invoke=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("command bus should not be reinvoked")
        )
    )
    monkeypatch.setitem(
        sys.modules, "guardian.command_bus.invoke", fake_command_bus_invoke
    )

    result = reinject_capability_manual_dispatch_result(
        account_id="acct-1",
        manual_dispatch_result=manual_result,
    )

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
    assert result.manual_dispatch_id == manual_result.manual_dispatch_id
    assert result.command_bus_run_id == manual_result.command_bus_run_id
    assert result.reinjected_output.account_id == "acct-1"


def test_reinjection_incomplete_command_bus_result_fails_closed(
    reinjection_store,
):
    store, gate, registry, bindings = reinjection_store
    manifest = _manifest(
        target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
        scope=ExtensionProposalScope.PROJECT.value,
        project_id=17,
    )
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=manifest,
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
        inline_result=None,
    )

    result = reinject_capability_manual_dispatch_result(
        account_id="acct-1",
        manual_dispatch_result=manual_result,
    )

    assert result.reinjection_outcome_token == (
        CapabilityResultReinjectionOutcome.UNUSABLE.value
    )
    assert result.result_shape_token == (
        CapabilityReinjectionResultShape.FAILED_CLOSED.value
    )
    assert result.reinjection_failure_reason_token == (
        CapabilityReinjectionFailureReason.MISSING_INLINE_RESULT.value
    )
    assert result.reinjected_output.normalized_command_result_payload is None
    assert result.reinjected_output.normalized_command_failure_payload is None
