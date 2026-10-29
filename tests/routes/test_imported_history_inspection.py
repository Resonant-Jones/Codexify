"""Real HTTP/account authentication and disposable canonical PostgreSQL proof."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import threading

import psycopg
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.core import dependencies, session_store
from guardian.core.auth import issue_session_token
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.core.session_store import SessionStore
from guardian.routes import migration
from guardian.services import imported_history_inspection_access as access
from guardian.services.imported_history_evidence import (
    EvidenceAccessError,
    EvidenceMetadataError,
    EvidenceReadError,
    EvidenceRequestError,
)
from tests.services.test_imported_history_evidence import (
    A,
    B,
    snapshot,
)

pytest_plugins = ["tests.services.test_imported_history_evidence"]

PATH = "/api/imports/history/inspect"
BODY = dict(
    project_id=1,
    thread_ids=[10, 11],
    origins=["openai", "anthropic"],
    max_messages=100,
    max_inspected_messages=1000,
    max_excerpt_bytes=8192,
    max_response_bytes=262144,
    offset=0,
)


class SessionReadStore:
    """SessionStore's ordinary Redis interface, isolated from any live Redis."""

    def __init__(self):
        self.values = {}
        self.writes = 0

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, **kwargs):
        self.writes += 1
        self.values[key] = value


