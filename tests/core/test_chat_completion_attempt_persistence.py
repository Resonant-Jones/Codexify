"""Shared acceptance must commit task-to-thread authority before enqueue."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from guardian.core import chat_completion_service as service
from guardian.queue.redis_queue import QueueEnqueueError
from guardian.queue.turn_lock import build_turn_lock_envelope
from guardian.tasks.types import ChatCompletionTask, HostedRoomInvocationMetadata


@dataclass
class _EphemeralParticipant:
    events: list[str]

    def prepare(self, _task):
        self.events.append("participant_prepare")

    def rollback(self):
        self.events.append("participant_rollback")

    def commit(self):
        self.events.append("participant_commit")


def _task(kind: str, thread_id: int) -> ChatCompletionTask:
    hosted = None
    if kind != "ordinary":
        hosted = HostedRoomInvocationMetadata(
            room_id="room-1",
            source_message_id=7,
            actor_participant_id="guardian-1",
            actor_source="resident",
            actor_ref="guardian",
            requester_authority="guest" if kind == "guest" else "owner",
            requester_participant_id="guest-1" if kind == "guest" else None,
        )
    return ChatCompletionTask(
        request_id=f"request-{kind}-{thread_id}",
        user_id="room-owner" if hosted else "private-owner",
        thread_id=thread_id,
        latest_turn_message_id=7,
        hosted_room_invocation=hosted,
        origin="api:hosted_room.invoke" if hosted else "api:chat.complete",
    )


@pytest.fixture
def acceptance(monkeypatch):
    events: list[str] = []
    rows: dict[str, dict] = {}
    monkeypatch.setattr(
        service.dependencies,
        "chatlog_db",
        SimpleNamespace(
            get_chat_thread=lambda _id: {
                "active_profile_id": None,
                "active_profile_revision": None,
            }
        ),
    )
    monkeypatch.setattr(service, "run_with_redis_timeout", lambda op: op())
    monkeypatch.setattr(
        service,
        "acquire_turn_lock",
        lambda thread_id, owner, **kw: (
            events.append("lock")
            or build_turn_lock_envelope(thread_id, owner, turn_id=kw["turn_id"])
        ),
    )
    monkeypatch.setattr(service, "renew_turn_lock", lambda _thread, lock, **_kw: lock)
    monkeypatch.setattr(
        service,
        "release_turn_lock",
        lambda *_args: events.append("release"),
    )

    def create(_db, *, request_id, backend_task_id, thread_id, turn_id):
        events.append("commit_attempt")
        rows[backend_task_id] = {
            "request_id": request_id,
            "backend_task_id": backend_task_id,
            "thread_id": thread_id,
            "turn_id": turn_id,
            "accepted_at": None,
        }

    def mark(_db, *, backend_task_id):
        events.append("record_acceptance")
        rows[backend_task_id]["accepted_at"] = "committed"

    def enqueue(task, _queue):
        events.append("enqueue")
        assert rows[task.task_id]["thread_id"] == task.thread_id
        assert rows[task.task_id]["request_id"] == task.request_id

    monkeypatch.setattr(service, "create_chat_completion_attempt", create)
    monkeypatch.setattr(service, "mark_chat_completion_attempt_accepted", mark)
    monkeypatch.setattr(service, "enqueue", enqueue)
    monkeypatch.setattr(
        service,
        "_publish_completion_start_event",
        lambda **_kw: {
            "ok": True,
            "task_id": _kw["task"].task_id,
            "event_type": "task.created",
            "event_id": "1-0",
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
        },
    )
    return SimpleNamespace(events=events, rows=rows)


@pytest.mark.parametrize("kind,thread_id", [("ordinary", 1), ("owner", 2), ("guest", 3)])
def test_every_completion_producer_commits_before_queue(acceptance, kind, thread_id):
    task = _task(kind, thread_id)
    result = service.enqueue_chat_completion(
        task, thread_id=thread_id, turn_id="turn-1", request_id=task.request_id
    )
    assert result.queue_accepted
    assert acceptance.events.index("lock") < acceptance.events.index("commit_attempt")
    assert acceptance.events.index("commit_attempt") < acceptance.events.index("enqueue")
    assert acceptance.events.index("enqueue") < acceptance.events.index("record_acceptance")
    assert acceptance.rows[task.task_id]["accepted_at"] == "committed"
    assert acceptance.rows[task.task_id]["thread_id"] == thread_id
    assert task.request_id != task.task_id
    if kind == "guest":
        assert task.hosted_room_invocation.requester_authority == "guest"
        assert task.user_id == "room-owner"


def test_persistence_failure_blocks_enqueue_and_cleans_up(acceptance, monkeypatch):
    task = _task("ordinary", 1)
    participant = _EphemeralParticipant(acceptance.events)
    enqueue = Mock()
    monkeypatch.setattr(service, "enqueue", enqueue)
    monkeypatch.setattr(
        service,
        "create_chat_completion_attempt",
        Mock(side_effect=RuntimeError("database unavailable")),
    )
    with pytest.raises(service.ChatCompletionEnqueueError) as error:
        service.enqueue_chat_completion(
            task, thread_id=1, turn_id="turn-1", participant=participant
        )
    assert error.value.reason == "attempt_persistence_unavailable"
    enqueue.assert_not_called()
    assert acceptance.events[-2:] == ["participant_rollback", "release"]


def test_queue_failure_retains_unaccepted_attempt(acceptance, monkeypatch):
    task = _task("ordinary", 1)
    participant = _EphemeralParticipant(acceptance.events)
    monkeypatch.setattr(
        service, "enqueue", Mock(side_effect=QueueEnqueueError("queue unavailable"))
    )
    with pytest.raises(service.ChatCompletionEnqueueError) as error:
        service.enqueue_chat_completion(
            task, thread_id=1, turn_id="turn-1", participant=participant
        )
    assert error.value.reason == "queue_unavailable"
    assert acceptance.rows[task.task_id]["accepted_at"] is None
    assert acceptance.events.index("commit_attempt") < acceptance.events.index("participant_rollback")
    assert acceptance.events[-2:] == ["participant_rollback", "release"]


def test_acceptance_record_failure_keeps_accepted_task(acceptance, monkeypatch):
    task = _task("ordinary", 1)
    monkeypatch.setattr(
        service,
        "mark_chat_completion_attempt_accepted",
        Mock(side_effect=RuntimeError("database unavailable")),
    )
    result = service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")
    assert result.queue_accepted
    assert result.degraded
    assert acceptance.rows[task.task_id]["accepted_at"] is None
    assert "release" not in acceptance.events
