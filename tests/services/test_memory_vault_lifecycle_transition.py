"""Focused PostgreSQL proof for the UMS-05C10B-W lifecycle transition writer.

Proves ``MemoryVaultMutationService.transition_lifecycle`` against real
disposable PostgreSQL, enforcing ADR-089 exactly:

* only ``retire`` and ``restore`` are admitted; no raw lifecycle target and
  no generic ``set_lifecycle_state`` surface exists;
* the full direct matrix: retire from ``active``/``dormant`` is changed, retire
  on ``retired`` is a no-op, restore on ``active``/``dormant`` is a no-op, and
  restore on ``retired`` resolves its target from canonical history;
* restore is **not** set-active: ``active -> retired -> restore`` returns
  ``active`` and ``dormant -> retired -> restore`` returns ``dormant``;
* a retired record with no reconstructable history fails closed rather than
  guessing ``active`` or ``dormant``;
* repeated cycles use the immediate history tail;
* CAS is validated before any no-op decision, so a stale token conflicts even
  when the action is already satisfied;
* each changed transition appends exactly one ``memory_lifecycle_revisions`` row
  and exactly one ``memory-vault-mutation.v1`` receipt atomically with the
  state and CAS updates;
* review state, hold, pin, content, project, persona, and both other revision
  families are preserved unchanged;
* malformed history fails closed and is never repaired.
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
    MemoryLifecycleRevision,
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
    ACTION_RESTORE,
    ACTION_RETIRE,
    RECEIPT_SCHEMA,
    MemoryVaultLifecycleIntegrityError,
    MemoryVaultLifecycleInvalid,
    MemoryVaultLifecycleUnsupported,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
)

ACCOUNT_A = "ums05c10bw-account-a"
ACCOUNT_B = "ums05c10bw-account-b"

CONTENT = "The red toolbox is in the garage."

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
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
    name = f"ums05c10bw_{uuid.uuid4().hex[:10]}"
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


def _seed(
    session,
    *,
    lifecycle_state: str = "active",
    review_state: str = "approved",
    pinned: bool = False,
    held: bool = False,
    species: str = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
    account: str = ACCOUNT_A,
) -> str:
    """Create one canonical memory plus its supporting rows."""
    # Idempotent: a test may seed more than one memory in the same database.
    existing = {
        row[0]
        for row in session.execute(
            sa.text("SELECT id FROM users WHERE id IN (:a, :b)"),
            {"a": ACCOUNT_A, "b": ACCOUNT_B},
        ).fetchall()
    }
    for account in (ACCOUNT_A, ACCOUNT_B):
        if account not in existing:
            session.add(
                User(id=account, username=account, password_hash="x", role="guest")
            )
    if not session.execute(
        sa.text("SELECT 1 FROM projects WHERE id = 9100")
    ).fetchone():
        session.add(
            Project(id=9100, user_id=ACCOUNT_A, name="p", identity_depth="light")
        )
    memory_id = str(uuid.uuid4())
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
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            project_id=9100,
            semantic_species=species,
            text_content=(
                CONTENT
                if species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
                else None
            ),
            fact_key=(
                None
                if species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
                else "k"
            ),
            fact_value=(
                None
                if species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
                else "v"
            ),
            fact_confidence=(
                None
                if species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
                else 0.9
            ),
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=pinned,
            held=held,
            review_state=review_state,
            lifecycle_state=lifecycle_state,
        )
    )
    session.commit()
    session.add(
        MemoryPersonaLink(
            link_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            persona_subject_id=subject_id,
            persona_user_id=ACCOUNT_A,
            link_kind=MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
        )
    )
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            source_system="codexify",
            source_subject_kind="vault",
            is_imported=False,
        )
    )
    session.commit()
    return memory_id


def _seed_lifecycle_history(
    session, memory_id: str, transitions: list[tuple[str, str]]
) -> None:
    """Seed canonical lifecycle history directly (persistence layer)."""
    for index, (old_state, new_state) in enumerate(transitions, start=1):
        session.add(
            MemoryLifecycleRevision(
                lifecycle_revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=ACCOUNT_A,
                revision_number=index,
                old_lifecycle_state=old_state,
                new_lifecycle_state=new_state,
            )
        )
    session.commit()


def _make(session_factory, **kwargs):
    with session_factory() as session:
        memory_id = _seed(session, **kwargs)
    return {"session_factory": session_factory, "memory_id": memory_id}


def _make_with_history(session_factory, transitions, **kwargs):
    ctx = _make(session_factory, **kwargs)
    with session_factory() as session:
        _seed_lifecycle_history(session, ctx["memory_id"], transitions)
    return ctx


def _row(session_factory, memory_id, account=ACCOUNT_A):
    with session_factory() as session:
        return session.execute(
            sa.select(MemoryRecord).where(MemoryRecord.memory_id == memory_id)
        ).scalar_one_or_none()


def _lifecycle_revisions(session_factory, memory_id):
    with session_factory() as session:
        return list(
            session.execute(
                sa.select(MemoryLifecycleRevision)
                .where(MemoryLifecycleRevision.memory_id == memory_id)
                .order_by(MemoryLifecycleRevision.revision_number.asc())
            ).scalars()
        )


def _receipts(session_factory, memory_id):
    with session_factory() as session:
        return list(
            session.execute(
                sa.select(MemoryProvenance).where(
                    MemoryProvenance.memory_id == memory_id
                )
            ).scalars()
        )


def _fresh_token(session_factory, memory_id):
    """Read the row's real current CAS token."""
    with session_factory() as session:
        return session.execute(
            sa.select(MemoryRecord.updated_at).where(
                MemoryRecord.memory_id == memory_id
            )
        ).scalar_one()


