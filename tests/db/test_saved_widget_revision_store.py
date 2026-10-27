"""Saved Widget storage: canonical identity, immutable revisions, isolation.

Proves the persistence foundation against a real disposable PostgreSQL
database. Nothing here is stubbed: the eligibility service, the ORM models,
the schema constraints, and the transaction boundaries are all the real ones.

The store is an internal repository. These tests prove its storage semantics;
they do not prove, and do not create, a user-facing save capability.

Contract: docs/architecture/saved-widget-contract.md
Storage authority: docs/architecture/data-and-storage.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import json
import os
import pathlib
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import quote

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.core.saved_widget_store import (
    PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT,
    REVISION_ORIGIN_INITIAL_PROMOTION,
    REVISION_ORIGIN_REVISION_APPEND,
    SAVED_WIDGET_ID_PREFIX,
    SavedWidgetConflict,
    SavedWidgetIneligible,
    SavedWidgetInvalidState,
    SavedWidgetNotFound,
    append_saved_widget_revision,
    promote_saved_widget,
    read_saved_widget,
    read_saved_widget_revision,
    read_saved_widget_revisions,
)
from guardian.core.saved_widget_validation import (
    REASON_EXTERNAL_DEPENDENCY,
    REASON_KIND_NOT_SANDBOX,
    REASON_MISSING_EXECUTABLE_CODE,
    REASON_SOURCE_NOT_AUTHORIZED,
)
from guardian.db.models import (
    ChatCompletionAttempt,
    ChatMessage,
    ChatThread,
    SavedWidget,
    SavedWidgetRevision,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

ACCOUNT_A = "saved-widget-account-a"
ACCOUNT_B = "saved-widget-account-b"

ELIGIBLE_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<button id='go'>go</button>",
    "js": "document.getElementById('go').onclick = function () {};",
}

SECOND_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<button id='go'>go again</button>",
    "js": "document.getElementById('go').onclick = function () { console.log(2); };",
}

EXTERNAL_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<button id='go'>go</button>",
    "js": "document.getElementById('go').onclick = function () {};",
    "css": "@import url('https://cdn.example.com/base.css');",
}

NATIVE_ARTIFACT = {
    "version": 1,
    "kind": "native",
    "component": "chart.bar",
}

NO_CODE_ARTIFACT = {
    "version": 1,
    "kind": "sandbox",
    "html": "<p>static</p>",
}


def _encode(payload: dict[str, Any]) -> str:
    """Percent-encode a payload the way the model-facing wire format does."""
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return quote(text, safe="-_.!~*'()")


def _marker(payload: dict[str, Any]) -> str:
    return f"<!-- cfy-ui:{_encode(payload)} -->"


class _ChatLogAdapter:
    """Minimal stand-in for the GuardianDB adapter's session contract.

    It supplies only ``_sa_session()``. The eligibility lookup, the ORM
    models, the schema constraints, and the transaction boundaries are all
    the real ones; nothing about the persistence path is stubbed out.
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _sa_session(self):
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                session.invalidate()
            raise
        finally:
            session.close()


@pytest.fixture
def disposable_database():
    """A disposable PostgreSQL database migrated to head."""
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_saved_widget_store_{uuid.uuid4().hex[:12]}"
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
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    os.environ["GUARDIAN_DATABASE_URL"] = test_url.render_as_string(hide_password=False)

    try:
        command.upgrade(config, "head")
        engine = sa.create_engine(test_url)
        session_factory = sessionmaker(bind=engine)
        yield _ChatLogAdapter(session_factory)
        engine.dispose()
    finally:
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("GUARDIAN_DATABASE_URL", None)
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
    ) -> str:
        with adapter._sa_session() as session:
            request = f"req-{uuid.uuid4().hex[:12]}"
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


def _eligible_source(chatlog, *, account_id: str) -> tuple[int, int]:
    """Build one eligible, server-proven source without promoting it."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(account_id)
    message_id = make_message(thread_id, account_id, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)
    return thread_id, message_id


def _promote(
    chatlog,
    *,
    account_id: str = ACCOUNT_A,
    artifact: dict[str, Any] | None = None,
    name: str = "Test widget",
):
    """Build one eligible, server-proven candidate and promote it."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(account_id)
    message_id = make_message(
        thread_id, account_id, _marker(artifact or ELIGIBLE_ARTIFACT)
    )
    make_attempt(thread_id, message_id)
    record = promote_saved_widget(
        adapter,
        account_id=account_id,
        thread_id=thread_id,
        message_id=message_id,
        name=name,
    )
    return adapter, thread_id, message_id, record


