from __future__ import annotations

import json

from guardian.core.delegation_service import DelegationService
from guardian.core.executors.base import ExecutorResult
from guardian.core.executors.codex_executor import CodexExecutor
from guardian.protocol_tokens import (
    DELEGATION_SUMMARY_OUTCOME_TYPE,
    DelegationExecutorName,
    DelegationJobStatus,
)
from guardian.tasks.types import DelegationDraftRequest


def _request() -> DelegationDraftRequest:
    return DelegationDraftRequest(
        thread_id=42,
        conversation_id="conversation-7",
        project_id=9,
        repo_path="/workspace/codexify",
        executor=DelegationExecutorName.CODEX.value,
        user_intent="Map the delegation lane end-to-end.",
        tags=["backend", "backend", "delegation"],
        context={"thread_subject": "delegation slice"},
    )


def test_draft_packet_construction() -> None:
    service = DelegationService()

    packet = service.draft_packet(_request())

    assert packet.packet_id
    assert packet.status == DelegationJobStatus.DRAFT.value
    assert packet.thread_id == 42
    assert packet.conversation_id == "conversation-7"
    assert packet.project_id == 9
    assert packet.repo_path == "/workspace/codexify"
    assert packet.executor == DelegationExecutorName.CODEX.value
    assert packet.task_prompt == "Map the delegation lane end-to-end."
    assert packet.tags == ["backend", "delegation"]
    assert packet.context == {"thread_subject": "delegation slice"}


def test_approval_creates_job_and_enqueue_payload() -> None:
    service = DelegationService()
    packet = service.draft_packet(_request())

    approval = service.approve_packet(packet.packet_id)

    assert approval.enqueue_required is True
    assert approval.packet.packet_id == packet.packet_id
    assert approval.job.packet_id == packet.packet_id
    assert approval.job.delegation_id
    assert approval.job.status == DelegationJobStatus.APPROVED.value
    assert approval.job.executor == DelegationExecutorName.CODEX.value
    assert approval.job.approved_at is not None
    assert approval.task.type == "delegation.task"
    assert approval.task.task_id == approval.job.task_id
    assert approval.task.packet_id == packet.packet_id
    assert approval.task.delegation_id == approval.job.delegation_id
    assert approval.task.status == DelegationJobStatus.QUEUED.value
    assert approval.task.task_prompt == packet.task_prompt
    assert approval.task.context == packet.context

    executor = service.resolve_executor(approval.job.executor)
    assert isinstance(executor, CodexExecutor)

    queued_job = service.mark_job_queued(approval.job.delegation_id)
    assert queued_job.status == DelegationJobStatus.QUEUED.value
    assert queued_job.queued_at is not None


def test_canonical_summary_normalization_from_expected_final_format() -> None:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)
    service.mark_job_queued(approval.job.delegation_id)

    final_text = json.dumps(
        {
            "outcomeType": "task_summary",
            "title": "Ignored in favor of packet prompt",
            "summary": "Codex completed the delegation lane.",
            "files_changed": [
                "guardian/core/delegation_service.py",
                "guardian/workers/delegation_worker.py",
            ],
            "commands_run": [
                "pytest -v tests/core/test_codex_executor.py",
            ],
            "key_changes": [
                "streamed Codex output",
                "normalized terminal summary",
            ],
            "unresolved_questions": [],
            "tags": ["backend", "backend", "codex"],
        }
    )
    executor_result = ExecutorResult(
        delegation_id=approval.job.delegation_id,
        task_id=approval.job.task_id,
        status=DelegationJobStatus.COMPLETED.value,
        summary=final_text,
        final_text=final_text,
        stdout=final_text,
        raw_transcript=f"[stdout] {final_text}\n",
        result={
            "tags": ["delegation", "backend", "delegation"],
            "raw_transcript": f"[stdout] {final_text}\n",
        },
        metadata={
            "executor": DelegationExecutorName.CODEX.value,
            "repo_path": packet.repo_path,
            "tags": ["backend", "delegation", "delegation"],
        },
    )

    summary = service.normalize_executor_result(
        approval.job,
        executor_result,
        packet=packet,
    )

    assert summary.outcome_type == DELEGATION_SUMMARY_OUTCOME_TYPE
    assert summary.title == approval.job.task_prompt
    assert summary.summary == "Codex completed the delegation lane."
    assert summary.files_changed == [
        "guardian/core/delegation_service.py",
        "guardian/workers/delegation_worker.py",
    ]
    assert summary.commands_run == [
        "pytest -v tests/core/test_codex_executor.py"
    ]
    assert summary.key_changes == [
        "streamed Codex output",
        "normalized terminal summary",
    ]
    assert summary.unresolved_questions == []
    assert summary.tags == ["backend", "delegation", "codex"]
    assert summary.raw_transcript == f"[stdout] {final_text}\n"
    assert summary.result["failure"] is None
    assert summary.metadata["executor"] == DelegationExecutorName.CODEX.value


def test_summary_normalization_falls_back_to_raw_final_text() -> None:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)

    final_text = "Codex output without structure"
    executor_result = ExecutorResult(
        delegation_id=approval.job.delegation_id,
        task_id=approval.job.task_id,
        status=DelegationJobStatus.COMPLETED.value,
        summary=final_text,
        final_text=final_text,
        stdout=final_text,
        raw_transcript=final_text,
        metadata={"tags": ["delegation", "delegation"]},
    )

    summary = service.normalize_executor_result(
        approval.job,
        executor_result,
        packet=packet,
    )

    assert summary.title == approval.job.task_prompt
    assert summary.summary == final_text
    assert summary.files_changed == []
    assert summary.commands_run == []
    assert summary.key_changes == []
    assert summary.unresolved_questions == []
    assert summary.tags == ["backend", "delegation"]
    assert summary.outcome_type == DELEGATION_SUMMARY_OUTCOME_TYPE


def test_canonical_summary_shape_defaults() -> None:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)
    service.mark_job_queued(approval.job.delegation_id)

    summary = service.build_summary_packet(approval.job)

    assert summary.delegation_id == approval.job.delegation_id
    assert summary.task_id == approval.job.task_id
    assert summary.status == DelegationJobStatus.COMPLETED.value
    assert summary.outcome_type == DELEGATION_SUMMARY_OUTCOME_TYPE
    assert summary.title == approval.job.task_prompt
    assert summary.summary is None
    assert summary.files_changed == []
    assert summary.commands_run == []
    assert summary.key_changes == []
    assert summary.unresolved_questions == []
    assert summary.tags == ["backend", "delegation"]
    assert summary.result == {}
    assert summary.metadata == {}
    assert summary.error_message is None
    assert summary.created_at
    assert summary.completed_at
