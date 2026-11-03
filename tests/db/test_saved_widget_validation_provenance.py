"""Saved Widget eligibility: server-proven provenance and account isolation.

E5 requires that the origin of a candidate be proven by the *server*, from
authoritative stored records, and never by a caller-supplied claim. This
suite exercises the real read-only lookup in ``guardian.core.db`` against a
disposable Postgres database built by the repository's own Alembic
migrations. No production data is used and no row is written by the code
under test.

Contract: docs/architecture/saved-widget-contract.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.core.saved_widget_validation import (
    REASON_ENVELOPE_INVALID,
    REASON_KIND_NOT_SANDBOX,
    REASON_PROVENANCE_CONTRADICTORY,
    REASON_PROVENANCE_NOT_ACCEPTED,
    REASON_PROVENANCE_UNPROVEN,
    REASON_SELECTION_INVALID,
    REASON_SELECTION_MISMATCH,
    REASON_SOURCE_NOT_AUTHORIZED,
    WidgetCandidateStatus,
    assess_saved_widget_candidate,
)
from guardian.db.models import ChatCompletionAttempt, ChatMessage, ChatThread

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

ACCOUNT_A = "saved-widget-account-a"
ACCOUNT_B = "saved-widget-account-b"

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


def _encode(payload: dict[str, Any]) -> str:
    """Percent-encode a payload the way the model-facing wire format does."""
    from urllib.parse import quote

    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return quote(text, safe="-_.!~*'()")


def _marker(payload: dict[str, Any]) -> str:
    return f"<!-- cfy-ui:{_encode(payload)} -->"


class _ChatLogAdapter:
    """Minimal stand-in for the GuardianDB adapter's session contract.

    It supplies only ``_sa_session()``. The query under test is the real one
    in ``guardian.core.db``; nothing about the lookup is stubbed out.
    """

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
    """A disposable Postgres database at the current Alembic head.

    Uses the same infrastructure as the repository's other Postgres proofs:
    a uniquely named database created from the admin connection and dropped
    afterwards. It never touches an existing database.
    """
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_saved_widget_{uuid.uuid4().hex[:12]}"
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
    monkeypatch.setenv("GUARDIAN_DATABASE_URL", test_url.render_as_string(hide_password=False))

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
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.fixture
def chatlog(disposable_database):
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


def _row_counts(adapter) -> dict[str, int]:
    with adapter._sa_session() as session:
        return {
            "threads": session.query(ChatThread).count(),
            "messages": session.query(ChatMessage).count(),
            "attempts": session.query(ChatCompletionAttempt).count(),
        }


# ---------------------------------------------------------------------------
# The eligible path
# ---------------------------------------------------------------------------


def test_server_proven_assistant_artifact_is_an_eligible_candidate(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, f"Here you go.\n{_marker(ELIGIBLE_ARTIFACT)}")
    request_id = make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.ELIGIBLE
    assert assessment.reasons == ()
    assert assessment.is_eligible
    assert assessment.artifact is not None
    assert assessment.artifact["kind"] == "sandbox"
    assert assessment.lineage is not None
    assert assessment.lineage.request_id == request_id
    assert assessment.lineage.message_id == message_id
    assert assessment.lineage.thread_id == thread_id


def test_assessment_creates_no_persistent_record(chatlog) -> None:
    """A Widget Candidate is ephemeral. Nothing may be written."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    before = _row_counts(adapter)
    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )
    after = _row_counts(adapter)

    assert assessment.status is WidgetCandidateStatus.ELIGIBLE
    assert before == after, "the assessment must not write anything"
    # And it must not hand back a widget identity.
    assert assessment.as_dict().get("widget_id") is None
    assert assessment.as_dict().get("widget_revision") is None


# ---------------------------------------------------------------------------
# Account isolation
# ---------------------------------------------------------------------------


