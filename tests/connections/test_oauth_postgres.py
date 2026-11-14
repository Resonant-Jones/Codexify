"""Opt-in real PostgreSQL concurrency proof using a disposable Unix-socket cluster.

Set CODEXIFY_OAUTH_TEST_PG_SOCKET to a private /tmp/codexify-oauth-pg.*/socket
and CODEXIFY_OAUTH_TEST_PG_PORT (default 55473). Never points at Preview/Docker.
Each test owns a fresh schema and drops only that schema after completion.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from alembic.migration import MigrationContext
from alembic.operations import Operations

from guardian.connections import oauth_store as store
from guardian.db.models import User, NotionConnectionCredential


@pytest.fixture
def db(monkeypatch):
    socket = os.getenv("CODEXIFY_OAUTH_TEST_PG_SOCKET")
    if not socket:
        pytest.skip("requires explicit disposable PostgreSQL Unix socket")
    path = Path(socket).resolve()
    assert str(path).startswith("/private/tmp/codexify-oauth-pg.") or str(
        path
    ).startswith("/tmp/codexify-oauth-pg.")
    assert path.name == "socket"
    monkeypatch.setenv(
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
        "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
    )
    url = URL.create(
        "postgresql+psycopg",
        database="postgres",
        query={
            "host": str(path),
            "port": os.getenv("CODEXIFY_OAUTH_TEST_PG_PORT", "55473"),
        },
    )
    root = create_engine(url)
    schema = "oauth_test_" + uuid.uuid4().hex
    with root.begin() as connection:
        assert connection.execute(text("SHOW listen_addresses")).scalar() == ""
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        connect_args={"options": f"-csearch_path={schema}"},
        pool_size=8,
        max_overflow=0,
    )
    try:
        with engine.begin() as connection:
            User.__table__.create(connection)
            NotionConnectionCredential.__table__.create(connection)
            for filename in (
                "c13f0713a901_user_scoped_github_knowledge_credentials.py",
                "d8a90bf32107_knowledge_oauth_custody.py",
            ):
                matches = list(
                    Path("guardian/db/migrations/versions").glob(
                        filename.split("_")[0] + "_*.py"
                    )
                )
                assert len(matches) == 1
                spec = importlib.util.spec_from_file_location(
                    "oauth_pg_migration", matches[0]
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.op = Operations(MigrationContext.configure(connection))
                module.upgrade()
            connection.execute(
                User.__table__.insert().values(
                    id="a", username="a", password_hash="unused"
                )
            )
        factory = sessionmaker(engine)

        @contextmanager
        def session():
            with factory() as instance:
                yield instance

        yield SimpleNamespace(get_session=session, engine=engine)
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def start(db, provider="notion"):
    return store.begin_flow(
        db,
        "a",
        provider,
        "https://example.test/callback",
        browser_binding="test-browser",
    )


def consume(db, flow, provider="notion"):
    return store.consume_flow(db, provider, flow.state, browser_binding="test-browser")


def connect(db, provider="notion"):
    flow = consume(db, start(db, provider), provider)
    assert store.complete_flow(db, flow, "test-access", "test-refresh", 100)
    return flow


def race(*actions):
    barrier = Barrier(len(actions))

    def invoke(action):
        barrier.wait(timeout=10)
        return action()

    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        return list(executor.map(invoke, actions))


def test_postgres_migration_shapes(db):
    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    assert {
        "github_knowledge_credentials",
        "knowledge_oauth_credentials",
        "knowledge_oauth_flows",
    } <= set(inspector.get_table_names())
    assert "browser_binding_hash" in {
        column["name"] for column in inspector.get_columns("knowledge_oauth_flows")
    }


def test_postgres_single_state_consumer(db):
    flow = start(db)

    def claim():
        try:
            return consume(db, flow)
        except store.OAuthStateError:
            return None

    results = race(*([claim] * 8))
    assert sum(result is not None for result in results) == 1


def test_postgres_single_refresh_claim(db):
    connect(db)
    results = race(*([lambda: store.claim_refresh(db, "a", "notion")] * 8))
    assert sum(result is not None for result in results) == 1


@pytest.mark.parametrize("iteration", range(5))
def test_postgres_callback_disconnect_fence(db, iteration):
    flow = consume(db, start(db))
    race(
        lambda: store.complete_flow(db, flow, "late-access"),
        lambda: store.disconnect(db, "a", "notion"),
    )
    assert store.status(db, "a", "notion")["state"] == "disconnected"
    assert store.credential(db, "a", "notion") is None
    assert not store.complete_flow(db, flow, "very-late-access")


@pytest.mark.parametrize("iteration", range(5))
def test_postgres_refresh_disconnect_fence(db, iteration):
    connect(db)
    claim = store.claim_refresh(db, "a", "notion")
    race(
        lambda: store.complete_refresh(db, claim, "late-access", "late-refresh", 100),
        lambda: store.disconnect(db, "a", "notion"),
    )
    assert store.status(db, "a", "notion")["state"] == "disconnected"
    assert store.credential(db, "a", "notion") is None
    assert not store.complete_refresh(db, claim, "very-late-access")


def test_postgres_repository_scope_fences_stale_refresh(db, monkeypatch):
    connect(db, "github")
    snapshot = store.credential(db, "a", "github")
    assert store.save_repositories(
        db, "a", "github", snapshot.generation, "1", ["owner/repo"]
    )
    monkeypatch.setattr(store, "credential", lambda *args: snapshot)
    assert store.claim_refresh(db, "a", "github") is None


def test_postgres_new_flow_disconnect_race(db):
    # First-row concurrent creation is serialized by unique key/retry, without
    # accidentally restoring any old usable credential.
    race(lambda: start(db), lambda: store.disconnect(db, "a", "notion"))
    assert store.credential(db, "a", "notion") is None
    assert store.status(db, "a", "notion")["state"] in {"pending", "disconnected"}
