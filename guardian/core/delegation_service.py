"""Thin delegation service for packet drafting and lifecycle state."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from guardian.db import models as db_models
from guardian.protocol_tokens import (
    DELEGATION_TERMINAL_STATUSES,
    DelegationJobStatus,
)
from guardian.tasks.types import (
    DelegationDraftRequest,
    DelegationPacket,
    DelegationSummary,
    DelegationTask,
)

QUEUE_NAME = os.getenv("DELEGATION_QUEUE_NAME", "codexify:queue:delegation")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    value_text = str(value).strip()
    return value_text or None


def _normalize_tags(tags: Any) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, (list, tuple, set)):
        result: list[str] = []
        for tag in tags:
            value = str(tag).strip()
            if value and value not in result:
                result.append(value)
        return result
    value = str(tags).strip()
    return [value] if value else []


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_context(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _packet_from_row(row: Any) -> DelegationPacket:
    return DelegationPacket(
        packet_id=str(getattr(row, "packet_id", "")),
        thread_id=getattr(row, "thread_id", None),
        conversation_id=getattr(row, "conversation_id", None),
        project_id=getattr(row, "project_id", None),
        repo_path=str(getattr(row, "repo_path", "") or ""),
        executor=str(getattr(row, "executor", "") or ""),
        status=str(getattr(row, "status", DelegationJobStatus.DRAFT.value)),
        task_prompt=str(getattr(row, "task_prompt", "") or ""),
        tags=_normalize_tags(getattr(row, "tags", None)),
        context=_normalize_context(getattr(row, "context_json", None)),
        created_at=_iso(getattr(row, "created_at", None)) or _now_iso(),
        approved_at=_iso(getattr(row, "approved_at", None)),
        completed_at=_iso(getattr(row, "completed_at", None)),
        error_message=_iso(getattr(row, "error_message", None)),
    )


def _summary_from_row(row: Any) -> DelegationSummary:
    summary_json = getattr(row, "summary_json", None) or {}
    if not isinstance(summary_json, dict):
        summary_json = {}
    return DelegationSummary.from_dict(
        {
            "delegation_id": getattr(row, "delegation_id", ""),
            "task_id": getattr(row, "task_id", ""),
            "status": getattr(
                row, "status", DelegationJobStatus.COMPLETED.value
            ),
            **summary_json,
            "created_at": _iso(getattr(row, "created_at", None)),
            "completed_at": _iso(getattr(row, "completed_at", None)),
            "error_message": _iso(getattr(row, "error_message", None)),
        }
    )


@dataclass(slots=True)
class DelegationJobRecord:
    delegation_id: str
    packet_id: str
    task_id: str
    thread_id: int | None
    conversation_id: str | None
    project_id: int | None
    repo_path: str
    executor: str
    status: str
    task_prompt: str
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    approved_at: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "packet_id": self.packet_id,
            "task_id": self.task_id,
            "thread_id": self.thread_id,
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "repo_path": self.repo_path,
            "executor": self.executor,
            "status": self.status,
            "task_prompt": self.task_prompt,
            "tags": list(self.tags),
            "context": dict(self.context),
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }

    def is_terminal(self) -> bool:
        return self.status in DELEGATION_TERMINAL_STATUSES


@dataclass(slots=True)
class DelegationApprovalResult:
    packet: DelegationPacket
    job: DelegationJobRecord
    task: DelegationTask
    enqueue_required: bool


@dataclass(slots=True)
class DelegationCancelResult:
    packet: DelegationPacket | None
    job: DelegationJobRecord
    changed: bool


class DelegationServiceError(RuntimeError):
    """Base service error."""


class DelegationNotFoundError(DelegationServiceError):
    """Raised when a packet or delegation cannot be found."""


class DelegationConflictError(DelegationServiceError):
    """Raised when an operation is incompatible with the current state."""


class DelegationService:
    """Owns delegation packet and job lifecycle transitions."""

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._packets: dict[str, DelegationPacket] = {}
        self._jobs: dict[str, DelegationJobRecord] = {}
        self._jobs_by_packet: dict[str, str] = {}
        self._jobs_by_task: dict[str, str] = {}
        self._summaries: dict[str, DelegationSummary] = {}

    def configure_db(self, db: Any | None) -> None:
        self._db = db
        self._packets.clear()
        self._jobs.clear()
        self._jobs_by_packet.clear()
        self._jobs_by_task.clear()
        self._summaries.clear()

    # ------------------------------------------------------------------
    # Draft packets
    # ------------------------------------------------------------------

    def draft_packet(self, request: DelegationDraftRequest) -> DelegationPacket:
        packet = DelegationPacket(
            packet_id=str(uuid.uuid4()),
            thread_id=request.thread_id,
            conversation_id=request.conversation_id,
            project_id=request.project_id,
            repo_path=_normalize_text(request.repo_path),
            executor=_normalize_text(request.executor),
            status=DelegationJobStatus.DRAFT.value,
            task_prompt=_normalize_text(request.user_intent),
            tags=_normalize_tags(request.tags),
            context=_normalize_context(request.context),
            created_at=_now_iso(),
        )
        if self._db is None:
            self._packets[packet.packet_id] = packet
            return packet

        with self._db.get_session() as session:
            row = db_models.DelegationPacket(
                packet_id=packet.packet_id,
                thread_id=packet.thread_id,
                conversation_id=packet.conversation_id,
                project_id=packet.project_id,
                repo_path=packet.repo_path,
                executor=packet.executor,
                status=packet.status,
                task_prompt=packet.task_prompt,
                tags=packet.tags,
                context_json=packet.context,
                created_at=_now(),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _packet_from_row(row)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_packet(self, packet_id: str) -> DelegationPacket | None:
        packet_id = str(packet_id or "").strip()
        if not packet_id:
            return None
        if self._db is None:
            return self._packets.get(packet_id)
        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationPacket)
                .filter_by(packet_id=packet_id)
                .first()
            )
            return _packet_from_row(row) if row else None

    def get_job(self, delegation_id: str) -> DelegationJobRecord | None:
        delegation_id = str(delegation_id or "").strip()
        if not delegation_id:
            return None
        if self._db is None:
            return self._jobs.get(delegation_id)
        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationJob)
                .filter_by(delegation_id=delegation_id)
                .first()
            )
            return self._job_from_row(session, row) if row else None

    def get_job_by_packet(self, packet_id: str) -> DelegationJobRecord | None:
        packet_id = str(packet_id or "").strip()
        if not packet_id:
            return None
        if self._db is None:
            delegation_id = self._jobs_by_packet.get(packet_id)
            if delegation_id is None:
                return None
            return self._jobs.get(delegation_id)
        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationJob)
                .filter_by(packet_id=packet_id)
                .first()
            )
            return self._job_from_row(session, row) if row else None

    def get_job_by_task(self, task_id: str) -> DelegationJobRecord | None:
        task_id = str(task_id or "").strip()
        if not task_id:
            return None
        if self._db is None:
            delegation_id = self._jobs_by_task.get(task_id)
            if delegation_id is None:
                return None
            return self._jobs.get(delegation_id)
        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationJob)
                .filter_by(task_id=task_id)
                .first()
            )
            return self._job_from_row(session, row) if row else None

    def get_summary(self, delegation_id: str) -> DelegationSummary | None:
        delegation_id = str(delegation_id or "").strip()
        if not delegation_id:
            return None
        if self._db is None:
            return self._summaries.get(delegation_id)
        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationSummary)
                .filter_by(delegation_id=delegation_id)
                .first()
            )
            return _summary_from_row(row) if row else None

    def _require_packet(self, packet_id: str) -> DelegationPacket:
        packet = self.get_packet(packet_id)
        if packet is None:
            raise DelegationNotFoundError(f"packet_not_found:{packet_id}")
        return packet

    def _require_job(self, delegation_id: str) -> DelegationJobRecord:
        job = self.get_job(delegation_id)
        if job is None:
            raise DelegationNotFoundError(
                f"delegation_not_found:{delegation_id}"
            )
        return job

    # ------------------------------------------------------------------
    # Approval / enqueue payloads
    # ------------------------------------------------------------------

    def approve_packet(self, packet_id: str) -> DelegationApprovalResult:
        packet = self._require_packet(packet_id)
        packet_status = str(packet.status or DelegationJobStatus.DRAFT.value)
        if packet_status in DELEGATION_TERMINAL_STATUSES:
            raise DelegationConflictError(
                f"packet_not_approvable:{packet.packet_id}:{packet_status}"
            )

        now_iso = _now_iso()
        existing_job = self.get_job_by_packet(packet.packet_id)
        if existing_job is None:
            job = DelegationJobRecord(
                delegation_id=str(uuid.uuid4()),
                packet_id=packet.packet_id,
                task_id=str(uuid.uuid4()),
                thread_id=packet.thread_id,
                conversation_id=packet.conversation_id,
                project_id=packet.project_id,
                repo_path=packet.repo_path,
                executor=packet.executor,
                status=DelegationJobStatus.APPROVED.value,
                task_prompt=packet.task_prompt,
                tags=list(packet.tags),
                context=dict(packet.context),
                created_at=now_iso,
                approved_at=now_iso,
            )
            packet.status = DelegationJobStatus.APPROVED.value
            packet.approved_at = packet.approved_at or now_iso
            self._save_packet(packet)
            self._save_job(job)
            enqueue_required = True
        else:
            job = existing_job
            if job.status in DELEGATION_TERMINAL_STATUSES:
                raise DelegationConflictError(
                    f"delegation_not_approvable:{job.delegation_id}:{job.status}"
                )
            enqueue_required = job.status == DelegationJobStatus.APPROVED.value
            if packet.status != job.status and job.status:
                packet.status = job.status
                if job.approved_at and not packet.approved_at:
                    packet.approved_at = job.approved_at
                self._save_packet(packet)
            self._save_job(job)

        task = self.build_enqueue_payload(job)
        return DelegationApprovalResult(
            packet=packet,
            job=job,
            task=task,
            enqueue_required=enqueue_required,
        )

    def build_enqueue_payload(self, job: DelegationJobRecord) -> DelegationTask:
        return DelegationTask(
            task_id=job.task_id,
            packet_id=job.packet_id,
            delegation_id=job.delegation_id,
            thread_id=job.thread_id,
            conversation_id=job.conversation_id,
            project_id=job.project_id,
            repo_path=job.repo_path,
            executor=job.executor,
            task_prompt=job.task_prompt,
            tags=list(job.tags),
            context=dict(job.context),
            status=DelegationJobStatus.QUEUED.value,
            origin="api:delegations.approve",
        )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def mark_job_queued(self, delegation_id: str) -> DelegationJobRecord:
        return self._transition_job(
            delegation_id,
            DelegationJobStatus.QUEUED.value,
            completed=False,
        )

    def mark_job_running(self, delegation_id: str) -> DelegationJobRecord:
        return self._transition_job(
            delegation_id,
            DelegationJobStatus.RUNNING.value,
            completed=False,
        )

    def mark_job_completed(
        self,
        delegation_id: str,
        *,
        summary: DelegationSummary | None = None,
    ) -> DelegationJobRecord:
        job = self._transition_job(
            delegation_id,
            DelegationJobStatus.COMPLETED.value,
            completed=True,
        )
        summary_packet = summary or self.build_summary_packet(job)
        self.record_summary(summary_packet)
        return job

    def mark_job_failed(
        self,
        delegation_id: str,
        *,
        error_message: str,
    ) -> DelegationJobRecord:
        return self._transition_job(
            delegation_id,
            DelegationJobStatus.FAILED.value,
            completed=True,
            error_message=error_message,
        )

    def cancel_delegation(self, delegation_id: str) -> DelegationCancelResult:
        job = self._require_job(delegation_id)
        if job.status in DELEGATION_TERMINAL_STATUSES:
            return DelegationCancelResult(
                packet=self.get_packet(job.packet_id),
                job=job,
                changed=False,
            )
        packet = self.get_packet(job.packet_id)
        updated = self._transition_job(
            delegation_id,
            DelegationJobStatus.CANCELLED.value,
            completed=True,
        )
        return DelegationCancelResult(
            packet=self.get_packet(updated.packet_id) or packet,
            job=updated,
            changed=True,
        )

    # ------------------------------------------------------------------
    # Summary packets
    # ------------------------------------------------------------------

    def build_summary_packet(
        self,
        job: DelegationJobRecord,
        *,
        summary: str | None = None,
        result: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> DelegationSummary:
        return DelegationSummary(
            delegation_id=job.delegation_id,
            task_id=job.task_id,
            status=_normalize_text(
                status or DelegationJobStatus.COMPLETED.value
            )
            or DelegationJobStatus.COMPLETED.value,
            summary=summary,
            result=dict(result or {}),
            metadata=dict(metadata or {}),
            error_message=error_message,
            created_at=_now_iso(),
            completed_at=_now_iso(),
        )

    def record_summary(self, summary: DelegationSummary) -> DelegationSummary:
        if self._db is None:
            self._summaries[summary.delegation_id] = summary
            return summary

        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationSummary)
                .filter_by(delegation_id=summary.delegation_id)
                .first()
            )
            if row is None:
                row = db_models.DelegationSummary(
                    delegation_id=summary.delegation_id,
                    task_id=summary.task_id,
                    status=summary.status,
                    summary_json=summary.to_dict(),
                    created_at=_now(),
                    completed_at=_now(),
                    error_message=summary.error_message,
                )
                session.add(row)
            else:
                row.task_id = summary.task_id
                row.status = summary.status
                row.summary_json = summary.to_dict()
                row.completed_at = _now()
                row.error_message = summary.error_message
            session.commit()
            session.refresh(row)
            return _summary_from_row(row)

    # ------------------------------------------------------------------
    # Internal storage helpers
    # ------------------------------------------------------------------

    def _save_packet(self, packet: DelegationPacket) -> None:
        if self._db is None:
            self._packets[packet.packet_id] = packet
            return

        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationPacket)
                .filter_by(packet_id=packet.packet_id)
                .first()
            )
            is_new = row is None
            if row is None:
                row = db_models.DelegationPacket(packet_id=packet.packet_id)
                session.add(row)
            row.thread_id = packet.thread_id
            row.conversation_id = packet.conversation_id
            row.project_id = packet.project_id
            row.repo_path = packet.repo_path
            row.executor = packet.executor
            row.status = packet.status
            row.task_prompt = packet.task_prompt
            row.tags = list(packet.tags)
            row.context_json = dict(packet.context)
            if is_new:
                row.created_at = _now()
            row.approved_at = (
                datetime.fromisoformat(packet.approved_at)
                if packet.approved_at
                else row.approved_at
            )
            row.completed_at = (
                datetime.fromisoformat(packet.completed_at)
                if packet.completed_at
                else row.completed_at
            )
            row.error_message = packet.error_message
            session.commit()

    def _save_job(self, job: DelegationJobRecord) -> None:
        if self._db is None:
            self._jobs[job.delegation_id] = job
            self._jobs_by_packet[job.packet_id] = job.delegation_id
            self._jobs_by_task[job.task_id] = job.delegation_id
            return

        with self._db.get_session() as session:
            row = (
                session.query(db_models.DelegationJob)
                .filter_by(delegation_id=job.delegation_id)
                .first()
            )
            if row is None:
                row = db_models.DelegationJob(
                    delegation_id=job.delegation_id,
                    packet_id=job.packet_id,
                    task_id=job.task_id,
                    thread_id=job.thread_id,
                    conversation_id=job.conversation_id,
                    project_id=job.project_id,
                    repo_path=job.repo_path,
                    executor=job.executor,
                    status=job.status,
                    task_prompt=job.task_prompt,
                    tags=list(job.tags),
                    created_at=_now(),
                )
                session.add(row)
            row.packet_id = job.packet_id
            row.task_id = job.task_id
            row.thread_id = job.thread_id
            row.conversation_id = job.conversation_id
            row.project_id = job.project_id
            row.repo_path = job.repo_path
            row.executor = job.executor
            row.status = job.status
            row.task_prompt = job.task_prompt
            row.tags = list(job.tags)
            row.approved_at = (
                datetime.fromisoformat(job.approved_at)
                if job.approved_at
                else row.approved_at
            )
            row.queued_at = (
                datetime.fromisoformat(job.queued_at)
                if job.queued_at
                else row.queued_at
            )
            row.started_at = (
                datetime.fromisoformat(job.started_at)
                if job.started_at
                else row.started_at
            )
            row.completed_at = (
                datetime.fromisoformat(job.completed_at)
                if job.completed_at
                else row.completed_at
            )
            row.error_message = job.error_message
            session.commit()

    def _job_from_row(
        self, session: Any, row: Any
    ) -> DelegationJobRecord | None:
        if row is None:
            return None
        packet_row = (
            session.query(db_models.DelegationPacket)
            .filter_by(packet_id=getattr(row, "packet_id", ""))
            .first()
        )
        context = (
            dict(getattr(packet_row, "context_json", {}) or {})
            if packet_row is not None
            else {}
        )
        return DelegationJobRecord(
            delegation_id=str(getattr(row, "delegation_id", "")),
            packet_id=str(getattr(row, "packet_id", "")),
            task_id=str(getattr(row, "task_id", "")),
            thread_id=getattr(row, "thread_id", None),
            conversation_id=getattr(row, "conversation_id", None),
            project_id=getattr(row, "project_id", None),
            repo_path=str(getattr(row, "repo_path", "") or ""),
            executor=str(getattr(row, "executor", "") or ""),
            status=str(
                getattr(row, "status", DelegationJobStatus.APPROVED.value)
            ),
            task_prompt=str(getattr(row, "task_prompt", "") or ""),
            tags=_normalize_tags(getattr(row, "tags", None)),
            context=context,
            created_at=_iso(getattr(row, "created_at", None)) or _now_iso(),
            approved_at=_iso(getattr(row, "approved_at", None)),
            queued_at=_iso(getattr(row, "queued_at", None)),
            started_at=_iso(getattr(row, "started_at", None)),
            completed_at=_iso(getattr(row, "completed_at", None)),
            error_message=_iso(getattr(row, "error_message", None)),
        )

    def _transition_job(
        self,
        delegation_id: str,
        status: str,
        *,
        completed: bool,
        error_message: str | None = None,
    ) -> DelegationJobRecord:
        job = self._require_job(delegation_id)
        if job.status in DELEGATION_TERMINAL_STATUSES and job.status != status:
            return job
        if job.status == status and job.status in DELEGATION_TERMINAL_STATUSES:
            return job

        now_iso = _now_iso()
        job.status = status
        if status == DelegationJobStatus.QUEUED.value and not job.queued_at:
            job.queued_at = now_iso
        elif status == DelegationJobStatus.RUNNING.value and not job.started_at:
            job.started_at = now_iso
        elif completed and not job.completed_at:
            job.completed_at = now_iso
        if status == DelegationJobStatus.APPROVED.value and not job.approved_at:
            job.approved_at = now_iso
        if error_message is not None:
            job.error_message = error_message
        packet = self.get_packet(job.packet_id)
        if packet is not None:
            packet.status = status
            if (
                status == DelegationJobStatus.APPROVED.value
                and not packet.approved_at
            ):
                packet.approved_at = now_iso
            if completed and not packet.completed_at:
                packet.completed_at = now_iso
            if error_message is not None:
                packet.error_message = error_message
            self._save_packet(packet)
        self._save_job(job)
        if status in DELEGATION_TERMINAL_STATUSES and not job.completed_at:
            job.completed_at = now_iso
            self._save_job(job)
        return job


__all__ = [
    "QUEUE_NAME",
    "DelegationApprovalResult",
    "DelegationCancelResult",
    "DelegationConflictError",
    "DelegationJobRecord",
    "DelegationNotFoundError",
    "DelegationService",
]
