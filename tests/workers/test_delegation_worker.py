from __future__ import annotations

from typing import Any

from guardian.core.delegation_service import DelegationService
from guardian.protocol_tokens import DelegationEventType, DelegationJobStatus
from guardian.tasks.types import DelegationDraftRequest
from guardian.workers import delegation_worker


def _request() -> DelegationDraftRequest:
    return DelegationDraftRequest(
        thread_id=11,
        conversation_id="conversation-11",
        project_id=4,
        repo_path="/workspace/codexify",
        executor="stub",
        user_intent="Validate the delegation worker stub.",
        tags=["worker", "delegation"],
        context={"source": "test"},
    )


def _make_service() -> tuple[DelegationService, Any]:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)
    service.mark_job_queued(approval.job.delegation_id)
    return service, approval


def test_worker_publishes_running_completed_lifecycle(monkeypatch) -> None:
    service, approval = _make_service()

    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish(task_id, event_type, data):
        published.append((task_id, event_type, dict(data or {})))
        return {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": f"evt-{len(published)}",
        }

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        fake_publish,
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert event_types == [
        DelegationEventType.RUNNING.value,
        DelegationEventType.PROGRESS.value,
        DelegationEventType.COMPLETED.value,
    ]
    assert result["status"] == DelegationJobStatus.COMPLETED.value
    assert result["delegation_id"] == approval.job.delegation_id
    assert result["task_id"] == approval.task.task_id


def test_worker_stub_result_persists_terminal_state(monkeypatch) -> None:
    service, approval = _make_service()

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": "evt",
        },
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.COMPLETED.value
    assert job.started_at is not None
    assert job.completed_at is not None

    assert summary is not None
    assert summary.status == DelegationJobStatus.COMPLETED.value
    assert summary.summary == "Delegation worker stub completed."
    assert summary.result["mode"] == "stub"
    assert summary.result["packet_id"] == approval.packet.packet_id
    assert summary.metadata["executor"] == "stub"
    assert result["status"] == DelegationJobStatus.COMPLETED.value


def test_worker_short_circuits_when_job_is_already_terminal(
    monkeypatch,
) -> None:
    service, approval = _make_service()
    service.cancel_delegation(approval.job.delegation_id)

    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish(task_id, event_type, data):
        published.append((task_id, event_type, dict(data or {})))
        return {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": f"evt-{len(published)}",
        }

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        fake_publish,
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.CANCELLED.value
    assert job.started_at is None
    assert summary is None
    assert published == []
    assert result["status"] == DelegationJobStatus.CANCELLED.value
    assert result["delegation_id"] == approval.job.delegation_id
    assert result["task_id"] == approval.task.task_id
