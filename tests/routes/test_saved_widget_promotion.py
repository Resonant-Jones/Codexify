"""Guardian-authorized Saved Widget promotion: the authorized operation.

This suite exercises the real HTTP surface in ``guardian.routes.saved_widgets``
against a disposable Postgres database built by the repository's own Alembic
migrations. Nothing about the store, the eligibility service, or the E5
provenance lookup is stubbed: the route calls the same code paths the
product calls.

What is proven here:

* an authenticated, account-authorized promotion of an eligible accepted
  artifact succeeds and returns canonical identities;
* the persisted revision is readable under its owning account;
* a missing, unaccepted, failed, cancelled, cross-account, or ineligible
  source fails closed, and a failed promotion writes nothing;
* client-supplied provenance, artifact payloads, and approval flags are
  structurally incapable of influencing the outcome;
* repeated and concurrent promotions respect the accepted identity
  semantics and leave no partial state;
* the operation is not model-dispatchable and grants no execution capability.

Contract: docs/architecture/saved-widget-contract.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.core import dependencies
from guardian.core.dependencies import get_account_user_id, require_account_session
from guardian.core.saved_widget_store import (
    PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT,
    SAVED_WIDGET_ID_PREFIX,
)
from guardian.core.saved_widget_validation import (
    REASON_KIND_NOT_SANDBOX,
    REASON_PROVENANCE_CONTRADICTORY,
    REASON_PROVENANCE_NOT_ACCEPTED,
    REASON_PROVENANCE_UNPROVEN,
    REASON_SOURCE_NOT_AUTHORIZED,
)
from guardian.db.models import (
    ChatCompletionAttempt,
    ChatMessage,
    ChatThread,
    SavedWidget,
    SavedWidgetRevision,
)
from guardian.routes.saved_widgets import router as saved_widgets_router

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

ACCOUNT_A = "saved-widget-promotion-account-a"
ACCOUNT_B = "saved-widget-promotion-account-b"

ELIGIBLE_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<button id='go'>go</button>",
    "js": "document.getElementById('go').onclick = function () {};",
}

NATIVE_ARTIFACT = {
    "version": 1,
    "kind": "native",
    "component": "chart.bar",
    "props": {"series": [{"label": "Mon", "value": 42}]},
}

EXTERNAL_DEPENDENCY_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<img src='https://cdn.example.com/logo.png'>",
    "js": "",
}


def _encode(payload: dict[str, Any]) -> str:
    from urllib.parse import quote

    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return quote(text, safe="-_.!~*'()")


def _marker(payload: dict[str, Any]) -> str:
    return f"<!-- cfy-ui:{_encode(payload)} -->"


class _ChatLogAdapter:
    """Minimal stand-in for the GuardianDB adapter's session contract."""

    def __init__(self, session_factory: Any) -> None:
        self._SessionLocal = session_factory

    @contextmanager
    def _sa_session(self) -> Iterator[Any]:
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@pytest.fixture
def disposable_database(monkeypatch):
    """A disposable Postgres database at the current Alembic head."""
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_saved_widget_promotion_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)

    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(f"CREATE DATABASE {db_name}")

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    monkeypatch.setenv(
        "GUARDIAN_DATABASE_URL", test_url.render_as_string(hide_password=False)
    )

    try:
        command.upgrade(config, "head")
        engine = sa.create_engine(test_url)
        session_factory = sessionmaker(bind=engine)
        yield _ChatLogAdapter(session_factory)
        engine.dispose()
    finally:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.fixture