# ---------------------------------------------------------------------------
# Canonical identity and ownership
# ---------------------------------------------------------------------------


def test_widget_identity_is_server_generated_and_stable(chatlog) -> None:
    """The identity is opaque, server-assigned, and never caller-chosen."""
    adapter, _, _, first = _promote(chatlog, name="First")
    _, _, _, second = _promote(chatlog, name="Second")

    assert first.widget_id.startswith(SAVED_WIDGET_ID_PREFIX)
    assert second.widget_id.startswith(SAVED_WIDGET_ID_PREFIX)
    assert first.widget_id != second.widget_id

    # The identity is stable across reads.
    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=first.widget_id
    )
    assert readback is not None
    assert readback.widget_id == first.widget_id


def test_ownership_is_the_account_and_is_singular(chatlog) -> None:
    """The canonical owner is the account, and it is the only owner field."""
    adapter, _, _, record = _promote(chatlog)

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.owner_user_id == ACCOUNT_A

    with adapter._sa_session() as session:
        widget = session.query(SavedWidget).filter_by(widget_id=record.widget_id).one()
        owner_columns = {
            column.name
            for column in widget.__table__.columns
            if column.name.endswith("_id")
            and column.name not in {"widget_id", "current_revision"}
        }
        # Exactly one ownership column, and it points at the account.
        assert owner_columns == {"owner_user_id"}


def test_two_same_account_widgets_each_have_revision_one(chatlog) -> None:
    """Revision numbering is scoped to the widget, not to the account."""
    adapter, _, _, first = _promote(chatlog, name="First")
    _, _, _, second = _promote(chatlog, name="Second")

    assert first.widget_id != second.widget_id
    assert first.current_revision == 1
    assert second.current_revision == 1

    first_revisions = read_saved_widget_revisions(
        adapter, account_id=ACCOUNT_A, widget_id=first.widget_id
    )
    second_revisions = read_saved_widget_revisions(
        adapter, account_id=ACCOUNT_A, widget_id=second.widget_id
    )
    assert [r.revision for r in first_revisions] == [1]
    assert [r.revision for r in second_revisions] == [1]

    # Both rows coexist: revision identity is (widget_id, revision).
    with adapter._sa_session() as session:
        assert (
            session.query(SavedWidgetRevision)
            .filter_by(revision=1)
            .count()
            == 2
        )


def test_initial_creation_writes_the_widget_and_its_first_revision_atomically(
    chatlog,
) -> None:
    """Both rows exist together, and the pointer names revision 1."""
    adapter, _, _, record = _promote(chatlog)

    with adapter._sa_session() as session:
        widget = session.query(SavedWidget).filter_by(widget_id=record.widget_id).one()
        revisions = (
            session.query(SavedWidgetRevision)
            .filter_by(widget_id=record.widget_id)
            .all()
        )
        assert widget.current_revision == 1
        assert [row.revision for row in revisions] == [1]
        assert revisions[0].edit_base_revision is None
        assert widget.lifecycle_state == "active"


# ---------------------------------------------------------------------------
# Provenance independence
# ---------------------------------------------------------------------------


def test_the_revision_snapshots_server_proven_provenance(chatlog) -> None:
    """Provenance is snapshotted, classified, and keeps its accepted-at time."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    provenance = readback.current.provenance_snapshot
    assert provenance["source_thread_id"] == thread_id
    assert provenance["source_message_id"] == message_id
    assert provenance["completion_attempt_request_id"].startswith("req-")
    assert provenance["provenance_classification"] == (
        PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT
    )
    assert provenance["captured_at"]
    assert provenance.get("accepted_at")


def test_deleting_the_source_thread_does_not_destroy_the_widget(chatlog) -> None:
    """A Saved Widget outlives the conversation it came from."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    before = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert before is not None

    with adapter._sa_session() as session:
        session.execute(
            sa.text("DELETE FROM chat_threads WHERE id = :id"), {"id": thread_id}
        )

    # The source rows are gone.
    with adapter._sa_session() as session:
        assert session.query(ChatThread).filter_by(id=thread_id).count() == 0
        assert session.query(ChatMessage).filter_by(id=message_id).count() == 0
        assert session.query(ChatCompletionAttempt).count() == 0

    # The widget and its provenance survive unchanged.
    after = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert after is not None
    assert after.current_revision == 1
    assert after.current.artifact_snapshot == before.current.artifact_snapshot
    assert after.current.provenance_snapshot == before.current.provenance_snapshot


