"""
Identity/Memory settings routes.

Thin wrapper over the durable IDDB settings service.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from guardian.core.dependencies import get_account_user as get_current_user, require_account_session as require_api_key
from guardian.services import iddb_settings_service

router = APIRouter(
    prefix="/api/iddb",
    tags=["IdentitySettings"],
    dependencies=[Depends(require_api_key)],
)

# The consent write accepts exactly one field: the consent state.  Account
# identity, actor identity, consent policy version and timestamps are derived
# by the server, so a caller cannot forge them.
_CONSENT_REQUEST_FIELDS = frozenset({"state"})


def _normalize_settings(
    body: dict[str, Any], *, current_user: str
) -> dict[str, Any]:
    settings = iddb_settings_service.get_user_settings(
        current_user, allow_legacy_default_fallback=False
    )
    try:
        return iddb_settings_service.normalize_settings_payload(
            body,
            base=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/settings")
def get_settings(
    current_user: str = Depends(get_current_user),
):
    return iddb_settings_service.get_user_settings(current_user)


@router.post("/settings")
def update_settings(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    next_settings = _normalize_settings(body, current_user=current_user)
    return iddb_settings_service.upsert_user_settings(
        current_user, next_settings
    )


@router.get("/automatic-memory-suggestions")
def get_automatic_memory_suggestions(
    current_user: str = Depends(get_current_user),
):
    """
    Return the authenticated account's automatic collection consent.

    The read is account-scoped and fail-closed: a missing, invalid, stale or
    unrecorded consent never reports as enabled.
    """
    return iddb_settings_service.read_automatic_memory_suggestions_consent(
        current_user
    )


@router.post("/automatic-memory-suggestions")
def update_automatic_memory_suggestions(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """
    Record the authenticated account's explicit collection consent.

    Only the consent state is accepted.  The account identity, the actor
    identity, the consent policy version and the timestamps are all derived
    by the server, so a forged identity, actor, timestamp or policy version
    is rejected rather than stored.
    """
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400, detail="consent request must be an object"
        )
    unsupported = sorted(set(body) - _CONSENT_REQUEST_FIELDS)
    if unsupported:
        raise HTTPException(
            status_code=400, detail="unsupported consent request fields"
        )
    if "state" not in body:
        raise HTTPException(status_code=400, detail="consent state is required")

    try:
        return iddb_settings_service.set_automatic_memory_suggestions_consent(
            current_user,
            body["state"],
            actor_user_id=current_user,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
