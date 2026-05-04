from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guardian.agents.adapters.base import AgentRunEnvelope
from guardian.tasks.types import CodingExecutionTask
from guardian.workers.coding_worker import CodingWorker


@dataclass
class _FakeAdapter:
    result: AgentRunEnvelope

    def execute(self, request: Any) -> AgentRunEnvelope:
        _ = request
        return self.result


class _FakeStore:
    def __init__(self) -> None:
        self.status_updates: list[tuple[str, str]] = []
        self.coding_results: list[dict[str, Any]] = []

    def update_run_status(self, *, run_id: str, status: str) -> None:
        self.status_updates.append((run_id, status))

    def store_coding_result(self, **kwargs: Any) -> None:
        self.coding_results.append(dict(kwargs))


def test_coding_worker_publishes_run_scoped_events(monkeypatch) -> None:
    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish_with_visibility(
        task_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        published.append((task_id, event_type, dict(payload or {})))
        return {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": "1-0",
            "failure_class": None,
            "error_code": None,
            "error": None,
        }

    fake_store = _FakeStore()
    fake_adapter = _FakeAdapter(
        result=AgentRunEnvelope(status="ok", summary="done")
    )

    monkeypatch.setattr(
        "guardian.workers.coding_worker.task_events.publish_with_visibility",
        fake_publish_with_visibility,
    )
    monkeypatch.setattr(
        "guardian.workers.coding_worker.ADAPTERS",
        {"pi_codex_runner": fake_adapter},
    )

    worker = CodingWorker(agent_store=fake_store)  # type: ignore[arg-type]
    task = CodingExecutionTask(
        task_id="queue-task-1",
        run_id="run-1",
        deployment_id="dep-1",
        instructions="echo hi",
        cwd="/tmp",
        timeout_seconds=1,
        coding_task_id="coding-1",
        attempt_id="attempt-1",
        thread_id=3,
        source_message_id="msg-1",
    )

    worker._process_task(task)

    assert [item[0] for item in published] == ["run-1", "run-1"]
    assert published[0][1] == "task.running"
    assert published[1][1] == "task.completed"
    assert published[0][2]["queue_task_id"] == "queue-task-1"
    assert fake_store.status_updates == []
    assert fake_store.coding_results[0]["run_id"] == "run-1"
