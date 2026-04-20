import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from guardian.core.config import Settings
from guardian.tasks.types import ChatCompletionTask
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


def _isolate_turn_anchor(monkeypatch) -> _FakeRedis:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)
    return fake_redis


def _build_task(
    *, thread_id: int = 11, turn_id: str = TURN_ID
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        thread_id=thread_id,
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
    )
    task.turn_id = turn_id
    task.turn_lock_owner = f"lock-{thread_id}"
    return task


def _stubbed_success_setup(monkeypatch):
    published: list[tuple[str, dict]] = []
    _isolate_turn_anchor(monkeypatch)

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_safe_emit_live_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_a, **_k: {
            "message_id": 501,
            "provider": "groq",
            "model": "moonshotai/kimi-k2-instruct-0905",
        },
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    return published


def test_metadata_persistence_false_is_non_fatal(monkeypatch, caplog):
    published = _stubbed_success_setup(monkeypatch)
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: False,
    )

    with caplog.at_level(logging.WARNING):
        chat_worker._run_chat_task(_build_task())

    event_types = [event_type for event_type, _payload in published]
    assert "task.completed" in event_types
    assert "task.failed" not in event_types
    assert any(
        "turn_id_metadata_persist_failed reason=persist_returned_false"
        in record.message
        for record in caplog.records
    )


def test_metadata_persistence_exception_is_non_fatal(monkeypatch, caplog):
    published = _stubbed_success_setup(monkeypatch)

    def _raise_persist(**_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        _raise_persist,
    )

    with caplog.at_level(logging.WARNING):
        chat_worker._run_chat_task(_build_task())

    event_types = [event_type for event_type, _payload in published]
    assert "task.completed" in event_types
    assert "task.failed" not in event_types
    assert any(
        "turn_id_metadata_persist_failed reason=exception" in record.message
        for record in caplog.records
    )


def test_retry_after_metadata_failure_reuses_cached_turn_anchor(monkeypatch):
    published: list[tuple[str, dict]] = []
    fake_redis = _isolate_turn_anchor(monkeypatch)
    completion_calls = {"count": 0}

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_safe_emit_live_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: False,
    )

    def _run_completion(*_args, **_kwargs):
        completion_calls["count"] += 1
        return {
            "message_id": 501,
            "provider": "groq",
            "model": "moonshotai/kimi-k2-instruct-0905",
        }

    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", _run_completion
    )

    chat_worker._run_chat_task(_build_task(thread_id=29, turn_id=TURN_ID))
    retry_task = ChatCompletionTask(
        user_id="local",
        task_id="task-retry",
        thread_id=29,
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
    )
    retry_task.turn_id = TURN_ID
    retry_task.turn_lock_owner = "lock-retry"
    chat_worker._run_chat_task(retry_task)

    assert completion_calls["count"] == 1
    completed_payloads = [
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    ]
    assert len(completed_payloads) == 2
    assert completed_payloads[-1].get("message_id") == 501
    assert completed_payloads[-1].get("selection_source") == "turn_id_dedupe"
    assert all(event_type != "task.failed" for event_type, _ in published)


def test_worker_failure_before_assistant_emit_marks_failed_and_emits_completion_error(
    monkeypatch,
):
    published: list[tuple[str, dict]] = []
    mirrored_live_events: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda event_type, payload: mirrored_live_events.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )

    def _raise_failure(*_a, **_k):
        raise RuntimeError("provider crashed")

    monkeypatch.setattr(chat_worker, "run_chat_completion_task", _raise_failure)

    task = _build_task(thread_id=17)
    chat_worker._run_chat_task(task)

    assert any(event_type == "task.failed" for event_type, _ in published)
    assert any(
        event_type == "completion.error"
        for event_type, _ in mirrored_live_events
    )
    completion_error_payload = next(
        payload
        for event_type, payload in mirrored_live_events
        if event_type == "completion.error"
    )
    assert completion_error_payload.get("task_id") == task.task_id
    assert completion_error_payload.get("thread_id") == 17