@pytest.fixture
def http(corpus, database_url, monkeypatch):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "history-http-fixture-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "history-local-key")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", A)
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOCAL_DEV", "true")
    settings = SimpleNamespace(
        GUARDIAN_API_KEY="history-local-key",
        GUARDIAN_API_KEYS="",
        CODEXIFY_MULTI_USER_ENABLED=True,
        GUARDIAN_DATABASE_URL=database_url,
    )
    # Deployment settings and backing stores are isolated. No authentication,
    # principal, Project, thread or reader dependency is overridden.
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
    monkeypatch.setattr(dependencies, "get_core_settings", lambda: settings)
    engine = create_engine(
        database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    monkeypatch.setattr(dependencies, "_PRINCIPAL_SESSION_DSN", database_url)
    monkeypatch.setattr(
        dependencies, "_PRINCIPAL_SESSION_FACTORY", sessionmaker(bind=engine)
    )
    redis = SessionReadStore()
    store = SessionStore(redis_client=redis)
    monkeypatch.setattr(session_store, "_SESSION_STORE", store)
    with psycopg.connect(database_url) as conn:
        conn.execute("DELETE FROM authenticated_principals")
        for account, subject in [(A, "subject-a"), (B, "subject-b")]:
            conn.execute(
                "INSERT INTO authenticated_principals(account_id,subject_id) VALUES (%s,%s)",
                (account, subject),
            )
    # An account credential is only accepted while its approved session is
    # stored, and the session user id is the account identity the routes
    # compare against the project and thread owners.
    token_a = issue_session_token(A, purpose="account_session")[0]
    token_b = issue_session_token(B, purpose="account_session")[0]
    store.store(token_a, A, 3600)
    store.store(token_b, B, 3600)
    operator = issue_session_token("subject-a", purpose="operator_session")[0]
    guest = issue_guest_session_token(
        room_id="fixture-room",
        room_slug="fixture-room",
        participant_id="fixture-person",
        invitation_id="fixture-invitation",
    )[0]
    monkeypatch.setattr(
        migration, "chatlog_db", SimpleNamespace(_connect=corpus._connect)
    )
    app = FastAPI()
    app.include_router(migration.router)
    with TestClient(app) as client:
        # Root conftest injects an API key by default. Real authentication proof
        # must start with no implicit credential; each test selects its headers.
        client.headers.clear()
        yield SimpleNamespace(
            client=client,
            token_a=token_a,
            token_b=token_b,
            operator=operator,
            guest=guest,
            settings=settings,
            redis=redis,
            store=store,
            url=database_url,
        )
    engine.dispose()


def post(http, body=None, headers=None):
    return http.client.post(
        PATH,
        json=BODY if body is None else body,
        headers=(
            {"Authorization": "Bearer " + http.token_a} if headers is None else headers
        ),
    )


def safe(response, status):
    assert response.status_code == status, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert not any(
        s in response.text
        for s in [
            "secret",
            "other account",
            "psycopg",
            "SELECT",
            "postgresql",
            "enqueue a task",
        ]
    )
    assert "excerpts" not in response.json()


def test_http_authenticated_evidence_and_no_store(http):
    response = post(http)
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    data = response.json()
    assert [e["message_id"] for e in data["excerpts"]] == [101, 103, 104, 105, 110]
    assert {e["origin_system"] for e in data["excerpts"]} == {"openai", "anthropic"}
    assert data["excerpts"][0]["original_role"] == "user"
    assert data["excerpts"][-1]["original_role"] == "human"
    assert data["excerpts"][2]["fallback_or_uncertain_time"]
    assert data["coverage"]["unproven_import_records"] == 2
    assert not data["coverage"]["source_archive_completeness_verified"]
    assert len(response.content) <= BODY["max_response_bytes"]
    assert http.redis.writes == 0
    assert not http.client.app.dependency_overrides


@pytest.mark.parametrize(
    "credential",
    [
        "missing",
        "raw-key",
        "bearer-key",
        "operator",
        "guest",
        "expired",
        "tampered",
        "unmapped",
    ],
)
def test_http_account_authentication_cannot_be_bypassed(http, monkeypatch, credential):
    reader = Mock(side_effect=AssertionError("Unauthenticated reader call"))
    monkeypatch.setattr(migration, "ImportedHistoryEvidenceReader", reader)
    headers = {}
    if credential == "raw-key":
        headers["X-API-Key"] = "history-local-key"
    elif credential == "bearer-key":
        headers["Authorization"] = "Bearer history-local-key"
    elif credential in ("operator", "guest"):
        headers["Authorization"] = "Bearer " + getattr(http, credential)
    elif credential == "expired":
        headers["Authorization"] = (
            "Bearer "
            + issue_session_token(
                "subject-a", ttl_seconds=-1, purpose="account_session"
            )[0]
        )
    elif credential == "tampered":
        headers["Authorization"] = "Bearer " + http.token_a + "tampered"
    elif credential == "unmapped":
        headers["Authorization"] = (
            "Bearer "
            + issue_session_token("unknown-subject", purpose="account_session")[0]
        )
    safe(post(http, headers=headers), 401)
    reader.assert_not_called()


@pytest.mark.parametrize(
    "kind",
    [
        "operator-cookie",
        "guest-cookie",
        "key-and-account",
        "different-accounts",
        "stored-subject-conflict",
    ],
)
def test_mixed_and_conflicting_principals(http, kind):
    headers = {"Authorization": "Bearer " + http.token_a}
    if kind == "operator-cookie":
        http.client.cookies.set("gc_session", http.operator)
    elif kind == "guest-cookie":
        http.client.cookies.set("codexify_hosted_room_session", http.guest)
    elif kind == "key-and-account":
        headers["X-API-Key"] = "history-local-key"
    elif kind == "different-accounts":
        http.client.cookies.set("gc_session", http.token_b)
    else:
        http.store.store(http.token_a, "different-subject", 3600)
    safe(
        post(http, headers=headers),
        401 if kind in ("different-accounts", "stored-subject-conflict") else 400,
    )


@pytest.mark.parametrize("mode", ["local", "remote"])
def test_local_spoofing_and_both_mode_owner_isolation(http, monkeypatch, mode):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", mode)
    http.settings.CODEXIFY_MULTI_USER_ENABLED = mode == "remote"
    headers = (
        {"X-API-Key": "history-local-key"}
        if mode == "local"
        else {"Authorization": "Bearer " + http.token_a}
    )
    headers["X-User-Id"] = B
    assert post(http, headers=headers).status_code == 200
    safe(post(http, dict(BODY, project_id=3, thread_ids=[14]), headers), 404)


@pytest.mark.parametrize("kind", ["operator", "guest", "guest-cookie"])
def test_local_wrong_purpose_rejected_even_with_valid_key(http, monkeypatch, kind):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    http.settings.CODEXIFY_MULTI_USER_ENABLED = False
    headers = {"X-API-Key": "history-local-key"}
    if kind == "guest-cookie":
        http.client.cookies.set("codexify_hosted_room_session", http.guest)
    else:
        headers["Authorization"] = "Bearer " + getattr(http, kind)
    safe(post(http, headers=headers), 401)


@pytest.mark.parametrize(
    "changes",
    [
        dict(project_id=3, thread_ids=[14]),
        dict(thread_ids=[13]),
        dict(thread_ids=[10, 14]),
        dict(thread_ids=[999]),
        dict(project_id=999),
        dict(thread_ids=[18]),
        dict(project_id=4, thread_ids=[23]),
        dict(project_id=5, thread_ids=[21]),
        dict(thread_ids=[19]),
        dict(thread_ids=[12]),
        dict(origins=["anthropic"], thread_ids=[10]),
    ],
)
def test_real_project_thread_message_owner_and_source_denials(http, changes):
    safe(post(http, dict(BODY, **changes)), 404)


def test_positive_second_account(http):
    response = post(
        http,
        dict(BODY, project_id=3, thread_ids=[14]),
        {"Authorization": "Bearer " + http.token_b},
    )
    assert response.status_code == 200
    assert [e["message_id"] for e in response.json()["excerpts"]] == [140]


@pytest.mark.parametrize(
    "changes",
    [
        dict(thread_ids=[]),
        dict(thread_ids=[10, 10]),
        dict(thread_ids=[True]),
        dict(thread_ids=["10"]),
        dict(thread_ids=list(range(21))),
        dict(project_id=0),
        dict(origins=["codexify"]),
        dict(origins=["chatgpt"]),
        dict(origins=["openai", "openai"]),
        dict(max_messages=101),
        dict(max_inspected_messages=1001),
        dict(max_excerpt_bytes=8193),
        dict(max_response_bytes=262145),
        dict(offset=100001),
        dict(max_messages=True),
        dict(account_id=B),
        dict(user_id=B),
        dict(authority={"allowed": True}),
    ],
)
def test_strict_request_selection_no_authority_fields_or_input_echo(http, changes):
    safe(post(http, dict(BODY, **changes)), 422)


@pytest.mark.parametrize("depth", ["light", "deep"])
def test_modeling_flags_and_diary_identity_write_lock_do_not_revoke_reads(http, depth):
    with psycopg.connect(http.url) as conn:
        conn.execute(
            "INSERT INTO user_settings(user_id,memory_mode,diary_requires_unlock,allow_sensitive_modeling) VALUES (%s,'none',true,false) ON CONFLICT (user_id) DO UPDATE SET memory_mode='none',diary_requires_unlock=true",
            (A,),
        )
        conn.execute("UPDATE projects SET identity_depth=%s WHERE id=1", (depth,))
    response = post(http, dict(BODY, thread_ids=[15, 16]))
    assert response.status_code == 200, response.text
    assert [e["message_id"] for e in response.json()["excerpts"]] == [150, 160]


@pytest.mark.parametrize("restriction", ["denied", "unresolved"])
def test_current_read_authority_denial_and_missing_decision_fail_closed(
    http, monkeypatch, restriction
):
    def unresolved(*args, **kwargs):
        if restriction == "denied":
            raise HTTPException(
                status_code=403, detail="private metadata must not escape"
            )
        return None

    monkeypatch.setattr(access, "require_thread_read_access", unresolved)
    safe(post(http, dict(BODY, thread_ids=[15])), 404)


@pytest.mark.parametrize(
    "field", ["record_read_allowed", "source_read_allowed", "diary_read_allowed"]
)
def test_reader_honors_denied_or_missing_receipt_decisions(http, monkeypatch, field):
    original = migration.resolve_inspection_access

    def narrow(*args, **kwargs):
        receipt = original(*args, **kwargs)
        return replace(
            receipt, decisions=(replace(receipt.decisions[0], **{field: None}),)
        )

    monkeypatch.setattr(migration, "resolve_inspection_access", narrow)
    safe(post(http, dict(BODY, thread_ids=[15])), 404)


def test_exact_principal_identity_and_owner_change_between_reads(http, monkeypatch):
    original = migration.resolve_inspection_access
    captured = {}

    def resolve(*args, **kwargs):
        receipt = original(*args, **kwargs)
        assert receipt.principal is kwargs["principal"]
        captured["principal"] = receipt.principal
        with psycopg.connect(http.url) as conn:
            conn.execute("UPDATE chat_threads SET user_id=%s WHERE id=10", (B,))
        return receipt

    reader_type = migration.ImportedHistoryEvidenceReader

    class VerifyingReader(reader_type):
        def read(self, **kwargs):
            assert (
                kwargs["principal"]
                is captured["principal"]
                is kwargs["authority"].principal
            )
            return super().read(**kwargs)

    monkeypatch.setattr(migration, "resolve_inspection_access", resolve)
    monkeypatch.setattr(migration, "ImportedHistoryEvidenceReader", VerifyingReader)
    safe(post(http), 404)


@pytest.mark.parametrize(
    "error,status",
    [
        (EvidenceRequestError, 422),
        (EvidenceAccessError, 404),
        (EvidenceMetadataError, 409),
        (EvidenceReadError, 503),
    ],
)
def test_safe_error_translation_without_partial_evidence(
    http, monkeypatch, error, status
):
    def fail(*args, **kwargs):
        raise error("secret SELECT postgresql://private-dsn")

    monkeypatch.setattr(migration, "resolve_inspection_access", fail)
    safe(post(http), status)


def test_real_metadata_and_database_failures(http, monkeypatch):
    safe(post(http, dict(BODY, thread_ids=[20])), 409)
    monkeypatch.setattr(
        migration,
        "chatlog_db",
        SimpleNamespace(
            _connect=lambda: psycopg.connect(http.url, dbname="inspection_nonexistent")
        ),
    )
    safe(post(http), 503)


def test_no_writes_or_forbidden_downstream_calls(http, monkeypatch):
    blocked = (
        "guardian.core.ai_router",
        "guardian.core.chat_completion_service",
        "guardian.core.outbox",
        "guardian.queue.document_embed_queue",
        "backend.rag.chatgpt_migration",
        "guardian.providers",
        "guardian.inference",
        "guardian.continuity",
        "guardian.personal_facts",
        "guardian.services.memory_vault",
        "guardian.connectors",
        "guardian.events",
        "backend.rag.personal_fact_extraction",
    )
    from guardian.core import event_bus
    from guardian.queue import redis_queue

    for module, name in [
        (event_bus, "emit_event"),
        (redis_queue, "enqueue_chat_import_embed"),
    ]:
        monkeypatch.setattr(
            module, name, Mock(side_effect=AssertionError("Forbidden downstream call"))
        )
    before = snapshot(http.url)
    previous = sys.getprofile()

    def profile(frame, event, arg):
        if event == "call" and (
            frame.f_globals.get("__name__", "").startswith(blocked)
            or (
                frame.f_globals.get("__name__", "").startswith("guardian.queue")
                and frame.f_code.co_name.startswith("enqueue")
            )
        ):
            raise AssertionError("Forbidden runtime consumer")

    try:
        threading.setprofile_all_threads(profile)
        assert post(http).status_code == 200
        assert post(http, dict(BODY, thread_ids=[15, 16])).status_code == 200
    finally:
        threading.setprofile_all_threads(previous)
    assert snapshot(http.url) == before
    assert http.redis.writes == 0
    event_bus.emit_event.assert_not_called()
    redis_queue.enqueue_chat_import_embed.assert_not_called()


def test_private_preview_account_session_and_approved_email(http, monkeypatch):
    email = "owner@history.test"
    with psycopg.connect(http.url) as conn:
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,'preview-owner','fixture')",
            (email,),
        )
        conn.execute("UPDATE projects SET user_id=%s WHERE id=1", (email,))
        conn.execute("UPDATE chat_threads SET user_id=%s WHERE id IN (10,11)", (email,))
        conn.execute(
            "UPDATE chat_messages SET user_id=%s, extra_meta=jsonb_set(extra_meta,'{user_id}',to_jsonb(%s::text)) WHERE thread_id IN (10,11)",
            (email, email),
        )
    token = issue_session_token(email, purpose="account_session")[0]
    http.store.store(token, email, 3600)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", email)
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", "")
    headers = {"Authorization": "Bearer " + token, "X-User-Id": B}
    assert post(http, headers=headers).status_code == 200
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "")
    safe(post(http, headers=headers), 401)


