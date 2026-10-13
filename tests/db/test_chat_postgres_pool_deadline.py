"""Accepted pool waits cannot borrow a connection after their parent expires."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import threading
import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.util import queue as pool_queue

from guardian.core import chat_postgres_deadline as bounds
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from tests.db.test_chat_postgres_deadline import (
    database as _database_fixture,
    disposable_database as _disposable_database_fixture,
)

database = _database_fixture
disposable_database = _disposable_database_fixture


def snapshot(seconds=0.25):
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=780 - seconds)
    )


@pytest.mark.integration
def test_full_pool_deadline_does_not_extend_or_change_legacy_borrower(database):
    repo, observer, _thread, label, _plain = database
    engine = repo._sa_engine
    pool = engine.pool
    assert pool.size() == 5 and pool._max_overflow == 10 and pool._timeout == 30
    held = []
    entered = threading.Event()
    legacy_entered = threading.Event()

    def bounded():
        deadline = snapshot()
        start = time.monotonic()
        with bounds.accepted_postgres_query_scope(deadline):
            entered.set()
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                with engine.connect():
                    pytest.fail("Expired borrower was admitted")
        assert datetime.now(timezone.utc) >= deadline.terminal_deadline_at
        return time.monotonic() - start

    def legacy():
        legacy_entered.set()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.execute(text("SHOW statement_timeout")).scalar_one() == "0"
        return True

    try:
        for _ in range(15):
            held.append(engine.connect())
        assert observer.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE application_name=%s",
            (label,),
        ).fetchone()[0] == 15
        with ThreadPoolExecutor(max_workers=2) as executor:
            bounded_future = executor.submit(bounded)
            legacy_future = executor.submit(legacy)
            try:
                assert entered.wait(1) and legacy_entered.wait(1)
                duration = bounded_future.result(timeout=1)
                assert 0.20 < duration < 0.55
                assert pool.checkedout() == 15
                assert pool._timeout == 30
                assert not legacy_future.done()
            finally:
                held.pop().close()
            assert legacy_future.result(timeout=1)
        with bounds.accepted_postgres_query_scope(snapshot(1)):
            with engine.connect() as connection:
                assert connection.execute(text("SELECT 1")).scalar_one() == 1
        print({"surface": "full_pool", "duration_seconds": duration,
               "held_until_deadline_exit": True, "legacy_independent": True})
    finally:
        for connection in held:
            connection.close()


@pytest.mark.integration
def test_stricter_pool_timeout_keeps_ordinary_policy_disposition(database):
    repo, _observer, _thread, _label, _plain = database
    pool = repo._sa_engine.pool
    held = []
    original_timeout = pool._timeout
    try:
        for _ in range(15):
            held.append(repo._sa_engine.connect())
        pool._timeout = 0.04
        deadline = snapshot(0.75)
        start = time.monotonic()
        with bounds.accepted_postgres_query_scope(deadline):
            with pytest.raises(PoolTimeout):
                repo._sa_engine.connect()
        duration = time.monotonic() - start
        assert 0.03 < duration < 0.30
        assert datetime.now(timezone.utc) < deadline.terminal_deadline_at
        assert pool.checkedout() == 15
        print({"surface": "stricter_pool_policy", "duration_seconds": duration})
    finally:
        pool._timeout = original_timeout
        for connection in held:
            connection.close()


def test_late_queue_entry_is_restored_without_admission(monkeypatch):
    real_get = pool_queue.Queue.get
    clock = [time.monotonic()]
    item = object()
    queue = bounds.AcceptedDeadlineQueue(maxsize=1)
    queue.put(item)
    deadline = snapshot()

    def late_get(self, *args, **kwargs):
        entry = real_get(self, *args, **kwargs)
        clock[0] += 1
        return entry

    monkeypatch.setattr(bounds.time, "monotonic", lambda: clock[0])
    with bounds.accepted_postgres_query_scope(deadline):
        monkeypatch.setattr(pool_queue.Queue, "get", late_get)
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            queue.get()
    monkeypatch.setattr(pool_queue.Queue, "get", real_get)
    assert queue.get(block=False) is item
    assert queue.empty()


def test_queue_mutex_wait_is_inside_parent_budget():
    queue = bounds.AcceptedDeadlineQueue(maxsize=1)
    entered = threading.Event()

    def bounded():
        with bounds.accepted_postgres_query_scope(snapshot()):
            entered.set()
            start = time.monotonic()
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                queue.get()
            return time.monotonic() - start

    queue.mutex.acquire()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(bounded)
            assert entered.wait(1)
            assert 0.20 < future.result(timeout=1) < 0.55
    finally:
        queue.mutex.release()
