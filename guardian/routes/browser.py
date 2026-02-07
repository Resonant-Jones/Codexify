"""Browser approval listing and decision routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from guardian.browser import approval
from guardian.browser.session_manager import (
    BrowserSessionError,
    BrowserSessionManager,
)
from guardian.core import event_bus
from guardian.core.dependencies import require_api_key

router = APIRouter(
    prefix="/api/browser",
    tags=["Browser"],
    dependencies=[Depends(require_api_key)],
)


class ApprovalDecisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ApprovalRequestBody(BaseModel):
    operation: str = Field(min_length=1, max_length=64)
    target: str | None = Field(default=None, max_length=512)
    reason: str | None = Field(default=None, max_length=1000)


_session_manager: BrowserSessionManager | None = None


def configure_db(db: Any) -> None:
    approval.configure_db(db)


def configure_session_manager(manager: BrowserSessionManager) -> None:
    """Inject session manager (mainly used by tests)."""

    global _session_manager
    _session_manager = manager


def _get_session_manager() -> BrowserSessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = BrowserSessionManager()
    return _session_manager


def _emit(event_name: str, payload: dict[str, Any]) -> None:
    event_bus.emit_event(event_name, payload)


def _serialize_session(session: Any) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "status": "active",
        "created_at": session.created_at.isoformat(),
        "last_used_at": session.last_used_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "profile_dir": str(session.profile_dir),
    }


@router.get("/approvals")
async def list_approvals(status_value: str | None = None) -> dict[str, Any]:
    rows = approval.list_approvals(status=status_value, limit=200)
    return {"items": rows, "count": len(rows)}


@router.post("/approvals/request")
async def request_approval(body: ApprovalRequestBody) -> dict[str, Any]:
    created = approval.create_approval_request(
        operation=body.operation.strip().lower(),
        target=body.target,
        actor="api_key",
        request_reason=(body.reason or "").strip() or None,
    )
    _emit(
        "browser.approval.requested",
        {
            "approval_id": created["id"],
            "operation": created["operation"],
            "target": created["target"],
            "status": created["status"],
        },
    )
    return created


@router.post("/approvals/{approval_id}/approve")
async def approve_request(
    approval_id: int, body: ApprovalDecisionRequest
) -> dict[str, Any]:
    try:
        updated = approval.decide_approval(
            approval_id=approval_id,
            decision="APPROVED",
            actor="api_key",
            decision_reason=body.reason.strip(),
        )
    except approval.ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except approval.ApprovalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    _emit(
        "browser.approval.decided",
        {
            "approval_id": updated["id"],
            "operation": updated["operation"],
            "status": updated["status"],
            "decided_by": updated["decided_by"],
        },
    )
    return updated


@router.post("/approvals/{approval_id}/deny")
async def deny_request(
    approval_id: int, body: ApprovalDecisionRequest
) -> dict[str, Any]:
    try:
        updated = approval.decide_approval(
            approval_id=approval_id,
            decision="DENIED",
            actor="api_key",
            decision_reason=body.reason.strip(),
        )
    except approval.ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except approval.ApprovalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    _emit(
        "browser.approval.decided",
        {
            "approval_id": updated["id"],
            "operation": updated["operation"],
            "status": updated["status"],
            "decided_by": updated["decided_by"],
        },
    )
    return updated


@router.post("/sessions")
async def create_session() -> dict[str, Any]:
    manager = _get_session_manager()
    try:
        session = manager.create_session()
    except BrowserSessionError as exc:
        _emit(
            "browser.session.updated",
            {
                "session_id": None,
                "status": "error",
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    data = _serialize_session(session)
    _emit(
        "browser.session.updated",
        {
            "session_id": data["session_id"],
            "status": "created",
            "expires_at": data["expires_at"],
        },
    )
    return data


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    manager = _get_session_manager()
    try:
        session = manager.get_session(session_id)
    except BrowserSessionError as exc:
        _emit(
            "browser.session.updated",
            {
                "session_id": session_id,
                "status": "error",
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    data = _serialize_session(session)
    _emit(
        "browser.session.updated",
        {
            "session_id": data["session_id"],
            "status": "active",
            "expires_at": data["expires_at"],
        },
    )
    return data


@router.delete("/sessions/{session_id}")
async def close_session(session_id: str) -> dict[str, Any]:
    manager = _get_session_manager()
    closed = manager.close_session(session_id)
    status_name = "closed" if closed else "not_found"
    _emit(
        "browser.session.updated",
        {
            "session_id": session_id,
            "status": status_name,
        },
    )
    if not closed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"session not found: {session_id}",
        )
    return {"ok": True, "session_id": session_id}
