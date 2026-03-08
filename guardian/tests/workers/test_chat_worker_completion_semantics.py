from __future__ import annotations

import logging

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
        thread_id=thread_id,
        provider="groq",
        model="moonshotai-kimi-k2-instruct-9050",
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
            "model": "moonshotai-kimi-k2-instruct-9050",
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
            "model": "moonshotai-kimi-k2-instruct-9050",
        }

    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", _run_completion
    )

    chat_worker._run_chat_task(_build_task(thread_id=29, turn_id=TURN_ID))
    retry_task = ChatCompletionTask(
        task_id="task-retry",
        thread_id=29,
        provider="groq",
        model="moonshotai-kimi-k2-instruct-9050",
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
            "model": "moonshotai-kimi-k2-instruct-9050",
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
            "model": "moonshotai-kimi-k2-instruct-9050",
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
