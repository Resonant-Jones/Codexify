"""HTTP schemas for the Guardian-owned presence and retention seams."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HeartbeatRequest(BaseModel):
    """An intentionally empty foreground heartbeat payload."""

    model_config = ConfigDict(extra="forbid")


class HeartbeatResponse(BaseModel):
    """Minimal acknowledgement with server-bounded lease timing."""

    active: bool
    active_window_seconds: int
    idle_expiry_seconds: int
    server_time: datetime


class RetentionCleanupReceipt(BaseModel):
    """Receipt for one deterministic retention cleanup execution."""

    execution_timestamp: datetime
    cutoff_presence_30d: datetime
    cutoff_idle_30m: datetime
    expired_session_count: int
    deleted_presence_count: int
    cutoff_guest_lineage_90d: datetime | None = None
    deleted_guest_count: int = 0


__all__ = [
    "HeartbeatRequest",
    "HeartbeatResponse",
    "RetentionCleanupReceipt",
]
