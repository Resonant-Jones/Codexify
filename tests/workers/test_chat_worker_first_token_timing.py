from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from guardian.core.chat_completion_service import ChatTaskCancelled
from guardian.tasks.types import ChatCompletionTask, TaskLifecycleState
from guardian.workers import chat_worker

TURN_ID = "11111111-1111-4111-8111-111111111111"


class _FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}

    def setex(self, name: str, _ttl: int, value: str) -> bool:
        self._values[name] = str(value).encode("utf-8")
        return True

    def get(self, name: str) -> bytes | None:
        return self._values.get(name)


class _TokenStream:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = list(tokens)

    def __iter__(self):
        return iter(self._tokens)

    def close(self):
        return None


def _isolate_turn_anchor(monkeypatch) -> _FakeRedis:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)
    return fake_redis


def _timestamp_sequence(*values: str):
    remaining = list(values)
    last = values[-1]

    def _next() -> str:
        nonlocal last
        if remaining:
            last = remaining.pop(0)
        return last

    return _next


def _build_task(
    *,
    task_id: str = "task-first-token-timing",
    thread_id: int = 7,
    provider: str = "local",
    model: str = "test-model",
    created_at: str = "2026-04-02T00:00:00+00:00",
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id=task_id,
        thread_id=thread_id,
        provider=provider,
        model=model,
        selection_source="explicit",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
        created_at=created_at,
    )
    task.turn_id = TURN_ID
    task.turn_lock_owner = task_id
    return task


def _prepare_worker_harness(
    monkeypatch,
    *,
    provider: str,
    model: str,
    stream_tokens: list[str] | None = None,
    assistant_text: str = "Hello world",
    chat_with_ai_exc: Exception | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    published: list[tuple[str, dict[str, Any]]] = []
    _isolate_turn_anchor(monkeypatch)

    mock_db = SimpleNamespace(
        create_message=lambda *_args, **_kwargs: 42,
        write_audit_log=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        )
        or {"ok": True},
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_for_turn",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_message_extra_meta",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *_, **__: None)
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "build_sanitized_payload_summary",
        lambda *args, **kwargs: {"message_count": 2},
    )
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider_name, settings, **kwargs: {
            "provider": provider_name,
            **kwargs,
        },
    )
    monkeypatch.setattr(
        chat_worker,
        "_fallback_provider_candidates",
        lambda **_kwargs: [],
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            provider,
            model,
            {},
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)

    if stream_tokens is not None:
        monkeypatch.setattr(
            chat_worker,
            "stream_local",
            lambda *_args, **_kwargs: _TokenStream(stream_tokens),
        )
    else:
        monkeypatch.setattr(
            chat_worker,
            "stream_local",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("stream_local should not be used")
            ),
        )

    if chat_with_ai_exc is not None:
        monkeypatch.setattr(
            chat_worker,
            "chat_with_ai",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(chat_with_ai_exc),
        )
    else:
        monkeypatch.setattr(
            chat_worker,
            "chat_with_ai",
            lambda *_args, **_kwargs: assistant_text,
        )

    return published


def test_chat_worker_stamps_chronological_timing_fields_for_streaming_flow(
    monkeypatch,
):
    monkeypatch.setattr(
        chat_worker,
        "_utc_now_iso",
        _timestamp_sequence(
            "2026-04-02T00:00:01+00:00",
            "2026-04-02T00:00:02+00:00",
            "2026-04-02T00:00:03+00:00",
            "2026-04-02T00:00:04+00:00",
        ),
    )
    published = _prepare_worker_harness(
        monkeypatch,
        provider="local",
        model="test-model",
        stream_tokens=["Hel", "lo"],
    )
    task = _build_task(provider="local")

    chat_worker._run_chat_task(task)

    state_events = [
        payload
        for event_type, payload in published
        if event_type == "task.state"
    ]
    state_by_name = {payload["state"]: payload for payload in state_events}

    assert state_by_name[TaskLifecycleState.QUEUED.value]["queued_at"] == (
        task.created_at
    )
    assert (
        state_by_name[TaskLifecycleState.AWAITING_MODEL.value][
            "awaiting_model_at"
        ]
        == "2026-04-02T00:00:01+00:00"
    )
    assert (
        state_by_name[TaskLifecycleState.AWAITING_FIRST_TOKEN.value][
            "awaiting_first_token_at"
        ]
        == "2026-04-02T00:00:02+00:00"
    )
    assert (
        state_by_name[TaskLifecycleState.STREAMING.value]["first_token_at"]
        == "2026-04-02T00:00:03+00:00"
    )
    assert (
        state_by_name[TaskLifecycleState.STREAMING.value]["first_output_at"]
        == "2026-04-02T00:00:03+00:00"
    )
    assert (
        state_by_name[TaskLifecycleState.COMPLETED.value]["completed_at"]
        == "2026-04-02T00:00:04+00:00"
    )

    terminal_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert terminal_payload["queued_at"] == task.created_at
    assert terminal_payload["awaiting_model_at"] == (
        "2026-04-02T00:00:01+00:00"
    )
    assert terminal_payload["awaiting_first_token_at"] == (
        "2026-04-02T00:00:02+00:00"
    )
    assert terminal_payload["first_token_at"] == ("2026-04-02T00:00:03+00:00")
    assert terminal_payload["first_output_at"] == ("2026-04-02T00:00:03+00:00")
    assert terminal_payload["completed_at"] == ("2026-04-02T00:00:04+00:00")
    assert terminal_payload["trace"]["queued_at"] == task.created_at
    assert terminal_payload["trace"]["first_token_at"] == (
        "2026-04-02T00:00:03+00:00"
    )

    assert (
        terminal_payload["queued_at"]
        < terminal_payload["awaiting_model_at"]
        < terminal_payload["awaiting_first_token_at"]
        < terminal_payload["first_token_at"]
        <= terminal_payload["completed_at"]
    )


