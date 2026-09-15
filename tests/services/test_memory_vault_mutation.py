"""Focused PostgreSQL tests for the Memory Vault governance mutation spine.

Proves the UMS-05C1 internal mutation service against a disposable
PostgreSQL authority:

- CAS-backed pin/unpin with ``memory_records.updated_at``;
- one atomic transaction per changed mutation;
- one append-only ``memory_provenance`` receipt per change;
- stale-write / cross-account / missing fail-closed posture;
- no-op and stale no-op semantics;
- receipt-insertion rollback;
- account-scoped and Project-scoped mutation;
- explicit account-to-Project, Project-to-Project, and Project-to-account scope;
- canonical Project ownership and ADR-081 conflict enforcement;
- shared record CAS across pin, hold, and Project scope;
- preservation of every other authoritative canonical field.
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

from guardian.db.models import MemoryProvenance, MemoryRecord, Project, User
from guardian.protocol_tokens import MemorySemanticSpecies
from guardian.services.memory_vault_mutation import (
    ACTION_CLEAR_PROJECT_SCOPE,
    ACTION_HOLD,
    ACTION_PIN,
    ACTION_RELEASE_HOLD,
    ACTION_SET_PROJECT_SCOPE,
    ACTION_UNPIN,
    RECEIPT_SCHEMA,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
    MemoryVaultProjectAuthorityConflict,
    MemoryVaultProjectNotAvailable,
)

ACCOUNT_A = "ums05c1-account-a"
ACCOUNT_B = "ums05c1-account-b"


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

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
    except Exception:
        pass


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
    name = f"ums05c1_{uuid.uuid4().hex[:10]}"
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture
def session_factory(database_url):
    engine = sa.create_engine(database_url, future=True)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    try:
        yield factory
    finally:
        engine.dispose()


def _seed(session) -> dict:
    session.add(
        User(id=ACCOUNT_A, username=ACCOUNT_A, password_hash="test", role="guest")
    )
    session.add(
        User(id=ACCOUNT_B, username=ACCOUNT_B, password_hash="test", role="guest")
    )
    session.add(
        Project(
            id=9000,
            user_id=ACCOUNT_A,
            name="a-project",
            identity_depth="light",
        )
    )
    session.add(
        Project(
            id=9001,
            user_id=ACCOUNT_A,
            name="a-project-2",
            identity_depth="light",
        )
    )
    session.add(
        Project(
            id=9002,
            user_id=ACCOUNT_A,
            name="a-project-conflicted",
            description=json.dumps(
                {
                    "__codexify_project_owner__": True,
                    "owner_user_id": ACCOUNT_B,
                    "description": "conflicted project",
                }
            ),
            identity_depth="light",
        )
    )
    session.add(
        Project(
            id=9100,
            user_id=ACCOUNT_B,
            name="b-project",
            identity_depth="light",
        )
    )
    session.commit()

    account_scoped_id = str(uuid.uuid4())
    project_scoped_id = str(uuid.uuid4())
    b_id = str(uuid.uuid4())
    conflicted_project_memory_id = str(uuid.uuid4())

    session.add(
        MemoryRecord(
            memory_id=account_scoped_id,
            user_id=ACCOUNT_A,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="account-scoped text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    session.add(
        MemoryRecord(
            memory_id=conflicted_project_memory_id,
            user_id=ACCOUNT_A,
            project_id=9002,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="conflicted-project-scoped text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    session.add(
        MemoryRecord(
            memory_id=project_scoped_id,
            user_id=ACCOUNT_A,
            project_id=9000,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="project-scoped text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    session.add(
        MemoryRecord(
            memory_id=b_id,
            user_id=ACCOUNT_B,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="account-b text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    session.flush()

    # One initial canonical provenance row for the account-scoped memory.
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=account_scoped_id,
            user_id=ACCOUNT_A,
            source_system="codexify",
            source_subject_kind="chat",
            is_imported=False,
        )
    )
    session.commit()

    return {
        "account_scoped_id": account_scoped_id,
        "project_scoped_id": project_scoped_id,
        "b_id": b_id,
        "project_id": 9000,
        "project_b_id": 9001,
        "conflicted_project_id": 9002,
        "foreign_project_id": 9100,
        "conflicted_project_memory_id": conflicted_project_memory_id,
    }


@pytest.fixture
def seeded(session_factory):
    with session_factory() as session:
        ids = _seed(session)
        yield {"session_factory": session_factory, **ids}


def _current(session_factory, memory_id: str) -> MemoryRecord:
    with session_factory() as session:
        row = session.query(MemoryRecord).filter_by(memory_id=memory_id).one()
        session.expunge(row)
        return row


def _receipts(session_factory, memory_id: str) -> list[MemoryProvenance]:
    with session_factory() as session:
        rows = (
            session.query(MemoryProvenance)
            .filter_by(memory_id=memory_id)
            .order_by(
                MemoryProvenance.created_at.asc(), MemoryProvenance.provenance_id.asc()
            )
            .all()
        )
        return [r for r in rows]


def _pin_count(session_factory, memory_id: str) -> int:
    return len(_receipts(session_factory, memory_id))


def _non_pin_fields(session_factory, memory_id: str) -> dict:
    row = _current(session_factory, memory_id)
    return {
        "user_id": row.user_id,
        "project_id": row.project_id,
        "semantic_species": row.semantic_species,
        "text_content": row.text_content,
        "fact_key": row.fact_key,
        "fact_value": row.fact_value,
        "fact_confidence": row.fact_confidence,
        "reviewed_at": row.reviewed_at,
        "activated_at": row.activated_at,
        "held": row.held,
        "extensions": row.extensions,
    }


def _non_project_fields(session_factory, memory_id: str) -> dict:
    row = _current(session_factory, memory_id)
    return {
        "user_id": row.user_id,
        "semantic_species": row.semantic_species,
        "text_content": row.text_content,
        "fact_key": row.fact_key,
        "fact_value": row.fact_value,
        "fact_confidence": row.fact_confidence,
        "reviewed_at": row.reviewed_at,
        "activated_at": row.activated_at,
        "pinned": row.pinned,
        "held": row.held,
        "extensions": row.extensions,
    }


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_successful_pin_then_unpin(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_pinned(
            memory_id=memory_id,
            expected_updated_at=t1,
            pinned=True,
            reason="operator pin",
            request_ref="req-1",
        )

    assert result.changed is True
    assert result.receipt_id is not None
    assert result.resulting_updated_at != t1
    assert result.item.pinned is True
    assert result.item.updated_at == result.resulting_updated_at
    assert _current(factory, memory_id).pinned is True

    t2 = result.resulting_updated_at
    receipts = _receipts(factory, memory_id)
    assert len(receipts) == 2  # one initial + one pin receipt
    assert receipts[-1].extensions["action"] == ACTION_PIN

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        unpin = svc.set_pinned(
            memory_id=memory_id,
            expected_updated_at=t2,
            pinned=False,
            reason="operator unpin",
        )

    assert unpin.changed is True
    assert unpin.resulting_updated_at != t2
    assert unpin.item.pinned is False
    assert _current(factory, memory_id).pinned is False
    receipts = _receipts(factory, memory_id)
    assert len(receipts) == 3
    assert receipts[-1].extensions["action"] == ACTION_UNPIN


def test_stale_token_conflicts(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        svc.set_pinned(memory_id=memory_id, expected_updated_at=t1, pinned=True)

    count_after_pin = _pin_count(factory, memory_id)
    pinned_after_pin = _current(factory, memory_id).pinned
    updated_after_pin = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            svc.set_pinned(
                memory_id=memory_id,
                expected_updated_at=t1,
                pinned=False,
            )

    assert _current(factory, memory_id).pinned is pinned_after_pin
    assert _current(factory, memory_id).updated_at == updated_after_pin
    assert _pin_count(factory, memory_id) == count_after_pin


def test_cross_account_denied(seeded):
    factory = seeded["session_factory"]
    b_id = seeded["b_id"]
    b_t = _current(factory, b_id).updated_at
    before = _pin_count(factory, b_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationNotAvailable):
            svc.set_pinned(
                memory_id=b_id,
                expected_updated_at=b_t,
                pinned=True,
            )

    assert _pin_count(factory, b_id) == before
    assert _current(factory, b_id).pinned is False


def test_missing_record_same_posture(seeded):
    factory = seeded["session_factory"]
    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationNotAvailable) as excinfo:
            svc.set_pinned(
                memory_id=str(uuid.uuid4()),
                expected_updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                pinned=True,
            )
    assert "not available" in str(excinfo.value)


def test_noop_fresh_token(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    count_before = _pin_count(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_pinned(
            memory_id=memory_id,
            expected_updated_at=t1,
            pinned=False,  # already false
        )

    assert result.changed is False
    assert result.receipt_id is None
    assert result.resulting_updated_at == t1
    assert result.item.pinned is False
    assert _current(factory, memory_id).updated_at == t1
    assert _pin_count(factory, memory_id) == count_before


def test_stale_noop_conflicts(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        svc.set_pinned(memory_id=memory_id, expected_updated_at=t1, pinned=True)

    # Now pinned=true. Request pinned=true with the old T1 (stale).
    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            svc.set_pinned(
                memory_id=memory_id,
                expected_updated_at=t1,
                pinned=True,
            )


def test_receipt_shape(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_pinned(
            memory_id=memory_id,
            expected_updated_at=t1,
            pinned=True,
            reason="test reason",
            request_ref="req-xyz",
        )

    receipt = _receipts(factory, memory_id)[-1]
    assert receipt.source_system == "codexify"
    assert receipt.source_subject_kind == "vault"
    assert receipt.is_imported is False
    assert receipt.source_record_id == "req-xyz"
    ext = receipt.extensions
    assert ext["receipt_schema"] == RECEIPT_SCHEMA
    assert ext["mutation_source"] == "vault"
    assert ext["action"] == ACTION_PIN
    assert ext["actor_account_id"] == ACCOUNT_A
    assert ext["previous_values"] == {"pinned": False}
    assert ext["new_values"] == {"pinned": True}
    assert ext["expected_updated_at"] == t1.isoformat()
    assert ext["resulting_updated_at"] == result.resulting_updated_at.isoformat()
    assert ext["reason"] == "test reason"
    assert ext["request_ref"] == "req-xyz"
    # Receipt never stores full memory content.
    serialized = repr(ext)
    assert "account-scoped text" not in serialized
    assert "text_content" not in serialized


def test_atomic_rollback(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    count_before = _pin_count(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)

        def _fail_provenance_flush(session_, flush_context, instances):
            if any(isinstance(obj, MemoryProvenance) for obj in session_.new):
                raise RuntimeError("forced receipt persistence failure")

        event.listen(session, "before_flush", _fail_provenance_flush)
        try:
            with pytest.raises(MemoryVaultMutationError):
                svc.set_pinned(
                    memory_id=memory_id,
                    expected_updated_at=t1,
                    pinned=True,
                )
        finally:
            event.remove(session, "before_flush", _fail_provenance_flush)

    assert _current(factory, memory_id).pinned is False
    assert _current(factory, memory_id).updated_at == t1
    assert _pin_count(factory, memory_id) == count_before


def test_account_scoped_and_project_scoped(seeded):
    factory = seeded["session_factory"]
    for mid in (seeded["account_scoped_id"], seeded["project_scoped_id"]):
        t = _current(factory, mid).updated_at
        project_id_before = _current(factory, mid).project_id
        with factory() as session:
            svc = MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            )
            result = svc.set_pinned(
                memory_id=mid,
                expected_updated_at=t,
                pinned=True,
            )
        assert result.changed is True
        assert _current(factory, mid).pinned is True
        assert _current(factory, mid).project_id == project_id_before


def test_mutation_preserves_other_authority(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    before = _non_pin_fields(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        svc.set_pinned(memory_id=memory_id, expected_updated_at=t1, pinned=True)

    after = _non_pin_fields(factory, memory_id)
    assert after == before


def test_naive_or_missing_token_rejected(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationError):
            svc.set_pinned(
                memory_id=memory_id,
                expected_updated_at=datetime(2026, 1, 1),  # naive
                pinned=True,
            )
        with pytest.raises(MemoryVaultMutationError):
            svc.set_pinned(
                memory_id=memory_id,
                expected_updated_at=None,
                pinned=True,
            )


# ---------------------------------------------------------------------------
# Hold / release-hold.
# ---------------------------------------------------------------------------


def test_successful_hold_then_release(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_held(
            memory_id=memory_id,
            expected_updated_at=t1,
            held=True,
            reason="operator hold",
            request_ref="req-hold",
        )

    assert result.changed is True
    assert result.receipt_id is not None
    assert result.resulting_updated_at != t1
    assert result.item.held is True
    assert result.item.pinned is False
    assert _current(factory, memory_id).held is True

    t2 = result.resulting_updated_at
    receipts = _receipts(factory, memory_id)
    assert len(receipts) == 2
    assert receipts[-1].extensions["action"] == ACTION_HOLD
    assert receipts[-1].extensions["previous_values"] == {"held": False}
    assert receipts[-1].extensions["new_values"] == {"held": True}

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        release = svc.set_held(
            memory_id=memory_id,
            expected_updated_at=t2,
            held=False,
        )

    assert release.changed is True
    assert release.resulting_updated_at != t2
    assert release.item.held is False
    assert _current(factory, memory_id).held is False
    receipts = _receipts(factory, memory_id)
    assert len(receipts) == 3
    assert receipts[-1].extensions["action"] == ACTION_RELEASE_HOLD
    assert receipts[-1].extensions["previous_values"] == {"held": True}
    assert receipts[-1].extensions["new_values"] == {"held": False}


def test_hold_fresh_noop(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    count_before = _pin_count(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_held(
            memory_id=memory_id,
            expected_updated_at=t1,
            held=False,  # already false
        )

    assert result.changed is False
    assert result.receipt_id is None
    assert result.resulting_updated_at == t1
    assert _current(factory, memory_id).updated_at == t1
    assert _pin_count(factory, memory_id) == count_before


def test_hold_stale_noop_conflicts(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        svc.set_held(memory_id=memory_id, expected_updated_at=t1, held=True)

    # held=true now; request held=true with stale T1.
    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            svc.set_held(memory_id=memory_id, expected_updated_at=t1, held=True)


def test_hold_project_scoped(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["project_scoped_id"]
    project_id_before = _current(factory, memory_id).project_id
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_held(memory_id=memory_id, expected_updated_at=t1, held=True)

    assert result.changed is True
    assert _current(factory, memory_id).held is True
    assert _current(factory, memory_id).project_id == project_id_before


def test_hold_receipt_shape(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        result = svc.set_held(
            memory_id=memory_id,
            expected_updated_at=t1,
            held=True,
            reason="reason-hold",
            request_ref="req-hold",
        )

    receipt = _receipts(factory, memory_id)[-1]
    assert receipt.source_system == "codexify"
    assert receipt.source_subject_kind == "vault"
    ext = receipt.extensions
    assert ext["receipt_schema"] == RECEIPT_SCHEMA
    assert ext["mutation_source"] == "vault"
    assert ext["action"] == ACTION_HOLD
    assert ext["actor_account_id"] == ACCOUNT_A
    assert ext["previous_values"] == {"held": False}
    assert ext["new_values"] == {"held": True}
    assert ext["expected_updated_at"] == t1.isoformat()
    assert ext["resulting_updated_at"] == result.resulting_updated_at.isoformat()
    assert ext["reason"] == "reason-hold"
    assert ext["request_ref"] == "req-hold"
    serialized = repr(ext)
    assert "account-scoped text" not in serialized
    assert "heat" not in serialized
    assert "decay" not in serialized


def test_hold_atomic_rollback(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    count_before = _pin_count(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)

        def _fail_provenance_flush(session_, flush_context, instances):
            if any(isinstance(obj, MemoryProvenance) for obj in session_.new):
                raise RuntimeError("forced receipt persistence failure")

        event.listen(session, "before_flush", _fail_provenance_flush)
        try:
            with pytest.raises(MemoryVaultMutationError):
                svc.set_held(
                    memory_id=memory_id,
                    expected_updated_at=t1,
                    held=True,
                )
        finally:
            event.remove(session, "before_flush", _fail_provenance_flush)

    assert _current(factory, memory_id).held is False
    assert _current(factory, memory_id).updated_at == t1
    assert _pin_count(factory, memory_id) == count_before


def test_hold_preserves_pin_state(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    # Pin the record first.
    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        pin_result = svc.set_pinned(
            memory_id=memory_id, expected_updated_at=t1, pinned=True
        )
    assert _current(factory, memory_id).pinned is True

    # Hold it; pin must remain true.
    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        hold_result = svc.set_held(
            memory_id=memory_id,
            expected_updated_at=pin_result.resulting_updated_at,
            held=True,
        )
    assert hold_result.changed is True
    assert _current(factory, memory_id).pinned is True
    assert _current(factory, memory_id).held is True


def test_hold_invalidates_stale_pin_intent(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        hold_result = svc.set_held(
            memory_id=memory_id, expected_updated_at=t1, held=True
        )
    assert hold_result.resulting_updated_at != t1

    receipts_after_hold = _pin_count(factory, memory_id)
    pinned_before = _current(factory, memory_id).pinned

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            svc.set_pinned(memory_id=memory_id, expected_updated_at=t1, pinned=True)

    assert _current(factory, memory_id).pinned is pinned_before
    assert _pin_count(factory, memory_id) == receipts_after_hold


def test_pin_invalidates_stale_hold_intent(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        hold_result = svc.set_held(
            memory_id=memory_id, expected_updated_at=t1, held=True
        )
    t2 = hold_result.resulting_updated_at

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        pin_result = svc.set_pinned(
            memory_id=memory_id, expected_updated_at=t2, pinned=True
        )
    assert pin_result.resulting_updated_at != t2

    held_before = _current(factory, memory_id).held
    receipts_after_pin = _pin_count(factory, memory_id)

    with factory() as session:
        svc = MemoryVaultMutationService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultMutationConflict):
            svc.set_held(memory_id=memory_id, expected_updated_at=t2, held=False)

    assert _current(factory, memory_id).held is held_before
    assert _pin_count(factory, memory_id) == receipts_after_pin


# ---------------------------------------------------------------------------
# Project-scope mutation.
# ---------------------------------------------------------------------------


def test_project_scope_account_to_project_to_project_to_account(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    project_a = seeded["project_id"]
    project_b = seeded["project_b_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        result_a = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=t1,
            project_id=project_a,
            reason="scope to A",
            request_ref="scope-a",
        )

    assert result_a.changed is True
    assert result_a.item.project_id == project_a
    assert result_a.resulting_updated_at != t1
    first_receipt = _receipts(factory, memory_id)[-1]
    assert first_receipt.extensions["action"] == ACTION_SET_PROJECT_SCOPE
    assert first_receipt.extensions["previous_values"] == {"project_id": None}
    assert first_receipt.extensions["new_values"] == {"project_id": project_a}
    assert first_receipt.extensions["reason"] == "scope to A"
    assert first_receipt.extensions["request_ref"] == "scope-a"

    with factory() as session:
        result_b = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=result_a.resulting_updated_at,
            project_id=project_b,
        )

    assert result_b.item.project_id == project_b
    assert result_b.resulting_updated_at != result_a.resulting_updated_at
    move_receipt = _receipts(factory, memory_id)[-1]
    assert move_receipt.extensions["action"] == ACTION_SET_PROJECT_SCOPE
    assert move_receipt.extensions["previous_values"] == {"project_id": project_a}
    assert move_receipt.extensions["new_values"] == {"project_id": project_b}

    with factory() as session:
        memory_owner, project_owner = session.execute(
            sa.select(MemoryRecord.user_id, Project.user_id)
            .join(Project, MemoryRecord.project_id == Project.id)
            .where(MemoryRecord.memory_id == memory_id)
        ).one()
    assert memory_owner == project_owner == ACCOUNT_A

    with factory() as session:
        cleared = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=result_b.resulting_updated_at,
            project_id=None,
        )

    assert cleared.item.project_id is None
    assert cleared.resulting_updated_at != result_b.resulting_updated_at
    clear_receipt = _receipts(factory, memory_id)[-1]
    assert clear_receipt.extensions["action"] == ACTION_CLEAR_PROJECT_SCOPE
    assert clear_receipt.extensions["previous_values"] == {"project_id": project_b}
    assert clear_receipt.extensions["new_values"] == {"project_id": None}


def test_project_scope_fresh_noop_and_stale_noop(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["project_scoped_id"]
    project_id = seeded["project_id"]
    t1 = _current(factory, memory_id).updated_at
    count_before = _pin_count(factory, memory_id)

    with factory() as session:
        noop = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=t1,
            project_id=project_id,
        )
    assert noop.changed is False
    assert noop.receipt_id is None
    assert noop.previous_updated_at == noop.resulting_updated_at == t1
    assert _pin_count(factory, memory_id) == count_before

    with factory() as session:
        changed = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=t1,
            project_id=seeded["project_b_id"],
        )
    count_after = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=t1,
                project_id=seeded["project_b_id"],
            )
    assert _current(factory, memory_id).project_id == seeded["project_b_id"]
    assert _current(factory, memory_id).updated_at == changed.resulting_updated_at
    assert _pin_count(factory, memory_id) == count_after


@pytest.mark.parametrize("project_key", ["foreign_project_id"])
def test_project_scope_foreign_target_is_unavailable(seeded, project_key):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    before = _current(factory, memory_id)
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultProjectNotAvailable) as excinfo:
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=before.updated_at,
                project_id=seeded[project_key],
            )
    assert "not available" in str(excinfo.value)
    assert _current(factory, memory_id).project_id == before.project_id
    assert _current(factory, memory_id).updated_at == before.updated_at
    assert _pin_count(factory, memory_id) == receipt_count


def test_project_scope_missing_target_shares_unavailable_posture(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    before = _current(factory, memory_id)
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultProjectNotAvailable) as excinfo:
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=before.updated_at,
                project_id=999_999,
            )
    assert "not available" in str(excinfo.value)
    assert _current(factory, memory_id).project_id is None
    assert _current(factory, memory_id).updated_at == before.updated_at
    assert _pin_count(factory, memory_id) == receipt_count


def test_project_scope_conflicted_target_fails_closed(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    before = _current(factory, memory_id)
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultProjectAuthorityConflict) as excinfo:
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=before.updated_at,
                project_id=seeded["conflicted_project_id"],
            )
    assert excinfo.value.code == "project_ownership_authority_conflict"
    assert _current(factory, memory_id).project_id is None
    assert _current(factory, memory_id).updated_at == before.updated_at
    assert _pin_count(factory, memory_id) == receipt_count


def test_project_scope_conflicted_current_project_fails_closed(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["conflicted_project_memory_id"]
    before = _current(factory, memory_id)
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultProjectAuthorityConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=before.updated_at,
                project_id=None,
            )
    assert _current(factory, memory_id).project_id == before.project_id
    assert _current(factory, memory_id).updated_at == before.updated_at
    assert _pin_count(factory, memory_id) == receipt_count


def test_project_scope_atomic_rollback_and_independence(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    receipt_count = _pin_count(factory, memory_id)
    independent_before = _non_project_fields(factory, memory_id)

    with factory() as session:
        service = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        )

        def _fail_provenance_flush(session_, flush_context, instances):
            if any(isinstance(obj, MemoryProvenance) for obj in session_.new):
                raise RuntimeError("forced receipt persistence failure")

        event.listen(session, "before_flush", _fail_provenance_flush)
        try:
            with pytest.raises(MemoryVaultMutationError):
                service.set_project_scope(
                    memory_id=memory_id,
                    expected_updated_at=t1,
                    project_id=seeded["project_id"],
                )
        finally:
            event.remove(session, "before_flush", _fail_provenance_flush)

    assert _current(factory, memory_id).project_id is None
    assert _current(factory, memory_id).updated_at == t1
    assert _pin_count(factory, memory_id) == receipt_count
    assert _non_project_fields(factory, memory_id) == independent_before


def test_project_scope_preserves_other_authority_and_receipt_privacy(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    before = _non_project_fields(factory, memory_id)
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=t1,
            project_id=seeded["project_id"],
        )

    assert result.item.project_id == seeded["project_id"]
    assert _non_project_fields(factory, memory_id) == before
    receipt_payload = repr(_receipts(factory, memory_id)[-1].extensions)
    assert "account-scoped text" not in receipt_payload
    assert "a-project" not in receipt_payload
    assert "owner_user_id" not in receipt_payload
    assert "description" not in receipt_payload


def test_project_scope_and_pin_share_record_cas(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        scope_result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_project_scope(
            memory_id=memory_id,
            expected_updated_at=t1,
            project_id=seeded["project_id"],
        )
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_pinned(
                memory_id=memory_id,
                expected_updated_at=t1,
                pinned=True,
            )
    assert _current(factory, memory_id).project_id == seeded["project_id"]
    assert _current(factory, memory_id).pinned is False
    assert _current(factory, memory_id).updated_at == scope_result.resulting_updated_at
    assert _pin_count(factory, memory_id) == receipt_count


def test_pin_and_hold_invalidate_stale_project_scope_intent(seeded):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at

    with factory() as session:
        pin_result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_pinned(
            memory_id=memory_id,
            expected_updated_at=t1,
            pinned=True,
        )
    receipt_count = _pin_count(factory, memory_id)

    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=t1,
                project_id=seeded["project_id"],
            )
    assert _current(factory, memory_id).project_id is None
    assert _current(factory, memory_id).updated_at == pin_result.resulting_updated_at
    assert _pin_count(factory, memory_id) == receipt_count

    with factory() as session:
        hold_result = MemoryVaultMutationService(
            session, authenticated_account_id=ACCOUNT_A
        ).set_held(
            memory_id=memory_id,
            expected_updated_at=pin_result.resulting_updated_at,
            held=True,
        )
    with factory() as session:
        with pytest.raises(MemoryVaultMutationConflict):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=pin_result.resulting_updated_at,
                project_id=seeded["project_id"],
            )
    assert _current(factory, memory_id).updated_at == hold_result.resulting_updated_at


@pytest.mark.parametrize("invalid_project_id", [0, -1, True, "9000"])
def test_project_scope_rejects_invalid_project_id(seeded, invalid_project_id):
    factory = seeded["session_factory"]
    memory_id = seeded["account_scoped_id"]
    t1 = _current(factory, memory_id).updated_at
    with factory() as session:
        with pytest.raises(MemoryVaultMutationError):
            MemoryVaultMutationService(
                session, authenticated_account_id=ACCOUNT_A
            ).set_project_scope(
                memory_id=memory_id,
                expected_updated_at=t1,
                project_id=invalid_project_id,
            )
