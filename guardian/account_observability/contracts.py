"""Typed HTTP contracts for account-observability runtime seams."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .tokens import (
    AccountObservabilityInvitePublicError,
    AccountObservabilityInviteResolutionResult,
)


class InviteCreateRequest(BaseModel):
    """Operator-authored invite metadata."""

    name: str = Field(min_length=1, max_length=255)
    campaign_label: str | None = Field(default=None, max_length=255)
    placement_label: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class InviteMetadataResponse(BaseModel):
    """Invite metadata safe for operator reads."""

    invite_id: str
    name: str
    campaign_label: str | None
    placement_label: str | None
    created_by_user_id: str
    status: str
    expires_at: datetime | None
    effective_expired: bool
    disabled_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InviteCreateResponse(InviteMetadataResponse):
    """The one response that may contain the raw bearer token."""

    raw_token: str
    invite_fragment: str


class InviteListResponse(BaseModel):
    invites: list[InviteMetadataResponse]


class InviteResolutionRequest(BaseModel):
    """Public resolver input; the token is accepted only in the JSON body."""

    token: str | None = None

    model_config = ConfigDict(extra="forbid")


class InviteResolutionResponse(BaseModel):
    """Minimal public resolver result with one generic failure code."""

    result: Literal[
        AccountObservabilityInviteResolutionResult.ATTRIBUTED.value,
        AccountObservabilityInviteResolutionResult.ALREADY_ATTRIBUTED.value,
    ] | None = None
    error: Literal[AccountObservabilityInvitePublicError.UNAVAILABLE.value] | None = None


class HeartbeatRequest(BaseModel):
    """Minimal foreground heartbeat with no analytics dimensions."""

    model_config = ConfigDict(extra="forbid")


class HeartbeatResponse(BaseModel):
    """Minimal heartbeat acknowledgement with bounded lease timing."""

    active: bool
    active_window_seconds: int
    idle_expiry_seconds: int
    server_time: datetime


class RetentionCleanupReceipt(BaseModel):
    """Structured receipt for a deterministic retention cleanup run."""

    execution_timestamp: datetime
    cutoff_presence_30d: datetime
    cutoff_idle_30m: datetime
    cutoff_guest_lineage_90d: datetime | None = None
    expired_session_count: int = 0
    deleted_presence_count: int = 0
    deleted_guest_count: int | None = None
    deferred_guest_count: int | None = None
    deferred_guest_reason: str | None = None
    dry_run: bool = False


__all__ = [
    "InviteCreateRequest",
    "InviteCreateResponse",
    "InviteListResponse",
    "InviteMetadataResponse",
    "InviteResolutionRequest",
    "InviteResolutionResponse",
    "HeartbeatRequest",
    "HeartbeatResponse",
    "RetentionCleanupReceipt",
]
