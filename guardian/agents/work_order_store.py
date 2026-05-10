"""Durable persistence helpers for coding work-order control-plane state.

This module persists and reads work-order lifecycle state only. It does not
queue workers, allocate leases, run Git commands, or trigger orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from guardian.agents.work_orders import (
    WORK_ORDER_STATUSES,
    WorkOrderContract,
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderValidationResult,
    validate_work_order_transition,
)
from guardian.db.models import CodingWorkOrder

MAX_LIST_ITEMS = 256
MAX_ITEM_CHARS = 1024
MAX_TEXT_CHARS = 4096
MAX_META_KEYS = 128


class WorkOrderStoreError(RuntimeError):
    """Base error for work-order store operations."""


class WorkOrderNotFound(WorkOrderStoreError):
    """Raised when a requested work_order_id does not exist."""


class WorkOrderValidationError(WorkOrderStoreError):
    """Raised when payload validation fails."""

    def __init__(self, result: WorkOrderValidationResult) -> None:
        super().__init__(result.reason or "invalid work order payload")
        self.reason = result.reason
        self.reason_code = result.reason_code


class WorkOrderTransitionError(WorkOrderStoreError):
    """Raised when a status transition is not allowed."""

    def __init__(
        self,
        *,
        from_status: str,
        to_status: str,
        reason: str | None = None,
        reason_code: str | None = None,
    ) -> None:
        message = (
            reason or f"forbidden transition: {from_status} -> {to_status}"
        )
        super().__init__(message)
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        self.reason_code = reason_code


@dataclass
class WorkOrderStore:
    """Postgres-backed store for durable coding work orders."""

    db: Any

    def create_work_order(self, payload: WorkOrderCreate) -> WorkOrderContract:
        validation = self._validate_create_payload(payload)
        if not validation.ok:
            raise WorkOrderValidationError(validation)

        now = _utc_now()
        status = self._normalize_initial_status(payload.status)
        row = CodingWorkOrder(
            work_order_id=_new_work_order_id(),
            campaign_id=_coerce_optional_text(payload.campaign_id),
            title=payload.title.strip(),
            objective=payload.objective.strip(),
            scope=_coerce_optional_text(payload.scope),
            status=status,
            priority=int(payload.priority),
            created_by=_coerce_optional_text(payload.created_by),
            assigned_worker_id=_coerce_optional_text(
                payload.assigned_worker_id
            ),
            source_thread_id=_coerce_optional_text(payload.source_thread_id),
            source_message_id=_coerce_optional_text(payload.source_message_id),
            dependency_ids=_bounded_text_list(payload.dependency_ids),
            file_scope=_bounded_text_list(payload.file_scope),
            validation_command=_coerce_optional_text(
                payload.validation_command
            ),
            adapter_kind=_coerce_optional_text(payload.adapter_kind),
            max_validation_attempts=max(
                1, int(payload.max_validation_attempts)
            ),
            require_worktree_lease=bool(payload.require_worktree_lease),
            commit_after_validation=bool(payload.commit_after_validation),
            require_human_review_before_merge=bool(
                payload.require_human_review_before_merge
            ),
            blocked_reason=_coerce_optional_text(payload.blocked_reason),
            extra_meta=_bounded_meta(payload.extra_meta),
            created_at=now,
            updated_at=now,
        )

        with self.db.get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def get_work_order(self, work_order_id: str) -> WorkOrderContract | None:
        with self.db.get_session() as session:
            row = (
                session.query(CodingWorkOrder)
                .filter_by(work_order_id=work_order_id)
                .first()
            )
            if row is None:
                return None
            return self._row_to_contract(row)

    def list_work_orders(
        self,
        status: str | None = None,
        campaign_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkOrderContract]:
        normalized_status = _coerce_optional_text(status)
        if (
            normalized_status is not None
            and normalized_status not in WORK_ORDER_STATUSES
        ):
            raise WorkOrderValidationError(
                WorkOrderValidationResult(
                    ok=False,
                    reason=f"invalid work-order status filter: {normalized_status}",
                    reason_code="invalid_work_order_status",
                )
            )

        bounded_limit = max(1, min(int(limit or 50), 200))
        bounded_offset = max(0, int(offset or 0))

        with self.db.get_session() as session:
            query = session.query(CodingWorkOrder)
            if normalized_status is not None:
                query = query.filter(
                    CodingWorkOrder.status == normalized_status
                )
            normalized_campaign = _coerce_optional_text(campaign_id)
            if normalized_campaign is not None:
                query = query.filter(
                    CodingWorkOrder.campaign_id == normalized_campaign
                )
            rows = (
                query.order_by(
                    CodingWorkOrder.priority.desc(),
                    CodingWorkOrder.created_at.desc(),
                )
                .offset(bounded_offset)
                .limit(bounded_limit)
                .all()
            )
            return [self._row_to_contract(row) for row in rows]

    def update_work_order(
        self,
        work_order_id: str,
        payload: WorkOrderUpdate,
    ) -> WorkOrderContract:
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, work_order_id)

            if payload.title is not None:
                row.title = payload.title
            if payload.objective is not None:
                row.objective = payload.objective
            if payload.scope is not None:
                row.scope = payload.scope
            if payload.priority is not None:
                row.priority = int(payload.priority)
            if payload.assigned_worker_id is not None:
                row.assigned_worker_id = payload.assigned_worker_id
            if payload.dependency_ids is not None:
                row.dependency_ids = _bounded_text_list(payload.dependency_ids)
            if payload.file_scope is not None:
                row.file_scope = _bounded_text_list(payload.file_scope)
            if payload.validation_command is not None:
                row.validation_command = payload.validation_command
            if payload.adapter_kind is not None:
                row.adapter_kind = payload.adapter_kind
            if payload.max_validation_attempts is not None:
                row.max_validation_attempts = max(
                    1, int(payload.max_validation_attempts)
                )
            if payload.require_worktree_lease is not None:
                row.require_worktree_lease = bool(
                    payload.require_worktree_lease
                )
            if payload.commit_after_validation is not None:
                row.commit_after_validation = bool(
                    payload.commit_after_validation
                )
            if payload.require_human_review_before_merge is not None:
                row.require_human_review_before_merge = bool(
                    payload.require_human_review_before_merge
                )
            if payload.blocked_reason is not None:
                row.blocked_reason = payload.blocked_reason
            if payload.extra_meta is not None:
                row.extra_meta = _bounded_meta(payload.extra_meta)

            row.updated_at = _utc_now()
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def transition_work_order(
        self,
        work_order_id: str,
        to_status: str,
        reason: str | None = None,
    ) -> WorkOrderContract:
        normalized_target = str(to_status or "").strip()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, work_order_id)
            current = str(row.status or "").strip()
            result = validate_work_order_transition(current, normalized_target)
            if not result.ok:
                if result.reason_code == "invalid_work_order_status":
                    raise WorkOrderValidationError(result)
                raise WorkOrderTransitionError(
                    from_status=current,
                    to_status=normalized_target,
                    reason=result.reason,
                    reason_code=result.reason_code,
                )

            now = _utc_now()
            row.status = normalized_target
            row.updated_at = now
            bounded_reason = _bounded_text(reason)
            if normalized_target == "archived":
                row.archived_at = now
            if normalized_target in {"blocked", "escalated", "cancelled"}:
                row.blocked_reason = bounded_reason
            elif bounded_reason and normalized_target == "failed":
                row.blocked_reason = bounded_reason

            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def cancel_work_order(
        self,
        work_order_id: str,
        reason: str | None = None,
    ) -> WorkOrderContract:
        return self.transition_work_order(
            work_order_id,
            "cancelled",
            reason=reason,
        )

    def archive_work_order(self, work_order_id: str) -> WorkOrderContract:
        return self.transition_work_order(work_order_id, "archived")

    def mark_latest_run(
        self,
        work_order_id: str,
        run_id: str | None,
        lease_id: str | None = None,
        receipt_id: str | None = None,
    ) -> WorkOrderContract:
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, work_order_id)
            row.latest_run_id = _coerce_optional_text(run_id)
            row.latest_lease_id = _coerce_optional_text(lease_id)
            row.latest_receipt_id = _coerce_optional_text(receipt_id)
            row.updated_at = _utc_now()
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def _validate_create_payload(
        self, payload: WorkOrderCreate
    ) -> WorkOrderValidationResult:
        title = str(payload.title or "").strip()
        objective = str(payload.objective or "").strip()
        if not title:
            return WorkOrderValidationResult(
                ok=False,
                reason="missing required field: title",
                reason_code="missing_required_field",
            )
        if not objective:
            return WorkOrderValidationResult(
                ok=False,
                reason="missing required field: objective",
                reason_code="missing_required_field",
            )

        if payload.status is not None:
            status = str(payload.status or "").strip()
            if status not in WORK_ORDER_STATUSES:
                return WorkOrderValidationResult(
                    ok=False,
                    reason=f"invalid work-order status: {status}",
                    reason_code="invalid_work_order_status",
                )
            if status not in {"draft", "ready"}:
                return WorkOrderValidationResult(
                    ok=False,
                    reason=(
                        "work order creation status must be draft or ready"
                    ),
                    reason_code="invalid_work_order_status",
                )

        try:
            int(payload.priority)
        except (TypeError, ValueError):
            return WorkOrderValidationResult(
                ok=False,
                reason="priority must be an integer",
                reason_code="invalid_priority",
            )

        try:
            attempts = int(payload.max_validation_attempts)
        except (TypeError, ValueError):
            return WorkOrderValidationResult(
                ok=False,
                reason="max_validation_attempts must be an integer",
                reason_code="invalid_max_validation_attempts",
            )
        if attempts < 1:
            return WorkOrderValidationResult(
                ok=False,
                reason="max_validation_attempts must be >= 1",
                reason_code="invalid_max_validation_attempts",
            )

        return WorkOrderValidationResult(ok=True)

    def _normalize_initial_status(self, status: str | None) -> str:
        normalized = str(status or "").strip()
        if normalized == "draft":
            return "draft"
        if normalized == "ready":
            return "ready"
        return "ready"

    def _get_row_or_raise(
        self, session: Any, work_order_id: str
    ) -> CodingWorkOrder:
        row = (
            session.query(CodingWorkOrder)
            .filter_by(work_order_id=work_order_id)
            .first()
        )
        if row is None:
            raise WorkOrderNotFound(f"unknown work_order_id: {work_order_id}")
        return row

    @staticmethod
    def _row_to_contract(row: CodingWorkOrder) -> WorkOrderContract:
        return WorkOrderContract(
            work_order_id=row.work_order_id,
            campaign_id=row.campaign_id,
            title=row.title,
            objective=row.objective,
            scope=row.scope,
            status=row.status,
            priority=int(row.priority),
            created_by=row.created_by,
            assigned_worker_id=row.assigned_worker_id,
            source_thread_id=row.source_thread_id,
            source_message_id=row.source_message_id,
            dependency_ids=_bounded_text_list(row.dependency_ids),
            file_scope=_bounded_text_list(row.file_scope),
            validation_command=row.validation_command,
            adapter_kind=row.adapter_kind,
            max_validation_attempts=max(
                1, int(row.max_validation_attempts or 1)
            ),
            require_worktree_lease=bool(row.require_worktree_lease),
            commit_after_validation=bool(row.commit_after_validation),
            require_human_review_before_merge=bool(
                row.require_human_review_before_merge
            ),
            latest_run_id=row.latest_run_id,
            latest_lease_id=row.latest_lease_id,
            latest_receipt_id=row.latest_receipt_id,
            blocked_reason=row.blocked_reason,
            extra_meta=_bounded_meta(row.extra_meta),
            created_at=_ensure_aware_datetime(row.created_at),
            updated_at=_ensure_aware_datetime(row.updated_at),
            archived_at=_ensure_aware_datetime(row.archived_at),
        )


def _new_work_order_id() -> str:
    return f"wo_{uuid4().hex[:16]}"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _bounded_text(raw: Any) -> str | None:
    value = _coerce_optional_text(raw)
    if value is None:
        return None
    return value[:MAX_TEXT_CHARS]


def _bounded_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        iterable = raw
    else:
        iterable = [raw]

    values: list[str] = []
    for item in iterable:
        value = str(item or "").strip()
        if not value:
            continue
        bounded = value[:MAX_ITEM_CHARS]
        if bounded not in values:
            values.append(bounded)
        if len(values) >= MAX_LIST_ITEMS:
            break
    return values


def _bounded_meta(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    bounded: dict[str, Any] = {}
    for index, (key, value) in enumerate(raw.items()):
        if index >= MAX_META_KEYS:
            break
        normalized_key = str(key).strip()[:128]
        if not normalized_key:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            bounded[normalized_key] = value
        elif isinstance(value, (list, tuple, set)):
            bounded[normalized_key] = _bounded_text_list(value)
        elif isinstance(value, dict):
            bounded[normalized_key] = {
                str(sub_key).strip()[:128]: str(sub_value)[:MAX_TEXT_CHARS]
                for sub_key, sub_value in list(value.items())[:32]
            }
        else:
            bounded[normalized_key] = str(value)[:MAX_TEXT_CHARS]
    return bounded