# ---------------------------------------------------------------------------
# Append-only revisions
# ---------------------------------------------------------------------------


def test_appending_a_revision_advances_the_pointer_monotonically(chatlog) -> None:
    """A new revision is appended; the pointer moves forward."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    appended = append_saved_widget_revision(
        adapter,
        account_id=ACCOUNT_A,
        widget_id=record.widget_id,
        base_revision=1,
        thread_id=thread_id,
        message_id=message_id,
    )
    assert appended.revision == 2
    assert appended.edit_base_revision == 1
    assert appended.creation_context["origin"] == REVISION_ORIGIN_REVISION_APPEND

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.current_revision == 2
    assert [r.revision for r in readback.revisions] == [1, 2]
    assert readback.current.artifact_snapshot == appended.artifact_snapshot


def test_an_earlier_revision_snapshot_is_never_rewritten(chatlog) -> None:
    """History is immutable: revision 1 is byte-identical after revision 2."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    before = read_saved_widget_revision(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id, revision=1
    )
    assert before is not None
    before_artifact = dict(before.artifact_snapshot)
    before_provenance = dict(before.provenance_snapshot)

    append_saved_widget_revision(
        adapter,
        account_id=ACCOUNT_A,
        widget_id=record.widget_id,
        base_revision=1,
        thread_id=thread_id,
        message_id=message_id,
    )

    after = read_saved_widget_revision(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id, revision=1
    )
    assert after is not None
    assert after.artifact_snapshot == before_artifact
    assert after.provenance_snapshot == before_provenance


