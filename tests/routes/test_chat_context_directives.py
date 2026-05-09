from __future__ import annotations

import json
from urllib.parse import unquote

import pytest

from tests.utils import get_test_user_id


def _configure_chat_complete_route(mock_db, monkeypatch) -> dict[str, object]:
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
    return captured


def _decode_context_directives_from_origin(origin: str) -> list[dict[str, str]]:
    context_raw = origin.split("|context_directives=", 1)[1]
    for delimiter in (
        "|context_request_plans=",
        "|slash_intent=",
        "|retrieval_override=",
    ):
        if delimiter in context_raw:
            context_raw = context_raw.split(delimiter, 1)[0]
    return json.loads(unquote(context_raw))


def _decode_context_request_plans_from_origin(
    origin: str,
) -> list[dict[str, object]]:
    plans_raw = origin.split("|context_request_plans=", 1)[1]
    for delimiter in ("|slash_intent=", "|retrieval_override="):
        if delimiter in plans_raw:
            plans_raw = plans_raw.split(delimiter, 1)[0]
    return json.loads(unquote(plans_raw))


def test_chat_complete_accepts_valid_context_directive_snake_case(
    test_client, mock_db, monkeypatch
):
    captured = _configure_chat_complete_route(mock_db, monkeypatch)

    response = test_client.post(
        "/chat/1/complete",
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "connector_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": " memory decay ",
                }
            ],
        },
    )

    assert response.status_code == 200
    origin = getattr(captured["task"], "origin")
    assert "|context_directives=" in origin
    assert "|context_request_plans=" in origin
    assert _decode_context_directives_from_origin(origin) == [
        {
            "kind": "connector_context",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
        }
    ]
    assert _decode_context_request_plans_from_origin(origin) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "accepted_not_executed",
            "execution_required": False,
        }
    ]


def test_chat_complete_accepts_valid_context_directive_camel_case(
    test_client, mock_db, monkeypatch
):
    captured = _configure_chat_complete_route(mock_db, monkeypatch)

    response = test_client.post(
        "/chat/1/complete",
        json={
            "depth_mode": "normal",
            "contextDirectives": [
                {
                    "kind": "connector_context",
                    "connectorId": "obsidian",
                    "invocation": "turn_scoped",
                    "queryText": "vault summary",
                }
            ],
        },
    )

    assert response.status_code == 200
    origin = getattr(captured["task"], "origin")
    assert "|context_directives=" in origin
    assert "|context_request_plans=" in origin
    assert _decode_context_directives_from_origin(origin) == [
        {
            "kind": "connector_context",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "vault summary",
        }
    ]
    assert _decode_context_request_plans_from_origin(origin) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "vault summary",
            "status": "accepted_not_executed",
            "execution_required": False,
        }
    ]


@pytest.mark.parametrize(
    "invalid_directive",
    [
        {
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
        },
        {
            "kind": "connector_context",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
        },
        {
            "kind": "connector_context",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "   ",
        },
    ],
)
def test_chat_complete_rejects_malformed_context_directives(
    test_client, mock_db, invalid_directive
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
        json={
            "depth_mode": "normal",
            "context_directives": [invalid_directive],
        },
    )

    # Route convention: request-model validation failures return 422.
    assert response.status_code == 422


def test_chat_complete_rejects_unsupported_context_directive_connector(
    test_client, mock_db
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
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "connector_context",
                    "connector_id": "github",
                    "invocation": "turn_scoped",
                    "query_text": "repo status",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_chat_complete_rejects_unsupported_context_directive_kind(
    test_client, mock_db
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
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "mcp_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_chat_complete_rejects_unsupported_directive_before_enqueue(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    def _enqueue_should_not_run(*_args, **_kwargs):
        raise AssertionError(
            "enqueue should not run for unsupported directives"
        )

    monkeypatch.setattr("guardian.routes.chat.enqueue", _enqueue_should_not_run)

    response = test_client.post(
        "/chat/1/complete",
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "connector_context",
                    "connector_id": "discord",
                    "invocation": "turn_scoped",
                    "query_text": "server status",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_chat_complete_without_context_directives_remains_accepted(
    test_client, mock_db, monkeypatch
):
    captured = _configure_chat_complete_route(mock_db, monkeypatch)

    response = test_client.post(
        "/chat/1/complete", json={"depth_mode": "normal"}
    )

    assert response.status_code == 200
    origin = getattr(captured["task"], "origin")
    assert "|context_directives=" not in origin
    assert "|context_request_plans=" not in origin


def test_chat_complete_returns_400_when_resolver_plan_classification_fails(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    def _enqueue_should_not_run(*_args, **_kwargs):
        raise AssertionError("enqueue should not run when resolver fails")

    monkeypatch.setattr("guardian.routes.chat.enqueue", _enqueue_should_not_run)
    monkeypatch.setattr(
        "guardian.routes.chat.resolve_context_request_plans",
        lambda _directives: (_ for _ in ()).throw(
            ValueError("resolver exploded")
        ),
    )

    response = test_client.post(
        "/chat/1/complete",
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "connector_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]["error"] == "invalid_context_directive_plan"
    )


def test_chat_complete_context_directive_validation_does_not_execute_completion_service(
    test_client, mock_db, monkeypatch
):
    captured = _configure_chat_complete_route(mock_db, monkeypatch)

    def _boom(*_args, **_kwargs):
        raise AssertionError(
            "completion service must not run at route acceptance"
        )

    monkeypatch.setattr(
        "guardian.core.chat_completion_service.run_chat_completion_task", _boom
    )

    response = test_client.post(
        "/chat/1/complete",
        json={
            "depth_mode": "normal",
            "context_directives": [
                {
                    "kind": "connector_context",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert captured["queue_name"] == "codexify:queue:chat"
