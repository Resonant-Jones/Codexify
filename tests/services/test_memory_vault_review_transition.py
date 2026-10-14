"""Focused PostgreSQL proof for the UMS-05C10A-W review transition writer.

Proves ``MemoryVaultMutationService.transition_review`` against real
disposable PostgreSQL, enforcing ADR-088 exactly:

* only ``approve`` / ``reject`` / ``dispute`` are admitted, and no path can
  target ``pending``;
* the full ADR-088 matrix across all four canonical states;
* same-state actions are no-ops *after* a fresh CAS check;
* a stale CAS conflicts even when the action would otherwise be a no-op, and
  allocates nothing;
* each changed transition emits exactly one ``memory_review_revisions`` row
  and exactly one ``memory-vault-mutation.v1`` receipt, atomically with the
  current-state and CAS updates;
* ``reviewed_at`` follows first-authoritative-approval semantics;
* existing review history must be contiguous and tail-consistent;
* forced revision and forced receipt failures roll everything back;
* lifecycle, content, pin, hold, Project, Persona, and prior provenance are
  unchanged.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from guardian.db.models import (
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    MemoryReviewRevision,
    MemoryRevision,
    PersonaSubject,
    Project,
    User,
)
from guardian.protocol_tokens import (
    MemoryPersonaLinkKind,
    MemorySemanticSpecies,
    PersonaSubjectLifecycle,
)
from guardian.services.memory_vault_mutation import (
    ACTION_APPROVE,
    ACTION_DISPUTE,
    ACTION_REJECT,
    RECEIPT_SCHEMA,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
    MemoryVaultReviewTransitionIntegrityError,
    MemoryVaultReviewTransitionInvalid,
    MemoryVaultReviewTransitionUnsupported,
)

ACCOUNT_A = "ums05c10aw-account-a"
ACCOUNT_B = "ums05c10aw-account-b"

CONTENT = "The red toolbox is in the garage."

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(seconds=1)


def _admin_url() -> str:
    base = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not base:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")
    return base


def _create_disposable_database(admin_url: str, name: str) -> str:
    import psycopg

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{name}"')
    parts = admin_url.split("?", 1)
    base = parts[0].rsplit("/", 1)[0]
    suffix = ("?" + parts[1]) if len(parts) == 2 else ""
    return f"{base}/{name}{suffix}"


def _drop_database(admin_url: str, name: str) -> None:
    import psycopg

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s",
                    (name,),
                )
            except psycopg.Error:
                pass
            try:
                cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
            except psycopg.Error:
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')


def _migrate_to_head(database_url: str) -> None:
    from alembic.command import upgrade
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    os.environ["DATABASE_URL"] = database_url
    os.environ["GUARDIAN_DATABASE_URL"] = database_url
    upgrade(config, "head")


@pytest.fixture
def database_url():
    admin = _admin_url()
    name = f"ums05c10aw_{uuid.uuid4().hex[:10]}"
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture
def session_factory(database_url):
    engine = sa.create_engine(database_url, future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _seed(session, *, review_state: str, reviewed_at=sa.func.now()) -> dict:
    # ADR-088 first-approval semantics: a never-approved memory has no
    # reviewed_at, and the frozen review-before-activation CHECK then
    # requires activated_at to be NULL too.
    session.add(User(id=ACCOUNT_A, username=ACCOUNT_A, password_hash="x", role="guest"))
    session.add(User(id=ACCOUNT_B, username=ACCOUNT_B, password_hash="x", role="guest"))
    session.add(Project(id=9000, user_id=ACCOUNT_A, name="p", identity_depth="light"))
    ordinary_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())
    subject_id = str(uuid.uuid4())
    session.commit()
    session.add(
        PersonaSubject(
            persona_subject_id=subject_id,
            user_id=ACCOUNT_A,
            display_name_snapshot="A",
            lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
        )
    )
    session.add(
        MemoryRecord(
            memory_id=ordinary_id,
            user_id=ACCOUNT_A,
            project_id=9000,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content=CONTENT,
            fact_key=None,
            fact_value=None,
            fact_confidence=None,
            reviewed_at=reviewed_at,
            activated_at=None if reviewed_at is None else sa.func.now(),
            pinned=True,
            held=True,
            review_state=review_state,
            lifecycle_state="active",
        )
    )
    session.add(
        MemoryRecord(
            memory_id=fact_id,
            user_id=ACCOUNT_A,
            project_id=None,
            semantic_species=MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value,
            text_content=None,
            fact_key="k",
            fact_value="v",
            fact_confidence=0.9,
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
            review_state="approved",
            lifecycle_state="active",
        )
    )
    session.commit()
    session.add(
        MemoryPersonaLink(
            link_id=str(uuid.uuid4()),
            memory_id=ordinary_id,
            user_id=ACCOUNT_A,
            persona_subject_id=subject_id,
            persona_user_id=ACCOUNT_A,
            link_kind=MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
        )
    )
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=ordinary_id,
            user_id=ACCOUNT_A,
            source_system="codexify",
            source_subject_kind="vault",
            is_imported=False,
        )
    )
    session.commit()
    return {"ordinary_id": ordinary_id, "fact_id": fact_id, "subject_id": subject_id}


def _make(session_factory, *, review_state: str, reviewed_at=sa.func.now()):
    with session_factory() as session:
        ids = _seed(session, review_state=review_state, reviewed_at=reviewed_at)
    return {"session_factory": session_factory, **ids}


def _fresh(service, session_factory, memory_id, action, **kwargs):
    with session_factory() as session:
        row = session.execute(
            sa.select(MemoryRecord).where(MemoryRecord.memory_id == memory_id)
        ).scalar_one()
        expected = row.updated_at
    with session_factory() as session:
        return service(session, authenticated_account_id=ACCOUNT_A).transition_review(
            memory_id=memory_id,
            expected_updated_at=expected,
            action=action,
            **kwargs,
        )


def _row(session_factory, memory_id, account=ACCOUNT_A):
    with session_factory() as session:
        return session.execute(
            sa.select(MemoryRecord).where(
                MemoryRecord.memory_id == memory_id,
                MemoryRecord.user_id == account,
            )
        ).scalar_one_or_none()


def _review_revisions(session_factory, memory_id, account=ACCOUNT_A):
    with session_factory() as session:
        return list(
            session.execute(
                sa.select(MemoryReviewRevision)
                .where(
                    MemoryReviewRevision.memory_id == memory_id,
                    MemoryReviewRevision.user_id == account,
                )
                .order_by(MemoryReviewRevision.revision_number.asc())
            ).scalars()
        )


def _receipts(session_factory, memory_id, account=ACCOUNT_A):
    with session_factory() as session:
        return list(
            session.execute(
                sa.select(MemoryProvenance).where(
                    MemoryProvenance.memory_id == memory_id,
                    MemoryProvenance.user_id == account,
                )
            ).scalars()
        )


def _content_revisions(session_factory, memory_id):
    with session_factory() as session:
        return list(
            session.execute(
                sa.select(MemoryRevision).where(MemoryRevision.memory_id == memory_id)
            ).scalars()
        )


def _fresh_token(session_factory, memory_id):
    with session_factory() as session:
        return session.execute(
            sa.select(MemoryRecord.updated_at).where(
                MemoryRecord.memory_id == memory_id
            )
        ).scalar_one()


def _service(session_factory):
    return MemoryVaultMutationService


# ---------------------------------------------------------------------------
# Authority and admission.
# ---------------------------------------------------------------------------


def test_account_can_review_own_ordinary_memory(session_factory):
    ctx = _make(session_factory, review_state="pending")
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_APPROVE
    )
    assert result.changed is True
    assert result.previous_review_state == "pending"
    assert result.resulting_review_state == "approved"


def test_missing_memory_is_unavailable(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationNotAvailable):
            service.transition_review(
                memory_id="00000000-0000-0000-0000-000000000000",
                expected_updated_at=NOW,
                action=ACTION_APPROVE,
            )


def test_cross_account_is_unavailable_with_same_posture(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_B)
        with pytest.raises(MemoryVaultMutationNotAvailable):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=NOW,
                action=ACTION_APPROVE,
            )


def test_personal_fact_species_is_refused(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReviewTransitionUnsupported):
            service.transition_review(
                memory_id=ctx["fact_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["fact_id"]),
                action=ACTION_APPROVE,
            )
    # Refused without writing a second generic review history.
    assert _review_revisions(session_factory, ctx["fact_id"]) == []


def test_only_three_admitted_actions_are_accepted(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        for bad in (
            "pending",
            "set_pending",
            "reset_review",
            "APPROVED_X",
            "",
            5,
            None,
        ):
            with pytest.raises(MemoryVaultReviewTransitionInvalid):
                service.transition_review(
                    memory_id=ctx["ordinary_id"],
                    expected_updated_at=NOW,
                    action=bad,
                )
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []


def test_caller_cannot_target_pending(session_factory):
    """ADR-088: no direct action targets pending, from any state."""
    ctx = _make(session_factory, review_state="approved")
    for state in ("pending", "approved", "rejected", "disputed"):
        with session_factory() as session:
            row = session.execute(
                sa.select(MemoryRecord).where(
                    MemoryRecord.memory_id == ctx["ordinary_id"]
                )
            ).scalar_one()
            row.review_state = state
            session.commit()
        with session_factory() as session:
            service = _service(session_factory)(
                session, authenticated_account_id=ACCOUNT_A
            )
            with pytest.raises(MemoryVaultReviewTransitionInvalid):
                service.transition_review(
                    memory_id=ctx["ordinary_id"],
                    expected_updated_at=NOW,
                    action="pending",
                )
    assert _row(session_factory, ctx["ordinary_id"]).review_state == "disputed"


# ---------------------------------------------------------------------------
# ADR-088 matrix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "action", "expected"),
    [
        ("pending", ACTION_APPROVE, "approved"),
        ("pending", ACTION_REJECT, "rejected"),
        ("pending", ACTION_DISPUTE, "disputed"),
        ("approved", ACTION_REJECT, "rejected"),
        ("approved", ACTION_DISPUTE, "disputed"),
        ("rejected", ACTION_APPROVE, "approved"),
        ("rejected", ACTION_DISPUTE, "disputed"),
        ("disputed", ACTION_APPROVE, "approved"),
        ("disputed", ACTION_REJECT, "rejected"),
    ],
)
def test_changed_transitions_follow_adr_088(session_factory, start, action, expected):
    ctx = _make(session_factory, review_state=start)
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], action
    )
    assert result.changed is True
    assert result.resulting_review_state == expected
    assert _row(session_factory, ctx["ordinary_id"]).review_state == expected


@pytest.mark.parametrize(
    ("start", "action"),
    [
        ("approved", ACTION_APPROVE),
        ("rejected", ACTION_REJECT),
        ("disputed", ACTION_DISPUTE),
    ],
)
def test_same_state_actions_are_no_ops(session_factory, start, action):
    ctx = _make(session_factory, review_state=start)
    before = _row(session_factory, ctx["ordinary_id"])
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], action
    )

    assert result.changed is False
    assert result.receipt_id is None
    assert result.review_revision_id is None
    assert result.review_revision_number is None
    assert result.previous_review_state == result.resulting_review_state == start
    assert result.previous_updated_at == result.resulting_updated_at

    after = _row(session_factory, ctx["ordinary_id"])
    assert after.updated_at == before.updated_at
    assert after.reviewed_at == before.reviewed_at
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []
    assert len(_receipts(session_factory, ctx["ordinary_id"])) == 1  # seed only


def test_noop_does_not_backfill_reviewed_at(session_factory):
    """A same-state approve must not write a missing first-approval stamp."""
    ctx = _make(session_factory, review_state="approved", reviewed_at=None)
    before = _row(session_factory, ctx["ordinary_id"])
    assert before.reviewed_at is None
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_APPROVE
    )
    assert result.changed is False
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at is None


def test_corrupted_review_state_fails_closed(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        row = session.execute(
            sa.select(MemoryRecord).where(MemoryRecord.memory_id == ctx["ordinary_id"])
        ).scalar_one()
        # The vocabulary CHECK would block an invalid token, so drop it to
        # simulate genuinely corrupted persisted state.
        session.execute(
            sa.text(
                "ALTER TABLE memory_records "
                "DROP CONSTRAINT memory_records_review_state_check"
            )
        )
        session.execute(
            sa.text(
                "UPDATE memory_records SET review_state = 'wat' " "WHERE memory_id = :m"
            ),
            {"m": ctx["ordinary_id"]},
        )
        session.commit()
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReviewTransitionIntegrityError):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["ordinary_id"]),
                action=ACTION_APPROVE,
            )


# ---------------------------------------------------------------------------
# CAS.
# ---------------------------------------------------------------------------


def test_stale_cas_conflicts_on_changed_transition(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=NOW,  # stale
                action=ACTION_APPROVE,
            )
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []


def test_stale_cas_conflicts_even_on_same_state_action(session_factory):
    """CAS is validated before the no-op decision."""
    ctx = _make(session_factory, review_state="approved")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=NOW,  # stale
                action=ACTION_APPROVE,  # would be a no-op if token were fresh
            )
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []
    assert _row(session_factory, ctx["ordinary_id"]).review_state == "approved"


def test_naive_cas_is_rejected(session_factory):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationError):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=datetime(2026, 9, 28, 12, 0),
                action=ACTION_APPROVE,
            )


def test_changed_transition_advances_cas(session_factory):
    ctx = _make(session_factory, review_state="pending")
    before = _row(session_factory, ctx["ordinary_id"]).updated_at
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_APPROVE
    )
    after = _row(session_factory, ctx["ordinary_id"]).updated_at
    assert result.resulting_updated_at == after
    assert after > before


# ---------------------------------------------------------------------------
# Review revisions.
# ---------------------------------------------------------------------------


def test_first_transition_starts_review_history_at_one(session_factory):
    """A direct-created approved memory has no fabricated prior history."""
    ctx = _make(session_factory, review_state="approved")
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_REJECT
    )

    assert result.review_revision_number == 1
    revisions = _review_revisions(session_factory, ctx["ordinary_id"])
    assert len(revisions) == 1
    first = revisions[0]
    assert first.old_review_state == "approved"
    assert first.new_review_state == "rejected"
    assert first.actor_account_id == ACCOUNT_A
    assert first.review_revision_id == result.review_revision_id
    assert first.created_at is not None


def test_second_transition_increments_review_sequence(session_factory):
    ctx = _make(session_factory, review_state="approved")
    svc = session_factory
    _fresh(_service(svc), svc, ctx["ordinary_id"], ACTION_REJECT)
    second = _fresh(_service(svc), svc, ctx["ordinary_id"], ACTION_APPROVE)
    assert second.review_revision_number == 2

    revisions = _review_revisions(svc, ctx["ordinary_id"])
    assert [r.revision_number for r in revisions] == [1, 2]
    # Chain continuity.
    assert revisions[0].new_review_state == revisions[1].old_review_state
    assert revisions[-1].new_review_state == _row(svc, ctx["ordinary_id"]).review_state


def test_review_sequence_is_independent_of_content_revisions(session_factory):
    ctx = _make(session_factory, review_state="approved")
    with session_factory() as session:
        session.add(
            MemoryRevision(
                revision_id=str(uuid.uuid4()),
                memory_id=ctx["ordinary_id"],
                user_id=ACCOUNT_A,
                revision_number=1,
                old_text_content="a",
                new_text_content="b",
            )
        )
        session.commit()
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_DISPUTE
    )
    # Both families number from 1 independently.
    assert result.review_revision_number == 1
    assert len(_content_revisions(session_factory, ctx["ordinary_id"])) == 1
    assert len(_review_revisions(session_factory, ctx["ordinary_id"])) == 1


def test_gapped_review_history_fails_closed(session_factory):
    ctx = _make(session_factory, review_state="approved")
    with session_factory() as session:
        session.add_all(
            [
                MemoryReviewRevision(
                    review_revision_id=str(uuid.uuid4()),
                    memory_id=ctx["ordinary_id"],
                    user_id=ACCOUNT_A,
                    revision_number=n,
                    old_review_state="pending",
                    new_review_state="approved",
                    actor_account_id=ACCOUNT_A,
                )
                for n in (1, 3)
            ]
        )
        session.commit()
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReviewTransitionIntegrityError):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["ordinary_id"]),
                action=ACTION_REJECT,
            )
    # Not renumbered or repaired.
    assert [
        r.revision_number
        for r in _review_revisions(session_factory, ctx["ordinary_id"])
    ] == [1, 3]


def test_divergent_review_tail_fails_closed(session_factory):
    ctx = _make(session_factory, review_state="approved")
    with session_factory() as session:
        session.add(
            MemoryReviewRevision(
                review_revision_id=str(uuid.uuid4()),
                memory_id=ctx["ordinary_id"],
                user_id=ACCOUNT_A,
                revision_number=1,
                old_review_state="pending",
                new_review_state="disputed",  # diverges from current 'approved'
                actor_account_id=ACCOUNT_A,
            )
        )
        session.commit()
    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReviewTransitionIntegrityError):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["ordinary_id"]),
                action=ACTION_REJECT,
            )
    assert len(_review_revisions(session_factory, ctx["ordinary_id"])) == 1


# ---------------------------------------------------------------------------
# Receipt.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "expected_state"),
    [
        (ACTION_APPROVE, "approved"),
        (ACTION_REJECT, "rejected"),
        (ACTION_DISPUTE, "disputed"),
    ],
)
def test_each_changed_action_emits_exactly_one_receipt(
    session_factory, action, expected_state
):
    ctx = _make(session_factory, review_state="pending")
    result = _fresh(
        _service(session_factory),
        session_factory,
        ctx["ordinary_id"],
        action,
        reason="user review",
        request_ref="req-1",
    )
    receipts = _receipts(session_factory, ctx["ordinary_id"])
    # One seeded creation receipt plus exactly one mutation receipt.
    assert len(receipts) == 2
    receipt = next(r for r in receipts if r.provenance_id == result.receipt_id)
    extensions = receipt.extensions
    assert extensions["receipt_schema"] == RECEIPT_SCHEMA
    assert extensions["action"] == action
    assert extensions["actor_account_id"] == ACCOUNT_A
    assert extensions["previous_values"]["review_state"] == "pending"
    assert extensions["new_values"]["review_state"] == expected_state
    assert extensions["new_values"]["review_revision_id"] == result.review_revision_id
    assert extensions["new_values"]["review_revision_number"] == 1
    assert receipt.source_record_id == "req-1"
    # Bounded evidence only: no authored memory text anywhere.
    assert CONTENT not in str(extensions)


def test_noop_emits_no_receipt(session_factory):
    ctx = _make(session_factory, review_state="approved")
    _fresh(
        _service(session_factory),
        session_factory,
        ctx["ordinary_id"],
        ACTION_APPROVE,
        reason="should not create a receipt",
    )
    assert len(_receipts(session_factory, ctx["ordinary_id"])) == 1


# ---------------------------------------------------------------------------
# reviewed_at semantics.
# ---------------------------------------------------------------------------


def test_first_approval_sets_reviewed_at(session_factory):
    ctx = _make(session_factory, review_state="pending", reviewed_at=None)
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at is None
    _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_APPROVE
    )
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at is not None


def test_reapproval_preserves_first_approval_timestamp(session_factory):
    ctx = _make(session_factory, review_state="approved")
    original = _row(session_factory, ctx["ordinary_id"]).reviewed_at
    _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_REJECT
    )
    _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_APPROVE
    )
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at == original


def test_reject_preserves_reviewed_at(session_factory):
    ctx = _make(session_factory, review_state="approved")
    original = _row(session_factory, ctx["ordinary_id"]).reviewed_at
    _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_REJECT
    )
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at == original


def test_dispute_preserves_reviewed_at(session_factory):
    ctx = _make(session_factory, review_state="approved")
    original = _row(session_factory, ctx["ordinary_id"]).reviewed_at
    _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_DISPUTE
    )
    assert _row(session_factory, ctx["ordinary_id"]).reviewed_at == original


# ---------------------------------------------------------------------------
# Adjacent-state preservation.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", [ACTION_APPROVE, ACTION_REJECT, ACTION_DISPUTE])
def test_adjacent_authority_is_unchanged(session_factory, action):
    ctx = _make(session_factory, review_state="pending")
    with session_factory() as session:
        links_before = session.execute(
            sa.select(sa.func.count()).select_from(MemoryPersonaLink)
        ).scalar_one()
        receipts_before = len(_receipts(session_factory, ctx["ordinary_id"]))
    before = _row(session_factory, ctx["ordinary_id"])

    _fresh(_service(session_factory), session_factory, ctx["ordinary_id"], action)

    after = _row(session_factory, ctx["ordinary_id"])
    # ADR-088 review/lifecycle independence and no collateral mutation.
    assert after.lifecycle_state == before.lifecycle_state
    assert after.text_content == before.text_content
    assert after.pinned == before.pinned
    assert after.held == before.held
    assert after.project_id == before.project_id
    assert after.semantic_species == before.semantic_species
    assert after.created_at == before.created_at
    with session_factory() as session:
        links_after = session.execute(
            sa.select(sa.func.count()).select_from(MemoryPersonaLink)
        ).scalar_one()
    assert links_after == links_before
    # Prior provenance preserved, exactly one new receipt appended.
    assert len(_receipts(session_factory, ctx["ordinary_id"])) == receipts_before + 1


# ---------------------------------------------------------------------------
# Atomicity.
# ---------------------------------------------------------------------------


def test_forced_review_revision_failure_rolls_back(session_factory):
    ctx = _make(session_factory, review_state="approved")
    before = _row(session_factory, ctx["ordinary_id"])
    receipts_before = len(_receipts(session_factory, ctx["ordinary_id"]))

    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        expected = before.updated_at

        @event.listens_for(session, "before_flush")
        def _boom(_session, _flush_context, _instances):
            raise RuntimeError("forced review revision failure")

        try:
            with pytest.raises(Exception):
                service.transition_review(
                    memory_id=ctx["ordinary_id"],
                    expected_updated_at=expected,
                    action=ACTION_REJECT,
                )
        finally:
            event.remove(session, "before_flush", _boom)
        session.rollback()

    after = _row(session_factory, ctx["ordinary_id"])
    assert after.review_state == before.review_state
    assert after.reviewed_at == before.reviewed_at
    assert after.updated_at == before.updated_at
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []
    assert len(_receipts(session_factory, ctx["ordinary_id"])) == receipts_before


def test_forced_receipt_failure_rolls_back(session_factory):
    ctx = _make(session_factory, review_state="approved")
    before = _row(session_factory, ctx["ordinary_id"])
    receipts_before = len(_receipts(session_factory, ctx["ordinary_id"]))

    with session_factory() as session:
        service = _service(session_factory)(session, authenticated_account_id=ACCOUNT_A)
        expected = before.updated_at
        # Force failure at the receipt stage only.
        original_build = service._build_receipt

        def _boom(*args, **kwargs):
            raise RuntimeError("forced receipt failure")

        service._build_receipt = _boom  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="forced receipt failure"):
            service.transition_review(
                memory_id=ctx["ordinary_id"],
                expected_updated_at=expected,
                action=ACTION_REJECT,
            )
        session.rollback()
        assert original_build is not None

    after = _row(session_factory, ctx["ordinary_id"])
    assert after.review_state == before.review_state
    assert after.reviewed_at == before.reviewed_at
    assert after.updated_at == before.updated_at
    # The staged review revision rolled back with the state change.
    assert _review_revisions(session_factory, ctx["ordinary_id"]) == []
    assert len(_receipts(session_factory, ctx["ordinary_id"])) == receipts_before


# ---------------------------------------------------------------------------
# Readback.
# ---------------------------------------------------------------------------


def test_changed_success_returns_canonical_readback(session_factory):
    ctx = _make(session_factory, review_state="pending")
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_DISPUTE
    )
    assert result.item.identity.canonical_memory_id == ctx["ordinary_id"]
    assert result.item.review_posture == "disputed"
    assert result.item.content == CONTENT
    assert result.item.lifecycle_posture == "active"


def test_noop_returns_canonical_unchanged_item(session_factory):
    ctx = _make(session_factory, review_state="rejected")
    result = _fresh(
        _service(session_factory), session_factory, ctx["ordinary_id"], ACTION_REJECT
    )
    assert result.changed is False
    assert result.item.review_posture == "rejected"
    assert result.item.content == CONTENT
