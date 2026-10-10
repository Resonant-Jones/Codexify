"""Focused PostgreSQL proof for the UMS-05C9-W content-correction writer.

Proves ``MemoryVaultMutationService.correct_content`` against real
disposable PostgreSQL:

* account-bound ordinary-memory correction succeeds;
* exact old/new text land in revision 1, then contiguous revision 2;
* canonical text, whitespace, line breaks, and Unicode are preserved;
* revision ID/number are server generated;
* each changed correction emits exactly one ``memory-vault-mutation.v1``
  receipt that references the revision without duplicating content;
* exact no-op creates neither revision nor receipt and never advances CAS;
* stale CAS conflicts before no-op handling and allocates nothing;
* missing and cross-account memories share one unavailable posture;
* Personal Fact species is refused without mutation;
* gapped or divergent revision tails fail closed;
* forced revision and forced receipt failures roll back everything;
* adjacent authority (Project, Persona, review, lifecycle, pin, hold,
  prior provenance) is unchanged.
"""

from __future__ import annotations

import json
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
    ACTION_CONTENT_CORRECTION,
    RECEIPT_SCHEMA,
    MemoryVaultContentCorrectionIntegrityError,
    MemoryVaultContentCorrectionUnsupported,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
)

ACCOUNT_A = "ums05c9w-account-a"
ACCOUNT_B = "ums05c9w-account-b"

ORIGINAL = "The red toolbox is in the garage."
CORRECTED = "  The red toolbox is in the garage, beside the bench.  "
FINAL = "Third revision.\nLine two — “quoted”, 日本語, 🎯"

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
    name = f"ums05c9w_{uuid.uuid4().hex[:10]}"
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


def _seed(session) -> dict:
    session.add(User(id=ACCOUNT_A, username=ACCOUNT_A, password_hash="x", role="guest"))
    session.add(User(id=ACCOUNT_B, username=ACCOUNT_B, password_hash="x", role="guest"))
    session.add(Project(id=8000, user_id=ACCOUNT_A, name="p", identity_depth="light"))
    ordinary_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())
    subject_id = str(uuid.uuid4())
    # Users must be committed before rows that carry their FK.
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
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content=ORIGINAL,
            fact_key=None,
            fact_value=None,
            fact_confidence=None,
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=True,
            held=True,
            review_state="approved",
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
    return {
        "ordinary_id": ordinary_id,
        "fact_id": fact_id,
        "subject_id": subject_id,
    }


@pytest.fixture
def seeded(session_factory):
    with session_factory() as session:
        ids = _seed(session)
    return {"session_factory": session_factory, **ids}


def _row(session_factory, memory_id, account=ACCOUNT_A):
    with session_factory() as session:
        return session.execute(
            sa.select(MemoryRecord).where(
                MemoryRecord.memory_id == memory_id,
                MemoryRecord.user_id == account,
            )
        ).scalar_one_or_none()


def _revisions(session_factory, memory_id):
    with session_factory() as session:
        return (
            session.execute(
                sa.select(MemoryRevision)
                .where(MemoryRevision.memory_id == memory_id)
                .order_by(MemoryRevision.revision_number.asc())
            )
            .scalars()
            .all()
        )


def _receipts(session_factory, memory_id):
    with session_factory() as session:
        return (
            session.execute(
                sa.select(MemoryProvenance)
                .where(MemoryProvenance.memory_id == memory_id)
                .order_by(MemoryProvenance.created_at.asc())
            )
            .scalars()
            .all()
        )


def _token(session_factory, memory_id):
    row = _row(session_factory, memory_id)
    return row.updated_at


