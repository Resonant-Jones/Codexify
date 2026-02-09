"""Pydantic models for cron routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CronJobCreateRequest(BaseModel):
    """Request body for creating a cron job."""

    name: str = Field(min_length=1, max_length=255)
    schedule: str = Field(min_length=1, max_length=128)
    job_type: str = Field(default="noop", min_length=1, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class CronJobUpdateRequest(BaseModel):
    """Request body for updating a cron job."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    schedule: str | None = Field(default=None, min_length=1, max_length=128)
    job_type: str | None = Field(default=None, min_length=1, max_length=32)
    payload: dict[str, Any] | None = None
    is_enabled: bool | None = None


class CronJobResponse(BaseModel):
    """Response payload for cron jobs."""

    id: int
    name: str
    schedule: str
    job_type: str
    payload: dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CronRunResponse(BaseModel):
    """Response payload for cron run records."""

    id: int
    job_id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    result: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
