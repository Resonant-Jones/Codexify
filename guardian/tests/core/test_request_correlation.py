"""Focused tests for bounded Codexify ⇄ Whoosh'd request correlation."""

from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from guardian.core import ai_router
from guardian.core import chat_completion_service
from guardian.core.ai_router import LocalModelResolution, call_local, stream_local
from guardian.core.chat_completion_service import ChatTaskCancelled
from guardian.core.completion_terminal import CompletionTerminalEvidence
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.providers.whooshd_control_plane import (
    parse_whooshd_response_correlation,
)
from guardian.tasks.types import ChatCompletionTask


class _Response:
    status_code = 200
    text = ""
    headers: dict[str, str] = {}

    def __init__(self, payload: dict, headers: dict[str, str] | None = None):
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def json(self):
        return self._payload

    def close(self):
        return None


class _StreamingResponse:
    status_code = 200
    text = ""

    def __init__(self, lines: list[bytes], headers: dict[str, str] | None = None):
        self._lines = lines
        self.headers = headers or {}

    def iter_lines(self, decode_unicode=False):
        _ = decode_unicode
        yield from self._lines

    def close(self):
        return None


class _BlockingStreamingResponse:
    status_code = 200
    text = ""

    def __init__(self):
        self.headers = {
            "X-Request-ID": "req-root-cancel",
            "X-Whooshd-Request-ID": "whooshd-local-cancel",
            "X-Codexify-Task-ID": "task-cancel",
            "X-Codexify-Attempt-ID": "attempt-cancel",
        }
        self.started = threading.Event()
        self.closed = threading.Event()
        self.json_called = False

    def json(self):
        self.json_called = True
        raise AssertionError("stream body must not be parsed before monitoring")

    def iter_lines(self, decode_unicode=False):
        _ = decode_unicode
        self.started.set()
        self.closed.wait(timeout=5)
        if False:  # pragma: no cover - keeps this a generator for the test
            yield b""

    def close(self):
        self.closed.set()


def _prepare_local(monkeypatch):
    monkeypatch.setattr(
        ai_router,
        "resolve_local_execution_model",
        lambda **_: LocalModelResolution(
            model="stub-model",
            source="test",
            strict=False,
        ),
    )
    monkeypatch.setattr(
        ai_router,
        "_resolve_local_base_candidates",
        lambda _settings: ["http://whooshd.test/v1"],
    )


def _settings():
    return SimpleNamespace(
        LOCAL_API_KEY="",
        LOCAL_BASE_URL="http://whooshd.test/v1",
        LOCAL_MAX_TOKENS=128,
        LOCAL_COMPAT_FIRST=False,
        LOCAL_PREFER_OPENAI_COMPAT=False,
        CODEXIFY_WHOOSHD_THREADWAKE_SEGMENTS_ENABLED=False,
    )


def test_ingress_ids_are_bounded_and_invalid_values_are_replaced():
    task = ChatCompletionTask(
        task_id="task with spaces",
        request_id="prompt sentinel",
        user_id="user-1",
        thread_id=1,
    )

    assert task.request_id != "prompt sentinel"
    assert task.request_id.startswith("req_")
    assert " " not in task.task_id
    assert len(task.request_id) <= 128
    assert len(task.task_id) <= 128


def test_task_serialization_preserves_root_task_and_attempt_ids():
    task = ChatCompletionTask(
        task_id="task-roundtrip",
        request_id="req-roundtrip",
        attempt_id="attempt-roundtrip",
        user_id="user-1",
        thread_id=1,
    )

    restored = ChatCompletionTask.from_dict(task.to_dict())

    assert restored.request_id == "req-roundtrip"
    assert restored.task_id == "task-roundtrip"
    assert restored.attempt_id == "attempt-roundtrip"


def test_each_provider_attempt_gets_a_new_id_without_changing_root(monkeypatch):
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )
    task = ChatCompletionTask(
        task_id="task-attempts",
        request_id="req-attempts",
        user_id="user-1",
        thread_id=1,
    )

    first = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[],
        provider="openai",
        model="model-1",
        bundle=None,
    )
    second = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[],
        provider="openai",
        model="model-1",
        bundle=None,
    )

    assert first.attempt_id != second.attempt_id
    assert task.request_id == "req-attempts"
    assert task.task_id == "task-attempts"


