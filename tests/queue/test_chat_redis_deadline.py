"""Actual owned TCP waits, inherited retry limits and DNS child cleanup."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import socket
import subprocess
import threading
import time

import pytest
from redis import Redis
from redis.backoff import ConstantBackoff, NoBackoff
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

from guardian.core import chat_redis_deadline as bounds
from guardian.queue import redis_queue, task_events, turn_lock
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded, build_accepted_chat_task_deadline,
)


def snapshot(phase="work", seconds=.25):
    age = 780 if phase == "terminal" else 720
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=age-seconds)
    )


def read_command(stream):
    line = stream.readline()
    if not line:
        return None
    assert line.startswith(b"*")
    result = []
    for _ in range(int(line[1:])):
        size = stream.readline()
        assert size.startswith(b"$")
        result.append(stream.read(int(size[1:])))
        assert stream.read(2) == b"\r\n"
    return result


@contextmanager
def peer(target, *, mode="stall"):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    listener.settimeout(.05)
    stop = threading.Event()
    arrived = threading.Event()
    eof = threading.Event()
    state = {"port": listener.getsockname()[1], "commands": 0, "eofs": 0}
    sockets = []

    def serve():
        try:
            while not stop.is_set():
                try:
                    client, _ = listener.accept()
                except socket.timeout:
                    continue
                sockets.append(client)
                client.settimeout(4)
                with client, client.makefile("rb") as stream:
                    while not stop.is_set():
                        parts = read_command(stream)
                        if parts is None:
                            state["eofs"] += 1
                            eof.set()
                            break
                        name = parts[0].upper()
                        if name == b"CLIENT":
                            client.sendall(b"+OK\r\n")
                        elif name == target:
                            state["commands"] += 1
                            if mode == "first_ok_then_stall" and state["commands"] == 1:
                                client.sendall(b"+OK\r\n")
                                continue
                            if mode == "first_ok_then_stall":
                                eof.clear()
                            arrived.set()
                            if mode == "drip":
                                client.sendall(b"$30\r\n")
                                for _ in range(30):
                                    if stop.wait(.03):
                                        break
                                    client.sendall(b"x")
                                client.sendall(b"\r\n")
                            elif mode == "error":
                                client.sendall(b"-ERR owned probe\r\n")
                            elif mode == "drop":
                                break
                            elif mode == "healthy":
                                client.sendall(b"+PONG\r\n")
                            else:
                                assert stream.readline() == b""
                                state["eofs"] += 1
                                eof.set()
                                break
                        else:
                            raise AssertionError(name)
        except (BrokenPipeError, ConnectionResetError):
            eof.set()
        except OSError as error:
            if not stop.is_set():
                state["error"] = repr(error)
        except BaseException as error:
            state["error"] = repr(error)

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        yield state, arrived, eof
    finally:
        stop.set()
        for client in sockets:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            client.close()
        listener.close()
        thread.join(5)
        assert not thread.is_alive()
        assert "error" not in state, state


def factory(monkeypatch, state, *, socket_timeout=2, retry=None, host="127.0.0.1"):
    if retry is None:
        retry = Retry(NoBackoff(), 0)
    monkeypatch.setattr(redis_queue, "_connect_request_client", lambda: Redis(
        host=host, port=state["port"], decode_responses=True,
        socket_timeout=socket_timeout, socket_connect_timeout=2, retry=retry,
    ))


def test_maintenance_publisher_held_response_closes_within_operation_budget(monkeypatch):
    from guardian.workers import chat_worker

    original = redis_queue._CLIENT
    monkeypatch.setattr(chat_worker, "redis_operation_scope", lambda: bounds.redis_operation_scope(.25))
    with peer(b"SETEX") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        start = time.monotonic()
        chat_worker._publish_worker_heartbeat("active")
        duration = time.monotonic() - start
        assert .20 < duration < .65
        assert arrived.is_set() and state["commands"] == 1 and eof.wait(.25)
    assert bounds._budget.get() is None and redis_queue._CLIENT is original
    print({"surface": "maintenance_SETEX", "duration": duration, "peer_eof": True})


def test_reporter_is_joined_after_native_held_redis_io_and_executor_drain(monkeypatch):
    from guardian.tasks.types import ChatCompletionTask
    from guardian.workers import chat_worker

    class StopProbe(BaseException):
        pass

    previous_threads = set(threading.enumerate())
    entered, release = threading.Event(), threading.Event()
    accepted = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    task = ChatCompletionTask(user_id="inert-heartbeat-proof", thread_id=909003,
                              **accepted.to_dict())
    monkeypatch.setattr(chat_worker, "_initialize_worker", lambda: None)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda _: False)
    monkeypatch.setattr(chat_worker, "redis_operation_scope", lambda: bounds.redis_operation_scope(.25))

    def worker(owned):
        assert owned.task_id == task.task_id
        entered.set()
        assert release.wait(3)

    monkeypatch.setattr(chat_worker, "_run_chat_task", worker)
    with peer(b"SETEX", mode="first_ok_then_stall") as (state, arrived, eof):
        factory(monkeypatch, state)
        dequeues = 0

        def dequeue(*args, **kwargs):
            nonlocal dequeues
            dequeues += 1
            if dequeues == 1:
                return task.to_dict()
            if dequeues == 2:
                assert entered.wait(2) and arrived.wait(2)
                release.set()
                return None
            raise StopProbe()

        monkeypatch.setattr(chat_worker, "dequeue", dequeue)
        start = time.monotonic()
        try:
            with pytest.raises(StopProbe):
                chat_worker.run_forever()
        finally:
            release.set()
        duration = time.monotonic() - start
        assert .20 < duration < .9
        assert state["commands"] == 2 and eof.wait(.25) and state["eofs"] == 2
    assert not [t for t in threading.enumerate()
                if t not in previous_threads and t.name == "chat-worker-heartbeat"]
    assert bounds._budget.get() is None
    print({"surface": "reporter_join_held_SETEX", "duration": duration, "peer_eof": True})


def test_maintenance_dns_child_is_killed_reaped_and_pipes_closed(monkeypatch):
    children = []
    original = bounds.subprocess.Popen

    def tracked(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(bounds.subprocess, "Popen", tracked)
    monkeypatch.setattr(bounds, "_DNS_PROGRAM", "import time;time.sleep(20)\n" + bounds._DNS_PROGRAM)
    factory(monkeypatch, {"port": 1}, host="owned.invalid")
    start = time.monotonic()
    with pytest.raises(RedisTimeoutError, match="operation deadline"):
        with bounds.redis_operation_scope(.25):
            redis_queue.get_request_redis_client().ping()
    duration = time.monotonic() - start
    assert .20 < duration < .65
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdin.closed and children[0].stdout.closed
    assert bounds._budget.get() is None
    print({"surface": "maintenance_DNS", "duration": duration, "child_reaped": True})


def test_maintenance_retry_backoff_consumes_one_operation_budget(monkeypatch):
    with peer(b"PING", mode="drop") as (state, arrived, _eof):
        factory(monkeypatch, state, retry=Retry(ConstantBackoff(2), 3))
        start = time.monotonic()
        with pytest.raises(RedisTimeoutError, match="operation deadline"):
            with bounds.redis_operation_scope(.25):
                redis_queue.get_request_redis_client().ping()
        assert .20 < time.monotonic() - start < .65
        assert arrived.is_set() and state["commands"] == 1


def test_maintenance_scope_cannot_replace_accepted_budget(monkeypatch):
    with peer(b"PING", mode="healthy") as (state, _arrived, eof):
        factory(monkeypatch, state)
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            inherited = bounds._budget.get()
            client = redis_queue.get_request_redis_client()
            with pytest.raises(ValueError, match="replace an inherited budget"):
                with bounds.redis_operation_scope(20):
                    pytest.fail("maintenance must not replace accepted task scope")
            assert bounds._budget.get() is inherited
            assert redis_queue.get_request_redis_client() is client and client.ping()
        assert eof.wait(.25)


def test_maintenance_pool_and_client_cannot_escape_or_borrow_another_scope(monkeypatch):
    original = redis_queue._CLIENT
    with peer(b"PING", mode="healthy") as (state, _arrived, eof):
        factory(monkeypatch, state)
        with bounds.redis_operation_scope(2):
            client = redis_queue.get_request_redis_client()
            assert client.ping()
            connection = client.connection_pool._available_connections[0]
            assert connection._sock is not None
        assert connection._sock is None and eof.wait(.25)
        with pytest.raises(ValueError, match="outside"):
            client.ping()
        with bounds.redis_operation_scope(2):
            with pytest.raises(ValueError, match="outside"):
                client.ping()
            next_client = redis_queue.get_request_redis_client()
            assert next_client is not client and next_client.ping()
    assert bounds._budget.get() is None and redis_queue._CLIENT is original


def test_maintenance_terminal_switch_cannot_extend_operation(monkeypatch):
    factory(monkeypatch, {"port": 1})
    with bounds.redis_operation_scope(.05):
        time.sleep(.08)
        bounds.use_redis_terminal_budget()
        with pytest.raises(RedisTimeoutError, match="operation deadline"):
            redis_queue.get_request_redis_client()


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan")])
def test_maintenance_invalid_operation_limit_fails_before_client(monkeypatch, seconds):
    calls = []
    monkeypatch.setattr(redis_queue, "_connect_request_client", lambda: calls.append(True))
    with pytest.raises(ValueError, match="finite and positive"):
        with bounds.redis_operation_scope(seconds):
            redis_queue.get_request_redis_client()
    assert not calls and bounds._budget.get() is None


@pytest.mark.parametrize("surface,phase", [
    ("publish", "work"), ("publish", "terminal"),
    ("release", "terminal"), ("cancel", "work"),
])
def test_actual_held_response_expires_and_closes_before_peer_release(monkeypatch, surface, phase):
    target = {"publish": b"XADD", "release": b"EVAL", "cancel": b"SISMEMBER"}[surface]
    original = redis_queue._CLIENT
    with peer(target) as (state, arrived, eof):
        factory(monkeypatch, state)
        start = time.monotonic()
        with bounds.accepted_redis_scope(snapshot(phase)):
            if surface == "publish":
                kind = "task.completed" if phase == "terminal" else "task.state"
                result = task_events.publish_with_visibility("owned-probe", kind)
                assert not result["ok"]
                assert result["terminal_visibility"] is (phase == "terminal")
                assert isinstance(result["exception"], AcceptedChatTaskDeadlineExceeded)
            else:
                with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                    if surface == "release":
                        turn_lock.release_turn_lock(900000001, "owned-probe")
                    else:
                        redis_queue.is_cancelled("owned-probe")
        duration = time.monotonic() - start
        assert .20 < duration < .65
        assert arrived.is_set() and state["commands"] == 1
        assert eof.wait(.25)
        assert redis_queue._CLIENT is original
        print({"surface": surface, "phase": phase, "duration": duration, "peer_eof": True})


@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_continuing_resp_bytes_do_not_refresh_parent(monkeypatch, phase):
    with peer(b"GET", mode="drip") as (state, arrived, eof):
        factory(monkeypatch, state, socket_timeout=.1)
        start = time.monotonic()
        with bounds.accepted_redis_scope(snapshot(phase)):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                redis_queue.get_request_redis_client().get("owned-probe")
        duration = time.monotonic()-start
        assert .20 < duration < .65
        assert arrived.is_set() and eof.wait(.3)
        print({"surface": "partial_RESP", "phase": phase, "duration": duration})


def test_native_backoff_is_clipped_without_a_second_command(monkeypatch):
    with peer(b"PING", mode="drop") as (state, arrived, _eof):
        factory(monkeypatch, state, retry=Retry(ConstantBackoff(2), 3))
        start = time.monotonic()
        with bounds.accepted_redis_scope(snapshot()):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                redis_queue.get_request_redis_client().ping()
        assert .20 < time.monotonic()-start < .65
        assert arrived.is_set() and state["commands"] == 1


def test_application_retries_consume_the_same_parent(monkeypatch):
    with peer(b"XADD", mode="error") as (state, arrived, _eof):
        factory(monkeypatch, state)
        start = time.monotonic()
        original = redis_queue._CLIENT
        with bounds.accepted_redis_scope(snapshot()):
            result = task_events.publish_with_visibility("owned-probe", "task.state")
        assert not result["ok"]
        assert isinstance(result["exception"], AcceptedChatTaskDeadlineExceeded)
        assert .20 < time.monotonic()-start < .65
        assert arrived.is_set() and state["commands"] == 2
        assert redis_queue._CLIENT is original


@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_dns_child_is_killed_reaped_and_pipes_closed(monkeypatch, phase):
    children = []
    original = bounds.subprocess.Popen
    def tracked(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(bounds.subprocess, "Popen", tracked)
    monkeypatch.setattr(bounds, "_DNS_PROGRAM", "import time;time.sleep(20)\n"+bounds._DNS_PROGRAM)
    state = {"port": 1}
    factory(monkeypatch, state, host="owned.invalid")
    start = time.monotonic()
    with bounds.accepted_redis_scope(snapshot(phase)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            redis_queue.get_request_redis_client().ping()
    duration = time.monotonic()-start
    assert .20 < duration < .65
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdin.closed and children[0].stdout.closed
    print({"surface":"DNS", "phase":phase, "duration":duration, "child_reaped":True})


def test_stricter_socket_policy_preserves_ordinary_timeout(monkeypatch):
    with peer(b"GET") as (state, arrived, eof):
        factory(monkeypatch, state, socket_timeout=.05)
        start = time.monotonic()
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            with pytest.raises(RedisTimeoutError):
                redis_queue.get_request_redis_client().get("owned-probe")
        assert .03 < time.monotonic()-start < .4
        assert arrived.is_set() and eof.wait(.25)


@pytest.mark.parametrize("invalid", [False, True])
def test_expired_or_invalid_snapshot_starts_no_client(monkeypatch, invalid):
    calls = []
    monkeypatch.setattr(redis_queue, "_connect_request_client", lambda: calls.append(True))
    with bounds.accepted_redis_scope(snapshot("terminal", seconds=-1) if not invalid else None, invalid=invalid):
        with pytest.raises(ValueError if invalid else AcceptedChatTaskDeadlineExceeded):
            redis_queue.get_request_redis_client()
    assert not calls


def test_terminal_switch_uses_original_reserve_and_pool(monkeypatch):
    with peer(b"PING", mode="healthy") as (state, _arrived, _eof):
        factory(monkeypatch, state)
        accepted = snapshot(seconds=.05)
        with bounds.accepted_redis_scope(accepted):
            client = redis_queue.get_request_redis_client()
            assert client.ping()
            time.sleep(.08)
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                redis_queue.get_request_redis_client()
            bounds.use_redis_terminal_budget()
            assert redis_queue.get_request_redis_client() is client
            assert client.ping()
            budget = bounds._budget.get()
            assert 59 < budget.remaining() < 60
        assert state["commands"] == 2


def test_legacy_global_client_and_policy_are_unchanged():
    original = redis_queue._CLIENT
    with bounds.accepted_redis_scope(None):
        assert redis_queue.get_request_redis_client() is original
    assert redis_queue._CLIENT is original


def test_scope_pool_is_closed_and_removed(monkeypatch):
    with peer(b"PING", mode="healthy") as (state, _arrived, eof):
        factory(monkeypatch, state)
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            client = redis_queue.get_request_redis_client()
            assert client.ping()
            assert client.connection_pool._available_connections[0]._sock is not None
        assert client.connection_pool._available_connections[0]._sock is None
        assert bounds._budget.get() is None and eof.wait(.25)


@pytest.mark.parametrize("phase", ["work", "terminal"])
def test_tls_handshake_stall_inherits_parent(monkeypatch, phase):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    arrived = threading.Event()
    eof = threading.Event()
    state = {}
    def serve():
        with listener.accept()[0] as client:
            client.settimeout(3)
            while True:
                data = client.recv(8192)
                if not data:
                    eof.set()
                    return
                arrived.set()
    thread = threading.Thread(target=serve)
    thread.start()
    monkeypatch.setattr(redis_queue, "_connect_request_client", lambda: Redis(
        host="127.0.0.1", port=listener.getsockname()[1], ssl=True,
        socket_timeout=2, socket_connect_timeout=2, retry=Retry(NoBackoff(),0),
    ))
    start = time.monotonic()
    try:
        with bounds.accepted_redis_scope(snapshot(phase)):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                redis_queue.get_request_redis_client().ping()
        duration = time.monotonic()-start
        assert .2 < duration < .65
        assert arrived.is_set() and eof.wait(.25)
        print({"surface":"TLS_handshake","phase":phase,"duration":duration,"peer_eof":True})
    finally:
        listener.close()
        thread.join(5)
        assert not thread.is_alive()


def test_actual_hostname_tls_identity_and_auth_are_preserved(monkeypatch, tmp_path):
    import ssl
    key=tmp_path/"owned-key.pem"
    cert=tmp_path/"owned-cert.pem"
    subprocess.run([
        "openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
        "-keyout",str(key),"-out",str(cert),"-subj","/CN=localhost",
        "-addext","subjectAltName=DNS:localhost",
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert,key)
    listener=socket.socket()
    listener.bind(("127.0.0.1",0))
    listener.listen(1)
    listener.settimeout(5)
    state={"auth":False,"ping":False}
    eof=threading.Event()
    def serve():
        try:
            with listener.accept()[0] as raw:
                raw.settimeout(5)
                with context.wrap_socket(raw,server_side=True) as client, client.makefile("rb") as stream:
                    while True:
                        parts=read_command(stream)
                        if parts is None:
                            eof.set()
                            return
                        if parts[0].upper()==b"AUTH":
                            assert parts[1:]==[b"owned-user",b"owned-password"]
                            state["auth"]=True
                            client.sendall(b"+OK\r\n")
                        elif parts[0].upper()==b"CLIENT":
                            client.sendall(b"+OK\r\n")
                        elif parts[0].upper()==b"PING":
                            state["ping"]=True
                            client.sendall(b"+PONG\r\n")
                        else:
                            raise AssertionError(parts[0])
        except BaseException as error:
            state["error"]=repr(error)
    thread=threading.Thread(target=serve)
    thread.start()
    monkeypatch.setattr(redis_queue,"_connect_request_client",lambda:Redis(
        host="localhost",port=listener.getsockname()[1],ssl=True,
        ssl_ca_certs=str(cert),ssl_check_hostname=True,
        username="owned-user",password="owned-password",
        decode_responses=True,socket_timeout=2,socket_connect_timeout=2,
        retry=Retry(NoBackoff(),0),
    ))
    try:
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            client=redis_queue.get_request_redis_client()
            assert client.ping()
            connection=client.connection_pool._available_connections[0]
            assert connection.host=="localhost"
            assert isinstance(connection,bounds.AcceptedDeadlineSSLConnection)
            assert connection._sock.getpeercert()["subjectAltName"]==(("DNS","localhost"),)
        assert eof.wait(.25) and state["auth"] and state["ping"] and "error" not in state
    finally:
        listener.close()
        thread.join(6)
        assert not thread.is_alive()


def test_ordinary_legacy_tcp_timeout_matches_shorter_accepted_policy():
    with peer(b"GET") as (state,arrived,eof):
        client=Redis(host="127.0.0.1",port=state["port"],socket_timeout=.05,
                     socket_connect_timeout=2,retry=Retry(NoBackoff(),0))
        start=time.monotonic()
        try:
            with bounds.accepted_redis_scope(None):
                with pytest.raises(RedisTimeoutError):
                    client.get("owned-probe")
            assert .03 < time.monotonic()-start < .4
            assert arrived.is_set() and eof.wait(.25)
        finally:
            client.close()
            client.connection_pool.disconnect()


def test_worker_scopes_share_one_wall_and_monotonic_anchor(monkeypatch):
    from guardian.core import chat_postgres_deadline
    from guardian.tasks.types import ChatCompletionTask
    from guardian.workers import chat_worker
    task=ChatCompletionTask(user_id="local",thread_id=1,task_id="owned",
                            **snapshot(seconds=5).to_dict())
    snapshot_fields = {key: getattr(task, key) for key in ("accepted_at", "work_deadline_at", "terminal_deadline_at")}
    seen=[]
    def body(_task):
        redis_budget=bounds._budget.get()
        pg_budget=chat_postgres_deadline._budget.get()
        assert redis_budget.work_end==pg_budget.work_end
        assert redis_budget.terminal_end==pg_budget.terminal_end
        seen.append(True)
    monkeypatch.setattr(chat_worker, "get_chat_completion_attempt_by_task_id", lambda _db, task_id: {
        "backend_task_id": task_id, "request_id": task.request_id,
        "thread_id": task.thread_id, "turn_id": chat_worker._extract_turn_id(task),
        "deadline_snapshot": snapshot_fields,
    })
    monkeypatch.setattr(chat_worker, "observe_chat_completion_attempt_terminal", lambda *args, **kwargs:
        SimpleNamespace(completed_message_id=None, terminal_event_type=None, terminal_outcome=None))
    monkeypatch.setattr(chat_worker,"_run_chat_task_with_query_budget",body)
    chat_worker._run_chat_task(task)
    assert seen and bounds._budget.get() is None


@pytest.mark.parametrize("condition",["cancelled","expired","invalid","unavailable"])
def test_pre_dispatch_observation_remains_bounded_and_task_is_not_dropped(monkeypatch,condition):
    from guardian.tasks.types import ChatCompletionTask
    from guardian.workers import chat_worker
    from redis.exceptions import ConnectionError
    deadline=snapshot("terminal",seconds=-1) if condition=="expired" else snapshot(seconds=5)
    task=ChatCompletionTask(user_id="local",thread_id=1,task_id="owned",**deadline.to_dict())
    if condition=="invalid":
        task.accepted_at="invalid"
    monkeypatch.setattr(chat_worker,"_publish_worker_heartbeat",lambda *_args:None)
    def cancellation(_task_id):
        assert bounds._budget.get() is not None
        bounds._budget.get().remaining()
        if condition=="unavailable":
            raise ConnectionError("owned unavailable")
        return condition=="cancelled"
    monkeypatch.setattr(chat_worker,"is_cancelled",cancellation)
    assert chat_worker._chat_task_cancelled_before_dispatch(task)==(condition!="unavailable")
    assert bounds._budget.get() is None


def test_dns_delay_and_response_wait_share_original_budget(monkeypatch):
    monkeypatch.setattr(bounds,"_DNS_PROGRAM","import time;time.sleep(.2)\n"+bounds._DNS_PROGRAM)
    with peer(b"GET") as (state,arrived,eof):
        factory(monkeypatch,state,host="localhost")
        start=time.monotonic()
        with bounds.accepted_redis_scope(snapshot(seconds=.5)):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                redis_queue.get_request_redis_client().get("owned-probe")
        duration=time.monotonic()-start
        assert .45 < duration < .7
        assert arrived.is_set() and eof.wait(.25)
        print({"surface":"DNS_then_RESP","duration":duration,"peer_eof":True})


def test_shorter_dns_policy_retains_ordinary_timeout_and_reaps(monkeypatch):
    monkeypatch.setattr(bounds,"_DNS_PROGRAM","import time;time.sleep(20)\n"+bounds._DNS_PROGRAM)
    children=[]
    original=bounds.subprocess.Popen
    def tracked(*args,**kwargs):
        child=original(*args,**kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(bounds.subprocess,"Popen",tracked)
    monkeypatch.setattr(redis_queue,"_connect_request_client",lambda:Redis(
        host="owned.invalid",port=1,decode_responses=True,
        socket_timeout=2,socket_connect_timeout=.05,retry=Retry(NoBackoff(),0),
    ))
    start=time.monotonic()
    with bounds.accepted_redis_scope(snapshot(seconds=5)):
        with pytest.raises(RedisTimeoutError):
            redis_queue.get_request_redis_client().ping()
    assert .03 < time.monotonic()-start < .4
    assert len(children)==1 and children[0].poll() is not None
    assert children[0].stdin.closed and children[0].stdout.closed


def test_owned_client_cannot_escape_or_borrow_a_new_task_budget(monkeypatch):
    with peer(b"PING",mode="healthy") as (state,_arrived,eof):
        factory(monkeypatch,state)
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            client=redis_queue.get_request_redis_client()
            assert client.ping()
        assert eof.wait(.25)
        with pytest.raises(ValueError,match="owning task scope"):
            client.ping()
        with bounds.accepted_redis_scope(snapshot(seconds=5)):
            with pytest.raises(ValueError,match="owning task scope"):
                client.ping()
        assert state["commands"]==1


def test_external_ocsp_fails_closed_before_connect(monkeypatch):
    from redis.exceptions import ConnectionError
    monkeypatch.setattr(redis_queue,"_connect_request_client",lambda:Redis(
        host="owned.invalid",port=1,ssl=True,ssl_validate_ocsp=True,
        socket_timeout=2,socket_connect_timeout=2,retry=Retry(NoBackoff(),0),
    ))
    def forbidden(*args,**kwargs):
        raise AssertionError("unsupported OCSP must not reach DNS or TCP")
    monkeypatch.setattr(bounds,"_addresses",forbidden)
    with bounds.accepted_redis_scope(snapshot(seconds=5)):
        with pytest.raises(ConnectionError,match="OCSP"):
            redis_queue.get_request_redis_client().ping()


def test_terminal_cleanup_held_eval_closes_under_maintenance_budget(monkeypatch):
    original = redis_queue._CLIENT
    with peer(b"EVAL") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        start = time.monotonic()
        with pytest.raises(RedisTimeoutError):
            with bounds.redis_operation_scope(.25):
                turn_lock.release_terminal_attempt_turn_lock(
                    1, owner_task_id="owned-task", lease_token="owned-token"
                )
        duration = time.monotonic() - start
        assert .20 < duration < .65
        assert arrived.is_set() and state["commands"] == 1 and eof.wait(.25)
    assert bounds._budget.get() is None and redis_queue._CLIENT is original
    print({"surface": "terminal_cleanup_EVAL", "duration": duration, "peer_eof": True})


def test_receipt_terminal_probe_held_xrange_closes_page_budget(monkeypatch):
    original = redis_queue._CLIENT
    with peer(b"XRANGE") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        start = time.monotonic()
        with bounds.redis_operation_scope(.25):
            result = task_events.describe_terminal_state_in_scope("owned-receipt-task")
        duration = time.monotonic() - start
        assert .20 < duration < .65
        assert result["state"] == "unknown" and result["event_type"] is None
        assert arrived.is_set() and state["commands"] == 1 and eof.wait(.25)
    assert bounds._budget.get() is None and redis_queue._CLIENT is original
    print({"surface": "receipt_terminal_XRANGE", "duration": duration, "peer_eof": True})


def test_supported_sse_held_xread_closes_owned_pool_within_transport_budget(monkeypatch):
    original = redis_queue._CLIENT
    original_queue = redis_queue._QUEUE_CLIENT
    monkeypatch.setattr(task_events, "redis_operation_scope", lambda *a: bounds.redis_operation_scope(.25))
    with peer(b"XREAD") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        start = time.monotonic()
        with pytest.raises(RedisTimeoutError):
            task_events.read_events_bounded("owned-sse-task", "0-0", block_ms=100)
        duration = time.monotonic() - start
        assert .20 < duration < .65
        assert arrived.is_set() and state["commands"] == 1 and eof.wait(.25)
    assert bounds._budget.get() is None and redis_queue._CLIENT is original
    assert redis_queue._QUEUE_CLIENT is original_queue
    print({"surface": "supported_sse_XREAD", "duration": duration, "peer_eof": True, "commands": state["commands"]})


@pytest.mark.asyncio
async def test_supported_sse_cancelled_consumer_leaves_no_unbounded_reader(monkeypatch):
    import asyncio
    from guardian import guardian_api
    from guardian.core import task_event_access
    from guardian.core.dependencies import RequestUserScope
    from guardian.guardian_api import stream_task_events

    principal = RequestUserScope(user_id="sse-owner", account_id="sse-owner", multi_user_enabled=True)
    monkeypatch.setattr(guardian_api, "chatlog_db", SimpleNamespace(
        get_chat_thread=lambda thread_id: {"id": thread_id, "user_id": "sse-owner"},
    ))
    monkeypatch.setattr(task_event_access, "get_chat_completion_attempt_by_task_id",
        lambda _db, task_id: {"backend_task_id": task_id, "thread_id": 1})

    class Request:
        async def is_disconnected(self):
            return False
    finished = threading.Event()
    reader = task_events.read_events_bounded
    def tracked(*args, **kwargs):
        try:
            return reader(*args, **kwargs)
        finally:
            finished.set()
    monkeypatch.setattr(task_events, "read_events_bounded", tracked)
    monkeypatch.setattr(task_events, "redis_operation_scope", lambda *a: bounds.redis_operation_scope(.25))
    with peer(b"XREAD") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        response = await stream_task_events(Request(), "owned-sse-task", last_id_query="0-0",
                                            last_event_id_header=None, principal=principal)
        assert await anext(response.body_iterator) == "retry: 3000\n\n"
        pending = asyncio.create_task(anext(response.body_iterator))
        assert await asyncio.to_thread(arrived.wait, .5)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert await asyncio.to_thread(finished.wait, .65)
        assert eof.wait(.25) and state["commands"] == 1
    assert bounds._budget.get() is None
