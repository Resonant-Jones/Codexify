"""Real loopback HTTP coverage of accepted-task streaming deadlines."""

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException

from guardian.core import ai_router, chat_completion_service, supported_profile
from guardian.core.config import Settings
from guardian.protocol_tokens import ErrorCode
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from guardian.tasks.types import ChatCompletionTask


@pytest.fixture
def runtime(monkeypatch):
    observed = {
        "mode": "success",
        "requests": [],
        "disconnect": threading.Event(),
        "abort": threading.Event(),
        "headers": {},
        "abort_paths": [],
        "inventory_match": True,
        "include_remote_header": True,
    }

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            headers = observed["headers"]
            body = json.dumps(
                {
                    "requests": [
                        {
                            "request_id": "fixture-remote",
                            "correlation_id": headers.get("X-Request-ID")
                            if observed["inventory_match"]
                            else "foreign",
                            "codexify_task_id": headers.get("X-Codexify-Task-ID"),
                            "codexify_attempt_id": headers.get("X-Codexify-Attempt-ID"),
                        }
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path.endswith("/cancel"):
                observed["abort_paths"].append(self.path)
                observed["abort"].set()
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    if observed.get("slow_abort"):
                        for byte in body:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(0.25)
                    else:
                        self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed["headers"] = dict(self.headers)
            observed["requests"].append((self.path, payload))
            mode = observed["mode"]
            try:
                if mode == "headers":
                    if observed["abort"].wait(0.7):
                        return
                status = (
                    500
                    if mode == "error_body"
                    else (
                        404
                        if mode == "retry" and len(observed["requests"]) == 1
                        else 200
                    )
                )
                self.send_response(status)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                if observed["include_remote_header"]:
                    self.send_header("X-Whooshd-Request-ID", "fixture-remote")
                self.end_headers()
                if mode == "retry" and len(observed["requests"]) == 1:
                    time.sleep(0.18)
                    return
                if mode in {"silent", "error_body"}:
                    if observed["abort"].wait(0.7):
                        return
                if mode in {"tokenless", "partial", "retry"}:
                    for index in range(14):
                        if observed["abort"].is_set():
                            return
                        content = "early " if mode == "partial" and index == 0 else ""
                        data = {
                            "choices": [{"delta": {"content": content}}],
                            "padding": "x" * 1024,
                        }
                        self.wfile.write(
                            ("data: " + json.dumps(data) + "\n\n").encode()
                        )
                        self.wfile.flush()
                        time.sleep(0.05)
                self.wfile.write(
                    b'data: {"choices":[{"delta":{"content":"answer"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
                )
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                observed["disconnect"].set()
            finally:
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}/v1"
    settings = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        LOCAL_BASE_URL=base,
        LOCAL_CHAT_MODEL="fixture-model",
        LOCAL_LLM_MODEL="fixture-model",
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_API_KEY="synthetic",
        LOCAL_COMPAT_FIRST=True,
        LLM_REQUEST_TIMEOUT_SECONDS=2,
    )
    monkeypatch.setattr(chat_completion_service, "get_settings", lambda: settings)
    monkeypatch.setattr(supported_profile, "get_active_supported_profile", lambda: None)
    monkeypatch.setattr(
        ai_router,
        "_resolve_local_base_candidates",
        lambda _: (
            [base, base.replace("/v1", "/fallback/v1")]
            if observed["mode"] == "retry"
            else [base]
        ),
    )
    yield observed, settings
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    assert not [
        t
        for t in threading.enumerate()
        if t.name in {"accepted-chat-http", "whooshd-cancel-monitor"}
    ]


def execute(remaining=0.25, *, cancel_check=lambda: False, callback=None):
    snapshot = (
        build_accepted_chat_task_deadline(
            datetime.now(timezone.utc) - timedelta(seconds=720 - remaining)
        ).to_dict()
        if remaining is not None
        else {}
    )
    task = ChatCompletionTask(user_id="fixture", thread_id=17001, **snapshot)
    try:
        result = chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "fixture"}],
            provider="local",
            model="fixture-model",
            bundle=None,
            token_callback=callback,
            cancel_check=cancel_check,
        )
    finally:
        assert {key: getattr(task, key) for key in snapshot} == snapshot
    return result


@pytest.mark.parametrize(
    "mode", ["headers", "silent", "tokenless", "partial", "retry", "error_body"]
)
def test_absolute_deadline_interrupts_real_http(runtime, mode):
    observed, _ = runtime
    observed["mode"] = mode
    chunks = []
    start = time.monotonic()
    with pytest.raises(HTTPException) as error:
        execute(callback=chunks.append)
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert time.monotonic() - start < 0.6
    assert "answer" not in chunks
    assert chunks == (["early "] if mode == "partial" else [])
    assert error.value.detail["completion_truth"]["completed"] is False
    assert error.value.detail["visible_output_emitted"] is (mode == "partial")
    assert len(observed["abort_paths"]) == 1
    assert observed["abort_paths"][0].endswith(
        "/runtime/requests/fixture-remote/cancel"
    )


@pytest.mark.parametrize("remaining", [10, None])
def test_valid_and_legacy_streams_keep_success(runtime, remaining):
    result = execute(remaining)
    assert result.output == "answer"
    assert result.terminal.successful


def test_expired_attempt_makes_zero_requests(runtime):
    observed, _ = runtime
    with pytest.raises(HTTPException) as error:
        execute(-1)
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert observed["requests"] == []


def test_child_inactivity_remains_provider_timeout(runtime, monkeypatch):
    from dataclasses import replace

    observed, settings = runtime
    observed["mode"] = "silent"
    policy = ai_router.resolve_local_runtime_policy("fixture-model", settings=settings)
    monkeypatch.setattr(
        ai_router,
        "resolve_local_runtime_policy",
        lambda *a, **k: replace(policy, read_timeout_seconds=0.1),
    )
    with pytest.raises(HTTPException) as error:
        execute(10)
    assert error.value.detail["failure_kind"] == "provider_timeout"
    assert "failure_code" not in error.value.detail


def test_explicit_cancellation_remains_distinct_and_closes_io(runtime):
    observed, _ = runtime
    observed["mode"] = "silent"
    start = time.monotonic()
    with pytest.raises(chat_completion_service.ChatTaskCancelled):
        execute(10, cancel_check=lambda: time.monotonic() - start >= 0.12)
    assert time.monotonic() - start < 0.6
    assert observed["abort_paths"] == ["/runtime/requests/fixture-remote/cancel"]


def test_deadline_cleanup_never_aborts_foreign_request(runtime):
    observed, _ = runtime
    observed.update(mode="silent", inventory_match=False, include_remote_header=False)
    with pytest.raises(HTTPException) as error:
        execute()
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert observed["abort_paths"] == []


def test_malformed_in_memory_envelope_fails_before_http(runtime):
    observed, _ = runtime
    task = ChatCompletionTask(
        user_id="fixture",
        thread_id=17001,
        accepted_at="invalid",
        work_deadline_at="invalid",
        terminal_deadline_at="invalid",
    )
    with pytest.raises(ValueError):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[],
            provider="local",
            model="fixture-model",
            bundle=None,
        )
    assert observed["requests"] == []


def test_abort_body_has_absolute_child_bound_and_preserves_deadline(runtime):
    observed, _ = runtime
    observed.update(mode="silent", slow_abort=True)
    start = time.monotonic()
    with pytest.raises(HTTPException) as error:
        execute()
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert time.monotonic() - start < 2.6
    assert observed["abort_paths"] == ["/runtime/requests/fixture-remote/cancel"]
