"""Shared helpers for normalized health responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Literal

HealthStatus = Literal["ok", "degraded", "down"]
HealthServiceName = Literal["core", "llm", "deps", "vector", "memory"]

_HEALTH_STATUS_ALIASES: dict[str, HealthStatus] = {
    "ok": "ok",
    "healthy": "ok",
    "online": "ok",
    "degraded": "degraded",
    "warning": "degraded",
    "stale": "degraded",
    "down": "down",
    "offline": "down",
    "unhealthy": "down",
    "error": "down",
    "fail": "down",
    "failed": "down",
    "misconfigured": "down",
    "dependency_unavailable": "down",
}


def health_timestamp(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def normalize_health_status(
    value: object | None,
    *,
    default: HealthStatus = "degraded",
) -> HealthStatus:
    if isinstance(value, bool):
        return "ok" if value else "down"

    if value is None:
        return default

    token = str(value).strip().lower()
    if not token:
        return default
    return _HEALTH_STATUS_ALIASES.get(token, default)


def build_health_response(
    service: HealthServiceName,
    status: HealthStatus,
    details: Mapping[str, Any] | None = None,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "service": service,
        "timestamp": timestamp or health_timestamp(),
        "details": dict(details or {}),
    }
