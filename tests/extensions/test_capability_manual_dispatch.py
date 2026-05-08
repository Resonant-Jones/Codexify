from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import guardian.extensions.dispatch as dispatch_module
from guardian.command_bus.contracts import InvokeArguments
from guardian.db.models import (
    AgentExtensionInstallBinding,
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
    Base,
)
from guardian.extensions.activation import activate_capability_for_owner_only
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
    CapabilityExposedCommand,
    CapabilityManualDispatchOutcomeToken,
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.dispatch import (
    manual_dispatch_capability_for_owner_and_profile,
    manual_dispatch_capability_for_owner_and_project,
    manual_dispatch_capability_for_owner_only,
    manual_dispatch_capability_for_owner_project_profile,
    manual_dispatch_capability_from_envelope,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.resolver import EffectiveCapabilityResolver
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationDenyReasonToken,
    CapabilityManualDispatchSourceToken,
    ExtensionInstallBindingScope,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)

COMMAND_ID = "command::activate-alpha"
OTHER_COMMAND_ID = "command::activate-beta"


def _requested_permissions() -> tuple[ExtensionRequestedPermission, ...]:
    return (
        ExtensionRequestedPermission(
            permission="command.run",
            resource="command_bus",
            reason="bounded command execution",
        ),
    )


@pytest.fixture()
def manual_dispatch_store():
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
    resolver = EffectiveCapabilityResolver(store)
    return store, gate, registry, bindings, resolver


def _manifest(
    *,
    target_surface: str,
    scope: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    source_thread_id: int | None = 41,
    source_message_id: int | None = 42,
    exposed_command_ids: tuple[str, ...] = (COMMAND_ID,),
    requested_permissions: tuple[ExtensionRequestedPermission, ...]
    | None = None,
) -> ExtensionProposalManifest:
    return ExtensionProposalManifest(
        target_surface=target_surface,
        scope=scope,
        project_id=project_id,
        profile_id=profile_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        summary="Generate a bounded tool plugin",
        description="Draft a tool proposal without executing it.",
        requested_permissions=requested_permissions or _requested_permissions(),
        declared_dependencies=(
            ExtensionDeclaredDependency(
                name="httpx",
                version_spec=">=0.28",
                source="pypi",
            ),
        ),
        exposed_commands=tuple(
            CapabilityExposedCommand(
                command_id=command_id,
                tool_aliases=(),
            )
            for command_id in exposed_command_ids
        ),
        rollback_metadata=ExtensionRollbackMetadata(
            strategy="disable_and_revert",
            rollback_ref="ticket-123",
        ),
        test_evidence_metadata=ExtensionTestEvidenceMetadata(
            status="passing",
            summary="manual dispatch contract coverage",
            artifacts=("tests/extensions/test_capability_manual_dispatch.py",),
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


def _bind_scope(
    bindings: ExtensionInstallBindings,
    registry_entry,
    *,
    account_id: str,
    scope_token: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    account_scope_target_id: str | None = "account-target-1",
):
    return bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id=account_id,
            registry_entry_id=registry_entry.registry_id,
            scope_token=scope_token,
            project_id=project_id,
            profile_id=profile_id,
            account_scope_target_id=account_scope_target_id,
        )
    )


def _bind_all_scopes(
    bindings: ExtensionInstallBindings,
    registry_entry,
    *,
    account_id: str,
    project_id: int | None = None,
    profile_id: str | None = None,
):
    bound = {}
    if project_id is not None:
        bound["project"] = _bind_scope(
            bindings,
            registry_entry,
            account_id=account_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=project_id,
            account_scope_target_id=None,
        )
    if profile_id is not None:
        bound["profile"] = _bind_scope(
            bindings,
            registry_entry,
            account_id=account_id,
            scope_token=ExtensionInstallBindingScope.PROFILE.value,
            profile_id=profile_id,
            account_scope_target_id=None,
        )
    bound["account"] = _bind_scope(
        bindings,
        registry_entry,
        account_id=account_id,
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id=f"{account_id}-target",
    )
    return bound


def _patch_execute_invoke(monkeypatch, *, status: str = "completed"):
    calls: list[dict[str, object]] = []

    async def _execute_invoke(*, payload, **kwargs):
        calls.append({"payload": payload, "kwargs": kwargs})
        return {
            "run_id": "run-123",
            "status": status,
            "invoke_version": payload.invoke_version,
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-123/events?after_seq=0",
            "inline_result": {"ok": True},
            "policy_warnings": [],
        }

    monkeypatch.setattr(dispatch_module, "execute_invoke", _execute_invoke)
    return calls