def test_auto_cloud_failure_rescues_to_local_once(monkeypatch):
    mock_db = MagicMock()
    mock_db.create_message.return_value = 321
    mock_db.write_audit_log = MagicMock()
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *a, **k: None)
    persisted_extra_meta: dict[str, object] = {}
    monkeypatch.setattr(
        chat_worker,
        "_persist_message_extra_meta",
        lambda **kwargs: persisted_extra_meta.update(kwargs) or True,
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "groq",
            "moonshotai/kimi-k2-instruct-0905",
            {},
            None,
            None,
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker,
        "get_settings",
        lambda: Settings(
            LLM_PROVIDER="local",
            ALLOW_CLOUD_PROVIDERS=True,
            CODEXIFY_LOCAL_ONLY_MODE=False,
            CODEXIFY_EGRESS_ALLOWLIST="groq,openai,minimax",
            LOCAL_LLM_MODEL="qwen3.5:27b",
            DEFAULT_LOCAL_MODEL="qwen3.5:27b",
            LLM_MODEL="qwen3.5:27b",
            GROQ_API_KEY="groq-key",
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "first_model_for_provider",
        lambda provider_id, settings=None: "qwen3.5:27b"
        if provider_id == "local"
        else None,
    )

    class _EmptyStream:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _EmptyStream()
    )

    def _chat_with_ai(_messages, *, model=None, provider=None, **_kwargs):
        if provider == "groq":
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "provider_request_failed",
                    "provider": "groq",
                    "model": model,
                    "upstream_status": 404,
                    "failure_kind": "http_error",
                    "message": "Groq request failed (404): not found",
                },
            )
        return "rescued locally"

    monkeypatch.setattr(chat_worker, "chat_with_ai", _chat_with_ai)

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
        selection_source="default",
        provider_pinned=False,
    )

    result = chat_worker._run_chat_completion_task_compat(task)

    assert result["provider"] == "local"
    assert result["model"] == "qwen3.5:27b"
    assert result["attempted_provider"] == "groq"
    assert result["upstream_status"] == 404
    assert result["fallback_reason"] == "cloud_failure_local_rescue"
    assert result["execution"] == {
        "attempted_provider": "groq",
        "attempted_model": "moonshotai/kimi-k2-instruct-0905",
        "final_provider": "local",
        "final_model": "qwen3.5:27b",
        "fallback_triggered": True,
    }
    assert result["completion_truth"] == {
        "accepted": True,
        "attempted": True,
        "fallback_attempted": True,
        "executed": True,
        "completed": True,
    }
    assert result["attempted_provider_truth"]["attempted"] is True
    assert result["final_provider_truth"]["completed"] is True
    assert mock_db.create_message.call_args[0][2] == "rescued locally"
    assert persisted_extra_meta["payload"]["execution"] == {
        "attempted_provider": "groq",
        "attempted_model": "moonshotai/kimi-k2-instruct-0905",
        "final_provider": "local",
        "final_model": "qwen3.5:27b",
        "fallback_triggered": True,
    }


def test_completion_result_includes_execution_metadata_without_fallback(
    monkeypatch,
):
    mock_db = MagicMock()
    mock_db.create_message.return_value = 322
    mock_db.write_audit_log = MagicMock()
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *a, **k: None)
    persisted_extra_meta: dict[str, object] = {}
    monkeypatch.setattr(
        chat_worker,
        "_persist_message_extra_meta",
        lambda **kwargs: persisted_extra_meta.update(kwargs) or True,
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    class _EmptyStream:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _EmptyStream()
    )
    monkeypatch.setattr(chat_worker, "chat_with_ai", lambda *_a, **_k: "ready")

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
    )

    result = chat_worker._run_chat_completion_task_compat(task)

    assert result["execution"] == {
        "attempted_provider": "local",
        "attempted_model": "qwen3.5:27b",
        "final_provider": "local",
        "final_model": "qwen3.5:27b",
        "fallback_triggered": False,
    }
    assert persisted_extra_meta["payload"]["execution"] == {
        "attempted_provider": "local",
        "attempted_model": "qwen3.5:27b",
        "final_provider": "local",
        "final_model": "qwen3.5:27b",
        "fallback_triggered": False,
    }


