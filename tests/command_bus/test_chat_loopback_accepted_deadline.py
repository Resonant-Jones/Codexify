"""Real-socket deadline proof for accepted chat command HTTP participation."""

import asyncio
import inspect
import json
import select
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from guardian.command_bus import invoke, loopback_http_adapter as adapter
from guardian.command_bus.contracts import ActorSpec, InvokeRequest
from guardian.command_bus.store import CommandBusStore
from guardian.protocol_tokens import ErrorCode
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from tests.command_bus.test_invoke_permission_profile_enforcement import _command


def deadline(remaining=0.35):
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=720 - remaining)
    )


def deadline_kwargs(function, snapshot):
    # The baseline must exercise the old transport, rather than fail on its API.
    return (
        {"accepted_deadline": snapshot}
        if "accepted_deadline" in inspect.signature(function).parameters
        else {}
    )


@pytest.fixture
def runtime(monkeypatch):
    state = SimpleNamespace(
        requests=[],
        clients=[],
        closed=threading.Event(),
        entered=threading.Event(),
        release=threading.Event(),
        active=threading.Event(),
        handlers=[],
    )

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            state.handlers.append(threading.current_thread())
            state.requests.append((self.path, dict(self.headers)))
            state.entered.set()
            state.active.set()
            try:
                if self.path == "/redirect":
                    time.sleep(0.13)
                    self.send_response(302)
                    self.send_header("Location", "/trickle")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                body = json.dumps({"ok": True, "padding": "x" * 1024}).encode()
                if self.path != "/headers":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                if self.path in {"/headers", "/silent"}:
                    finish = time.monotonic() + 0.9
                    while time.monotonic() < finish and not state.release.is_set():
                        ready, _, _ = select.select([self.connection], [], [], 0.02)
                        if ready and self.connection.recv(1, socket.MSG_PEEK) == b"":
                            state.closed.set()
                            # A disconnected client does not cancel server work.
                            state.release.wait(1.0)
                            break
                    if self.path == "/headers":
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                if self.path == "/trickle":
                    for start in range(0, len(body), 32):
                        self.wfile.write(body[start : start + 32])
                        self.wfile.flush()
                        if state.release.wait(0.04):
                            break
                else:
                    self.wfile.write(body)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                state.closed.set()
            finally:
                state.active.clear()
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    state.base = base
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", base)
    original_client = httpx.AsyncClient
    original_send = original_client.send

    class ObservedClient(original_client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            state.clients.append(self)

        async def send(self, request, *args, **kwargs):
            assert str(request.url).startswith(base + "/")
            return await original_send(self, request, *args, **kwargs)

    monkeypatch.setattr(adapter.httpx, "AsyncClient", ObservedClient)
    yield state
    state.release.set()
    server.shutdown()
    server.server_close()
    thread.join(2)
    for handler in state.handlers:
        handler.join(2)
        assert not handler.is_alive()
    assert not thread.is_alive()
    assert all(client.is_closed for client in state.clients)


async def request(runtime, path, snapshot):
    return await adapter.execute_loopback_request(
        method="GET",
        path_template=path,
        path_params={},
        query={},
        headers={},
        body=None,
        inbound_headers={"X-API-Key": "fixture-key", "Ignored": "drop"},
        **deadline_kwargs(adapter.execute_loopback_request, snapshot),
    )


@pytest.mark.parametrize("path", ["/headers", "/silent", "/trickle", "/redirect"])
def test_parent_total_deadline_closes_real_http(runtime, path):
    snapshot = deadline()
    before = snapshot.to_dict()

    async def probe():
        start = time.monotonic()
        with pytest.raises(HTTPException) as caught:
            await request(runtime, path, snapshot)
        assert caught.value.detail["failure_code"] == (
            ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
        )
        assert time.monotonic() - start < 0.75
        assert all(client.is_closed for client in runtime.clients)
        assert not [
            task
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task() and not task.done()
        ]

    asyncio.run(probe())
    assert runtime.closed.wait(0.5)
    assert runtime.requests
    if path in {"/headers", "/silent"}:
        assert (
            runtime.active.is_set()
        ), "client closure must not imply server cancellation"
    if path == "/redirect":
        assert [item[0] for item in runtime.requests] == ["/redirect", "/trickle"]
    assert snapshot.to_dict() == before


def test_expired_snapshot_starts_no_http(runtime):
    with pytest.raises(AcceptedChatTaskDeadlineExceeded):
        asyncio.run(request(runtime, "/fast", deadline(-1)))
    assert runtime.requests == []


@pytest.mark.parametrize("legacy", [False, True])
def test_fast_and_legacy_success_preserve_auth(runtime, legacy):
    result = asyncio.run(request(runtime, "/fast", None if legacy else deadline(2)))
    assert result["status_code"] == 200
    assert result["body"]["ok"] is True
    assert runtime.requests[0][1]["X-API-Key"] == "fixture-key"
    assert "Ignored" not in runtime.requests[0][1]
    assert not any("deadline" in header.lower() for header in runtime.requests[0][1])


def test_outer_cancellation_closes_client_without_deadline_substitution(runtime):
    async def probe():
        task = asyncio.create_task(request(runtime, "/headers", deadline(5)))
        for _ in range(100):
            if runtime.entered.is_set():
                break
            await asyncio.sleep(0.01)
        assert runtime.entered.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert all(client.is_closed for client in runtime.clients)

    asyncio.run(probe())
    assert runtime.closed.wait(0.5)


def test_child_policy_timeout_before_parent_is_not_parent_failure(runtime, monkeypatch):
    monkeypatch.setattr(
        adapter, "LOOPBACK_REQUEST_TIMEOUT_SECONDS", 0.15, raising=False
    )
    snapshot = deadline(3)
    with pytest.raises(httpx.TimeoutException):
        asyncio.run(request(runtime, "/trickle", snapshot))
    assert datetime.now(timezone.utc) < snapshot.work_deadline_at
    assert runtime.closed.wait(0.5)


def test_expiry_during_preparation_starts_no_http(runtime, monkeypatch):
    original = adapter.render_path

    def slow_path(*args):
        time.sleep(0.08)
        return original(*args)

    monkeypatch.setattr(adapter, "render_path", slow_path)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded):
        asyncio.run(request(runtime, "/fast", deadline(0.04)))
    assert runtime.requests == []