def _call(session_factory, memory_id, action, *, account=ACCOUNT_A, expected=None):
    with session_factory() as session:
        if expected is None:
            expected = session.execute(
                sa.select(MemoryRecord.updated_at).where(
                    MemoryRecord.memory_id == memory_id
                )
            ).scalar_one()
        return MemoryVaultMutationService(
            session, authenticated_account_id=account
        ).transition_lifecycle(
            memory_id=memory_id,
            expected_updated_at=expected,
            action=action,
        )


# ---------------------------------------------------------------------------
# Authority and admission.
# ---------------------------------------------------------------------------


def test_account_can_retire_own_ordinary_memory(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert result.changed is True
    assert result.previous_lifecycle_state == "active"
    assert result.resulting_lifecycle_state == "retired"
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "retired"


def test_missing_memory_is_unavailable(session_factory):
    ctx = _make(session_factory)
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultMutationNotAvailable):
            service.transition_lifecycle(
                memory_id="00000000-0000-0000-0000-000000000000",
                expected_updated_at=NOW,
                action=ACTION_RETIRE,
            )
    assert ctx["memory_id"]


def test_cross_account_has_same_unavailable_posture(session_factory):
    ctx = _make(session_factory)
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_B
        )
        with pytest.raises(MemoryVaultMutationNotAvailable):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=NOW,
                action=ACTION_RETIRE,
            )


def test_personal_fact_species_is_refused(session_factory):
    ctx = _make(
        session_factory,
        species=MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value,
    )
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleUnsupported):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RETIRE,
            )
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []


@pytest.mark.parametrize(
    "bad", ["active", "dormant", "retired", "activate", "", None, 7]
)
def test_no_raw_lifecycle_target_or_unknown_action_is_admitted(session_factory, bad):
    ctx = _make(session_factory, lifecycle_state="active")
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleInvalid):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=NOW,
                action=bad,
            )
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []


def test_service_exposes_no_generic_set_lifecycle_state(session_factory):
    service_names = {
        n for n in dir(MemoryVaultMutationService) if not n.startswith("_")
    }
    assert "set_lifecycle_state" not in service_names
    assert "activate" not in service_names
    assert "reactivate" not in service_names
    assert "transition_lifecycle" in service_names


# ---------------------------------------------------------------------------
# Retire matrix.
# ---------------------------------------------------------------------------


def test_active_retire_is_changed(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert (result.changed, result.resulting_lifecycle_state) == (True, "retired")


def test_dormant_retire_is_changed(session_factory):
    ctx = _make(session_factory, lifecycle_state="dormant")
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert (result.changed, result.resulting_lifecycle_state) == (True, "retired")


def test_retired_retire_is_noop(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    before = _row(session_factory, ctx["memory_id"])
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)

    assert result.changed is False
    assert result.receipt_id is None
    assert result.lifecycle_revision_id is None
    assert result.lifecycle_revision_number is None
    assert result.previous_lifecycle_state == result.resulting_lifecycle_state
    assert result.previous_updated_at == result.resulting_updated_at
    after = _row(session_factory, ctx["memory_id"])
    assert after.updated_at == before.updated_at
    # No retired -> retired history is invented.
    assert len(_lifecycle_revisions(session_factory, ctx["memory_id"])) == 1


# ---------------------------------------------------------------------------
# Restore matrix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["active", "dormant"])
def test_restore_on_non_retired_is_noop(session_factory, state):
    ctx = _make(session_factory, lifecycle_state=state)
    before = _row(session_factory, ctx["memory_id"])
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)

    assert result.changed is False
    assert result.receipt_id is None
    assert result.lifecycle_revision_id is None
    assert result.lifecycle_revision_number is None
    assert result.previous_lifecycle_state == result.resulting_lifecycle_state == state
    after = _row(session_factory, ctx["memory_id"])
    assert after.updated_at == before.updated_at
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []


