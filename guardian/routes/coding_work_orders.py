"""Durable coding work-order task-board routes (Phases 5-6 foundation).

These routes expose durable work-order control-plane state only. They do not
queue/dispatch workers, allocate worktrees, or run Git operations. The
orchestrator route provides recommendation-only outputs and does not mutate
runtime state.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

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
from guardian.command_bus.store import CommandBusStore
from guardian.core.dependencies import require_api_key
from guardian.db.models import WorkOrderResultReceipt
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
_command_bus_store: CommandBusStore | None = None


def configure_db(db: Any | None) -> None:
    global _store, _lease_store, _campaign_runner_store, _command_bus_store
    _store = WorkOrderStore(db=db)
    _lease_store = WorktreeLeaseStore(db=db)
    _campaign_runner_store = CampaignRunnerStore(db=db)
    _command_bus_store = CommandBusStore(db=db)


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


@router.get("/{work_order_id}/latest-run")
async def get_work_order_latest_run(
    work_order_id: str,
) -> dict[str, Any]:
    """Resolve a work order's latest_run_id to the durable CommandRun."""
    store = _ensure_store_configured()
    try:
        wo = store.get_work_order(work_order_id)
    except WorkOrderNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        ) from exc

    if wo is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        )

    run_id = (wo.latest_run_id or "").strip()
    if not run_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "work_order_latest_run_not_found", "work_order_id": work_order_id},
        )

    cbs = _command_bus_store
    if cbs is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "command_bus_store_unavailable"},
        )

    run = cbs.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "work_order_latest_run_missing", "work_order_id": work_order_id, "run_id": run_id},
        )

    return {
        "work_order_id": work_order_id,
        "latest_run_id": run_id,
        "run": {
            **run,
            "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
        },
    }


# ── Receipt helpers ────────────────────────────────────────────────────


def _compute_integrity_hash(
    *,
    receipt_id: str,
    work_order_id: str,
    command_run_id: str,
    receipt_kind: str,
    observed_command_id: str,
    observed_run_status: str,
    observed_result_summary: str,
    observed_error_text: str | None,
    created_at: str,
    created_by: str,
    source_thread_id: str | None,
    source_message_id: str | None,
    schema_version: int,
) -> str:
    """Compute SHA-256 integrity hash over canonical receipt payload fields."""
    payload = {
        "receipt_id": receipt_id,
        "work_order_id": work_order_id,
        "command_run_id": command_run_id,
        "receipt_kind": receipt_kind,
        "observed_command_id": observed_command_id,
        "observed_run_status": observed_run_status,
        "observed_result_summary": observed_result_summary,
        "observed_error_text": observed_error_text or "",
        "created_at": created_at,
        "created_by": created_by,
        "source_thread_id": source_thread_id or "",
        "source_message_id": source_message_id or "",
        "schema_version": schema_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _summarize_result(result_json: dict[str, Any] | None) -> str:
    """Summarize a CommandRun result_json into a safe human-readable string."""
    if not result_json:
        return "No result available"
    body = result_json.get("body")
    if isinstance(body, dict):
        status = body.get("status", "unknown")
        service = body.get("service", "")
        if service:
            return f"Status: {status}, Service: {service}"
        return f"Status: {status}"
    if isinstance(body, str):
        return body[:500]
    return "Result received"


class ReceiptCreateRequest(BaseModel):
    command_run_id: str | None = None
    operator_note: str | None = None

    model_config = ConfigDict(extra="forbid")


@router.post("/{work_order_id}/receipts", status_code=201)
async def create_work_order_receipt(
    work_order_id: str,
    body: ReceiptCreateRequest = Body(default_factory=ReceiptCreateRequest),
) -> dict[str, Any]:
    """Create an immutable receipt observing a work-order-linked CommandRun."""
    store = _ensure_store_configured()
    try:
        wo = store.get_work_order(work_order_id)
    except WorkOrderNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        ) from exc
    if wo is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        )

    # Resolve command_run_id
    run_id = (
        (body.command_run_id or "").strip()
        or (wo.latest_run_id or "").strip()
    )
    if not run_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "work_order_receipt_source_run_not_found"},
        )

    cbs = _command_bus_store
    if cbs is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "command_bus_store_unavailable"},
        )

    run = cbs.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "work_order_receipt_source_run_not_found"},
        )

    now = datetime.now(tz=timezone.utc)
    now_iso = now.isoformat()
    receipt_id = f"wor_{uuid4().hex}"
    receipt_kind = "command_run_observation"

    observed_command_id = str(run.get("command_id", ""))
    observed_run_status = str(run.get("status", ""))
    result_json = run.get("result_json")
    observed_result_summary = _summarize_result(
        result_json if isinstance(result_json, dict) else None
    )
    observed_error_text = run.get("error_text")

    integrity_hash = _compute_integrity_hash(
        receipt_id=receipt_id,
        work_order_id=work_order_id,
        command_run_id=run_id,
        receipt_kind=receipt_kind,
        observed_command_id=observed_command_id,
        observed_run_status=observed_run_status,
        observed_result_summary=observed_result_summary,
        observed_error_text=observed_error_text,
        created_at=now_iso,
        created_by="system",
        source_thread_id=wo.source_thread_id,
        source_message_id=wo.source_message_id,
        schema_version=1,
    )

    redaction_summary = {
        "args_redacted": True,
        "result_summarized": True,
    }

    provenance = {
        "receipt_kind": receipt_kind,
        "work_order_id": work_order_id,
        "command_run_id": run_id,
        "created_at": now_iso,
        "created_by": "system",
    }

    row = WorkOrderResultReceipt(
        receipt_id=receipt_id,
        work_order_id=work_order_id,
        command_run_id=run_id,
        receipt_kind=receipt_kind,
        observed_command_id=observed_command_id,
        observed_run_status=observed_run_status,
        observed_result_summary=observed_result_summary,
        observed_error_text=observed_error_text,
        created_at=now,
        created_by="system",
        source_thread_id=wo.source_thread_id,
        source_message_id=wo.source_message_id,
        provenance_json=provenance,
        redaction_summary_json=redaction_summary,
        integrity_hash=integrity_hash,
        schema_version=1,
        review_state="unreviewed",
        operator_note=body.operator_note,
    )

    # Persist within a session if DB is available
    cbs_db = getattr(cbs, "_db", None)
    if cbs_db is not None and hasattr(cbs_db, "get_session"):
        with cbs_db.get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
    else:
        # In-memory fallback — store in a simple dict on the store
        if not hasattr(cbs, "_receipts"):
            cbs._receipts = {}
        cbs._receipts[receipt_id] = row

    return _serialize_receipt(row)


