"""Actual isolated SQLite custody semantics, not PostgreSQL locking proof."""

from contextlib import contextmanager
from types import SimpleNamespace
import hashlib
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.connections import oauth_store as store
from guardian.db.models import KnowledgeOAuthCredential as Credential
from guardian.db.models import KnowledgeOAuthFlow as Flow
from guardian.db.models import User


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv(
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
        "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
    )
    engine = create_engine("sqlite://")
    for table in (User.__table__, Credential.__table__, Flow.__table__):
        table.create(engine)
    factory = sessionmaker(engine)

    @contextmanager
    def session():
        with factory() as s:
            yield s

    with session() as s:
        s.add_all([User(id=x, username=x, password_hash="unused") for x in ("a", "b")])
        s.commit()
    return SimpleNamespace(get_session=session)


def start(db, user="a", provider="notion"):
    return store.begin_flow(
        db, user, provider, "https://example.test/callback", browser_binding="browser"
    )


def consume(db, flow, provider="notion", binding="browser"):
    return store.consume_flow(db, provider, flow.state, browser_binding=binding)


def connect(db, provider="notion"):
    flow = consume(db, start(db, provider=provider), provider)
    assert store.complete_flow(db, flow, "access-secret", "refresh-secret", 100)
    return flow


def test_state_encrypted_and_one_use(db):
    initial = start(db)
    with db.get_session() as s:
        row = s.query(Flow).one()
        assert row.state_hash == hashlib.sha256(initial.state.encode()).hexdigest()
        assert initial.code_verifier not in row.encrypted_verifier
    flow = consume(db, initial)
    assert flow.user_id == "a"
    with pytest.raises(store.OAuthStateError):
        consume(db, initial)
    assert store.complete_flow(db, flow, "secret")
    assert not store.complete_flow(db, flow, "other")
    assert store.credential(db, "b", "notion") is None
    assert "secret" not in repr(store.credential(db, "a", "notion"))


def test_binding_and_provider_mixup_do_not_consume(db):
    flow = start(db)
    for provider, binding in (("github", "browser"), ("notion", "wrong")):
        with pytest.raises(store.OAuthStateError):
            consume(db, flow, provider, binding)
    assert consume(db, flow).user_id == "a"


def test_expired(db):
    flow = start(db)
    with db.get_session() as s:
        s.query(Flow).update({"expires_at": time.time() - 1})
        s.commit()
    with pytest.raises(store.OAuthStateError):
        consume(db, flow)


@pytest.mark.parametrize("action", ["disconnect", "restart"])
def test_stale_callback_fenced(db, action):
    flow = consume(db, start(db))
    if action == "disconnect":
        store.disconnect(db, "a", "notion")
    else:
        start(db)
    assert not store.complete_flow(db, flow, "stale-secret")
    assert store.credential(db, "a", "notion") is None


def test_unconsumed_old_flow_invalid_after_restart(db):
    first = start(db)
    start(db)
    with pytest.raises(store.OAuthStateError):
        consume(db, first)


def test_refresh_only_one_claim_and_rotation(db):
    connect(db)
    claim = store.claim_refresh(db, "a", "notion")
    assert claim and claim.credential.refresh_token == "refresh-secret"
    assert store.claim_refresh(db, "a", "notion") is None
    assert store.credential(db, "a", "notion") is None
    assert store.complete_refresh(db, claim, "new-access", "new-refresh", 200)
    assert not store.complete_refresh(db, claim, "replayed", "old", 200)
    assert store.credential(db, "a", "notion").refresh_token == "new-refresh"


@pytest.mark.parametrize("action", ["disconnect", "restart"])
def test_refresh_stale_response_cannot_resurrect(db, action):
    connect(db)
    claim = store.claim_refresh(db, "a", "notion")
    if action == "disconnect":
        store.disconnect(db, "a", "notion")
    else:
        start(db)
    assert not store.complete_refresh(db, claim, "stale")
    store.fail_refresh(db, claim)
    assert store.credential(db, "a", "notion") is None


def test_failed_refresh_requires_reconnect(db):
    connect(db)
    claim = store.claim_refresh(db, "a", "notion")
    store.fail_refresh(db, claim)
    assert store.status(db, "a", "notion")["state"] == "reconnect_required"
    with db.get_session() as s:
        row = s.query(Credential).one()
        assert (
            row.encrypted_access_token is None and row.encrypted_refresh_token is None
        )


def test_deleted_account_cannot_complete(db):
    flow = consume(db, start(db))
    with db.get_session() as s:
        s.query(User).filter_by(id="a").delete()
        s.commit()
    assert not store.complete_flow(db, flow, "secret")


def test_repository_generation_scope(db):
    flow = connect(db, "github")
    assert store.status(db, "a", "github")["state"] == "needs_scope"
    assert not store.save_repositories(db, "b", "github", flow.generation, "1", ["o/r"])
    assert store.save_repositories(db, "a", "github", flow.generation, "1", ["o/r"])
    assert store.status(db, "a", "github")["configured"]
    store.disconnect(db, "a", "github")
    assert not store.save_repositories(db, "a", "github", flow.generation, "1", ["o/r"])


def test_absent_vs_tombstone(db):
    assert store.status(db, "a", "notion")["generation"] is None
    connect(db)
    store.disconnect(db, "a", "notion")
    assert store.status(db, "a", "notion")["generation"] is not None


def test_migration_round_trip():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = Path(
        "guardian/db/migrations/versions/d8a90bf32107_knowledge_oauth_custody.py"
    )
    spec = importlib.util.spec_from_file_location("oauth_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert set(inspect(connection).get_table_names()) == {
            "knowledge_oauth_credentials",
            "knowledge_oauth_flows",
        }
        module.downgrade()
        assert inspect(connection).get_table_names() == []


def test_scope_selection_fences_old_refresh_snapshot(db, monkeypatch):
    connect(db, "github")
    old = store.credential(db, "a", "github")
    assert store.save_repositories(db, "a", "github", old.generation, "7", ["o/r"])
    monkeypatch.setattr(store, "credential", lambda *args: old)
    assert store.claim_refresh(db, "a", "github") is None