def test_restore_returns_active_when_history_proves_active(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)

    assert result.changed is True
    assert result.previous_lifecycle_state == "retired"
    assert result.resulting_lifecycle_state == "active"
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "active"
    assert result.lifecycle_revision_number == 2


def test_restore_returns_dormant_when_history_proves_dormant(session_factory):
    ctx = _make_with_history(
        session_factory, [("dormant", "retired")], lifecycle_state="retired"
    )
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)

    # Restore is NOT set-active: dormant stays dormant.
    assert result.resulting_lifecycle_state == "dormant"
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "dormant"


def test_two_retirement_postures_stay_distinct(session_factory):
    from_active = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    from_dormant = _make_with_history(
        session_factory, [("dormant", "retired")], lifecycle_state="retired"
    )
    _call(session_factory, from_active["memory_id"], ACTION_RESTORE)
    _call(session_factory, from_dormant["memory_id"], ACTION_RESTORE)

    assert _row(session_factory, from_active["memory_id"]).lifecycle_state == "active"
    assert _row(session_factory, from_dormant["memory_id"]).lifecycle_state == "dormant"


def test_repeated_cycle_uses_immediate_history_tail(session_factory):
    ctx = _make_with_history(
        session_factory,
        [("active", "retired"), ("retired", "active")],
        lifecycle_state="active",
    )
    # Third transition retires again, from active.
    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)

    # Tail is 3: active -> retired, so restore returns active.
    assert result.resulting_lifecycle_state == "active"
    assert result.lifecycle_revision_number == 4


# ---------------------------------------------------------------------------
# Restore history gate.
# ---------------------------------------------------------------------------


def test_zero_history_retired_restore_fails_closed(session_factory):
    ctx = _make(session_factory, lifecycle_state="retired")
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleIntegrityError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RESTORE,
            )
    # Neither active nor dormant was guessed.
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "retired"
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []


def test_gapped_lifecycle_history_fails_closed(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    with session_factory() as session:
        session.add(
            MemoryLifecycleRevision(
                lifecycle_revision_id=str(uuid.uuid4()),
                memory_id=ctx["memory_id"],
                user_id=ACCOUNT_A,
                revision_number=3,  # gap: 1, 3
                old_lifecycle_state="retired",
                new_lifecycle_state="active",
            )
        )
        session.commit()
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleIntegrityError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RESTORE,
            )


def test_broken_history_chain_fails_closed(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    with session_factory() as session:
        session.add(
            MemoryLifecycleRevision(
                lifecycle_revision_id=str(uuid.uuid4()),
                memory_id=ctx["memory_id"],
                user_id=ACCOUNT_A,
                revision_number=2,
                old_lifecycle_state="dormant",  # chain break
                new_lifecycle_state="active",
            )
        )
        session.commit()
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleIntegrityError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RESTORE,
            )


def test_history_tail_state_mismatch_fails_closed(session_factory):
    # History tail ends in "dormant" but the parent says "retired".
    ctx = _make_with_history(
        session_factory, [("active", "dormant")], lifecycle_state="retired"
    )
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleIntegrityError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RESTORE,
            )
    # History is never repaired to match the parent.
    assert len(_lifecycle_revisions(session_factory, ctx["memory_id"])) == 1


def test_restore_does_not_read_provenance_for_posture(session_factory):
    """A provenance claim of prior posture is not authority."""
    ctx = _make(session_factory, lifecycle_state="retired")
    with session_factory() as session:
        session.execute(
            sa.text(
                "UPDATE memory_provenance SET extensions = :ext " "WHERE memory_id = :m"
            ),
            {
                "ext": '{"lifecycle_history": ["active", "retired"]}',
                "m": ctx["memory_id"],
            },
        )
        session.commit()
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultLifecycleIntegrityError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=_fresh_token(session_factory, ctx["memory_id"]),
                action=ACTION_RESTORE,
            )
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "retired"


# ---------------------------------------------------------------------------
# CAS.
# ---------------------------------------------------------------------------


def test_stale_cas_conflicts_on_changed_retire(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultMutationConflict):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=NOW,  # stale
                action=ACTION_RETIRE,
            )
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "active"


