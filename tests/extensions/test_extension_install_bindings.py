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
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    ExtensionProposalScope,
    ExtensionTargetSurface,
    ExtensionTokenError,
)


@pytest.fixture()
def extension_binding_store():
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
            summary="binding seam coverage",
            artifacts=("tests/extensions/test_extension_install_bindings.py",),
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


@pytest.mark.parametrize(
    "scope_token, manifest_scope, manifest_surface, manifest_scope_kwargs, binding_kwargs",
    [
        (
            ExtensionInstallBindingScope.PROJECT.value,
            ExtensionProposalScope.PROJECT.value,
            ExtensionTargetSurface.COMMAND_BUS.value,
            {"project_id": 17},
            {"project_id": 17},
        ),
        (
            ExtensionInstallBindingScope.PROFILE.value,
            ExtensionProposalScope.PROFILE.value,
            ExtensionTargetSurface.PERSONA_STUDIO.value,
            {"profile_id": "profile-beta"},
            {"profile_id": "profile-beta"},
        ),
        (
            ExtensionInstallBindingScope.ACCOUNT.value,
            ExtensionProposalScope.ACCOUNT.value,
            ExtensionTargetSurface.PERSONA_STUDIO.value,
            {},
            {"account_scope_target_id": "account-target-1"},
        ),
    ],
)
def test_extension_install_binding_round_trip_by_scope(
    extension_binding_store,
    scope_token,
    manifest_scope,
    manifest_surface,
    manifest_scope_kwargs,
    binding_kwargs,
):
    store, gate, registry, bindings = extension_binding_store
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=manifest_surface,
            scope=manifest_scope,
            **manifest_scope_kwargs,
        ),
    )

    binding = ExtensionInstallBinding(
        account_id="acct-1",
        registry_entry_id=registry_entry.registry_id,
        scope_token=scope_token,
        bind_reason="manual install binding",
        bind_notes={"reviewer": "alice"},
        bind_metadata={"source": "unit-test"},
        **binding_kwargs,
    )
    record = bindings.bind_registry_entry_to_scope(binding=binding)

    assert record.account_id == "acct-1"
    assert record.registry_entry_id == registry_entry.registry_id
    assert record.proposal_id == registry_entry.proposal_id
    assert record.scope_token == scope_token
    assert record.bind_reason == "manual install binding"
    assert (
        record.bind_metadata["registry_entry_id"] == registry_entry.registry_id
    )
    assert record.bind_metadata["proposal_id"] == registry_entry.proposal_id
    assert record.bind_metadata["source_thread_id"] == 41
    assert record.bind_metadata["source_message_id"] == 42
    assert record.source_thread_id == 41
    assert record.source_message_id == 42
    assert record.is_active is True
    assert record.unbound_at is None

    fetched = bindings.get_binding_by_id(
        account_id="acct-1", binding_id=record.binding_id
    )
    assert fetched == record

    scope_filters = {
        ExtensionInstallBindingScope.PROJECT.value: dict(project_id=17),
        ExtensionInstallBindingScope.PROFILE.value: dict(
            profile_id="profile-beta"
        ),
        ExtensionInstallBindingScope.ACCOUNT.value: dict(
            account_scope_target_id="account-target-1"
        ),
    }
    assert bindings.list_bindings(
        account_id="acct-1",
        scope=scope_token,
        **scope_filters[scope_token],
    ) == [record]


def test_extension_install_binding_owner_isolation(extension_binding_store):
    store, gate, registry, bindings = extension_binding_store
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

    assert (
        bindings.get_binding_by_id(
            account_id="acct-2", binding_id=record.binding_id
        )
        is None
    )
    assert bindings.list_bindings(account_id="acct-2") == []


def test_extension_install_binding_rejects_duplicate_active_binding(
    extension_binding_store,
):
    store, gate, registry, bindings = extension_binding_store
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

    binding = ExtensionInstallBinding(
        account_id="acct-1",
        registry_entry_id=registry_entry.registry_id,
        scope_token=ExtensionInstallBindingScope.PROJECT.value,
        project_id=17,
    )
    bindings.bind_registry_entry_to_scope(binding=binding)

    with pytest.raises(ValueError, match="duplicate active binding"):
        bindings.bind_registry_entry_to_scope(binding=binding)


def test_extension_install_binding_unbind_preserves_history(
    extension_binding_store,
):
    store, gate, registry, bindings = extension_binding_store
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

    unbound = bindings.unbind_existing_binding(
        account_id="acct-1",
        binding_id=record.binding_id,
        reason="no longer needed",
        notes={"reviewer": "alice"},
        unbind_metadata={"source": "unit-test"},
    )

    assert (
        unbound.binding_status_token
        == ExtensionInstallBindingStatus.UNBOUND.value
    )
    assert unbound.unbound_at is not None
    assert unbound.unbind_metadata["reason"] == "no longer needed"
    assert unbound.unbind_metadata["binding_id"] == record.binding_id
    assert (
        unbound.unbind_metadata["registry_entry_id"]
        == registry_entry.registry_id
    )
    assert (
        bindings.get_binding_by_id(
            account_id="acct-1", binding_id=record.binding_id
        )
        == unbound
    )
    assert bindings.list_bindings(
        account_id="acct-1",
        scope=ExtensionInstallBindingScope.PROJECT.value,
        status=ExtensionInstallBindingStatus.UNBOUND.value,
    ) == [unbound]
    assert (
        bindings.list_bindings(
            account_id="acct-1",
            scope=ExtensionInstallBindingScope.PROJECT.value,
            status=ExtensionInstallBindingStatus.ACTIVE.value,
        )
        == []
    )


def test_extension_install_binding_listing_filters(extension_binding_store):
    store, gate, registry, bindings = extension_binding_store

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
            profile_id="profile-beta",
        ),
    )[2]
    account_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )[2]

    project_binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=project_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )
    profile_binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=profile_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROFILE.value,
            profile_id="profile-beta",
        )
    )
    account_binding = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=account_registry.registry_id,
            scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
            account_scope_target_id="account-target-1",
        )
    )
    unbound_project = bindings.unbind_existing_binding(
        account_id="acct-1",
        binding_id=project_binding.binding_id,
        reason="scope changed",
    )

    assert bindings.list_bindings(
        account_id="acct-1", scope=ExtensionInstallBindingScope.PROJECT.value
    ) == [unbound_project]
    assert bindings.list_bindings(
        account_id="acct-1",
        project_id=17,
        status=ExtensionInstallBindingStatus.UNBOUND.value,
    ) == [unbound_project]
    assert bindings.list_bindings(
        account_id="acct-1",
        profile_id="profile-beta",
        status=ExtensionInstallBindingStatus.ACTIVE.value,
    ) == [profile_binding]
    assert bindings.list_bindings(
        account_id="acct-1",
        account_scope_target_id="account-target-1",
        status=ExtensionInstallBindingStatus.ACTIVE.value,
    ) == [account_binding]


def test_extension_install_binding_invalid_tokens_are_rejected(
    extension_binding_store,
):
    store, gate, registry, bindings = extension_binding_store
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

    with pytest.raises(ExtensionTokenError):
        ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token="bogus",
            project_id=17,
        )

    record = bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id="acct-1",
            registry_entry_id=registry_entry.registry_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=17,
        )
    )

    with pytest.raises(ExtensionTokenError):
        bindings.update_binding_status(
            account_id="acct-1",
            binding_id=record.binding_id,
            status="bogus",
        )
