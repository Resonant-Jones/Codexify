from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from guardian.tasks.types import ChatCompletionTask, TaskLifecycleState
from guardian.core.completion_terminal import CompletionTerminalEvidence
from guardian.protocol_tokens import CompletionTerminalStatus
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
        yield from self._tokens
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.SUCCESS,
            visible_output_emitted=bool(self._tokens),
            explicit_provider_terminal_observed=True,
            finish_reason="stop",
            transport_ended_cleanly=True,
            provider="local",
            model="test-model",
        )

    def close(self):
        return None


def _isolate_turn_anchor(monkeypatch) -> _FakeRedis:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)
    return fake_redis


def _build_task(
    *,
    task_id: str,
    thread_id: int = 7,
    provider: str = "local",
    model: str = "test-model",
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id=task_id,
        thread_id=thread_id,
        provider=provider,
        model=model,
        selection_source="explicit",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
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
        monkeypatch.setattr(
            chat_worker._chat_completion_service,
            "stream_local",
            lambda *_args, **_kwargs: _TokenStream(stream_tokens),
        )
    else:

        def _unexpected_stream_local(*_args, **_kwargs):
            raise AssertionError("stream_local should not be used")

        monkeypatch.setattr(
            chat_worker,
            "stream_local",
            _unexpected_stream_local,
        )
        monkeypatch.setattr(
            chat_worker._chat_completion_service,
            "stream_local",
            _unexpected_stream_local,
        )

    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_args, **_kwargs: assistant_text,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: assistant_text,
    )

    return published


def test_chat_worker_emits_chunk_events_for_streaming_local_flow(monkeypatch):
    published = _prepare_worker_harness(
        monkeypatch,
        provider="local",
        model="test-model",
        stream_tokens=["Hel", "lo"],
    )
    task = _build_task(task_id="task-streaming")

    chat_worker._run_chat_task(task)

    state_sequence = [
        payload["state"]
        for event_type, payload in published
        if event_type == "task.state"
    ]
    assert state_sequence == [
        TaskLifecycleState.QUEUED.value,
        TaskLifecycleState.AWAITING_MODEL.value,
        TaskLifecycleState.AWAITING_FIRST_TOKEN.value,
        TaskLifecycleState.STREAMING.value,
        TaskLifecycleState.COMPLETED.value,
    ]

    chunk_payloads = [
        payload for event_type, payload in published if event_type == "task.chunk"
    ]
    assert [payload["delta"] for payload in chunk_payloads] == ["Hel", "lo"]
    assert chunk_payloads[0]["thread_id"] == task.thread_id
    assert chunk_payloads[0]["task_id"] == task.task_id
    assert chunk_payloads[0]["turn_id"] == TURN_ID

    event_types = [event_type for event_type, _payload in published]
    assert "task.progress" in event_types
    assert event_types[-1] == "task.completed"
    assert published[-1][1]["message_id"] == 42


def test_chat_worker_does_not_fabricate_chunks_for_non_streaming_flow(
    monkeypatch,
):
    published = _prepare_worker_harness(
        monkeypatch,
        provider="openai",
        model="gpt-5.4-mini",
        stream_tokens=None,
        assistant_text="Final answer",
    )
    task = _build_task(
        task_id="task-non-streaming",
        provider="openai",
        model="gpt-5.4-mini",
    )

    chat_worker._run_chat_task(task)

    assert [
        payload["state"]
        for event_type, payload in published
        if event_type == "task.state"
    ] == [
        TaskLifecycleState.QUEUED.value,
        TaskLifecycleState.AWAITING_MODEL.value,
        TaskLifecycleState.AWAITING_FIRST_TOKEN.value,
        TaskLifecycleState.STREAMING.value,
        TaskLifecycleState.COMPLETED.value,
    ]
    assert not any(event_type == "task.chunk" for event_type, _payload in published)
    assert any(event_type == "task.completed" for event_type, _payload in published)


def test_pre_output_fallback_success_persists_exactly_one_assistant(monkeypatch):
    published = _prepare_worker_harness(
        monkeypatch,
        provider="groq",
        model="cloud-model",
        stream_tokens=["rescued"],
    )
    task = _build_task(
        task_id="task-pre-output-fallback",
        provider="groq",
        model="cloud-model",
    )
    task.selection_source = "default"
    task.provider_pinned = False
    persisted: list[str] = []
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda _thread_id, _role, text: persisted.append(text) or 42,
            write_audit_log=lambda *_args, **_kwargs: None,
        ),
    )
    cloud_error = HTTPException(
        status_code=502,
        detail={"failure_kind": "provider_unavailable"},
    )

    def _cloud_fails(*_args, **_kwargs):
        raise cloud_error

    monkeypatch.setattr(chat_worker, "chat_with_ai", _cloud_fails)
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "chat_with_ai",
        _cloud_fails,
    )
    monkeypatch.setattr(
        chat_worker,
        "_fallback_provider_candidates",
        lambda **_kwargs: [("local", "test-model")],
    )

    chat_worker._run_chat_task(task)

    assert persisted == ["rescued"]
    assert [event for event, _payload in published].count("task.completed") == 1


def test_failure_after_visible_chunk_forbids_fallback_and_persistence(
    monkeypatch,
):
    published = _prepare_worker_harness(
        monkeypatch,
        provider="local",
        model="test-model",
        stream_tokens=["unused"],
    )
    task = _build_task(task_id="task-visible-failure")
    task.selection_source = "default"
    task.provider_pinned = False
    persisted: list[str] = []
    fallback_calls: list[str] = []

    def _partial_then_error():
        yield "partial"
        raise HTTPException(
            status_code=502,
            detail={"failure_kind": "provider_unavailable"},
        )

    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "stream_local",
        lambda *_args, **_kwargs: _partial_then_error(),
    )
    monkeypatch.setattr(
        chat_worker,
        "_fallback_provider_candidates",
        lambda **_kwargs: [("groq", "fallback-model")],
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: fallback_calls.append("called") or "fallback",
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda *_args, **_kwargs: persisted.append("created") or 42,
            write_audit_log=lambda *_args, **_kwargs: None,
        ),
    )

    chat_worker._run_chat_task(task)

    event_types = [event for event, _payload in published]
    assert "task.failed" in event_types
    assert "task.completed" not in event_types
    assert fallback_calls == []
    assert persisted == []