def seeded(disposable_database):
    """A populated database plus helpers for building authoritative rows."""
    adapter = disposable_database

    def _seed_account(account_id: str) -> None:
        with adapter._sa_session() as session:
            session.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :id, 'inert-test-hash', 'guest')"
                ),
                {"id": account_id},
            )

    def _make_thread(account_id: str, title: str = "Thread") -> int:
        with adapter._sa_session() as session:
            thread = ChatThread(user_id=account_id, title=title)
            session.add(thread)
            session.flush()
            return int(thread.id)

    def _make_message(
        thread_id: int,
        account_id: str,
        content: str,
        role: str = "assistant",
    ) -> int:
        with adapter._sa_session() as session:
            message = ChatMessage(
                thread_id=thread_id,
                user_id=account_id,
                role=role,
                content=content,
                kind="chat",
                event_at=datetime.now(timezone.utc),
                extra_meta={},
            )
            session.add(message)
            session.flush()
            return int(message.id)

    def _make_attempt(
        thread_id: int,
        message_id: int | None,
        *,
        accepted: bool = True,
        terminal_event_type: str | None = None,
        request_id: str | None = None,
    ) -> str:
        with adapter._sa_session() as session:
            request = request_id or f"req-{uuid.uuid4().hex[:12]}"
            attempt = ChatCompletionAttempt(
                request_id=request,
                backend_task_id=f"task-{uuid.uuid4().hex[:12]}",
                thread_id=thread_id,
                turn_id=f"turn-{uuid.uuid4().hex[:12]}",
                completed_message_id=message_id,
                terminal_event_type=terminal_event_type,
                accepted_at=(
                    datetime.now(timezone.utc) if accepted else None
                ),
            )
            session.add(attempt)
            session.flush()
            return request

    _seed_account(ACCOUNT_A)
    _seed_account(ACCOUNT_B)
    return adapter, _make_thread, _make_message, _make_attempt


@pytest.fixture
def client(seeded, monkeypatch):
    """A TestClient over the saved-widgets router with an explicit account."""
    adapter, _thread, _message, _attempt = seeded
    monkeypatch.setattr(dependencies, "chatlog_db", adapter)

    app = FastAPI()
    app.include_router(saved_widgets_router)

    def _account() -> str:
        return ACCOUNT_A

    app.dependency_overrides[require_account_session] = lambda: "session-credential"
    app.dependency_overrides[get_account_user_id] = _account

    with TestClient(app) as test_client:
        yield test_client


def _promotion_body(thread_id: int, message_id: int, name: str = "My Widget"):
    return {
        "name": name,
        "thread_id": thread_id,
        "message_id": message_id,
    }


def _widget_rows(adapter) -> int:
    with adapter._sa_session() as session:
        return session.query(SavedWidget).count()


def _revision_rows(adapter) -> int:
    with adapter._sa_session() as session:
        return session.query(SavedWidgetRevision).count()


# ---------------------------------------------------------------------------
# The authorized path
# ---------------------------------------------------------------------------


def test_authorized_promotion_succeeds_for_an_eligible_accepted_artifact(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(
        thread_id, ACCOUNT_A, f"Here you go.\n{_marker(ELIGIBLE_ARTIFACT)}"
    )
    make_attempt(thread_id, message_id)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["widget_id"].startswith(SAVED_WIDGET_ID_PREFIX)
    assert body["revision"] == 1
    assert body["current_revision"] == 1
    assert body["lifecycle_state"] == "active"
    assert body["name"] == "My Widget"


def test_promotion_denormalizes_server_proven_provenance(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    request_id = make_attempt(thread_id, message_id)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))
    assert response.status_code == 201, response.text

    provenance = response.json()["provenance"]
    assert provenance["provenance_classification"] == (
        PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT
    )
    assert provenance["source_thread_id"] == thread_id
    assert provenance["source_message_id"] == message_id
    assert provenance["completion_attempt_request_id"] == request_id
    assert provenance["captured_at"]


def test_promotion_persists_exactly_one_widget_and_one_revision(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))
    assert response.status_code == 201, response.text

    assert _widget_rows(adapter) == 1
    assert _revision_rows(adapter) == 1


def test_persisted_revision_is_readable_under_the_owning_account(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    created = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id)
    ).json()
    widget_id = created["widget_id"]

    readback = client.get(f"/saved-widgets/{widget_id}")
    assert readback.status_code == 200, readback.text
    body = readback.json()
    assert body["widget_id"] == widget_id
    assert body["current_revision"] == 1
    assert body["source_withheld"] is False
    assert [r["revision"] for r in body["revisions"]] == [1]
    assert (
        body["provenance"]["provenance_classification"]
        == PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT
    )


