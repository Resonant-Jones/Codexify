from __future__ import annotations

from typing import Any

import pytest

from guardian.protocol_tokens import DelegationEventType, DelegationJobStatus
from guardian.routes import delegations


@pytest.fixture(autouse=True)
def reset_delegation_service() -> None:
    delegations.configure_db(None)
    yield
    delegations.configure_db(None)


def _draft_payload() -> dict[str, Any]:
    return {
        "thread_id": 17,
        "conversation_id": "thread-17",
        "project_id": 3,
        "repo_path": "/workspace/codexify",
        "executor": "stub",
        "user_intent": "Build the delegation lane backend slice.",
        "tags": ["backend", "delegation"],
        "context": {"thread_title": "Delegation slice"},
    }


def test_delegation_draft_creation(test_client) -> None:
    response = test_client.post("/api/delegations/draft", json=_draft_payload())

    assert response.status_code == 201
    payload = response.json()
    packet = payload["packet"]
    assert payload["ok"] is True
    assert packet["status"] == DelegationJobStatus.DRAFT.value
    assert packet["thread_id"] == 17
    assert packet["task_prompt"] == "Build the delegation lane backend slice."
    assert packet["tags"] == ["backend", "delegation"]


def test_delegation_approve_creates_queued_task_and_returns_ids(
    test_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_response = test_client.post(
        "/api/delegations/draft",
        json=_draft_payload(),
    )
    packet_id = draft_response.json()["packet"]["packet_id"]

    enqueued_payloads: list[dict[str, Any]] = []
    published_events: list[tuple[str, str, dict[str, Any]]] = []

    def fake_enqueue(task, queue_name):
        enqueued_payloads.append(task.to_dict())
        assert queue_name == delegations.QUEUE_NAME

    def fake_publish(task_id, event_type, data):
        published_events.append((task_id, event_type, dict(data or {})))
        return {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": "evt-1",
        }

    monkeypatch.setattr(delegations, "enqueue", fake_enqueue)
    monkeypatch.setattr(
        delegations.task_events,
        "publish_with_visibility",
        fake_publish,
    )

    response = test_client.post(f"/api/delegations/{packet_id}/approve")

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["packet_id"] == packet_id
    assert body["delegation_id"]
    assert body["task_id"]
    assert body["status"] == DelegationJobStatus.QUEUED.value
    assert body["acceptance_metadata"]["status"] == "accepted"
    assert body["acceptance_metadata"]["warnings"] == []

    assert len(enqueued_payloads) == 1
    queued_task = enqueued_payloads[0]
    assert queued_task["type"] == "delegation.task"
    assert queued_task["status"] == DelegationJobStatus.QUEUED.value
    assert queued_task["packet_id"] == packet_id
    assert queued_task["delegation_id"] == body["delegation_id"]
    assert queued_task["task_id"] == body["task_id"]

    assert len(published_events) == 1
    event_task_id, event_type, event_payload = published_events[0]
    assert event_task_id == body["task_id"]
    assert event_type == DelegationEventType.CREATED.value
    assert event_payload["delegation_id"] == body["delegation_id"]

    job = delegations.get_service().get_job(body["delegation_id"])
    assert job is not None
    assert job.status == DelegationJobStatus.QUEUED.value
    assert job.task_id == body["task_id"]


def test_delegation_cancel_marks_terminal_state(
    test_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_response = test_client.post(
        "/api/delegations/draft",
        json=_draft_payload(),
    )
    packet_id = draft_response.json()["packet"]["packet_id"]

    monkeypatch.setattr(delegations, "enqueue", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        delegations.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": "evt-2",
        },
    )
    approve_response = test_client.post(f"/api/delegations/{packet_id}/approve")
    approve_body = approve_response.json()

    cancel_published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_cancel_publish(task_id, event_type, data):
        cancel_published.append((task_id, event_type, dict(data or {})))
        return {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "terminal",
            "terminal_visibility": True,
            "execution_continued": True,
            "event_id": "evt-3",
        }

    monkeypatch.setattr(
        delegations.task_events,
        "publish_with_visibility",
        fake_cancel_publish,
    )
    monkeypatch.setattr(
        delegations, "cancel_task", lambda *_args, **_kwargs: None
    )

    response = test_client.post(
        f"/api/delegations/{approve_body['delegation_id']}/cancel"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["delegation_id"] == approve_body["delegation_id"]
    assert body["status"] == DelegationJobStatus.CANCELLED.value

    assert len(cancel_published) == 1
    task_id, event_type, event_payload = cancel_published[0]
    assert task_id == approve_body["task_id"]
    assert event_type == DelegationEventType.CANCELLED.value
    assert event_payload["delegation_id"] == approve_body["delegation_id"]

    job = delegations.get_service().get_job(approve_body["delegation_id"])
    assert job is not None
    assert job.status == DelegationJobStatus.CANCELLED.value
    assert job.completed_at is not None


def test_delegation_events_endpoint_resolves_for_created_delegation(
    test_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_response = test_client.post(
        "/api/delegations/draft",
        json=_draft_payload(),
    )
    packet_id = draft_response.json()["packet"]["packet_id"]

    monkeypatch.setattr(delegations, "enqueue", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        delegations.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": "evt-4",
        },
    )
    approve_response = test_client.post(f"/api/delegations/{packet_id}/approve")
    approve_body = approve_response.json()

    read_events_calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_read_events(task_id, last_id, *, block_ms, count):
        read_events_calls.append(
            (task_id, last_id, {"block_ms": block_ms, "count": count})
        )
        return [
            (
                "1-0",
                {
                    "type": DelegationEventType.COMPLETED.value,
                    "task_id": task_id,
                    "data": {
                        "delegation_id": approve_body["delegation_id"],
                        "task_id": task_id,
                        "status": DelegationJobStatus.COMPLETED.value,
                    },
                    "created_at": "2026-04-04T00:00:00+00:00",
                },
            )
        ]

    monkeypatch.setattr(
        delegations.task_events, "read_events", fake_read_events
    )

    response = test_client.get(
        f"/api/delegations/{approve_body['delegation_id']}/events"
    )

    assert response.status_code == 200
    assert DelegationEventType.COMPLETED.value in response.text
    assert approve_body["task_id"] in response.text
    assert read_events_calls
    assert read_events_calls[0][0] == approve_body["task_id"]
