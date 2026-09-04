"""Account-scoped Persona Profile manifest routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from guardian.cognition.system_profiles.manifest import (
    PersonaProfileManifest,
    PersonaProfileManifestWrite,
)
from guardian.cognition.system_profiles.store import (
    StoredPersonaProfile,
    create_persona_profile,
    get_persona_profile_by_id,
    list_persona_profiles,
    persona_profile_to_dict,
    update_persona_profile,
)
from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    require_api_key,
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


def _request_account_id(request_user_scope: RequestUserScope) -> str:
    account_id = _clean_optional_text(request_user_scope.account_id)
    if not account_id:
        account_id = _clean_optional_text(request_user_scope.user_id)
    if not account_id:
        raise HTTPException(
            status_code=401,
            detail="persona profile account scope unavailable",
        )
    return account_id


class PersonaProfileResponse(BaseModel):
    id: str
    name: str
    system_prompt: str
    model_provider: str
    model_id: str
    temperature: float
    api_version: str
    current_revision: int = Field(gt=0)
    manifest: PersonaProfileManifest
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class PersonaProfileCreateRequest(BaseModel):
    manifest: PersonaProfileManifestWrite | None = None
    id: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, max_length=255)
    system_prompt: str | None = None
    model_provider: str | None = Field(default=None, max_length=64)
    model_id: str | None = Field(default=None, max_length=255)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

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
        return _clean_optional_text(value)

    @model_validator(mode="after")
    def _validate_write_shape(self) -> PersonaProfileCreateRequest:
        legacy_values = (
            self.id,
            self.name,
            self.system_prompt,
            self.model_provider,
            self.model_id,
            self.temperature,
        )
        if self.manifest is not None:
            if any(value is not None for value in legacy_values):
                raise ValueError("manifest and legacy fields may not be mixed")
            return self
        for value in legacy_values[1:]:
            if value is None:
                raise ValueError("all legacy Persona Profile fields are required")
        return self


class PersonaProfileUpdateRequest(BaseModel):
    manifest: PersonaProfileManifestWrite | None = None
    name: str | None = Field(default=None, max_length=255)
    system_prompt: str | None = None
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

    @model_validator(mode="after")
    def _reject_mixed_write(self) -> PersonaProfileUpdateRequest:
        if self.manifest is not None and any(
            value is not None
            for value in (
                self.name,
                self.system_prompt,
                self.model_provider,
                self.model_id,
                self.temperature,
            )
        ):
            raise ValueError("manifest and legacy fields may not be mixed")
        return self


def _serialize(profile: StoredPersonaProfile) -> dict[str, Any]:
    response = PersonaProfileResponse.model_validate(persona_profile_to_dict(profile))
    return response.model_dump(mode="json", by_alias=True, exclude_none=True)


@router.get("")
def list_profiles(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _request_account_id(request_user_scope)
    profiles = [
        _serialize(profile) for profile in list_persona_profiles(account_id=account_id)
    ]
    return {"ok": True, "profiles": profiles}


@router.get("/{profile_id}")
def read_profile(
    profile_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _request_account_id(request_user_scope)
    profile = get_persona_profile_by_id(profile_id, account_id=account_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="persona profile not found")
    return {"ok": True, "profile": _serialize(profile)}


@router.post("")
def create_profile(
    body: PersonaProfileCreateRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _request_account_id(request_user_scope)
    try:
        if body.manifest is not None:
            profile = create_persona_profile(
                account_id=account_id,
                manifest=body.manifest,
            )
        else:
            profile = create_persona_profile(
                account_id=account_id,
                profile_id=body.id,
                name=body.name,
                system_prompt=body.system_prompt,
                model_provider=body.model_provider,
                model_id=body.model_id,
                temperature=body.temperature,
            )
    except ValueError as exc:
        detail = str(exc)
        if detail == "persona_profile_conflict":
            raise HTTPException(
                status_code=409,
                detail="persona profile identity conflicts with existing state",
            ) from exc
        if detail == "persona_profile_owner_not_found":
            raise HTTPException(status_code=401, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return {"ok": True, "profile": _serialize(profile)}


@router.patch("/{profile_id}")
def update_profile(
    profile_id: str,
    body: PersonaProfileUpdateRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    if body.manifest is None and not any(
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

    account_id = _request_account_id(request_user_scope)
    try:
        profile = update_persona_profile(
            profile_id,
            account_id=account_id,
            manifest=body.manifest,
            name=body.name,
            system_prompt=body.system_prompt,
            model_provider=body.model_provider,
            model_id=body.model_id,
            temperature=body.temperature,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("persona_profile_not_found:"):
            raise HTTPException(
                status_code=404,
                detail="persona profile not found",
            ) from exc
        if detail == "persona_profile_revision_conflict":
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return {"ok": True, "profile": _serialize(profile)}


__all__ = ["router"]