def test_transport_timeout_before_parent_retains_original_error(runtime, monkeypatch):
    original = httpx.ConnectTimeout("fixture connect timeout")

    async def fail(self, **kwargs):
        raise original

    monkeypatch.setattr(adapter.httpx.AsyncClient, "request", fail)
    with pytest.raises(httpx.ConnectTimeout) as caught:
        asyncio.run(request(runtime, "/fast", deadline(3)))
    assert caught.value is original
    assert runtime.requests == []


def prepare_invoke(monkeypatch):
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    command = _command()
    monkeypatch.setattr(
        invoke,
        "build_command_index",
        lambda app: (
            {command.command_id: command},
            SimpleNamespace(manifest_version="1.0"),
        ),
    )
    return InvokeRequest(
        invoke_version="1.0",
        command_id=command.command_id,
        actor=ActorSpec(kind="human", id="operator"),
        idempotency_key="fixture-key",
    )


@pytest.mark.parametrize("serialized", [False, True])
def test_invoke_preserves_deadline_and_records_failed_run(monkeypatch, serialized):
    payload = prepare_invoke(monkeypatch)
    snapshot = deadline(3)
    original = AcceptedChatTaskDeadlineExceeded(attempted=True)
    if serialized:
        original = HTTPException(status_code=504, detail=dict(original.detail))
    observed = []

    async def fail(**kwargs):
        observed.append(kwargs)
        raise original

    monkeypatch.setattr(invoke, "execute_loopback_request", fail)
    store = CommandBusStore()
    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            invoke.execute_invoke(
                payload=payload,
                auth_subject="operator",
                inbound_headers={},
                store=store,
                app=object(),
                execution_lane="tools",
                **deadline_kwargs(invoke.execute_invoke, snapshot),
            )
        )
    assert caught.value is original
    assert observed[0]["accepted_deadline"] is snapshot
    run = store.get_run_by_idempotency_key(payload.command_id, payload.idempotency_key)
    assert run["status"] == "failed"
    events = store._mem_events[run["run_id"]]
    assert events[-1]["event_type"] == "run.failed"
    assert not any(event["event_type"] == "run.completed" for event in events)


def test_public_payload_cannot_supply_accepted_deadline():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InvokeRequest(
            invoke_version="1.0",
            command_id="cmd.read.health",
            actor=ActorSpec(kind="human", id="operator"),
            accepted_deadline=deadline().to_dict(),
        )


def test_shared_service_deadline_closes_http_without_followup_generation(
    runtime, monkeypatch
):
    from unittest.mock import Mock
    from guardian.core import chat_completion_service as service
    from guardian.routes import command_bus as routes
    from tests.providers.test_tool_turn_transport_convergence import (
        CANONICAL_ARGUMENTS,
        CANONICAL_COMMAND_ID,
        _build_task,
        _canonical_tool_spec,
        _seed_service,
        _whooshd_stage_2e_response,
    )

    model = "gemma-4-12b-it-qat-4bit"
    _seed_service(monkeypatch, provider="local", model=model)
    task = _build_task(
        task_id="fixture-loopback-parent",
        provider="local",
        model=model,
        tools=[_canonical_tool_spec()],
    )
    snapshot = deadline(0.5).to_dict()
    for key, value in snapshot.items():
        setattr(task, key, value)
    provider = Mock(
        return_value=_whooshd_stage_2e_response(
            kind="tool_decision",
            text=None,
            command_id=CANONICAL_COMMAND_ID,
            arguments=CANONICAL_ARGUMENTS,
        )
    )
    command = _command(command_id=CANONICAL_COMMAND_ID, path_template="/trickle")
    monkeypatch.setattr(
        invoke,
        "build_command_index",
        lambda app: (
            {command.command_id: command},
            SimpleNamespace(manifest_version="1.0"),
        ),
    )
    store = CommandBusStore()
    monkeypatch.setattr(routes, "_store", store)
    monkeypatch.setattr(service, "execute_invoke", invoke.execute_invoke)
    monkeypatch.setattr(service, "chat_with_ai", provider)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded):
        service.run_chat_completion_task(task, persist_assistant_message=False)
    assert provider.call_count == 1
    assert [item[0] for item in runtime.requests] == ["/trickle"]
    assert runtime.closed.wait(0.5)
    assert len(store._mem_runs) == 1
    assert next(iter(store._mem_runs.values()))["status"] == "failed"
    assert {key: getattr(task, key) for key in snapshot} == snapshot