def test_explicit_provider_failure_does_not_rescue(monkeypatch):
    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "groq",
            "moonshotai/kimi-k2-instruct-0905",
            {},
            None,
            None,
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker,
        "get_settings",
        lambda: Settings(
            LLM_PROVIDER="local",
            ALLOW_CLOUD_PROVIDERS=True,
            CODEXIFY_LOCAL_ONLY_MODE=False,
            CODEXIFY_EGRESS_ALLOWLIST="groq,openai,minimax",
            LOCAL_LLM_MODEL="qwen3.5:27b",
            DEFAULT_LOCAL_MODEL="qwen3.5:27b",
            LLM_MODEL="qwen3.5:27b",
            GROQ_API_KEY="groq-key",
        ),
    )
    monkeypatch.setattr(chat_worker, "stream_local", lambda *a, **k: iter(()))
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_a, **_k: (_ for _ in ()).throw(
            HTTPException(
                status_code=502,
                detail={
                    "error": "provider_request_failed",
                    "provider": "groq",
                    "model": "moonshotai/kimi-k2-instruct-0905",
                    "upstream_status": 404,
                    "failure_kind": "http_error",
                    "message": "Groq request failed (404): not found",
                },
            )
        ),
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
        selection_source="explicit",
        provider_pinned=True,
    )

    try:
        chat_worker._run_chat_completion_task_compat(task)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 502
        assert exc.detail["provider"] == "groq"


def test_generation_success_but_persistence_failure_is_non_authoritative(
    monkeypatch,
):
    mock_db = MagicMock()
    mock_db.create_message.side_effect = RuntimeError("db down")
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)

    class _EmptyStream:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _EmptyStream()
    )
    monkeypatch.setattr(chat_worker, "chat_with_ai", lambda *_a, **_k: "ready")

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
    )

    try:
        chat_worker._run_chat_completion_task_compat(task)
        assert False, "expected AssistantPersistenceError"
    except chat_worker.AssistantPersistenceError as exc:
        assert exc.metadata["error"] == "assistant_message_persist_failed"
        assert exc.metadata["final_provider"] == "local"
        assert exc.metadata["persistence_outcome"] == "failed"
        assert exc.metadata["completion_truth"]["executed"] is True
        assert exc.metadata["completion_truth"]["completed"] is False


def test_extract_assistant_response_strips_structured_scratchpad():
    raw = (
        "=== SCRATCHPAD ===\n"
        "% System Note === internal\n"
        "% User Note === internal\n"
        "% System Response === Hello!\n"
    )
    assert chat_worker.extract_assistant_response(raw) == "Hello!"

    raw_fallback = "header\n" "=== SCRATCHPAD ===\n" "Final visible reply"
    assert (
        chat_worker.extract_assistant_response(raw_fallback)
        == "Final visible reply"
    )


def test_completion_persists_stripped_response_boundary(monkeypatch):
    mock_db = MagicMock()
    mock_db.create_message.return_value = 321
    mock_db.write_audit_log = MagicMock()
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *a, **k: None)

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker,
        "get_settings",
        lambda: Settings(
            LLM_PROVIDER="local",
            ALLOW_CLOUD_PROVIDERS=True,
            CODEXIFY_LOCAL_ONLY_MODE=False,
            CODEXIFY_EGRESS_ALLOWLIST="groq,openai,minimax",
            LOCAL_LLM_MODEL="qwen3.5:27b",
            DEFAULT_LOCAL_MODEL="qwen3.5:27b",
            LLM_MODEL="qwen3.5:27b",
        ),
    )

    class _EmptyStream:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _EmptyStream()
    )
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_a, **_k: (
            "=== SCRATCHPAD ===\n"
            "% System Note === internal\n"
            "% User Note === internal\n"
            "% System Response === Hello!\n"
        ),
    )

    callback_tokens: list[str] = []
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
    )

    result = chat_worker._run_chat_completion_task_compat(
        task,
        token_callback=callback_tokens.append,
    )

    assert result["assistant_text"] == "Hello!"
    assert callback_tokens == ["Hello!"]
    assert mock_db.create_message.call_args[0][2] == "Hello!"


