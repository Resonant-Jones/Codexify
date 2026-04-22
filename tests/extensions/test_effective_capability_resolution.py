from __future__ import annotations

from dataclasses import replace

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
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
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
from guardian.extensions.resolver import (
    EffectiveCapabilityResolutionError,
    EffectiveCapabilityResolver,
)
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityRegistryStatus,
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)


@pytest.fixture()
def effective_resolution_store():
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
        requested_permissions=(
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
        rollback_metadata=ExtensionRollbackMetadata(
            strategy="disable_and_revert",
            rollback_ref="ticket-123",
        ),
        test_evidence_metadata=ExtensionTestEvidenceMetadata(
            status="passing",
            summary="effective capability coverage",
            artifacts=(
                "tests/extensions/test_effective_capability_resolution.py",
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


def _bind_all_scopes(
    bindings: ExtensionInstallBindings,
    registry_entry,
    *,
    account_id: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    account_scope_target_id: str | None = "account-target-1",
):
    bound = {}
    if project_id is not None:
        bound["project"] = bindings.bind_registry_entry_to_scope(
            binding=ExtensionInstallBinding(
                account_id=account_id,
                registry_entry_id=registry_entry.registry_id,
                scope_token=ExtensionInstallBindingScope.PROJECT.value,
                project_id=project_id,
            )
        )
    if profile_id is not None:
        bound["profile"] = bindings.bind_registry_entry_to_scope(
            binding=ExtensionInstallBinding(
                account_id=account_id,
                registry_entry_id=registry_entry.registry_id,
                scope_token=ExtensionInstallBindingScope.PROFILE.value,
                profile_id=profile_id,
            )
        )
    if account_scope_target_id is not None:
        bound["account"] = bindings.bind_registry_entry_to_scope(
            binding=ExtensionInstallBinding(
                account_id=account_id,
                registry_entry_id=registry_entry.registry_id,
                scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
                account_scope_target_id=account_scope_target_id,
            )
        )
    return bound


def test_effective_resolution_owner_only_returns_account_bindings_only(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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

    snapshot = resolver.resolve_effective_capabilities_for_owner(
        account_id="acct-1"
    )

    assert snapshot.account_id == "acct-1"
    assert snapshot.project_id is None
    assert snapshot.profile_id is None
    assert [record.binding_id for record in snapshot.records] == [
        scoped["account"].binding_id
    ]
    assert snapshot.records[0].binding_scope_token == (
        ExtensionInstallBindingScope.ACCOUNT.value
    )


def test_effective_resolution_project_prefers_project_over_account(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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

    snapshot = resolver.resolve_effective_capabilities_for_owner_and_project(
        account_id="acct-1",
        project_id=17,
    )

    assert [record.binding_id for record in snapshot.records] == [
        scoped["project"].binding_id
    ]
    assert snapshot.records[0].resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROJECT.value
    )


def test_effective_resolution_profile_prefers_profile_over_project_account(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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

    snapshot = resolver.resolve_effective_capabilities_for_owner_and_profile(
        account_id="acct-1",
        profile_id="profile-alpha",
    )

    assert [record.binding_id for record in snapshot.records] == [
        scoped["profile"].binding_id
    ]
    assert snapshot.records[0].resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROFILE.value
    )


def test_effective_resolution_project_profile_prefers_profile_over_project_account(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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

    snapshot = (
        resolver.resolve_effective_capabilities_for_owner_project_profile(
            account_id="acct-1",
            project_id=17,
            profile_id="profile-alpha",
        )
    )

    assert [record.binding_id for record in snapshot.records] == [
        scoped["profile"].binding_id
    ]
    assert snapshot.records[0].resolved_from_scope_token == (
        ExtensionInstallBindingScope.PROFILE.value
    )


def test_effective_resolution_missing_context_does_not_activate_scoped_bindings(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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

    bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=project_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )
    bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=profile_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROFILE.value,
            profile_id="profile-alpha",
        )
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner(
        account_id="acct-1"
    )
    assert snapshot.records == ()


def test_effective_resolution_inactive_unbound_bindings_excluded(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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
    record = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )
    bindings.unbind_existing_binding(
        account_id="acct-1",
        binding_id=record.binding_id,
        reason="no longer needed",
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner_and_project(
        account_id="acct-1",
        project_id=17,
    )
    assert snapshot.records == ()


def test_effective_resolution_inactive_registry_entries_excluded(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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
    bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )
    registry.update_registry_status(
        account_id="acct-1",
        registry_id=registry_entry.registry_id,
        status=CapabilityRegistryStatus.SUSPENDED.value,
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner_and_project(
        account_id="acct-1",
        project_id=17,
    )
    assert snapshot.records == ()


def test_effective_resolution_owner_isolation(effective_resolution_store):
    store, gate, registry, bindings, resolver = effective_resolution_store
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
    bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner(
        account_id="acct-2"
    )
    assert snapshot.records == ()


def test_effective_resolution_preserves_lineage_snapshots(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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
    binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner_and_project(
        account_id="acct-1",
        project_id=17,
    )

    assert len(snapshot.records) == 1
    record = snapshot.records[0]
    assert record.registry_entry == registry_entry
    assert record.binding == binding
    assert record.manifest_snapshot.source_thread_id == 41
    assert record.manifest_snapshot.source_message_id == 42
    assert record.source_thread_id == 41
    assert record.source_message_id == 42
    assert record.provenance_json["source_thread_id"] == 41
    assert record.bind_metadata["source_thread_id"] == 41
    assert EffectiveCapabilityRecord.from_payload(record.to_payload()) == record
    assert snapshot == snapshot.__class__.from_payload(snapshot.to_payload())


def test_effective_resolution_deterministic_ordering(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
    first_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.PROJECT.value,
            project_id=17,
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

    first_binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=first_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
            account_scope_target_id="account-target-1",
        )
    )
    second_binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=second_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
            account_scope_target_id="account-target-2",
        )
    )

    snapshot = resolver.resolve_effective_capabilities_for_owner(
        account_id="acct-1"
    )

    assert [record.target_surface_token for record in snapshot.records] == [
        ExtensionTargetSurface.COMMAND_BUS.value,
        ExtensionTargetSurface.PERSONA_STUDIO.value,
    ]
    assert [record.binding_id for record in snapshot.records] == [
        first_binding.binding_id,
        second_binding.binding_id,
    ]


def test_effective_resolution_duplicate_same_precedence_fails_closed(
    effective_resolution_store,
):
    store, gate, registry, bindings, resolver = effective_resolution_store
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
    binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )
    duplicate = replace(binding, binding_id="binding-duplicate")

    def _duplicate_bindings(**_kwargs):
        return [binding, duplicate]

    store.list_active_bindings = _duplicate_bindings  # type: ignore[assignment]

    with pytest.raises(EffectiveCapabilityResolutionError, match="ambiguous"):
        resolver.resolve_effective_capabilities_for_owner_and_project(
            account_id="acct-1",
            project_id=17,
        )
