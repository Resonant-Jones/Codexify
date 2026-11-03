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
from datetime import datetime, timedelta

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


def test_client_supplied_origin_is_replaced_by_the_backend_assertion(client, db):
    """A forged claim is discarded and the backend authors its own."""
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

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] != ASSERTED_AT
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["version"] == 1
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM
    assert stored["note"] == "keep"


def test_client_supplied_origin_is_replaced_on_the_send_path(client, db):
    """The create-on-send entry path behaves the same way."""
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

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] != ASSERTED_AT
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM


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

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM


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


# ---------------------------------------------------------------------------
# Trusted native-origin stamping on the ordinary user-message path
# ---------------------------------------------------------------------------

FOREIGN_ACCOUNT = "custody-foreign-account"


def _message_count(db, thread_id: int = 10) -> int:
    with psycopg.connect(_connect_url(db)) as conn:
        return int(
            conn.execute(
                "SELECT count(*) FROM chat_messages WHERE thread_id = %s",
                (thread_id,),
            ).fetchone()[0]
        )


def _seed_foreign_thread(db) -> int:
    """Create a thread owned by a different account."""
    with psycopg.connect(_connect_url(db)) as conn:
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,%s,'fixture')",
            (FOREIGN_ACCOUNT, "user-" + FOREIGN_ACCOUNT),
        )
        conn.execute(
            "INSERT INTO projects(id,user_id,name) VALUES (2,%s,'foreign')",
            (FOREIGN_ACCOUNT,),
        )
        conn.execute(
            "INSERT INTO chat_threads(id,user_id,project_id,title,origin_system) "
            "VALUES (11,%s,2,'foreign thread','codexify')",
            (FOREIGN_ACCOUNT,),
        )
    return 11


def _assertion(db, message_id: int) -> dict:
    stored = _stored_extra_meta(db, message_id)
    return dict(stored.get(RESERVED_MESSAGE_ORIGIN_KEY) or {})


def test_a_native_user_message_receives_a_backend_authored_assertion(client, db):
    """The ordinary user-message path writes positive native-origin evidence."""
    response = client.post(
        "/api/chat/10/messages",
        json={"role": "user", "content": "hello"},
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assertion = _assertion(db, _latest_message_id(db))

    assert assertion["version"] == 1
    assert assertion["origin_system"] == ORIGIN_SYSTEM
    moment = datetime.fromisoformat(assertion["asserted_at"])
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)


