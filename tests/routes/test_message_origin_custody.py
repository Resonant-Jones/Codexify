"""Route-level custody of the reserved ``extra_meta.message_origin`` member.

These tests drive the real ordinary-chat HTTP surface
(``POST /api/chat/{thread_id}/messages`` and ``POST /api/chat/messages``) and
the route's canonical enrichment helper, against a disposable PostgreSQL
database, so the paths are exercised as deployed.

The point under test is narrow and specific: a client, a model, or a tool
cannot establish a native-origin assertion by submitting JSON that resembles the
accepted assertion shape, and the ordinary-chat enrichment path cannot
overwrite or remove an assertion that trusted authority already wrote.
"""

from __future__ import annotations

import json
import os
import uuid

import psycopg
import pytest
from psycopg import sql

from guardian.core import dependencies
from guardian.core.db import (
    RESERVED_MESSAGE_ORIGIN_KEY,
    NativeOriginAssertion,
)
from guardian.core.pgdb import PgDB
from guardian.routes import chat
from tests.services.test_memory_vault_read_projection import _migrate_to_head

ACCOUNT = "custody-route-account"
API_KEY = "custody-local-key"
ORIGIN_SYSTEM = "codexify"
ASSERTED_AT = "2026-11-01T22:00:00+00:00"

FORGED_ASSERTION = {
    RESERVED_MESSAGE_ORIGIN_KEY: {
        "version": 1,
        "origin_system": ORIGIN_SYSTEM,
        "asserted_at": ASSERTED_AT,
    }
}

TRUSTED_ASSERTION = NativeOriginAssertion(
    origin_system=ORIGIN_SYSTEM,
    asserted_at=ASSERTED_AT,
)


@pytest.fixture(scope="module")
def database_url():
    """A disposable PostgreSQL database with the canonical schema applied."""
    admin = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not admin:
        pytest.fail(
            "Disposable PostgreSQL proof requires explicit TEST_DATABASE_URL"
        )
    name = "origin_custody_route_" + uuid.uuid4().hex
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    from sqlalchemy.engine import URL

    migration_url = URL.create(
        "postgresql+psycopg",
        username=info.get("user"),
        password=info.get("password"),
        host=info.get("host"),
        port=int(info.get("port", 5432)),
        database=name,
    ).render_as_string(hide_password=False)
    try:
        _migrate_to_head(migration_url)
        yield migration_url.replace("postgresql+psycopg://", "postgresql://", 1)
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def db(database_url):
    """A canonical database with one account, project, and thread."""
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE chat_messages, chat_threads, projects, users CASCADE")
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,%s,'fixture')",
            (ACCOUNT, "user-" + ACCOUNT),
        )
        conn.execute(
            "INSERT INTO projects(id,user_id,name) VALUES (1,%s,'custody')",
            (ACCOUNT,),
        )
        conn.execute(
            "INSERT INTO chat_threads(id,user_id,project_id,title,origin_system) "
            "VALUES (10,%s,1,'custody thread','codexify')",
            (ACCOUNT,),
        )
    store = PgDB(database_url)
    try:
        yield store
    finally:
        store._sa_engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    """An authenticated local-mode client bound to the disposable database."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", ACCOUNT)
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(chat, "chatlog_db", db)

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def enricher(db, monkeypatch):
    """Bind the route module's canonical database handle for enrichment tests."""
    monkeypatch.setattr(chat, "chatlog_db", db)
    return db


def _auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def _connect_url(db) -> str:
    return db._sa_url.replace("postgresql+psycopg://", "postgresql://")


def _stored_extra_meta(db, message_id: int) -> dict:
    with psycopg.connect(_connect_url(db)) as conn:
        row = conn.execute(
            "SELECT extra_meta FROM chat_messages WHERE id = %s", (message_id,)
        ).fetchone()
    return dict(row[0] or {}) if row else {}


