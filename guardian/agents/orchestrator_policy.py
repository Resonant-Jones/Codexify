"""Deterministic recommendation-only orchestrator policy for coding work orders.

This module produces ranked next-task recommendations from durable control-plane
state. It never dispatches work, mutates state, allocates leases, or performs
Git operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Sequence

from guardian.agents.work_orders import WorkOrderContract
from guardian.agents.worktree_leases import (
    WorktreeLeaseContract,
    is_active_lease_status,
)
from guardian.protocol_tokens import (
    ORCHESTRATOR_DECISION_TOKENS,
    ORCHESTRATOR_REASON_CODES,
    OrchestratorDecisionToken,
    OrchestratorReasonCode,
)

OrchestratorDecisionValue = Literal[
    "recommend",
    "skip",
    "blocked",
    "recommendation_only",
]


@dataclass(frozen=True)
class OrchestratorDecision:
    decision: OrchestratorDecisionValue
    reason_codes: list[str] = field(default_factory=list)
    message: str | None = None


@dataclass(frozen=True)
class OrchestratorRecommendation:
    work_order_id: str
    title: str
    status: str
    priority: int
    rank: int
    decision: str
    reason_codes: list[str]
    dependency_ids: list[str]
    file_scope: list[str]
    requires_human_review: bool
    latest_run_id: str | None
    latest_lease_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "work_order_id": self.work_order_id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "rank": self.rank,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "dependency_ids": list(self.dependency_ids),
            "file_scope": list(self.file_scope),
            "requires_human_review": self.requires_human_review,
            "latest_run_id": self.latest_run_id,
            "latest_lease_id": self.latest_lease_id,
        }


@dataclass(frozen=True)
class OrchestratorSkipReason:
    work_order_id: str
    reason_code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "work_order_id": self.work_order_id,
            "reason_code": self.reason_code,
            "message": self.message,
        }


@dataclass(frozen=True)
class OrchestratorPolicyInput:
    work_orders: list[WorkOrderContract]
    active_leases: list[WorktreeLeaseContract] = field(default_factory=list)
    limit: int = 5


@dataclass(frozen=True)
class OrchestratorPolicyResult:
    recommendations: list[OrchestratorRecommendation]
    skipped: list[OrchestratorSkipReason]
    decision_reasons: list[str]
    generated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "recommendations": [
                item.to_dict() for item in self.recommendations
            ],
            "skipped": [item.to_dict() for item in self.skipped],
            "decision_reasons": list(self.decision_reasons),
            "generated_at": self.generated_at.isoformat(),
        }


def select_next_work_orders(
    work_orders: Sequence[WorkOrderContract],
    active_leases: Sequence[WorktreeLeaseContract] | None = None,
    limit: int = 5,
) -> OrchestratorPolicyResult:
    """Return deterministic recommendation-only next-task selections.

    Selection is read-only and fail-closed on dependency ambiguity/conflicts.
    """

    normalized_limit = max(1, int(limit or 1))
    lease_rows = list(active_leases or [])
    all_work_orders = list(work_orders)

    by_id: dict[str, WorkOrderContract] = {
        row.work_order_id: row for row in all_work_orders
    }
    active_lease_ids: set[str] = {
        lease.lease_id
        for lease in lease_rows
        if is_active_lease_status(lease.status)
    }
    active_lease_work_order_ids: set[str] = {
        lease.work_order_id
        for lease in lease_rows
        if is_active_lease_status(lease.status)
    }

    active_execution_statuses = {"leased", "running", "validating", "retrying"}
    active_file_scopes: dict[str, set[str]] = {
        row.work_order_id: {value for value in row.file_scope if value}
        for row in all_work_orders
        if row.status in active_execution_statuses
    }

    skipped: list[OrchestratorSkipReason] = []
    eligible: list[WorkOrderContract] = []

    for work_order in sorted(
        all_work_orders, key=lambda item: item.work_order_id
    ):
        if work_order.status != "ready":
            skipped.append(
                OrchestratorSkipReason(
                    work_order_id=work_order.work_order_id,
                    reason_code=OrchestratorReasonCode.STATUS_NOT_READY.value,
                    message=(
                        "work order is not in ready status "
                        f"(current={work_order.status})"
                    ),
                )
            )
            continue

        dependency_failure = _dependency_failure(work_order, by_id)
        if dependency_failure is not None:
            skipped.append(dependency_failure)
            continue

        lease_failure = _lease_conflict(
            work_order,
            active_lease_ids=active_lease_ids,
            active_lease_work_order_ids=active_lease_work_order_ids,
        )
        if lease_failure is not None:
            skipped.append(lease_failure)
            continue

        scope_failure = _file_scope_conflict(
            work_order,
            active_file_scopes=active_file_scopes,
        )
        if scope_failure is not None:
            skipped.append(scope_failure)
            continue

        eligible.append(work_order)

    ranked_eligible = sorted(
        eligible,
        key=lambda item: (
            -int(item.priority),
            _datetime_sort_key(item.created_at),
            item.work_order_id,
        ),
    )

    selected = ranked_eligible[:normalized_limit]
    overflow = ranked_eligible[normalized_limit:]

    recommendations: list[OrchestratorRecommendation] = []
    for index, work_order in enumerate(selected, start=1):
        decision, reason_codes = _recommendation_decision(work_order)
        recommendations.append(
            OrchestratorRecommendation(
                work_order_id=work_order.work_order_id,
                title=work_order.title,
                status=work_order.status,
                priority=int(work_order.priority),
                rank=index,
                decision=decision,
                reason_codes=reason_codes,
                dependency_ids=list(work_order.dependency_ids),
                file_scope=list(work_order.file_scope),
                requires_human_review=bool(
                    work_order.require_human_review_before_merge
                ),
                latest_run_id=work_order.latest_run_id,
                latest_lease_id=work_order.latest_lease_id,
            )
        )

    for work_order in overflow:
        skipped.append(
            OrchestratorSkipReason(
                work_order_id=work_order.work_order_id,
                reason_code=OrchestratorReasonCode.READY_FOR_DISPATCH.value,
                message=(
                    "work order is ready but not selected due to ranking/limit"
                ),
            )
        )

    decision_reasons = _build_decision_reasons(recommendations, skipped)

    return OrchestratorPolicyResult(
        recommendations=recommendations,
        skipped=sorted(
            skipped,
            key=lambda item: (
                item.work_order_id,
                item.reason_code,
                item.message,
            ),
        ),
        decision_reasons=decision_reasons,
        generated_at=datetime.now(UTC),
    )


def _dependency_failure(
    work_order: WorkOrderContract,
    by_id: dict[str, WorkOrderContract],
) -> OrchestratorSkipReason | None:
    for dependency_id in work_order.dependency_ids:
        dependency = by_id.get(dependency_id)
        if dependency is None:
            return OrchestratorSkipReason(
                work_order_id=work_order.work_order_id,
                reason_code=OrchestratorReasonCode.AMBIGUOUS_STATE.value,
                message=f"dependency is missing from input set: {dependency_id}",
            )

        if dependency.status not in {"merged", "archived"}:
            return OrchestratorSkipReason(
                work_order_id=work_order.work_order_id,
                reason_code=OrchestratorReasonCode.DEPENDENCY_NOT_SATISFIED.value,
                message=(
                    "dependency is not in a satisfied terminal status "
                    f"(dependency_id={dependency_id}, status={dependency.status})"
                ),
            )

    return None


def _lease_conflict(
    work_order: WorkOrderContract,
    *,
    active_lease_ids: set[str],
    active_lease_work_order_ids: set[str],
) -> OrchestratorSkipReason | None:
    if work_order.work_order_id in active_lease_work_order_ids:
        return OrchestratorSkipReason(
            work_order_id=work_order.work_order_id,
            reason_code=OrchestratorReasonCode.ACTIVE_LEASE_CONFLICT.value,
            message="work order already has an active lease",
        )

    latest_lease_id = (work_order.latest_lease_id or "").strip()
    if latest_lease_id and latest_lease_id in active_lease_ids:
        return OrchestratorSkipReason(
            work_order_id=work_order.work_order_id,
            reason_code=OrchestratorReasonCode.ACTIVE_LEASE_CONFLICT.value,
            message=f"latest lease is currently active: {latest_lease_id}",
        )

    return None


def _file_scope_conflict(
    work_order: WorkOrderContract,
    *,
    active_file_scopes: dict[str, set[str]],
) -> OrchestratorSkipReason | None:
    candidate_scope = {value for value in work_order.file_scope if value}
    if not candidate_scope:
        return None

    for active_work_order_id, active_scope in active_file_scopes.items():
        if active_work_order_id == work_order.work_order_id:
            continue
        overlap = sorted(candidate_scope.intersection(active_scope))
        if overlap:
            return OrchestratorSkipReason(
                work_order_id=work_order.work_order_id,
                reason_code=OrchestratorReasonCode.FILE_SCOPE_CONFLICT.value,
                message=(
                    "file scope overlaps with active work-order scope "
                    f"(active_work_order_id={active_work_order_id}, overlap={overlap})"
                ),
            )

    return None


def _recommendation_decision(
    work_order: WorkOrderContract,
) -> tuple[str, list[str]]:
    reason_codes = [OrchestratorReasonCode.READY_FOR_DISPATCH.value]
    if work_order.require_human_review_before_merge:
        reason_codes.append(OrchestratorReasonCode.HUMAN_REVIEW_REQUIRED.value)
        return OrchestratorDecisionToken.RECOMMENDATION_ONLY.value, reason_codes
    return OrchestratorDecisionToken.RECOMMEND.value, reason_codes


def _build_decision_reasons(
    recommendations: Sequence[OrchestratorRecommendation],
    skipped: Sequence[OrchestratorSkipReason],
) -> list[str]:
    reasons: list[str] = []
    reasons.append(
        f"evaluated work orders: {len(recommendations) + len(skipped)}"
    )
    reasons.append(f"recommended count: {len(recommendations)}")
    reasons.append(f"skipped count: {len(skipped)}")

    skip_counts: dict[str, int] = {}
    for item in skipped:
        skip_counts[item.reason_code] = skip_counts.get(item.reason_code, 0) + 1

    for reason_code in sorted(skip_counts):
        reasons.append(f"skip {reason_code}: {skip_counts[reason_code]}")

    return reasons


def _datetime_sort_key(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validate_tokens() -> None:
    required_decisions = {
        OrchestratorDecisionToken.RECOMMEND.value,
        OrchestratorDecisionToken.SKIP.value,
        OrchestratorDecisionToken.BLOCKED.value,
        OrchestratorDecisionToken.RECOMMENDATION_ONLY.value,
    }
    if not required_decisions.issubset(ORCHESTRATOR_DECISION_TOKENS):
        raise RuntimeError(
            "orchestrator decision tokens are not fully registered"
        )

    required_reason_codes = {
        OrchestratorReasonCode.DEPENDENCY_NOT_SATISFIED.value,
        OrchestratorReasonCode.ACTIVE_LEASE_CONFLICT.value,
        OrchestratorReasonCode.FILE_SCOPE_CONFLICT.value,
        OrchestratorReasonCode.STATUS_NOT_READY.value,
        OrchestratorReasonCode.HUMAN_REVIEW_REQUIRED.value,
        OrchestratorReasonCode.AMBIGUOUS_STATE.value,
        OrchestratorReasonCode.READY_FOR_DISPATCH.value,
    }
    if not required_reason_codes.issubset(ORCHESTRATOR_REASON_CODES):
        raise RuntimeError(
            "orchestrator reason-code tokens are not fully registered"
        )


_validate_tokens()

__all__ = [
    "OrchestratorDecision",
    "OrchestratorRecommendation",
    "OrchestratorSkipReason",
    "OrchestratorPolicyInput",
    "OrchestratorPolicyResult",
    "select_next_work_orders",
]
