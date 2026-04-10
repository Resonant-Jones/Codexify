from __future__ import annotations

from typing import Any

import pytest

from guardian.core.delegation_service import DelegationService
from guardian.core.executors.base import (
    CanonicalEscalation,
    ExecutorEscalationEvent,
    ExecutorFailure,
    ExecutorProgressEvent,
    ExecutorTerminalResult,
)
from guardian.protocol_tokens import (
    DelegationEventType,
    DelegationExecutorName,
    DelegationJobStatus,
    ErrorCode,
    ExecutorEventType,
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
        context={"source": "test", "source_message_id": 77},
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
    registry_calls: list[Any] = []

    real_get_executor_entry = delegation_worker.get_executor_entry

    def spy_get_executor_entry(executor_id: Any):  # type: ignore[no-untyped-def]
        registry_calls.append(executor_id)
        return real_get_executor_entry(executor_id)

    def fake_execute(self, request, *, on_output=None, should_stop=None):  # type: ignore[no-untyped-def]
        if on_output is not None:
            on_output(
                ExecutorProgressEvent(
                    stream="stdout",
                    text="Analyzing workspace",
                    sequence=0,
                    request_id=request.request_id,
                    thread_id=request.thread_id,
                    source_message_id=request.source_message_id,
                    project_id=request.project_id,
                    executor_id=request.executor_id,
                    title=request.title,
                    tags=list(request.tags),
                    metadata={
                        "phase": "analysis",
                        "request_id": request.request_id,
                    },
                )
            )
            on_output(
                ExecutorEscalationEvent(
                    request_id=request.request_id,
                    thread_id=request.thread_id,
                    source_message_id=request.source_message_id,
                    project_id=request.project_id,
                    executor_id=request.executor_id,
                    title=request.title,
                    tags=list(request.tags),
                    escalation=CanonicalEscalation(
                        kind="needs_permission",
                        severity="hard",
                        reason_code="write_required",
                        reason="Need approval before writing to disk.",
                        preserved_worktree=True,
                        payload={"path": request.repo_path},
                    ),
                )
            )
        return ExecutorTerminalResult(
            request_id=request.request_id,
            delegation_id=request.delegation_id,
            task_id=request.task_id,
            thread_id=request.thread_id,
            source_message_id=request.source_message_id,
            project_id=request.project_id,
            executor_id=request.executor_id,
            title=request.title,
            status=DelegationJobStatus.COMPLETED.value,
            summary="Codex completed delegation.",
            final_text="Codex completed delegation.",
            stdout=(
                "Analyzing workspace\n"
                "Need approval before writing to disk.\n"
            ),
            raw_transcript=(
                "[stdout] Analyzing workspace\n"
                "[escalation] Need approval before writing to disk.\n"
            ),
            files_changed=["guardian/workers/delegation_worker.py"],
            commands_run=["pytest -v tests/workers/test_delegation_worker.py"],
            tags=list(request.tags),
            result={"summary": "Codex completed delegation."},
            metadata={
                "executor": request.executor_id,
                "request_id": request.request_id,
                "thread_id": request.thread_id,
                "source_message_id": request.source_message_id,
            },
        )

    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker, "get_executor_entry", spy_get_executor_entry
    )
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
        "guardian.core.executors.codex_executor.CodexExecutor.execute",
        fake_execute,
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert event_types[0] == DelegationEventType.RUNNING.value
    assert ExecutorEventType.PROGRESS.value in event_types
    assert ExecutorEventType.ESCALATION.value in event_types
    assert event_types[-1] == DelegationEventType.COMPLETED.value
    assert registry_calls == [approval.job.executor]
    assert result["status"] == DelegationJobStatus.COMPLETED.value
    assert result["outcome_type"] == "task_summary"
    assert result["delegation_id"] == approval.job.delegation_id
    assert result["task_id"] == approval.task.task_id
    assert result["request_id"] == approval.job.delegation_id
    assert result["thread_id"] == approval.job.thread_id
    assert result["source_message_id"] == approval.task.source_message_id
    assert result["executor_id"] == DelegationExecutorName.CODEX.value
    assert result["files_changed"] == ["guardian/workers/delegation_worker.py"]

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.COMPLETED.value
    assert job.started_at is not None
    assert job.completed_at is not None

    assert summary is not None
    assert summary.status == DelegationJobStatus.COMPLETED.value
    assert summary.request_id == approval.job.delegation_id
    assert summary.thread_id == approval.job.thread_id
    assert summary.source_message_id == approval.task.source_message_id
    assert summary.project_id == approval.job.project_id
    assert summary.executor_id == DelegationExecutorName.CODEX.value
    assert summary.title == approval.job.task_prompt
    assert summary.summary == "Codex completed delegation."
    assert summary.files_changed == ["guardian/workers/delegation_worker.py"]
    assert summary.commands_run == [
        "pytest -v tests/workers/test_delegation_worker.py"
    ]
    assert summary.metadata["executor"] == DelegationExecutorName.CODEX.value
    assert summary.lineage["request_id"] == approval.job.delegation_id
    assert summary.lineage["executor_id"] == DelegationExecutorName.CODEX.value

    progress_payloads = [
        payload
        for _task_id, event_type, payload in published
        if event_type == ExecutorEventType.PROGRESS.value
    ]
    escalation_payloads = [
        payload
        for _task_id, event_type, payload in published
        if event_type == ExecutorEventType.ESCALATION.value
    ]
    assert progress_payloads
    assert progress_payloads[0]["text"] == "Analyzing workspace"
    assert progress_payloads[0]["request_id"] == approval.job.delegation_id
    assert (
        progress_payloads[0]["executor_id"]
        == DelegationExecutorName.CODEX.value
    )
    assert escalation_payloads
    assert escalation_payloads[0]["escalation"]["kind"] == "needs_permission"
    assert escalation_payloads[0]["request_id"] == approval.job.delegation_id


