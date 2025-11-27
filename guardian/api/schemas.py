"""Pydantic schemas for Guardian API endpoints."""

from pydantic import BaseModel, Field


class PersonaSwitchRequest(BaseModel):
    """Payload for activating a companion profile."""

    profile_id: str = Field(
        ..., min_length=1, description="Identifier of the profile to activate"
    )
