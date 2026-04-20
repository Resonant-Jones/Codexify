from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.routes import chat as chat_routes
from guardian.tasks.types import ChatCompletionTask, task_from_dict


@pytest.mark.asyncio
async def test_chat_complete_injects_local_user_id_into_task_payload(
    monkeypatch,
):
    monkeypatch.setattr(
        chat_routes,
        "chatlog_db",
        SimpleNamespace(
            get_chat_thread=lambda _thread_id: {
                "id": 1,
                "user_id": "test_user",
                "project_id": 7,
                "archived_at": None,
            },
            list_messages=lambda *_args, **_kwargs: [
                {"role": "user", "content": "Hello"}
            ],
            count_messages=lambda *_args, **_kwargs: 1,
            write_audit_log=lambda *_args, **_kwargs: None,
            get_thread_profile=lambda *_args, **_kwargs: None,
        ),
    )

    captured: dict[str, object] = {}
    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(
        chat_routes,
        "enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        chat_routes,
        "_publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    response = await chat_routes.chat_complete(
        1,
        chat_routes.ChatCompletionRequest(depth_mode="normal"),
        request=None,
        api_key="test",
        request_id=None,
        request_user_scope=SimpleNamespace(
            multi_user_enabled=False,
            account_id=None,
        ),
    )

    assert isinstance(response, dict)
    task = captured["task"]
    assert isinstance(task, ChatCompletionTask)
    assert task.user_id == "local"
    assert task.to_dict()["user_id"] == "local"

    round_tripped = task_from_dict(task.to_dict())
    assert isinstance(round_tripped, ChatCompletionTask)
    assert round_tripped.user_id == "local"


@pytest.mark.asyncio
async def test_chat_complete_uses_request_account_id_for_task_payload(
    monkeypatch,
):
    monkeypatch.setattr(
        chat_routes,
        "chatlog_db",
        SimpleNamespace(
            get_chat_thread=lambda _thread_id: {
                "id": 1,
                "user_id": "acct-123",
                "project_id": 7,
                "archived_at": None,
            },
            list_messages=lambda *_args, **_kwargs: [
                {"role": "user", "content": "Hello"}
            ],
            count_messages=lambda *_args, **_kwargs: 1,
            write_audit_log=lambda *_args, **_kwargs: None,
            get_thread_profile=lambda *_args, **_kwargs: None,
        ),
    )

    captured: dict[str, object] = {}
    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(
        chat_routes,
        "enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        chat_routes,
        "_publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    response = await chat_routes.chat_complete(
        1,
        chat_routes.ChatCompletionRequest(depth_mode="normal"),
        request=None,
        api_key="test",
        request_id=None,
        request_user_scope=SimpleNamespace(
            multi_user_enabled=True,
            account_id="acct-123",
        ),
    )

    assert isinstance(response, dict)
    task = captured["task"]
    assert isinstance(task, ChatCompletionTask)
    assert task.user_id == "acct-123"
    assert task.to_dict()["user_id"] == "acct-123"

    round_tripped = task_from_dict(task.to_dict())
    assert isinstance(round_tripped, ChatCompletionTask)
    assert round_tripped.user_id == "acct-123"
