"""Guardian-owned delegation proof routes for the direct v1 seam."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.dependencies import require_operator_auth
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
    dependencies=[Depends(require_operator_auth)],
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


@router.get("")
async def list_guardian_delegations(
    thread_id: int = Query(gt=0),
) -> dict[str, Any]:
    try:
        return _service.list_delegated_tasks(thread_id)
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


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


class GuardianDelegationQuarantineRequest(BaseModel):
    """One operator's explicit intent to quarantine a single unresolved run.

    The request carries the operator's *optimistic concurrency* values: the
    worker instance and the claim the operator believes still own the run.
    They do not grant authority -- the service revalidates the canonical run,
    the ownership, the lineage, and the heartbeat condition inside the
    persistence transaction.
    """

    expected_worker_instance_id: str = Field(min_length=1, max_length=64)
    expected_worker_claim_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(extra="forbid")


@router.post("/runs/{run_id}/quarantine")
async def quarantine_guardian_coding_run(
    run_id: str = Path(min_length=1, max_length=64),
    body: GuardianDelegationQuarantineRequest = ...,
    request: Request = ...,
    response: Response = ...,
) -> dict[str, Any]:
    """Record an operator-authorized uncertain-outcome quarantine.

    This is an **explicit operator action**, never an automatic recovery. The
    router already requires operator authority, and the service performs its
    own authoritative verification from the presented credential material: no
    caller-supplied boolean, actor name, or run knowledge can authorize the
    disposition.

    The route does not touch the database. The existing service and the
    existing atomic quarantine persistence operation remain the only
    implementation: the run's transition to ``escalated`` and its open
    escalation record commit together, or not at all.

    The receipt is bounded: it reports the committed disposition, the
    escalation identity, the preserved ownership, and the verified operator
    actor. It never echoes credential material, and it never claims the
    execution's external effects were prevented or undone.
    """
    operator_api_key = request.headers.get("X-API-Key")
    authorization = request.headers.get("Authorization") or ""
    operator_session_token = None
    if authorization.lower().startswith("bearer "):
        operator_session_token = authorization[7:].strip() or None
    operator_session_cookie = request.cookies.get("gc_session")

    try:
        receipt = _service.quarantine_uncertain_coding_run(
            run_id=run_id,
            # The credential material travels server-side, from the verified
            # request to the service's own verification. It is never taken
            # from the body, the query string, or the path.
            operator_api_key=operator_api_key,
            operator_session_token=operator_session_token,
            operator_session_cookie=operator_session_cookie,
            expected_worker_instance_id=body.expected_worker_instance_id,
            expected_claim_id=body.expected_worker_claim_id,
            reason=body.reason,
        )
    except GuardianDelegationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc

    already_quarantined = str(receipt.get("outcome") or "") == "already_disposed"
    # A newly committed quarantine is a created disposition; a repeated
    # request observes the existing one read-only.
    response.status_code = 200 if already_quarantined else 201
    return {
        "run_id": receipt.get("run_id"),
        "disposition": receipt.get("status") or "escalated",
        "escalation_id": receipt.get("escalation_id"),
        "reason_code": receipt.get("reason_code"),
        "original_worker_instance_id": receipt.get(
            "original_worker_instance_id"
        ),
        "original_worker_claim_id": receipt.get("original_worker_claim_id"),
        "operator_actor": receipt.get("operator_actor"),
        "already_quarantined": already_quarantined,
        "recorded_at": receipt.get("recorded_at"),
    }


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
