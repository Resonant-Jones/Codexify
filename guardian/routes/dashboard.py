"""Authenticated, read-only Guardian dashboard projections."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from guardian.core import dependencies
from guardian.core.auth_dependencies import resolve_session_user_id
from guardian.core.dependencies import (
    get_request_user_scope,
    require_api_key,
    require_service_api_key,
)
from guardian.core.preview_access import (
    ADMIN_ROLE,
    GUEST_ROLE,
    is_private_preview,
    require_preview_principal,
)
from guardian.routes import health as health_routes
from guardian.routes.heartbeat import heartbeat_status
from guardian.routes.user_profile import resolve_user_profile_owner


class DashboardOrientation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: list[dict[str, Any]] = Field(default_factory=list)
    presence: list[dict[str, Any]] = Field(default_factory=list)
    mentions: list[dict[str, Any]] = Field(default_factory=list)


class DashboardViewer(BaseModel):
    """Bounded current-viewer projection derived from Guardian authority."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    display_name: str | None = None
    role: Literal["admin", "guest"]
    avatar_url: str | None = None
    timezone: str | None = None


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["guardian.dashboard.snapshot.v1"] = (
        "guardian.dashboard.snapshot.v1"
    )
    generated_at: str
    source: dict[str, str]
    viewer: DashboardViewer
    health: dict[str, Any]
    runtime: dict[str, Any]
    host: dict[str, Any]
    changes: list[dict[str, Any]] = Field(default_factory=list)
    attention: list[dict[str, Any]] = Field(default_factory=list)
    orientation: DashboardOrientation = Field(
        default_factory=DashboardOrientation
    )


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_api_key)],
)


def resolve_dashboard_viewer(request: Request) -> DashboardViewer:
    """Resolve a viewer from the Guardian session, never caller input."""
    require_service_api_key(request.headers.get("X-API-Key"))
    if is_private_preview():
        principal = require_preview_principal(request)
        user_id = principal.email
        role = principal.role
    else:
        session_user_id = resolve_session_user_id(
            request.headers.get("Authorization"), request.cookies.get("gc_session")
        )
        if not session_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dashboard snapshot requires an authenticated Guardian session",
            )
        request_scope = get_request_user_scope(request)
        user_id = str(
            request_scope.account_id or request_scope.user_id or ""
        ).strip()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dashboard snapshot requires a canonical authenticated user",
            )
        role = ""

    profile, persisted_role = resolve_user_profile_owner(user_id)
    if not is_private_preview():
        role = persisted_role
    if role not in {ADMIN_ROLE, GUEST_ROLE}:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Canonical user role is invalid",
        )

    return DashboardViewer(
        user_id=user_id,
        display_name=profile.display_name,
        role=role,
        avatar_url=profile.avatar_url,
        timezone=profile.timezone,
    )


def _payload(value: Any) -> dict[str, Any]:
    """Normalize an existing health handler result without recollecting data."""
    if isinstance(value, Response):
        try:
            return json.loads(value.body.decode("utf-8"))
        except (AttributeError, json.JSONDecodeError):
            return {"status": "down", "error": "health_payload_unavailable"}
    if isinstance(value, BaseModel):
        return value.model_dump()
    return dict(value) if isinstance(value, dict) else {"value": value}


def _host_snapshot() -> dict[str, Any]:
    """Project the already-wired Guardian sensor provider with provenance."""
    sensors = getattr(dependencies, "_sensors", None)
    sensor_snapshot: dict[str, Any] = {}
    if sensors is not None and hasattr(sensors, "snapshot"):
        try:
            sensor_snapshot = dict(sensors.snapshot())
        except Exception:
            sensor_snapshot = {"status": "unavailable"}

    return {
        "hostname": socket.gethostname(),
        "process_id": os.getpid(),
        "containerized": os.path.exists("/.dockerenv"),
        "telemetry_source": "guardian.sensors.state.Sensors",
        "sensors": sensor_snapshot,
    }


def _attention_items(health: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for component, payload in health.items():
        if "status" not in payload:
            continue
        status = str(payload.get("status") or "unknown")
        if status not in {"ok", "healthy", "online"}:
            items.append(
                {
                    "component": component,
                    "status": status,
                    "reason": payload.get("error")
                    or payload.get("status_reason")
                    or "health_check_requires_attention",
                }
            )
    return items


async def build_dashboard_snapshot(
    request: Request,
    viewer: DashboardViewer,
) -> DashboardSnapshot:
    """Build one server-owned snapshot from canonical Guardian health seams."""
    core = _payload(health_routes.health(request))
    llm = _payload(health_routes.health_llm())
    chat = _payload(health_routes.health_chat())
    heartbeat = (await heartbeat_status()).model_dump()
    health = {"core": core, "llm": llm, "chat": chat, "heartbeat": heartbeat}

    return DashboardSnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source={
            "service": "guardian",
            "projection": "canonical_health_and_sensor_telemetry",
        },
        viewer=viewer,
        health=health,
        runtime={
            "provider": llm.get("provider"),
            "model": llm.get("model"),
            "chat_status": chat.get("status"),
            "worker_status": (chat.get("worker") or {}).get("status"),
            "queue_status": (chat.get("queue") or {}).get("status"),
        },
        host=_host_snapshot(),
        attention=_attention_items(health),
    )


@router.get("/snapshot", response_model=DashboardSnapshot)
async def dashboard_snapshot(
    request: Request,
    viewer: DashboardViewer = Depends(resolve_dashboard_viewer),
) -> DashboardSnapshot:
    """Return the authenticated, read-only Guardian dashboard snapshot."""
    return await build_dashboard_snapshot(request, viewer)
