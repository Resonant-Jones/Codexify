"""Redis-backed UI session cache for tab/model/draft state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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
DEFAULT_MODEL_ID = "default"
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_tab(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    tab_id_raw = value.get("tabId")
    if not isinstance(tab_id_raw, str):
        return None
    tab_id = tab_id_raw.strip()
    if not tab_id:
        return None

    model_raw = value.get("modelId")
    model_id = (
        model_raw.strip()
        if isinstance(model_raw, str) and model_raw.strip()
        else DEFAULT_MODEL_ID
    )

    created_at_raw = value.get("createdAt")
    created_at = (
        created_at_raw.strip()
        if isinstance(created_at_raw, str) and created_at_raw.strip()
        else _now_iso()
    )
    updated_at_raw = value.get("updatedAt")
    updated_at = (
        updated_at_raw.strip()
        if isinstance(updated_at_raw, str) and updated_at_raw.strip()
        else created_at
    )

    normalized: dict[str, Any] = {
        "tabId": tab_id,
        "modelId": model_id,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }

    thread_id_raw = value.get("threadId")
    if thread_id_raw is not None:
        thread_id = str(thread_id_raw).strip()
        if thread_id:
            normalized["threadId"] = thread_id

    title_raw = value.get("title")
    if title_raw is not None:
        title = str(title_raw).strip()
        if title:
            normalized["title"] = title

    return normalized


def _coerce_state(
    value: Any,
    *,
    user_id: str | None = None,
    device_id: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    tabs_raw = value.get("tabs")
    if not isinstance(tabs_raw, list):
        return None

    tabs: list[dict[str, Any]] = []
    for tab in tabs_raw:
        coerced_tab = _coerce_tab(tab)
        if coerced_tab:
            tabs.append(coerced_tab)

    # Minimum-one-tab invariant.
    if not tabs:
        return None

    tab_ids = {tab["tabId"] for tab in tabs}
    active_tab_raw = value.get("activeTabId")
    active_tab_id = (
        active_tab_raw.strip() if isinstance(active_tab_raw, str) else ""
    )
    if not active_tab_id or active_tab_id not in tab_ids:
        active_tab_id = tabs[0]["tabId"]

    resolved_user = (user_id or value.get("userId") or "").strip()
    resolved_device = (device_id or value.get("deviceId") or "").strip()
    if not resolved_user or not resolved_device:
        return None

    version_raw = value.get("version")
    version = version_raw if isinstance(version_raw, int) else 1
    version = max(version, 1)

    updated_at_raw = value.get("updatedAt")
    updated_at = (
        updated_at_raw.strip()
        if isinstance(updated_at_raw, str) and updated_at_raw.strip()
        else _now_iso()
    )

    normalized: dict[str, Any] = {
        "userId": resolved_user,
        "deviceId": resolved_device,
        "tabs": tabs,
        "activeTabId": active_tab_id,
        "version": version,
        "updatedAt": updated_at,
    }

    drafts_raw = value.get("drafts")
    if isinstance(drafts_raw, dict):
        drafts: dict[str, str] = {}
        for tab_id, text in drafts_raw.items():
            if not isinstance(tab_id, str) or tab_id not in tab_ids:
                continue
            if not isinstance(text, str):
                continue
            if not text.strip():
                continue
            drafts[tab_id] = text
        if drafts:
            normalized["drafts"] = drafts

    return normalized


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
    state = _coerce_state(decoded, user_id=user_id, device_id=device_id)
    if not state:
        try:
            client.delete(key)
        except Exception:
            pass
        return {"ok": True, "state": None}
    return {"ok": True, "state": state}


@router.put("/api/ui/session")
def set_ui_session(
    body: SessionSetRequest = Body(...),  # noqa: B008
    api_key: str = Depends(require_api_key),  # noqa: B008
) -> dict[str, Any]:
    _ = api_key
    state = _coerce_state(
        dict(body.state), user_id=body.user_id, device_id=body.device_id
    )
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
        try:
            client.delete(key)
        except Exception:
            pass
        return {"ok": True, "state": None}

    current = decoded if isinstance(decoded, dict) else {}
    next_state = {**current, **body.patch}
    coerced = _coerce_state(
        next_state, user_id=body.user_id, device_id=body.device_id
    )
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
