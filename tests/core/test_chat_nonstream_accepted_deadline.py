"""Real loopback HTTP proof for accepted local non-streaming inference."""

import json
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException

from guardian.core import ai_router, chat_completion_service, supported_profile
from guardian.core.config import Settings
from guardian.protocol_tokens import ErrorCode
from guardian.providers.whooshd_tool_adapter import (
    QUALIFIED_MODEL_ALIAS,
    WhooshdStructuredResponse,
)
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from guardian.tasks.types import ChatCompletionTask

TOOL = {
    "command_id": "op::lookup_widget",
    "description": "Inspect a synthetic widget.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [],
        "properties": {},
    },
}
ANSWER = json.dumps({"kind": "assistant", "text": "answer"})


@pytest.fixture
def runtime(monkeypatch):
    observed = {
        "mode": "success",
        "requests": [],
        "headers": {},
        "abort_paths": [],
        "abort": threading.Event(),
        "inventory_match": True,
        "remote_header": True,
    }

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            headers = observed["headers"]
            self.reply(
                json.dumps(
                    {
                        "requests": [
                            {
                                "request_id": "fixture-remote",
                                "correlation_id": (
                                    headers.get("X-Request-ID")
                                    if observed["inventory_match"]
                                    else "foreign"
                                ),
                                "codexify_task_id": headers.get("X-Codexify-Task-ID"),
                                "codexify_attempt_id": headers.get(
                                    "X-Codexify-Attempt-ID"
                                ),
                            }
                        ]
                    }
                ).encode()
            )

        def reply(self, body):
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path.endswith("/cancel"):
                observed["abort_paths"].append(self.path)
                observed["abort"].set()
                body = b'{"ok":true}'
                if observed.get("slow_abort"):
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    try:
                        for byte in body:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(0.25)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                else:
                    self.reply(body)
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed["headers"] = dict(self.headers)
            observed["requests"].append((self.path, payload))
            mode = observed["mode"]
            body = json.dumps(
                {
                    "choices": [
                        {"message": {"content": ANSWER}, "finish_reason": "stop"}
                    ],
                    "padding": "x" * 1024,
                }
            ).encode()
            first_retry = mode == "retry" and len(observed["requests"]) == 1
            try:
                if mode == "headers" or mode == "retry" and not first_retry:
                    if observed["abort"].wait(0.8):
                        return
                self.send_response(
                    404 if first_retry else 500 if mode == "error_body" else 200
                )
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                if observed["remote_header"]:
                    self.send_header("X-Whooshd-Request-ID", "fixture-remote")
                self.end_headers()
                if first_retry:
                    time.sleep(0.16)
                if mode in {"silent", "error_body"}:
                    if observed["abort"].wait(0.8):
                        return
                if mode == "trickle":
                    for start in range(0, len(body), 64):
                        if observed["abort"].is_set():
                            return
                        self.wfile.write(body[start : start + 64])
                        self.wfile.flush()
                        time.sleep(0.05)
                else:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
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
        LOCAL_CHAT_MODEL=QUALIFIED_MODEL_ALIAS,
        LOCAL_LLM_MODEL=QUALIFIED_MODEL_ALIAS,
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
    origin = base.removesuffix("/v1")
    post = ai_router.requests.post
    send = httpx.AsyncClient.send

    def guarded_post(url, *args, **kwargs):
        assert str(url).startswith(origin + "/")
        return post(url, *args, **kwargs)

    async def guarded_send(client, request, *args, **kwargs):
        assert str(request.url).startswith(origin + "/")
        return await send(client, request, *args, **kwargs)

    monkeypatch.setattr(ai_router.requests, "post", guarded_post)
    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_send)
    yield observed, settings
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    assert not [t for t in threading.enumerate() if t.name == "accepted-chat-http"]


def execute(remaining=0.25):
    snapshot = (
        build_accepted_chat_task_deadline(
            datetime.now(timezone.utc) - timedelta(seconds=720 - remaining)
        ).to_dict()
        if remaining is not None
        else {}
    )
    task = ChatCompletionTask(
        user_id="fixture", thread_id=17002, tools=[TOOL], **snapshot
    )
    try:
        return chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "fixture"}],
            provider="local",
            model=QUALIFIED_MODEL_ALIAS,
            bundle=None,
        )
    finally:
        assert {key: getattr(task, key) for key in snapshot} == snapshot


