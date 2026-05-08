"""Guardian intent spine routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from guardian.core.dependencies import get_current_user, require_api_key
from guardian.intents import service as intent_service
from guardian.intents.contracts import (
    GuardianIntentDispatchResult,
    GuardianIntentRequest,
)

router = APIRouter(
    prefix="/api/guardian/intents",
    tags=["Intent Spine"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/dispatch", response_model=GuardianIntentDispatchResult)
async def dispatch_intent(
    body: GuardianIntentRequest,
    request: Request,
    auth_subject: str = Depends(get_current_user),
) -> dict[str, Any]:
    inbound_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "x-api-key", "x-user-id", "cookie"}
    }
    result = await intent_service.dispatch_guardian_intent(
        intent=body,
        auth_subject=auth_subject,
        inbound_headers=inbound_headers,
        app=request.app,
    )
    return result.model_dump(mode="json")
