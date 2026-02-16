"""
Tools Routes
~~~~~~~~~~~~

Minimal tools execution dispatcher and job status endpoints.
"""

import logging
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from guardian.cognition.system_profiles.resolver import switch_thread_profile

logger = logging.getLogger(__name__)

# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, Dict[str, Any]] = {}


class ToolRequest(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class ToolResponse(BaseModel):
    job_id: str
    status: str = "done"
    result: dict = Field(default_factory=dict)


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict = Field(default_factory=dict)


# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import (
        chatlog_db,
        event_bus,
        require_api_key,
    )
except ImportError:
    # Fallback for standalone usage
    def require_api_key(api_key: str = None):
        return api_key

    chatlog_db = None

    class _NoopEventBus:
        @staticmethod
        def emit_event(_topic: str, _payload: dict[str, Any]) -> None:
            return None

    event_bus = _NoopEventBus()


router = APIRouter(prefix="/tools", tags=["Tools"])
api_router = APIRouter(prefix="/api/tools", tags=["Tools"])


def _coerce_thread_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@router.post("/execute", response_model=ToolResponse)
def tools_execute(body: ToolRequest, api_key: str = Depends(require_api_key)):
    """
    Minimal tools dispatcher. For now, just echoes args and marks job done.
    Replace with real tool routing/execution as needed.

    Args:
        body: Tool execution request with name and arguments

    Returns:
        Job ID for tracking execution
    """
    jid = str(uuid4())
    result: dict[str, Any]
    args = body.args or {}

    if body.name in {"guardian.profile.switch", "set_profile"}:
        thread_id = _coerce_thread_id(args.get("thread_id"))
        profile_id = str(args.get("profile_id") or "").strip()
        if thread_id is None:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "thread_id is required for guardian.profile.switch",
            }
        elif not profile_id:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "profile_id is required",
            }
        elif chatlog_db is None:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "chat_db_unavailable",
                "thread_id": thread_id,
                "profile_id": profile_id,
            }
        else:
            try:
                resolved = switch_thread_profile(
                    thread_id=thread_id,
                    profile_id=profile_id,
                    chatlog_db=chatlog_db,
                )
                result = {
                    "ok": True,
                    "tool": body.name,
                    "thread_id": thread_id,
                    "active_profile_id": resolved.active_profile_id,
                    "provider_override": resolved.provider_override,
                    "model_override": resolved.model_override,
                }
                try:
                    event_bus.emit_event(
                        "thread.profile.switched",
                        {
                            "thread_id": thread_id,
                            "active_profile_id": resolved.active_profile_id,
                            "provider_override": resolved.provider_override,
                            "model_override": resolved.model_override,
                        },
                    )
                except Exception:
                    logger.debug(
                        "Tools.execute profile switch event emit failed",
                        exc_info=True,
                    )
            except Exception as exc:
                result = {
                    "ok": False,
                    "tool": body.name,
                    "error": str(exc),
                    "thread_id": thread_id,
                    "profile_id": profile_id,
                }
    else:
        # Example: default no-op tool path.
        result = {"ok": True, "tool": body.name, "args": args}

    JOBS[jid] = {"status": "done", "result": result}
    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
    return {"job_id": jid, "status": "done", "result": result}


@router.get("/jobs/{job_id}", response_model=JobStatus)
def tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Return job status/result for a previous tools.execute call."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return {
        "job_id": job_id,
        "status": str(job.get("status") or "unknown"),
        "result": job.get("result") or {},
    }


@api_router.post("/execute", response_model=ToolResponse)
def api_tools_execute(
    body: ToolRequest, api_key: str = Depends(require_api_key)
):
    """Compat alias for POST /tools/execute."""
    return tools_execute(body, api_key=api_key)


@api_router.get("/jobs/{job_id}", response_model=JobStatus)
def api_tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Compat alias for GET /tools/jobs/{job_id}."""
    return tools_job_status(job_id, api_key=api_key)
