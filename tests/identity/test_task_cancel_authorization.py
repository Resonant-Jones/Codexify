from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from guardian.core import task_event_access
from guardian.core.dependencies import RequestUserScope


def _principal(account_id: str) -> RequestUserScope:
    return RequestUserScope(
        user_id=account_id,
        subject_id=account_id,
        account_id=account_id,
        multi_user_enabled=True,
    )


@pytest.mark.parametrize(
    ("task_id", "account_id", "expected_status"),
    [
        ("task-a", "account-a", None),
        ("task-b", "account-a", 403),
        ("missing-task", "account-a", 404),
    ],
    ids=["owner-can-cancel", "foreign-task-denied", "unknown-task-denied"],
)
def test_cancellation_callback_runs_only_after_durable_owner_check(
    monkeypatch, task_id, account_id, expected_status
):
    db = Mock()
    db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "account-a" if thread_id == 1 else "account-b",
    }
    attempts = {
        "task-a": {"backend_task_id": "task-a", "thread_id": 1},
        "task-b": {"backend_task_id": "task-b", "thread_id": 2},
    }
    lookup = Mock(side_effect=lambda _db, requested_id: attempts.get(requested_id))
    monkeypatch.setattr(
        task_event_access, "get_chat_completion_attempt_by_task_id", lookup
    )
    cancel = Mock()

    if expected_status is None:
        task_event_access.cancel_account_task(
            task_id, _principal(account_id), chatlog_db=db, cancel_task=cancel
        )
        cancel.assert_called_once_with(task_id)
    else:
        with pytest.raises(HTTPException) as raised:
            task_event_access.cancel_account_task(
                task_id, _principal(account_id), chatlog_db=db, cancel_task=cancel
            )
        assert raised.value.status_code == expected_status
        cancel.assert_not_called()

    lookup.assert_called_once_with(db, task_id)


def test_cancel_route_retains_account_auth_and_uses_owned_task_mutator():
    source = Path("guardian/guardian_api.py").read_text()
    module = ast.parse(source)
    route = next(
        node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "request_task_cancel"
    )
    route_source = ast.unparse(route)

    assert "Depends(require_account_session)" in route_source
    assert "Depends(get_account_user_scope)" in route_source
    assert "cancel_account_task(" in route_source
    assert "cancel_task(task_id)" not in route_source
