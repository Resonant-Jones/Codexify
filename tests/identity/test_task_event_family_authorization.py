"""Moved/quarantined producer IDs confer no generic public task-SSE grant."""

from uuid import uuid4

import pytest

from tests.identity.test_task_event_stream_authorization import (
    task_event_client as _task_event_client,
)
from guardian.core.dependencies import require_task_event_read_principal
from guardian.core.hosted_room_session import (
    decode_principal,
    issue_guest_session_token,
)
from guardian.tasks.types import (
    CodingExecutionTask,
    DelegationTask,
    VoiceTurnTask,
    WarmupTask,
)


task_event_client = _task_event_client


@pytest.mark.parametrize("reader", ["account", "guest"])
@pytest.mark.parametrize(
    "family",
    ["agent/coding", "delegation", "account-import", "voice", "warmup", "unknown"],
)
def test_non_chat_producer_ids_are_denied_before_thread_or_redis(
    task_event_client, monkeypatch, reader, family
):
    client, db, lookup, redis_read, attempts = task_event_client
    producers = {
        "agent/coding": CodingExecutionTask(run_id="durable-run", thread_id=7),
        "delegation": DelegationTask(),
        "voice": VoiceTurnTask(thread_id=7),
        "warmup": WarmupTask(),
    }
    task_id = producers[family].task_id if family in producers else str(uuid4())
    assert task_id not in attempts
    if reader == "guest":
        monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "family-exclusion-test-secret")
        token, _ = issue_guest_session_token(
            room_id="room-a",
            room_slug="room-a",
            participant_id="guest-a",
            invitation_id="invite-a",
        )
        guest = decode_principal(token)
        client.app.dependency_overrides[require_task_event_read_principal] = (
            lambda: guest
        )

    # The fixture has an owned thread and secret Redis events available. Neither
    # existing data nor caller-supplied family/ownership hints create admission.
    response = client.get(
        f"/api/tasks/{task_id}/events?task_family=chat&thread_id=7",
        headers={"X-User-Id": "account-a", "Last-Event-ID": "5-9"},
    )
    assert response.status_code == 404
    assert "private generated output" not in response.text
    lookup.assert_called_once_with(db, task_id)
    db.get_chat_thread.assert_not_called()
    redis_read.assert_not_called()
