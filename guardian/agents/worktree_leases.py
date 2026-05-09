"""Canonical contract types and validation helpers for worktree leases.

This module defines a planning-phase contract seam only. It does not perform
Git operations, filesystem allocation, persistence, worker execution, or route
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Sequence

WorktreeLeaseStatus = Literal[
    "active",
    "expired",
    "released",
    "abandoned",
    "cleanup_pending",
    "cleaned",
    "blocked",
    "failed",
]

WorktreeLeaseCleanupPolicy = Literal[
    "cleanup_on_merge",
    "preserve_on_fail",
    "manual_cleanup_required",
]

WORKTREE_LEASE_STATUSES: frozenset[str] = frozenset(
    {
        "active",
        "expired",
        "released",
        "abandoned",
        "cleanup_pending",
        "cleaned",
        "blocked",
        "failed",
    }
)

WORKTREE_LEASE_CLEANUP_POLICIES: frozenset[str] = frozenset(
    {
        "cleanup_on_merge",
        "preserve_on_fail",
        "manual_cleanup_required",
    }
)

# Terminal means this lease lifecycle should not re-enter mutable execution.
WORKTREE_LEASE_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "expired",
        "released",
        "abandoned",
        "cleaned",
        "failed",
    }
)

# Active means this lease currently owns mutable branch/worktree scope.
WORKTREE_LEASE_ACTIVE_STATUSES: frozenset[str] = frozenset({"active"})


@dataclass(frozen=True)
class WorktreeLeaseContract:
    lease_id: str
    work_order_id: str
    run_id: str
    worker_id: str
    base_ref: str
    branch_name: str
    worktree_path: str
    status: WorktreeLeaseStatus
    created_at: datetime
    expires_at: datetime
    preserve_on_failure: bool
    cleanup_policy: WorktreeLeaseCleanupPolicy
    last_heartbeat_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "work_order_id": self.work_order_id,
            "run_id": self.run_id,
            "worker_id": self.worker_id,
            "base_ref": self.base_ref,
            "branch_name": self.branch_name,
            "worktree_path": self.worktree_path,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "preserve_on_failure": self.preserve_on_failure,
            "cleanup_policy": self.cleanup_policy,
            "last_heartbeat_at": (
                self.last_heartbeat_at.isoformat()
                if self.last_heartbeat_at is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorktreeLeaseContract:
        return cls(
            lease_id=str(payload.get("lease_id", "")),
            work_order_id=str(payload.get("work_order_id", "")),
            run_id=str(payload.get("run_id", "")),
            worker_id=str(payload.get("worker_id", "")),
            base_ref=str(payload.get("base_ref", "")),
            branch_name=str(payload.get("branch_name", "")),
            worktree_path=str(payload.get("worktree_path", "")),
            status=str(payload.get("status", "")),
            created_at=_parse_datetime(payload.get("created_at")),
            expires_at=_parse_datetime(payload.get("expires_at")),
            preserve_on_failure=bool(payload.get("preserve_on_failure", False)),
            cleanup_policy=str(payload.get("cleanup_policy", "")),
            last_heartbeat_at=(
                _parse_datetime(payload.get("last_heartbeat_at"))
                if payload.get("last_heartbeat_at") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class WorktreeLeaseRequest:
    work_order_id: str
    run_id: str
    worker_id: str
    base_ref: str
    branch_name: str | None
    worktree_path: str | None
    preserve_on_failure: bool
    cleanup_policy: WorktreeLeaseCleanupPolicy

    def to_dict(self) -> dict[str, object]:
        return {
            "work_order_id": self.work_order_id,
            "run_id": self.run_id,
            "worker_id": self.worker_id,
            "base_ref": self.base_ref,
            "branch_name": self.branch_name,
            "worktree_path": self.worktree_path,
            "preserve_on_failure": self.preserve_on_failure,
            "cleanup_policy": self.cleanup_policy,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorktreeLeaseRequest:
        branch_name = payload.get("branch_name")
        worktree_path = payload.get("worktree_path")
        return cls(
            work_order_id=str(payload.get("work_order_id", "")),
            run_id=str(payload.get("run_id", "")),
            worker_id=str(payload.get("worker_id", "")),
            base_ref=str(payload.get("base_ref", "")),
            branch_name=(None if branch_name is None else str(branch_name)),
            worktree_path=(
                None if worktree_path is None else str(worktree_path)
            ),
            preserve_on_failure=bool(payload.get("preserve_on_failure", False)),
            cleanup_policy=str(payload.get("cleanup_policy", "")),
        )


@dataclass(frozen=True)
class WorktreeLeaseValidationResult:
    ok: bool
    reason: str | None = None
    reason_code: str | None = None


def is_terminal_lease_status(status: str) -> bool:
    return str(status) in WORKTREE_LEASE_TERMINAL_STATUSES


def is_active_lease_status(status: str) -> bool:
    return str(status) in WORKTREE_LEASE_ACTIVE_STATUSES


def validate_lease_contract(
    lease: WorktreeLeaseContract,
) -> WorktreeLeaseValidationResult:
    required_fields = (
        ("lease_id", lease.lease_id),
        ("work_order_id", lease.work_order_id),
        ("run_id", lease.run_id),
        ("worker_id", lease.worker_id),
        ("base_ref", lease.base_ref),
        ("branch_name", lease.branch_name),
        ("worktree_path", lease.worktree_path),
    )
    for field_name, value in required_fields:
        if not _is_non_empty_string(value):
            return WorktreeLeaseValidationResult(
                ok=False,
                reason=f"missing required string field: {field_name}",
                reason_code="missing_required_string_field",
            )

    if lease.status not in WORKTREE_LEASE_STATUSES:
        return WorktreeLeaseValidationResult(
            ok=False,
            reason=f"invalid lease status: {lease.status}",
            reason_code="invalid_lease_status",
        )

    if lease.cleanup_policy not in WORKTREE_LEASE_CLEANUP_POLICIES:
        return WorktreeLeaseValidationResult(
            ok=False,
            reason=f"invalid cleanup policy: {lease.cleanup_policy}",
            reason_code="invalid_cleanup_policy",
        )

    if not _is_timezone_aware(lease.created_at):
        return WorktreeLeaseValidationResult(
            ok=False,
            reason="created_at must be timezone-aware",
            reason_code="created_at_not_timezone_aware",
        )

    if not _is_timezone_aware(lease.expires_at):
        return WorktreeLeaseValidationResult(
            ok=False,
            reason="expires_at must be timezone-aware",
            reason_code="expires_at_not_timezone_aware",
        )

    if lease.expires_at < lease.created_at:
        return WorktreeLeaseValidationResult(
            ok=False,
            reason="expires_at must be >= created_at",
            reason_code="expires_before_created",
        )

    if lease.last_heartbeat_at is not None:
        if not _is_timezone_aware(lease.last_heartbeat_at):
            return WorktreeLeaseValidationResult(
                ok=False,
                reason="last_heartbeat_at must be timezone-aware",
                reason_code="last_heartbeat_not_timezone_aware",
            )
        if lease.last_heartbeat_at < lease.created_at:
            return WorktreeLeaseValidationResult(
                ok=False,
                reason="last_heartbeat_at must be >= created_at",
                reason_code="heartbeat_before_created",
            )

    return WorktreeLeaseValidationResult(ok=True, reason=None, reason_code=None)


def validate_no_shared_mutable_worktree(
    leases: Sequence[WorktreeLeaseContract],
) -> WorktreeLeaseValidationResult:
    active_by_path: dict[str, str] = {}
    active_by_branch: dict[str, str] = {}

    for lease in leases:
        validity = validate_lease_contract(lease)
        if not validity.ok:
            return validity

        if not is_active_lease_status(lease.status):
            continue

        existing_lease_for_path = active_by_path.get(lease.worktree_path)
        if (
            existing_lease_for_path is not None
            and existing_lease_for_path != lease.lease_id
        ):
            return WorktreeLeaseValidationResult(
                ok=False,
                reason=(
                    "active leases share worktree_path: "
                    f"{lease.worktree_path}"
                ),
                reason_code="shared_active_worktree_path",
            )
        active_by_path[lease.worktree_path] = lease.lease_id

        existing_lease_for_branch = active_by_branch.get(lease.branch_name)
        if (
            existing_lease_for_branch is not None
            and existing_lease_for_branch != lease.lease_id
        ):
            return WorktreeLeaseValidationResult(
                ok=False,
                reason=(
                    "active leases share branch_name: " f"{lease.branch_name}"
                ),
                reason_code="shared_active_branch_name",
            )
        active_by_branch[lease.branch_name] = lease.lease_id

    return WorktreeLeaseValidationResult(ok=True, reason=None, reason_code=None)


def _parse_datetime(raw_value: Any) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value
    if raw_value is None:
        raise ValueError("missing datetime value")
    value = str(raw_value).strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


__all__ = [
    "WorktreeLeaseCleanupPolicy",
    "WorktreeLeaseContract",
    "WorktreeLeaseRequest",
    "WorktreeLeaseStatus",
    "WorktreeLeaseValidationResult",
    "WORKTREE_LEASE_ACTIVE_STATUSES",
    "WORKTREE_LEASE_CLEANUP_POLICIES",
    "WORKTREE_LEASE_STATUSES",
    "WORKTREE_LEASE_TERMINAL_STATUSES",
    "is_active_lease_status",
    "is_terminal_lease_status",
    "validate_lease_contract",
    "validate_no_shared_mutable_worktree",
]
