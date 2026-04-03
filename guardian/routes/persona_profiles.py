"""Persona profile routes for Persona Studio first-wave runtime fields."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from guardian.core.dependencies import require_api_key
except Exception:  # pragma: no cover - fallback for import issues

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key


from guardian.cognition.system_profiles.store import (
    create_persona_profile,
    get_persona_profile_by_id,
    list_persona_profiles,
    persona_profile_to_dict,
    update_persona_profile,
)

router = APIRouter(
    prefix="/api/persona-profiles",
    tags=["Persona Profiles"],
    dependencies=[Depends(require_api_key)],
)


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_required_text(value: Any) -> str:
    text = _clean_optional_text(value)
    if not text:
        raise ValueError("field is required")
    return text


class PersonaProfileResponse(BaseModel):
    id: str
    name: str
    system_prompt: str
    model_provider: str
    model_id: str
    temperature: float
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class PersonaProfileCreateRequest(BaseModel):
    id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    system_prompt: str = Field(min_length=1)
    model_provider: str = Field(min_length=1, max_length=64)
    model_id: str = Field(min_length=1, max_length=255)
    temperature: float = Field(ge=0.0, le=2.0)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "id",
        "name",
        "system_prompt",
        "model_provider",
        "model_id",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _clean_optional_text(value)

    @field_validator("name", "system_prompt", "model_provider", "model_id")
    @classmethod
    def _require_text(cls, value: str | None) -> str:
        return _clean_required_text(value)


class PersonaProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    system_prompt: str | None = Field(default=None)
    model_provider: str | None = Field(default=None, max_length=64)
    model_id: str | None = Field(default=None, max_length=255)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "name", "system_prompt", "model_provider", "model_id", mode="before"
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return _clean_optional_text(value)


def _serialize(profile) -> PersonaProfileResponse:
    return PersonaProfileResponse.model_validate(
        persona_profile_to_dict(profile)
    )


@router.get("")
def list_profiles() -> dict[str, Any]:
    profiles = [
        _serialize(profile).model_dump(mode="json")
        for profile in list_persona_profiles()
    ]
    return {"ok": True, "profiles": profiles}


@router.get("/{profile_id}")
def read_profile(profile_id: str) -> dict[str, Any]:
    profile = get_persona_profile_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="persona profile not found")
    return {"ok": True, "profile": _serialize(profile).model_dump(mode="json")}


@router.post("")
def create_profile(
    body: PersonaProfileCreateRequest = Body(...),
) -> dict[str, Any]:
    try:
        profile = create_persona_profile(
            profile_id=body.id,
            name=body.name,
            system_prompt=body.system_prompt,
            model_provider=body.model_provider,
            model_id=body.model_id,
            temperature=body.temperature,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 409 if detail.startswith("persona_profile_exists:") else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return {"ok": True, "profile": _serialize(profile).model_dump(mode="json")}


@router.patch("/{profile_id}")
def update_profile(
    profile_id: str,
    body: PersonaProfileUpdateRequest = Body(...),
) -> dict[str, Any]:
    if not any(
        value is not None
        for value in (
            body.name,
            body.system_prompt,
            body.model_provider,
            body.model_id,
            body.temperature,
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="at least one first-wave persona field is required",
        )
    try:
        profile = update_persona_profile(
            profile_id,
            name=body.name,
            system_prompt=body.system_prompt,
            model_provider=body.model_provider,
            model_id=body.model_id,
            temperature=body.temperature,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("persona_profile_not_found:"):
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return {"ok": True, "profile": _serialize(profile).model_dump(mode="json")}


__all__ = ["router"]
