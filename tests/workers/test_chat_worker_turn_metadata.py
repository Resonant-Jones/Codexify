from __future__ import annotations

import json

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
