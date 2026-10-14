"""Owned resolver processes inherit the accepted PostgreSQL deadline."""

from datetime import datetime, timedelta, timezone
import json
import os
import signal
import time

import psycopg
from psycopg._conninfo_attempts import conninfo_attempts
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
from tests.db.test_chat_postgres_connect_deadline import stalled_peer

database = _database_fixture
disposable_database = _disposable_database_fixture


@pytest.fixture(autouse=True)
def isolate_pg_addressing(monkeypatch):
    for name in ["PGHOST", "PGHOSTADDR", "PGPORT", "PGSERVICE",
                 "PGTARGETSESSIONATTRS", "PGLOADBALANCEHOSTS"]:
        monkeypatch.delenv(name, raising=False)


def snapshot(seconds=0.5, *, phase="terminal"):
    age = 720 if phase == "work" else 780
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=age - seconds)
    )


def held_resolver(monkeypatch, tmp_path):
    record = tmp_path / "resolver.json"
    prefix = f"""
import json, os, pathlib, socket, time
record = pathlib.Path({str(record)!r})
def held_lookup(host, port, **kwargs):
    record.write_text(json.dumps({{'pid': os.getpid(), 'host': host,
        'port': port, 'inputs': params}}))
    time.sleep(20)
    raise AssertionError('held DNS unexpectedly resumed')
socket.getaddrinfo = held_lookup
"""
    monkeypatch.setattr(bounds, "_DNS_RESOLVE_PROGRAM", prefix + bounds._DNS_RESOLVE_PROGRAM)
    children = []
    original = bounds.subprocess.Popen

    def capture(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(bounds.subprocess, "Popen", capture)
    return record, children


def assert_owned_resolver_reaped(record, children):
    observed = json.loads(record.read_text())
    assert observed["host"] == "held-dns.invalid"
    assert set(observed["inputs"]) <= {
        "host", "hostaddr", "port", "target_session_attrs", "load_balance_hosts"
    }
    assert len(children) == 1 and children[0].pid == observed["pid"]
    assert children[0].returncode == -signal.SIGKILL
    assert children[0].stdin.closed and children[0].stdout.closed
    with pytest.raises(ProcessLookupError):
        os.kill(observed["pid"], 0)


@pytest.mark.parametrize("surface", ["raw", "orm"])
@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_held_dns_expires_with_owned_child_reaped(monkeypatch, tmp_path, surface, phase):
    record, children = held_resolver(monkeypatch, tmp_path)
    repo = PgDB("postgresql://inert:inert@held-dns.invalid:5432/inert?sslmode=disable")
    start = time.monotonic()
    try:
        with bounds.accepted_postgres_query_scope(snapshot(phase=phase)):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded) as failure:
                if surface == "raw":
                    repo._connect()
                else:
                    with repo._sa_session() as session:
                        session.connection()
        duration = time.monotonic() - start
        assert 0.45 < duration < 0.9
        assert failure.value.detail["failure_code"] == "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED"
        assert_owned_resolver_reaped(record, children)
        print({"surface": surface, "phase": phase, "duration_seconds": duration,
               "held_dns_child_reaped": True, "late_connection_admitted": False})
    finally:
        repo._sa_engine.dispose()


def test_shorter_dns_connection_policy_is_preserved(monkeypatch, tmp_path):
    record, children = held_resolver(monkeypatch, tmp_path)
    deadline = snapshot(5)
    start = time.monotonic()
    with bounds.accepted_postgres_query_scope(deadline):
        with pytest.raises(psycopg.errors.ConnectionTimeout):
            bounds.connect_with_query_bounds(
                "host=held-dns.invalid connect_timeout=1 user=inert password=inert"
            )
    duration = time.monotonic() - start
    assert 1.8 < duration < 2.7
    assert datetime.now(timezone.utc) < deadline.terminal_deadline_at
    assert_owned_resolver_reaped(record, children)
    print({"surface": "shorter_dns_policy", "duration_seconds": duration,
           "owned_child_reaped": True})