def test_local_provider_headers_preserve_root_task_and_attempt(monkeypatch):
    _prepare_local(monkeypatch)
    calls: dict[str, object] = {}

    def fake_post(url, json, headers, timeout):
        calls.update(url=url, json=json, headers=headers, timeout=timeout)
        return _Response({"choices": [{"message": {"content": "bounded"}}]})

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    result = call_local(
        [{"role": "user", "content": "prompt-sentinel"}],
        "stub-model",
        settings=_settings(),
        request_id="req-root-7",
        task_id="task-7",
        attempt_id="attempt-7",
    )

    assert result == "bounded"
    headers = calls["headers"]
    assert headers["X-Request-ID"] == "req-root-7"
    assert headers["X-Codexify-Task-ID"] == "task-7"
    assert headers["X-Codexify-Attempt-ID"] == "attempt-7"
    assert "prompt-sentinel" not in json.dumps(headers)


def test_streaming_provider_headers_preserve_ids(monkeypatch):
    _prepare_local(monkeypatch)
    calls: dict[str, object] = {}

    def fake_post(url, json, headers, stream, timeout):
        calls.update(
            url=url, json=json, headers=headers, stream=stream, timeout=timeout
        )
        return _StreamingResponse(
            [b'data: {"choices":[{"delta":{"content":"ok"}}]}', b"data: [DONE]"]
        )

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    assert list(
        stream_local(
            [{"role": "user", "content": "prompt-sentinel"}],
            "stub-model",
            settings=_settings(),
            request_id="req-root-8",
            task_id="task-8",
            attempt_id="attempt-8",
        )
    ) == ["ok"]
    headers = calls["headers"]
    assert headers["X-Request-ID"] == "req-root-8"
    assert headers["X-Codexify-Task-ID"] == "task-8"
    assert headers["X-Codexify-Attempt-ID"] == "attempt-8"


def test_streaming_cancellation_propagates_to_whooshd_local_request(monkeypatch):
    _prepare_local(monkeypatch)
    response = _BlockingStreamingResponse()
    cancel_requested = threading.Event()
    cancel_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post(url, **kwargs):
        if kwargs.get("stream"):
            return response
        cancel_calls.append((url, kwargs))
        return _Response({})

    monkeypatch.setattr(ai_router.requests, "post", fake_post)
    result: dict[str, object] = {}

    def consume():
        iterator = iter(
            stream_local(
                [{"role": "user", "content": "prompt-sentinel"}],
                "stub-model",
                settings=_settings(),
                request_id="req-root-cancel",
                task_id="task-cancel",
                attempt_id="attempt-cancel",
                cancel_check=cancel_requested.is_set,
            )
        )
        try:
            while True:
                next(iterator)
        except StopIteration as stop:
            result["terminal"] = stop.value

    consumer = threading.Thread(target=consume)
    consumer.start()
    assert response.started.wait(timeout=2)
    cancel_requested.set()
    consumer.join(timeout=3)

    assert not consumer.is_alive()
    terminal = result["terminal"]
    assert isinstance(terminal, CompletionTerminalEvidence)
    assert terminal.status is CompletionTerminalStatus.CANCELLED
    assert terminal.visible_output_emitted is False
    assert response.json_called is False
    assert cancel_calls[0][0] == (
        "http://whooshd.test/runtime/requests/whooshd-local-cancel/cancel"
    )
    assert cancel_calls[0][1]["headers"]["X-Request-ID"] == "req-root-cancel"
    assert "prompt-sentinel" not in json.dumps(cancel_calls)


