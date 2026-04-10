"""Thin delegation service for packet drafting and lifecycle state."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from guardian.core.executors.base import (
    CodeExecutor,
    CodexifyExecutorContextBundle,
    CodexifyExecutorRequest,
    ExecutorFailure,
    ExecutorResult,
)
from guardian.core.executors.registry import ExecutorId, get_executor_entry
from guardian.db import models as db_models
from guardian.protocol_tokens import (
    DELEGATION_SUMMARY_OUTCOME_TYPE,
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


def _preserve_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalize_context(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_identifier(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return text


def _normalize_executor_id(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _dedupe_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        items = raw
    elif isinstance(raw, str):
        items = [part.strip() for part in raw.split(",")]
    else:
        items = [raw]
    result: list[str] = []
    for item in items:
        value = _normalize_text(item)
        if value and value not in result:
            result.append(value)
    return result


_SUMMARY_SECTION_HEADERS: dict[str, str] = {
    "title": "title",
    "summary": "summary",
    "files changed": "files_changed",
    "files_changed": "files_changed",
    "commands run": "commands_run",
    "commands_run": "commands_run",
    "key changes": "key_changes",
    "key_changes": "key_changes",
    "unresolved questions": "unresolved_questions",
    "unresolved_questions": "unresolved_questions",
    "tags": "tags",
    "outcome type": "outcome_type",
    "outcome_type": "outcome_type",
}


def _flatten_summary_list(raw: Any) -> list[str]:
    values = _dedupe_text_list(raw)
    result: list[str] = []
    for value in values:
        if value.lower() in {"none", "n/a", "na"}:
            continue
        if value not in result:
            result.append(value)
    return result


def _parse_structured_summary_text(
    text: str | None,
) -> dict[str, Any]:
    stripped = _normalize_text(text)
    parsed: dict[str, Any] = {
        "title": None,
        "summary": None,
        "files_changed": [],
        "commands_run": [],
        "key_changes": [],
        "unresolved_questions": [],
        "tags": [],
        "outcome_type": DELEGATION_SUMMARY_OUTCOME_TYPE,
    }
    if not stripped:
        return parsed

    try:
        decoded = json.loads(stripped)
    except Exception:
        decoded = None

    if isinstance(decoded, dict):
        parsed["title"] = (
            _normalize_text(decoded.get("title") or decoded.get("name")) or None
        )
        parsed["summary"] = (
            _normalize_text(
                decoded.get("summary")
                or decoded.get("final_text")
                or decoded.get("text")
            )
            or None
        )
        parsed["files_changed"] = _flatten_summary_list(
            decoded.get("files_changed") or decoded.get("filesChanged")
        )
        parsed["commands_run"] = _flatten_summary_list(
            decoded.get("commands_run") or decoded.get("commandsRun")
        )
        parsed["key_changes"] = _flatten_summary_list(
            decoded.get("key_changes") or decoded.get("keyChanges")
        )
        parsed["unresolved_questions"] = _flatten_summary_list(
            decoded.get("unresolved_questions")
            or decoded.get("unresolvedQuestions")
        )
        parsed["tags"] = _flatten_summary_list(decoded.get("tags"))
        parsed["outcome_type"] = (
            _normalize_text(
                decoded.get("outcome_type") or decoded.get("outcomeType")
            )
            or DELEGATION_SUMMARY_OUTCOME_TYPE
        )
        return parsed

    sections: dict[str, list[str]] = {
        "files_changed": [],
        "commands_run": [],
        "key_changes": [],
        "unresolved_questions": [],
        "tags": [],
    }
    current: str | None = None
    summary_lines: list[str] = []

    for raw_line in stripped.splitlines():
        line = raw_line.rstrip()
        normalized = line.strip().lower()
        header = None
        if ":" in normalized:
            candidate = normalized.split(":", 1)[0].strip()
            header = _SUMMARY_SECTION_HEADERS.get(candidate)

        if header:
            current = header
            remainder = line.split(":", 1)[1].strip() if ":" in line else ""
            if remainder:
                if header == "title":
                    parsed["title"] = _normalize_text(remainder) or None
                elif header == "summary":
                    summary_lines.append(remainder)
                elif header == "outcome_type":
                    parsed["outcome_type"] = (
                        _normalize_text(remainder)
                        or DELEGATION_SUMMARY_OUTCOME_TYPE
                    )
                else:
                    sections[header].append(remainder)
            continue

        if current == "summary":
            summary_lines.append(line)
        elif current in sections:
            sections[current].append(line)

    def _flatten(values: list[str]) -> list[str]:
        items: list[str] = []
        for line in values:
            candidate = line.strip().lstrip("-*• ").strip()
            if not candidate:
                continue
            parts = [candidate]
            if "," in candidate and "\n" not in candidate:
                parts = [part.strip() for part in candidate.split(",")]
            for part in parts:
                value = _normalize_text(part)
                if not value or value.lower() in {"none", "n/a", "na"}:
                    continue
                if value not in items:
                    items.append(value)
        return items

    parsed["files_changed"] = _flatten(sections["files_changed"])
    parsed["commands_run"] = _flatten(sections["commands_run"])
    parsed["key_changes"] = _flatten(sections["key_changes"])
    parsed["unresolved_questions"] = _flatten(sections["unresolved_questions"])
    parsed["tags"] = _flatten(sections["tags"])
    if summary_lines:
        parsed["summary"] = (
            "\n".join(line for line in summary_lines if line).strip() or None
        )
    if parsed["summary"] is None:
        parsed["summary"] = stripped
    return parsed


def _merge_text_lists(*values: Any) -> list[str]:
    merged: list[str] = []
    for raw in values:
        for value in _dedupe_text_list(raw):
            if value not in merged:
                merged.append(value)
    return merged


def _source_message_id_from_context(*contexts: Any) -> int | str | None:
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for key in (
            "source_message_id",
            "sourceMessageId",
            "message_id",
            "messageId",
        ):
            normalized = _normalize_identifier(context.get(key))
            if normalized is not None:
                return normalized
    return None


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

    def resolve_executor(self, executor_name: str) -> CodeExecutor:
        normalized = _normalize_executor_id(executor_name)
        try:
            entry = get_executor_entry(normalized)
        except KeyError as exc:
            raise DelegationConflictError(
                f"unsupported_executor:{normalized or '<missing>'}"
            ) from exc

        if entry.executor_id != ExecutorId.CODEX:
            raise DelegationConflictError(
                f"unsupported_executor:{entry.executor_id.value}"
            )

        from guardian.core.executors.codex_executor import CodexExecutor

        return CodexExecutor()

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
        # Validate the executor choice before creating durable queue state.
        self.resolve_executor(packet.executor)

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

        task = self.build_enqueue_payload(job, packet=packet)
        return DelegationApprovalResult(
            packet=packet,
            job=job,
            task=task,
            enqueue_required=enqueue_required,
        )

    def build_enqueue_payload(
        self,
        job: DelegationJobRecord,
        *,
        packet: DelegationPacket | None = None,
    ) -> DelegationTask:
        packet = packet or self.get_packet(job.packet_id)
        source_message_id = _source_message_id_from_context(
            job.context,
            packet.context if packet is not None else None,
        )
        return DelegationTask(
            task_id=job.task_id,
            packet_id=job.packet_id,
            delegation_id=job.delegation_id,
            thread_id=job.thread_id,
            source_message_id=source_message_id
            if isinstance(source_message_id, int)
            else None,
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

    def build_executor_request(
        self,
        job: DelegationJobRecord,
        *,
        packet: DelegationPacket | None = None,
        task: DelegationTask | None = None,
    ) -> CodexifyExecutorRequest:
        packet = packet or self.get_packet(job.packet_id)
        task_context = dict(task.context) if task is not None else {}
        packet_context = dict(packet.context) if packet is not None else {}
        merged_context: dict[str, Any] = {
            **packet_context,
            **task_context,
            **job.context,
        }
        source_message_id = (
            task.source_message_id
            if task is not None and task.source_message_id is not None
            else _source_message_id_from_context(
                task_context,
                job.context,
                packet_context,
                merged_context,
            )
        )
        workspace_path = _normalize_text(job.repo_path)
        context_bundle = CodexifyExecutorContextBundle(
            workspace_path=workspace_path or None,
            thread_context=dict(merged_context),
            message_context=_normalize_context(
                merged_context.get("message_context")
            ),
            routing=_normalize_context(merged_context.get("routing")),
            artifacts=list(merged_context.get("artifacts") or []),
            metadata={
                "packet_id": packet.packet_id if packet is not None else None,
                "delegation_id": job.delegation_id,
                "task_id": job.task_id,
                "executor_id": job.executor,
                "thread_id": job.thread_id,
                "source_message_id": source_message_id,
                "project_id": job.project_id,
            },
            raw=dict(merged_context),
        )
        tags = _normalize_tags(job.tags)
        request = CodexifyExecutorRequest(
            request_id=job.delegation_id,
            thread_id=job.thread_id,
            source_message_id=source_message_id,
            project_id=job.project_id,
            executor_id=job.executor,
            title=packet.task_prompt if packet is not None else job.task_prompt,
            canonical_task_prompt=job.task_prompt,
            context_bundle=context_bundle,
            permissions=_normalize_context(merged_context.get("permissions")),
            tags=tags,
            delegation_id=job.delegation_id,
            task_id=job.task_id,
            repo_path=job.repo_path,
            executor=job.executor,
            task_prompt=job.task_prompt,
            context=merged_context,
            metadata={
                "packet_id": packet.packet_id if packet is not None else None,
                "delegation_id": job.delegation_id,
                "task_id": job.task_id,
                "thread_id": job.thread_id,
                "source_message_id": source_message_id,
                "project_id": job.project_id,
                "executor_id": job.executor,
                "title": packet.task_prompt
                if packet is not None
                else job.task_prompt,
                "tags": tags,
                "repo_path": job.repo_path,
            },
        )
        request.metadata.setdefault("executor", job.executor)
        request.metadata.setdefault("request_id", request.request_id)
        request.metadata.setdefault("thread_id", request.thread_id)
        request.metadata.setdefault(
            "source_message_id", request.source_message_id
        )
        request.metadata.setdefault("project_id", request.project_id)
        request.metadata.setdefault("executor_id", request.executor_id)
        request.metadata.setdefault("title", request.title)
        request.metadata.setdefault("tags", list(request.tags))
        request.metadata.setdefault("repo_path", request.repo_path)
        return request

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
        summary: DelegationSummary | None = None,
    ) -> DelegationJobRecord:
        job = self._transition_job(
            delegation_id,
            DelegationJobStatus.FAILED.value,
            completed=True,
            error_message=error_message,
        )
        summary_packet = summary or self.build_summary_packet(
            job,
            status=DelegationJobStatus.FAILED.value,
            error_message=error_message,
            result={"failure": {"message": error_message}},
        )
        self.record_summary(summary_packet)
        return job

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
        packet = self.get_packet(job.packet_id)
        result_payload = dict(result or {})
        metadata_payload = dict(metadata or {})
        parsed = _parse_structured_summary_text(
            summary
            or result_payload.get("summary")
            or result_payload.get("final_text")
            or result_payload.get("raw_transcript")
        )

        request_id = (
            _normalize_text(
                result_payload.get("request_id")
                or result_payload.get("requestId")
                or metadata_payload.get("request_id")
                or metadata_payload.get("requestId")
                or job.delegation_id
            )
            or job.delegation_id
        )
        thread_id = _normalize_identifier(
            result_payload.get("thread_id")
            or result_payload.get("threadId")
            or metadata_payload.get("thread_id")
            or metadata_payload.get("threadId")
            or job.thread_id
        )
        source_message_id = _normalize_identifier(
            result_payload.get("source_message_id")
            or result_payload.get("sourceMessageId")
            or metadata_payload.get("source_message_id")
            or metadata_payload.get("sourceMessageId")
            or _source_message_id_from_context(
                job.context,
                packet.context if packet is not None else None,
            )
        )
        project_id = _normalize_identifier(
            result_payload.get("project_id")
            or result_payload.get("projectId")
            or metadata_payload.get("project_id")
            or metadata_payload.get("projectId")
            or job.project_id
        )
        executor_id = _normalize_executor_id(
            result_payload.get("executor_id")
            or result_payload.get("executorId")
            or metadata_payload.get("executor_id")
            or metadata_payload.get("executorId")
            or job.executor
        ) or _normalize_executor_id(job.executor)
        title = (
            _normalize_text(
                result_payload.get("title")
                or metadata_payload.get("title")
                or job.task_prompt
            )
            or job.task_prompt
        )
        normalized_status = (
            _normalize_text(
                status
                or result_payload.get("status")
                or metadata_payload.get("status")
                or DelegationJobStatus.COMPLETED.value
            )
            or DelegationJobStatus.COMPLETED.value
        )
        outcome_type = (
            _normalize_text(
                result_payload.get("outcome_type")
                or result_payload.get("outcomeType")
                or metadata_payload.get("outcome_type")
                or metadata_payload.get("outcomeType")
                or parsed.get("outcome_type")
                or DELEGATION_SUMMARY_OUTCOME_TYPE
            )
            or DELEGATION_SUMMARY_OUTCOME_TYPE
        )
        files_changed = _merge_text_lists(
            result_payload.get("files_changed"),
            result_payload.get("filesChanged"),
            parsed.get("files_changed"),
        )
        commands_run = _merge_text_lists(
            result_payload.get("commands_run"),
            result_payload.get("commandsRun"),
            parsed.get("commands_run"),
        )
        key_changes = _merge_text_lists(
            result_payload.get("key_changes"),
            result_payload.get("keyChanges"),
            parsed.get("key_changes"),
        )
        unresolved_questions = _merge_text_lists(
            result_payload.get("unresolved_questions"),
            result_payload.get("unresolvedQuestions"),
            parsed.get("unresolved_questions"),
        )
        packet_tags = _normalize_tags(job.tags)
        request_tags = _merge_text_lists(
            result_payload.get("tags"),
            metadata_payload.get("tags"),
            parsed.get("tags"),
        )
        tags = _normalize_tags([*packet_tags, *request_tags])
        raw_transcript = _preserve_text(
            result_payload.get("raw_transcript")
            or result_payload.get("rawTranscript")
            or metadata_payload.get("raw_transcript")
            or metadata_payload.get("rawTranscript")
        )
        transcript = (
            _normalize_text(
                result_payload.get("transcript")
                or result_payload.get("stdout")
                or parsed.get("summary")
                or summary
            )
            or None
        )
        canonical_summary = (
            _normalize_text(
                parsed.get("summary")
                or summary
                or result_payload.get("summary")
                or result_payload.get("final_text")
                or transcript
            )
            or None
        )
        failure_payload = result_payload.get("failure")
        if failure_payload is None:
            failure_payload = metadata_payload.get("failure")
        if failure_payload is None and error_message:
            failure_payload = {"message": error_message}
        if isinstance(failure_payload, ExecutorFailure):
            failure_payload = failure_payload.to_dict()
        normalized_failure = (
            dict(failure_payload) if isinstance(failure_payload, dict) else None
        )
        normalized_error_message = (
            _normalize_text(
                error_message
                or (normalized_failure or {}).get("message")
                or result_payload.get("error_message")
            )
            or None
        )
        lineage_payload = {
            "request_id": request_id,
            "delegation_id": job.delegation_id,
            "task_id": job.task_id,
            "thread_id": thread_id,
            "source_message_id": source_message_id,
            "project_id": project_id,
            "executor_id": executor_id,
            "title": title,
            "status": normalized_status,
            "outcome_type": outcome_type,
            "tags": list(tags),
        }
        enrich_payload = bool(
            result_payload
            or metadata_payload
            or summary
            or status
            or error_message
        )
        if enrich_payload:
            result_payload.update(
                {
                    "request_id": request_id,
                    "thread_id": thread_id,
                    "source_message_id": source_message_id,
                    "project_id": project_id,
                    "executor_id": executor_id,
                    "title": title,
                    "summary": canonical_summary,
                    "status": normalized_status,
                    "outcome_type": outcome_type,
                    "outcomeType": outcome_type,
                    "files_changed": files_changed,
                    "commands_run": commands_run,
                    "key_changes": key_changes,
                    "unresolved_questions": unresolved_questions,
                    "tags": tags,
                    "raw_transcript": raw_transcript,
                    "transcript": transcript,
                    "failure": normalized_failure,
                    "error_message": normalized_error_message,
                    "lineage": lineage_payload,
                }
            )
            metadata_payload.update(
                {
                    "request_id": request_id,
                    "thread_id": thread_id,
                    "source_message_id": source_message_id,
                    "project_id": project_id,
                    "executor_id": executor_id,
                    "title": title,
                    "status": normalized_status,
                    "outcome_type": outcome_type,
                    "tags": tags,
                    "error_message": normalized_error_message,
                    "lineage": lineage_payload,
                }
            )
        return DelegationSummary(
            request_id=request_id,
            delegation_id=job.delegation_id,
            task_id=job.task_id,
            thread_id=thread_id,
            source_message_id=source_message_id,
            project_id=project_id,
            executor_id=executor_id,
            title=title,
            status=normalized_status,
            outcome_type=outcome_type,
            summary=canonical_summary,
            files_changed=files_changed,
            commands_run=commands_run,
            key_changes=key_changes,
            unresolved_questions=unresolved_questions,
            tags=tags,
            result=result_payload,
            metadata=metadata_payload,
            raw_transcript=raw_transcript,
            transcript=transcript,
            failure=normalized_failure,
            error_message=normalized_error_message,
            lineage=lineage_payload,
            created_at=_now_iso(),
            completed_at=_now_iso(),
        )

    def normalize_executor_result(
        self,
        job: DelegationJobRecord,
        executor_result: ExecutorResult,
        *,
        packet: DelegationPacket | None = None,
    ) -> DelegationSummary:
        packet = packet or self.get_packet(job.packet_id)
        canonical_summary = executor_result.canonical_task_summary
        result_payload = dict(executor_result.result or {})
        result_payload.update(
            {
                "request_id": executor_result.request_id,
                "thread_id": executor_result.thread_id,
                "source_message_id": executor_result.source_message_id,
                "project_id": executor_result.project_id,
                "executor_id": executor_result.executor_id,
                "title": executor_result.title,
                "final_text": executor_result.final_text,
                "summary": executor_result.summary,
                "stdout": executor_result.stdout,
                "stderr": executor_result.stderr,
                "raw_transcript": executor_result.raw_transcript,
                "files_changed": list(executor_result.files_changed),
                "commands_run": list(executor_result.commands_run),
                "output_chunks": [
                    chunk.to_dict() for chunk in executor_result.output_chunks
                ],
                "failure": (
                    executor_result.failure.to_dict()
                    if executor_result.failure is not None
                    else None
                ),
                "status": executor_result.status,
                "outcome_type": canonical_summary.outcome_type,
                "lineage": dict(canonical_summary.lineage),
            }
        )
        metadata_payload = dict(executor_result.metadata or {})
        metadata_payload.setdefault("executor", job.executor)
        metadata_payload.setdefault("repo_path", job.repo_path)
        metadata_payload.setdefault("task_id", job.task_id)
        metadata_payload.setdefault("delegation_id", job.delegation_id)
        metadata_payload.setdefault("request_id", executor_result.request_id)
        metadata_payload.setdefault("thread_id", executor_result.thread_id)
        metadata_payload.setdefault(
            "source_message_id", executor_result.source_message_id
        )
        metadata_payload.setdefault("project_id", executor_result.project_id)
        metadata_payload.setdefault("executor_id", executor_result.executor_id)
        metadata_payload.setdefault("title", executor_result.title)
        metadata_payload.setdefault("lineage", dict(canonical_summary.lineage))
        if packet is not None:
            metadata_payload.setdefault("packet_id", packet.packet_id)
            metadata_payload.setdefault("title", packet.task_prompt)
        if executor_result.failure is not None:
            metadata_payload.setdefault(
                "failure", executor_result.failure.to_dict()
            )
        return self.build_summary_packet(
            job,
            summary=executor_result.summary or executor_result.final_text,
            result=result_payload,
            metadata=metadata_payload,
            status=executor_result.status,
            error_message=executor_result.error_message
            or (
                executor_result.failure.message
                if executor_result.failure is not None
                else None
            ),
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
