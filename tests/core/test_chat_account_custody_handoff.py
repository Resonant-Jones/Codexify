"""Route/enqueue handoff proof with hermetic auth, queue and storage doubles."""

# Re-exported pytest fixtures are injected by their imported names.
# ruff: noqa: F811

from unittest.mock import Mock

import pytest

from guardian.core import chat_completion_service as service
from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat
from tests.core.test_chat_completion_attempt_persistence import (
    _task,
    acceptance,  # noqa: F401
)
from tests.routes.conftest import mock_auth, mock_db, test_client  # noqa: F401
from tests.routes.test_chat_complete_thread_config_precedence import (
    _capture_accepted_completion,
)
from tests.utils import get_test_user_id


def _capture_create(monkeypatch):
    original = service.create_chat_completion_attempt
    captured = []

    def create(db, **kwargs):
        captured.append(dict(kwargs))
        kwargs.pop("accepted_account_id", None)
        return original(db, **kwargs)

    monkeypatch.setattr(service, "create_chat_completion_attempt", create)
    return captured


def test_authenticated_ordinary_scope_reaches_persistence(acceptance, monkeypatch):
    task = _task("ordinary", 1)
    scope = RequestUserScope(
        user_id=task.user_id, account_id=task.user_id, subject_id="external-subject"
    )
    captured = _capture_create(monkeypatch)
    result = service.enqueue_chat_completion(
        task, thread_id=1, turn_id="turn-a", account_acceptance_scope=scope
    )
    assert result.queue_accepted
    assert captured[0]["accepted_account_id"] == scope.account_id
    assert acceptance.events.index("commit_attempt") < acceptance.events.index(
        "enqueue"
    )


@pytest.mark.parametrize("kind", ["ordinary", "owner", "guest"])
def test_omitted_scope_does_not_infer_custody_from_task(acceptance, monkeypatch, kind):
    task = _task(kind, 1)
    captured = _capture_create(monkeypatch)
    assert service.enqueue_chat_completion(
        task, thread_id=1, turn_id="turn-a"
    ).queue_accepted
    assert "accepted_account_id" not in captured[0]


def test_legacy_local_scope_preserves_chat_without_new_custody(acceptance, monkeypatch):
    task = _task("ordinary", 1)
    captured = _capture_create(monkeypatch)
    assert service.enqueue_chat_completion(
        task,
        thread_id=1,
        turn_id="turn-a",
        account_acceptance_scope=RequestUserScope(user_id=task.user_id),
    ).queue_accepted
    assert "accepted_account_id" not in captured[0]


@pytest.mark.parametrize("kind", ["owner", "guest"])
def test_hosted_scope_cannot_launder_owner_as_ordinary_acceptance(
    acceptance, monkeypatch, kind
):
    task = _task(kind, 1)
    enqueue = Mock()
    monkeypatch.setattr(service, "enqueue", enqueue)
    with pytest.raises(service.ChatCompletionEnqueueError) as error:
        service.enqueue_chat_completion(
            task,
            thread_id=1,
            turn_id="turn-a",
            account_acceptance_scope=RequestUserScope(
                user_id=task.user_id, account_id=task.user_id
            ),
        )
    assert error.value.reason == "account_acceptance_unavailable"
    assert acceptance.events == []
    enqueue.assert_not_called()


def test_mismatched_scope_blocks_before_lock_or_queue(acceptance):
    task = _task("ordinary", 1)
    with pytest.raises(service.ChatCompletionEnqueueError):
        service.enqueue_chat_completion(
            task,
            thread_id=1,
            turn_id="turn-a",
            account_acceptance_scope=RequestUserScope(
                user_id="other", account_id="other"
            ),
        )
    assert acceptance.events == []


def test_chat_route_passes_dependency_scope_not_client_account(
    test_client, mock_db, monkeypatch
):
    user = get_test_user_id()
    scope = RequestUserScope(
        user_id=user, account_id=user, subject_id="external-subject"
    )
    test_client.app.dependency_overrides[chat.get_request_user_scope] = lambda: scope
    mock_db.list_messages.return_value = [{"id": 1, "role": "user", "content": "Hello"}]
    captured = {}
    accepted = _capture_accepted_completion(captured)

    def enqueue(task, **kwargs):
        captured["scope"] = kwargs["account_acceptance_scope"]
        return accepted(task, **kwargs)

    monkeypatch.setattr(chat, "enqueue_chat_completion", enqueue)
    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda *_a, **_k: None)
    response = test_client.post(
        "/chat/1/complete",
        json={
            "user_id": "attacker",
            "account_acceptance_scope": {"account_id": "attacker"},
        },
    )
    assert response.status_code == 200
    assert captured["scope"] is scope
    assert captured["task"].user_id == user
