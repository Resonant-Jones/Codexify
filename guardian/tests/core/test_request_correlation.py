"""Focused tests for bounded Codexify ⇄ Whoosh'd request correlation."""

from __future__ import annotations

import json
from types import SimpleNamespace

from guardian.core import ai_router
from guardian.core import chat_completion_service
from guardian.core.ai_router import LocalModelResolution, call_local, stream_local
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
