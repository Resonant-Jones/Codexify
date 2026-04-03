from __future__ import annotations

import json
from unittest.mock import MagicMock

from guardian.tasks.types import TaskLifecycleState


def _parse_sse_events(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    normalized = body.replace("\r\n", "\n")
    for block in normalized.split("\n\n"):
        stripped = block.strip()
        if not stripped or stripped.startswith("retry:"):
            continue
        event_type: str | None = None
        payload: dict[str, object] = {}
        for line in stripped.splitlines():
            if line.startswith("event: "):
                event_type = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: ").strip())
        if event_type:
            events.append((event_type, payload))
    return events


def test_task_event_stream_surfaces_lifecycle_states(test_client, monkeypatch):
    task_id = "task-lifecycle-123"
    events = [
        (
            "1-0",
            {
                "type": "task.state",
                "task_id": task_id,
                "data": {
                    "state": TaskLifecycleState.QUEUED.value,
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-1",
            {
                "type": "task.state",
                "task_id": task_id,
                "data": {
                    "state": TaskLifecycleState.AWAITING_MODEL.value,
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-2",
            {
                "type": "task.state",
                "task_id": task_id,
                "data": {
                    "state": TaskLifecycleState.AWAITING_FIRST_TOKEN.value,
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-3",
            {
                "type": "task.state",
                "task_id": task_id,
                "data": {
                    "state": TaskLifecycleState.STREAMING.value,
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-4",
            {
                "type": "task.chunk",
                "task_id": task_id,
                "data": {
                    "delta": "Hel",
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-5",
            {
                "type": "task.state",
                "task_id": task_id,
                "data": {
                    "state": TaskLifecycleState.COMPLETED.value,
                    "thread_id": 7,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
        (
            "1-6",
            {
                "type": "task.completed",
                "task_id": task_id,
                "data": {
                    "message_id": 42,
                },
                "created_at": "2026-04-02T00:00:00+00:00",
            },
        ),
    ]
    read_events_spy = MagicMock(return_value=events)
    monkeypatch.setattr(
        "guardian.guardian_api.task_events.read_events",
        read_events_spy,
    )

    with test_client.stream("GET", f"/api/tasks/{task_id}/events") as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    parsed_events = _parse_sse_events(body)
    state_sequence = [
        payload["state"]
        for event_type, payload in parsed_events
        if event_type == "task.state"
    ]
    assert state_sequence == [
        TaskLifecycleState.QUEUED.value,
        TaskLifecycleState.AWAITING_MODEL.value,
        TaskLifecycleState.AWAITING_FIRST_TOKEN.value,
        TaskLifecycleState.STREAMING.value,
        TaskLifecycleState.COMPLETED.value,
    ]
    assert any(
        event_type == "task.chunk" and payload["delta"] == "Hel"
        for event_type, payload in parsed_events
    )
    assert parsed_events[-1][0] == "task.completed"
    assert parsed_events[-1][1]["message_id"] == 42
    read_events_spy.assert_called_once()
