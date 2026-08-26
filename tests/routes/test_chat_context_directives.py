from __future__ import annotations

import json
from urllib.parse import unquote

import pytest

from guardian.core import chat_completion_service
from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes
from tests.utils import get_test_user_id


@pytest.fixture(autouse=True)
def _override_request_scope(test_client):
    user_id = get_test_user_id()
    test_client.app.dependency_overrides[
        chat_routes.get_request_user_scope
    ] = lambda: RequestUserScope(
        user_id=user_id,
        subject_id=user_id,
        account_id=user_id,
        multi_user_enabled=False,
    )
    yield
    test_client.app.dependency_overrides.pop(
        chat_routes.get_request_user_scope, None
    )


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

    def _capture_accepted_completion(task, **_kwargs):
        captured["task"] = task
        captured["acceptance_calls"] = (
            int(captured.get("acceptance_calls", 0)) + 1
        )
        task_created_event = chat_completion_service.ChatCompletionTaskCreatedEventResult(
            ok=True,
            task_id=task.task_id,
            event_type="task.created",
            event_id=f"{task.task_id}:created",
            visibility_scope="progress",
            terminal_visibility=False,
            execution_continued=True,
        )
        return chat_completion_service.ChatCompletionEnqueueResult(
            task=task,
            task_id=task.task_id,
            acceptance_status="accepted",
            acceptance_warnings=(),
            queue_accepted=True,
            degraded=False,
            turn_lock_acquired=True,
            turn_lock={},
            task_created_event=task_created_event,
        )

    monkeypatch.setattr(
        chat_routes,
        "enqueue_chat_completion",
        _capture_accepted_completion,
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
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
    assert captured["acceptance_calls"] == 1


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
    assert captured["acceptance_calls"] == 1


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

    def _acceptance_should_not_run(*_args, **_kwargs):
        raise AssertionError(
            "acceptance service should not run for unsupported directives"
        )

    monkeypatch.setattr(
        chat_routes,
        "enqueue_chat_completion",
        _acceptance_should_not_run,
    )

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
    assert captured["acceptance_calls"] == 1


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

    def _acceptance_should_not_run(*_args, **_kwargs):
        raise AssertionError("acceptance service should not run when resolver fails")

    monkeypatch.setattr(
        chat_routes,
        "enqueue_chat_completion",
        _acceptance_should_not_run,
    )
    monkeypatch.setattr(
        chat_routes,
        "resolve_context_request_plans",
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

    monkeypatch.setattr(chat_completion_service, "run_chat_completion_task", _boom)

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
    assert captured["acceptance_calls"] == 1
    assert captured["task"]
