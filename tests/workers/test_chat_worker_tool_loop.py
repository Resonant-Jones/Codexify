from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker

TURN_ID = "11111111-1111-4111-8111-111111111111"


def _build_task(
    *,
    task_id: str = "task-tool-loop",
    thread_id: int = 7,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id=task_id,
        thread_id=thread_id,
        provider="openai",
        model="gpt-4o",
        selection_source="explicit",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
        request_id="req-tool-loop",
        latest_turn_message_id=11,
    )
    task.turn_id = TURN_ID
    task.turn_lock_owner = task_id
    return task


def test_worker_forwards_tool_loop_observability_fields(monkeypatch):
    task = _build_task()

    published: list[tuple[str, dict[str, Any]]] = []
    mock_db = SimpleNamespace(
        create_message=lambda *_args, **_kwargs: 99,
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
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: {
            "message_id": 99,
            "provider": "openai",
            "model": "gpt-4o",
            "assistant_text": "final answer",
            "latest_turn_message_id": 11,
            "messageId": 11,
            "requestId": "req-tool-loop",
            "toolTurnId": "tool-turn-1",
            "toolTurnState": "completed",
            "loopStopReason": "tool_turn_completed",
            "commandRunId": "run-123",
            "tool_loop": {
                "messageId": 11,
                "requestId": "req-tool-loop",
                "toolTurnId": "tool-turn-1",
                "toolTurnState": "completed",
                "loopStopReason": "tool_turn_completed",
                "commandRunId": "run-123",
            },
            "payload_summary": {
                "message_id": 11,
                "request_id": "req-tool-loop",
                "tool_turn_id": "tool-turn-1",
                "tool_turn_state": "completed",
                "loop_stop_reason": "tool_turn_completed",
                "command_run_id": "run-123",
                "tool_loop": {
                    "messageId": 11,
                    "requestId": "req-tool-loop",
                    "toolTurnId": "tool-turn-1",
                    "toolTurnState": "completed",
                    "loopStopReason": "tool_turn_completed",
                    "commandRunId": "run-123",
                },
            },
            "retrieval_provenance": {},
            "trace": {},
        },
    )

    chat_worker._run_chat_task(task)

    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload["messageId"] == 11
    assert completed_payload["requestId"] == "req-tool-loop"
    assert completed_payload["toolTurnId"] == "tool-turn-1"
    assert completed_payload["toolTurnState"] == "completed"
    assert completed_payload["loopStopReason"] == "tool_turn_completed"
    assert completed_payload["commandRunId"] == "run-123"
    assert completed_payload["tool_loop"]["toolTurnId"] == "tool-turn-1"
