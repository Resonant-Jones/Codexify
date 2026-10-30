"""Route and authorization tests for account-scoped historical recall.

These tests drive the real HTTP surface (``GET
/api/chat/projects/{project_id}/history/search``) through the authenticated
principal seam and the canonical database fixture, so the account binding,
the Project scope, and the failure mapping are exercised as deployed.

The data-access boundary is validated against a disposable SQLAlchemy
database rather than mocks. A disposable PostgreSQL variant of the same
boundary is not executed in this environment because no ``TEST_DATABASE_URL``
is available here.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import dependencies
from guardian.db.models import ChatMessage
from guardian.routes import chat
from tests.core.test_account_history_recall import (  # noqa: F401
    ACCOUNT_A,
    ACCOUNT_B,
    _seed,
    session_factory,
)


API_KEY = "history-recall-local-key"
RECALL_PATH = "/api/chat/projects/{project_id}/history/search"


class _DatabaseStub:
    """Minimal chatlog surface: the route only needs a session factory."""

    def __init__(self, session_factory_):
        self._session_factory = session_factory_

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()


class _BrokenDatabaseStub:
    def get_session(self):
        raise RuntimeError("database unavailable")


@pytest.fixture
def client(session_factory, monkeypatch):  # noqa: F811
    """Authenticated local-mode client bound to the disposable database."""

    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", ACCOUNT_A)
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)
    monkeypatch.setattr(
        dependencies, "chatlog_db", _DatabaseStub(session_factory)
    )

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    with TestClient(app) as test_client:
        yield test_client


def _auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


# ---------------------------------------------------------------------------
# Authorized recall
# ---------------------------------------------------------------------------


def test_a_signed_in_user_can_recall_their_project_history(client, session_factory):
    _seed(
        session_factory,
        messages=[
            ("user", "We discussed the original memory architecture", "2025-05-02T10:00:00+00:00"),
        ],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory architecture"},
        headers=_auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["account_id"] == ACCOUNT_A
    assert body["project_id"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["occurred_at"] == "2025-05-02T10:00:00+00:00"
    assert body["results"][0]["origin_system"] == "codexify"
    assert body["treatment"] == "inert_evidence"
    assert any(
        "UNTRUSTED HISTORY EVIDENCE" in block
        for block in body["evidence_blocks"]
    )


def test_the_recall_window_bounds_the_result(client, session_factory):
    _seed(
        session_factory,
        messages=[
            ("user", "memory architecture", "2025-04-01T10:00:00+00:00"),
            ("user", "memory architecture", "2025-05-02T10:00:00+00:00"),
        ],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={
            "q": "memory architecture",
            "start": "2025-05-01",
            "end": "2025-05-31",
        },
        headers=_auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["occurred_at"] == "2025-05-02T10:00:00+00:00"


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_missing_authentication_is_rejected(client, session_factory):
    # The repository TestClient injects a default API key, so an empty key
    # header is how this suite expresses "no credential presented".
    _seed(session_factory)

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory"},
        headers={"X-API-Key": ""},
    )

    assert response.status_code == 401


def test_a_model_supplied_account_identifier_cannot_change_the_scope(
    client, session_factory
):
    """An account field in the request is ignored, never honoured."""

    _seed(
        session_factory,
        messages=[
            ("user", "memory architecture", "2025-05-02T10:00:00+00:00"),
        ],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory architecture", "account_id": ACCOUNT_B},
        headers=_auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == ACCOUNT_A
    assert body["results"][0]["thread_id"] is not None


def test_a_user_id_header_cannot_redirect_the_account(
    client, session_factory, monkeypatch
):
    """Even with the debug header override enabled, recall stays on account."""

    monkeypatch.setenv("DEBUG", "true")
    _seed(
        session_factory,
        account_id=ACCOUNT_B,
        project_owner=ACCOUNT_B,
        messages=[("user", "other account history", "2025-05-02T10:00:00+00:00")],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "other account history"},
        headers={**_auth(), "X-User-Id": ACCOUNT_B},
    )

    assert response.status_code == 403
    assert "other account history" not in response.text


def test_cross_account_retrieval_fails_closed(client, session_factory):
    _seed(
        session_factory,
        account_id=ACCOUNT_B,
        project_owner=ACCOUNT_B,
        messages=[("user", "other account history", "2025-05-02T10:00:00+00:00")],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "other account history"},
        headers=_auth(),
    )

    assert response.status_code == 403
    assert "other account history" not in response.text


def test_a_missing_project_is_denied(client, session_factory):
    _seed(session_factory)

    response = client.get(
        RECALL_PATH.format(project_id=987),
        params={"q": "memory"},
        headers=_auth(),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Imported archive handling
# ---------------------------------------------------------------------------


def test_imported_conversations_are_not_exposed_through_the_route(
    client, session_factory
):
    _seed(
        session_factory,
        thread_kwargs={"origin_system": "openai"},
        messages=[
            ("user", "exported chatgpt transcript", "2025-05-02T10:00:00+00:00"),
        ],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "exported chatgpt transcript"},
        headers=_auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["coverage"]["excluded_imported_threads"] == 1
    assert "exported chatgpt transcript" not in str(body["results"])


# ---------------------------------------------------------------------------
# Failure behavior
# ---------------------------------------------------------------------------


def test_an_invalid_window_bound_is_a_bad_request(client, session_factory):
    _seed(session_factory)

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory", "start": "not-a-date"},
        headers=_auth(),
    )

    assert response.status_code == 400


def test_an_empty_result_is_distinguishable_from_a_failure(client, session_factory):
    _seed(
        session_factory,
        messages=[("user", "memory architecture", "2025-05-02T10:00:00+00:00")],
    )

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "no such subject"},
        headers=_auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["coverage"]["returned_records"] == 0


def test_a_database_failure_is_not_reported_as_an_empty_success(
    client, session_factory, monkeypatch
):
    _seed(session_factory)
    monkeypatch.setattr(dependencies, "chatlog_db", _BrokenDatabaseStub())

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory"},
        headers=_auth(),
    )

    assert response.status_code == 503


def test_the_recall_route_does_not_mutate_records(client, session_factory):
    _seed(
        session_factory,
        messages=[("user", "memory architecture", "2025-05-02T10:00:00+00:00")],
    )

    with session_factory() as session:
        before = [
            (row.id, row.content) for row in session.query(ChatMessage).all()
        ]

    response = client.get(
        RECALL_PATH.format(project_id=1),
        params={"q": "memory architecture"},
        headers=_auth(),
    )

    assert response.status_code == 200
    with session_factory() as session:
        after = [
            (row.id, row.content) for row in session.query(ChatMessage).all()
        ]
    assert before == after