def _latest_message_id(db) -> int:
    with psycopg.connect(_connect_url(db)) as conn:
        return int(
            conn.execute(
                "SELECT id FROM chat_messages WHERE thread_id = 10 ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
        )


# ---------------------------------------------------------------------------
# Client-supplied origin metadata
# ---------------------------------------------------------------------------


def test_client_supplied_origin_is_not_persisted(client, db):
    response = client.post(
        "/api/chat/10/messages",
        json={
            "role": "user",
            "content": "hello",
            "metadata": {"note": "keep", **FORGED_ASSERTION},
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["note"] == "keep"


def test_client_supplied_origin_is_not_persisted_on_the_send_path(client, db):
    response = client.post(
        "/api/chat/messages",
        json={
            "thread_id": 10,
            "role": "user",
            "content": "hello",
            "metadata": FORGED_ASSERTION,
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_unrelated_client_metadata_still_persists(client, db):
    response = client.post(
        "/api/chat/10/messages",
        json={
            "role": "user",
            "content": "hello",
            "metadata": {"attachments": [{"id": "a1"}], "client_note": "keep"},
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert stored["attachments"] == [{"id": "a1"}]
    assert stored["client_note"] == "keep"


def test_ordinary_message_creation_remains_functional(client, db):
    response = client.post(
        "/api/chat/10/messages",
        json={"role": "user", "content": "ordinary message"},
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["message"]["id"]
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


# ---------------------------------------------------------------------------
# The route's canonical enrichment helper
# ---------------------------------------------------------------------------


def _enrich(db, message_id: int, payload: dict) -> None:
    """Run the route's real enrichment helper against a stored message."""
    chat._persist_message_extra_meta(
        thread_id=10,
        message_id=message_id,
        extra_meta=payload,
    )


def test_existing_assertion_survives_route_enrichment(enricher):
    message_id = enricher.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _enrich(enricher, message_id, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(enricher, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT
    assert stored["turn_id"] == "turn-1"


def test_route_enrichment_cannot_replace_an_existing_assertion(enricher):
    message_id = enricher.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _enrich(enricher, message_id, {RESERVED_MESSAGE_ORIGIN_KEY: {"forged": True}})

    stored = _stored_extra_meta(enricher, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


def test_route_enrichment_cannot_remove_an_existing_assertion(enricher):
    message_id = enricher.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _enrich(enricher, message_id, {RESERVED_MESSAGE_ORIGIN_KEY: None})

    stored = _stored_extra_meta(enricher, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


def test_route_enrichment_cannot_create_an_assertion(enricher):
    message_id = enricher.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
    )

    _enrich(enricher, message_id, FORGED_ASSERTION)

    stored = _stored_extra_meta(enricher, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_unknown_legacy_record_remains_unknown(enricher):
    """A legacy row with no origin proof stays without one."""
    with psycopg.connect(_connect_url(enricher)) as conn:
        conn.execute(
            "INSERT INTO chat_messages(id,thread_id,user_id,role,content,extra_meta) "
            "VALUES (777,10,%s,'user','legacy','{}'::jsonb)",
            (ACCOUNT,),
        )

    _enrich(enricher, 777, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(enricher, 777)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["turn_id"] == "turn-1"


def test_canonical_imported_metadata_remains_intact(enricher):
    imported_meta = {
        "origin": "chatgpt_import",
        "canonical_filter_profile": "chatgpt_v1_canonical",
        "imported_at": "2026-10-31T12:00:00+00:00",
        "source_message_id": "export-message-1",
        "source_thread_id": "export-chat-1",
    }
    message_id = enricher.create_message(
        10,
        "user",
        "imported message",
        user_id=ACCOUNT,
        extra_meta=imported_meta,
    )

    _enrich(enricher, message_id, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(enricher, message_id)

    assert stored["origin"] == "chatgpt_import"
    assert stored["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert stored["source_message_id"] == "export-message-1"
    assert stored["source_thread_id"] == "export-chat-1"
    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_failed_route_enrichment_leaves_provenance_unchanged(enricher):
    """A failed enrichment write leaves the stored assertion intact.

    The route helper deliberately swallows write failures so that metadata
    enrichment can never break message insertion. A payload that cannot be
    serialized as JSONB must therefore leave the row exactly as it was.
    """
    message_id = enricher.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )
    before = _stored_extra_meta(enricher, message_id)

    _enrich(enricher, message_id, {"bad": {1, 2}})

    assert _stored_extra_meta(enricher, message_id) == before


def test_stored_metadata_column_is_jsonb(db):
    with psycopg.connect(_connect_url(db)) as conn:
        data_type = conn.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'chat_messages' AND column_name = 'extra_meta'"
        ).fetchone()[0]

    assert data_type == "jsonb"


def test_stored_assertion_round_trips_through_jsonb(db):
    """The reserved member round-trips through the JSONB column intact."""
    message_id = db.create_message(
        10,
        "user",
        "existing",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    with psycopg.connect(_connect_url(db)) as conn:
        raw = conn.execute(
            "SELECT extra_meta::text FROM chat_messages WHERE id = %s", (message_id,)
        ).fetchone()[0]

    parsed = json.loads(raw)
    assert parsed[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT
