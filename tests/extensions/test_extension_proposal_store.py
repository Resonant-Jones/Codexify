from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import AgentExtensionProposal, Base
from guardian.extensions.contracts import (
    ExtensionDeclaredDependency,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.store import ExtensionProposalStore


@pytest.fixture()
def proposal_store():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine, tables=[AgentExtensionProposal.__table__]
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    class _DB:
        def get_session(self):
            return Session()

    return ExtensionProposalStore(_DB()), Session


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
            artifacts=("tests/extensions/test_extension_proposal_store.py",),
        ),
    )


def test_extension_proposal_round_trip_and_lineage_persistence(
    proposal_store,
):
    store, session_factory = proposal_store
    manifest = _manifest()

    record = store.create_proposal(
        account_id="acct-1",
        manifest=manifest,
    )

    assert record.account_id == "acct-1"
    assert record.status == "draft"
    assert record.target_surface == "command_bus"
    assert record.scope == "project_scoped"
    assert record.project_id == 17
    assert record.profile_id == "profile-alpha"
    assert record.source_thread_id == 41
    assert record.source_message_id == 42
    assert record.requested_permissions[0].permission == "command.run"
    assert record.declared_dependencies[0].name == "httpx"
    assert record.rollback_metadata is not None
    assert record.test_evidence_metadata is not None

    fetched = store.get_proposal_by_id(
        account_id="acct-1", proposal_id=record.proposal_id
    )
    assert fetched == record

    listed = store.list_proposals(account_id="acct-1")
    assert listed == [record]

    with session_factory() as session:
        row = (
            session.query(AgentExtensionProposal)
            .filter_by(proposal_id=record.proposal_id)
            .one()
        )
        assert row.account_id == "acct-1"
        assert row.project_id == 17
        assert row.profile_id == "profile-alpha"
        assert row.source_thread_id == 41
        assert row.source_message_id == 42
        assert row.target_surface_token == "command_bus"
        assert row.scope_token == "project_scoped"
        assert row.status_token == "draft"
        assert row.manifest_json["summary"] == "Generate a bounded tool plugin"
        assert row.manifest_json["requested_permissions"][0]["permission"] == (
            "command.run"
        )


def test_extension_proposal_owner_isolation_and_scope_filters(
    proposal_store,
):
    store, _session_factory = proposal_store
    project_manifest = _manifest(project_id=10, profile_id=None)
    profile_manifest = _manifest(
        target_surface="persona_studio",
        scope="profile_scoped",
        project_id=None,
        profile_id="profile-beta",
        source_thread_id=51,
        source_message_id=52,
    )
    account_manifest = _manifest(
        target_surface="retrieval_router",
        scope="account_scoped",
        project_id=None,
        profile_id=None,
        source_thread_id=61,
        source_message_id=62,
    )

    project_record = store.create_proposal(
        account_id="acct-1",
        manifest=project_manifest,
        status="proposed",
    )
    profile_record = store.create_proposal(
        account_id="acct-1",
        manifest=profile_manifest,
        status="accepted",
    )
    account_record = store.create_proposal(
        account_id="acct-1",
        manifest=account_manifest,
        status="archived",
    )
    other_account_record = store.create_proposal(
        account_id="acct-2",
        manifest=project_manifest,
        status="rejected",
    )

    assert (
        store.get_proposal_by_id(
            account_id="acct-2", proposal_id=project_record.proposal_id
        )
        is None
    )
    assert store.list_proposals(account_id="acct-2") == [other_account_record]
    assert store.list_proposals(account_id="acct-1", project_id=10) == [
        project_record
    ]
    assert store.list_proposals(
        account_id="acct-1", profile_id="profile-beta"
    ) == [profile_record]
    assert store.list_proposals(
        account_id="acct-1", scope="account_scoped"
    ) == [account_record]
    assert store.list_proposals(account_id="acct-1", status="accepted") == [
        profile_record
    ]


def test_extension_proposal_rejects_invalid_tokens(proposal_store):
    store, _session_factory = proposal_store

    with pytest.raises(ValueError):
        _manifest(target_surface="not-a-surface")

    with pytest.raises(ValueError):
        ExtensionProposalManifest(
            target_surface="command_bus",
            scope="not-a-scope",
        )

    with pytest.raises(ValueError):
        store.create_proposal(
            account_id="acct-1",
            manifest=_manifest(),
            status="not-a-status",
        )

    record = store.create_proposal(
        account_id="acct-1",
        manifest=_manifest(),
    )

    with pytest.raises(LookupError):
        store.update_proposal_status(
            account_id="acct-2",
            proposal_id=record.proposal_id,
            status="accepted",
        )

    updated = store.update_proposal_status(
        account_id="acct-1",
        proposal_id=record.proposal_id,
        status="accepted",
    )
    assert updated.status == "accepted"
