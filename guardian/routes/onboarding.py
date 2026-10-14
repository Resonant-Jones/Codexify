"""Account-purpose onboarding; independent of direct_messages admission."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import (
    RequestUserScope,
    get_account_user_scope,
    require_account_session,
)
from guardian.services import onboarding_service as service

router = APIRouter(
    prefix="/api/onboarding",
    tags=["Onboarding"],
    dependencies=[Depends(require_account_session)],
)


class OnboardingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarding_version: int = Field(default=1, ge=1, le=1, strict=True)
    status: Literal["not_started", "in_progress", "skipped", "completed"] = (
        "not_started"
    )
    last_step_key: str | None = Field(default=None, max_length=32)
    desktop_tour_completed: StrictBool = False
    mobile_tour_completed: StrictBool = False
    contextual_tips_enabled: StrictBool = True

    @field_validator("last_step_key")
    @classmethod
    def validate_step(cls, value):
        if value is not None and value not in service.STEP_KEYS:
            raise ValueError("Unknown onboarding step")
        return value


def database():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(503, "Onboarding database unavailable")
    return db


@router.get("")
def get_onboarding(scope: RequestUserScope = Depends(get_account_user_scope)):
    with database().get_session() as session:
        return service.read_state(session, scope.user_id)


@router.patch("")
def patch_onboarding(
    body: OnboardingPatch, scope: RequestUserScope = Depends(get_account_user_scope)
):
    with database().get_session() as session:
        return service.patch_state(
            session, scope.user_id, body.model_dump(exclude_unset=True)
        )