def test_cancellation_finds_whooshd_id_before_stream_headers_arrive(monkeypatch):
    _prepare_local(monkeypatch)
    settings = _settings()
    settings.LOCAL_PROVIDER_VENDOR = "whooshd"
    response = _BlockingStreamingResponse()
    cancel_requested = threading.Event()
    initial_post_started = threading.Event()
    release_initial_post = threading.Event()
    cancel_seen = threading.Event()
    cancel_calls: list[tuple[str, dict[str, object]]] = []

    def fake_get(url, timeout):
        assert url == "http://whooshd.test/runtime/requests"
        _ = timeout
        return _Response(
            {
                "requests": [
                    {
                        "request_id": "whooshd-local-preheader",
                        "correlation_id": "req-root-preheader",
                        "codexify_task_id": "task-preheader",
                        "codexify_attempt_id": "attempt-preheader",
                        "status": "streaming",
                    }
                ]
            }
        )

    def fake_post(url, **kwargs):
        if kwargs.get("stream"):
            initial_post_started.set()
            release_initial_post.wait(timeout=3)
            return response
        cancel_calls.append((url, kwargs))
        cancel_seen.set()
        return _Response({})

    monkeypatch.setattr(ai_router.requests, "get", fake_get)
    monkeypatch.setattr(ai_router.requests, "post", fake_post)
    result: dict[str, object] = {}

    def consume():
        iterator = iter(
            stream_local(
                [{"role": "user", "content": "prompt-sentinel"}],
                "stub-model",
                settings=settings,
                request_id="req-root-preheader",
                task_id="task-preheader",
                attempt_id="attempt-preheader",
                cancel_check=cancel_requested.is_set,
            )
        )
        try:
            while True:
                next(iterator)
        except StopIteration as stop:
            result["terminal"] = stop.value

    consumer = threading.Thread(target=consume)
    consumer.start()
    assert initial_post_started.wait(timeout=2)
    cancel_requested.set()
    assert cancel_seen.wait(timeout=2)
    release_initial_post.set()
    consumer.join(timeout=3)

    assert not consumer.is_alive()
    terminal = result["terminal"]
    assert isinstance(terminal, CompletionTerminalEvidence)
    assert terminal.status is CompletionTerminalStatus.CANCELLED
    assert cancel_calls[0][0].endswith(
        "/runtime/requests/whooshd-local-preheader/cancel"
    )


def test_cancelled_local_terminal_uses_existing_task_cancellation_path(monkeypatch):
    def cancelled_stream(*_args, **_kwargs):
        if False:  # pragma: no cover - keeps this a generator
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.CANCELLED,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="cancelled",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", cancelled_stream)
    task = ChatCompletionTask(
        task_id="task-cancel-path",
        request_id="req-cancel-path",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(ChatTaskCancelled):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[],
            provider="local",
            model="stub-model",
            bundle=None,
        )


def test_response_correlation_accepts_only_bounded_machine_ids():
    response = _Response(
        {},
        headers={
            "X-Request-ID": "req-root-9",
            "X-Whooshd-Request-ID": "whooshd-local-9",
            "X-Codexify-Task-ID": "task-9",
            "X-Codexify-Attempt-ID": "attempt-9",
        },
    )
    assert parse_whooshd_response_correlation(response) == {
        "correlation_id": "req-root-9",
        "whooshd_request_id": "whooshd-local-9",
        "codexify_task_id": "task-9",
        "codexify_attempt_id": "attempt-9",
    }

    unsafe = _Response({}, headers={"X-Request-ID": "prompt secret"})
    assert parse_whooshd_response_correlation(unsafe) == {}


def _drain_stream(stream):
    tokens: list[str] = []
    iterator = iter(stream)
    while True:
        try:
            tokens.append(next(iterator))
        except StopIteration as stop:
            return tokens, stop.value


_FULL_RUNTIME_PROVENANCE = {
    "schema_version": "whooshd.runtime.v1",
    "runtime_kind": "stub",
    "adapter_name": "stub-adapter",
    "resolution_source": "configured_stub",
    "execution_mode": "stub",
    "streaming": True,
    "queued": False,
    "batched": False,
    "request_id": "whooshd-internal-7",
}
_FULL_RUNTIME_PROVENANCE_HEADER = json.dumps(_FULL_RUNTIME_PROVENANCE)

_SSE_OK = [
    b'data: {"choices":[{"delta":{"content":"ok"}}]}',
    b"data: [DONE]",
]


def test_stream_local_preserves_header_only_whooshd_request_id(monkeypatch):
    _prepare_local(monkeypatch)

    def fake_post(url, json, headers, stream, timeout):
        return _StreamingResponse(
            _SSE_OK,
            headers={
                "X-Whooshd-Request-ID": "whooshd-stream-only",
                "X-Request-ID": "req-stream-only",
            },
        )

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_settings(),
            request_id="req-stream-only",
            task_id="task-stream-only",
            attempt_id="attempt-stream-only",
        )
    )

    assert tokens == ["ok"]
    assert isinstance(terminal, CompletionTerminalEvidence)
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    # No runtime provenance block was emitted, so none is synthesized.
    assert terminal.runtime_provenance is None
    # Header-only Whoosh'd request ID survives stream termination.
    assert terminal.response_correlation == {
        "whooshd_request_id": "whooshd-stream-only",
        "correlation_id": "req-stream-only",
    }