def test_migration_mount_boundary_unchanged():
    # Static wiring evidence only; HTTP tests above exercise this same router.
    source = (
        Path(__file__).resolve().parents[2] / "guardian/guardian_api.py"
    ).read_text()
    assert (
        'flag_name="CODEXIFY_ENABLE_MIGRATION_ROUTES",\n    include_fn=lambda: app.include_router(migration.router)'
        in source
    )
    assert [r.path for r in migration.router.routes].count(PATH) == 1


@pytest.mark.parametrize("field", list(BODY))
def test_explicit_request_fields_required(http, field):
    body = dict(BODY)
    del body[field]
    safe(post(http, body), 422)


def test_http_wire_budget_and_utf8_excerpt_preserved(http):
    response = post(
        http,
        dict(
            BODY,
            max_messages=2,
            max_inspected_messages=5,
            max_excerpt_bytes=5,
            max_response_bytes=2400,
        ),
    )
    assert response.status_code == 200, response.text
    assert len(response.content) <= 2400
    data = response.json()
    assert all(len(e["excerpt"].encode()) <= 5 for e in data["excerpts"])
    coverage = data["coverage"]
    assert not coverage["selected_window_complete"]
    assert coverage["inspected_records"] == sum(
        coverage[k]
        for k in (
            "returned_records",
            "unproven_import_records",
            "omitted_by_message_limit",
            "omitted_by_response_budget",
        )
    )


