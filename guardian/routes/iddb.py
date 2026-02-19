"""
Identity/Memory settings routes.

Thin wrapper over guardian.cognition.user_settings.store.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from guardian.cognition.user_settings import store as user_settings_store
from guardian.core.dependencies import get_current_user, require_api_key

router = APIRouter(prefix="/api/iddb", tags=["IdentitySettings"])


def _normalize_settings(
    body: dict[str, Any], *, current_user: str
) -> dict[str, Any]:
    settings = user_settings_store.get_user_settings(current_user)
    next_settings = {
        "memory_mode": body.get(
            "memory_mode", settings.get("memory_mode", "deep")
        ),
        "diary_requires_unlock": bool(
            body.get(
                "diary_requires_unlock",
                settings.get("diary_requires_unlock", False),
            )
        ),
        "allow_sensitive_modeling": bool(
            body.get(
                "allow_sensitive_modeling",
                settings.get("allow_sensitive_modeling", False),
            )
        ),
    }
    if next_settings["memory_mode"] not in ("none", "light", "deep"):
        raise HTTPException(status_code=400, detail="invalid memory_mode")
    return next_settings


@router.get("/settings")
def get_settings(
    _api_key: str = Depends(require_api_key),
    current_user: str = Depends(get_current_user),
):
    return user_settings_store.get_user_settings(current_user)


@router.post("/settings")
def update_settings(
    body: dict[str, Any] = Body(...),
    _api_key: str = Depends(require_api_key),
    current_user: str = Depends(get_current_user),
):
    next_settings = _normalize_settings(body, current_user=current_user)
    user_settings_store.set_user_settings(current_user, next_settings)
    return next_settings