def test_account_context_manual_dispatch_succeeds_when_activation_allows(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    account_binding = _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-1",
            requested_command_id=COMMAND_ID,
            command_arguments=InvokeArguments(
                body={"payload": "account-dispatch"}
            ),
            requested_permissions=_requested_permissions(),
            resolver=resolver,
            request_metadata={"source": "test"},
            idempotency_key="dispatch-1",
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DISPATCHED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.selected_match is not None
    assert result.activation_decision.selected_match.binding_id == (
        account_binding.binding_id
    )
    assert result.dispatch_envelope is not None
    assert result.dispatch_envelope.proposal_id == proposal.proposal_id
    assert result.command_bus_request is not None
    assert result.command_bus_request.actor.id == "acct-1"
    assert result.command_bus_request.idempotency_key == "dispatch-1"
    assert (
        result.command_bus_request.provenance_json[
            "manual_dispatch_source_token"
        ]
        == CapabilityManualDispatchSourceToken.MANUAL_CAPABILITY_DISPATCH.value
    )
    assert (
        result.command_bus_request.provenance_json[
            "capability_dispatch_envelope_json"
        ]["binding_id"]
        == account_binding.binding_id
    )
    assert result.command_bus_result is not None
    assert result.command_bus_result.status == "completed"
    assert result.command_run_id == "run-123"
    assert len(calls) == 1


def test_project_context_manual_dispatch_uses_project_precedence(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.PROJECT.value,
            project_id=17,
        ),
    )
    scoped = _bind_all_scopes(
        bindings,
        registry_entry,
        account_id="acct-1",
        project_id=17,
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_and_project(
            account_id="acct-1",
            project_id=17,
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "project-dispatch"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DISPATCHED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.selected_match is not None
    assert result.activation_decision.selected_match.binding_id == (
        scoped["project"].binding_id
    )
    assert result.dispatch_envelope is not None
    assert result.dispatch_envelope.binding_id == scoped["project"].binding_id
    assert result.dispatch_envelope.proposal_id == proposal.proposal_id
    assert len(calls) == 1


def test_profile_context_manual_dispatch_uses_profile_precedence(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.PROFILE.value,
            profile_id="profile-alpha",
        ),
    )
    scoped = _bind_all_scopes(
        bindings,
        registry_entry,
        account_id="acct-1",
        project_id=17,
        profile_id="profile-alpha",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_and_profile(
            account_id="acct-1",
            profile_id="profile-alpha",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "profile-dispatch"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DISPATCHED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.selected_match is not None
    assert result.activation_decision.selected_match.binding_id == (
        scoped["profile"].binding_id
    )
    assert result.dispatch_envelope is not None
    assert result.dispatch_envelope.binding_id == scoped["profile"].binding_id
    assert len(calls) == 1


def test_combined_project_profile_context_respects_profile_precedence(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.PROJECT.value,
            project_id=17,
        ),
    )
    scoped = _bind_all_scopes(
        bindings,
        registry_entry,
        account_id="acct-1",
        project_id=17,
        profile_id="profile-alpha",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_project_profile(
            account_id="acct-1",
            project_id=17,
            profile_id="profile-alpha",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "profile-wins"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DISPATCHED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.selected_match is not None
    assert result.activation_decision.selected_match.binding_id == (
        scoped["profile"].binding_id
    )
    assert result.dispatch_envelope is not None
    assert result.dispatch_envelope.binding_id == scoped["profile"].binding_id
    assert len(calls) == 1


def test_missing_project_profile_context_does_not_widen_into_scoped_bindings(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    project_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.PROJECT.value,
            project_id=17,
        ),
    )[2]
    profile_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.PROFILE.value,
            profile_id="profile-alpha",
        ),
    )[2]
    _bind_scope(
        bindings,
        project_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.PROJECT.value,
        project_id=17,
        account_scope_target_id=None,
    )
    _bind_scope(
        bindings,
        profile_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.PROFILE.value,
        profile_id="profile-alpha",
        account_scope_target_id=None,
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-1",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "narrow"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DENIED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )
    assert len(calls) == 0


def test_denied_when_no_effective_capability_exposes_requested_command(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(OTHER_COMMAND_ID,),
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-1",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "missing"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DENIED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )
    assert result.command_bus_request is None
    assert len(calls) == 0


def test_denied_when_approved_permissions_are_insufficient(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-1",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "elevated"}},
            requested_permissions=(
                ExtensionRequestedPermission(
                    permission="command.admin",
                    resource="command_bus",
                    reason="requires elevated permission",
                ),
            ),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DENIED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
    )
    assert result.command_bus_request is None
    assert len(calls) == 0


def test_owner_account_isolation_blocks_other_accounts(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-2",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "wrong-owner"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DENIED.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )
    assert len(calls) == 0


def test_manual_dispatch_from_allowed_envelope_invokes_command_bus_once_and_preserves_lineage(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    account_binding = _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    activation = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        requested_permissions=_requested_permissions(),
        resolver=resolver,
    )
    assert activation.dispatch_envelope is not None
    calls = _patch_execute_invoke(monkeypatch)
    registry_before = store.list_registry_entries(account_id="acct-1")
    bindings_before = store.list_bindings(account_id="acct-1")

    result = asyncio.run(
        manual_dispatch_capability_from_envelope(
            account_id="acct-1",
            dispatch_envelope=activation.dispatch_envelope,
            command_arguments=InvokeArguments(
                body={"payload": "from-envelope"}
            ),
            requested_permissions=_requested_permissions(),
            request_metadata={"source": "envelope"},
            idempotency_key="dispatch-envelope-1",
            source_thread_id=99,
            source_message_id=100,
        )
    )

    registry_after = store.list_registry_entries(account_id="acct-1")
    bindings_after = store.list_bindings(account_id="acct-1")

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.DISPATCHED.value
    )
    assert result.dispatch_envelope is not None
    assert result.dispatch_envelope.proposal_id == proposal.proposal_id
    assert result.dispatch_envelope.binding_id == account_binding.binding_id
    assert result.command_bus_request is not None
    assert (
        result.command_bus_request.provenance_json[
            "manual_dispatch_source_token"
        ]
        == CapabilityManualDispatchSourceToken.MANUAL_CAPABILITY_DISPATCH.value
    )
    assert (
        result.command_bus_request.provenance_json[
            "capability_dispatch_envelope_json"
        ]["proposal_id"]
        == proposal.proposal_id
    )
    assert (
        result.command_bus_request.provenance_json[
            "capability_dispatch_envelope_json"
        ]["binding_id"]
        == account_binding.binding_id
    )
    assert result.command_bus_request.arguments.body == {
        "payload": "from-envelope"
    }
    assert result.command_bus_result is not None
    assert result.command_bus_result.run_id == "run-123"
    assert result.command_run_id == "run-123"
    assert len(calls) == 1
    assert registry_after == registry_before
    assert bindings_after == bindings_before


def test_ambiguous_same_command_exposure_fails_closed_before_command_bus(
    manual_dispatch_store, monkeypatch
):
    store, gate, registry, bindings, resolver = manual_dispatch_store
    first_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(COMMAND_ID,),
        ),
    )[2]
    second_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(COMMAND_ID,),
        ),
    )[2]
    first_binding = _bind_scope(
        bindings,
        first_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    second_binding = _bind_scope(
        bindings,
        second_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-2",
    )
    calls = _patch_execute_invoke(monkeypatch)

    result = asyncio.run(
        manual_dispatch_capability_for_owner_only(
            account_id="acct-1",
            requested_command_id=COMMAND_ID,
            command_arguments={"body": {"payload": "ambiguous"}},
            requested_permissions=_requested_permissions(),
            resolver=resolver,
        )
    )

    assert result.outcome_token == (
        CapabilityManualDispatchOutcomeToken.CONFLICT.value
    )
    assert result.activation_decision is not None
    assert result.activation_decision.conflict_class_token == (
        CapabilityActivationConflictClassToken.SAME_COMMAND_EXPOSURE.value
    )
    assert [
        match.binding_id
        for match in result.activation_decision.conflict_details[
            0
        ].candidate_matches
    ] == [
        first_binding.binding_id,
        second_binding.binding_id,
    ]
    assert [
        match.target_surface_token
        for match in result.activation_decision.conflict_details[
            0
        ].candidate_matches
    ] == [
        ExtensionTargetSurface.COMMAND_BUS.value,
        ExtensionTargetSurface.PERSONA_STUDIO.value,
    ]
    assert result.command_bus_request is None
    assert len(calls) == 0
