"""Redis-backed UI session cache for tab/model/draft state."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from guardian.queue.redis_queue import get_redis_client

try:
    from guardian.core.dependencies import require_api_key
except Exception:  # pragma: no cover - test/import fallback

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key


router = APIRouter(tags=["UI Session"])

SESSION_NAMESPACE = "ui:v1"
SESSION_STATE_KEY = "session"
DEFAULT_TTL_SECONDS = int(
    os.getenv("UI_SESSION_TTL_SECONDS", str(14 * 24 * 3600))
)
MAX_TTL_SECONDS = int(
    os.getenv("UI_SESSION_MAX_TTL_SECONDS", str(30 * 24 * 3600))
)
MIN_TTL_SECONDS = int(os.getenv("UI_SESSION_MIN_TTL_SECONDS", "60"))


class SessionSetRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1)
    state: dict[str, Any]
    ttl_seconds: int | None = Field(default=None, ge=MIN_TTL_SECONDS)


class SessionPatchRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1)
    patch: dict[str, Any]
    ttl_seconds: int | None = Field(default=None, ge=MIN_TTL_SECONDS)


def _normalize_segment(value: str) -> str:
    return quote(value.strip(), safe="")


def make_session_key(user_id: str, device_id: str) -> str:
    return (
        f"{SESSION_NAMESPACE}:{_normalize_segment(user_id)}:"
        f"{_normalize_segment(device_id)}:{SESSION_STATE_KEY}"
    )


def _resolve_ttl(ttl_seconds: int | None) -> int:
    ttl = int(ttl_seconds or DEFAULT_TTL_SECONDS)
    ttl = max(MIN_TTL_SECONDS, ttl)
    ttl = min(MAX_TTL_SECONDS, ttl)
    return ttl


def _coerce_state(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    tabs = value.get("tabs")
    active_tab_id = value.get("activeTabId")
    if not isinstance(tabs, list) or not isinstance(active_tab_id, str):
        return None
    if "version" not in value:
        value["version"] = 1
    return value


@router.get("/api/ui/session")
def get_ui_session(
    user_id: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    api_key: str = Depends(require_api_key),  # noqa: B008
) -> dict[str, Any]:
    _ = api_key
    key = make_session_key(user_id, device_id)
    client = get_redis_client()
    try:
        raw = client.get(key)
    except Exception as exc:  # pragma: no cover - network/runtime failure path
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {exc}")
    if not raw:
        return {"ok": True, "state": None}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        try:
            client.delete(key)
        except Exception:
            pass
        return {"ok": True, "state": None}
    state = _coerce_state(decoded)
    if not state:
        return {"ok": True, "state": None}
    return {"ok": True, "state": state}


@router.put("/api/ui/session")
def set_ui_session(
    body: SessionSetRequest = Body(...),  # noqa: B008
    api_key: str = Depends(require_api_key),  # noqa: B008
) -> dict[str, Any]:
    _ = api_key
    state = _coerce_state(dict(body.state))
    if not state:
        raise HTTPException(
            status_code=400, detail="Invalid session state payload"
        )

    key = make_session_key(body.user_id, body.device_id)
    ttl_seconds = _resolve_ttl(body.ttl_seconds)
    payload = json.dumps(state, separators=(",", ":"), default=str)

    client = get_redis_client()
    try:
        client.setex(key, ttl_seconds, payload)
    except Exception as exc:  # pragma: no cover - network/runtime failure path
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {exc}")
    return {"ok": True}


@router.patch("/api/ui/session")
def patch_ui_session(
    body: SessionPatchRequest = Body(...),  # noqa: B008
    api_key: str = Depends(require_api_key),  # noqa: B008
) -> dict[str, Any]:
    _ = api_key
    key = make_session_key(body.user_id, body.device_id)
    client = get_redis_client()
    try:
        raw = client.get(key)
    except Exception as exc:  # pragma: no cover - network/runtime failure path
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {exc}")

    if not raw:
        return {"ok": True, "state": None}

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = {}

    current = decoded if isinstance(decoded, dict) else {}
    next_state = {**current, **body.patch}
    coerced = _coerce_state(next_state)
    if not coerced:
        raise HTTPException(
            status_code=400, detail="Invalid session patch payload"
        )

    ttl_seconds = _resolve_ttl(body.ttl_seconds)
    payload = json.dumps(coerced, separators=(",", ":"), default=str)
    try:
        client.setex(key, ttl_seconds, payload)
    except Exception as exc:  # pragma: no cover - network/runtime failure path
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {exc}")
    return {"ok": True, "state": coerced}


@router.delete("/api/ui/session")
def delete_ui_session(
    user_id: str = Query(..., min_length=1),
    device_id: str = Query(..., min_length=1),
    api_key: str = Depends(require_api_key),  # noqa: B008
) -> dict[str, Any]:
    _ = api_key
    key = make_session_key(user_id, device_id)
    client = get_redis_client()
    try:
        client.delete(key)
    except Exception as exc:  # pragma: no cover - network/runtime failure path
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {exc}")
    return {"ok": True}