def test_resolver_database_read_only_enforced(http, monkeypatch):
    before = snapshot(http.url)
    captured = psycopg.connect(http.url)

    def attempted_write(*args, **kwargs):
        captured.execute("UPDATE chat_threads SET title='changed' WHERE id=10")

    monkeypatch.setattr(
        migration, "chatlog_db", SimpleNamespace(_connect=lambda: captured)
    )
    monkeypatch.setattr(access, "require_thread_read_access", attempted_write)
    safe(post(http), 503)
    assert snapshot(http.url) == before


def test_no_receipt_reuse_across_http_requests(http, monkeypatch):
    receipts = []
    original = migration.resolve_inspection_access

    def collect(*args, **kwargs):
        receipt = original(*args, **kwargs)
        assert receipt.principal is kwargs["principal"]
        receipts.append(receipt)
        return receipt

    monkeypatch.setattr(migration, "resolve_inspection_access", collect)
    assert post(http).status_code == 200
    assert post(http).status_code == 200
    assert receipts[0] is not receipts[1]
    assert receipts[0].principal is not receipts[1].principal


@pytest.mark.parametrize("transport", ["cookie", "bearer"])
def test_local_key_and_account_session_cannot_choose_by_header_precedence(
    http, monkeypatch, transport
):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    http.settings.CODEXIFY_MULTI_USER_ENABLED = False
    token = issue_session_token(B, purpose="account_session")[0]
    http.store.store(token, B, 3600)
    if transport == "cookie":
        http.client.cookies.set("gc_session", token)
        headers = {"Authorization": "Bearer history-local-key"}
    else:
        headers = {"X-API-Key": "history-local-key", "Authorization": "Bearer " + token}
    safe(post(http, headers=headers), 400)


