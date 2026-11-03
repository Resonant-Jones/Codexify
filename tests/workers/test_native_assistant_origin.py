"""Native-origin proof for the accepted assistant-completion writer.

The canonical assistant writer binds an assistant message to its exact durable
completion attempt inside one transaction. These tests prove that the same
transaction carries the reserved native-origin assertion, and that nothing
short of that exact binding produces native proof.

Every test runs against disposable PostgreSQL, because the claim under test is
about a JSONB column written inside a transaction, not about the presence of
a JSON key.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from guardian.core.db import (
    MERGE_MESSAGE_METADATA_SQL,
    RESERVED_MESSAGE_ORIGIN_KEY,
    RESERVED_MESSAGE_ORIGIN_VERSION,
    create_chat_completion_attempt,
    mark_chat_completion_attempt_accepted,
    record_chat_completion_attempt_terminal_event,
)
from guardian.core.pgdb import PgDB
from tests.services.test_memory_vault_read_projection import _migrate_to_head

ACCOUNT = "assistant-origin-account"
ORIGIN_SYSTEM = "codexify"
FORGED_ASSERTED_AT = "1999-12-31T23:59:59+00:00"

#: A payload shaped exactly like the accepted assertion. Wherever it comes
#: from it is untrusted, and it must never be able to establish origin.
FORGED_ASSERTION = {
    RESERVED_MESSAGE_ORIGIN_KEY: {
        "version": 1,
        "origin_system": ORIGIN_SYSTEM,
        "asserted_at": FORGED_ASSERTED_AT,
    }
}

#: The canonical importer's message metadata shape. An imported record carries
#: positive provider lineage and must never be relabeled native.
IMPORTED_META = {
    "origin": "chatgpt_import",
    "canonical_filter_profile": "chatgpt_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-1",
    "source_message_id": "export-message-1",
    "source_created_at": "2025-05-02T10:00:00+00:00",
    "raw_role": "assistant",
    "era": "legacy",
}

#: The ADR-016 provenance fixture file. It is documentation-only, so these
#: tests read its expectations and then prove the *runtime* behaviour they
#: describe rather than treating the fixture text as proof.
PROVENANCE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "fixtures"
    / "history-message-provenance.v1.json"
)


def _admin_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.fail(
            "Disposable PostgreSQL proof requires explicit TEST_DATABASE_URL"
        )
    return url


@pytest.fixture(scope="module")
def database_url():
    """A disposable PostgreSQL database with the canonical schema applied."""
    admin = _admin_url()
    name = "assistant_origin_" + uuid.uuid4().hex
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


class _Repo:
    """The canonical store plus the plain connection URL for direct reads."""

    def __init__(self, store: PgDB, url: str) -> None:
        self._store = store
        self._url = url

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    @property
    def url(self) -> str:
        return self._url


@pytest.fixture
def repo(database_url):
    """A canonical database with one account, project, and thread."""
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "TRUNCATE chat_completion_attempts, chat_messages, chat_threads, "
            "projects, users CASCADE"
        )
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,%s,'fixture')",
            (ACCOUNT, "user-" + ACCOUNT),
        )
        conn.execute(
            "INSERT INTO projects(id,user_id,name) VALUES (1,%s,'assistant')",
            (ACCOUNT,),
        )
        conn.execute(
            "INSERT INTO chat_threads(id,user_id,project_id,title,origin_system) "
            "VALUES (10,%s,1,'assistant thread','codexify')",
            (ACCOUNT,),
        )
        conn.execute(
            "INSERT INTO chat_threads(id,user_id,project_id,title,origin_system) "
            "VALUES (11,%s,1,'other thread','codexify')",
            (ACCOUNT,),
        )
    store = PgDB(database_url)
    try:
        yield _Repo(store, database_url)
    finally:
        store._sa_engine.dispose()


def _accepted_attempt(
    repo,
    *,
    backend_task_id: str,
    turn_id: str = "turn-1",
    request_id: str = "request-1",
):
    """Create and accept one durable completion attempt for thread 10."""
    create_chat_completion_attempt(
        repo,
        request_id=request_id,
        backend_task_id=backend_task_id,
        thread_id=10,
        turn_id=turn_id,
    )
    mark_chat_completion_attempt_accepted(repo, backend_task_id=backend_task_id)


def _stored_extra_meta(repo, message_id: int) -> dict:
    with psycopg.connect(repo.url) as conn:
        row = conn.execute(
            "SELECT extra_meta FROM chat_messages WHERE id = %s", (message_id,)
        ).fetchone()
    return dict(row[0] or {}) if row is not None else {}


def _stored_message(repo, message_id: int) -> tuple | None:
    with psycopg.connect(repo.url) as conn:
        return conn.execute(
            "SELECT id, thread_id, role, extra_meta FROM chat_messages WHERE id = %s",
            (message_id,),
        ).fetchone()


def _assistant_count(repo) -> int:
    with psycopg.connect(repo.url) as conn:
        return int(
            conn.execute(
                "SELECT count(*) FROM chat_messages WHERE role = 'assistant'"
            ).fetchone()[0]
        )


def _attempt_row(repo, backend_task_id: str) -> dict:
    with psycopg.connect(repo.url) as conn:
        row = conn.execute(
            "SELECT request_id, thread_id, turn_id, completed_message_id, "
            "terminal_event_type, accepted_at FROM chat_completion_attempts "
            "WHERE backend_task_id = %s",
            (backend_task_id,),
        ).fetchone()
    return {
        "request_id": row[0],
        "thread_id": row[1],
        "turn_id": row[2],
        "completed_message_id": row[3],
        "terminal_event_type": row[4],
        "accepted_at": row[5],
    }


def _assertion(repo, message_id: int) -> dict:
    stored = _stored_extra_meta(repo, message_id)
    return dict(stored.get(RESERVED_MESSAGE_ORIGIN_KEY) or {})


def _fixture_by_id(fixture_id: str) -> dict:
    fixtures = json.loads(
        PROVENANCE_FIXTURE_PATH.read_text(encoding="utf-8")
    )["fixtures"]
    for entry in fixtures:
        if entry["id"] == fixture_id:
            return entry
    raise AssertionError(f"provenance fixture {fixture_id!r} is missing")


@contextmanager
def _failing_trigger(repo, *, table: str, timing: str, event: str):
    """Make one table operation fail at the database level.

    The disposable database is shared by the module, so the trigger is removed
    again when the block ends.
    """
    name = f"test_fail_{table}_{event}".lower()
    with psycopg.connect(repo.url) as conn:
        conn.execute(
            f"CREATE OR REPLACE FUNCTION {name}() RETURNS trigger AS $$ "
            "BEGIN "
            "RAISE EXCEPTION 'forced failure inside the canonical transaction'; "
            "END; "
            "$$ LANGUAGE plpgsql"
        )
        conn.execute(
            f"CREATE TRIGGER {name} BEFORE {timing} ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {name}()"
        )
    try:
        yield
    finally:
        with psycopg.connect(repo.url) as conn:
            conn.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}")
            conn.execute(f"DROP FUNCTION IF EXISTS {name}()")


# ---------------------------------------------------------------------------
# The accepted completion writer is the trusted creation boundary
# ---------------------------------------------------------------------------


def test_an_accepted_assistant_completion_receives_a_native_origin_assertion(
    repo,
):
    """The canonical writer stamps the reserved member for a bound completion."""
    _accepted_attempt(repo, backend_task_id="task-native")

    message_id, linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-native",
        turn_id="turn-1",
        extra_meta={"attempted_provider": "deepseek"},
    )

    assert linked is True
    assertion = _assertion(repo, message_id)

    assert assertion["version"] == RESERVED_MESSAGE_ORIGIN_VERSION
    assert assertion["origin_system"] == ORIGIN_SYSTEM


def test_the_assertion_timestamp_is_backend_generated_and_zoned(repo):
    """The backend owns the timestamp; the caller cannot supply it."""
    _accepted_attempt(repo, backend_task_id="task-zoned")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-zoned",
        turn_id="turn-1",
        extra_meta={
            RESERVED_MESSAGE_ORIGIN_KEY: {
                "version": 1,
                "origin_system": ORIGIN_SYSTEM,
                "asserted_at": FORGED_ASSERTED_AT,
            }
        },
    )

    asserted_at = _assertion(repo, message_id)["asserted_at"]
    moment = datetime.fromisoformat(asserted_at)

    assert asserted_at != FORGED_ASSERTED_AT
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)


def test_a_forged_native_looking_payload_cannot_control_the_assertion(repo):
    """An untrusted payload shaped like the assertion is discarded."""
    _accepted_attempt(repo, backend_task_id="task-forged")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-forged",
        turn_id="turn-1",
        extra_meta={
            **FORGED_ASSERTION,
            "version": 99,
            "origin_system": "openai",
        },
    )

    stored = _stored_extra_meta(repo, message_id)
    assertion = stored[RESERVED_MESSAGE_ORIGIN_KEY]

    assert assertion["asserted_at"] != FORGED_ASSERTED_AT
    assert assertion["version"] == RESERVED_MESSAGE_ORIGIN_VERSION
    assert assertion["origin_system"] == ORIGIN_SYSTEM


def test_unrelated_completion_metadata_keeps_its_semantics(repo):
    """The completion metadata keeps its established behaviour."""
    _accepted_attempt(repo, backend_task_id="task-metadata")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-metadata",
        turn_id="turn-1",
        extra_meta={
            "attempted_provider": "deepseek",
            "resolved_model": "deepseek-chat",
            "tool_loop_execution": {"iterations": 2},
        },
    )

    stored = _stored_extra_meta(repo, message_id)

    assert stored["attempted_provider"] == "deepseek"
    assert stored["resolved_model"] == "deepseek-chat"
    assert stored["tool_loop_execution"] == {"iterations": 2}
    assert RESERVED_MESSAGE_ORIGIN_KEY in stored


def test_conflicting_imported_origin_metadata_is_not_relabeled_native(repo):
    """Imported-source evidence wins; the record keeps its own provenance."""
    _accepted_attempt(repo, backend_task_id="task-imported")

    message_id, linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-imported",
        turn_id="turn-1",
        extra_meta=dict(IMPORTED_META),
    )

    stored = _stored_extra_meta(repo, message_id)

    assert linked is True
    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["origin"] == "chatgpt_import"
    assert stored["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert stored["source_message_id"] == "export-message-1"


def test_the_generic_writer_is_not_an_assistant_creation_authority(repo):
    """Role ``assistant`` alone proves nothing."""
    message_id = repo.create_message(
        10,
        "assistant",
        "unbound assistant output",
        user_id=ACCOUNT,
    )

    stored = _stored_extra_meta(repo, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_a_message_without_a_durable_attempt_stays_unproven(repo):
    """Without the exact attempt binding there is no creation proof."""
    message_id, linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-without-attempt",
        turn_id="turn-1",
    )

    assert linked is False
    assert RESERVED_MESSAGE_ORIGIN_KEY not in _stored_extra_meta(repo, message_id)


# ---------------------------------------------------------------------------
# The attempt-to-message binding is the proof
# ---------------------------------------------------------------------------


def test_the_attempt_is_bound_to_this_exact_message(repo):
    """The durable attempt names the message this transaction created."""
    _accepted_attempt(repo, backend_task_id="task-bound")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-bound",
        turn_id="turn-1",
    )

    attempt = _attempt_row(repo, "task-bound")
    stored = _stored_message(repo, message_id)

    assert attempt["completed_message_id"] == message_id
    assert attempt["request_id"] == "request-1"
    assert attempt["turn_id"] == "turn-1"
    assert attempt["terminal_event_type"] is None
    assert stored[1] == 10
    assert stored[2] == "assistant"


def test_an_attempt_for_another_identity_cannot_bind_this_message(repo):
    """A mismatched attempt identity refuses the write outright."""
    _accepted_attempt(repo, backend_task_id="task-mismatch")

    with pytest.raises(ValueError):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=10,
            content="assistant reply",
            request_id="request-1",
            backend_task_id="task-mismatch",
            turn_id="turn-other",
        )

    assert _assistant_count(repo) == 0
    assert _attempt_row(repo, "task-mismatch")["completed_message_id"] is None


def test_an_unrelated_attempt_cannot_claim_this_message(repo):
    """Each attempt binds to its own exact message; no binding is reused."""
    _accepted_attempt(repo, backend_task_id="task-first")
    _accepted_attempt(
        repo,
        backend_task_id="task-second",
        turn_id="turn-2",
        request_id="request-2",
    )

    first_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="first reply",
        request_id="request-1",
        backend_task_id="task-first",
        turn_id="turn-1",
    )
    second_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="second reply",
        request_id="request-2",
        backend_task_id="task-second",
        turn_id="turn-2",
    )

    assert first_id != second_id
    assert _attempt_row(repo, "task-first")["completed_message_id"] == first_id
    assert _attempt_row(repo, "task-second")["completed_message_id"] == second_id
    assert _assistant_count(repo) == 2


# ---------------------------------------------------------------------------
# Atomicity, retry, failure, and cancellation
# ---------------------------------------------------------------------------


def test_a_failed_insert_rolls_back_the_message_and_its_origin(repo):
    """A failed insert leaves neither a message nor a provenance write."""
    _accepted_attempt(repo, backend_task_id="task-rollback")

    with _failing_trigger(repo, table="chat_messages", timing="INSERT", event="insert"):
        with pytest.raises(psycopg.Error):
            repo.create_assistant_message_for_completion_attempt(
                thread_id=10,
                content="assistant reply",
                request_id="request-1",
                backend_task_id="task-rollback",
                turn_id="turn-1",
            )

    assert _assistant_count(repo) == 0
    attempt = _attempt_row(repo, "task-rollback")

    assert attempt["completed_message_id"] is None
    assert attempt["terminal_event_type"] is None


def test_a_failed_binding_rolls_back_the_inserted_message_and_its_origin(repo):
    """The assertion shares the message's transaction, not a later write.

    The trigger makes the attempt binding fail *after* the message row and its
    origin assertion have been written inside the transaction. If the
    assertion were written by a separate statement, the rolled-back message
    would leave a provenance claim behind; if it shared the transaction, both
    disappear together.
    """
    _accepted_attempt(repo, backend_task_id="task-binding-failure")

    with _failing_trigger(
        repo,
        table="chat_completion_attempts",
        timing="UPDATE",
        event="update",
    ):
        with pytest.raises(psycopg.Error):
            repo.create_assistant_message_for_completion_attempt(
                thread_id=10,
                content="assistant reply",
                request_id="request-1",
                backend_task_id="task-binding-failure",
                turn_id="turn-1",
            )

    assert _assistant_count(repo) == 0
    attempt = _attempt_row(repo, "task-binding-failure")

    assert attempt["completed_message_id"] is None
    assert attempt["terminal_event_type"] is None


def test_a_duplicate_completion_preserves_the_original_message_and_assertion(
    repo,
):
    """A repeated delivery returns the original message with its assertion."""
    _accepted_attempt(repo, backend_task_id="task-duplicate")

    first_id, first_linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-duplicate",
        turn_id="turn-1",
    )
    original = _assertion(repo, first_id)

    second_id, second_linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-duplicate",
        turn_id="turn-1",
    )

    assert first_linked is True
    assert second_linked is True
    assert second_id == first_id
    assert _assistant_count(repo) == 1
    assert _assertion(repo, second_id) == original
    assert _assertion(repo, second_id)["asserted_at"] == original["asserted_at"]


def test_a_retry_does_not_mint_a_second_assertion(repo):
    """The original asserted_at is never refreshed by a later delivery."""
    _accepted_attempt(repo, backend_task_id="task-retry")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-retry",
        turn_id="turn-1",
    )
    original = _assertion(repo, message_id)

    for _ in range(3):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=10,
            content="assistant reply",
            request_id="request-1",
            backend_task_id="task-retry",
            turn_id="turn-1",
        )

    assert _assistant_count(repo) == 1
    assert _assertion(repo, message_id) == original


def test_a_failed_attempt_cannot_produce_a_proven_assistant_row(repo):
    """A failed attempt is not reinterpreted as a successful native completion."""
    _accepted_attempt(repo, backend_task_id="task-failed")
    assert record_chat_completion_attempt_terminal_event(
        repo,
        request_id="request-1",
        backend_task_id="task-failed",
        thread_id=10,
        turn_id="turn-1",
        event_type="task.failed",
    )

    with pytest.raises(ValueError):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=10,
            content="assistant reply",
            request_id="request-1",
            backend_task_id="task-failed",
            turn_id="turn-1",
        )

    assert _assistant_count(repo) == 0
    assert _attempt_row(repo, "task-failed")["completed_message_id"] is None


def test_a_cancelled_attempt_cannot_produce_a_proven_assistant_row(repo):
    """A cancelled attempt is not reinterpreted as a successful completion."""
    _accepted_attempt(repo, backend_task_id="task-cancelled")
    assert record_chat_completion_attempt_terminal_event(
        repo,
        request_id="request-1",
        backend_task_id="task-cancelled",
        thread_id=10,
        turn_id="turn-1",
        event_type="task.cancelled",
    )

    with pytest.raises(ValueError):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=10,
            content="assistant reply",
            request_id="request-1",
            backend_task_id="task-cancelled",
            turn_id="turn-1",
        )

    assert _assistant_count(repo) == 0
    assert _attempt_row(repo, "task-cancelled")["completed_message_id"] is None


def test_an_attempt_pointing_at_no_assistant_in_its_thread_is_refused(repo):
    """A binding that names no assistant row cannot be honoured."""
    _accepted_attempt(repo, backend_task_id="task-dangling")

    other_thread_message = repo.create_message(
        11,
        "assistant",
        "assistant reply in another thread",
        user_id=ACCOUNT,
    )
    with psycopg.connect(repo.url) as conn:
        conn.execute(
            "UPDATE chat_completion_attempts SET completed_message_id = %s "
            "WHERE backend_task_id = %s",
            (other_thread_message, "task-dangling"),
        )

    with pytest.raises(ValueError):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=10,
            content="assistant reply",
            request_id="request-1",
            backend_task_id="task-dangling",
            turn_id="turn-1",
        )

    assert _assistant_count(repo) == 1
    assert _attempt_row(repo, "task-dangling")["completed_message_id"] == (
        other_thread_message
    )


# ---------------------------------------------------------------------------
# Custody of the stored assertion
# ---------------------------------------------------------------------------


def test_generic_metadata_enrichment_cannot_alter_the_assertion(repo):
    """The enrichment statement cannot replace, remove, or forge the member."""
    _accepted_attempt(repo, backend_task_id="task-enrich")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-enrich",
        turn_id="turn-1",
    )
    original = _assertion(repo, message_id)

    from psycopg.types.json import Jsonb

    for payload in (
        FORGED_ASSERTION,
        {RESERVED_MESSAGE_ORIGIN_KEY: None},
        {"unrelated": "value"},
    ):
        with repo._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    MERGE_MESSAGE_METADATA_SQL,
                    (Jsonb(payload), 10, message_id),
                )

    stored = _stored_extra_meta(repo, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY] == original
    assert stored["unrelated"] == "value"


def test_existing_user_message_stamping_still_works(repo):
    """The ordinary user-message writer is unaffected by this change."""
    message_id = repo.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )

    assertion = _assertion(repo, message_id)

    assert assertion["version"] == RESERVED_MESSAGE_ORIGIN_VERSION
    assert assertion["origin_system"] == ORIGIN_SYSTEM
    assert datetime.fromisoformat(assertion["asserted_at"]).tzinfo is not None


# ---------------------------------------------------------------------------
# The ADR-016 fixture, proven against the runtime
# ---------------------------------------------------------------------------


def test_the_native_assistant_fixture_describes_what_the_writer_produces(repo):
    """P02's stored evidence is the shape the trusted writer produces."""
    fixture = _fixture_by_id("P02")
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]
    expected_assertion = expected[RESERVED_MESSAGE_ORIGIN_KEY]

    _accepted_attempt(repo, backend_task_id="task-fixture")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-fixture",
        turn_id="turn-1",
    )
    stored = _assertion(repo, message_id)

    assert set(stored) == set(expected_assertion)
    assert stored["version"] == expected_assertion["version"]
    assert stored["origin_system"] == expected_assertion["origin_system"]
    assert fixture["expected_origin_classification"] == "native"