def test_revision_readback_returns_the_immutable_snapshot(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    created = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id)
    ).json()
    widget_id = created["widget_id"]

    revision = client.get(f"/saved-widgets/{widget_id}/revisions/1")
    assert revision.status_code == 200, revision.text
    body = revision.json()
    assert body["revision"] == 1
    assert body["edit_base_revision"] is None
    assert body["artifact_snapshot"]["kind"] == "sandbox"

    history = client.get(f"/saved-widgets/{widget_id}/revisions")
    assert history.status_code == 200, history.text
    assert [r["revision"] for r in history.json()["revisions"]] == [1]


# ---------------------------------------------------------------------------
# Failing closed
# ---------------------------------------------------------------------------


def test_cross_account_promotion_is_denied(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    other_thread = make_thread(ACCOUNT_B)
    other_message = make_message(
        other_thread, ACCOUNT_B, _marker(ELIGIBLE_ARTIFACT)
    )
    make_attempt(other_thread, other_message)

    response = client.post(
        "/saved-widgets", json=_promotion_body(other_thread, other_message)
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"]["reasons"] == [REASON_SOURCE_NOT_AUTHORIZED]
    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


def test_cross_account_readback_is_indistinguishable_from_missing(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)
    widget_id = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id)
    ).json()["widget_id"]

    missing = client.get("/saved-widgets/sw_does_not_exist")
    assert missing.status_code == 404, missing.text

    # Reading another account's widget is the same error, not a distinct one.
    app = client.app
    app.dependency_overrides[get_account_user_id] = lambda: ACCOUNT_B
    try:
        wrong_account = client.get(f"/saved-widgets/{widget_id}")
    finally:
        app.dependency_overrides[get_account_user_id] = lambda: ACCOUNT_A

    assert wrong_account.status_code == 404, wrong_account.text
    assert wrong_account.json()["detail"]["error"] == missing.json()["detail"]["error"]


def test_unaccepted_attempt_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id, accepted=False)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert REASON_PROVENANCE_NOT_ACCEPTED in response.json()["detail"]["reasons"]
    assert _widget_rows(adapter) == 0


def test_contradictory_terminal_attempt_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(
        thread_id,
        message_id,
        accepted=True,
        terminal_event_type="task.failed",
    )

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert REASON_PROVENANCE_CONTRADICTORY in response.json()["detail"]["reasons"]
    assert _widget_rows(adapter) == 0


def test_cancelled_attempt_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(
        thread_id,
        message_id,
        accepted=False,
        terminal_event_type="task.cancelled",
    )

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


def test_missing_provenance_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    # No completion attempt at all.

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert REASON_PROVENANCE_UNPROVEN in response.json()["detail"]["reasons"]
    assert _widget_rows(adapter) == 0


def test_non_assistant_source_message_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    # A user message that merely claims assistant authorship.
    message_id = make_message(
        thread_id,
        ACCOUNT_A,
        _marker(ELIGIBLE_ARTIFACT),
        role="user",
    )
    make_attempt(thread_id, message_id)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert REASON_SOURCE_NOT_AUTHORIZED in response.json()["detail"]["reasons"]
    assert _widget_rows(adapter) == 0


def test_native_kind_artifact_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(NATIVE_ARTIFACT))
    make_attempt(thread_id, message_id)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert REASON_KIND_NOT_SANDBOX in response.json()["detail"]["reasons"]
    assert _widget_rows(adapter) == 0


def test_external_dependency_artifact_fails_closed(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(
        thread_id, ACCOUNT_A, _marker(EXTERNAL_DEPENDENCY_ARTIFACT)
    )
    make_attempt(thread_id, message_id)

    response = client.post("/saved-widgets", json=_promotion_body(thread_id, message_id))

    assert response.status_code == 422, response.text
    assert _widget_rows(adapter) == 0


def test_failed_promotion_writes_no_partial_state(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(NATIVE_ARTIFACT))
    make_attempt(thread_id, message_id)

    assert client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id)
    ).status_code == 422

    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