@pytest.mark.parametrize("conninfo", [
    "host=127.0.0.1", "host=::1", "host=/tmp", "",
    "host=original.invalid hostaddr=127.0.0.1",
])
def test_already_addressed_targets_do_not_spawn(monkeypatch, conninfo):
    def forbidden(*args, **kwargs):
        raise AssertionError("Resolved/local target started a DNS subprocess")

    monkeypatch.setattr(bounds.subprocess, "Popen", forbidden)
    expected = psycopg.Connection._get_connection_params(conninfo)
    with bounds.accepted_postgres_query_scope(snapshot(2)):
        actual = bounds.AcceptedDeadlineConnection._get_connection_params(conninfo)
    assert actual == expected


def test_pg_hostaddr_environment_preserves_hostname(monkeypatch):
    monkeypatch.setenv("PGHOST", "identity.invalid")
    monkeypatch.setenv("PGHOSTADDR", "127.0.0.1")
    monkeypatch.setattr(bounds, "_resolve_dns_params", lambda *a: pytest.fail("resolved env used DNS"))
    with bounds.accepted_postgres_query_scope(snapshot(2)):
        params = bounds.AcceptedDeadlineConnection._get_connection_params("")
    assert params == {}
    attempts = conninfo_attempts(params)
    assert attempts == [{}]  # Original environment remains driver authority.


def test_address_expansion_preserves_identity_ports_and_applies_target_policy_once(monkeypatch):
    expected_addressing = []

    def resolve(params, budget):
        expected_addressing.append(params.copy())
        return [
            {"host": "identity.invalid", "hostaddr": "::1", "port": "111"},
            {"host": "identity.invalid", "hostaddr": "127.0.0.1", "port": "111"},
            {"host": "127.0.0.2", "hostaddr": "127.0.0.2", "port": "222"},
            {"host": "/tmp", "port": "333"},
        ]

    monkeypatch.setattr(bounds, "_resolve_dns_params", resolve)
    dsn = (
        "host=identity.invalid,127.0.0.2,/tmp port=111,222,333 "
        "user=inert password=inert dbname=inert sslmode=verify-full "
        "target_session_attrs=prefer-standby load_balance_hosts=random"
    )
    with bounds.accepted_postgres_query_scope(snapshot(2)):
        params = bounds.AcceptedDeadlineConnection._get_connection_params(dsn)
    assert len(expected_addressing) == 1
    assert params["host"] == "identity.invalid,identity.invalid,127.0.0.2,/tmp"
    assert params["hostaddr"] == "::1,127.0.0.1,127.0.0.2,"
    assert params["port"] == "111,111,222,333"
    for key in ["user", "password", "dbname", "sslmode", "target_session_attrs", "load_balance_hosts"]:
        assert params[key] == psycopg.Connection._get_connection_params(dsn)[key]
    attempts = conninfo_attempts(params)
    assert len(attempts) == 8
    assert all(a["target_session_attrs"] == "standby" for a in attempts[:4])
    assert all("target_session_attrs" not in a for a in attempts[4:])
    assert {a.get("hostaddr", "") for a in attempts} == {"::1", "127.0.0.1", "127.0.0.2", ""}


@pytest.mark.parametrize("environment", [False, True])
def test_service_file_resolution_fails_closed_only_in_accepted_scope(monkeypatch, environment):
    if environment:
        monkeypatch.setenv("PGSERVICE", "inert-service")
        dsn = "host=127.0.0.1"
    else:
        dsn = "service=inert-service host=127.0.0.1"
    expected = psycopg.Connection._get_connection_params(dsn)
    assert bounds.AcceptedDeadlineConnection._get_connection_params(dsn) == expected
    with bounds.accepted_postgres_query_scope(snapshot(2)):
        with pytest.raises(psycopg.OperationalError, match="cannot bound service-file"):
            bounds.AcceptedDeadlineConnection._get_connection_params(dsn)


