"""Authenticated, read-only Guardian dashboard projections."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from guardian.core import dependencies
from guardian.core.dependencies import require_api_key
from guardian.routes import health as health_routes
from guardian.routes.heartbeat import heartbeat_status


class DashboardOrientation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: list[dict[str, Any]] = Field(default_factory=list)
    presence: list[dict[str, Any]] = Field(default_factory=list)
    mentions: list[dict[str, Any]] = Field(default_factory=list)


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["guardian.dashboard.snapshot.v1"] = (
        "guardian.dashboard.snapshot.v1"
    )
    generated_at: str
    source: dict[str, str]
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


async def build_dashboard_snapshot(request: Request) -> DashboardSnapshot:
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
async def dashboard_snapshot(request: Request) -> DashboardSnapshot:
    """Return the authenticated, read-only Guardian dashboard snapshot."""
    return await build_dashboard_snapshot(request)
