"""Current-user profile routes for account-owned presentation metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.db.models import User, UserProfile

router = APIRouter(prefix="/api/user", tags=["User Profile"])


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class UserProfileResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)
    timezone: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "display_name", "avatar_url", "timezone", mode="before"
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return _normalize_optional_text(value)


def _profile_db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="User profile database unavailable",
        )
    return db


def _profile_payload(profile: UserProfile) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _require_canonical_user(
    session,
    request_user_scope: RequestUserScope,
) -> str:
    owner_id = str(request_user_scope.user_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Missing authenticated user")
    if session.get(User, owner_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    return owner_id


def _get_or_create_profile(session, owner_id: str) -> UserProfile:
    profile = session.scalar(
        select(UserProfile).where(UserProfile.user_id == owner_id)
    )
    if profile is not None:
        return profile

    profile = UserProfile(user_id=owner_id)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/profile")
def get_profile(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    db = _profile_db()
    with db.get_session() as session:
        owner_id = _require_canonical_user(session, request_user_scope)
        profile = _get_or_create_profile(session, owner_id)
        return {"ok": True, "profile": _profile_payload(profile).model_dump(mode="json")}


@router.patch("/profile")
def update_profile(
    body: UserProfileUpdateRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    update_values = body.model_dump(exclude_unset=True)
    if not update_values:
        raise HTTPException(
            status_code=400,
            detail="at least one profile field is required",
        )

    db = _profile_db()
    with db.get_session() as session:
        owner_id = _require_canonical_user(session, request_user_scope)
        profile = _get_or_create_profile(session, owner_id)
        if "display_name" in update_values:
            profile.display_name = body.display_name
        if "avatar_url" in update_values:
            profile.avatar_url = body.avatar_url
        if "timezone" in update_values:
            profile.timezone = body.timezone
        session.commit()
        session.refresh(profile)
        return {"ok": True, "profile": _profile_payload(profile).model_dump(mode="json")}


__all__ = ["router"]
