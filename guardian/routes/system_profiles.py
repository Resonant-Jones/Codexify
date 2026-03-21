from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from guardian.cognition.system_profiles.resolver import switch_thread_profile
from guardian.core.dependencies import require_api_key

# Import optional dependencies used by profile-switch helper.
try:
    from guardian.core.dependencies import chatlog_db as _CHATLOG_DB
    from guardian.core.dependencies import event_bus as _EVENT_BUS
except ImportError:
    _CHATLOG_DB = None

    class _NoopEventBus:
        @staticmethod
        def emit_event(_topic: str, _payload: dict[str, Any]) -> None:
            return None

    _EVENT_BUS = _NoopEventBus()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system-profiles", tags=["SystemProfiles"])


class SystemProfileSwitchRequest(BaseModel):
    thread_id: int | None = None
    profile_id: str | None = None


class SystemProfileSwitchResponse(BaseModel):
    ok: bool
    thread_id: int | None = None
    active_profile_id: str | None = None
    provider_override: str | None = None
    model_override: str | None = None
    profile_id: str | None = None
    error: str | None = None
    tool: str | None = None


def _coerce_thread_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def switch_profile_payload(
    *,
    thread_id: Any,
    profile_id: Any,
    tool_name: str | None = None,
    chatlog_db: Any | None = None,
    event_bus: Any | None = None,
) -> dict[str, Any]:
    resolved_thread_id = _coerce_thread_id(thread_id)
    resolved_profile_id = str(profile_id or "").strip()
    if resolved_thread_id is None:
        result: dict[str, Any] = {
            "ok": False,
            "error": "thread_id is required for guardian.profile.switch",
        }
        if tool_name:
            result["tool"] = tool_name
        return result
    if not resolved_profile_id:
        result = {"ok": False, "error": "profile_id is required"}
        if tool_name:
            result["tool"] = tool_name
        return result

    db = chatlog_db if chatlog_db is not None else _CHATLOG_DB
    bus = event_bus if event_bus is not None else _EVENT_BUS
    if db is None:
        result = {
            "ok": False,
            "error": "chat_db_unavailable",
            "thread_id": resolved_thread_id,
            "profile_id": resolved_profile_id,
        }
        if tool_name:
            result["tool"] = tool_name
        return result

    try:
        resolved = switch_thread_profile(
            thread_id=resolved_thread_id,
            profile_id=resolved_profile_id,
            chatlog_db=db,
        )
        result = {
            "ok": True,
            "thread_id": resolved_thread_id,
            "active_profile_id": resolved.active_profile_id,
            "provider_override": resolved.provider_override,
            "model_override": resolved.model_override,
        }
        if tool_name:
            result["tool"] = tool_name
        if bus is not None:
            try:
                bus.emit_event(
                    "thread.profile.switched",
                    {
                        "thread_id": resolved_thread_id,
                        "active_profile_id": resolved.active_profile_id,
                        "provider_override": resolved.provider_override,
                        "model_override": resolved.model_override,
                    },
                )
            except Exception:
                logger.debug(
                    "System profile switch event emit failed",
                    exc_info=True,
                )
        return result
    except Exception as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "thread_id": resolved_thread_id,
            "profile_id": resolved_profile_id,
        }
        if tool_name:
            result["tool"] = tool_name
        return result


@router.post(
    "/switch",
    response_model=SystemProfileSwitchResponse,
    operation_id="system_profiles_switch",
)
def switch_system_profile(
    body: SystemProfileSwitchRequest,
    api_key: str = Depends(require_api_key),
) -> dict[str, Any]:
    _ = api_key
    return switch_profile_payload(
        thread_id=body.thread_id,
        profile_id=body.profile_id,
    )
