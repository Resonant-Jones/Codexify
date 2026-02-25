"""
Tools Routes
~~~~~~~~~~~~

Minimal tools execution dispatcher and job status endpoints.
"""

from __future__ import annotations

import logging
import os
import traceback
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from guardian.core.db import GuardianDB
from guardian.core.dependencies import get_database_dsn
from guardian.db import models

logger = logging.getLogger(__name__)

IN_MEMORY_FALLBACK_ENABLED = os.getenv(
    "CODEXIFY_ENABLE_IN_MEMORY_TOOL_JOBS", "0"
).lower() in ("1", "true", "yes", "on")
JOBS: dict[str, dict[str, Any]] = {}
_db: GuardianDB | Any | None = None


class ToolRequest(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


class JobStatus(BaseModel):
    job_id: str
    tool_name: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import require_api_key
except ImportError:
    # Fallback for standalone usage
    def require_api_key(api_key: str = None):
        return api_key


def configure_db(db: GuardianDB | Any | None) -> None:
    """Override DB provider (used in tests and local embedding contexts)."""
    global _db
    _db = db


def _get_db() -> GuardianDB | Any:
    global _db
    if _db is not None:
        return _db

    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError("DATABASE_URL is not configured for tools jobs")

    _db = GuardianDB(db_url=dsn)
    return _db


@contextmanager
def _session_scope() -> Any:
    db = _get_db()
    with db.get_session() as session:
        yield session


def _dispatch_tool(body: ToolRequest) -> dict[str, Any]:
    """Current tool behavior: echo args and return an OK envelope."""
    return {"ok": True, "tool": body.name, "args": body.args}


def _serialize_job(job: models.ToolJob) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "tool_name": job.tool_name,
        "status": job.status,
        "result": job.result_json,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _execute_in_memory(job_id: str, body: ToolRequest) -> dict[str, Any]:
    """Dev-only fallback when DB storage is unavailable."""
    JOBS[job_id] = {
        "job_id": job_id,
        "tool_name": body.name,
        "status": "running",
        "request_json": body.model_dump(),
        "result": None,
        "error": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    try:
        result = _dispatch_tool(body)
        JOBS[job_id]["status"] = "succeeded"
        JOBS[job_id]["result"] = result
        JOBS[job_id]["updated_at"] = datetime.now(UTC).isoformat()
        return {
            "job_id": job_id,
            "status": "succeeded",
            "result": result,
        }
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = err_msg
        JOBS[job_id]["updated_at"] = datetime.now(UTC).isoformat()
        raise HTTPException(
            status_code=500,
            detail={"job_id": job_id, "status": "failed", "error": err_msg},
        ) from exc


router = APIRouter(tags=["Tools"])


@router.post("/tools/execute", response_model=ToolResponse)
@router.post("/api/tools/execute", response_model=ToolResponse)
def tools_execute(body: ToolRequest, api_key: str = Depends(require_api_key)):
    """
    Execute a tool and persist the job lifecycle in Postgres.

    Args:
        body: Tool execution request with name and arguments

    Returns:
        Job execution state and result payload
    """
    job_id = str(uuid4())
    payload = body.model_dump()

    try:
        with _session_scope() as session:
            job = models.ToolJob(
                id=job_id,
                tool_name=body.name,
                status="running",
                request_json=payload,
                result_json=None,
                error=None,
                error_json=None,
            )
            session.add(job)
            session.commit()
            session.refresh(job)

            try:
                result = _dispatch_tool(body)
                job.status = "succeeded"
                job.result_json = result
                job.error = None
                job.error_json = None
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.info(
                    "Tools.execute succeeded: %s job_id=%s", body.name, job_id
                )
                return {
                    "job_id": job_id,
                    "status": job.status,
                    "result": result,
                }
            except Exception as exc:
                err_msg = f"{type(exc).__name__}: {exc}"
                job.status = "failed"
                job.error = err_msg
                job.error_json = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=10),
                }
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.exception(
                    "Tools.execute failed: %s job_id=%s", body.name, job_id
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "job_id": job_id,
                        "status": "failed",
                        "error": err_msg,
                    },
                ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        logger.error("Tools.execute storage unavailable: %s", exc)
        if IN_MEMORY_FALLBACK_ENABLED:
            logger.warning(
                "Falling back to in-memory jobs; CODEXIFY_ENABLE_IN_MEMORY_TOOL_JOBS is enabled"
            )
            return _execute_in_memory(job_id=job_id, body=body)
        raise HTTPException(
            status_code=503, detail="tool_job_storage_unavailable"
        ) from exc


@router.get("/tools/jobs/{job_id}", response_model=JobStatus)
@router.get("/api/tools/jobs/{job_id}", response_model=JobStatus)
def tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Fetch a persisted tool job by id."""
    try:
        with _session_scope() as session:
            job = session.get(models.ToolJob, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="job_not_found")
            return _serialize_job(job)
    except (RuntimeError, SQLAlchemyError) as exc:
        logger.error("Tools.jobs lookup storage unavailable: %s", exc)
        if IN_MEMORY_FALLBACK_ENABLED:
            job = JOBS.get(job_id)
            if not job:
                raise HTTPException(
                    status_code=404, detail="job_not_found"
                ) from exc
            return {
                "job_id": job["job_id"],
                "tool_name": job["tool_name"],
                "status": job["status"],
                "result": job.get("result"),
                "error": job.get("error"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
            }
        raise HTTPException(
            status_code=503, detail="tool_job_storage_unavailable"
        ) from exc
