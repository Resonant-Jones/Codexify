from __future__ import annotations

import json
from urllib.parse import unquote

import pytest


@pytest.mark.parametrize(
    ("raw_source_mode", "expected_source_mode"),
    [
        ("personal_knowledge", "personal_knowledge"),
        ("", "project"),
        ("invalid", "project"),
        (None, "project"),
    ],
)
def test_chat_complete_normalizes_source_mode_and_encodes_origin(
    test_client, mock_db, monkeypatch, raw_source_mode, expected_source_mode
):
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    payload = {"depth_mode": "normal"}
    if raw_source_mode is not None:
        payload["source_mode"] = raw_source_mode

    response = test_client.post("/chat/1/complete", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == expected_source_mode
    task = captured["task"]
    assert getattr(task, "origin").startswith("api:chat.complete|turn_id=")
    assert f"|source_mode={expected_source_mode}" in getattr(task, "origin")
    assert "|slash_intent=" not in getattr(task, "origin")
    assert "|retrieval_override=" not in getattr(task, "origin")
    assert captured["queue_name"] == "codexify:queue:chat"


@pytest.mark.parametrize(
    ("slash_intent", "expected_retrieval_override"),
    [
        (
            {
                "commandId": "project",
                "rawInput": "/project search",
                "intentKind": "workspace",
                "retrievalHint": "project",
            },
            {"mode": "project", "reason": "slash_project_hint"},
        ),
        (
            {
                "commandId": "thread",
                "rawInput": "/thread recap",
                "intentKind": "conversation",
                "retrievalHint": "none",
            },
            {"mode": "none", "reason": "no_override"},
        ),
    ],
)
def test_chat_complete_derives_retrieval_override_without_changing_source_mode(
    test_client, mock_db, monkeypatch, slash_intent, expected_retrieval_override
):
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    payload = {
        "depth_mode": "normal",
        "source_mode": "personal_knowledge",
        "slashIntent": slash_intent,
    }

    response = test_client.post("/chat/1/complete", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == "personal_knowledge"
    task = captured["task"]
    origin = getattr(task, "origin")
    assert "|source_mode=personal_knowledge" in origin
    assert "|slash_intent=" in origin
    assert "|retrieval_override=" in origin

    slash_intent_raw = origin.split("|slash_intent=", 1)[1]
    slash_intent_payload = json.loads(
        unquote(slash_intent_raw.split("|retrieval_override=", 1)[0])
    )
    assert slash_intent_payload == {
        "commandId": slash_intent["commandId"],
        "intentKind": slash_intent["intentKind"],
        "retrievalHint": slash_intent["retrievalHint"],
    }
    assert "rawInput" not in slash_intent_payload

    retrieval_override_raw = origin.split("|retrieval_override=", 1)[1]
    retrieval_override = json.loads(unquote(retrieval_override_raw))
    assert retrieval_override == expected_retrieval_override
    assert captured["queue_name"] == "codexify:queue:chat"


@pytest.mark.parametrize(
    "invalid_slash_intent",
    [
        {
            "commandId": "bogus",
            "rawInput": "/bogus",
            "intentKind": "workspace",
            "retrievalHint": "project",
        },
        {
            "commandId": "project",
            "rawInput": "/project",
            "intentKind": "workspace",
            "retrievalHint": "team",
        },
    ],
)
def test_chat_complete_rejects_invalid_slash_intent_values(
    test_client, mock_db, invalid_slash_intent
):
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    response = test_client.post(
        "/chat/1/complete",
        json={"depth_mode": "normal", "slashIntent": invalid_slash_intent},
    )

    assert response.status_code == 422