def test_native_dns_error_retains_driver_operational_error(monkeypatch):
    prefix = """
import socket
def denied(*args, **kwargs):
    raise socket.gaierror(-2, 'controlled lookup rejected')
socket.getaddrinfo = denied
"""
    monkeypatch.setattr(bounds, "_DNS_RESOLVE_PROGRAM", prefix + bounds._DNS_RESOLVE_PROGRAM)
    with bounds.accepted_postgres_query_scope(snapshot(3)):
        with pytest.raises(psycopg.OperationalError, match="controlled lookup rejected"):
            bounds.connect_with_query_bounds("host=held-dns.invalid user=inert password=inert")


@pytest.mark.parametrize("surface", ["raw", "orm"])
@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_dns_then_real_handshake_share_original_budget(monkeypatch, surface, phase):
    prefix = """
import socket, time
def delayed(host, port, **kwargs):
    time.sleep(0.2)
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
             '', ('127.0.0.1', int(port)))]
socket.getaddrinfo = delayed
"""
    monkeypatch.setattr(bounds, "_DNS_RESOLVE_PROGRAM", prefix + bounds._DNS_RESOLVE_PROGRAM)
    with stalled_peer() as (peer, started, ended):
        repo = PgDB(
            f"postgresql://inert:inert@identity.invalid:{peer['port']}/inert"
            "?sslmode=disable&connect_timeout=1"
        )
        start = time.monotonic()
        try:
            with bounds.accepted_postgres_query_scope(snapshot(phase=phase)):
                with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                    if surface == "raw":
                        repo._connect()
                    else:
                        with repo._sa_session() as session:
                            session.connection()
            duration = time.monotonic() - start
            assert 0.45 < duration < 0.75
            assert started.is_set() and peer['startup_bytes'] > 0
            assert ended.wait(0.25) and peer.get('eof')
            print({"surface": surface, "phase": phase,
                   "dns_then_handshake_seconds": duration,
                   "native_peer_eof_before_release": True})
        finally:
            repo._sa_engine.dispose()


def test_failed_hostname_keeps_next_resolved_host_in_driver_order(monkeypatch):
    prefix = """
import socket
original = socket.getaddrinfo
def reject_first(host, port, **kwargs):
    if host == 'bad.invalid':
        raise socket.gaierror(-2, 'controlled lookup rejected')
    return original(host, port, **kwargs)
socket.getaddrinfo = reject_first
"""
    monkeypatch.setattr(bounds, "_DNS_RESOLVE_PROGRAM", prefix + bounds._DNS_RESOLVE_PROGRAM)
    with bounds.accepted_postgres_query_scope(snapshot(3)):
        params = bounds.AcceptedDeadlineConnection._get_connection_params(
            "host=bad.invalid,localhost port=111,222 sslmode=verify-full"
        )
    attempts = conninfo_attempts(params)
    assert attempts and all(a['host'] == 'localhost' and a['port'] == '222' for a in attempts)
    assert params['sslmode'] == 'verify-full'


@pytest.mark.integration
def test_healthy_dns_raw_new_and_reused_orm_sql(database):
    repo, _observer, _thread, _label, plain = database
    from sqlalchemy.engine import make_url

    url = make_url(plain)
    if url.host == "127.0.0.1":
        url = url.set(host="localhost")
    dns_repo = PgDB(url.render_as_string(hide_password=False))
    try:
        with bounds.accepted_postgres_query_scope(snapshot(4)):
            with dns_repo._connect() as connection:
                assert connection.execute("SELECT 1 AS value").fetchone()["value"] == 1
            with dns_repo._sa_session() as session:
                assert session.execute(text("SELECT 1")).scalar_one() == 1
            with dns_repo._sa_session() as session:
                assert session.execute(text("SELECT 1")).scalar_one() == 1
        with dns_repo._sa_session() as session:
            assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"
    finally:
        dns_repo._sa_engine.dispose()
