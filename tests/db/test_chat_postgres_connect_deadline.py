"""Real TCP handshake stalls are clipped before query execution begins."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import gc
import os
import socket
import threading
import time

import psycopg
import pytest
from sqlalchemy import text

from guardian.core import chat_postgres_deadline as bounds
from guardian.core.pgdb import PgDB
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


def snapshot(seconds=0.25, *, phase="terminal"):
    age = 780 if phase == "terminal" else 720
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=age - seconds)
    )


@contextmanager
def stalled_peer():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(5)
    state = {"port": listener.getsockname()[1], "startup_bytes": 0}
    started = threading.Event()
    ended = threading.Event()
    stop = threading.Event()

    def peer():
        client = None
        try:
            client, _ = listener.accept()
            client.settimeout(0.05)
            while not stop.is_set():
                try:
                    data = client.recv(8192)
                except socket.timeout:
                    continue
                if not data:
                    state["eof"] = True
                    ended.set()
                    return
                state["startup_bytes"] += len(data)
                started.set()
        except OSError:
            if not stop.is_set():
                state["error"] = True
        finally:
            if client is not None:
                client.close()

    thread = threading.Thread(target=peer)
    thread.start()
    try:
        yield state, started, ended
    finally:
        stop.set()
        listener.close()
        thread.join(timeout=6)
        assert not thread.is_alive()


@pytest.mark.parametrize("surface", ["raw", "orm"])
@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_real_handshake_expires_and_closes_socket_before_peer_release(surface, phase):
    with stalled_peer() as (peer, started, ended):
        repo = PgDB(
            f"postgresql://inert:inert@127.0.0.1:{peer['port']}/inert"
            "?sslmode=disable&connect_timeout=1"
        )
        deadline = snapshot(phase=phase)
        start = time.monotonic()
        try:
            with bounds.accepted_postgres_query_scope(deadline):
                with pytest.raises(AcceptedChatTaskDeadlineExceeded) as failure:
                    if surface == "raw":
                        repo._connect()
                    else:
                        with repo._sa_session() as session:
                            session.connection()
            duration = time.monotonic() - start
            assert 0.20 < duration < 0.60
            assert failure.value.detail["failure_code"] == "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED"
            assert started.is_set() and peer["startup_bytes"] > 0
            assert ended.wait(0.25) and peer.get("eof")
            assert "error" not in peer
            print({"surface": surface, "phase": phase, "duration_seconds": duration,
                   "startup_bytes": peer["startup_bytes"], "peer_eof_before_release": True})
        finally:
            repo._sa_engine.dispose()


def test_host_attempts_share_original_deadline():
    with stalled_peer() as (first, first_started, first_ended):
        with stalled_peer() as (second, second_started, second_ended):
            deadline = snapshot(2.4)
            dsn = (
                "host=127.0.0.1,127.0.0.1 "
                f"port={first['port']},{second['port']} "
                "user=inert password=inert dbname=inert sslmode=disable connect_timeout=1"
            )
            start = time.monotonic()
            with bounds.accepted_postgres_query_scope(deadline):
                with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                    bounds.connect_with_query_bounds(dsn)
            duration = time.monotonic() - start
            assert 2.3 < duration < 2.9
            assert first_started.is_set() and second_started.is_set()
            assert first_ended.wait(0.25) and second_ended.wait(0.25)
            assert first.get("eof") and second.get("eof")
            print({"surface": "two_host_attempts", "duration_seconds": duration,
                   "both_peer_eof": True})


@pytest.mark.parametrize("accepted", [False, True])
def test_shorter_connection_policy_keeps_ordinary_disposition(accepted):
    connectors = [bounds.connect_with_query_bounds]
    if not accepted:
        connectors.insert(0, psycopg.Connection.connect)
    observed = []
    for connect in connectors:
        with stalled_peer() as (peer, started, ended):
            deadline = snapshot(5)
            dsn = (
                f"postgresql://inert:inert@127.0.0.1:{peer['port']}/inert"
                "?sslmode=disable&connect_timeout=1"
            )
            start = time.monotonic()
            with bounds.accepted_postgres_query_scope(deadline if accepted else None):
                with pytest.raises(psycopg.errors.ConnectionTimeout) as failure:
                    connect(dsn)
            duration = time.monotonic() - start
            assert 1.8 < duration < 2.7
            assert datetime.now(timezone.utc) < deadline.terminal_deadline_at
            assert started.is_set()
            eof_with_exception = ended.wait(0.25)
            if accepted:
                assert eof_with_exception and peer.get("eof")
            # Driver 3.3's outer timeout retains its suspended generator through
            # the exception traceback. Outside accepted scope, compare directly
            # with that driver behavior, then release it before harness cleanup.
            del failure
            gc.collect()
            assert ended.wait(0.25) and peer.get("eof")
            observed.append(eof_with_exception)
            print({"surface": "shorter_connect_policy", "accepted_scope": accepted,
                   "connector": connect.__qualname__, "duration_seconds": duration,
                   "peer_eof_with_exception": eof_with_exception,
                   "peer_eof_after_exception_release": True})
    if not accepted:
        assert observed[0] == observed[1]


@pytest.mark.integration
def test_healthy_raw_and_new_then_reused_orm_connections(database):
    repo, _observer, _thread, _label, _plain = database
    repo._sa_engine.dispose()  # Exercise actual new native connection creation.
    with bounds.accepted_postgres_query_scope(snapshot(2)):
        with repo._connect() as connection:
            assert connection.execute("SELECT 1 AS value").fetchone()["value"] == 1
        with repo._sa_session() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
        with repo._sa_session() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
    with repo._sa_session() as session:
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"


def test_late_native_connection_return_is_closed(monkeypatch):
    clock = [time.monotonic()]
    closed = []

    class LateConnection:
        def close(self):
            closed.append(True)

    def late_gen(cls, *args, **kwargs):
        clock[0] += 1
        if False:
            yield
        return LateConnection()

    monkeypatch.setattr(bounds.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(psycopg.Connection, "_connect_gen", classmethod(late_gen))
    with bounds.accepted_postgres_query_scope(snapshot()):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            next(bounds.AcceptedDeadlineConnection._connect_gen())
    assert closed == [True]


def test_native_socket_replacement_reusing_descriptor_is_observed(monkeypatch):
    first_reader, first_writer = socket.socketpair()
    second_reader, second_writer = socket.socketpair()
    result = object()

    def replacing_gen(cls, *args, **kwargs):
        fd = first_reader.fileno()
        first_writer.sendall(b"first")
        yield fd, bounds.waiting.WAIT_R
        assert first_reader.recv(16) == b"first"
        # Replace an owned descriptor atomically; its number and wait interest
        # stay unchanged while the selector's underlying socket is different.
        os.dup2(second_reader.fileno(), fd)
        second_writer.sendall(b"second")
        yield fd, bounds.waiting.WAIT_R
        assert first_reader.recv(16) == b"second"
        return result

    monkeypatch.setattr(psycopg.Connection, "_connect_gen", classmethod(replacing_gen))
    try:
        with bounds.accepted_postgres_query_scope(snapshot(1)):
            with pytest.raises(StopIteration) as completed:
                next(bounds.AcceptedDeadlineConnection._connect_gen())
        assert completed.value.value is result
    finally:
        for peer in [first_reader, first_writer, second_reader, second_writer]:
            peer.close()
