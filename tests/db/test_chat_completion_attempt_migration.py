"""Disposable Postgres upgrade and durable completion authority proof."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from guardian.core.db import (
    create_chat_completion_attempt,
    get_chat_completion_attempt_by_task_id,
    mark_chat_completion_attempt_accepted,
    record_chat_completion_attempt_terminal_event,
    reconcile_chat_completion_attempt_after_deadline,
)
from guardian.core.pgdb import PgDB


PREVIOUS_REVISION = "a8d4c2f6b1e9"
ATTEMPT_REVISION = "c9f3e2a7b601"


@pytest.fixture
def disposable_database(monkeypatch):
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    db_name = f"codexify_attempt_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {db_name}")
    config = Config(str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", test_url.render_as_string(hide_password=False).replace("%", "%%"))
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    try:
        yield config, test_url
    finally:
        with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.mark.integration
def test_upgrade_preserves_chat_data_and_adds_authority(disposable_database):
    config, test_url = disposable_database
    command.upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        for account in ("account-a", "account-b"):
            connection.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :id, 'inert-test-hash', 'guest')"
                ),
                {"id": account},
            )
        thread_a = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('account-a', 'Existing A') RETURNING id"
            )
        ).scalar_one()
        thread_b = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('account-b', 'Existing B') RETURNING id"
            )
        ).scalar_one()
        message_id = connection.execute(
            sa.text(
                "INSERT INTO chat_messages (thread_id, user_id, role, content) "
                "VALUES (:thread, 'account-a', 'user', 'pre-migration text') RETURNING id"
            ),
            {"thread": thread_a},
        ).scalar_one()

    command.upgrade(config, ATTEMPT_REVISION)
    inspector = sa.inspect(engine)
    assert "chat_completion_attempts" in inspector.get_table_names()
    assert {"request_id", "backend_task_id", "thread_id", "turn_id", "created_at", "accepted_at"} <= {
        column["name"] for column in inspector.get_columns("chat_completion_attempts")
    }
    assert ("backend_task_id",) in {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("chat_completion_attempts")
    }
    assert any(
        item["referred_table"] == "chat_threads" and item["constrained_columns"] == ["thread_id"]
        for item in inspector.get_foreign_keys("chat_completion_attempts")
    )
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM chat_completion_attempts")).scalar_one() == 0
        assert connection.execute(
            sa.text("SELECT content FROM chat_messages WHERE id = :id"), {"id": message_id}
        ).scalar_one() == "pre-migration text"
        assert connection.execute(sa.text("SELECT count(*) FROM users WHERE id IN ('account-a', 'account-b')")).scalar_one() == 2

    command.upgrade(config, "head")
    inspector = sa.inspect(engine)
    assert {
        "completed_message_id",
        "terminal_event_type",
    } <= {column["name"] for column in inspector.get_columns("chat_completion_attempts")}

    repo = PgDB(test_url.render_as_string(hide_password=False))
    create_chat_completion_attempt(repo, request_id="req-a", backend_task_id="task-a", thread_id=thread_a, turn_id="turn-a")
    create_chat_completion_attempt(repo, request_id="req-b", backend_task_id="task-b", thread_id=thread_b, turn_id="turn-b")
    fresh_repo = PgDB(test_url.render_as_string(hide_password=False))
    attempt_a = get_chat_completion_attempt_by_task_id(fresh_repo, "task-a")
    attempt_b = get_chat_completion_attempt_by_task_id(fresh_repo, "task-b")
    assert attempt_a["request_id"] == "req-a"
    assert attempt_a["thread_id"] == thread_a
    assert attempt_a["accepted_at"] is None
    assert attempt_b["thread_id"] == thread_b
    assert get_chat_completion_attempt_by_task_id(fresh_repo, "missing") is None
    mark_chat_completion_attempt_accepted(fresh_repo, backend_task_id="task-a")
    assert get_chat_completion_attempt_by_task_id(repo, "task-a")["accepted_at"] is not None
    assert get_chat_completion_attempt_by_task_id(repo, "task-b")["accepted_at"] is None
    assert record_chat_completion_attempt_terminal_event(
        repo,
        request_id="req-a",
        backend_task_id="task-a",
        thread_id=thread_a,
        turn_id="turn-a",
        event_type="task.failed",
    )
    assert record_chat_completion_attempt_terminal_event(
        fresh_repo,
        request_id="req-a",
        backend_task_id="task-a",
        thread_id=thread_a,
        turn_id="turn-a",
        event_type="task.failed",
    )
    assert not record_chat_completion_attempt_terminal_event(
        repo,
        request_id="req-a",
        backend_task_id="task-a",
        thread_id=thread_a,
        turn_id="turn-a",
        event_type="task.cancelled",
    )
    assert record_chat_completion_attempt_terminal_event(
        fresh_repo,
        request_id="req-b",
        backend_task_id="task-b",
        thread_id=thread_b,
        turn_id="turn-b",
        event_type="task.cancelled",
    )
    assert get_chat_completion_attempt_by_task_id(repo, "task-a")[
        "terminal_event_type"
    ] == "task.failed"
    assert get_chat_completion_attempt_by_task_id(fresh_repo, "task-b")[
        "terminal_event_type"
    ] == "task.cancelled"
    with pytest.raises(ValueError, match="already has a failure or cancellation"):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=thread_a,
            content="must not complete a failed attempt",
            request_id="req-a",
            backend_task_id="task-a",
            turn_id="turn-a",
        )
    engine.dispose()


@pytest.mark.integration
def test_assistant_and_attempt_success_link_commit_atomically(disposable_database):
    psycopg = pytest.importorskip("psycopg")
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('atomic-account', 'atomic-account', 'inert-test-hash', 'guest')"
            )
        )
        thread_id = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('atomic-account', 'Atomic completion') RETURNING id"
            )
        ).scalar_one()

    repo = PgDB(test_url.render_as_string(hide_password=False))
    create_chat_completion_attempt(
        repo,
        request_id="atomic-request",
        backend_task_id="atomic-task",
        thread_id=thread_id,
        turn_id="atomic-turn",
    )
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """CREATE FUNCTION reject_completion_link() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    IF NEW.completed_message_id IS NOT NULL THEN
                        RAISE EXCEPTION 'injected link failure';
                    END IF;
                    RETURN NEW;
                END; $$"""
            )
        )
        connection.execute(
            sa.text(
                "CREATE TRIGGER reject_completion_link BEFORE UPDATE "
                "ON chat_completion_attempts FOR EACH ROW "
                "EXECUTE FUNCTION reject_completion_link()"
            )
        )

    with pytest.raises(psycopg.errors.RaiseException, match="injected link failure"):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=thread_id,
            content="must roll back",
            request_id="atomic-request",
            backend_task_id="atomic-task",
            turn_id="atomic-turn",
        )

    with engine.begin() as connection:
        connection.execute(sa.text("DROP TRIGGER reject_completion_link ON chat_completion_attempts"))
        connection.execute(sa.text("DROP FUNCTION reject_completion_link()"))
    with engine.connect() as connection:
        assert connection.execute(
            sa.text(
                "SELECT count(*) FROM chat_messages "
                "WHERE thread_id = :thread_id AND content = 'must roll back'"
            ),
            {"thread_id": thread_id},
        ).scalar_one() == 0
        assert connection.execute(
            sa.text(
                "SELECT completed_message_id FROM chat_completion_attempts "
                "WHERE backend_task_id = 'atomic-task'"
            )
        ).scalar_one() is None

    message_id, linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=thread_id,
        content="committed together",
        request_id="atomic-request",
        backend_task_id="atomic-task",
        turn_id="atomic-turn",
    )
    assert linked is True
    repeated_message_id, repeated_linked = (
        repo.create_assistant_message_for_completion_attempt(
            thread_id=thread_id,
            content="must not create another assistant",
            request_id="atomic-request",
            backend_task_id="atomic-task",
            turn_id="atomic-turn",
        )
    )
    assert repeated_linked is True
    assert repeated_message_id == message_id
    with engine.connect() as connection:
        message = connection.execute(
            sa.text(
                "SELECT thread_id, role, content FROM chat_messages WHERE id = :message_id"
            ),
            {"message_id": message_id},
        ).one()
        linked_message_id = connection.execute(
            sa.text(
                "SELECT completed_message_id FROM chat_completion_attempts "
                "WHERE backend_task_id = 'atomic-task'"
            )
        ).scalar_one()
    assert tuple(message) == (thread_id, "assistant", "committed together")
    assert linked_message_id == message_id
    with engine.connect() as connection:
        assert connection.execute(
            sa.text(
                "SELECT count(*) FROM chat_messages "
                "WHERE thread_id = :thread_id AND role = 'assistant'"
            ),
            {"thread_id": thread_id},
        ).scalar_one() == 1
    engine.dispose()


@pytest.mark.integration
def test_original_recovery_snapshot_survives_upgrade_and_is_immutable(disposable_database):
    from datetime import datetime, timezone

    from sqlalchemy.exc import IntegrityError
    from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

    config, test_url = disposable_database
    command.upgrade(config, "d4c69e03a712")
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('snapshot-account', 'snapshot-account', 'inert-test-hash', 'guest')"
        ))
        thread = connection.execute(sa.text(
            "INSERT INTO chat_threads (user_id, title) "
            "VALUES ('snapshot-account', 'Snapshot') RETURNING id"
        )).scalar_one()
        connection.execute(sa.text(
            "INSERT INTO chat_completion_attempts "
            "(request_id, backend_task_id, thread_id, turn_id, accepted_at) "
            "VALUES ('legacy-request', 'legacy-task', :thread, 'legacy-turn', "
            "'2026-10-03T10:17:59+00:00')"
        ), {"thread": thread})
    command.upgrade(config, "head")
    with engine.connect() as connection:
        legacy = connection.execute(sa.text(
            "SELECT deadline_snapshot, turn_lock_token, accepted_at "
            "FROM chat_completion_attempts WHERE request_id='legacy-request'"
        )).one()
        assert legacy[0] is None and legacy[1] is None
        assert legacy[2] == datetime(2026, 10, 3, 10, 17, 59, tzinfo=timezone.utc)

    deadline = build_accepted_chat_task_deadline(
        datetime(2026, 10, 4, 10, 0, 0, 123456, tzinfo=timezone.utc)
    )
    repo = PgDB(test_url.render_as_string(hide_password=False))
    create_chat_completion_attempt(
        repo, request_id="snapshot-request", backend_task_id="snapshot-task",
        thread_id=thread, turn_id="snapshot-turn", deadline_snapshot=deadline,
        turn_lock_token="existing-lock-token",
    )
    # Later queue acknowledgement remains separate and cannot refresh the envelope.
    mark_chat_completion_attempt_accepted(repo, backend_task_id="snapshot-task")
    with engine.connect() as connection:
        snapshot = connection.execute(sa.text(
            "SELECT deadline_snapshot, turn_lock_token, accepted_at "
            "FROM chat_completion_attempts WHERE request_id='snapshot-request'"
        )).one()
        assert snapshot[0] == deadline.to_dict()
        assert snapshot[1] == "existing-lock-token"
        assert snapshot[2] != deadline.accepted_at
    assert "turn_lock_token" not in get_chat_completion_attempt_by_task_id(repo, "snapshot-task")
    # The database itself rejects refreshed envelopes, token replacement and legacy backfill.
    changes = (
        "deadline_snapshot = jsonb_set(deadline_snapshot, '{accepted_at}', '\"2030-01-01T00:00:00+00:00\"')",
        "turn_lock_token = 'replacement-token'",
        "deadline_snapshot = NULL, turn_lock_token = NULL",
    )
    for assignment in changes:
        with pytest.raises(IntegrityError, match="immutable"):
            with engine.begin() as connection:
                connection.execute(sa.text(
                    "UPDATE chat_completion_attempts SET " + assignment
                    + " WHERE request_id='snapshot-request'"
                ))
    with pytest.raises(IntegrityError, match="immutable"):
        with engine.begin() as connection:
            connection.execute(sa.text(
                "UPDATE chat_completion_attempts SET deadline_snapshot = "
                "(SELECT deadline_snapshot FROM chat_completion_attempts WHERE request_id='snapshot-request'), "
                "turn_lock_token='invented-token' WHERE request_id='legacy-request'"
            ))
    with pytest.raises(ValueError, match="original accepted deadline"):
        create_chat_completion_attempt(
            repo, request_id="invalid-request", backend_task_id="invalid-task",
            thread_id=thread, turn_id="invalid-turn", deadline_snapshot={},
            turn_lock_token="token",
        )
    with pytest.raises(ValueError, match="turn lock token"):
        create_chat_completion_attempt(
            repo, request_id="missing-token-request", backend_task_id="missing-token-task",
            thread_id=thread, turn_id="missing-token-turn", deadline_snapshot=deadline,
        )
    # Failure/cancellation updates remain valid; they preserve the original snapshot.
    assert record_chat_completion_attempt_terminal_event(
        repo, request_id="snapshot-request", backend_task_id="snapshot-task",
        thread_id=thread, turn_id="snapshot-turn", event_type="task.failed",
    )
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT deadline_snapshot FROM chat_completion_attempts WHERE request_id='snapshot-request'"
        )).scalar_one() == deadline.to_dict()
        assert connection.execute(sa.text(
            "SELECT count(*) FROM chat_completion_attempts"
        )).scalar_one() == 2
    # Downgrade preserves preexisting attempt data; no historical values were backfilled.
    command.downgrade(config, "d4c69e03a712")
    assert "deadline_snapshot" not in {
        c["name"] for c in sa.inspect(engine).get_columns("chat_completion_attempts")
    }
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM chat_completion_attempts")).scalar_one() == 2
    engine.dispose()


@pytest.fixture
def recovery_database(disposable_database):
    from datetime import datetime, timezone
    from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('recovery-account', 'recovery-account', 'inert-test-hash', 'guest')"
        ))
        thread_id = connection.execute(sa.text(
            "INSERT INTO chat_threads (user_id, title) "
            "VALUES ('recovery-account', 'Recovery proof') RETURNING id"
        )).scalar_one()
    repo = PgDB(test_url.render_as_string(hide_password=False))
    deadline = build_accepted_chat_task_deadline(datetime(2026, 10, 1, tzinfo=timezone.utc))

    def create(name, *, legacy=False, accepted=True):
        identity = dict(request_id=f"request-{name}", backend_task_id=f"task-{name}",
                        thread_id=thread_id, turn_id=f"turn-{name}")
        create_chat_completion_attempt(
            repo, **identity, deadline_snapshot=None if legacy else deadline,
            turn_lock_token=None if legacy else f"lock-{name}",
        )
        if accepted:
            mark_chat_completion_attempt_accepted(repo, backend_task_id=identity["backend_task_id"])
        return identity

    try:
        yield config, engine, repo, deadline, create
    finally:
        engine.dispose()


@pytest.mark.integration
def test_post_terminal_orphan_arbitration_and_database_fence(recovery_database):
    from datetime import timedelta
    from guardian.core.db import record_chat_completion_attempt_success
    from guardian.protocol_tokens import ErrorCode

    config, engine, repo, deadline, create = recovery_database
    identity = create("orphan")
    before = reconcile_chat_completion_attempt_after_deadline(
        repo, **identity, now=deadline.terminal_deadline_at - timedelta(microseconds=1)
    )
    assert before.terminal_event_type is None and before.turn_lock_token is None
    result = reconcile_chat_completion_attempt_after_deadline(
        repo, **identity, now=deadline.terminal_deadline_at
    )
    assert result.completed_message_id is None
    assert result.terminal_event_type == "task.failed"
    assert result.terminal_outcome == {
        "failure_code": ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value,
        "reconciled_at": deadline.terminal_deadline_at.isoformat(),
    }
    assert result.turn_lock_token == "lock-orphan"
    assert reconcile_chat_completion_attempt_after_deadline(
        repo, **identity, now=deadline.terminal_deadline_at + timedelta(days=1)
    ) == result
    fresh_repo = PgDB(repo.dsn)
    public = get_chat_completion_attempt_by_task_id(fresh_repo, identity["backend_task_id"])
    assert public["terminal_outcome"] == result.terminal_outcome
    assert "turn_lock_token" not in public
    assert public["accepted_at"] != deadline.accepted_at
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT deadline_snapshot FROM chat_completion_attempts WHERE request_id=:id"
        ), {"id": identity["request_id"]}).scalar_one() == deadline.to_dict()
    with pytest.raises(ValueError, match="already has a failure or cancellation"):
        fresh_repo.create_assistant_message_for_completion_attempt(
            **identity, content="late assistant must not exist"
        )
    # Same failed kind is not permission for a late worker to publish its own reason.
    assert not record_chat_completion_attempt_terminal_event(
        repo, **identity, event_type="task.failed"
    )
    assert not record_chat_completion_attempt_terminal_event(
        repo, **identity, event_type="task.cancelled"
    )
    assert not record_chat_completion_attempt_success(repo, **identity, assistant_message_id=999999)
    for assignment in (
        "terminal_outcome=NULL", "terminal_event_type=NULL",
        "terminal_event_type='task.cancelled'", "completed_message_id=999999",
        "terminal_outcome=jsonb_set(terminal_outcome, '{reconciled_at}', '\"2027-01-01T00:00:00+00:00\"')",
    ):
        with pytest.raises(sa.exc.IntegrityError, match="Chat orphan outcome is immutable"):
            with engine.begin() as connection:
                connection.execute(sa.text(
                    f"UPDATE chat_completion_attempts SET {assignment} WHERE request_id=:id"
                ), {"id": identity["request_id"]})
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT count(*) FROM chat_messages WHERE thread_id=:thread"
        ), {"thread": identity["thread_id"]}).scalar_one() == 0
    command.downgrade(config, "e8a9b03d6712")
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT terminal_event_type FROM chat_completion_attempts WHERE request_id=:id"
        ), {"id": identity["request_id"]}).scalar_one() == "task.failed"


@pytest.mark.integration
def test_reconciliation_respects_truth_identity_and_unknown_admission(recovery_database):
    from datetime import timedelta

    _config, engine, repo, deadline, create = recovery_database
    completed = create("completed")
    message_id, bound = repo.create_assistant_message_for_completion_attempt(
        **completed, content="durable completion wins"
    )
    assert bound
    result = reconcile_chat_completion_attempt_after_deadline(
        repo, **completed, now=deadline.terminal_deadline_at + timedelta(days=1)
    )
    assert result.completed_message_id == message_id
    assert result.terminal_event_type is None and result.terminal_outcome is None
    for kind in ("task.failed", "task.cancelled"):
        identity = create(kind)
        assert record_chat_completion_attempt_terminal_event(repo, **identity, event_type=kind)
        result = reconcile_chat_completion_attempt_after_deadline(
            repo, **identity, now=deadline.accepted_at
        )
        assert result.terminal_event_type == kind and result.terminal_outcome is None
    for identity in (create("legacy", legacy=True), create("unconfirmed", accepted=False)):
        result = reconcile_chat_completion_attempt_after_deadline(
            repo, **identity, now=deadline.terminal_deadline_at + timedelta(days=1)
        )
        assert result.completed_message_id is None and result.terminal_event_type is None
        assert result.turn_lock_token is None
    # Native constraints reject early orphan outcomes even through direct SQL.
    early = create("early")
    with pytest.raises(sa.exc.IntegrityError, match="ck_chat_attempt_orphan_outcome"):
        with engine.begin() as connection:
            connection.execute(sa.text(
                "UPDATE chat_completion_attempts SET terminal_event_type='task.failed', "
                "terminal_outcome=jsonb_build_object('failure_code','CHAT_ACCEPTED_TASK_ORPHANED', "
                "'reconciled_at',CAST(:at AS text)) WHERE backend_task_id=:task"
            ), {"at": deadline.work_deadline_at.isoformat(), "task": early["backend_task_id"]})
    assert get_chat_completion_attempt_by_task_id(repo, early["backend_task_id"])["terminal_event_type"] is None
    untouched = create("identity")
    for key, value in (("request_id", "wrong"), ("backend_task_id", "missing"),
                       ("thread_id", untouched["thread_id"]+1), ("turn_id", "wrong")):
        with pytest.raises(ValueError, match="identity does not match"):
            reconcile_chat_completion_attempt_after_deadline(
                repo, **(untouched | {key: value}), now=deadline.terminal_deadline_at
            )
    with pytest.raises(ValueError, match="aware server timestamp"):
        reconcile_chat_completion_attempt_after_deadline(
            repo, **untouched, now=deadline.terminal_deadline_at.replace(tzinfo=None)
        )
    # An invalid imported snapshot must not be reconstructed from accepted_at.
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO chat_completion_attempts "
            "(request_id, backend_task_id, thread_id, turn_id, accepted_at, deadline_snapshot, turn_lock_token) "
            "VALUES ('bad-request','bad-task',:thread,'bad-turn',now(), "
            "jsonb_build_object('accepted_at','invalid'), 'bad-token')"
        ), {"thread": untouched["thread_id"]})
    with pytest.raises(ValueError, match="snapshot is incomplete"):
        reconcile_chat_completion_attempt_after_deadline(
            repo, request_id="bad-request", backend_task_id="bad-task",
            thread_id=untouched["thread_id"], turn_id="bad-turn", now=deadline.terminal_deadline_at
        )
    for task_id in ("task-identity", "bad-task"):
        assert get_chat_completion_attempt_by_task_id(repo, task_id)["terminal_event_type"] is None
    # A later direct write cannot recast an already persisted cancellation as orphaned.
    with pytest.raises(sa.exc.IntegrityError, match="terminal truth precedes"):
        with engine.begin() as connection:
            connection.execute(sa.text(
                "UPDATE chat_completion_attempts SET terminal_event_type='task.failed', "
                "terminal_outcome=jsonb_build_object('failure_code','CHAT_ACCEPTED_TASK_ORPHANED', "
                "'reconciled_at',CAST(:at AS text)) WHERE backend_task_id='task-task.cancelled'"
            ), {"at": deadline.terminal_deadline_at.isoformat()})


@pytest.mark.integration
def test_orphan_persistence_failure_cannot_report_recovery(recovery_database):
    _config, engine, repo, deadline, create = recovery_database
    identity = create("rollback")
    with engine.begin() as connection:
        connection.execute(sa.text("""CREATE FUNCTION reject_orphan() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                IF NEW.terminal_outcome IS NOT NULL THEN RAISE EXCEPTION 'injected orphan failure'; END IF;
                RETURN NEW;
            END; $$"""))
        connection.execute(sa.text(
            "CREATE TRIGGER reject_orphan BEFORE UPDATE ON chat_completion_attempts "
            "FOR EACH ROW EXECUTE FUNCTION reject_orphan()"
        ))
    with pytest.raises(sa.exc.DBAPIError, match="injected orphan failure"):
        reconcile_chat_completion_attempt_after_deadline(repo, **identity, now=deadline.terminal_deadline_at)
    row = get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
    assert row["terminal_event_type"] is None and row["terminal_outcome"] is None
    with engine.begin() as connection:
        connection.execute(sa.text("DROP TRIGGER reject_orphan ON chat_completion_attempts"))
        connection.execute(sa.text("DROP FUNCTION reject_orphan()"))
    assert reconcile_chat_completion_attempt_after_deadline(
        repo, **identity, now=deadline.terminal_deadline_at
    ).terminal_event_type == "task.failed"


@pytest.mark.integration
@pytest.mark.parametrize("winner", ["assistant", "reconciler"])
def test_assistant_and_orphan_serialize_on_the_same_attempt(recovery_database, monkeypatch, winner):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    from threading import Event

    _config, engine, repo, deadline, create = recovery_database
    identity = create(f"race-{winner}")
    rival_repo = PgDB(repo.dsn)
    locked, release, rival_started = Event(), Event(), Event()
    if winner == "assistant":
        original = repo.create_message

        def pause_assistant(*args, **kwargs):
            locked.set()
            assert release.wait(10)
            return original(*args, **kwargs)

        monkeypatch.setattr(repo, "create_message", pause_assistant)
        def first():
            return repo.create_assistant_message_for_completion_attempt(**identity, content="winner")

        def rival():
            rival_started.set()
            return reconcile_chat_completion_attempt_after_deadline(
                rival_repo, **identity, now=deadline.terminal_deadline_at
            )
    else:
        original_session = repo._sa_session

        @contextmanager
        def pause_reconciliation_commit():
            with original_session() as session:
                yield session
                session.flush()
                locked.set()
                assert release.wait(10)

        monkeypatch.setattr(repo, "_sa_session", pause_reconciliation_commit)
        def first():
            return reconcile_chat_completion_attempt_after_deadline(
                repo, **identity, now=deadline.terminal_deadline_at
            )

        def rival():
            rival_started.set()
            return rival_repo.create_assistant_message_for_completion_attempt(**identity, content="must roll back")

    with ThreadPoolExecutor(max_workers=2) as pool:
        leading = pool.submit(first)
        try:
            assert locked.wait(10)
            trailing = pool.submit(rival)
            assert rival_started.wait(10)
            assert not trailing.done()
        finally:
            release.set()
        first_result = leading.result(timeout=10)
        if winner == "assistant":
            second_result = trailing.result(timeout=10)
            assert second_result.completed_message_id == first_result[0]
            assert second_result.terminal_event_type is None
        else:
            assert first_result.terminal_event_type == "task.failed"
            with pytest.raises(ValueError, match="failure or cancellation"):
                trailing.result(timeout=10)
    with engine.connect() as connection:
        assistants = connection.execute(sa.text(
            "SELECT count(*) FROM chat_messages WHERE thread_id=:thread AND role='assistant'"
        ), {"thread": identity["thread_id"]}).scalar_one()
    assert assistants == (1 if winner == "assistant" else 0)
