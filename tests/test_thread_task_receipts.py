"""Thread receipts discover durable identity after reload, without replay."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.routes import chat


def _attempt(task="task-a", request="request-a", completed_message_id=None):
    return {
        "request_id": request,
        "backend_task_id": task,
        "thread_id": 11,
        "turn_id": "turn-a",
        "completed_message_id": completed_message_id,
        "created_at": "2026-10-02T00:00:00Z",
        "accepted_at": "2026-10-02T00:00:01Z",
    }


@pytest.fixture
def receipt_route(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {"id": 11, "user_id": "account-a", "metadata": {}}
    monkeypatch.setattr(chat, "chatlog_db", db)
    attempts = MagicMock(return_value=[])
    monkeypatch.setattr(chat, "list_chat_completion_attempts_for_thread", attempts)
    evidence = MagicMock(
        return_value={
            "state": "unknown",
            "event_type": None,
            "reason": "task_events_missing",
        }
    )
    monkeypatch.setattr(chat.task_events, "describe_terminal_state", evidence)
    monkeypatch.setattr(chat, "_require_thread_account_scope", lambda *a, **kw: None)
    return db, attempts, evidence


def test_receipts_use_durable_attempts_and_ignore_process_cache(
    receipt_route, monkeypatch
):
    db, attempts, evidence = receipt_route
    monkeypatch.setitem(chat._thread_latest_task, 11, "unbound-cache-task")
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"] == []
    attempts.assert_called_once_with(db, 11, limit=101, offset=0)
    evidence.assert_not_called()


def test_durable_assistant_link_recovers_completion_without_redis(receipt_route):
    _, attempts, evidence = receipt_route
    attempts.return_value = [_attempt(completed_message_id=73)]
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"] == [
        {
            "task_id": "task-a",
            "request_id": "request-a",
            "thread_id": 11,
            "turn_id": "turn-a",
            "completed_message_id": 73,
            "created_at": "2026-10-02T00:00:00Z",
            "accepted_at": "2026-10-02T00:00:01Z",
            "state": "terminal",
            "event_type": "task.completed",
            "reason": "durable_completion_recorded",
        }
    ]
    evidence.assert_not_called()


def test_unlinked_attempt_retains_observation_uncertainty(receipt_route):
    _, attempts, evidence = receipt_route
    attempts.return_value = [_attempt()]
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"][0]["state"] == "unknown"
    assert result["tasks"][0]["event_type"] is None
    evidence.assert_called_once_with("task-a")


def test_unlinked_attempt_preserves_terminal_event_evidence(receipt_route):
    _, attempts, evidence = receipt_route
    attempts.return_value = [_attempt()]
    evidence.return_value = {
        "state": "terminal",
        "event_type": "task.failed",
        "reason": "terminal_event_found",
    }
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"][0]["event_type"] == "task.failed"
    assert result["tasks"][0]["reason"] == "terminal_event_found"


def test_receipt_pagination_is_bounded(receipt_route):
    db, attempts, evidence = receipt_route
    attempts.return_value = [_attempt(), _attempt("task-b", "request-b")]
    result = chat.chat_list_tasks(
        11,
        api_key="inert",
        request_user_scope=MagicMock(),
        limit=1,
        offset=4,
    )
    assert [item["task_id"] for item in result["tasks"]] == ["task-a"]
    assert result["has_more"] is True
    assert result["next_offset"] == 5
    attempts.assert_called_once_with(db, 11, limit=2, offset=4)
    evidence.assert_called_once_with("task-a")


def test_missing_or_foreign_thread_is_rejected_before_attempt_read(
    receipt_route, monkeypatch
):
    db, attempts, evidence = receipt_route

    def require_scope(*_args, thread=None, **_kwargs):
        if thread and thread.get("user_id") == "account-b":
            raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(chat, "_require_thread_account_scope", require_scope)
    for thread, expected in [(None, 404), ({"id": 11, "user_id": "account-b"}, 403)]:
        db.get_chat_thread.return_value = thread
        with pytest.raises(HTTPException) as exc:
            chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
        assert exc.value.status_code == expected
    attempts.assert_not_called()
    evidence.assert_not_called()


def test_thread_task_route_is_registered():
    assert "/chat/threads/{thread_id}/tasks" in [r.path for r in chat.router.routes]


def test_http_pagination_rejects_unbounded_query_values(receipt_route):
    _, attempts, _ = receipt_route
    app = FastAPI()
    app.include_router(chat.router)
    app.dependency_overrides[chat.require_api_key] = lambda: "inert"
    app.dependency_overrides[chat.get_request_user_scope] = lambda: MagicMock()
    client = TestClient(app)
    for query in ("limit=0", "limit=101", "offset=-1"):
        response = client.get("/chat/threads/11/tasks?" + query)
        assert response.status_code == 422
    attempts.assert_not_called()