def test_stream_local_keeps_full_runtime_provenance_and_correlation(monkeypatch):
    _prepare_local(monkeypatch)

    def fake_post(url, json, headers, stream, timeout):
        return _StreamingResponse(
            _SSE_OK,
            headers={
                "X-Whooshd-Runtime-Provenance": _FULL_RUNTIME_PROVENANCE_HEADER,
                "X-Whooshd-Request-ID": "whooshd-stream-full",
                "X-Request-ID": "req-stream-full",
            },
        )

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_settings(),
            request_id="req-stream-full",
            task_id="task-stream-full",
            attempt_id="attempt-stream-full",
        )
    )

    assert tokens == ["ok"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    # Complete provenance continues to be parsed and is not regressed.
    assert terminal.runtime_provenance is not None
    assert terminal.runtime_provenance["request_id"] == "whooshd-internal-7"
    assert terminal.runtime_provenance["whooshd_request_id"] == "whooshd-stream-full"
    # Independent response correlation is still captured alongside provenance.
    assert terminal.response_correlation == {
        "whooshd_request_id": "whooshd-stream-full",
        "correlation_id": "req-stream-full",
    }


def test_stream_local_does_not_synthesize_correlation_without_headers(monkeypatch):
    _prepare_local(monkeypatch)

    def fake_post(url, json, headers, stream, timeout):
        return _StreamingResponse(_SSE_OK)

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_settings(),
        )
    )

    assert tokens == ["ok"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    assert terminal.runtime_provenance is None
    # No headers means no correlation and no fabricated identifier.
    assert terminal.response_correlation is None


def test_stream_terminal_response_correlation_reaches_completion_attempt(monkeypatch):
    terminal = CompletionTerminalEvidence(
        status=CompletionTerminalStatus.SUCCESS,
        visible_output_emitted=True,
        explicit_provider_terminal_observed=True,
        finish_reason="stop",
        transport_ended_cleanly=True,
        provider="local",
        model="stub-model",
        response_correlation={"whooshd_request_id": "whooshd-plumbing-1"},
    )

    def fake_stream(*_args, **_kwargs):
        if False:  # pragma: no cover - keeps this a generator
            yield ""
        return terminal

    monkeypatch.setattr(chat_completion_service, "stream_local", fake_stream)
    task = ChatCompletionTask(
        task_id="task-plumbing",
        request_id="req-plumbing",
        user_id="user-1",
        thread_id=1,
    )

    attempt = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[{"role": "user", "content": "hi"}],
        provider="local",
        model="stub-model",
        bundle=None,
    )

    assert attempt.response_correlation == {"whooshd_request_id": "whooshd-plumbing-1"}


class _RejectedStreamResponse:
    """A non-streaming-shaped response used for rejected candidate attempts."""

    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self.text = ""
        self._body = body or {}
        self.headers: dict[str, str] = {}
        self.closed = False

    def json(self):
        return self._body

    def iter_lines(self, decode_unicode=False):
        _ = decode_unicode
        return iter(())

    def close(self):
        self.closed = True


