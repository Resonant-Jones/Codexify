"""Canonical contract types and lifecycle helpers for coding work orders.

This module defines the durable control-plane contract seam for task-board
work-order state. It does not dispatch workers, allocate worktrees, run Git
commands, or expose route behavior by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

WorkOrderStatus = Literal[
    "draft",
    "ready",
    "leased",
    "running",
    "validating",
    "retrying",
    "passed",
    "failed",
    "blocked",
    "escalated",
    "merge_ready",
    "merged",
    "archived",
    "cancelled",
]

WORK_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        "draft",
        "ready",
        "leased",
        "running",
        "validating",
        "retrying",
        "passed",
        "failed",
        "blocked",
        "escalated",
        "merge_ready",
        "merged",
        "archived",
        "cancelled",
    }
)

WORK_ORDER_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "failed",
        "merged",
        "archived",
        "cancelled",
    }
)

WORK_ORDER_ACTIVE_STATUSES: frozenset[str] = frozenset(
    WORK_ORDER_STATUSES.difference(WORK_ORDER_TERMINAL_STATUSES)
)

WORK_ORDER_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"leased", "cancelled"}),
    "leased": frozenset({"running", "cancelled"}),
    "running": frozenset(
        {"validating", "failed", "blocked", "escalated", "cancelled"}
    ),
    "validating": frozenset({"retrying", "passed", "failed", "cancelled"}),
    "retrying": frozenset({"running", "cancelled"}),
    "passed": frozenset({"merge_ready", "cancelled"}),
    "blocked": frozenset({"ready", "cancelled"}),
    "escalated": frozenset({"ready", "cancelled"}),
    "merge_ready": frozenset({"merged", "cancelled"}),
    "failed": frozenset({"archived"}),
    "merged": frozenset({"archived"}),
    "cancelled": frozenset({"archived"}),
    "archived": frozenset(),
}


@dataclass(frozen=True)
class WorkOrderValidationResult:
    ok: bool
    reason: str | None = None
    reason_code: str | None = None


@dataclass(frozen=True)
class WorkOrderCreate:
    campaign_id: str | None
    title: str
    objective: str
    scope: str | None = None
    status: str | None = None
    priority: int = 0
    created_by: str | None = None
    assigned_worker_id: str | None = None
    source_thread_id: str | None = None
    source_message_id: str | None = None
    dependency_ids: list[str] = field(default_factory=list)
    file_scope: list[str] = field(default_factory=list)
    validation_command: str | None = None
    adapter_kind: str | None = None
    max_validation_attempts: int = 1
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    require_human_review_before_merge: bool = True
    blocked_reason: str | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "title": self.title,
            "objective": self.objective,
            "scope": self.scope,
            "status": self.status,
            "priority": self.priority,
            "created_by": self.created_by,
            "assigned_worker_id": self.assigned_worker_id,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "dependency_ids": list(self.dependency_ids),
            "file_scope": list(self.file_scope),
            "validation_command": self.validation_command,
            "adapter_kind": self.adapter_kind,
            "max_validation_attempts": self.max_validation_attempts,
            "require_worktree_lease": self.require_worktree_lease,
            "commit_after_validation": self.commit_after_validation,
            "require_human_review_before_merge": self.require_human_review_before_merge,
            "blocked_reason": self.blocked_reason,
            "extra_meta": dict(self.extra_meta),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkOrderCreate:
        data = dict(payload or {})
        return cls(
            campaign_id=_coerce_optional_text(data.get("campaign_id")),
            title=_coerce_optional_text(data.get("title")) or "",
            objective=_coerce_optional_text(data.get("objective")) or "",
            scope=_coerce_optional_text(data.get("scope")),
            status=_coerce_optional_text(data.get("status")),
            priority=_coerce_int(data.get("priority"), default=0),
            created_by=_coerce_optional_text(data.get("created_by")),
            assigned_worker_id=_coerce_optional_text(
                data.get("assigned_worker_id")
            ),
            source_thread_id=_coerce_optional_text(
                data.get("source_thread_id")
            ),
            source_message_id=_coerce_optional_text(
                data.get("source_message_id")
            ),
            dependency_ids=_coerce_deduped_text_list(
                data.get("dependency_ids")
            ),
            file_scope=_coerce_deduped_text_list(data.get("file_scope")),
            validation_command=_coerce_optional_text(
                data.get("validation_command")
            ),
            adapter_kind=_coerce_optional_text(data.get("adapter_kind")),
            max_validation_attempts=max(
                1, _coerce_int(data.get("max_validation_attempts"), default=1)
            ),
            require_worktree_lease=bool(
                data.get("require_worktree_lease", False)
            ),
            commit_after_validation=bool(
                data.get("commit_after_validation", False)
            ),
            require_human_review_before_merge=bool(
                data.get("require_human_review_before_merge", True)
            ),
            blocked_reason=_coerce_optional_text(data.get("blocked_reason")),
            extra_meta=_coerce_mapping(data.get("extra_meta")),
        )


@dataclass(frozen=True)
class WorkOrderUpdate:
    title: str | None = None
    objective: str | None = None
    scope: str | None = None
    priority: int | None = None
    assigned_worker_id: str | None = None
    dependency_ids: list[str] | None = None
    file_scope: list[str] | None = None
    validation_command: str | None = None
    adapter_kind: str | None = None
    max_validation_attempts: int | None = None
    require_worktree_lease: bool | None = None
    commit_after_validation: bool | None = None
    require_human_review_before_merge: bool | None = None
    blocked_reason: str | None = None
    extra_meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for field_name in (
            "title",
            "objective",
            "scope",
            "priority",
            "assigned_worker_id",
            "dependency_ids",
            "file_scope",
            "validation_command",
            "adapter_kind",
            "max_validation_attempts",
            "require_worktree_lease",
            "commit_after_validation",
            "require_human_review_before_merge",
            "blocked_reason",
            "extra_meta",
        ):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkOrderUpdate:
        data = dict(payload or {})
        dependency_ids = data.get("dependency_ids")
        file_scope = data.get("file_scope")
        extra_meta = data.get("extra_meta")
        return cls(
            title=_coerce_optional_text(data.get("title")),
            objective=_coerce_optional_text(data.get("objective")),
            scope=_coerce_optional_text(data.get("scope")),
            priority=(
                None
                if data.get("priority") is None
                else _coerce_int(data.get("priority"), default=0)
            ),
            assigned_worker_id=_coerce_optional_text(
                data.get("assigned_worker_id")
            ),
            dependency_ids=(
                None
                if dependency_ids is None
                else _coerce_deduped_text_list(dependency_ids)
            ),
            file_scope=(
                None
                if file_scope is None
                else _coerce_deduped_text_list(file_scope)
            ),
            validation_command=_coerce_optional_text(
                data.get("validation_command")
            ),
            adapter_kind=_coerce_optional_text(data.get("adapter_kind")),
            max_validation_attempts=(
                None
                if data.get("max_validation_attempts") is None
                else max(
                    1,
                    _coerce_int(data.get("max_validation_attempts"), default=1),
                )
            ),
            require_worktree_lease=(
                None
                if data.get("require_worktree_lease") is None
                else bool(data.get("require_worktree_lease"))
            ),
            commit_after_validation=(
                None
                if data.get("commit_after_validation") is None
                else bool(data.get("commit_after_validation"))
            ),
            require_human_review_before_merge=(
                None
                if data.get("require_human_review_before_merge") is None
                else bool(data.get("require_human_review_before_merge"))
            ),
            blocked_reason=(
                None
                if data.get("blocked_reason") is None
                else _coerce_optional_text(data.get("blocked_reason"))
            ),
            extra_meta=(
                None if extra_meta is None else _coerce_mapping(extra_meta)
            ),
        )


@dataclass(frozen=True)
class WorkOrderContract:
    work_order_id: str
    campaign_id: str | None
    title: str
    objective: str
    scope: str | None
    status: WorkOrderStatus
    priority: int
    created_by: str | None
    assigned_worker_id: str | None
    source_thread_id: str | None
    source_message_id: str | None
    dependency_ids: list[str]
    file_scope: list[str]
    validation_command: str | None
    adapter_kind: str | None
    max_validation_attempts: int
    require_worktree_lease: bool
    commit_after_validation: bool
    require_human_review_before_merge: bool
    latest_run_id: str | None
    latest_lease_id: str | None
    latest_receipt_id: str | None
    blocked_reason: str | None
    extra_meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "work_order_id": self.work_order_id,
            "campaign_id": self.campaign_id,
            "title": self.title,
            "objective": self.objective,
            "scope": self.scope,
            "status": self.status,
            "priority": self.priority,
            "created_by": self.created_by,
            "assigned_worker_id": self.assigned_worker_id,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "dependency_ids": list(self.dependency_ids),
            "file_scope": list(self.file_scope),
            "validation_command": self.validation_command,
            "adapter_kind": self.adapter_kind,
            "max_validation_attempts": self.max_validation_attempts,
            "require_worktree_lease": self.require_worktree_lease,
            "commit_after_validation": self.commit_after_validation,
            "require_human_review_before_merge": self.require_human_review_before_merge,
            "latest_run_id": self.latest_run_id,
            "latest_lease_id": self.latest_lease_id,
            "latest_receipt_id": self.latest_receipt_id,
            "blocked_reason": self.blocked_reason,
            "extra_meta": dict(self.extra_meta),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "archived_at": (
                self.archived_at.isoformat()
                if self.archived_at is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkOrderContract:
        data = dict(payload or {})
        return cls(
            work_order_id=str(data.get("work_order_id") or ""),
            campaign_id=_coerce_optional_text(data.get("campaign_id")),
            title=str(data.get("title") or ""),
            objective=str(data.get("objective") or ""),
            scope=_coerce_optional_text(data.get("scope")),
            status=str(data.get("status") or "ready"),
            priority=_coerce_int(data.get("priority"), default=0),
            created_by=_coerce_optional_text(data.get("created_by")),
            assigned_worker_id=_coerce_optional_text(
                data.get("assigned_worker_id")
            ),
            source_thread_id=_coerce_optional_text(
                data.get("source_thread_id")
            ),
            source_message_id=_coerce_optional_text(
                data.get("source_message_id")
            ),
            dependency_ids=_coerce_deduped_text_list(
                data.get("dependency_ids")
            ),
            file_scope=_coerce_deduped_text_list(data.get("file_scope")),
            validation_command=_coerce_optional_text(
                data.get("validation_command")
            ),
            adapter_kind=_coerce_optional_text(data.get("adapter_kind")),
            max_validation_attempts=max(
                1, _coerce_int(data.get("max_validation_attempts"), default=1)
            ),
            require_worktree_lease=bool(
                data.get("require_worktree_lease", False)
            ),
            commit_after_validation=bool(
                data.get("commit_after_validation", False)
            ),
            require_human_review_before_merge=bool(
                data.get("require_human_review_before_merge", True)
            ),
            latest_run_id=_coerce_optional_text(data.get("latest_run_id")),
            latest_lease_id=_coerce_optional_text(data.get("latest_lease_id")),
            latest_receipt_id=_coerce_optional_text(
                data.get("latest_receipt_id")
            ),
            blocked_reason=_coerce_optional_text(data.get("blocked_reason")),
            extra_meta=_coerce_mapping(data.get("extra_meta")),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            archived_at=_parse_optional_datetime(data.get("archived_at")),
        )


def is_terminal_work_order_status(status: str) -> bool:
    return str(status) in WORK_ORDER_TERMINAL_STATUSES


def is_active_work_order_status(status: str) -> bool:
    return str(status) in WORK_ORDER_ACTIVE_STATUSES


def validate_work_order_transition(
    from_status: str,
    to_status: str,
) -> WorkOrderValidationResult:
    current = str(from_status).strip()
    target = str(to_status).strip()

    if current not in WORK_ORDER_STATUSES:
        return WorkOrderValidationResult(
            ok=False,
            reason=f"invalid from status: {current}",
            reason_code="invalid_work_order_status",
        )

    if target not in WORK_ORDER_STATUSES:
        return WorkOrderValidationResult(
            ok=False,
            reason=f"invalid to status: {target}",
            reason_code="invalid_work_order_status",
        )

    if current == target:
        return WorkOrderValidationResult(ok=True)

    allowed = WORK_ORDER_ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        return WorkOrderValidationResult(
            ok=False,
            reason=f"forbidden transition: {current} -> {target}",
            reason_code="invalid_work_order_transition",
        )

    return WorkOrderValidationResult(ok=True)


def _parse_datetime(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    value = str(raw or "").strip()
    if not value:
        raise ValueError("datetime value is required")
    return datetime.fromisoformat(value)


def _parse_optional_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return datetime.fromisoformat(value)


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _coerce_int(raw: Any, *, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(default)


def _coerce_deduped_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    values: list[str] = []
    if isinstance(raw, (list, tuple, set)):
        iterable = raw
    else:
        iterable = [raw]
    for item in iterable:
        value = str(item or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}
