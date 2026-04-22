from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
    Base,
)
from guardian.extensions.contracts import (
    CapabilityRegistryEntry,
    ExtensionDeclaredDependency,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
    InstallGateDecisionRecord,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore


@pytest.fixture()
def extension_registry_store():
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
    return store, gate, registry


def _manifest(
    *,
    target_surface: str = "command_bus",
    scope: str = "project_scoped",
    project_id: int | None = 17,
    profile_id: str | None = "profile-alpha",
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
            summary="proposal draft coverage",
            artifacts=("tests/extensions/test_install_gate_and_registry.py",),
        ),
    )


def test_install_gate_approval_creates_decision_and_registry_entry(
    extension_registry_store,
):
    store, gate, registry = extension_registry_store
    proposal = store.create_proposal(account_id="acct-1", manifest=_manifest())

    decision, registry_entry = gate.approve_proposal(
        account_id="acct-1",
        proposal_id=proposal.proposal_id,
        reason="manual approval",
        notes={"reviewer": "alice", "note": "approved for testing"},
        approved_permissions=[
            {
                "permission": "command.run",
                "resource": "command_bus",
                "reason": "bounded command execution",
                "metadata": {},
            }
        ],
        registration_metadata={"reviewer": "alice"},
        provenance={"review_note": "manual approval"},
    )

    assert decision.decision_token == "approved"
    assert decision.requested_permissions == proposal.requested_permissions
    assert decision.approved_permissions == proposal.requested_permissions
    assert decision.updated_at is not None
    assert registry_entry.registry_id
    assert registry_entry.account_id == "acct-1"
    assert registry_entry.proposal_id == proposal.proposal_id
    assert registry_entry.decision_id == decision.decision_id
    assert registry_entry.status_token == "registered"
    assert registry_entry.target_surface == "command_bus"
    assert registry_entry.scope == "project_scoped"
    assert registry_entry.project_id == 17
    assert registry_entry.profile_id == "profile-alpha"
    assert registry_entry.source_thread_id == 41
    assert registry_entry.source_message_id == 42
    assert (
        registry_entry.manifest_snapshot.summary
        == "Generate a bounded tool plugin"
    )
    assert registry_entry.provenance_class_token == "proposal_approval"
    assert registry_entry.registration_metadata["reviewer"] == "alice"
    assert registry_entry.provenance_json["review_note"] == "manual approval"

    fetched_decision = store.get_install_gate_decision_by_id(
        account_id="acct-1", decision_id=decision.decision_id
    )
    fetched_registry = store.get_registry_entry_by_id(
        account_id="acct-1", registry_id=registry_entry.registry_id
    )
    assert fetched_decision == decision
    assert fetched_registry == registry_entry
    assert store.list_install_gate_decisions(
        account_id="acct-1", proposal_id=proposal.proposal_id
    ) == [decision]
    assert store.list_registry_entries(account_id="acct-1", project_id=17) == [
        registry_entry
    ]
    assert (
        store.get_proposal_by_id(
            account_id="acct-1", proposal_id=proposal.proposal_id
        ).status
        == "accepted"
    )


def test_install_gate_rejection_creates_decision_without_registry_entry(
    extension_registry_store,
):
    store, gate, registry = extension_registry_store
    proposal = store.create_proposal(account_id="acct-1", manifest=_manifest())

    decision = gate.reject_proposal(
        account_id="acct-1",
        proposal_id=proposal.proposal_id,
        reason="missing test evidence",
        notes={"reviewer": "bob"},
    )

    assert decision.decision_token == "rejected"
    assert decision.approved_permissions == ()
    assert (
        store.get_install_gate_decision_by_id(
            account_id="acct-1", decision_id=decision.decision_id
        )
        == decision
    )
    assert store.list_registry_entries(account_id="acct-1") == []
    assert (
        store.get_registry_entry_by_id(
            account_id="acct-1", registry_id="registry-missing"
        )
        is None
    )
    assert store.list_install_gate_decisions(
        account_id="acct-1", proposal_id=proposal.proposal_id
    ) == [decision]
    assert (
        store.get_proposal_by_id(
            account_id="acct-1", proposal_id=proposal.proposal_id
        ).status
        == "rejected"
    )


def test_install_gate_owner_isolation_and_scope_filters(
    extension_registry_store,
):
    store, gate, registry = extension_registry_store
    project_proposal = store.create_proposal(
        account_id="acct-1",
        manifest=_manifest(project_id=17, profile_id=None),
    )
    profile_proposal = store.create_proposal(
        account_id="acct-1",
        manifest=_manifest(
            target_surface="persona_studio",
            scope="profile_scoped",
            project_id=None,
            profile_id="profile-beta",
            source_thread_id=51,
            source_message_id=52,
        ),
    )

    project_decision, project_entry = gate.approve_proposal(
        account_id="acct-1",
        proposal_id=project_proposal.proposal_id,
    )
    profile_decision, profile_entry = gate.approve_proposal(
        account_id="acct-1",
        proposal_id=profile_proposal.proposal_id,
    )

    assert (
        store.get_install_gate_decision_by_id(
            account_id="acct-2", decision_id=project_decision.decision_id
        )
        is None
    )
    assert (
        store.get_registry_entry_by_id(
            account_id="acct-2", registry_id=project_entry.registry_id
        )
        is None
    )
    assert store.list_install_gate_decisions(account_id="acct-2") == []
    assert store.list_registry_entries(account_id="acct-2") == []
    assert store.list_registry_entries(account_id="acct-1", project_id=17) == [
        project_entry
    ]
    assert store.list_registry_entries(
        account_id="acct-1", profile_id="profile-beta"
    ) == [profile_entry]
    assert store.list_install_gate_decisions(
        account_id="acct-1", proposal_id=profile_proposal.proposal_id
    ) == [profile_decision]


def test_install_gate_invalid_tokens_are_rejected(extension_registry_store):
    store, gate, registry = extension_registry_store
    manifest = _manifest()
    proposal = store.create_proposal(account_id="acct-1", manifest=manifest)

    with pytest.raises(ValueError):
        InstallGateDecisionRecord(
            decision_id="decision-invalid",
            account_id="acct-1",
            proposal_id=proposal.proposal_id,
            decision_token="not-a-token",
        )

    with pytest.raises(ValueError):
        CapabilityRegistryEntry(
            registry_id="registry-invalid",
            account_id="acct-1",
            proposal_id=proposal.proposal_id,
            decision_id="decision-invalid",
            status_token="not-a-status",
            manifest_snapshot=manifest,
        )

    decision, entry = gate.approve_proposal(
        account_id="acct-1",
        proposal_id=proposal.proposal_id,
    )

    with pytest.raises(ValueError):
        registry.update_registry_status(
            account_id="acct-1",
            registry_id=entry.registry_id,
            status="not-a-status",
        )

    assert decision.is_approved


def test_install_gate_registry_status_update_round_trip(
    extension_registry_store,
):
    store, gate, registry = extension_registry_store
    proposal = store.create_proposal(account_id="acct-1", manifest=_manifest())
    _decision, entry = gate.approve_proposal(
        account_id="acct-1",
        proposal_id=proposal.proposal_id,
    )

    updated = registry.update_registry_status(
        account_id="acct-1",
        registry_id=entry.registry_id,
        status="suspended",
    )

    assert updated.status_token == "suspended"
    assert (
        store.get_registry_entry_by_id(
            account_id="acct-1", registry_id=entry.registry_id
        )
        == updated
    )
    assert store.list_registry_entries(
        account_id="acct-1", status="suspended"
    ) == [updated]