# ── Receipt serialization ──────────────────────────────────────────


def _serialize_receipt(row: WorkOrderResultReceipt) -> dict[str, Any]:
    return {
        "receipt_id": row.receipt_id,
        "work_order_id": row.work_order_id,
        "command_run_id": row.command_run_id,
        "receipt_kind": row.receipt_kind,
        "observed_command_id": row.observed_command_id,
        "observed_run_status": row.observed_run_status,
        "observed_result_summary": row.observed_result_summary,
        "observed_error_text": row.observed_error_text,
        "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else row.created_at,
        "created_by": row.created_by,
        "source_thread_id": row.source_thread_id,
        "source_message_id": row.source_message_id,
        "provenance_json": row.provenance_json,
        "redaction_summary_json": row.redaction_summary_json,
        "integrity_hash": row.integrity_hash,
        "schema_version": row.schema_version,
        "review_state": row.review_state,
        "operator_note": row.operator_note,
    }


@router.get("/{work_order_id}/receipts")
async def list_work_order_receipts(
    work_order_id: str,
) -> dict[str, Any]:
    """List receipts for a work order, newest first."""
    store = _ensure_store_configured()
    try:
        wo = store.get_work_order(work_order_id)
    except WorkOrderNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        ) from exc
    if wo is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        )

    cbs = _command_bus_store
    receipts: list[dict[str, Any]] = []
    if cbs is not None:
        # Try real DB first
        cbs_db = getattr(cbs, "_db", None)
        if cbs_db is not None and hasattr(cbs_db, "get_session"):
            with cbs_db.get_session() as session:
                rows = (
                    session.query(WorkOrderResultReceipt)
                    .filter_by(work_order_id=work_order_id)
                    .order_by(WorkOrderResultReceipt.created_at.desc())
                    .all()
                )
                receipts = [_serialize_receipt(row) for row in rows]
        # Fallback to in-memory
        elif hasattr(cbs, "_receipts"):
            for row in cbs._receipts.values():
                if getattr(row, "work_order_id", None) == work_order_id:
                    receipts.append(_serialize_receipt(row))
            receipts.sort(
                key=lambda r: r.get("created_at") or "",
                reverse=True,
            )

    return {
        "work_order_id": work_order_id,
        "receipts": receipts,
    }


@router.get("/{work_order_id}/receipts/{receipt_id}")
async def get_work_order_receipt(
    work_order_id: str,
    receipt_id: str,
) -> dict[str, Any]:
    """Read a single receipt by work order id and receipt id."""
    store = _ensure_store_configured()
    try:
        wo = store.get_work_order(work_order_id)
    except WorkOrderNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        ) from exc
    if wo is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorCode.WORK_ORDER_NOT_FOUND.value,
        )

    cbs = _command_bus_store
    if cbs is not None:
        # Try real DB first
        cbs_db = getattr(cbs, "_db", None)
        if cbs_db is not None and hasattr(cbs_db, "get_session"):
            with cbs_db.get_session() as session:
                row = (
                    session.query(WorkOrderResultReceipt)
                    .filter_by(
                        receipt_id=receipt_id,
                        work_order_id=work_order_id,
                    )
                    .first()
                )
                if row is not None:
                    return _serialize_receipt(row)
        # Fallback to in-memory
        elif hasattr(cbs, "_receipts"):
            row = cbs._receipts.get(receipt_id)
            if row is not None and getattr(row, "work_order_id", None) == work_order_id:
                return _serialize_receipt(row)

    raise HTTPException(
        status_code=404,
        detail={"error": "work_order_receipt_not_found"},
    )


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
