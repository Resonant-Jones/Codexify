from __future__ import annotations

from unittest.mock import MagicMock

from guardian.core import chat_completion_service as service
from guardian.routes import chat
from guardian.tasks.types import ChatCompletionTask


def test_chat_complete_delegates_acceptance_to_shared_operation(
    test_client, mock_db, monkeypatch
):
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]
    accepted_task = ChatCompletionTask(
        request_id="request-1",
        user_id="test_user",
        thread_id=1,
        origin="api:chat.complete|turn_id=turn-1|source_mode=project",
    )
    event = service.ChatCompletionTaskCreatedEventResult(
        ok=True,
        task_id=accepted_task.task_id,
        event_type="task.created",
        event_id="evt-1",
        visibility_scope="progress",
        terminal_visibility=False,
        execution_continued=True,
    )
    accepted = service.ChatCompletionEnqueueResult(
        task=accepted_task,
        task_id=accepted_task.task_id,
        acceptance_status="accepted",
        acceptance_warnings=(),
        queue_accepted=True,
        degraded=False,
        turn_lock_acquired=True,
        turn_lock={},
        task_created_event=event,
    )
    enqueue = MagicMock(return_value=accepted)
    monkeypatch.setattr(chat, "enqueue_chat_completion", enqueue)
    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    response = test_client.post(
        "/chat/1/complete",
        json={},
        headers={"X-Request-ID": "req-delegation"},
    )

    assert response.status_code == 200
    assert response.json()["acceptance_status"] == "accepted"
    enqueue.assert_called_once()
    called_task = enqueue.call_args.args[0]
    assert called_task.type == "chat_completion"
    assert enqueue.call_args.kwargs["thread_id"] == 1
    assert enqueue.call_args.kwargs["turn_id"] == response.json()["turn_id"]
    assert enqueue.call_args.kwargs["request_id"] == "req-delegation"