def test_cross_account_source_cannot_pass(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    other_thread = make_thread(ACCOUNT_B)
    other_message = make_message(other_thread, ACCOUNT_B, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(other_thread, other_message)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=other_thread,
        message_id=other_message,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert assessment.reasons == (REASON_SOURCE_NOT_AUTHORIZED,)
    assert assessment.artifact is None
    assert assessment.lineage is None


def test_missing_source_is_indistinguishable_from_a_cross_account_source(chatlog) -> None:
    """A caller must not be able to probe for another account's messages."""
    adapter, make_thread, make_message, make_attempt = chatlog
    other_thread = make_thread(ACCOUNT_B)
    other_message = make_message(other_thread, ACCOUNT_B, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(other_thread, other_message)

    missing = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=other_thread,
        message_id=987654321,
    )
    cross_account = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=other_thread,
        message_id=other_message,
    )

    assert missing.reasons == cross_account.reasons
    assert missing.status is cross_account.status
    assert missing.as_dict() == cross_account.as_dict()


def test_wrong_thread_source_cannot_pass(chatlog) -> None:
    """A message that exists but is in another thread is not a valid source."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_a = make_thread(ACCOUNT_A, "Thread A")
    thread_b = make_thread(ACCOUNT_A, "Thread B")
    message_id = make_message(thread_a, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_a, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_b,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert assessment.reasons == (REASON_SOURCE_NOT_AUTHORIZED,)


def test_user_role_message_is_not_an_assistant_source(chatlog) -> None:
    """Message role alone is not provenance, and a user message is not a source."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(
        thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT), role="user"
    )
    make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert assessment.reasons == (REASON_SOURCE_NOT_AUTHORIZED,)


# ---------------------------------------------------------------------------
# E5: completion-attempt provenance
# ---------------------------------------------------------------------------


def test_missing_completion_attempt_cannot_prove_provenance(chatlog) -> None:
    adapter, make_thread, make_message, _ = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert REASON_PROVENANCE_UNPROVEN in assessment.reasons
    assert assessment.lineage is None


def test_unaccepted_attempt_cannot_prove_provenance(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id, accepted=False)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert REASON_PROVENANCE_NOT_ACCEPTED in assessment.reasons


def test_contradictory_terminal_failure_cannot_prove_provenance(chatlog) -> None:
    """A terminal failure or cancellation on the same message is a contradiction."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id, terminal_event_type="task.failed")

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert REASON_PROVENANCE_CONTRADICTORY in assessment.reasons
    assert assessment.lineage is None


def test_a_cancelled_attempt_cannot_prove_provenance(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id, terminal_event_type="task.cancelled")

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert REASON_PROVENANCE_CONTRADICTORY in assessment.reasons


# ---------------------------------------------------------------------------
# Server-owned source resolution
# ---------------------------------------------------------------------------


def test_artifact_is_resolved_from_stored_content_not_from_the_caller(chatlog) -> None:
    """A caller-supplied payload is never proof that it is the stored artifact."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    stored = _marker(ELIGIBLE_ARTIFACT)
    message_id = make_message(thread_id, ACCOUNT_A, stored)
    make_attempt(thread_id, message_id)

    # A caller claims a different, perfectly valid payload.
    forged = _marker(
        {
            "version": 1,
            "kind": "sandbox",
            "html": "<p>attacker supplied</p>",
            "js": "void 0;",
        }
    )

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
        claimed_payload=forged,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert assessment.reasons == (REASON_SELECTION_MISMATCH,)
    # The stored artifact is not the caller's payload.
    assert assessment.artifact is None


def test_a_matching_claimed_payload_is_accepted(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
        claimed_payload=_encode(ELIGIBLE_ARTIFACT),
    )

    assert assessment.status is WidgetCandidateStatus.ELIGIBLE


def test_invalid_artifact_index_is_rejected(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    for index in (-1, 1, 99):
        assessment = assess_saved_widget_candidate(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            artifact_index=index,
        )
        assert assessment.status is WidgetCandidateStatus.INELIGIBLE
        assert assessment.reasons == (REASON_SELECTION_INVALID,)


def test_a_malformed_marker_in_the_message_is_reported_as_structurally_invalid(
    chatlog,
) -> None:
    """A malformed marker is selectable, so it can be named rather than skipped."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(
        thread_id, ACCOUNT_A, "<!-- cfy-ui:not-a-payload -->"
    )
    make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.STRUCTURALLY_INVALID
    assert REASON_ENVELOPE_INVALID in assessment.reasons


def test_a_native_artifact_in_stored_content_is_not_a_v1_candidate(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(NATIVE_ARTIFACT))
    make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert REASON_KIND_NOT_SANDBOX in assessment.reasons
    # The lineage was proven, so the only failure is the artifact-side gate.
    assert assessment.lineage is not None


def test_the_second_artifact_in_a_message_is_selectable(chatlog) -> None:
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(
        thread_id,
        ACCOUNT_A,
        f"{_marker(NATIVE_ARTIFACT)}\n{_marker(ELIGIBLE_ARTIFACT)}",
    )
    make_attempt(thread_id, message_id)

    assessment = assess_saved_widget_candidate(
        adapter,
        account_id=ACCOUNT_A,
        thread_id=thread_id,
        message_id=message_id,
        artifact_index=1,
    )

    assert assessment.status is WidgetCandidateStatus.ELIGIBLE
    assert assessment.artifact_index == 1
    assert assessment.valid_artifact_index == 1