# 1-3, 17-18: basic correction, exact text, canonical update.
def test_correction_writes_exact_text_and_revision_one(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)

    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id,
            expected_updated_at=t1,
            content=CORRECTED,
        )

    assert result.changed is True
    assert result.revision_number == 1
    assert isinstance(result.revision_id, str) and len(result.revision_id) == 36
    assert result.previous_updated_at == t1
    assert result.resulting_updated_at != t1

    row = _row(factory, memory_id)
    assert row.text_content == CORRECTED
    assert row.updated_at == result.resulting_updated_at

    revs = _revisions(factory, memory_id)
    assert len(revs) == 1
    assert revs[0].old_text_content == ORIGINAL
    assert revs[0].new_text_content == CORRECTED
    assert revs[0].revision_id == result.revision_id
    assert revs[0].user_id == ACCOUNT_A


# 4-6, 12-13: whitespace, line breaks, Unicode, chain continuity.
def test_second_correction_chains_and_preserves_unicode(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)

    with factory() as session:
        first = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
        )
    assert first.revision_number == 1

    with factory() as session:
        second = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id,
            expected_updated_at=first.resulting_updated_at,
            content=FINAL,
        )
    assert second.revision_number == 2

    revs = _revisions(factory, memory_id)
    assert [r.revision_number for r in revs] == [1, 2]
    assert revs[1].old_text_content == revs[0].new_text_content == CORRECTED
    assert revs[1].new_text_content == FINAL
    # Exact fidelity: no trimming on the leading/trailing whitespace variant.
    assert revs[0].new_text_content.startswith("  ")
    assert revs[0].new_text_content.endswith("  ")
    assert "\n" in revs[1].new_text_content
    assert "日本語" in revs[1].new_text_content
    assert "🎯" in revs[1].new_text_content

    row = _row(factory, memory_id)
    assert row.text_content == FINAL
    assert row.text_content == revs[-1].new_text_content


# 14-16: receipt shape, revision reference, no content duplication.
def test_receipt_references_revision_without_content(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)

    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id,
            expected_updated_at=t1,
            content=CORRECTED,
            reason="clarify location",
            request_ref="req-c9w-1",
        )

    receipts = _receipts(factory, memory_id)
    receipt = next(r for r in receipts if r.provenance_id == result.receipt_id)
    ext = dict(receipt.extensions)
    assert ext["receipt_schema"] == RECEIPT_SCHEMA
    assert ext["mutation_source"] == "vault"
    assert ext["action"] == ACTION_CONTENT_CORRECTION
    assert ext["actor_account_id"] == ACCOUNT_A
    assert ext["reason"] == "clarify location"
    assert ext["request_ref"] == "req-c9w-1"
    assert ext["new_values"]["revision_id"] == result.revision_id
    assert ext["new_values"]["revision_number"] == 1
    assert ext["new_values"]["content_changed"] is True
    # No authored old/new text anywhere in the receipt.
    serialized = json.dumps(ext)
    assert ORIGINAL not in serialized
    assert CORRECTED not in serialized
    assert "text_content" not in serialized


# 21-25, 30-33: no-op creates nothing and never advances CAS.
def test_fresh_exact_noop_creates_nothing(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    revs_before = len(_revisions(factory, memory_id))
    provs_before = len(_receipts(factory, memory_id))

    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(memory_id=memory_id, expected_updated_at=t1, content=ORIGINAL)

    assert result.changed is False
    assert result.receipt_id is None
    assert result.revision_id is None
    assert result.revision_number is None
    assert result.previous_updated_at == result.resulting_updated_at == t1
    assert _token(factory, memory_id) == t1
    assert len(_revisions(factory, memory_id)) == revs_before
    assert len(_receipts(factory, memory_id)) == provs_before
    assert _row(factory, memory_id).text_content == ORIGINAL


# 5, 12, 26-28: stale CAS conflicts before no-op handling.
def test_stale_cas_conflicts_even_for_noop_text(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    stale = t1 - timedelta(days=1)
    revs_before = len(_revisions(factory, memory_id))
    provs_before = len(_receipts(factory, memory_id))

    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=memory_id,
                expected_updated_at=stale,
                content=ORIGINAL,  # same as current: still conflicts
            )

    assert len(_revisions(factory, memory_id)) == revs_before
    assert len(_receipts(factory, memory_id)) == provs_before
    assert _token(factory, memory_id) == t1


def test_stale_cas_after_a_change_creates_nothing(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    with factory() as session:
        first = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
        )
    revs_before = len(_revisions(factory, memory_id))

    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=memory_id, expected_updated_at=t1, content=FINAL
            )

    assert len(_revisions(factory, memory_id)) == revs_before
    assert _row(factory, memory_id).text_content == CORRECTED
    assert _token(factory, memory_id) == first.resulting_updated_at


