from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.parse import unquote

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
)
from guardian.tasks.types import task_from_dict
from tests.utils import get_test_user_id


@pytest.mark.parametrize(
    ("raw_source_mode", "expected_source_mode"),
    [
        ("personal_knowledge", "personal_knowledge"),
        ("obsidian", "obsidian_only"),
        ("obsidian_only", "obsidian_only"),
        ("", "project"),
        ("invalid", "project"),
        (None, "project"),
    ],
)
def test_chat_complete_normalizes_source_mode_and_encodes_origin(
    test_client, mock_db, monkeypatch, raw_source_mode, expected_source_mode
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
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

    expected_requested_source_mode = (
        "project" if raw_source_mode is None else raw_source_mode
    )

    response = test_client.post("/chat/1/complete", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == expected_source_mode
    task = captured["task"]
    assert getattr(task, "origin").startswith("api:chat.complete|turn_id=")
    assert f"|source_mode={expected_source_mode}" in getattr(task, "origin")
    assert "|slash_intent=" not in getattr(task, "origin")
    assert "|retrieval_override=" not in getattr(task, "origin")
    assert (
        getattr(task, "requested_source_mode") == expected_requested_source_mode
    )
    assert getattr(task, "retrieval_override", None) is None
    round_tripped = task_from_dict(task.to_dict())
    assert (
        getattr(round_tripped, "requested_source_mode")
        == expected_requested_source_mode
    )
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
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
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
    assert getattr(task, "requested_source_mode") == "personal_knowledge"
    assert getattr(task, "retrieval_override") == expected_retrieval_override
    round_tripped = task_from_dict(task.to_dict())
    assert (
        getattr(round_tripped, "retrieval_override")
        == expected_retrieval_override
    )
    assert (
        getattr(round_tripped, "requested_source_mode") == "personal_knowledge"
    )

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
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    response = test_client.post(
        "/chat/1/complete",
        json={"depth_mode": "normal", "slashIntent": invalid_slash_intent},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "retrieval_override",
        "expected_policy",
        "expected_widening_enabled",
    ),
    [
        (
            None,
            {
                "source_mode": SOURCE_MODE_PROJECT,
                "widening_enabled": True,
                "identity_scope": SOURCE_MODE_PROJECT,
            },
            True,
        ),
        (
            {"mode": "project"},
            {
                "source_mode": SOURCE_MODE_PROJECT,
                "widening_enabled": True,
                "identity_scope": SOURCE_MODE_PROJECT,
            },
            True,
        ),
        (
            {"mode": "personal_knowledge"},
            {
                "source_mode": SOURCE_MODE_PERSONAL_KNOWLEDGE,
                "widening_enabled": True,
                "identity_scope": SOURCE_MODE_PERSONAL_KNOWLEDGE,
            },
            True,
        ),
        (
            {"mode": "conversation"},
            {
                "source_mode": "thread",
                "widening_enabled": False,
                "identity_scope": "thread",
            },
            False,
        ),
    ],
)
async def test_context_broker_merges_retrieval_override_without_skipping_thread_first(
    monkeypatch, retrieval_override, expected_policy, expected_widening_enabled
):
    expected_user_id = get_test_user_id()

    class _Chatlog:
        def get_chat_thread(self, thread_id):
            return {
                "id": thread_id,
                "user_id": expected_user_id,
                "project_id": 7,
                "archived_at": None,
            }

        def list_messages(self, thread_id, limit, offset):
            return [{"id": 1, "role": "user", "content": "Hello"}]

    broker = ContextBroker(
        _Chatlog(),
        None,
        None,
        None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )
    captured: dict[str, object] = {}

    async def _fake_search_with_widening(
        *,
        query,
        k,
        thread_id,
        user_id,
        project_id,
        source_mode,
        search_fn,
        widening_enabled=True,
    ):
        captured.update(
            {
                "called": True,
                "query": query,
                "k": k,
                "thread_id": thread_id,
                "user_id": user_id,
                "project_id": project_id,
                "source_mode": source_mode,
                "widening_enabled": widening_enabled,
            }
        )
        return (
            [{"id": "doc-1", "score": 0.9, "text": "thread hit"}],
            "none",
            {
                "attempted": True,
                "status": "contributed",
                "reason": "local_hits",
            },
        )

    async def _fake_get_scoped_documents(**_kwargs):
        return {"project": [], "thread": [], "global": []}

    monkeypatch.setattr(
        broker,
        "_search_with_widening",
        _fake_search_with_widening,
    )
    monkeypatch.setattr(
        broker,
        "get_scoped_documents",
        _fake_get_scoped_documents,
    )

    _context, trace = await broker.assemble(
        1,
        query="Hello",
        depth_mode="normal",
        user_id="test_user",
        project_id=7,
        source_mode=SOURCE_MODE_PROJECT,
        retrieval_override=retrieval_override,
    )

    assert captured["called"] is True
    assert captured["widening_enabled"] is expected_widening_enabled
    assert trace["effective_policy"] == expected_policy