def test_stream_completion_ignores_reasoning_chunks(monkeypatch):
    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    class _ChunkStream:
        def __iter__(self):
            return iter(
                [
                    {"delta": {"thinking": "private", "content": "Hello"}},
                    {"delta": {"thinking": "hidden"}},
                    {"delta": {"content": " world"}},
                ]
            )

        def close(self):
            return None

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _ChunkStream()
    )

    callback_tokens: list[str] = []
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
    )

    result = chat_worker._run_chat_completion_task_compat(
        task,
        token_callback=callback_tokens.append,
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "Hello world"
    assert callback_tokens == ["Hello", " world"]
    assert "thinking" not in result
    assert "reasoning" not in result


def test_completion_fallback_response_ignores_reasoning_fields(monkeypatch):
    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    class _EmptyStream:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker, "stream_local", lambda *a, **k: _EmptyStream()
    )
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_a, **_k: {
            "content": "visible fallback",
            "thinking": "private reasoning",
            "reasoning": "internal only",
        },
    )

    callback_tokens: list[str] = []
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
    )

    result = chat_worker._run_chat_completion_task_compat(
        task,
        token_callback=callback_tokens.append,
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "visible fallback"
    assert callback_tokens == ["visible fallback"]
    assert "thinking" not in result
    assert "reasoning" not in result


def test_duplicate_turn_is_prevented_before_new_completion(monkeypatch):
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_safe_emit_live_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_for_turn",
        lambda **_kwargs: 90210,
    )

    completion_called = False

    def _should_not_run(*_a, **_k):
        nonlocal completion_called
        completion_called = True
        return {"message_id": 1}

    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", _should_not_run
    )

    chat_worker._run_chat_task(_build_task(thread_id=23))

    assert completion_called is False
    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload.get("message_id") == 90210
    assert completed_payload.get("selection_source") == "turn_id_dedupe"


def test_completion_schedules_background_audio_generation_without_blocking(
    monkeypatch,
):
    published = _stubbed_success_setup(monkeypatch)
    scheduled: list[dict[str, object]] = []
    task = _build_task(thread_id=31)
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **kwargs: scheduled.append(dict(kwargs)) or True,
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_a, **_k: {
            "message_id": 777,
            "assistant_text": "hello from the assistant",
            "provider": "groq",
            "model": "moonshotai/kimi-k2-instruct-0905",
        },
    )

    chat_worker._run_chat_task(task)

    assert scheduled == [
        {
            "thread_id": 31,
            "message_id": 777,
            "assistant_text": "hello from the assistant",
            "task_id": task.task_id,
            "turn_id": TURN_ID,
        }
    ]
    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload.get("assistant_message_audio_autogenerate") is True
    assert all(event_type != "task.failed" for event_type, _ in published)


def test_audio_generation_schedule_failure_does_not_fail_text_reply(
    monkeypatch,
):
    published = _stubbed_success_setup(monkeypatch)

    def _raise_schedule(**_kwargs):
        raise RuntimeError("tts scheduling unavailable")

    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        _raise_schedule,
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_a, **_k: {
            "message_id": 778,
            "assistant_text": "still persist the reply",
            "provider": "groq",
            "model": "moonshotai/kimi-k2-instruct-0905",
        },
    )

    chat_worker._run_chat_task(_build_task(thread_id=32))

    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload.get("message_id") == 778
    assert (
        completed_payload.get("assistant_message_audio_autogenerate") is False
    )
    assert all(event_type != "task.failed" for event_type, _ in published)


def test_schedule_audio_generation_defaults_enabled_when_flag_absent(
    monkeypatch,
):
    submitted: list[dict[str, object]] = []
    pending: list[dict[str, object]] = []

    monkeypatch.delenv(
        "CODEXIFY_ASSISTANT_MESSAGE_AUDIO_AUTOGENERATE", raising=False
    )
    monkeypatch.setattr(
        chat_worker,
        "find_cached_asset",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "upsert_message_audio_asset_status",
        lambda **kwargs: pending.append(dict(kwargs))
        or {"id": 1, "status": "pending"},
    )
    monkeypatch.setattr(
        chat_worker,
        "_assistant_message_audio_provider_key",
        lambda: ("chatterbox", "http://tts:8000"),
    )

    class _FakeExecutor:
        def submit(self, fn, **kwargs):
            submitted.append({"fn": fn, **kwargs})
            return object()

    monkeypatch.setattr(
        chat_worker, "_ASSISTANT_AUDIO_EXECUTOR", _FakeExecutor()
    )

    scheduled = chat_worker._schedule_assistant_message_audio_generation(
        thread_id=61,
        message_id=991,
        assistant_text="generate this",
        task_id="task-audio-default-on",
        turn_id=TURN_ID,
    )

    assert scheduled is True
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"
    assert len(submitted) == 1
    assert submitted[0]["thread_id"] == 61
    assert submitted[0]["message_id"] == 991


