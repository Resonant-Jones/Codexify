from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

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


def test_chat_create_thread_normalizes_display_label_in_single_user_mode(
    monkeypatch,
):
    db = MagicMock()
    db.get_recent_thread.return_value = None
    db.create_chat_thread.return_value = {
        "id": 11,
        "user_id": "local",
        "title": "Legacy",
        "summary": "",
        "project_id": 7,
    }
    db.write_audit_log.return_value = None
    monkeypatch.setattr(chat_routes, "chatlog_db", db)
    monkeypatch.setattr(chat_routes, "get_single_user_id", lambda: "local")

    result = chat_routes.chat_create_thread(
        {"title": "Legacy", "user_id": "Resonant Jones"},
        api_key="test-api-key",
        request_user_scope=SimpleNamespace(
            user_id="local",
            account_id=None,
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == "local"
    assert db.get_recent_thread.call_args.args[0] == "local"
    assert db.create_chat_thread.call_args.kwargs["user_id"] == "local"


def test_chat_message_create_on_send_normalizes_display_label_in_single_user_mode(
    monkeypatch,
):
    db = MagicMock()
    db.create_chat_thread.return_value = {
        "id": 21,
        "user_id": "local",
        "title": "Legacy",
        "summary": "",
        "project_id": 7,
    }
    db.write_audit_log.return_value = None
    monkeypatch.setattr(chat_routes, "chatlog_db", db)
    monkeypatch.setattr(chat_routes, "get_single_user_id", lambda: "local")

    captured: dict[str, object] = {}

    def fake_persist_message_to_thread(*, thread_id, role, content, owner):
        captured.update(
            {
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "owner": owner,
            }
        )
        return {
            "thread": {
                "id": thread_id,
                "user_id": owner,
                "title": "Legacy",
            },
            "message": {
                "id": 99,
                "thread_id": thread_id,
                "role": role,
                "content": content,
            },
        }

    monkeypatch.setattr(
        chat_routes,
        "_persist_message_to_thread",
        fake_persist_message_to_thread,
    )

    result = chat_routes.chat_post_message_create_on_send(
        chat_routes.ChatMessageCreateRequest(
            thread_id=None,
            role="user",
            content="Hello",
            user_id="Resonant Jones",
            title="Legacy",
            project_id=7,
        ),
        api_key="test-api-key",
        request_user_scope=SimpleNamespace(
            user_id="local",
            account_id=None,
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == "local"
    assert captured["owner"] == "local"
    assert db.create_chat_thread.call_args.kwargs["user_id"] == "local"
    assert db.write_audit_log.call_args.kwargs["user_id"] == "local"
