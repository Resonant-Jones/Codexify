"""Browser approval listing and decision routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from guardian.browser import approval
from guardian.core.dependencies import require_api_key

router = APIRouter(
    prefix="/api/browser",
    tags=["Browser"],
    dependencies=[Depends(require_api_key)],
)


class ApprovalDecisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


def configure_db(db: Any) -> None:
    approval.configure_db(db)


@router.get("/approvals")
async def list_approvals(status_value: str | None = None) -> dict[str, Any]:
    rows = approval.list_approvals(status=status_value, limit=200)
    return {"items": rows, "count": len(rows)}


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
    return updated
