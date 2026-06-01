"""Guardian-owned delegation proof routes for the direct v1 seam."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.dependencies import require_api_key
from guardian.core.guardian_delegation_service import (
    GuardianDelegationError,
    GuardianDelegationService,
)
from guardian.protocol_tokens import (
    GuardianDelegationApprovalMode,
    GuardianDelegationInteractionMode,
)

router = APIRouter(
    prefix="/api/guardian/delegations",
    tags=["Guardian Delegations"],
    dependencies=[Depends(require_api_key)],
)

_service = GuardianDelegationService()


def configure_db(db: Any | None) -> None:
    _service.configure_db(db)


def get_service() -> GuardianDelegationService:
    return _service


class GuardianDelegationCreateRequest(BaseModel):
    thread_id: int = Field(gt=0)
    source_message_id: int = Field(gt=0)
    project_id: int | None = Field(default=None, gt=0)
    interaction_mode: GuardianDelegationInteractionMode = (
        GuardianDelegationInteractionMode.NON_BLOCKING
    )
    approval_mode: GuardianDelegationApprovalMode = (
        GuardianDelegationApprovalMode.SCOPED_AUTO
    )

    model_config = ConfigDict(extra="forbid")


@router.post("", status_code=201)
async def create_guardian_delegation(
    body: GuardianDelegationCreateRequest,
) -> dict[str, Any]:
    # Guardian Delegation Loop v1 still uses a direct Guardian-owned route to prove delegation
    # semantics. Intent-spine unification remains deferred until the hybrid
    # loop is proven, per the Guardian Delegation Loop Contract. This route
    # must not be treated as an independent long-term control plane.
    try:
        return _service.create_intent(
            thread_id=body.thread_id,
            source_message_id=body.source_message_id,
            project_id=body.project_id,
            interaction_mode=body.interaction_mode.value,
            approval_mode=body.approval_mode.value,
        )
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


@router.post("/{intent_id}/approve")
async def approve_guardian_delegation(intent_id: str) -> dict[str, Any]:
    try:
        return _service.approve_intent(intent_id)
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


@router.post("/{intent_id}/cancel")
async def cancel_guardian_delegation(intent_id: str) -> dict[str, Any]:
    try:
        return _service.cancel_intent(intent_id)
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


@router.get("/{intent_id}")
async def get_guardian_delegation(intent_id: str) -> dict[str, Any]:
    try:
        return _service.get_intent(intent_id)
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


@router.get("/{intent_id}/transcript")
async def get_guardian_delegation_transcript(intent_id: str) -> dict[str, Any]:
    try:
        return _service.get_transcript(intent_id)
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


__all__ = ["configure_db", "get_service", "router"]
