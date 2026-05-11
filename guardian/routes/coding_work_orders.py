"""Durable coding work-order task-board routes (Phases 5-6 foundation).

These routes expose durable work-order control-plane state only. They do not
queue/dispatch workers, allocate worktrees, or run Git operations. The
orchestrator route provides recommendation-only outputs and does not mutate
runtime state.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from guardian.agents.campaign_runner_store import (
    CampaignRunnerNotFound,
    CampaignRunnerStore,
    CampaignRunnerValidationError,
)
from guardian.agents.orchestrator_policy import select_next_work_orders
from guardian.agents.work_order_store import (
    WorkOrderNotFound,
    WorkOrderStore,
    WorkOrderTransitionError,
    WorkOrderValidationError,
)
from guardian.agents.work_orders import WORK_ORDER_STATUSES, WorkOrderCreate
from guardian.agents.worktree_lease_store import WorktreeLeaseStore
from guardian.core.dependencies import require_api_key
from guardian.protocol_tokens import ErrorCode

router = APIRouter(
    prefix="/api/coding/work-orders",
    tags=["Coding Work Orders"],
    dependencies=[Depends(require_api_key)],
)
campaign_runner_router = APIRouter(
    prefix="/api/coding/campaign-runner",
    tags=["Campaign Runner"],
    dependencies=[Depends(require_api_key)],
)
orchestrator_router = APIRouter(
    prefix="/api/coding/orchestrator",
    tags=["Coding Orchestrator"],
    dependencies=[Depends(require_api_key)],
)

_store = WorkOrderStore(db=None)
_lease_store = WorktreeLeaseStore(db=None)
_campaign_runner_store = CampaignRunnerStore(db=None)


def configure_db(db: Any | None) -> None:
    global _store, _lease_store, _campaign_runner_store
    _store = WorkOrderStore(db=db)
    _lease_store = WorktreeLeaseStore(db=db)
    _campaign_runner_store = CampaignRunnerStore(db=db)


def _normalize_validation_error_code(reason_code: str | None) -> str:
    mapping = {
        "invalid_work_order_status": ErrorCode.WORK_ORDER_INVALID_STATUS.value,
        "invalid_work_order_transition": ErrorCode.WORK_ORDER_INVALID_TRANSITION.value,
    }
    if reason_code is None:
        return ErrorCode.WORK_ORDER_INVALID.value
    return mapping.get(reason_code, ErrorCode.WORK_ORDER_INVALID.value)


def _is_terminal_work_order_status(status: str) -> bool:
    return status in {"failed", "merged", "archived", "cancelled"}


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


class CampaignGoalCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str | None = None
    status: str = "active"
    source_thread_id: str | None = None
    source_message_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class CampaignCreateRequest(BaseModel):
    goal_id: str = Field(min_length=1)
    campaign_id: str | None = None
    title: str = Field(min_length=1)
    summary: str | None = None
    status: str = "active"
    source_thread_id: str | None = None
    source_message_id: str | None = None

    model_config = ConfigDict(extra="forbid")


def _ensure_store_configured() -> WorkOrderStore:
    if _store.db is None:
        raise HTTPException(
            status_code=503, detail="work_order_store_unavailable"
        )
    return _store


def _ensure_stores_configured() -> tuple[WorkOrderStore, WorktreeLeaseStore]:
    store = _ensure_store_configured()
    if _lease_store.db is None:
        raise HTTPException(
            status_code=503,
            detail="worktree_lease_store_unavailable",
        )
    return store, _lease_store


def _ensure_campaign_runner_store_configured() -> CampaignRunnerStore:
    if _campaign_runner_store.db is None:
        raise HTTPException(
            status_code=503,
            detail="campaign_runner_store_unavailable",
        )
    return _campaign_runner_store


def _list_all_work_orders(
    *,
    store: WorkOrderStore,
    campaign_id: str | None = None,
) -> list[Any]:
    items: list[Any] = []
    page_size = 200
    offset = 0
    while True:
        page = store.list_work_orders(
            status=None,
            campaign_id=campaign_id,
            limit=page_size,
            offset=offset,
        )
        if not page:
            break
        items.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return items


@campaign_runner_router.post("/goals")
async def create_campaign_goal(
    body: CampaignGoalCreateRequest,
) -> dict[str, Any]:
    campaign_store = _ensure_campaign_runner_store_configured()
    try:
        goal = campaign_store.create_goal(
            title=body.title,
            summary=body.summary,
            status=body.status,
            source_thread_id=body.source_thread_id,
            source_message_id=body.source_message_id,
        )
    except CampaignRunnerValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorCode.CAMPAIGN_GOAL_INVALID.value,
        ) from exc

    return {"ok": True, "goal": goal}


@campaign_runner_router.get("/goals/{goal_id}")
async def get_campaign_goal(goal_id: str) -> dict[str, Any]:
    campaign_store = _ensure_campaign_runner_store_configured()
    goal = campaign_store.get_goal(goal_id)
    if goal is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.CAMPAIGN_GOAL_NOT_FOUND.value,
        )
    return {"ok": True, "goal": goal}


@campaign_runner_router.post("/campaigns")
async def create_campaign(
    body: CampaignCreateRequest,
) -> dict[str, Any]:
    campaign_store = _ensure_campaign_runner_store_configured()
    try:
        campaign = campaign_store.create_campaign(
            goal_id=body.goal_id,
            campaign_id=body.campaign_id,
            title=body.title,
            summary=body.summary,
            status=body.status,
            source_thread_id=body.source_thread_id,
            source_message_id=body.source_message_id,
        )
    except CampaignRunnerNotFound as exc:
        if exc.entity == "goal":
            raise HTTPException(
                status_code=404,
                detail=ErrorCode.CAMPAIGN_GOAL_NOT_FOUND.value,
            ) from exc
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.CAMPAIGN_NOT_FOUND.value,
        ) from exc
    except CampaignRunnerValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorCode.CAMPAIGN_INVALID.value,
        ) from exc

    return {"ok": True, "campaign": campaign}


@campaign_runner_router.get("/campaigns/{campaign_id}")
async def get_campaign_detail(campaign_id: str) -> dict[str, Any]:
    store, lease_store = _ensure_stores_configured()
    campaign_store = _ensure_campaign_runner_store_configured()

    campaign = campaign_store.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.CAMPAIGN_NOT_FOUND.value,
        )

    goal = campaign_store.get_goal(str(campaign.get("goal_id") or ""))
    work_orders = _list_all_work_orders(store=store, campaign_id=campaign_id)
    active_leases = lease_store.list_active_leases()
    recommendation_result = select_next_work_orders(
        work_orders=work_orders,
        active_leases=active_leases,
        limit=1,
    )
    attempts = campaign_store.list_attempts_for_campaign(campaign_id, limit=200)
    latest_attempts_by_work_order = campaign_store.latest_attempt_by_work_order(
        campaign_id
    )
    next_recommended = (
        recommendation_result.recommendations[0].to_dict()
        if recommendation_result.recommendations
        else None
    )
    current_work_order = next(
        (
            item
            for item in work_orders
            if not _is_terminal_work_order_status(item.status)
        ),
        None,
    )
    current_work_order_id = (
        current_work_order.work_order_id if current_work_order else None
    )

    return {
        "ok": True,
        "goal": goal,
        "campaign": campaign,
        "current_work_order_id": current_work_order_id,
        "next_recommended_work_order": next_recommended,
        "recommendation_decision_reasons": list(
            recommendation_result.decision_reasons
        ),
        "recommendation_skipped": [
            item.to_dict() for item in recommendation_result.skipped
        ],
        "work_orders": [item.to_dict() for item in work_orders],
        "latest_attempts_by_work_order": latest_attempts_by_work_order,
        "attempts": attempts,
    }


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


@orchestrator_router.get("/next")
async def get_next_work_order_recommendations(
    campaign_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    store, lease_store = _ensure_stores_configured()
    work_orders = _list_all_work_orders(store=store, campaign_id=campaign_id)
    active_leases = lease_store.list_active_leases()
    result = select_next_work_orders(
        work_orders=work_orders,
        active_leases=active_leases,
        limit=limit,
    )

    payload = result.to_dict()
    payload["ok"] = True
    payload["campaign_id"] = campaign_id
    payload["limit"] = limit
    return payload