# 34-35: content validation.
@pytest.mark.parametrize("bad", ["", "   ", "\n\t  "])
def test_blank_content_is_rejected(seeded, bad):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    with factory() as session:
        with pytest.raises(MemoryVaultMutationError):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(memory_id=memory_id, expected_updated_at=t1, content=bad)
    assert _row(factory, memory_id).text_content == ORIGINAL
    assert _revisions(factory, memory_id) == []


def test_non_string_content_is_rejected(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    with factory() as session:
        with pytest.raises(MemoryVaultMutationError):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=memory_id, expected_updated_at=t1, content=12345
            )


# 36: missing and cross-account share one posture.
def test_missing_and_cross_account_share_unavailable_posture(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    missing = "00000000-0000-0000-0000-000000000000"

    for target in (missing, memory_id):
        with factory() as session:
            with pytest.raises(MemoryVaultMutationNotAvailable):
                MemoryVaultMutationService(
                    session, authenticated_account_id=ACCOUNT_B
                ).correct_content(
                    memory_id=target,
                    expected_updated_at=t1,
                    content=CORRECTED,
                )
    assert _revisions(factory, memory_id) == []


# 37-38: Personal Facts are never corrected through the generic writer.
def test_personal_fact_species_is_refused_without_mutation(seeded):
    factory = seeded["session_factory"]
    fact_id = seeded["fact_id"]
    with factory() as session:
        row = session.get(MemoryRecord, fact_id)
        t1 = row.updated_at
        session.commit()
    with factory() as session:
        with pytest.raises(MemoryVaultContentCorrectionUnsupported):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=fact_id,
                expected_updated_at=t1,
                content="should not apply",
            )
    with factory() as session:
        row = session.get(MemoryRecord, fact_id)
        assert row.fact_value == "v"
        assert row.text_content is None
    assert _revisions(factory, fact_id) == []


# 39-40: revision-tail integrity.
def test_divergent_revision_tail_fails_closed(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    with factory() as session:
        # A revision whose new_text does not match canonical content.
        session.add(
            MemoryRevision(
                revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=ACCOUNT_A,
                revision_number=1,
                old_text_content="a",
                new_text_content="b",
            )
        )
        session.commit()
    t1 = _token(factory, memory_id)
    with factory() as session:
        with pytest.raises(MemoryVaultContentCorrectionIntegrityError):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
            )
    assert _row(factory, memory_id).text_content == ORIGINAL


def test_gapped_revision_numbering_fails_closed(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    with factory() as session:
        session.add(
            MemoryRevision(
                revision_id=str(uuid.uuid4()),
                memory_id=memory_id,
                user_id=ACCOUNT_A,
                revision_number=2,
                old_text_content="a",
                new_text_content=ORIGINAL,
            )
        )
        session.commit()
    t1 = _token(factory, memory_id)
    with factory() as session:
        with pytest.raises(MemoryVaultContentCorrectionIntegrityError):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).correct_content(
                memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
            )


# 41-42: transactional atomicity.
def test_forced_revision_failure_rolls_everything_back(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)

    with factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )

        def _fail_on_revision(session_, flush_context, instances):
            if any(isinstance(obj, MemoryRevision) for obj in session_.new):
                raise RuntimeError("forced revision persistence failure")

        event.listen(session, "before_flush", _fail_on_revision)
        try:
            with pytest.raises(MemoryVaultContentCorrectionIntegrityError):
                service.correct_content(
                    memory_id=memory_id,
                    expected_updated_at=t1,
                    content=CORRECTED,
                )
        finally:
            event.remove(session, "before_flush", _fail_on_revision)

    assert _row(factory, memory_id).text_content == ORIGINAL
    assert _token(factory, memory_id) == t1
    assert _revisions(factory, memory_id) == []
    assert all(
        r.source_subject_kind != "vault" or r.source_record_id is None
        for r in _receipts(factory, memory_id)
    )


