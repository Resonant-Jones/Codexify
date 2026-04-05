from __future__ import annotations

from typing import Any

from guardian.core.delegation_service import DelegationService
from guardian.core.executors.base import (
    ExecutorFailure,
    ExecutorResult,
    ExecutorStreamChunk,
)
from guardian.protocol_tokens import (
    DelegationEventType,
    DelegationExecutorName,
    DelegationJobStatus,
    ErrorCode,
)
from guardian.tasks.types import DelegationDraftRequest
from guardian.workers import delegation_worker


def _request() -> DelegationDraftRequest:
    return DelegationDraftRequest(
        thread_id=11,
        conversation_id="conversation-11",
        project_id=4,
        repo_path="/workspace/codexify",
        executor=DelegationExecutorName.CODEX.value,
        user_intent="Validate the delegation worker Codex path.",
        tags=["worker", "delegation"],
        context={"source": "test"},
    )


def _make_service() -> tuple[DelegationService, Any]:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)
    service.mark_job_queued(approval.job.delegation_id)
    return service, approval


def test_worker_publishes_running_progress_completed_lifecycle(
    monkeypatch,
) -> None:
    service, approval = _make_service()

    published: list[tuple[str, str, dict[str, Any]]] = []

    class FakeExecutor:
        def execute(self, request, *, on_output=None, should_stop=None):  # type: ignore[no-untyped-def]
            if on_output is not None:
                on_output(
                    ExecutorStreamChunk(
                        stream="stdout",
                        text="Analyzing workspace",
                        sequence=0,
                    )
                )
                on_output(
                    ExecutorStreamChunk(
                        stream="stdout",
                        text="Files changed: guardian/workers/delegation_worker.py",
                        sequence=1,
                    )
                )
            return ExecutorResult(
                delegation_id=request.delegation_id,
                task_id=request.task_id,
                status=DelegationJobStatus.COMPLETED.value,
                summary="Codex completed delegation.",
                final_text="Codex completed delegation.",
                stdout="Analyzing workspace\nFiles changed: guardian/workers/delegation_worker.py\n",
                raw_transcript=(
                    "[stdout] Analyzing workspace\n"
                    "[stdout] Files changed: guardian/workers/delegation_worker.py\n"
                ),
                files_changed=["guardian/workers/delegation_worker.py"],
                commands_run=[
                    "pytest -v tests/workers/test_delegation_worker.py"
                ],
                metadata={"executor": DelegationExecutorName.CODEX.value},
            )

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: (
            published.append((task_id, event_type, dict(data or {})))
            or {
                "ok": True,
                "task_id": task_id,
                "event_type": event_type,
                "visibility_scope": "progress",
                "terminal_visibility": False,
                "execution_continued": True,
                "event_id": f"evt-{len(published)}",
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "resolve_executor",
        lambda _name: FakeExecutor(),
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert event_types[0] == DelegationEventType.RUNNING.value
    assert DelegationEventType.PROGRESS.value in event_types
    assert event_types[-1] == DelegationEventType.COMPLETED.value
    assert result["status"] == DelegationJobStatus.COMPLETED.value
    assert result["outcome_type"] == "task_summary"
    assert result["delegation_id"] == approval.job.delegation_id
    assert result["task_id"] == approval.task.task_id
    assert result["files_changed"] == ["guardian/workers/delegation_worker.py"]

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.COMPLETED.value
    assert job.started_at is not None
    assert job.completed_at is not None

    assert summary is not None
    assert summary.status == DelegationJobStatus.COMPLETED.value
    assert summary.summary == "Codex completed delegation."
    assert summary.files_changed == ["guardian/workers/delegation_worker.py"]
    assert summary.commands_run == [
        "pytest -v tests/workers/test_delegation_worker.py"
    ]
    assert summary.metadata["executor"] == DelegationExecutorName.CODEX.value


def test_worker_publishes_terminal_failed_state_on_executor_failure(
    monkeypatch,
) -> None:
    service, approval = _make_service()

    published: list[tuple[str, str, dict[str, Any]]] = []

    class FailingExecutor:
        def execute(self, request, *, on_output=None, should_stop=None):  # type: ignore[no-untyped-def]
            return ExecutorResult(
                delegation_id=request.delegation_id,
                task_id=request.task_id,
                status=DelegationJobStatus.FAILED.value,
                summary="Codex binary not found: codex",
                final_text="",
                stdout="",
                raw_transcript="",
                failure=ExecutorFailure(
                    error_code=ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value,
                    failure_class="FileNotFoundError",
                    message="Codex binary not found: codex",
                    binary="codex",
                    command=["codex", "exec", request.task_prompt],
                    timeout_seconds=900,
                    details={"cwd": request.repo_path},
                ),
                error_message="Codex binary not found: codex",
                metadata={"executor": DelegationExecutorName.CODEX.value},
            )

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: (
            published.append((task_id, event_type, dict(data or {})))
            or {
                "ok": True,
                "task_id": task_id,
                "event_type": event_type,
                "visibility_scope": "progress",
                "terminal_visibility": False,
                "execution_continued": True,
                "event_id": f"evt-{len(published)}",
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "resolve_executor",
        lambda _name: FailingExecutor(),
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert DelegationEventType.FAILED.value in event_types
    assert result["status"] == DelegationJobStatus.FAILED.value
    assert (
        result["failure"]["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
    )

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.FAILED.value
    assert job.completed_at is not None
    assert job.error_message == "Codex binary not found: codex"

    assert summary is not None
    assert summary.status == DelegationJobStatus.FAILED.value
    assert summary.summary == "Codex binary not found: codex"
    assert summary.failure is not None
    assert (
        summary.failure["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
    )
    assert summary.error_message == "Codex binary not found: codex"


def test_worker_short_circuits_when_job_is_already_terminal(
    monkeypatch,
) -> None:
    service, approval = _make_service()
    service.cancel_delegation(approval.job.delegation_id)

    published: list[tuple[str, str, dict[str, Any]]] = []

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data: (
            published.append((task_id, event_type, dict(data or {})))
            or {
                "ok": True,
                "task_id": task_id,
                "event_type": event_type,
                "visibility_scope": "progress",
                "terminal_visibility": False,
                "execution_continued": True,
                "event_id": f"evt-{len(published)}",
            }
        ),
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
