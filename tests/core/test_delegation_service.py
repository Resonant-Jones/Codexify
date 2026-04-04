from __future__ import annotations

from guardian.core.delegation_service import DelegationService
from guardian.protocol_tokens import DelegationJobStatus
from guardian.tasks.types import DelegationDraftRequest


def _request() -> DelegationDraftRequest:
    return DelegationDraftRequest(
        thread_id=42,
        conversation_id="conversation-7",
        project_id=9,
        repo_path="/workspace/codexify",
        executor="stub",
        user_intent="Map the delegation lane end-to-end.",
        tags=["backend", "delegation"],
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
    assert packet.executor == "stub"
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
    assert approval.job.approved_at is not None
    assert approval.task.type == "delegation.task"
    assert approval.task.task_id == approval.job.task_id
    assert approval.task.packet_id == packet.packet_id
    assert approval.task.delegation_id == approval.job.delegation_id
    assert approval.task.status == DelegationJobStatus.QUEUED.value
    assert approval.task.task_prompt == packet.task_prompt
    assert approval.task.context == packet.context

    queued_job = service.mark_job_queued(approval.job.delegation_id)
    assert queued_job.status == DelegationJobStatus.QUEUED.value
    assert queued_job.queued_at is not None


def test_canonical_summary_shape_defaults() -> None:
    service = DelegationService()
    packet = service.draft_packet(_request())
    approval = service.approve_packet(packet.packet_id)
    service.mark_job_queued(approval.job.delegation_id)

    summary = service.build_summary_packet(approval.job)

    assert summary.delegation_id == approval.job.delegation_id
    assert summary.task_id == approval.job.task_id
    assert summary.status == DelegationJobStatus.COMPLETED.value
    assert summary.summary is None
    assert summary.result == {}
    assert summary.metadata == {}
    assert summary.error_message is None
    assert summary.created_at
    assert summary.completed_at