def test_forced_receipt_failure_rolls_everything_back(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    provs_before = len(_receipts(factory, memory_id))

    with factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )

        def _fail_on_vault_receipt(session_, flush_context, instances):
            for obj in session_.new:
                if (
                    isinstance(obj, MemoryProvenance)
                    and (obj.extensions or {}).get("action")
                    == ACTION_CONTENT_CORRECTION
                ):
                    raise RuntimeError("forced receipt persistence failure")

        event.listen(session, "before_flush", _fail_on_vault_receipt)
        try:
            with pytest.raises(MemoryVaultMutationError):
                service.correct_content(
                    memory_id=memory_id,
                    expected_updated_at=t1,
                    content=CORRECTED,
                )
        finally:
            event.remove(session, "before_flush", _fail_on_vault_receipt)

    assert _row(factory, memory_id).text_content == ORIGINAL
    assert _token(factory, memory_id) == t1
    assert _revisions(factory, memory_id) == []
    assert len(_receipts(factory, memory_id)) == provs_before


# 32-38: adjacent authority preserved.
def test_adjacent_authority_is_unchanged(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    with factory() as session:
        before = session.get(MemoryRecord, memory_id)
        snapshot = {
            "project_id": before.project_id,
            "semantic_species": before.semantic_species,
            "pinned": before.pinned,
            "held": before.held,
            "review_state": before.review_state,
            "lifecycle_state": before.lifecycle_state,
            "reviewed_at": before.reviewed_at,
            "activated_at": before.activated_at,
            "extensions": before.extensions,
        }
        links_before = (
            session.execute(
                sa.select(MemoryPersonaLink).where(
                    MemoryPersonaLink.memory_id == memory_id
                )
            )
            .scalars()
            .all()
        )
        provs_before = len(_receipts(factory, memory_id))
        session.commit()

    t1 = _token(factory, memory_id)
    with factory() as session:
        MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(memory_id=memory_id, expected_updated_at=t1, content=FINAL)

    with factory() as session:
        after = session.get(MemoryRecord, memory_id)
        for key, value in snapshot.items():
            assert getattr(after, key) == value, key
        links_after = (
            session.execute(
                sa.select(MemoryPersonaLink).where(
                    MemoryPersonaLink.memory_id == memory_id
                )
            )
            .scalars()
            .all()
        )
        assert len(links_after) == len(links_before) == 1
        assert links_after[0].link_id == links_before[0].link_id
    # Prior provenance preserved and exactly one new receipt added.
    assert len(_receipts(factory, memory_id)) == provs_before + 1


# 43: readback comes from the existing projection.
def test_readback_returns_corrected_content_via_existing_projection(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
        )
    item = result.item
    assert item.content == CORRECTED
    assert item.identity.canonical_memory_id == memory_id
    assert item.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    assert item.updated_at == result.resulting_updated_at
    assert item.pinned is True
    assert item.held is True
    assert item.review_posture == "approved"
    assert item.lifecycle_posture == "active"


# 7-9: server-generated revision identity.
def test_revision_identity_and_number_are_server_generated(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["ordinary_id"]
    t1 = _token(factory, memory_id)
    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).correct_content(
            memory_id=memory_id, expected_updated_at=t1, content=CORRECTED
        )
    rev = _revisions(factory, memory_id)[0]
    assert rev.revision_id == result.revision_id
    assert rev.revision_number == 1
    # No caller input exists for these fields.
    import inspect

    params = set(
        inspect.signature(MemoryVaultMutationService.correct_content).parameters
    )
    assert "revision_id" not in params
    assert "revision_number" not in params
    assert "account_id" not in params and "user_id" not in params
