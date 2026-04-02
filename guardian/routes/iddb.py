"""
Identity/Memory settings routes.

Thin wrapper over the durable IDDB settings service.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from guardian.core.dependencies import get_current_user, require_api_key
from guardian.services import iddb_settings_service

router = APIRouter(
    prefix="/api/iddb",
    tags=["IdentitySettings"],
    dependencies=[Depends(require_api_key)],
)


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
