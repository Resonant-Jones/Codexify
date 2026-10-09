"""Thread receipts discover durable identity after reload, without replay."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.routes import chat
from guardian.core import chat_completion_service as service
from guardian.core.db import ChatAttemptReconciliation
from guardian.protocol_tokens import ErrorCode
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline


def _attempt(task="task-a", request="request-a", completed_message_id=None):
    return {
        "request_id": request,
        "backend_task_id": task,
        "thread_id": 11,
        "turn_id": "turn-a",
        "completed_message_id": completed_message_id,
        "terminal_event_type": None,
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
    monkeypatch.setattr(chat.task_events, "describe_terminal_state_in_scope", evidence)
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


@pytest.mark.parametrize("event_type", ["task.failed", "task.cancelled"])
def test_durable_worker_terminal_outcome_wins_over_expired_redis_evidence(
    receipt_route, event_type
):
    _, attempts, evidence = receipt_route
    attempts.return_value = [_attempt() | {"terminal_event_type": event_type}]
    evidence.return_value = {
        "state": "unknown",
        "event_type": None,
        "reason": "task_events_missing",
    }

    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())

    assert result["tasks"][0]["state"] == "terminal"
    assert result["tasks"][0]["event_type"] == event_type
    assert result["tasks"][0]["reason"] == "durable_terminal_outcome_recorded"
    evidence.assert_not_called()


def test_durable_completion_link_precedes_other_terminal_projection(receipt_route):
    _, attempts, evidence = receipt_route
    attempts.return_value = [
        _attempt(completed_message_id=73)
        | {"terminal_event_type": "task.failed"}
    ]

    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())

    assert result["tasks"][0]["event_type"] == "task.completed"
    assert result["tasks"][0]["reason"] == "durable_completion_recorded"
    evidence.assert_not_called()


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
    assert "/api/chat/threads/{thread_id}/tasks" in [
        r.path for r in chat.api_chat_router.routes
    ]


def test_api_compatibility_route_preserves_pagination_and_identity(receipt_route):
    db, attempts, evidence = receipt_route
    attempts.return_value = [_attempt()]
    app = FastAPI()
    app.include_router(chat.api_chat_router)
    app.dependency_overrides[chat.require_api_key] = lambda: "inert"
    app.dependency_overrides[chat.get_request_user_scope] = lambda: MagicMock()
    response = TestClient(app).get("/api/chat/threads/11/tasks?limit=2&offset=3")

    assert response.status_code == 200
    assert response.json()["tasks"][0]["request_id"] == "request-a"
    assert response.json()["next_offset"] == 4
    attempts.assert_called_once_with(db, 11, limit=3, offset=3)
    evidence.assert_called_once_with("task-a")


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


@pytest.fixture
def recovery_receipt(receipt_route, monkeypatch):
    _db, attempts, evidence = receipt_route
    deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc) - timedelta(days=1))
    attempts.return_value = [_attempt() | {"deadline_snapshot": deadline.to_dict()}]
    outcome = {"failure_code": ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value,
               "reconciled_at": datetime.now(timezone.utc).isoformat()}
    reconcile = MagicMock(return_value=ChatAttemptReconciliation(None, "task.failed", outcome, "private-token"))
    cleanup = MagicMock(return_value=True)
    monkeypatch.setattr(service, "reconcile_chat_completion_attempt_after_deadline", reconcile)
    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", cleanup)
    return attempts, evidence, reconcile, cleanup, outcome


def test_receipt_reconciles_expired_attempt_and_hides_cleanup_capability(recovery_receipt):
    attempts, evidence, reconcile, cleanup, outcome = recovery_receipt
    attempts.return_value[0]["turn_lock_token"] = "private-token"
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    row = result["tasks"][0]
    assert row["state"] == "terminal" and row["event_type"] == "task.failed"
    assert row["reason"] == "durable_terminal_outcome_recorded"
    assert row["failure_code"] == ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value
    assert row["terminal_outcome"] == outcome
    assert "private-token" not in repr(result)
    reconcile.assert_called_once()
    cleanup.assert_called_once_with(11, owner_task_id="task-a", lease_token="private-token")
    evidence.assert_not_called()


def test_cleanup_error_keeps_durable_orphan_receipt_and_can_retry(recovery_receipt):
    _attempts, evidence, reconcile, cleanup, _outcome = recovery_receipt
    cleanup.side_effect = RuntimeError("injected unavailable Redis")
    first = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert first["tasks"][0]["failure_code"] == ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value
    cleanup.side_effect = None
    second = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert second["tasks"] == first["tasks"]
    assert cleanup.call_count == reconcile.call_count == 2
    evidence.assert_not_called()


def test_existing_orphan_retries_matching_lock_cleanup(recovery_receipt):
    attempts, evidence, reconcile, cleanup, outcome = recovery_receipt
    attempts.return_value[0].update(terminal_event_type="task.failed", terminal_outcome=outcome)
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"][0]["failure_code"] == ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value
    reconcile.assert_called_once()
    cleanup.assert_called_once()
    evidence.assert_not_called()


@pytest.mark.parametrize("unknown", ["legacy", "unconfirmed", "pending"])
def test_receipt_does_not_reconstruct_admission_or_deadline(recovery_receipt, unknown):
    attempts, _evidence, reconcile, cleanup, _outcome = recovery_receipt
    if unknown == "legacy":
        attempts.return_value[0]["deadline_snapshot"] = None
    elif unknown == "unconfirmed":
        attempts.return_value[0]["accepted_at"] = None
    else:
        attempts.return_value[0]["deadline_snapshot"] = build_accepted_chat_task_deadline(datetime.now(timezone.utc)).to_dict()
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["tasks"][0]["state"] == "unknown"
    reconcile.assert_not_called()
    cleanup.assert_not_called()


def test_reconciliation_failure_returns_unconfirmed_without_redis_fallback(recovery_receipt):
    _attempts, evidence, reconcile, cleanup, _outcome = recovery_receipt
    reconcile.side_effect = RuntimeError("injected ambiguous database acknowledgement")
    with pytest.raises(HTTPException) as error:
        chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert error.value.status_code == 503
    evidence.assert_not_called()
    cleanup.assert_not_called()


def test_receipt_authorization_precedes_reconciliation(recovery_receipt, monkeypatch):
    attempts, _evidence, reconcile, cleanup, _outcome = recovery_receipt
    def deny(*args, **kwargs):
        raise HTTPException(status_code=403)
    monkeypatch.setattr(chat, "_require_thread_account_scope", deny)
    with pytest.raises(HTTPException) as error:
        chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert error.value.status_code == 403
    attempts.assert_not_called()
    reconcile.assert_not_called()
    cleanup.assert_not_called()


def test_receipt_page_budgets_do_not_slide_per_attempt(recovery_receipt):
    from guardian.core import chat_postgres_deadline, chat_redis_deadline

    attempts, evidence, reconcile, cleanup, outcome = recovery_receipt
    attempts.return_value = [attempts.return_value[0], attempts.return_value[0] | {"backend_task_id": "task-b", "request_id": "request-b"}]
    pg_ends, redis_ends = [], []
    def observe_reconcile(*args, **kwargs):
        budget = chat_postgres_deadline._budget.get()
        assert budget.operation
        pg_ends.append(budget.work_end)
        return ChatAttemptReconciliation(None, "task.failed", outcome, "private-token")
    def observe_cleanup(*args, **kwargs):
        budget = chat_redis_deadline._budget.get()
        assert budget.operation
        redis_ends.append(budget.work_end)
        return True
    reconcile.side_effect = observe_reconcile
    cleanup.side_effect = observe_cleanup
    result = chat.chat_list_tasks(11, api_key="inert", request_user_scope=MagicMock())
    assert result["count"] == 2
    assert len(pg_ends) == len(redis_ends) == 2
    assert pg_ends[0] == pg_ends[1] and redis_ends[0] == redis_ends[1]
    evidence.assert_not_called()