def test_chat_worker_uses_first_output_only_for_body_completion(
    monkeypatch,
):
    monkeypatch.setattr(
        chat_worker,
        "_utc_now_iso",
        _timestamp_sequence(
            "2026-04-02T00:00:01+00:00",
            "2026-04-02T00:00:02+00:00",
            "2026-04-02T00:00:03+00:00",
            "2026-04-02T00:00:04+00:00",
        ),
    )
    published = _prepare_worker_harness(
        monkeypatch,
        provider="groq",
        model="test-model",
        assistant_text="Hello world",
    )
    task = _build_task(provider="groq")

    chat_worker._run_chat_task(task)

    state_by_name = {
        payload["state"]: payload
        for event_type, payload in published
        if event_type == "task.state"
    }
    assert TaskLifecycleState.STREAMING.value in state_by_name
    assert (
        "first_token_at"
        not in state_by_name[TaskLifecycleState.STREAMING.value]
    )
    assert (
        state_by_name[TaskLifecycleState.STREAMING.value]["first_output_at"]
        == "2026-04-02T00:00:03+00:00"
    )

    terminal_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert terminal_payload["awaiting_model_at"] == (
        "2026-04-02T00:00:01+00:00"
    )
    assert terminal_payload["awaiting_first_token_at"] == (
        "2026-04-02T00:00:02+00:00"
    )
    assert "first_token_at" not in terminal_payload
    assert terminal_payload["first_output_at"] == ("2026-04-02T00:00:03+00:00")
    assert terminal_payload["completed_at"] == ("2026-04-02T00:00:04+00:00")
    assert terminal_payload["trace"]["first_output_at"] == (
        "2026-04-02T00:00:03+00:00"
    )


@pytest.mark.parametrize(
    ("error", "terminal_event"),
    [
        (RuntimeError("provider crashed"), "task.failed"),
        (ChatTaskCancelled("task_cancelled"), "task.cancelled"),
    ],
)
def test_chat_worker_does_not_fabricate_first_token_timing_on_terminal_error(
    monkeypatch,
    error: Exception,
    terminal_event: str,
):
    monkeypatch.setattr(
        chat_worker,
        "_utc_now_iso",
        _timestamp_sequence(
            "2026-04-02T00:00:01+00:00",
            "2026-04-02T00:00:02+00:00",
            "2026-04-02T00:00:03+00:00",
        ),
    )
    published = _prepare_worker_harness(
        monkeypatch,
        provider="groq",
        model="test-model",
        chat_with_ai_exc=error,
    )
    task = _build_task(provider="groq")

    chat_worker._run_chat_task(task)

    state_by_name = {
        payload["state"]: payload
        for event_type, payload in published
        if event_type == "task.state"
    }
    assert TaskLifecycleState.AWAITING_MODEL.value in state_by_name
    assert TaskLifecycleState.AWAITING_FIRST_TOKEN.value in state_by_name
    assert TaskLifecycleState.STREAMING.value not in state_by_name

    terminal_payload = next(
        payload
        for event_type, payload in published
        if event_type == terminal_event
    )
    assert terminal_payload["queued_at"] == task.created_at
    assert terminal_payload["awaiting_model_at"] == (
        "2026-04-02T00:00:01+00:00"
    )
    assert terminal_payload["awaiting_first_token_at"] == (
        "2026-04-02T00:00:02+00:00"
    )
    assert "first_token_at" not in terminal_payload
    assert "first_output_at" not in terminal_payload
    assert terminal_payload["completed_at"] == ("2026-04-02T00:00:03+00:00")
