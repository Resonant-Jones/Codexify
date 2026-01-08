"""
Identity/Memory settings routes.

Thin wrapper over guardian.cognition.user_settings.store.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from guardian.cognition.user_settings import store as user_settings_store

router = APIRouter(prefix="/api/iddb", tags=["IdentitySettings"])


def _normalize_settings(body: dict[str, Any]) -> dict[str, Any]:
    settings = user_settings_store.get_user_settings(
        body.get("user_id", "default")
    )
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
def get_settings(user_id: str = "default"):
    return user_settings_store.get_user_settings(user_id)


@router.post("/settings")
def update_settings(body: dict[str, Any] = Body(...)):
    user_id = body.get("user_id") or "default"
    next_settings = _normalize_settings(body)
    user_settings_store.set_user_settings(user_id, next_settings)
    return next_settings
