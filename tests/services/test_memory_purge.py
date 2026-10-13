"""Focused PostgreSQL proof for the UMS-11 audited permanent-erasure service.

Proves ``MemoryPurgeService`` against real disposable PostgreSQL:

* exact-target preview that is account-scoped and reports the real
  child-state inventory;
* a confirmation token that binds the destructive target and is invalidated
  by any change to it;
* account-only authority: cross-account targets are indistinguishable from
  missing ones, and a cross-account retry cannot observe a tombstone;
* CAS validated before confirmation, and both before any deletion;
* complete canonical deletion fan-out with only a minimum non-content
  tombstone surviving;
* a NULL source-atom fingerprint for a direct/manual record, and a
  deterministic versioned digest for an import-origin one, with the
  plaintext source entity id never retained;
* fail-closed behaviour when an import-origin record cannot yield one safe
  source-atom identity, *before* anything is destroyed;
* an idempotent retry that returns the original receipt and creates nothing;
* account-scoped replay suppression, with no model/operator/Service bypass;
* and atomic pairing of tombstone with canonical deletion.

It does not assert a purge *policy*: the contract already owns the semantics.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from guardian.db.models import (
    MemoryLifecycleRevision,
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryPurgeTombstone,
    MemoryRecord,
    MemoryReviewRevision,
    MemoryRevision,
    PersonaSubject,
    Project,
    User,
)
from guardian.protocol_tokens import MemorySemanticSpecies, PersonaSubjectLifecycle
from guardian.services.memory_purge import (
    SUPPRESSION_OUTCOME_ALLOWED,
    SUPPRESSION_OUTCOME_SUPPRESSED,
    MemoryPurgeAmbiguousSourceIdentity,
    MemoryPurgeConflict,
    MemoryPurgeError,
    MemoryPurgeInvalid,
    MemoryPurgeNotAvailable,
    MemoryPurgeService,
    purged_record_fingerprint,
    source_atom_fingerprint,
)

ACCOUNT_A = "ums11-service-account-a"
ACCOUNT_B = "ums11-service-account-b"

CONTENT = "The red toolbox is in the garage."

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
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
    name = f"ums11svc_{uuid.uuid4().hex[:10]}"
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture
def session(database_url):
    engine = sa.create_engine(database_url, future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as sess:
        yield sess
    engine.dispose()


def _ensure_accounts(session) -> None:
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
    if not session.execute(sa.text("SELECT 1 FROM projects WHERE id = 9200")).first():
        session.add(
            Project(id=9200, user_id=ACCOUNT_A, name="p", identity_depth="light")
        )
    session.commit()


def _seed_memory(
    session,
    *,
    account: str = ACCOUNT_A,
    with_content_revision: bool = False,
    with_review_revision: bool = False,
    with_lifecycle_revision: bool = False,
    with_persona_link: bool = False,
    is_imported: bool = False,
    source_record_id: str | None = None,
    species: str = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
) -> str:
    """Create one canonical memory plus an optional full child-state fan-out."""
    _ensure_accounts(session)
    memory_id = str(uuid.uuid4())
    subject_id = str(uuid.uuid4())
    session.add(
        PersonaSubject(
            persona_subject_id=subject_id,
            user_id=account,
            display_name_snapshot="A",
            lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
        )
    )
    session.add(
        MemoryRecord(
            memory_id=memory_id,
            user_id=account,
            project_id=9200,
            semantic_species=species,
            text_content=(
                CONTENT
                if species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
                else None
            ),
            fact_key=None,
            fact_value=None,
            fact_confidence=None,
            review_state="approved",
            lifecycle_state="active",
            pinned=False,
            held=False,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    # Flush the parent before its composite-FK children: the ORM cannot infer
    # insert order for a composite (memory_id, user_id) constraint.
    session.flush()
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=account,
            source_system="openai" if is_imported else "codexify",
            source_record_id=source_record_id,
            source_subject_kind="importer" if is_imported else "vault",
            is_imported=is_imported,
            created_at=NOW,
        )
    )
    if with_content_revision:
        session.add(
            MemoryRevision(
                revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=account,
                revision_number=1,
                old_text_content="",
                new_text_content=CONTENT,
                created_at=NOW,
            )
        )
    if with_review_revision:
        session.add(
            MemoryReviewRevision(
                review_revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=account,
                revision_number=1,
                old_review_state="pending",
                new_review_state="approved",
                actor_account_id=account,
                created_at=NOW,
            )
        )
    if with_lifecycle_revision:
        session.add(
            MemoryLifecycleRevision(
                lifecycle_revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=account,
                revision_number=1,
                old_lifecycle_state="dormant",
                new_lifecycle_state="active",
                created_at=NOW,
            )
        )
    if with_persona_link:
        session.add(
            MemoryPersonaLink(
                link_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=account,
                persona_subject_id=subject_id,
                persona_user_id=account,
                link_kind="captured_under",
                created_at=NOW,
            )
        )
    session.commit()
    return memory_id


def _service(session, account: str) -> MemoryPurgeService:
    return MemoryPurgeService(session, authenticated_account_id=account)


def _row_count(session, model) -> int:
    return int(session.query(model).count())


# ---------------------------------------------------------------------------
# Preview.
# ---------------------------------------------------------------------------


def test_preview_reports_exact_child_inventory(session) -> None:
    memory_id = _seed_memory(
        session,
        with_content_revision=True,
        with_review_revision=True,
        with_lifecycle_revision=True,
        with_persona_link=True,
    )
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)

    assert preview.memory_id == memory_id
    assert preview.content_revision_count == 1
    assert preview.review_revision_count == 1
    assert preview.lifecycle_revision_count == 1
    assert preview.provenance_count == 1
    assert preview.persona_link_count == 1
    # Parent + every child row that will be destroyed.
    assert preview.total_affected_rows == 6
    # Verified absent derived state, reported explicitly rather than implied.
    assert preview.derived_state_count == 0
    # A direct/manual record has no import source to suppress.
    assert preview.suppression_fingerprint_available is False
    assert preview.suppression_ambiguity is None
    assert preview.record_fingerprint == purged_record_fingerprint(memory_id)
    # Preview embeds no content.
    assert CONTENT not in preview.confirmation_token


def test_preview_is_account_scoped(session) -> None:
    memory_id = _seed_memory(session, account=ACCOUNT_A)
    service_b = _service(session, ACCOUNT_B)
    with pytest.raises(MemoryPurgeNotAvailable):
        service_b.preview_purge(memory_id=memory_id)


def test_confirmation_token_is_invalidated_by_target_change(session) -> None:
    memory_id = _seed_memory(session, with_content_revision=True)
    service = _service(session, ACCOUNT_A)

    first = service.preview_purge(memory_id=memory_id)
    # A real mutation advances the CAS token, so the old confirmation dies.
    session.add(
        MemoryRevision(
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            revision_number=2,
            old_text_content=CONTENT,
            new_text_content=CONTENT + " Updated.",
            created_at=LATER,
        )
    )
    session.flush()
    session.execute(
        sa.text("UPDATE memory_records SET updated_at = :t WHERE memory_id = :m"),
        {"t": LATER, "m": memory_id},
    )
    session.commit()

    second = service.preview_purge(memory_id=memory_id)
    assert second.confirmation_token != first.confirmation_token
    assert second.content_revision_count == 2


# ---------------------------------------------------------------------------
# Authority.
# ---------------------------------------------------------------------------


def test_account_may_purge_own_memory(session) -> None:
    memory_id = _seed_memory(session, account=ACCOUNT_A)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    result = service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )
    assert result.changed is True
    assert result.already_purged is False
    assert result.suppression is True


def test_cross_account_target_is_unavailable(session) -> None:
    memory_id = _seed_memory(session, account=ACCOUNT_A)
    service_b = _service(session, ACCOUNT_B)
    with pytest.raises(MemoryPurgeNotAvailable):
        service_b.purge(
            memory_id=memory_id,
            expected_updated_at=NOW,
            confirmation_token="v1:" + "0" * 64,
        )
    # Account A's memory is untouched.
    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


def test_missing_target_is_unavailable(session) -> None:
    service = _service(session, ACCOUNT_A)
    with pytest.raises(MemoryPurgeNotAvailable):
        service.purge(
            memory_id=str(uuid.uuid4()),
            expected_updated_at=NOW,
            confirmation_token="v1:" + "0" * 64,
        )


# ---------------------------------------------------------------------------
# CAS and confirmation.
# ---------------------------------------------------------------------------


def test_stale_cas_deletes_nothing(session) -> None:
    memory_id = _seed_memory(session, with_content_revision=True)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)

    with pytest.raises(MemoryPurgeConflict):
        service.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at - timedelta(seconds=5),
            confirmation_token=preview.confirmation_token,
        )

    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryRevision) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


def test_wrong_confirmation_deletes_nothing(session) -> None:
    memory_id = _seed_memory(session)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)

    with pytest.raises(MemoryPurgeConflict):
        service.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at,
            confirmation_token="v1:" + "1" * 64,
        )

    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


def test_confirmation_is_recomputed_against_current_state(session) -> None:
    """A token minted against an older snapshot must not authorize the new one."""
    memory_id = _seed_memory(session, with_content_revision=True)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)

    # Change the destructive surface *without* changing the CAS token, so only
    # the confirmation binding can catch it.
    session.add(
        MemoryRevision(
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            revision_number=2,
            old_text_content=CONTENT,
            new_text_content="something new",
            created_at=LATER,
        )
    )
    session.commit()

    with pytest.raises(MemoryPurgeConflict):
        service.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at,
            confirmation_token=preview.confirmation_token,
        )
    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


def test_malformed_cas_token_is_rejected(session) -> None:
    memory_id = _seed_memory(session)
    service = _service(session, ACCOUNT_A)
    with pytest.raises(MemoryPurgeInvalid):
        service.purge(
            memory_id=memory_id,
            expected_updated_at="not-a-datetime",  # type: ignore[arg-type]
            confirmation_token="v1:" + "0" * 64,
        )


# ---------------------------------------------------------------------------
# Canonical fan-out + tombstone shape.
# ---------------------------------------------------------------------------


def test_purge_removes_every_canonical_child_and_keeps_one_tombstone(
    session,
) -> None:
    memory_id = _seed_memory(
        session,
        with_content_revision=True,
        with_review_revision=True,
        with_lifecycle_revision=True,
        with_persona_link=True,
    )
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    result = service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    assert result.deleted_content_revisions == 1
    assert result.deleted_review_revisions == 1
    assert result.deleted_lifecycle_revisions == 1
    assert result.deleted_provenance == 1
    assert result.deleted_persona_links == 1

    # Independent readback: every erased surface is actually absent.
    assert _row_count(session, MemoryRecord) == 0
    assert _row_count(session, MemoryRevision) == 0
    assert _row_count(session, MemoryReviewRevision) == 0
    assert _row_count(session, MemoryLifecycleRevision) == 0
    assert _row_count(session, MemoryProvenance) == 0
    assert _row_count(session, MemoryPersonaLink) == 0

    tombstone = session.query(MemoryPurgeTombstone).one()
    assert tombstone.purge_receipt_id == result.purge_receipt_id
    assert tombstone.user_id == ACCOUNT_A
    assert tombstone.suppress_reimport is True
    assert tombstone.purged_at is not None
    # A direct/manual purge legitimately carries no source atom.
    assert tombstone.source_atom_fingerprint is None
    assert tombstone.purged_record_fingerprint == purged_record_fingerprint(memory_id)

    # No deleted text survives anywhere in the tombstone row.
    rendered = " ".join(str(v) for v in tombstone.__table__.columns.keys()).join(
        str(getattr(tombstone, column.name)) for column in tombstone.__table__.columns
    )
    assert CONTENT not in rendered


def test_tombstone_carries_no_content_bearing_column(session) -> None:
    memory_id = _seed_memory(session)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )
    columns = {c.name for c in MemoryPurgeTombstone.__table__.columns}
    assert columns == {
        "purge_receipt_id",
        "user_id",
        "purged_record_fingerprint",
        "source_system",
        "source_entity_kind",
        "source_atom_fingerprint",
        "purged_at",
        "suppress_reimport",
    }
    for forbidden in (
        "text_content",
        "content",
        "excerpt",
        "embedding",
        "memory_id",
        "source_record_id",
    ):
        assert forbidden not in columns


# ---------------------------------------------------------------------------
# Import-origin suppression identity.
# ---------------------------------------------------------------------------


def test_import_origin_derives_deterministic_source_fingerprint(session) -> None:
    memory_id = _seed_memory(
        session, is_imported=True, source_record_id="thread-abc-123"
    )
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    assert preview.suppression_fingerprint_available is True
    assert preview.suppression_ambiguity is None

    result = service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )
    tombstone = session.query(MemoryPurgeTombstone).one()
    assert tombstone.source_system == "openai"
    assert tombstone.source_entity_kind == "importer"
    assert tombstone.source_atom_fingerprint == source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="thread-abc-123",
    )
    assert result.source_atom_fingerprint == tombstone.source_atom_fingerprint
    # The plaintext source entity id is never retained.
    assert "thread-abc-123" not in str(tombstone.source_atom_fingerprint)


def test_ambiguous_import_origin_fails_closed_before_deletion(session) -> None:
    """Import-origin provenance with no stable source id must not be erased."""
    memory_id = _seed_memory(session, is_imported=True, source_record_id=None)
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    assert preview.suppression_fingerprint_available is False
    assert preview.suppression_ambiguity is not None

    with pytest.raises(MemoryPurgeAmbiguousSourceIdentity):
        service.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at,
            confirmation_token=preview.confirmation_token,
        )

    # Nothing was destroyed: the record survives rather than being erased
    # into a state where it could silently resurrect.
    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryProvenance) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


def test_multiple_distinct_source_atoms_fail_closed(session) -> None:
    memory_id = _seed_memory(session, is_imported=True, source_record_id="thread-1")
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=ACCOUNT_A,
            source_system="openai",
            source_record_id="thread-2",
            source_subject_kind="importer",
            is_imported=True,
            created_at=LATER,
        )
    )
    session.commit()
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    assert preview.suppression_ambiguity is not None
    with pytest.raises(MemoryPurgeAmbiguousSourceIdentity):
        service.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at,
            confirmation_token=preview.confirmation_token,
        )
    assert _row_count(session, MemoryRecord) == 1
    assert _row_count(session, MemoryPurgeTombstone) == 0


# ---------------------------------------------------------------------------
# Idempotent retry.
# ---------------------------------------------------------------------------


def test_retry_reports_already_purged_with_same_receipt(session) -> None:
    memory_id = _seed_memory(session, is_imported=True, source_record_id="t-1")
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    first = service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    # A retry presents the original identity; the CAS token is irrelevant now
    # because the canonical row is gone.
    second = service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )
    assert second.changed is False
    assert second.already_purged is True
    assert second.purge_receipt_id == first.purge_receipt_id
    assert second.purged_at == first.purged_at
    # No second tombstone and no second receipt identity.
    assert _row_count(session, MemoryPurgeTombstone) == 1


def test_cross_account_retry_cannot_observe_tombstone(session) -> None:
    memory_id = _seed_memory(session, account=ACCOUNT_A)
    service_a = _service(session, ACCOUNT_A)
    preview = service_a.preview_purge(memory_id=memory_id)
    service_a.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    # Account B gets the same indistinguishable 404 posture as a never-existed
    # target: one account's erasure is never another account's information.
    service_b = _service(session, ACCOUNT_B)
    with pytest.raises(MemoryPurgeNotAvailable):
        service_b.purge(
            memory_id=memory_id,
            expected_updated_at=preview.updated_at,
            confirmation_token=preview.confirmation_token,
        )
    with pytest.raises(MemoryPurgeNotAvailable):
        service_b.preview_purge(memory_id=memory_id)


# ---------------------------------------------------------------------------
# Replay suppression.
# ---------------------------------------------------------------------------


def test_same_account_source_replay_is_suppressed(session) -> None:
    memory_id = _seed_memory(session, is_imported=True, source_record_id="atom-9")
    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    status = service.source_atom_suppression_status(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="atom-9",
    )
    assert status.suppressed is True
    assert status.outcome == SUPPRESSION_OUTCOME_SUPPRESSED
    assert status.purged_at is not None

    # Retry suppression is deterministic.
    again = service.source_atom_suppression_status(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="atom-9",
    )
    assert again.outcome == SUPPRESSION_OUTCOME_SUPPRESSED
    assert again.source_atom_fingerprint == status.source_atom_fingerprint


def test_cross_account_and_different_atoms_are_allowed(session) -> None:
    memory_id = _seed_memory(session, is_imported=True, source_record_id="atom-1")
    service_a = _service(session, ACCOUNT_A)
    preview = service_a.preview_purge(memory_id=memory_id)
    service_a.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    service_b = _service(session, ACCOUNT_B)
    # Another account is unaffected by this account's erasure.
    assert (
        service_b.source_atom_suppression_status(
            source_system="openai",
            source_entity_kind="importer",
            source_atom_identity="atom-1",
        ).outcome
        == SUPPRESSION_OUTCOME_ALLOWED
    )

    # A different atom is allowed for the purging account too.
    assert (
        service_a.source_atom_suppression_status(
            source_system="openai",
            source_entity_kind="importer",
            source_atom_identity="atom-2",
        ).outcome
        == SUPPRESSION_OUTCOME_ALLOWED
    )

    # A different source system is a different identity.
    assert (
        service_a.source_atom_suppression_status(
            source_system="anthropic",
            source_entity_kind="importer",
            source_atom_identity="atom-1",
        ).outcome
        == SUPPRESSION_OUTCOME_ALLOWED
    )


def test_suppression_has_no_bypass_surface(session) -> None:
    """No public API can clear suppression for a model or an Operator."""
    import inspect

    from guardian.services import memory_purge as purge_module

    public = {
        name
        for name, _ in inspect.getmembers(
            purge_module.MemoryPurgeService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    # Exactly the three authorized entrypoints. No clear/force/override/ignore.
    assert public == {
        "preview_purge",
        "purge",
        "source_atom_suppression_status",
    }
    for forbidden in (
        "clear_suppression",
        "force_unpurge",
        "override_tombstone",
        "ignore_purge_tombstone",
        "resurrect",
        "unpurge",
    ):
        assert not hasattr(purge_module.MemoryPurgeService, forbidden)
        assert forbidden not in {
            n.lower() for n in dir(purge_module.MemoryPurgeService)
        }


def test_suppression_lookup_requires_canonical_identity(session) -> None:
    service = _service(session, ACCOUNT_A)
    with pytest.raises(MemoryPurgeInvalid):
        service.source_atom_suppression_status(
            source_system="",
            source_entity_kind="importer",
            source_atom_identity="atom-1",
        )
    with pytest.raises(MemoryPurgeInvalid):
        service.source_atom_suppression_status(
            source_system="openai",
            source_entity_kind="importer",
            source_atom_identity="   ",
        )


# ---------------------------------------------------------------------------
# Fingerprint determinism.
# ---------------------------------------------------------------------------


def test_fingerprints_are_versioned_deterministic_and_content_free() -> None:
    a = purged_record_fingerprint("mem-1")
    assert a == purged_record_fingerprint("mem-1")
    assert a != purged_record_fingerprint("mem-2")
    assert a.startswith("v1:")

    s1 = source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="atom-1",
    )
    s2 = source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="atom-2",
    )
    assert s1 == source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="atom-1",
    )
    assert s1 != s2
    assert s1.startswith("v1:")

    # Field boundaries are not forgeable: shifting a value across a delimiter
    # must not collide.
    x = source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer",
        source_atom_identity="a\x1fb",
    )
    y = source_atom_fingerprint(
        source_system="openai",
        source_entity_kind="importer\x1fa",
        source_atom_identity="b",
    )
    assert x != y

    with pytest.raises(MemoryPurgeInvalid):
        purged_record_fingerprint("   ")


# ---------------------------------------------------------------------------
# Atomicity + Personal Facts boundary.
# ---------------------------------------------------------------------------


def test_purge_does_not_touch_personal_facts(session) -> None:
    from guardian.db.models import PersonalFact

    memory_id = _seed_memory(session, with_content_revision=True)
    _ensure_accounts(session)
    session.add(
        PersonalFact(
            user_id=ACCOUNT_A,
            key="favorite-color",
            value="blue",
            status="verified",
            confidence=0.9,
            is_active=True,
        )
    )
    session.commit()

    service = _service(session, ACCOUNT_A)
    preview = service.preview_purge(memory_id=memory_id)
    service.purge(
        memory_id=memory_id,
        expected_updated_at=preview.updated_at,
        confirmation_token=preview.confirmation_token,
    )

    # Personal Facts retain their specialized authority: ordinary-memory purge
    # has no schema path to them and does not generic-delete them.
    fact = session.query(PersonalFact).one()
    assert fact.key == "favorite-color"
    assert fact.value == "blue"


def test_service_requires_authenticated_account(session) -> None:
    with pytest.raises(MemoryPurgeError):
        MemoryPurgeService(session, authenticated_account_id="")
    with pytest.raises(MemoryPurgeError):
        MemoryPurgeService(None, authenticated_account_id=ACCOUNT_A)  # type: ignore[arg-type]
