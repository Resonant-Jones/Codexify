from __future__ import annotations

import json
from types import SimpleNamespace

from guardian.core.completion_terminal import successful_non_stream_terminal
from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.workers import chat_worker


ACCEPTED_TURN_ID = "11111111-1111-4111-8111-111111111111"
OTHER_TURN_ID = "22222222-2222-4222-8222-222222222222"


def test_chat_completion_task_queue_round_trip_preserves_accepted_turn_id():
    task = ChatCompletionTask(
        user_id="account-1",
        thread_id=17,
        turn_id=ACCEPTED_TURN_ID,
        origin=f"api:chat.complete|turn_id={OTHER_TURN_ID}",
    )

    queued_payload = json.loads(json.dumps(task.to_dict()))
    restored = task_from_dict(queued_payload)

    assert isinstance(restored, ChatCompletionTask)
    assert queued_payload["turn_id"] == ACCEPTED_TURN_ID
    assert restored.turn_id == ACCEPTED_TURN_ID
    assert chat_worker._extract_turn_id(restored) == ACCEPTED_TURN_ID


def test_historical_origin_turn_id_is_promoted_before_worker_deduplication(
    monkeypatch,
):
    task = task_from_dict(
        {
            "type": "chat_completion",
            "user_id": "account-1",
            "thread_id": 17,
            "task_id": "historical-task",
            "origin": f"api:chat.complete|turn_id={ACCEPTED_TURN_ID}",
        }
    )
    assert isinstance(task, ChatCompletionTask)
    assert task.turn_id is None
    # Historical queue payloads without a durable accepted request must not
    # synthesize one during this turn-id promotion check.
    task.request_id = ""
    monkeypatch.setattr(chat_worker, "_publish_task_state", lambda *_a, **_k: {})
    monkeypatch.setattr(chat_worker, "_safe_publish", lambda *_a, **_k: {})
    looked_up: list[str] = []

    def find_existing(*, thread_id: int, turn_id: str) -> int:
        looked_up.append(turn_id)
        return 501

    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_for_turn", find_existing
    )

    chat_worker._run_chat_task(task)

    assert looked_up == [ACCEPTED_TURN_ID]
    assert task.turn_id == ACCEPTED_TURN_ID


def test_accepted_turn_identity_is_in_atomic_worker_message_metadata(monkeypatch):
    atomic_metadata: list[dict[str, object]] = []
    fallback_metadata: list[dict[str, object]] = []

    async def build_messages(_task, **_kwargs):
        return (
            [{"role": "user", "content": "hello"}],
            "groq",
            "proof-model",
            {},
            None,
        )

    service = chat_worker._chat_completion_service
    monkeypatch.setattr(chat_worker, "_build_messages_for_llm_compat", build_messages)
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, _settings, **kwargs: {"provider": provider, **kwargs},
    )
    monkeypatch.setattr(service, "_prepare_chat_tool_exposure", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service,
        "_execute_bounded_tool_turn_completion",
        lambda *_a, **_k: {
            "assistant_text": "answer",
            "terminal_evidence": successful_non_stream_terminal(
                provider="groq", model="proof-model"
            ).as_dict(),
        },
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *_a, **_k: None)
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )

    class AtomicChatLog:
        def create_assistant_message_for_completion_attempt(self, **kwargs):
            atomic_metadata.append(dict(kwargs.get("extra_meta") or {}))
            return 42, True

        def write_audit_log(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        chat_worker.dependencies, "chatlog_db", AtomicChatLog()
    )
    task = ChatCompletionTask(
        user_id="account-1",
        thread_id=17,
        task_id="task-atomic-turn-metadata",
        request_id="request-atomic-turn-metadata",
        turn_id=ACCEPTED_TURN_ID,
        provider="groq",
        model="proof-model",
        origin=f"api:chat.complete|turn_id={ACCEPTED_TURN_ID}",
    )

    result = chat_worker._run_chat_completion_task_compat(task)

    assert result["message_id"] == 42
    assert atomic_metadata[0]["turn_id"] == ACCEPTED_TURN_ID
    assert atomic_metadata[0]["turnId"] == ACCEPTED_TURN_ID
    assert fallback_metadata == []