def test_a_stale_edit_base_is_reported_as_an_explicit_conflict(chatlog) -> None:
    """An outdated base is rejected, and the store does not re-base silently."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    append_saved_widget_revision(
        adapter,
        account_id=ACCOUNT_A,
        widget_id=record.widget_id,
        base_revision=1,
        thread_id=thread_id,
        message_id=message_id,
    )

    with pytest.raises(SavedWidgetConflict) as excinfo:
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_A,
            widget_id=record.widget_id,
            base_revision=1,
            thread_id=thread_id,
            message_id=message_id,
        )

    conflict = excinfo.value
    assert conflict.base_revision == 1
    assert conflict.current_revision == 2
    # The rejected candidate is still available to the caller.
    assert conflict.candidate_artifact is not None
    assert conflict.candidate_artifact.get("kind") == "sandbox"

    # Nothing was appended by the rejected attempt.
    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.current_revision == 2
    assert [r.revision for r in readback.revisions] == [1, 2]


def test_concurrent_appends_on_one_edit_base_produce_at_most_one_revision(
    chatlog,
) -> None:
    """Two writers on the same base cannot both win."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    barrier = threading.Barrier(2, timeout=30)
    succeeded: list[Any] = []
    failed: list[BaseException] = []

    def _worker() -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError as exc:  # pragma: no cover
            failed.append(exc)
            return
        try:
            succeeded.append(
                append_saved_widget_revision(
                    adapter,
                    account_id=ACCOUNT_A,
                    widget_id=record.widget_id,
                    base_revision=1,
                    thread_id=thread_id,
                    message_id=message_id,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - the failure is the assertion
            failed.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(succeeded) == 1, f"expected one winner, got {len(succeeded)}"
    assert len(failed) == 1
    assert isinstance(failed[0], SavedWidgetConflict)
    assert failed[0].current_revision == 2

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.current_revision == 2
    assert [r.revision for r in readback.revisions] == [1, 2]


def test_a_failed_append_leaves_no_partial_revision(chatlog) -> None:
    """A failed write rolls back completely: no revision, no pointer move."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    # Occupy revision 2 directly so the store's insert violates the composite
    # primary key. The whole transaction must roll back.
    with adapter._sa_session() as session:
        session.add(
            SavedWidgetRevision(
                widget_id=record.widget_id,
                revision=2,
                artifact_snapshot={"probe": True},
                provenance_snapshot={"probe": True},
                creation_context={"probe": True},
                edit_base_revision=1,
            )
        )
        session.flush()

    with pytest.raises(IntegrityError):
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_A,
            widget_id=record.widget_id,
            base_revision=1,
            thread_id=thread_id,
            message_id=message_id,
        )

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    # The pointer did not move, and the occupied row was not overwritten.
    assert readback.current_revision == 1
    occupied = read_saved_widget_revision(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id, revision=2
    )
    assert occupied is not None
    assert occupied.provenance_snapshot == {"probe": True}


def test_a_failed_widget_transaction_leaves_neither_row(chatlog) -> None:
    """A broken revision takes the widget row down with it."""
    adapter, _, _, _ = chatlog

    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.add(
                SavedWidget(
                    widget_id="sw-atomicity-probe",
                    owner_user_id=ACCOUNT_A,
                    name="Atomicity probe",
                    lifecycle_state="active",
                    current_revision=1,
                )
            )
            session.flush()
            # edit_base_revision 7 is not below revision 1, so this row is
            # invalid and the transaction must not commit.
            session.add(
                SavedWidgetRevision(
                    widget_id="sw-atomicity-probe",
                    revision=1,
                    artifact_snapshot={},
                    provenance_snapshot={},
                    creation_context={},
                    edit_base_revision=7,
                )
            )
            session.flush()

    with adapter._sa_session() as session:
        assert (
            session.query(SavedWidget)
            .filter_by(widget_id="sw-atomicity-probe")
            .count()
            == 0
        )
        assert (
            session.query(SavedWidgetRevision)
            .filter_by(widget_id="sw-atomicity-probe")
            .count()
            == 0
        )


# ---------------------------------------------------------------------------
# Account isolation
# ---------------------------------------------------------------------------


def test_a_cross_account_read_returns_nothing(chatlog) -> None:
    """Another account cannot see that the widget exists."""
    adapter, _, _, record = _promote(chatlog)

    assert (
        read_saved_widget(adapter, account_id=ACCOUNT_B, widget_id=record.widget_id)
        is None
    )
    assert (
        read_saved_widget_revisions(
            adapter, account_id=ACCOUNT_B, widget_id=record.widget_id
        )
        == ()
    )
    assert (
        read_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_B,
            widget_id=record.widget_id,
            revision=1,
        )
        is None
    )


def test_a_cross_account_write_fails_closed(chatlog) -> None:
    """Another account cannot append a revision to the widget.

    The candidate is the caller's *own* eligible artifact, so the failure is
    the widget-ownership check rather than a source-authorization check.
    """
    adapter, _, _, record = _promote(chatlog)
    other_thread, other_message = _eligible_source(chatlog, account_id=ACCOUNT_B)

    with pytest.raises(SavedWidgetNotFound):
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_B,
            widget_id=record.widget_id,
            base_revision=1,
            thread_id=other_thread,
            message_id=other_message,
        )

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.current_revision == 1


def test_a_missing_widget_is_indistinguishable_from_a_foreign_one(chatlog) -> None:
    """The failure for "not mine" is the failure for "does not exist"."""
    adapter, _, _, record = _promote(chatlog)
    other_thread, other_message = _eligible_source(chatlog, account_id=ACCOUNT_B)

    with pytest.raises(SavedWidgetNotFound) as foreign:
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_B,
            widget_id=record.widget_id,
            base_revision=1,
            thread_id=other_thread,
            message_id=other_message,
        )
    with pytest.raises(SavedWidgetNotFound) as missing:
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_B,
            widget_id="sw-does-not-exist",
            base_revision=1,
            thread_id=other_thread,
            message_id=other_message,
        )
    assert type(foreign.value) is type(missing.value)


# ---------------------------------------------------------------------------
# Lifecycle safety
# ---------------------------------------------------------------------------


def test_a_deleted_widget_does_not_return_its_executable_source(chatlog) -> None:
    """Deletion withdraws the source; identity and numbering stay addressable."""
    adapter, _, _, record = _promote(chatlog)

    with adapter._sa_session() as session:
        session.execute(
            sa.text(
                "UPDATE saved_widgets SET lifecycle_state = 'deleted' "
                "WHERE widget_id = :widget_id"
            ),
            {"widget_id": record.widget_id},
        )

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.lifecycle_state == "deleted"
    assert readback.source_withheld is True
    assert readback.current.artifact_snapshot is None
    # The identity and the revision numbering remain addressable for audit.
    assert readback.widget_id == record.widget_id
    assert readback.current_revision == 1

    revision = read_saved_widget_revision(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id, revision=1
    )
    assert revision is not None
    assert revision.artifact_snapshot is None


def test_an_archived_widget_is_not_treated_as_active(chatlog) -> None:
    """An archived widget is not a servable program."""
    adapter, _, _, record = _promote(chatlog)

    with adapter._sa_session() as session:
        session.execute(
            sa.text(
                "UPDATE saved_widgets SET lifecycle_state = 'archived' "
                "WHERE widget_id = :widget_id"
            ),
            {"widget_id": record.widget_id},
        )

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    assert readback.lifecycle_state == "archived"
    assert readback.source_withheld is True
    assert readback.current.artifact_snapshot is None


def test_an_inactive_widget_refuses_a_new_revision(chatlog) -> None:
    """A deleted widget accepts no further revisions."""
    adapter, thread_id, message_id, record = _promote(chatlog)

    with adapter._sa_session() as session:
        session.execute(
            sa.text(
                "UPDATE saved_widgets SET lifecycle_state = 'deleted' "
                "WHERE widget_id = :widget_id"
            ),
            {"widget_id": record.widget_id},
        )

    with pytest.raises(SavedWidgetInvalidState):
        append_saved_widget_revision(
            adapter,
            account_id=ACCOUNT_A,
            widget_id=record.widget_id,
            base_revision=1,
            thread_id=thread_id,
            message_id=message_id,
        )


# ---------------------------------------------------------------------------
# Schema-level guarantees
# ---------------------------------------------------------------------------


def test_the_database_refuses_an_invalid_lifecycle_state(chatlog) -> None:
    adapter, _, _, _ = chatlog
    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.add(
                SavedWidget(
                    widget_id="sw-bad-lifecycle",
                    owner_user_id=ACCOUNT_A,
                    name="Bad lifecycle",
                    lifecycle_state="banana",
                    current_revision=1,
                )
            )
            session.flush()


def test_the_database_refuses_a_dangling_current_revision_pointer(chatlog) -> None:
    """The pointer may not name a revision that does not exist."""
    adapter, _, _, _ = chatlog
    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.add(
                SavedWidget(
                    widget_id="sw-dangling-pointer",
                    owner_user_id=ACCOUNT_A,
                    name="Dangling pointer",
                    lifecycle_state="active",
                    current_revision=9,
                )
            )
            session.flush()


def test_the_database_refuses_a_duplicate_revision(chatlog) -> None:
    adapter, _, _, record = _promote(chatlog)
    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.add(
                SavedWidgetRevision(
                    widget_id=record.widget_id,
                    revision=1,
                    artifact_snapshot={},
                    provenance_snapshot={},
                    creation_context={},
                    edit_base_revision=None,
                )
            )
            session.flush()


def test_the_database_refuses_an_invalid_owner(chatlog) -> None:
    """A widget cannot belong to an account that does not exist."""
    adapter, _, _, _ = chatlog
    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.add(
                SavedWidget(
                    widget_id="sw-bad-owner",
                    owner_user_id="no-such-account",
                    name="Bad owner",
                    lifecycle_state="active",
                    current_revision=1,
                )
            )
            session.flush()


def test_a_stored_revision_cannot_be_updated_in_place(chatlog) -> None:
    """The narrow database guard makes a revision immutable."""
    adapter, _, _, record = _promote(chatlog)

    with pytest.raises(IntegrityError):
        with adapter._sa_session() as session:
            session.execute(
                sa.text(
                    "UPDATE saved_widget_revisions "
                    "SET creation_context = CAST(:context AS jsonb) "
                    "WHERE widget_id = :widget_id AND revision = 1"
                ),
                {
                    "context": json.dumps({"rewritten": True}),
                    "widget_id": record.widget_id,
                },
            )

    revision = read_saved_widget_revision(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id, revision=1
    )
    assert revision is not None
    assert revision.creation_context.get("rewritten") is None


# ---------------------------------------------------------------------------
# E1-E6 are preserved
# ---------------------------------------------------------------------------


def test_an_external_dependency_artifact_cannot_be_promoted(chatlog) -> None:
    """E4 still governs promotion: the store does not bypass eligibility."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(EXTERNAL_ARTIFACT))
    make_attempt(thread_id, message_id)

    with pytest.raises(SavedWidgetIneligible) as excinfo:
        promote_saved_widget(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            name="External",
        )
    assert REASON_EXTERNAL_DEPENDENCY in excinfo.value.reasons

    with adapter._sa_session() as session:
        assert session.query(SavedWidget).count() == 0
        assert session.query(SavedWidgetRevision).count() == 0


def test_a_native_artifact_cannot_be_promoted(chatlog) -> None:
    """E2 still governs promotion."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(NATIVE_ARTIFACT))
    make_attempt(thread_id, message_id)

    with pytest.raises(SavedWidgetIneligible) as excinfo:
        promote_saved_widget(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            name="Native",
        )
    assert REASON_KIND_NOT_SANDBOX in excinfo.value.reasons


def test_an_artifact_without_executable_code_cannot_be_promoted(chatlog) -> None:
    """E3 still governs promotion."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(NO_CODE_ARTIFACT))
    make_attempt(thread_id, message_id)

    with pytest.raises(SavedWidgetIneligible) as excinfo:
        promote_saved_widget(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            name="No code",
        )
    assert REASON_MISSING_EXECUTABLE_CODE in excinfo.value.reasons


def test_a_source_without_server_proven_lineage_cannot_be_promoted(chatlog) -> None:
    """E5 still governs promotion: an unaccepted attempt proves nothing."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_A)
    message_id = make_message(thread_id, ACCOUNT_A, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id, accepted=False)

    with pytest.raises(SavedWidgetIneligible):
        promote_saved_widget(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            name="Unproven",
        )

    with adapter._sa_session() as session:
        assert session.query(SavedWidget).count() == 0
        assert session.query(SavedWidgetRevision).count() == 0


def test_a_cross_account_source_cannot_be_promoted(chatlog) -> None:
    """Ownership of the source is still enforced at promotion time."""
    adapter, make_thread, make_message, make_attempt = chatlog
    thread_id = make_thread(ACCOUNT_B)
    message_id = make_message(thread_id, ACCOUNT_B, _marker(ELIGIBLE_ARTIFACT))
    make_attempt(thread_id, message_id)

    with pytest.raises(SavedWidgetIneligible) as excinfo:
        promote_saved_widget(
            adapter,
            account_id=ACCOUNT_A,
            thread_id=thread_id,
            message_id=message_id,
            name="Foreign source",
        )
    assert REASON_SOURCE_NOT_AUTHORIZED in excinfo.value.reasons


# ---------------------------------------------------------------------------
# No runtime activation
# ---------------------------------------------------------------------------


def test_the_store_activates_no_route_and_no_model_authority() -> None:
    """Storage exists; the product does not yet use it."""
    import guardian.core.saved_widget_store as store

    # The module defines no web surface and no dispatch surface.
    for attribute in ("router", "APIRouter", "app", "register_tool", "dispatch"):
        assert not hasattr(store, attribute), attribute

    # No route module imports the store.
    routes_dir = REPO_ROOT / "guardian" / "routes"
    offenders = [
        path.name
        for path in sorted(routes_dir.glob("*.py"))
        if "saved_widget_store" in path.read_text()
    ]
    assert offenders == []

    # The store is not reachable from the model-facing tool surface.
    tool_dirs = [
        REPO_ROOT / "guardian" / "agent_tools",
        REPO_ROOT / "guardian" / "tools",
    ]
    for directory in tool_dirs:
        if not directory.exists():
            continue
        offenders = [
            path.name
            for path in sorted(directory.rglob("*.py"))
            if "saved_widget_store" in path.read_text()
        ]
        assert offenders == []


def test_a_promotion_records_its_origin_and_actor(chatlog) -> None:
    """The revision-creation context is recorded, not inferred."""
    adapter, _, _, record = _promote(chatlog)

    readback = read_saved_widget(
        adapter, account_id=ACCOUNT_A, widget_id=record.widget_id
    )
    assert readback is not None
    context = readback.current.creation_context
    assert context["origin"] == REVISION_ORIGIN_INITIAL_PROMOTION
    assert context["actor"] == "guardian"
    assert context["captured_at"]