@pytest.mark.parametrize(
    "mode", ["headers", "silent", "trickle", "error_body", "retry"]
)
def test_absolute_deadline_interrupts_local_nonstream_http(runtime, mode):
    observed, _ = runtime
    observed["mode"] = mode
    start = time.monotonic()
    with pytest.raises(HTTPException) as error:
        execute()
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert time.monotonic() - start < 0.65
    assert error.value.detail["completion_truth"]["completed"] is False
    assert error.value.detail["completion_truth"]["attempted"] is True
    assert error.value.detail["visible_output_emitted"] is False
    assert "terminal_evidence" not in error.value.detail
    correlation = error.value.detail["request_correlation"]
    assert observed["headers"]["X-Request-ID"] == correlation["request_id"]
    assert observed["headers"]["X-Codexify-Task-ID"] == correlation["task_id"]
    assert observed["headers"]["X-Codexify-Attempt-ID"] == correlation["attempt_id"]
    assert len(observed["requests"]) == (2 if mode == "retry" else 1)
    assert len(observed["abort_paths"]) == 1
    assert observed["abort_paths"][0].endswith(
        "/runtime/requests/fixture-remote/cancel"
    )


@pytest.mark.parametrize("remaining", [10, None])
def test_valid_and_legacy_structured_responses_preserve_output(runtime, remaining):
    observed, _ = runtime
    result = execute(remaining)
    assert result.terminal.successful
    assert isinstance(result.output, WhooshdStructuredResponse)
    assert result.output.content == ANSWER
    assert (
        observed["requests"][0][1]["response_format"]["json_schema"]["strict"] is True
    )
    assert observed["abort_paths"] == []


def test_expired_task_makes_zero_provider_requests(runtime):
    observed, _ = runtime
    with pytest.raises(HTTPException) as error:
        execute(-1)
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert observed["requests"] == []


def test_foreign_inventory_request_is_not_aborted(runtime):
    observed, _ = runtime
    observed.update(mode="headers", inventory_match=False, remote_header=False)
    with pytest.raises(HTTPException) as error:
        execute()
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert observed["abort_paths"] == []


def test_child_inactivity_remains_provider_timeout(runtime, monkeypatch):
    observed, settings = runtime
    observed["mode"] = "silent"
    policy = ai_router.resolve_local_runtime_policy(
        QUALIFIED_MODEL_ALIAS, settings=settings
    )
    monkeypatch.setattr(
        ai_router,
        "resolve_local_runtime_policy",
        lambda *a, **k: (replace(policy, read_timeout_seconds=0.1)),
    )
    with pytest.raises(HTTPException) as error:
        execute(10)
    assert error.value.detail["failure_kind"] == "provider_timeout"
    assert "failure_code" not in error.value.detail
    assert observed["abort_paths"] == []


def test_slow_abort_rpc_cannot_escape_its_terminal_child_bound(runtime):
    observed, _ = runtime
    observed.update(mode="headers", slow_abort=True)
    start = time.monotonic()
    with pytest.raises(HTTPException) as error:
        execute()
    assert (
        error.value.detail["failure_code"]
        == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert time.monotonic() - start < 2.8
    assert len(observed["abort_paths"]) == 1


@pytest.mark.parametrize("remaining", [10, None])
def test_plain_nonstream_local_responses_preserve_output(runtime, remaining):
    observed, settings = runtime
    deadline = (
        build_accepted_chat_task_deadline(
            datetime.now(timezone.utc) - timedelta(seconds=720 - remaining)
        )
        if remaining is not None
        else None
    )
    output = ai_router.call_local(
        [{"role": "user", "content": "fixture"}],
        QUALIFIED_MODEL_ALIAS,
        settings=settings,
        accepted_deadline=deadline,
    )
    assert isinstance(output, ai_router.ProviderResponse)
    assert output == ANSWER
    assert "response_format" not in observed["requests"][0][1]
    assert observed["abort_paths"] == []