def test_worker_publishes_terminal_failed_state_on_executor_failure(
    monkeypatch,
) -> None:
    service, approval = _make_service()

    published: list[tuple[str, str, dict[str, Any]]] = []
    registry_calls: list[Any] = []

    real_get_executor_entry = delegation_worker.get_executor_entry

    def spy_get_executor_entry(executor_id: Any):  # type: ignore[no-untyped-def]
        registry_calls.append(executor_id)
        return real_get_executor_entry(executor_id)

    def fake_execute(self, request, *, on_output=None, should_stop=None):  # type: ignore[no-untyped-def]
        return ExecutorTerminalResult(
            request_id=request.request_id,
            delegation_id=request.delegation_id,
            task_id=request.task_id,
            thread_id=request.thread_id,
            source_message_id=request.source_message_id,
            project_id=request.project_id,
            executor_id=request.executor_id,
            title=request.title,
            status=DelegationJobStatus.FAILED.value,
            summary="Codex binary not found: codex",
            final_text="",
            stdout="",
            raw_transcript="",
            failure=ExecutorFailure(
                error_code=ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value,
                failure_class="FileNotFoundError",
                message="Codex binary not found: codex",
                request_id=request.request_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                project_id=request.project_id,
                executor_id=request.executor_id,
                kind="missing_binary",
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
        delegation_worker, "get_executor_entry", spy_get_executor_entry
    )
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
        "guardian.core.executors.codex_executor.CodexExecutor.execute",
        fake_execute,
    )

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert registry_calls == [approval.job.executor]
    assert event_types[0] == DelegationEventType.RUNNING.value
    assert DelegationEventType.FAILED.value in event_types
    assert result["status"] == DelegationJobStatus.FAILED.value
    assert (
        result["failure"]["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
    )
    assert result["request_id"] == approval.job.delegation_id
    assert result["source_message_id"] == approval.task.source_message_id

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.FAILED.value
    assert job.completed_at is not None
    assert job.error_message == "Codex binary not found: codex"

    assert summary is not None
    assert summary.status == DelegationJobStatus.FAILED.value
    assert summary.request_id == approval.job.delegation_id
    assert summary.thread_id == approval.job.thread_id
    assert summary.source_message_id == approval.task.source_message_id
    assert summary.project_id == approval.job.project_id
    assert summary.executor_id == DelegationExecutorName.CODEX.value
    assert summary.summary == "Codex binary not found: codex"
    assert summary.failure is not None
    assert (
        summary.failure["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_NOT_FOUND.value
    )
    assert summary.error_message == "Codex binary not found: codex"
    assert summary.lineage["request_id"] == approval.job.delegation_id
    assert summary.lineage["executor_id"] == DelegationExecutorName.CODEX.value


def test_worker_rejects_unsupported_executor_ids(
    monkeypatch,
) -> None:
    service, approval = _make_service()
    approval.job.executor = "not-real"
    approval.task.executor = "not-real"

    published: list[tuple[str, str, dict[str, Any]]] = []
    registry_calls: list[Any] = []

    real_get_executor_entry = delegation_worker.get_executor_entry

    def spy_get_executor_entry(executor_id: Any):  # type: ignore[no-untyped-def]
        registry_calls.append(executor_id)
        return real_get_executor_entry(executor_id)

    monkeypatch.setattr(
        delegation_worker, "get_executor_entry", spy_get_executor_entry
    )
    monkeypatch.setattr(
        service,
        "resolve_executor",
        lambda _name: pytest.fail(
            "resolve_executor should not be called for unsupported executors"
        ),
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

    result = delegation_worker.process_delegation_task(
        approval.task,
        service=service,
    )

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert registry_calls == ["not-real"]
    assert event_types == [DelegationEventType.FAILED.value]
    assert result["status"] == DelegationJobStatus.FAILED.value
    assert (
        result["failure"]["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_UNSUPPORTED.value
    )
    assert result["executor_id"] == "not_real"

    job = service.get_job(approval.job.delegation_id)
    summary = service.get_summary(approval.job.delegation_id)

    assert job is not None
    assert job.status == DelegationJobStatus.FAILED.value
    assert job.completed_at is not None
    assert job.error_message == "Unsupported executor id: not-real"

    assert summary is not None
    assert summary.status == DelegationJobStatus.FAILED.value
    assert summary.request_id == approval.job.delegation_id
    assert summary.thread_id == approval.job.thread_id
    assert summary.source_message_id == approval.task.source_message_id
    assert summary.project_id == approval.job.project_id
    assert summary.executor_id == "not_real"
    assert summary.title == approval.job.task_prompt
    assert summary.summary == "Unsupported executor id: not-real"
    assert summary.failure is not None
    assert (
        summary.failure["error_code"]
        == ErrorCode.DELEGATION_EXECUTOR_UNSUPPORTED.value
    )
    assert summary.error_message == "Unsupported executor id: not-real"
    assert summary.lineage["request_id"] == approval.job.delegation_id
    assert summary.lineage["executor_id"] == "not_real"


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
