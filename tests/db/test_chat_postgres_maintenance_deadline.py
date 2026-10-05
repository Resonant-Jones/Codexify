"""Recovery bounds grant no accepted work and close physical PostgreSQL waits."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import time

import psycopg
import pytest
from sqlalchemy import text

from guardian.core import chat_postgres_deadline as bounds
from guardian.core.db import (
    create_chat_completion_attempt,
    get_chat_completion_attempt_by_task_id,
    mark_chat_completion_attempt_accepted,
    reconcile_chat_completion_attempt_after_deadline,
)
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from tests.db.test_chat_postgres_connect_deadline import stalled_peer
from tests.db.test_chat_postgres_deadline import (
    database as _database_fixture,
    disposable_database as _disposable_database_fixture,
)

database = _database_fixture
disposable_database = _disposable_database_fixture


def test_maintenance_is_fixed_and_grants_no_task_authority():
    snapshot = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    original = snapshot.to_dict()
    with bounds.postgres_operation_scope(.25):
        budget = bounds._budget.get()
        assert budget.operation and budget.work_end == budget.terminal_end
        first = budget.remaining()
        time.sleep(.01)
        assert budget.remaining() < first
        for operation in (bounds.require_accepted_work_budget,
                          bounds.accepted_child_deadline_bounds,
                          bounds.use_postgres_terminal_budget):
            with pytest.raises(ValueError, match="Maintenance cannot authorize"):
                operation()
        assert bounds._budget.get() is budget
        with pytest.raises(ValueError, match="cannot replace"):
            with bounds.postgres_operation_scope(1):
                pytest.fail("Nested maintenance admitted")
        for deadline in (None, snapshot):
            with pytest.raises(ValueError, match="cannot replace"):
                with bounds.accepted_postgres_query_scope(deadline):
                    pytest.fail("Accepted scope replaced maintenance")
    assert bounds._budget.get() is None and snapshot.to_dict() == original
    with bounds.accepted_postgres_query_scope(snapshot):
        inherited = bounds._budget.get()
        with pytest.raises(ValueError, match="cannot replace"):
            with bounds.postgres_operation_scope(.25):
                pytest.fail("Maintenance replaced accepted work")
        assert bounds._budget.get() is inherited
    assert bounds._budget.get() is None


@pytest.mark.parametrize("seconds", [0, -1, float("nan"), float("inf")])
def test_maintenance_rejects_invalid_limits(seconds):
    with pytest.raises(ValueError, match="finite and positive"):
        with bounds.postgres_operation_scope(seconds):
            pytest.fail("Unbounded maintenance admitted")
    assert bounds._budget.get() is None


def test_real_maintenance_handshake_timeout_closes_peer_before_release():
    with stalled_peer() as (peer, started, ended):
        dsn = f"host=127.0.0.1 port={peer['port']} dbname=owned user=owned sslmode=disable"
        begin = time.monotonic()
        with pytest.raises(bounds.PostgresOperationTimeout):
            with bounds.postgres_operation_scope(.25):
                bounds.connect_with_query_bounds(dsn)
        duration = time.monotonic() - begin
        assert .20 < duration < .65
        assert started.is_set() and peer["startup_bytes"] > 0
        assert ended.wait(.25) and peer["eof"]
    assert bounds._budget.get() is None
    print({"surface": "maintenance_handshake", "duration_seconds": duration, "peer_eof": True})


@pytest.mark.integration
def test_real_reconciliation_row_lock_is_bounded_without_sliding_original_deadline(database):
    repo, observer, thread, label, plain = database
    original = build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(days=1)
    )
    identity = dict(request_id="recovery-request", backend_task_id="recovery-task",
                    thread_id=thread, turn_id="recovery-turn")
    create_chat_completion_attempt(repo, **identity, deadline_snapshot=original, turn_lock_token="original-token")
    mark_chat_completion_attempt_accepted(repo, backend_task_id="recovery-task")
    with psycopg.connect(plain) as locker:
        locker.execute("SELECT request_id FROM chat_completion_attempts WHERE backend_task_id='recovery-task' FOR UPDATE")

        def maintenance():
            with pytest.raises(bounds.PostgresOperationTimeout):
                with bounds.postgres_operation_scope(.5):
                    reconcile_chat_completion_attempt_after_deadline(repo, **identity)
            assert bounds._budget.get() is None

        begin = time.monotonic()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(maintenance)
            wait = None
            while time.monotonic() - begin < .35:
                wait = observer.execute(
                    "SELECT pid FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                    (label,),
                ).fetchone()
                if wait:
                    break
                assert not future.done(), "No physical lock wait was observed"
                time.sleep(.005)
            assert wait is not None
            future.result(timeout=1)
            duration = time.monotonic() - begin
            assert duration < .75
            until = time.monotonic() + .2
            while observer.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE application_name=%s AND state='active'", (label,)
            ).fetchone()[0]:
                assert time.monotonic() < until
                time.sleep(.005)
            # Observation/failure cannot claim a durable orphan after timeout.
            row = get_chat_completion_attempt_by_task_id(repo, "recovery-task")
            assert row["terminal_event_type"] is None and row["terminal_outcome"] is None
            locker.rollback()
    with bounds.postgres_operation_scope(1):
        result = reconcile_chat_completion_attempt_after_deadline(repo, **identity)
    assert result.terminal_outcome["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
    assert result.turn_lock_token == "original-token"
    with repo._sa_session() as session:
        persisted = session.execute(text(
            "SELECT deadline_snapshot FROM chat_completion_attempts WHERE backend_task_id='recovery-task'"
        )).scalar_one()
        assert persisted == original.to_dict()
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"
    print({"surface": "maintenance_reconcile_row_lock", "duration_seconds": duration,
           "wait_ended_before_unlock": True, "original_deadline_preserved": True})


@pytest.mark.integration
@pytest.mark.parametrize("surface", ["raw", "orm"])
def test_real_maintenance_query_closes_and_legacy_limits_restore(database, surface):
    repo, observer, _thread, label, _plain = database
    begin = time.monotonic()
    with pytest.raises(bounds.PostgresOperationTimeout):
        with bounds.postgres_operation_scope(.25):
            if surface == "raw":
                with repo._connect() as connection:
                    connection.execute("SELECT pg_sleep(1)")
            else:
                with repo._sa_session() as session:
                    session.execute(text("SELECT pg_sleep(1)"))
    duration = time.monotonic() - begin
    assert .20 < duration < .65 and bounds._budget.get() is None
    until = time.monotonic() + .2
    while observer.execute(
        "SELECT count(*) FROM pg_stat_activity WHERE application_name=%s AND state='active'", (label,)
    ).fetchone()[0]:
        assert time.monotonic() < until
        time.sleep(.005)
    with repo._sa_session() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"
    print({"surface": f"maintenance_{surface}_query", "duration_seconds": duration,
           "server_quiescent": True, "legacy_limits_restored": True})


@pytest.mark.integration
def test_real_maintenance_full_pool_cannot_admit_after_expiry(database):
    repo, _observer, _thread, _label, _plain = database
    pool = repo._sa_engine.pool
    held = []
    try:
        for _ in range(15):
            held.append(repo._sa_engine.connect())
        begin = time.monotonic()
        with pytest.raises(bounds.PostgresOperationTimeout):
            with bounds.postgres_operation_scope(.25):
                with repo._sa_engine.connect():
                    pytest.fail("Expired maintenance borrower admitted")
        duration = time.monotonic() - begin
        assert .20 < duration < .65
        assert pool.checkedout() == 15 and pool._timeout == 30
        assert bounds._budget.get() is None
        held.pop().close()
        with repo._sa_engine.connect() as connection:
            assert connection.execute(text("SHOW statement_timeout")).scalar_one() == "0"
        print({"surface": "maintenance_full_pool", "duration_seconds": duration,
               "pool_policy_preserved": True})
    finally:
        for connection in held:
            connection.close()


@pytest.mark.parametrize("surface", ["raw", "orm"])
def test_maintenance_held_dns_reaps_the_owned_resolver(monkeypatch, tmp_path, surface):
    from guardian.core.pgdb import PgDB
    from tests.db.test_chat_postgres_dns_deadline import (
        assert_owned_resolver_reaped,
        held_resolver,
    )

    for name in ("PGHOST", "PGHOSTADDR", "PGPORT", "PGSERVICE"):
        monkeypatch.delenv(name, raising=False)
    record, children = held_resolver(monkeypatch, tmp_path)
    repo = PgDB("postgresql://inert:inert@held-dns.invalid:5432/inert?sslmode=disable")
    begin = time.monotonic()
    try:
        with pytest.raises(bounds.PostgresOperationTimeout):
            with bounds.postgres_operation_scope(.5):
                if surface == "raw":
                    repo._connect()
                else:
                    with repo._sa_session() as session:
                        session.connection()
        duration = time.monotonic() - begin
        assert .45 < duration < .9
        assert_owned_resolver_reaped(record, children)
        assert bounds._budget.get() is None
        print({"surface": f"maintenance_{surface}_dns", "duration_seconds": duration,
               "owned_resolver_reaped": True})
    finally:
        repo._sa_engine.dispose()