# ---------------------------------------------------------------------------
# Client claims are structurally inert
# ---------------------------------------------------------------------------


def test_client_supplied_provenance_and_approval_fields_are_rejected(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = _promotion_body(thread_id, message_id)
    body["approved"] = True
    body["provenance"] = {"provenance_classification": "generated"}
    body["role"] = "assistant"

    response = client.post("/saved-widgets", json=body)

    assert response.status_code == 422, response.text
    assert _widget_rows(adapter) == 0


def test_client_supplied_artifact_payload_is_rejected(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = _promotion_body(thread_id, message_id)
    body["artifact"] = ELIGIBLE_ARTIFACT

    response = client.post("/saved-widgets", json=body)

    assert response.status_code == 422, response.text
    assert _widget_rows(adapter) == 0


# ---------------------------------------------------------------------------
# The display name is a required, requester-supplied field
# ---------------------------------------------------------------------------


def test_the_display_name_is_required(client, seeded) -> None:
    """An absent display name is rejected by the request schema.

    The accepted contract makes the display name one of the five things an
    explicit promotion requires, and it is supplied by the requester. A
    promotion without one never reaches the store.
    """
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = _promotion_body(thread_id, message_id)
    del body["name"]

    response = client.post("/saved-widgets", json=body)

    assert response.status_code == 422, response.text
    # A missing required field is reported by the schema, not by the route.
    errors = response.json()["detail"]
    assert isinstance(errors, list), errors
    assert any("name" in str(error.get("loc", "")) for error in errors), errors
    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


def test_a_blank_display_name_is_rejected(client, seeded) -> None:
    """Whitespace-only satisfies the schema's length rule but is not a name."""
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = _promotion_body(thread_id, message_id, name="   ")

    response = client.post("/saved-widgets", json=body)

    assert response.status_code == 400, response.text
    assert response.json()["detail"]["error"] == "invalid_request"
    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


def test_an_over_long_display_name_is_rejected(client, seeded) -> None:
    """The display name is bounded by the same bound the store enforces."""
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = _promotion_body(thread_id, message_id, name="x" * 256)

    response = client.post("/saved-widgets", json=body)

    assert response.status_code == 422, response.text
    assert _widget_rows(adapter) == 0
    assert _revision_rows(adapter) == 0


def test_the_persisted_widget_retains_the_requester_supplied_display_name(
    client, seeded
) -> None:
    """The name the requester supplied is the name that is stored.

    Surrounding whitespace is normalized away; the name itself is kept
    verbatim, so the widget is identifiable by what its owner called it.
    """
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    requested = "Q3 Revenue Dashboard"
    response = client.post(
        "/saved-widgets",
        json=_promotion_body(thread_id, message_id, name=f"  {requested}  "),
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == requested

    widget_id = response.json()["widget_id"]
    readback = client.get(f"/saved-widgets/{widget_id}")
    assert readback.status_code == 200, readback.text
    assert readback.json()["name"] == requested


def test_promotion_requires_an_account_session(seeded, monkeypatch) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    monkeypatch.setattr(dependencies, "chatlog_db", adapter)
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    app = FastAPI()
    app.include_router(saved_widgets_router)

    def _reject() -> str:
        raise HTTPException(status_code=401, detail="Account session required")

    app.dependency_overrides[require_account_session] = _reject
    app.dependency_overrides[get_account_user_id] = lambda: ACCOUNT_A

    with TestClient(app) as test_client:
        response = test_client.post(
            "/saved-widgets", json=_promotion_body(thread_id, message_id)
        )

    assert response.status_code == 401, response.text
    assert _widget_rows(adapter) == 0


# ---------------------------------------------------------------------------
# Repeated and concurrent promotion
# ---------------------------------------------------------------------------


def test_repeated_promotion_creates_distinct_canonical_identities(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    first = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id, "First")
    )
    second = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id, "Second")
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    first_id = first.json()["widget_id"]
    second_id = second.json()["widget_id"]

    # Two explicit human acts are two resources, not one overwritten resource.
    assert first_id != second_id
    assert first.json()["revision"] == second.json()["revision"] == 1
    assert _widget_rows(adapter) == 2
    assert _revision_rows(adapter) == 2

    # Each keeps its own name and its own identity.
    assert client.get(f"/saved-widgets/{first_id}").json()["name"] == "First"
    assert client.get(f"/saved-widgets/{second_id}").json()["name"] == "Second"


def test_concurrent_promotion_is_atomic_and_leaves_no_orphan_revision(
    client, seeded
) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    def _promote(index: int):
        return client.post(
            "/saved-widgets", json=_promotion_body(thread_id, message_id, f"W{index}")
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(_promote, range(4)))

    assert all(r.status_code == 201 for r in responses), [
        r.status_code for r in responses
    ]
    widget_ids = {r.json()["widget_id"] for r in responses}
    assert len(widget_ids) == 4
    assert _widget_rows(adapter) == 4
    assert _revision_rows(adapter) == 4

    # Every widget is readable and holds exactly its own first revision.
    for widget_id in widget_ids:
        readback = client.get(f"/saved-widgets/{widget_id}")
        assert readback.status_code == 200, readback.text
        assert [r["revision"] for r in readback.json()["revisions"]] == [1]


# ---------------------------------------------------------------------------
# No capability expansion
# ---------------------------------------------------------------------------


def test_promotion_response_carries_no_executable_source(client, seeded) -> None:
    adapter, make_thread, make_message, make_attempt = seeded
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    body = client.post(
        "/saved-widgets", json=_promotion_body(thread_id, message_id)
    ).json()

    # The promotion result names the resource; it does not hand back a
    # program that something might render.
    assert "artifact" not in body
    assert "artifact_snapshot" not in body
    assert "html" not in body
    assert "js" not in body


def test_the_router_exposes_no_invocation_or_installation_surface() -> None:
    paths = {route.path for route in saved_widgets_router.routes}
    for path in paths:
        lowered = path.lower()
        for forbidden in (
            "invoke",
            "render",
            "install",
            "publish",
            "launch",
            "execute",
        ):
            assert forbidden not in lowered, path


def test_promotion_is_not_advertised_to_the_model() -> None:
    """The model's ordinary-chat tool set is a fixed allowlist.

    ``resolve_ordinary_chat_tools`` returns only the health command and,
    conditionally, the repository-search command. A new mutating route can
    never enter it, and the command-bus manifest classifies the promotion as
    a write that requires confirmation.
    """
    from guardian.command_bus.manifest import build_manifest
    from guardian.tools.chat_exposure import resolve_ordinary_chat_tools

    app = FastAPI()
    app.include_router(saved_widgets_router)

    manifest = build_manifest(app)
    promotion = next(
        (
            command
            for command in manifest.commands
            if command.path_template == "/saved-widgets"
            and command.method == "POST"
        ),
        None,
    )
    assert promotion is not None, "the promotion route must be in the manifest"
    assert promotion.effect == "write"
    assert promotion.risk == "mutating"
    assert promotion.idempotency == "unsafe"
    # A write is never an unattended model call.
    assert promotion.approval_mode != "none"

    tools = resolve_ordinary_chat_tools(
        provider="deepseek",
        model="test-model",
        provider_vendor="test-vendor",
        manifest_commands=manifest.commands,
    )
    advertised = {
        str(tool.get("command_id"))
        for tool in (tools or [])
        if isinstance(tool, dict)
    }
    assert not any("saved" in command_id for command_id in advertised)
    assert "op::promote_saved_widget" not in advertised


def test_saved_widgets_route_is_enabled_in_every_supported_profile() -> None:
    """The route must not be silently quarantined by a route posture."""
    profiles_dir = REPO_ROOT / "config" / "supported_profiles"
    profiles = sorted(profiles_dir.glob("*.yaml"))
    assert profiles, "expected supported profiles to exist"

    for profile in profiles:
        text = profile.read_text()
        assert "    - saved_widgets\n" in text, profile.name