def test_stale_cas_conflicts_even_on_already_satisfied_retire(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultMutationConflict):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=NOW,  # stale, even though retire is a no-op
                action=ACTION_RETIRE,
            )
    assert len(_lifecycle_revisions(session_factory, ctx["memory_id"])) == 1


def test_stale_cas_conflicts_even_on_already_satisfied_restore(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultMutationConflict):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=NOW,  # stale, even though restore is a no-op
                action=ACTION_RESTORE,
            )
    assert _row(session_factory, ctx["memory_id"]).lifecycle_state == "active"


def test_naive_cas_is_rejected(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        with pytest.raises(MemoryVaultMutationError):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=datetime(2026, 9, 29, 12, 0),
                action=ACTION_RETIRE,
            )


def test_changed_transition_advances_cas(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    before = _row(session_factory, ctx["memory_id"]).updated_at
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    after = _row(session_factory, ctx["memory_id"]).updated_at
    assert after > before
    assert result.resulting_updated_at == after


# ---------------------------------------------------------------------------
# Lifecycle revisions.
# ---------------------------------------------------------------------------


def test_first_retire_from_zero_history_gets_revision_one(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert result.lifecycle_revision_number == 1
    revisions = _lifecycle_revisions(session_factory, ctx["memory_id"])
    assert len(revisions) == 1
    assert revisions[0].old_lifecycle_state == "active"
    assert revisions[0].new_lifecycle_state == "retired"
    assert revisions[0].created_at is not None  # server/database authored


def test_second_changed_transition_increments_revision(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    assert result.lifecycle_revision_number == 2
    revisions = _lifecycle_revisions(session_factory, ctx["memory_id"])
    assert [r.revision_number for r in revisions] == [1, 2]
    # Chain continuity.
    assert revisions[0].new_lifecycle_state == revisions[1].old_lifecycle_state


def test_lifecycle_numbering_is_independent_of_other_families(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    with session_factory() as session:
        session.add(
            MemoryRevision(
                revision_id=str(uuid.uuid4()),
                memory_id=ctx["memory_id"],
                user_id=ACCOUNT_A,
                revision_number=1,
                old_text_content="a",
                new_text_content="b",
            )
        )
        session.add(
            MemoryReviewRevision(
                review_revision_id=str(uuid.uuid4()),
                memory_id=ctx["memory_id"],
                user_id=ACCOUNT_A,
                revision_number=1,
                old_review_state="pending",
                new_review_state="approved",
                actor_account_id=ACCOUNT_A,
            )
        )
        session.commit()
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    # Each family numbers independently from 1.
    assert result.lifecycle_revision_number == 1


# ---------------------------------------------------------------------------
# Receipt.
# ---------------------------------------------------------------------------


def test_changed_transition_creates_exactly_one_receipt(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    result = _call(
        session_factory,
        ctx["memory_id"],
        ACTION_RETIRE,
    )
    receipts = _receipts(session_factory, ctx["memory_id"])
    # One seeded creation receipt plus exactly one mutation receipt.
    assert len(receipts) == 2
    receipt = next(r for r in receipts if r.provenance_id == result.receipt_id)
    ext = receipt.extensions
    assert ext["receipt_schema"] == RECEIPT_SCHEMA
    assert ext["action"] == ACTION_RETIRE
    assert ext["actor_account_id"] == ACCOUNT_A
    assert ext["previous_values"]["lifecycle_state"] == "active"
    assert ext["new_values"]["lifecycle_state"] == "retired"
    assert ext["new_values"]["lifecycle_revision_id"] == (result.lifecycle_revision_id)
    assert ext["new_values"]["lifecycle_revision_number"] == 1
    # No authored memory content in the receipt.
    assert CONTENT not in str(ext)


def test_restore_receipt_action_is_restore(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    receipt = next(
        r
        for r in _receipts(session_factory, ctx["memory_id"])
        if r.provenance_id == result.receipt_id
    )
    assert receipt.extensions["action"] == ACTION_RESTORE
    assert receipt.extensions["new_values"]["lifecycle_state"] == "active"


def test_noop_creates_no_receipt(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    # Only the seeded creation receipt.
    assert len(_receipts(session_factory, ctx["memory_id"])) == 1


# ---------------------------------------------------------------------------
# Independence.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "review_state", ["approved", "pending", "rejected", "disputed"]
)
def test_review_state_is_preserved_through_retire(session_factory, review_state):
    ctx = _make(session_factory, lifecycle_state="active", review_state=review_state)
    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert _row(session_factory, ctx["memory_id"]).review_state == review_state


@pytest.mark.parametrize(
    "review_state", ["approved", "pending", "rejected", "disputed"]
)
def test_review_state_is_preserved_through_restore(session_factory, review_state):
    ctx = _make_with_history(
        session_factory,
        [("active", "retired")],
        lifecycle_state="retired",
        review_state=review_state,
    )
    _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    row = _row(session_factory, ctx["memory_id"])
    # Restore never auto-approves.
    assert row.review_state == review_state
    assert row.lifecycle_state == "active"


def test_held_memory_can_retire_and_restore(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired", held=True
    )
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    row = _row(session_factory, ctx["memory_id"])
    # Hold never blocks explicit user actions and is never cleared.
    assert result.changed is True
    assert row.held is True
    assert row.lifecycle_state == "active"

    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert _row(session_factory, ctx["memory_id"]).held is True


def test_pinned_memory_keeps_pin(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired", pinned=True
    )
    _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    row = _row(session_factory, ctx["memory_id"])
    assert row.pinned is True
    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert _row(session_factory, ctx["memory_id"]).pinned is True


def test_content_project_and_persona_are_preserved(session_factory):
    ctx = _make_with_history(
        session_factory, [("active", "retired")], lifecycle_state="retired"
    )
    with session_factory() as session:
        links_before = session.execute(
            sa.select(sa.func.count()).select_from(MemoryPersonaLink)
        ).scalar_one()
    _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    row = _row(session_factory, ctx["memory_id"])
    assert row.text_content == CONTENT
    assert row.project_id == 9100
    assert row.semantic_species == (
        MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    )
    with session_factory() as session:
        links_after = session.execute(
            sa.select(sa.func.count()).select_from(MemoryPersonaLink)
        ).scalar_one()
    assert links_after == links_before


# ---------------------------------------------------------------------------
# Atomicity.
# ---------------------------------------------------------------------------


def test_forced_lifecycle_revision_failure_rolls_back(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    before = _row(session_factory, ctx["memory_id"])
    receipts_before = len(_receipts(session_factory, ctx["memory_id"]))

    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        expected = before.updated_at

        @event.listens_for(session, "before_flush")
        def _boom(_session, _flush_context, _instances):
            raise RuntimeError("forced lifecycle revision failure")

        try:
            with pytest.raises(Exception):
                service.transition_lifecycle(
                    memory_id=ctx["memory_id"],
                    expected_updated_at=expected,
                    action=ACTION_RETIRE,
                )
        finally:
            event.remove(session, "before_flush", _boom)
        session.rollback()

    after = _row(session_factory, ctx["memory_id"])
    assert after.lifecycle_state == before.lifecycle_state
    assert after.review_state == before.review_state
    assert after.updated_at == before.updated_at
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []
    assert len(_receipts(session_factory, ctx["memory_id"])) == receipts_before


def test_forced_receipt_failure_rolls_back(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    before = _row(session_factory, ctx["memory_id"])
    receipts_before = len(_receipts(session_factory, ctx["memory_id"]))

    with session_factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )
        expected = before.updated_at

        def _boom(*args, **kwargs):
            raise RuntimeError("forced lifecycle receipt failure")

        service._build_receipt = _boom  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="forced lifecycle receipt failure"):
            service.transition_lifecycle(
                memory_id=ctx["memory_id"],
                expected_updated_at=expected,
                action=ACTION_RETIRE,
            )
        session.rollback()

    after = _row(session_factory, ctx["memory_id"])
    assert after.lifecycle_state == before.lifecycle_state
    assert after.updated_at == before.updated_at
    # The staged lifecycle revision rolled back with the state change.
    assert _lifecycle_revisions(session_factory, ctx["memory_id"]) == []
    assert len(_receipts(session_factory, ctx["memory_id"])) == receipts_before


# ---------------------------------------------------------------------------
# Readback.
# ---------------------------------------------------------------------------


def test_changed_result_returns_canonical_readback(session_factory):
    ctx = _make(session_factory, lifecycle_state="active")
    result = _call(session_factory, ctx["memory_id"], ACTION_RETIRE)
    assert result.item.identity.canonical_memory_id == ctx["memory_id"]
    assert result.item.lifecycle_posture == "retired"
    assert result.item.review_posture == "approved"
    assert result.item.content == CONTENT


def test_noop_returns_canonical_unchanged_readback(session_factory):
    ctx = _make(session_factory, lifecycle_state="dormant")
    result = _call(session_factory, ctx["memory_id"], ACTION_RESTORE)
    assert result.changed is False
    assert result.item.lifecycle_posture == "dormant"
    assert result.item.content == CONTENT
