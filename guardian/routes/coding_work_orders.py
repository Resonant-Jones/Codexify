"""Durable coding work-order task-board routes (Phase 5 foundation).

These routes expose durable work-order control-plane state only. They do not
queue/dispatch workers, allocate worktrees, run Git operations, or make
orchestrator decisions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from guardian.agents.work_order_store import (
    WorkOrderNotFound,
    WorkOrderStore,
    WorkOrderTransitionError,
    WorkOrderValidationError,
)
from guardian.agents.work_orders import WORK_ORDER_STATUSES, WorkOrderCreate
from guardian.core.dependencies import require_api_key
from guardian.protocol_tokens import ErrorCode

router = APIRouter(
    prefix="/api/coding/work-orders",
    tags=["Coding Work Orders"],
    dependencies=[Depends(require_api_key)],
)

_store = WorkOrderStore(db=None)


def configure_db(db: Any | None) -> None:
    global _store
    _store = WorkOrderStore(db=db)


def _normalize_validation_error_code(reason_code: str | None) -> str:
    mapping = {
        "invalid_work_order_status": ErrorCode.WORK_ORDER_INVALID_STATUS.value,
        "invalid_work_order_transition": ErrorCode.WORK_ORDER_INVALID_TRANSITION.value,
    }
    if reason_code is None:
        return ErrorCode.WORK_ORDER_INVALID.value
    return mapping.get(reason_code, ErrorCode.WORK_ORDER_INVALID.value)


class WorkOrderCreateRequest(BaseModel):
    campaign_id: str | None = None
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    scope: str | None = None
    status: str | None = None
    priority: int = 0
    created_by: str | None = None
    assigned_worker_id: str | None = None
    source_thread_id: str | None = None
    source_message_id: str | None = None
    dependency_ids: list[str] = Field(default_factory=list)
    file_scope: list[str] = Field(default_factory=list)
    validation_command: str | None = None
    adapter_kind: str | None = None
    max_validation_attempts: int = Field(default=1, ge=1)
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    require_human_review_before_merge: bool = True
    blocked_reason: str | None = None
    extra_meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class WorkOrderCancelRequest(BaseModel):
    reason: str | None = None

    model_config = ConfigDict(extra="forbid")


def _ensure_store_configured() -> WorkOrderStore:
    if _store.db is None:
        raise HTTPException(
            status_code=503, detail="work_order_store_unavailable"
        )
    return _store


@router.post("")
async def create_work_order(
    body: WorkOrderCreateRequest,
) -> dict[str, Any]:
    store = _ensure_store_configured()
    try:
        created = store.create_work_order(
            WorkOrderCreate.from_dict(body.model_dump())
        )
    except WorkOrderValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=_normalize_validation_error_code(exc.reason_code),
        ) from exc

    return {
        "ok": True,
        "work_order": created.to_dict(),
    }


@router.get("")
async def list_work_orders(
    status: str | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    store = _ensure_store_configured()
    normalized_status = str(status or "").strip() or None
    if (
        normalized_status is not None
        and normalized_status not in WORK_ORDER_STATUSES
    ):
        raise HTTPException(
            status_code=400,
            detail=ErrorCode.WORK_ORDER_INVALID_STATUS.value,
        )

    try:
        items = store.list_work_orders(
            status=normalized_status,
            campaign_id=campaign_id,
            limit=limit,
            offset=offset,
        )
    except WorkOrderValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=_normalize_validation_error_code(exc.reason_code),
        ) from exc

    return {
        "ok": True,
        "items": [item.to_dict() for item in items],
        "count": len(items),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{work_order_id}")
async def get_work_order(work_order_id: str) -> dict[str, Any]:
    store = _ensure_store_configured()
    work_order = store.get_work_order(work_order_id)
    if work_order is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        )

    return {
        "ok": True,
        "work_order": work_order.to_dict(),
    }


@router.post("/{work_order_id}/cancel")
async def cancel_work_order(
    work_order_id: str,
    body: WorkOrderCancelRequest = Body(default_factory=WorkOrderCancelRequest),
) -> dict[str, Any]:
    store = _ensure_store_configured()
    try:
        cancelled = store.cancel_work_order(work_order_id, reason=body.reason)
    except WorkOrderNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        ) from exc
    except WorkOrderTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail=_normalize_validation_error_code(exc.reason_code),
        ) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=_normalize_validation_error_code(exc.reason_code),
        ) from exc

    return {
        "ok": True,
        "work_order": cancelled.to_dict(),
    }