def test_legitimate_local_account_session_keeps_server_approved_identity(
    http, monkeypatch
):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    http.settings.CODEXIFY_MULTI_USER_ENABLED = False
    token = issue_session_token(B, purpose="account_session")[0]
    http.store.store(token, B, 3600)
    headers = {"Authorization": "Bearer " + token, "X-User-Id": A}
    response = post(http, dict(BODY, project_id=3, thread_ids=[14]), headers)
    assert response.status_code == 200, response.text
    assert response.json()["excerpts"][0]["message_id"] == 140
    safe(post(http, headers=headers), 404)


@pytest.mark.parametrize(
    "subject,status", [(A, 200), (B, 401), ("unknown-subject", 401)]
)
def test_remote_single_user_signed_subject_cannot_fall_back_to_another_account(
    http, subject, status
):
    http.settings.CODEXIFY_MULTI_USER_ENABLED = False
    token = issue_session_token(subject, purpose="account_session")[0]
    response = post(http, headers={"Authorization": "Bearer " + token, "X-User-Id": B})
    if status == 200:
        assert response.status_code == 200, response.text
        assert response.json()["excerpts"][0]["message_id"] == 101
    else:
        safe(response, status)


def test_authentication_store_unavailable_is_safe_and_never_reads(http, monkeypatch):
    def fail(key):
        raise RuntimeError("secret authentication backend diagnostics")

    monkeypatch.setattr(http.redis, "get", fail)
    reader = Mock(side_effect=AssertionError("Unauthenticated reader call"))
    monkeypatch.setattr(migration, "ImportedHistoryEvidenceReader", reader)
    safe(post(http), 503)
    reader.assert_not_called()
