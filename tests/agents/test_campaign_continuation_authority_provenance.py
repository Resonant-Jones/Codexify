"""Campaign Continuation Authority provenance: store-level semantics.

Proves the persistence foundation of ADR-105 at the store boundary: the
provenance discriminator is required, is validated against a closed
vocabulary, is stored per action, and participates in the idempotent
approval comparison.

These tests run against SQLite so they exercise the real store, the real
ORM models, and the real schema constraints without a database service.
The PostgreSQL migration, readback, and recovery proof lives in
``tests/db/test_campaign_continuation_authority_provenance_migration.py``.

ADR: docs/architecture/adr/105-operator-actor-identity-and-human-approval-provenance.md
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from guardian.agents.campaign_runner_store import (
    CampaignRunnerStore,
    CampaignRunnerValidationError,
)
from guardian.db.models import (
    Campaign,
    CampaignContinuationAuthorityRecord,
    CampaignGoal,
)
from guardian.protocol_tokens import (
    HUMAN_APPROVED_CONTINUATION_AUTHORITY_PROVENANCES,
    ContinuationAuthorityProvenance,
)

ACCOUNT_ADMIN = ContinuationAuthorityProvenance.ACCOUNT_ADMIN.value
OPERATOR_DEPLOYMENT = ContinuationAuthorityProvenance.OPERATOR_DEPLOYMENT.value
LEGACY = ContinuationAuthorityProvenance.LEGACY_UNVERIFIED.value


class _Db:
    """A minimal database handle shaped like the one the store expects."""

    def __init__(self, session_factory: Any) -> None:
        self.SessionLocal = session_factory

    def get_session(self) -> Session:
        return self.SessionLocal()


@pytest.fixture
def store() -> Iterator[CampaignRunnerStore]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        CampaignGoal.__table__,
        Campaign.__table__,
        CampaignContinuationAuthorityRecord.__table__,
    ):
        table.create(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield CampaignRunnerStore(db=_Db(session_factory))
    finally:
        engine.dispose()


@pytest.fixture
def campaign_id(store: CampaignRunnerStore) -> str:
    goal = store.create_goal(title="Provenance probe goal")
    campaign = store.create_campaign(goal_id=goal["goal_id"], title="Probe campaign")
    return str(campaign["campaign_id"])


def _envelope() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "campaign_objective": "Probe the provenance discriminator",
        "allowed_task_classes": ["coding"],
        "permitted_execution_lanes": ["operator"],
        "permitted_workspace_scope": ["repo"],
        "permitted_validation_proof_classes": ["unit"],
        "spend_posture": {"daily_usd": 1},
        "automatic_retry_permitted": False,
        "max_retries": 0,
        "automatic_downstream_dispatch_permitted": False,
        "promotion_authorities": {"commit": False},
        "explicit_stop_conditions": ["halt on failure"],
    }


def test_approval_records_the_provenance_class(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """The approval stores the class it was given, per action."""
    authority = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-1",
        approval_provenance=ACCOUNT_ADMIN,
    )
    assert authority["approval_provenance"] == ACCOUNT_ADMIN
    assert authority["revocation_provenance"] is None

    listed = store.list_continuation_authorities(campaign_id)
    assert len(listed) == 1
    assert listed[0]["approval_provenance"] == ACCOUNT_ADMIN


def test_an_unknown_provenance_class_is_rejected(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """A class outside the vocabulary is refused, not stored."""
    with pytest.raises(CampaignRunnerValidationError) as excinfo:
        store.approve_continuation_authority(
            campaign_id=campaign_id,
            envelope=_envelope(),
            approved_by_actor_id="admin-1",
            approval_provenance="human_admin",
        )
    assert excinfo.value.reason_code == "invalid_continuation_authority_provenance"
    assert store.list_continuation_authorities(campaign_id) == []


def test_a_missing_provenance_class_is_rejected(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """An absent class is refused rather than inferred."""
    with pytest.raises(CampaignRunnerValidationError) as excinfo:
        store.approve_continuation_authority(
            campaign_id=campaign_id,
            envelope=_envelope(),
            approved_by_actor_id="admin-1",
            approval_provenance="",
        )
    assert excinfo.value.reason_code == "invalid_continuation_authority_provenance"
    assert store.list_continuation_authorities(campaign_id) == []


def test_identical_actor_bytes_across_classes_are_not_idempotent(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """The same actor bytes under a different class is not an idempotent hit.

    This is the ambiguity ADR-105 exists to remove. The deployment
    principal's actor id may equal a canonical administrator's ``User.id``,
    so the approval comparison has to include the provenance class. Without
    it, the second call would return the first record as an idempotent
    success and the two authority classes would silently merge.
    """
    first = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="shared-actor-id",
        approval_provenance=ACCOUNT_ADMIN,
    )

    with pytest.raises(CampaignRunnerValidationError) as excinfo:
        store.approve_continuation_authority(
            campaign_id=campaign_id,
            envelope=_envelope(),
            approved_by_actor_id="shared-actor-id",
            approval_provenance=OPERATOR_DEPLOYMENT,
        )
    assert excinfo.value.reason_code == "continuation_authority_already_exists"

    # The stored record is untouched and still carries its own class.
    listed = store.list_continuation_authorities(campaign_id)
    assert len(listed) == 1
    assert listed[0]["authority_id"] == first["authority_id"]
    assert listed[0]["approval_provenance"] == ACCOUNT_ADMIN


def test_the_same_provenance_class_is_idempotent(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """A genuine repeat under the same class stays idempotent."""
    first = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-1",
        approval_provenance=ACCOUNT_ADMIN,
    )
    second = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-1",
        approval_provenance=ACCOUNT_ADMIN,
    )
    assert second["authority_id"] == first["authority_id"]
    assert len(store.list_continuation_authorities(campaign_id)) == 1


def test_revocation_records_its_own_provenance_class(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """Approval and revocation carry independent provenance."""
    authority = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-1",
        approval_provenance=ACCOUNT_ADMIN,
    )
    revoked = store.revoke_continuation_authority(
        campaign_id=campaign_id,
        authority_id=authority["authority_id"],
        revoked_by_actor_id="admin-2",
        revocation_provenance=ACCOUNT_ADMIN,
        reason="operator requested",
    )
    assert revoked["approval_provenance"] == ACCOUNT_ADMIN
    assert revoked["revocation_provenance"] == ACCOUNT_ADMIN


def test_revocation_rejects_an_unknown_provenance_class(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """A revocation cannot be recorded without a canonical class."""
    authority = store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-1",
        approval_provenance=ACCOUNT_ADMIN,
    )
    with pytest.raises(CampaignRunnerValidationError) as excinfo:
        store.revoke_continuation_authority(
            campaign_id=campaign_id,
            authority_id=authority["authority_id"],
            revoked_by_actor_id="admin-2",
            revocation_provenance="deployment",
            reason="operator requested",
        )
    assert excinfo.value.reason_code == "invalid_continuation_authority_provenance"

    listed = store.list_continuation_authorities(campaign_id)
    assert listed[0]["revoked_at"] is None
    assert listed[0]["revocation_provenance"] is None


def test_a_legacy_row_is_not_read_as_a_human_approval(
    store: CampaignRunnerStore, campaign_id: str
) -> None:
    """Matching actor bytes do not promote a legacy row to human approved.

    The classification is read from the durable discriminator. An
    unrevoked legacy row whose actor bytes happen to equal a canonical
    administrator's ``User.id`` is still legacy, so it is never treated as
    a human approval by any consumer.
    """
    store.approve_continuation_authority(
        campaign_id=campaign_id,
        envelope=_envelope(),
        approved_by_actor_id="admin-collision-id",
        approval_provenance=OPERATOR_DEPLOYMENT,
    )
    # Reclassify the stored row the way the bounded migration would.
    with store.db.get_session() as session:
        row = (
            session.query(CampaignContinuationAuthorityRecord)
            .filter_by(campaign_id=campaign_id)
            .one()
        )
        row.approval_provenance = LEGACY
        session.commit()

    listed = store.list_continuation_authorities(campaign_id)
    assert listed[0]["approved_by_actor_id"] == "admin-collision-id"
    assert listed[0]["approval_provenance"] == LEGACY
    assert listed[0]["approval_provenance"] not in (
        HUMAN_APPROVED_CONTINUATION_AUTHORITY_PROVENANCES
    )