def test_schedule_audio_generation_respects_explicit_disable_flag(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ASSISTANT_MESSAGE_AUDIO_AUTOGENERATE", "0")
    monkeypatch.setattr(
        chat_worker,
        "find_cached_asset",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("cache lookup should be skipped when disabled")
        ),
    )

    scheduled = chat_worker._schedule_assistant_message_audio_generation(
        thread_id=62,
        message_id=992,
        assistant_text="skip this",
        task_id="task-audio-disabled",
        turn_id=TURN_ID,
    )

    assert scheduled is False


def test_background_audio_generation_persists_ready_asset_with_message_linkage(
    monkeypatch,
):
    saved: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    monkeypatch.setattr(
        chat_worker.tts_trigger,
        "generate_tts_artifact_with_result",
        lambda *_a, **_k: chat_worker.tts_trigger.TTSAttemptResult(
            ok=True,
            plugin_id="chatterbox",
            base_url="http://tts:8000",
            provider="qwen3_0.6b",
            audio_bytes=b"RIFF....WAVE",
            audio_format="wav",
            artifact_bytes=len(b"RIFF....WAVE"),
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "save_message_audio_asset",
        lambda **kwargs: saved.append(dict(kwargs)) or {"id": 1},
    )
    monkeypatch.setattr(
        chat_worker,
        "upsert_message_audio_asset_status",
        lambda **kwargs: failed.append(dict(kwargs)) or {"id": 1},
    )

    chat_worker._generate_assistant_message_audio_artifact(
        thread_id=41,
        message_id=901,
        assistant_text="persist me",
        task_id="task-audio",
        turn_id=TURN_ID,
        provider_key="chatterbox",
        voice="assistant",
        plugin_base_url="http://tts:8000",
    )

    assert len(saved) == 1
    assert saved[0]["message_id"] == 901
    assert saved[0]["provider"] == "chatterbox"
    assert saved[0]["voice"] == "assistant"
    assert saved[0]["audio_bytes"] == b"RIFF....WAVE"
    assert saved[0]["delivery_variants_json"]["source"] == (
        "assistant_message_autogenerate"
    )
    assert saved[0]["delivery_variants_json"]["thread_id"] == 41
    assert saved[0]["delivery_variants_json"]["message_id"] == 901
    assert failed == []


def test_background_audio_generation_marks_failed_without_breaking_reply(
    monkeypatch,
):
    failed: list[dict[str, object]] = []
    monkeypatch.setattr(
        chat_worker.tts_trigger,
        "generate_tts_artifact_with_result",
        lambda *_a, **_k: chat_worker.tts_trigger.TTSAttemptResult(
            ok=False,
            plugin_id="chatterbox",
            base_url="http://tts:8000",
            failure_kind="plugin_unreachable",
            error_code="transport_failure",
            error_message="connection refused",
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "save_message_audio_asset",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("ready asset should not be written")
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "upsert_message_audio_asset_status",
        lambda **kwargs: failed.append(dict(kwargs)) or {"id": 1},
    )

    chat_worker._generate_assistant_message_audio_artifact(
        thread_id=42,
        message_id=902,
        assistant_text="mark failure",
        task_id="task-audio-failed",
        turn_id=TURN_ID,
        provider_key="chatterbox",
        voice="assistant",
        plugin_base_url="http://tts:8000",
    )

    assert len(failed) == 1
    assert failed[0]["status"] == "failed"
    assert failed[0]["delivery_variants_json"]["error"]["code"] == (
        "transport_failure"
    )