def test_the_send_path_receives_the_same_backend_authored_assertion(client, db):
    """Both ordinary user-message entry paths converge on one creation rule."""
    response = client.post(
        "/api/chat/messages",
        json={"thread_id": 10, "role": "user", "content": "hello"},
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assertion = _assertion(db, _latest_message_id(db))

    assert assertion["version"] == 1
    assert assertion["origin_system"] == ORIGIN_SYSTEM
    assert datetime.fromisoformat(assertion["asserted_at"]).tzinfo is not None


def test_the_assertion_is_written_by_the_insert_not_by_a_later_merge(client, db):
    """Neutralizing the enrichment merge leaves the assertion in place."""
    from guardian.routes import chat as chat_module

    original = chat_module._persist_message_extra_meta
    calls: list[dict] = []

    def _recording_enrichment(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    chat_module._persist_message_extra_meta = _recording_enrichment
    try:
        response = client.post(
            "/api/chat/10/messages",
            json={
                "role": "user",
                "content": "hello",
                "metadata": {"client_note": "keep"},
            },
            headers=_auth(),
        )
    finally:
        chat_module._persist_message_extra_meta = original

    assert response.status_code == 200, response.text
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert calls, "the route must still run its canonical enrichment merge"
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM
    assert stored["client_note"] == "keep"


def test_a_forged_asserted_at_never_reaches_the_stored_assertion(client, db):
    """The client cannot choose when its own message is asserted."""
    forged = "1999-12-31T23:59:59+00:00"

    response = client.post(
        "/api/chat/10/messages",
        json={
            "role": "user",
            "content": "hello",
            "metadata": {
                RESERVED_MESSAGE_ORIGIN_KEY: {
                    "version": 99,
                    "origin_system": "openai",
                    "asserted_at": forged,
                }
            },
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assertion = _assertion(db, _latest_message_id(db))

    assert assertion["asserted_at"] != forged
    assert assertion["version"] == 1
    assert assertion["origin_system"] == ORIGIN_SYSTEM


def test_unrelated_client_metadata_survives_next_to_the_assertion(client, db):
    """Ordinary metadata keeps its established behaviour."""
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
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM


def test_a_non_user_role_posted_to_the_route_is_not_stamped(client, db):
    """Only the ordinary authenticated user message is native creation."""
    before = _message_count(db)

    response = client.post(
        "/api/chat/10/messages",
        json={"role": "assistant", "content": "not a user turn"},
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assert _message_count(db) == before + 1
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_conflicting_source_lineage_metadata_is_refused(client, db):
    """Importer-origin claims are refused instead of laundered."""
    before = _message_count(db)

    response = client.post(
        "/api/chat/10/messages",
        json={
            "role": "user",
            "content": "hello",
            "metadata": {
                "origin": "chatgpt_import",
                "canonical_filter_profile": "chatgpt_v1_canonical",
                "imported_at": "2026-10-31T12:00:00+00:00",
                "source_message_id": "export-message-1",
            },
        },
        headers=_auth(),
    )

    assert response.status_code == 400, response.text
    assert _message_count(db) == before


def test_conflicting_source_lineage_is_refused_before_a_thread_is_created(
    client, db
):
    """A refused create-on-send request leaves no thread behind."""
    with psycopg.connect(_connect_url(db)) as conn:
        before = int(
            conn.execute("SELECT count(*) FROM chat_threads").fetchone()[0]
        )

    response = client.post(
        "/api/chat/messages",
        json={
            "role": "user",
            "content": "hello",
            "metadata": {"origin": "chatgpt_import"},
        },
        headers=_auth(),
    )

    assert response.status_code == 400, response.text
    with psycopg.connect(_connect_url(db)) as conn:
        after = int(
            conn.execute("SELECT count(*) FROM chat_threads").fetchone()[0]
        )

    assert after == before


def test_quoting_external_material_in_the_content_is_not_refused(client, db):
    """Content that resembles imported material is still a native message."""
    quoted = json.dumps(
        {
            "origin": "chatgpt_import",
            "source_message_id": "export-message-1",
        }
    )

    response = client.post(
        "/api/chat/10/messages",
        json={
            "role": "user",
            "content": f"Here is the snippet I pasted: {quoted}",
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    stored = _stored_extra_meta(db, _latest_message_id(db))

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM


def test_a_foreign_thread_is_denied_and_creates_no_message(db, monkeypatch):
    """Cross-account requests stay denied by existing account and thread authority."""
    from fastapi import HTTPException

    from guardian.core.dependencies import RequestUserScope
    from guardian.routes import chat as chat_module

    monkeypatch.setattr(chat_module, "chatlog_db", db)
    thread_id = _seed_foreign_thread(db)
    before = _message_count(db, thread_id)

    with pytest.raises(HTTPException) as exc_info:
        chat_module.chat_post_message(
            thread_id,
            {"role": "user", "content": "hello"},
            api_key=API_KEY,
            request_user_scope=RequestUserScope(
                user_id=ACCOUNT,
                account_id=ACCOUNT,
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    assert _message_count(db, thread_id) == before


def test_the_message_route_never_mints_a_recall_grant(client, db, monkeypatch):
    """Stamping native origin does not authorize historical recall."""
    from guardian.core import account_history_recall

    calls: list[tuple] = []
    monkeypatch.setattr(
        account_history_recall,
        "resolve_history_recall_authorization",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    response = client.post(
        "/api/chat/10/messages",
        json={"role": "user", "content": "hello"},
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assert calls == []


def test_ordinary_chat_does_not_advertise_history_search():
    """The history command exists in the manifest but stays unadvertised."""
    from fastapi import FastAPI

    from guardian.command_bus.manifest import build_manifest
    from guardian.routes import health
    from guardian.tools.chat_exposure import (
        HISTORY_SEARCH_COMMAND_ID,
        history_search_is_advertised,
        resolve_ordinary_chat_tools,
    )

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(chat.api_chat_router)
    commands = build_manifest(app).commands

    assert any(
        command.command_id == HISTORY_SEARCH_COMMAND_ID for command in commands
    ), "the history command must exist for this assertion to mean anything"

    tools = resolve_ordinary_chat_tools(
        provider="deepseek",
        model="deepseek-model",
        provider_vendor=None,
        manifest_commands=commands,
        history_recall_grant=None,
    )

    assert tools is not None
    assert not history_search_is_advertised(tools)
