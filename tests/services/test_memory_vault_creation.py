"""Focused PostgreSQL tests for the Memory Vault direct creation service.

Proves the UMS-05C6 internal user-authored creation service against a
disposable PostgreSQL authority:

- explicit human-authored text is preserved verbatim;
- canonical ``episodic_semantic_memory`` semantic species is fixed;
- account scope is enforced (``project_id`` NULL, no Persona links,
  ``fact_*`` NULL);
- approved + active posture is expressed via ``reviewed_at`` and
  ``activated_at`` (database-authored);
- pinned/held start false; ``extensions`` is NULL;
- exactly one initial ``memory_provenance`` row is created with
  ``source_system = "codexify"`` and ``source_subject_kind = "vault"``;
- receipt carries the canonical ``create_memory`` action and never
  contains the authored text;
- atomic rollback: forced receipt persistence failure leaves zero
  ``memory_records`` and zero ``memory_provenance`` rows;
- Projects, Persona subjects, Persona bindings, and existing
  canonical memories are never mutated by creation;
- canonical readback uses ``MemoryVaultReadService``.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from guardian.db.models import (
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    PersonaSubject,
    Project,
    User,
)
from guardian.protocol_tokens import (
    MemoryPersonaLinkKind,
    MemorySemanticSpecies,
    PersonaSubjectLifecycle,
)
from guardian.services.memory_vault_creation import (
    ACTION_CREATE_MEMORY,
    RECEIPT_SCHEMA,
    SOURCE_SUBJECT_KIND_VAULT,
    SOURCE_SYSTEM_CODEXIFY,
    MemoryVaultCreationAccountNotAvailable,
    MemoryVaultCreationError,
    MemoryVaultCreationIntegrityError,
    MemoryVaultCreationService,
    VaultCreationResult,
)

ACCOUNT_A = "ums05c6-account-a"
ACCOUNT_B = "ums05c6-account-b"


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
    db_part = parts[0].rsplit("/", 1)[1]
    return f"{base}/{name}{suffix}".replace(f"/{db_part}", f"/{name}", 1)


def _drop_database(admin_url: str, name: str) -> None:
    import psycopg

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


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
    name = f"ums05c6_{uuid.uuid4().hex[:10]}"
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
    session.add(
        User(
            id=ACCOUNT_A,
            username=ACCOUNT_A,
            password_hash="test",
            role="guest",
        )
    )
    session.add(
        User(
            id=ACCOUNT_B,
            username=ACCOUNT_B,
            password_hash="test",
            role="guest",
        )
    )
    session.add(
        Project(
            id=7000,
            user_id=ACCOUNT_A,
            name="a-project",
            identity_depth="light",
        )
    )
    session.commit()

    subject_a = str(uuid.uuid4())
    session.add(
        PersonaSubject(
            persona_subject_id=subject_a,
            user_id=ACCOUNT_A,
            display_name_snapshot="Alice",
            lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
        )
    )
    session.commit()
    return {
        "subject_a": subject_a,
        "project_id": 7000,
    }


@pytest.fixture
def seeded(session_factory):
    with session_factory() as session:
        ids = _seed(session)
    return {"session_factory": session_factory, **ids}


def _row(session_factory, memory_id: str) -> MemoryRecord | None:
    with session_factory() as session:
        return session.scalar(
            sa.select(MemoryRecord).where(
                MemoryRecord.memory_id == memory_id,
                MemoryRecord.user_id == ACCOUNT_A,
            )
        )


def _receipts_for(session_factory, memory_id: str) -> list[MemoryProvenance]:
    with session_factory() as session:
        rows = (
            session.query(MemoryProvenance)
            .filter_by(memory_id=memory_id, user_id=ACCOUNT_A)
            .all()
        )
        return rows


def _initial_receipt_for(session_factory, memory_id: str) -> MemoryProvenance:
    rows = _receipts_for(session_factory, memory_id)
    assert len(rows) == 1, f"expected one initial receipt, got {len(rows)}"
    return rows[0]


def _snapshots(session_factory):
    with session_factory() as session:
        project_count = session.scalar(sa.text("SELECT COUNT(*) FROM projects"))
        person_count = session.scalar(sa.text("SELECT COUNT(*) FROM persona_subjects"))
        binding_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM persona_subject_bindings")
        )
        memory_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
        link_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_persona_links WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
        person_facts_count = session.scalar(
            sa.text(
                "SELECT COUNT(*) FROM memory_records WHERE user_id = :u "
                "AND semantic_species IN ("
                "'verified_personal_fact', 'candidate_unreviewed_fact')"
            ),
            {"u": ACCOUNT_A},
        )
    return {
        "projects": int(project_count),
        "persona_subjects": int(person_count),
        "persona_subject_bindings": int(binding_count),
        "memory_records": int(memory_count),
        "memory_persona_links": int(link_count),
        "personal_facts": int(person_facts_count),
    }


def test_create_memory_persists_canonical_episodic_state(seeded):
    factory = seeded["session_factory"]
    content = "The red toolbox is in the garage."
    snap_before = _snapshots(factory)

    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content=content, request_ref="req-create-1")

    assert isinstance(result, VaultCreationResult)
    assert (
        isinstance(result.item.identity.canonical_memory_id, str)
        and len(result.item.identity.canonical_memory_id) == 36
    )
    row = _row(factory, result.item.identity.canonical_memory_id)
    assert row is not None
    assert row.user_id == ACCOUNT_A
    assert row.project_id is None
    assert row.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    assert row.text_content == content
    assert row.fact_key is None
    assert row.fact_value is None
    assert row.fact_confidence is None
    assert row.pinned is False
    assert row.held is False
    assert row.extensions is None
    assert row.reviewed_at is not None
    assert row.activated_at is not None
    assert row.activated_at >= row.reviewed_at
    assert row.created_at is not None
    assert row.updated_at is not None

    item = result.item
    assert item.identity.kind == "canonical"
    assert item.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    assert item.content == content
    assert item.account_owner == ACCOUNT_A
    assert item.project_id is None
    assert item.review_posture == "approved"
    assert item.lifecycle_posture == "active"
    assert item.pinned is False
    assert item.held is False
    assert list(item.persona_links) == []

    snap_after = _snapshots(factory)
    # Creation may increase the memory_records count by exactly one; it
    # must not mutate Projects, Persona subjects/bindings, or
    # memory_persona_links, and must not create Personal Facts.
    assert snap_after["memory_records"] == snap_before["memory_records"] + 1
    for key in (
        "projects",
        "persona_subjects",
        "persona_subject_bindings",
        "memory_persona_links",
        "personal_facts",
    ):
        assert snap_after[key] == snap_before[key], key


def test_create_memory_initial_provenance_is_vault_scoped(seeded):
    factory = seeded["session_factory"]
    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="trusted lineage test")

    memory_id = result.item.identity.canonical_memory_id
    receipt = _initial_receipt_for(factory, memory_id)
    assert receipt.source_system == SOURCE_SYSTEM_CODEXIFY
    assert receipt.source_subject_kind == SOURCE_SUBJECT_KIND_VAULT
    assert receipt.is_imported is False
    assert receipt.source_record_id == memory_id
    ext = receipt.extensions
    assert ext["receipt_schema"] == RECEIPT_SCHEMA
    assert ext["mutation_source"] == "vault"
    assert ext["action"] == ACTION_CREATE_MEMORY
    assert ext["actor_account_id"] == ACCOUNT_A
    assert ext["previous_values"] == {"exists": False}
    assert ext["new_values"] == {
        "exists": True,
        "semantic_species": MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        "project_id": None,
        "review_posture": "approved",
        "lifecycle_posture": "active",
        "pinned": False,
        "held": False,
    }
    assert ext["reason"] is None
    # Receipt extensions must not carry a copy of the authored content.
    serialized = json.dumps(ext)
    assert "trusted lineage test" not in serialized


def test_create_memory_without_request_ref(seeded):
    factory = seeded["session_factory"]
    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="no request ref")

    receipt = _initial_receipt_for(factory, result.item.identity.canonical_memory_id)
    assert receipt.extensions["request_ref"] is None


def test_create_memory_request_ref_is_preserved(seeded):
    factory = seeded["session_factory"]
    ref = "ref-uuid-" + uuid.uuid4().hex[:10]
    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="with ref", request_ref=ref)

    receipt = _initial_receipt_for(factory, result.item.identity.canonical_memory_id)
    assert receipt.extensions["request_ref"] == ref


def test_duplicate_content_creates_distinct_canonical_memories(seeded):
    factory = seeded["session_factory"]
    content = "duplicate content unique to this pair"
    with factory() as session:
        first = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content=content)
    with factory() as session:
        second = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content=content)

    assert (
        first.item.identity.canonical_memory_id
        != second.item.identity.canonical_memory_id
    )


def test_create_memory_preserves_internal_whitespace(seeded):
    factory = seeded["session_factory"]
    content = "  leading + trailing +  internal   spaces  "
    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content=content)

    row = _row(factory, result.item.identity.canonical_memory_id)
    assert row.text_content == content
    assert result.item.content == content


def test_create_memory_whitespace_only_is_rejected(seeded):
    factory = seeded["session_factory"]
    snap_before = _snapshots(factory)
    with factory() as session:
        with pytest.raises(MemoryVaultCreationError):
            MemoryVaultCreationService(
                session, authenticated_account_id=ACCOUNT_A
            ).create_memory(content="   \n\t  ")

    with factory() as session:
        memory_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
        prov_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_provenance WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
    assert int(memory_count) == 0
    assert int(prov_count) == 0
    assert _snapshots(factory) == snap_before


def test_create_memory_invalid_content_type_is_rejected(seeded):
    factory = seeded["session_factory"]
    with factory() as session:
        with pytest.raises(MemoryVaultCreationError):
            MemoryVaultCreationService(
                session, authenticated_account_id=ACCOUNT_A
            ).create_memory(
                content=12345
            )  # type: ignore[arg-type]
    with factory() as session:
        assert (
            int(
                session.scalar(
                    sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :u"),
                    {"u": ACCOUNT_A},
                )
            )
            == 0
        )


def test_create_memory_blank_account_constructor_fails():
    with pytest.raises(MemoryVaultCreationAccountNotAvailable):
        MemoryVaultCreationService(None, authenticated_account_id="")  # type: ignore[arg-type]
    with pytest.raises(MemoryVaultCreationAccountNotAvailable):
        MemoryVaultCreationService(None, authenticated_account_id="   ")  # type: ignore[arg-type]


def test_create_memory_mutation_isolated_to_new_row_and_receipt(seeded):
    factory = seeded["session_factory"]
    snap_before = _snapshots(factory)

    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="isolation check")

    snap_after = _snapshots(factory)
    # One new memory and one new provenance row; everything else unchanged.
    assert snap_after["memory_records"] == snap_before["memory_records"] + 1
    assert snap_after["memory_persona_links"] == snap_before["memory_persona_links"]
    assert snap_after["personal_facts"] == snap_before["personal_facts"]
    assert snap_after["projects"] == snap_before["projects"]
    assert snap_after["persona_subjects"] == snap_before["persona_subjects"]
    assert (
        snap_after["persona_subject_bindings"]
        == snap_before["persona_subject_bindings"]
    )
    with factory() as session:
        prov_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_provenance WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
    assert int(prov_count) == snap_after["memory_records"]


def test_create_memory_atomic_rollback_on_receipt_failure(seeded):
    factory = seeded["session_factory"]
    snap_before = _snapshots(factory)

    with factory() as session:
        service = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        )

        def _fail_on_provenance_add(session_, flush_context, instances):
            if any(isinstance(obj, MemoryProvenance) for obj in session_.new):
                raise RuntimeError("forced provenance persistence failure")

        event.listen(session, "before_flush", _fail_on_provenance_add)
        try:
            with pytest.raises(MemoryVaultCreationIntegrityError):
                service.create_memory(content="rollback test")
        finally:
            event.remove(session, "before_flush", _fail_on_provenance_add)

    # After failure, no orphan row exists.
    snap_after = _snapshots(factory)
    assert snap_after == snap_before
    with factory() as session:
        memory_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
        prov_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_provenance WHERE user_id = :u"),
            {"u": ACCOUNT_A},
        )
    assert int(memory_count) == 0
    assert int(prov_count) == 0


def test_create_memory_canonical_readback_matches_persisted_state(seeded):
    factory = seeded["session_factory"]
    content = "round trip readback proof"
    with factory() as session:
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content=content)

    memory_id = result.item.identity.canonical_memory_id
    row = _row(factory, memory_id)
    item = result.item
    assert item.identity.canonical_memory_id == row.memory_id
    assert item.created_at == row.created_at
    assert item.updated_at == row.updated_at
    assert item.account_owner == row.user_id
    assert item.content == row.text_content
    assert item.semantic_species == row.semantic_species
    assert item.pinned == row.pinned
    assert item.held == row.held
    assert item.project_id == row.project_id
    assert item.review_posture == "approved"
    assert item.lifecycle_posture == "active"
    # Readback must include the initial Vault provenance row.
    assert any(
        prov.source_system == SOURCE_SYSTEM_CODEXIFY
        and prov.source_subject_kind == SOURCE_SUBJECT_KIND_VAULT
        for prov in item.provenance
    )


def test_create_memory_does_not_create_persona_links(seeded):
    factory = seeded["session_factory"]
    subject_id = seeded["subject_a"]
    with factory() as session:
        MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="no persona at creation")

    with factory() as session:
        link_count = session.scalar(
            sa.text(
                "SELECT COUNT(*) FROM memory_persona_links "
                "WHERE user_id = :u AND persona_subject_id = :sid"
            ),
            {"u": ACCOUNT_A, "sid": subject_id},
        )
    assert int(link_count) == 0


def test_create_memory_account_authority_is_constructor_bound(seeded):
    factory = seeded["session_factory"]
    with factory() as session:
        # Attempt to override account via session-level substitution is
        # impossible — the service constructor locked ACCOUNT_A. The only
        # way to get Account B memory would be to re-instantiate the
        # service, which we do not do.
        result = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="constructor bound")

    with factory() as session:
        b_count = session.scalar(
            sa.text("SELECT COUNT(*) FROM memory_records WHERE user_id = :u"),
            {"u": ACCOUNT_B},
        )
    assert int(b_count) == 0


def test_create_memory_two_profiles_in_one_session_independent(seeded):
    """Two services with different constructors in separate sessions produce
    two independent memories owned by their respective accounts."""
    factory = seeded["session_factory"]
    with factory() as session:
        a = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_A
        ).create_memory(content="for A")
    with factory() as session:
        b = MemoryVaultCreationService(
            session, authenticated_account_id=ACCOUNT_B
        ).create_memory(content="for B")
    assert a.item.account_owner == ACCOUNT_A
    assert b.item.account_owner == ACCOUNT_B
    assert a.item.identity.canonical_memory_id != b.item.identity.canonical_memory_id