def test_the_imported_assistant_fixture_is_never_relabeled_native(repo):
    """P04's imported assistant evidence survives the trusted writer."""
    fixture = _fixture_by_id("P04")
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]

    _accepted_attempt(repo, backend_task_id="task-fixture-imported")

    message_id, _ = repo.create_assistant_message_for_completion_attempt(
        thread_id=10,
        content="assistant reply",
        request_id="request-1",
        backend_task_id="task-fixture-imported",
        turn_id="turn-1",
        extra_meta=dict(expected),
    )
    stored = _stored_extra_meta(repo, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["origin"] == expected["origin"]
    assert stored["canonical_filter_profile"] == expected[
        "canonical_filter_profile"
    ]


# ---------------------------------------------------------------------------
# The historical recall surface stays closed
# ---------------------------------------------------------------------------


def test_the_production_store_takes_the_worker_atomic_branch(repo):
    """The worker's trusted branch is the writer that stamps the origin.

    The worker selects the atomic writer by looking the method up on the
    *class* of the store it was given, and falls back to a create-then-enrich
    adapter when the class does not provide it. This asserts that the
    production chat store does provide it, so ordinary completions are stamped
    by the trusted writer rather than left unproven.
    """
    from guardian.core.chatlog_postgres import PostgresChatLogDB

    assert callable(
        getattr(
            type(PostgresChatLogDB(repo.url)),
            "create_assistant_message_for_completion_attempt",
            None,
        )
    )


def test_no_historical_recall_tool_becomes_visible(repo):
    """Assistant-origin qualification advertises nothing."""
    from fastapi import FastAPI

    from guardian.command_bus.manifest import build_manifest
    from guardian.routes import chat, health
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
