from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    AgentExtensionInstallBinding,
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
    Base,
)
from guardian.extensions.activation import (
    activate_capability_for_owner_and_profile,
    activate_capability_for_owner_and_project,
    activate_capability_for_owner_only,
    activate_capability_for_owner_project_profile,
)
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationDenyReasonToken,
    CapabilityActivationOutcomeToken,
    CapabilityExposedCommand,
    CapabilityRegistryEntry,
    EffectiveCapabilityRecord,
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.resolver import EffectiveCapabilityResolver
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityRegistryStatus,
    ExtensionInstallBindingScope,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)

COMMAND_ID = "command::activate-alpha"
COMMAND_ALIAS = "command::activate-alpha-alias"
OTHER_COMMAND_ID = "command::activate-beta"


@pytest.fixture()
def activation_store():
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
        requested_permissions=requested_permissions
        or (
            ExtensionRequestedPermission(
                permission="command.run",
                resource="command_bus",
                reason="bounded command execution",
            ),
        ),
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
                tool_aliases=(
                    (COMMAND_ALIAS,) if command_id == COMMAND_ID else ()
                ),
            )
            for command_id in exposed_command_ids
        ),
        rollback_metadata=ExtensionRollbackMetadata(
            strategy="disable_and_revert",
            rollback_ref="ticket-123",
        ),
        test_evidence_metadata=ExtensionTestEvidenceMetadata(
            status="passing",
            summary="activation contract coverage",
            artifacts=(
                "tests/extensions/test_capability_activation_contract.py",
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


def test_account_context_activation_succeeds_for_account_scoped_capability(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
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

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert decision.dispatch_envelope is not None
    assert decision.selected_match is not None
    assert decision.selected_match.binding_id == account_binding.binding_id
    assert decision.dispatch_envelope.owner_account_id == "acct-1"
    assert decision.dispatch_envelope.requested_command_id == COMMAND_ID
    assert decision.dispatch_envelope.command_id == COMMAND_ID
    assert decision.dispatch_envelope.proposal_id == _proposal.proposal_id
    assert (
        decision.dispatch_envelope.registry_entry_id
        == registry_entry.registry_id
    )
    assert decision.dispatch_envelope.binding_id == account_binding.binding_id
    assert decision.dispatch_envelope.resolved_from_scope_token == (
        ExtensionInstallBindingScope.ACCOUNT.value
    )


def test_project_context_activation_prefers_project_effective_over_account_effective(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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
    )

    decision = activate_capability_for_owner_and_project(
        account_id="acct-1",
        project_id=17,
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert decision.selected_match is not None
    assert decision.selected_match.binding_id == scoped["project"].binding_id
    assert decision.selected_match.resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROJECT.value
    )
    assert decision.dispatch_envelope is not None
    assert decision.dispatch_envelope.binding_id == scoped["project"].binding_id


def test_profile_context_activation_prefers_profile_effective_over_project_account(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_and_profile(
        account_id="acct-1",
        profile_id="profile-alpha",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert decision.selected_match is not None
    assert decision.selected_match.binding_id == scoped["profile"].binding_id
    assert decision.selected_match.resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROFILE.value
    )


def test_combined_project_profile_context_respects_profile_over_project_account(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_project_profile(
        account_id="acct-1",
        project_id=17,
        profile_id="profile-alpha",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert decision.selected_match is not None
    assert decision.selected_match.binding_id == scoped["profile"].binding_id
    assert decision.selected_match.resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROFILE.value
    )


def test_missing_project_profile_context_does_not_widen_into_scoped_bindings(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )


def test_denied_when_no_effective_capability_exposes_requested_command(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )
    assert decision.dispatch_envelope is None


def test_denied_when_approved_permissions_are_insufficient(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            requested_permissions=(
                ExtensionRequestedPermission(
                    permission="command.run",
                    resource="command_bus",
                    reason="bounded command execution",
                ),
            ),
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        requested_permissions=(
            ExtensionRequestedPermission(
                permission="command.admin",
                resource="command_bus",
                reason="requires elevated permission",
            ),
        ),
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
    )
    assert decision.candidate_matches
    assert decision.dispatch_envelope is None


def test_owner_account_isolation_blocks_other_accounts(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_only(
        account_id="acct-2",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert decision.denial_reason_token == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )


def test_activation_preserves_lineage_in_decision_and_dispatch_envelope(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
    proposal, decision_row, registry_entry = _approved_registry_entry(
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

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert decision.request.account_id == "acct-1"
    assert decision.selected_match is not None
    assert decision.selected_match.proposal_id == proposal.proposal_id
    assert (
        decision.selected_match.registry_entry_id == registry_entry.registry_id
    )
    assert decision.selected_match.binding_id == account_binding.binding_id
    assert (
        decision.selected_match.manifest_snapshot
        == registry_entry.manifest_snapshot
    )
    assert (
        decision.selected_match.approved_permissions
        == registry_entry.approved_permissions
    )
    assert decision.dispatch_envelope is not None
    assert decision.dispatch_envelope.proposal_id == proposal.proposal_id
    assert (
        decision.dispatch_envelope.registry_entry_id
        == registry_entry.registry_id
    )
    assert decision.dispatch_envelope.binding_id == account_binding.binding_id
    assert (
        decision.dispatch_envelope.manifest_snapshot
        == registry_entry.manifest_snapshot
    )
    assert (
        decision.dispatch_envelope.approved_permissions
        == registry_entry.approved_permissions
    )


def test_activation_deterministic_ordering_for_conflicts(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token
        == CapabilityActivationOutcomeToken.CONFLICT.value
    )
    assert decision.conflict_details
    assert [
        match.binding_id
        for match in decision.conflict_details[0].candidate_matches
    ] == [
        first_binding.binding_id,
        second_binding.binding_id,
    ]
    assert [
        match.target_surface_token
        for match in decision.conflict_details[0].candidate_matches
    ] == [
        ExtensionTargetSurface.COMMAND_BUS.value,
        ExtensionTargetSurface.PERSONA_STUDIO.value,
    ]


def test_ambiguous_same_command_exposure_fails_closed_with_conflict(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
    first_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )[2]
    second_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )[2]

    _bind_scope(
        bindings,
        first_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    _bind_scope(
        bindings,
        second_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-2",
    )

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    assert (
        decision.outcome_token
        == CapabilityActivationOutcomeToken.CONFLICT.value
    )
    assert decision.conflict_class_token == (
        CapabilityActivationConflictClassToken.SAME_COMMAND_EXPOSURE.value
    )
    assert decision.dispatch_envelope is None
    assert decision.conflict_details[0].candidate_matches


def test_activation_is_side_effect_free(
    activation_store,
):
    store, gate, registry, bindings, resolver = activation_store
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

    registry_before = store.list_registry_entries(account_id="acct-1")
    bindings_before = store.list_bindings(account_id="acct-1")

    decision = activate_capability_for_owner_only(
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        resolver=resolver,
    )

    registry_after = store.list_registry_entries(account_id="acct-1")
    bindings_after = store.list_bindings(account_id="acct-1")

    assert (
        decision.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert registry_after == registry_before
    assert bindings_after == bindings_before
    assert (
        store.get_registry_entry_by_id(
            account_id="acct-1", registry_id=registry_entry.registry_id
        )
        == registry_entry
    )