class _RecordingCancelMonitor(ai_router._WhooshdCancellationMonitor):
    """Records lifecycle calls so tests can prove rejected monitors are stopped."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_calls = 0
        self.set_response_calls = 0

    def set_response(self, response):
        self.set_response_calls += 1
        return super().set_response(response)

    def stop(self):
        self.stop_calls += 1
        return super().stop()

    def thread_is_alive(self):
        return self._thread.is_alive()


def _install_recording_monitors(monkeypatch):
    created: list[_RecordingCancelMonitor] = []

    def factory(**kwargs):
        monitor = _RecordingCancelMonitor(**kwargs)
        created.append(monitor)
        return monitor

    monkeypatch.setattr(ai_router, "_WhooshdCancellationMonitor", factory)
    return created


def _whooshd_vendor_settings():
    settings = _settings()
    settings.LOCAL_PROVIDER_VENDOR = "whooshd"
    return settings


def _prepare_local_fallback(monkeypatch):
    monkeypatch.setattr(
        ai_router,
        "resolve_local_execution_model",
        lambda **_: LocalModelResolution(
            model="stub-model",
            source="test",
            strict=False,
        ),
    )
    # Non-/v1 base so /api/chat and /v1/chat/completions are both candidates.
    monkeypatch.setattr(
        ai_router,
        "_resolve_local_base_candidates",
        lambda _settings: ["http://whooshd.test"],
    )


def test_rejected_candidate_stops_cancellation_monitor_before_fallback(monkeypatch):
    _prepare_local_fallback(monkeypatch)
    created = _install_recording_monitors(monkeypatch)
    accepted: dict[str, object] = {}

    def fake_post(url, **kwargs):
        if "/api/chat" in url:
            return _RejectedStreamResponse(404)
        accepted["url"] = url
        return _StreamingResponse(
            _SSE_OK,
            headers={"X-Whooshd-Request-ID": "whooshd-accepted-1"},
        )

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_whooshd_vendor_settings(),
            request_id="req-fallback-1",
            task_id="task-fallback-1",
            attempt_id="attempt-fallback-1",
            cancel_check=lambda: False,
        )
    )

    assert tokens == ["ok"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    assert accepted["url"].endswith("/v1/chat/completions")
    # Two candidate monitors were created (one per candidate URL).
    assert len(created) == 2
    # Only the accepted response's monitor is promoted via set_response.
    assert sum(m.set_response_calls for m in created) == 1
    assert created[1].set_response_calls == 1
    assert created[0].set_response_calls == 0
    # Every candidate monitor (rejected + accepted) is stopped, leaving no
    # daemon polling thread behind after the fallback succeeds.
    assert all(m.stop_calls >= 1 for m in created)
    assert all(not m.thread_is_alive() for m in created)
    # Accepted stream still carries live Whoosh'd correlation.
    assert terminal.response_correlation == {"whooshd_request_id": "whooshd-accepted-1"}


def test_candidate_monitor_stopped_on_transport_exception_before_acceptance(monkeypatch):
    _prepare_local_fallback(monkeypatch)
    created = _install_recording_monitors(monkeypatch)
    accepted: dict[str, object] = {}

    def fake_post(url, **kwargs):
        if "/api/chat" in url:
            raise ai_router.req_exc.ConnectionError("boom")
        accepted["url"] = url
        return _StreamingResponse(_SSE_OK)

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_whooshd_vendor_settings(),
            cancel_check=lambda: False,
        )
    )

    assert tokens == ["ok"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    assert accepted["url"].endswith("/v1/chat/completions")
    assert len(created) == 2
    # The rejected (exception) candidate never reaches acceptance, and only the
    # accepted candidate's monitor is promoted.
    assert created[0].set_response_calls == 0
    assert created[1].set_response_calls == 1
    assert all(m.stop_calls >= 1 for m in created)
    assert all(not m.thread_is_alive() for m in created)


def test_candidate_monitor_stopped_on_retryable_status_before_acceptance(monkeypatch):
    _prepare_local_fallback(monkeypatch)
    created = _install_recording_monitors(monkeypatch)

    def fake_post(url, **kwargs):
        if "/api/chat" in url:
            # Non-2xx, non-404, non-whooshd-error: exercises the generic
            # retryable-status rejection path.
            return _RejectedStreamResponse(503, body={"error": "unavailable"})
        return _StreamingResponse(_SSE_OK)

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_whooshd_vendor_settings(),
            cancel_check=lambda: False,
        )
    )

    assert tokens == ["ok"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    assert len(created) == 2
    assert created[0].set_response_calls == 0
    assert created[1].set_response_calls == 1
    assert all(m.stop_calls >= 1 for m in created)
    assert all(not m.thread_is_alive() for m in created)


def test_all_rejected_candidates_stop_their_cancellation_monitors(monkeypatch):
    _prepare_local_fallback(monkeypatch)
    created = _install_recording_monitors(monkeypatch)

    def fake_post(url, **kwargs):
        return _RejectedStreamResponse(404)

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    with pytest.raises(HTTPException):
        list(
            stream_local(
                [{"role": "user", "content": "hi"}],
                "stub-model",
                settings=_whooshd_vendor_settings(),
                cancel_check=lambda: False,
            )
        )

    # Every candidate was rejected, so every candidate monitor is stopped and
    # none is promoted as the active cancellation monitor.
    assert len(created) >= 1
    assert all(m.set_response_calls == 0 for m in created)
    assert all(m.stop_calls >= 1 for m in created)
    assert all(not m.thread_is_alive() for m in created)
