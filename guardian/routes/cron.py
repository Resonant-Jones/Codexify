"""Cron job CRUD and run-history routes."""

from __future__ import annotations

import ipaddress
import os
import re
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from guardian.core.db import GuardianDB
from guardian.core.dependencies import require_api_key
from guardian.core.egress import require_egress_allowed
from guardian.cron.models import (
    CronJobCreateRequest,
    CronJobResponse,
    CronJobUpdateRequest,
    CronRunResponse,
)
from guardian.db import models as db_models

router = APIRouter(
    prefix="/api/cron",
    tags=["Cron"],
    dependencies=[Depends(require_api_key)],
)

_db: GuardianDB | None = None
_SIMPLE_INTERVAL_RE = re.compile(r"^\*/([1-9]\d*) \* \* \* \*$")
_PRESET_SCHEDULES = {"@hourly", "@daily", "@weekly", "@monthly"}


def configure_db(db: GuardianDB) -> None:
    """Configure database instance for cron routes."""

    global _db
    _db = db


def _get_db() -> GuardianDB:
    if _db is None:
        raise RuntimeError("Database not configured for cron router")
    return _db


def _validate_schedule(schedule: str) -> str:
    value = (schedule or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="schedule is required",
        )
    if value in _PRESET_SCHEDULES:
        return value
    if _SIMPLE_INTERVAL_RE.match(value):
        return value
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Invalid schedule. Allowed values: @hourly/@daily/@weekly/@monthly "
            "or */N * * * *"
        ),
    )


def _webhook_allowlist() -> set[str]:
    raw = (os.getenv("CRON_WEBHOOK_ALLOWLIST") or "").strip()
    if not raw:
        return set()
    return {entry.strip().lower() for entry in raw.split(",") if entry.strip()}


def _is_forbidden_host(host: str) -> bool:
    lowered = host.lower()
    if lowered in {
        "localhost",
        "0.0.0.0",
        "127.0.0.1",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }:
        return True
    if lowered.endswith(".internal") or lowered.endswith(".local"):
        return True

    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_webhook_target(payload: dict[str, Any]) -> None:
    require_egress_allowed("webhook")

    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="webhook payload.url is required",
        )
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="webhook payload.url must be a valid http(s) URL",
        )
    host = parsed.hostname.lower()
    if _is_forbidden_host(host):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="webhook target host is forbidden by default policy",
        )

    allowlist = _webhook_allowlist()
    if allowlist and host not in allowlist:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="webhook target host not present in CRON_WEBHOOK_ALLOWLIST",
        )


def _serialize_job(job: db_models.CronJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "name": job.name,
        "schedule": job.schedule,
        "job_type": job.job_type,
        "payload": job.payload or {},
        "is_enabled": bool(job.is_enabled),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _serialize_run(run: db_models.CronRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "job_id": run.job_id,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error": run.error,
        "result": run.result,
        "created_at": run.created_at,
    }


@router.post(
    "/jobs",
    response_model=CronJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cron_job(
    body: CronJobCreateRequest,
) -> dict[str, Any]:
    schedule = _validate_schedule(body.schedule)
    job_type = body.job_type.strip().lower()
    payload = body.payload or {}
    if job_type == "webhook":
        _validate_webhook_target(payload)

    db = _get_db()
    with db.get_session() as session:
        job = db_models.CronJob(
            name=body.name.strip(),
            schedule=schedule,
            job_type=job_type,
            payload=payload,
            is_enabled=body.is_enabled,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return _serialize_job(job)


@router.get("/jobs", response_model=list[CronJobResponse])
async def list_cron_jobs() -> list[dict[str, Any]]:
    db = _get_db()
    with db.get_session() as session:
        jobs = (
            session.query(db_models.CronJob)
            .order_by(db_models.CronJob.updated_at.desc())
            .all()
        )
        return [_serialize_job(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=CronJobResponse)
async def get_cron_job(
    job_id: int,
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cron job {job_id} not found",
            )
        return _serialize_job(job)


@router.patch("/jobs/{job_id}", response_model=CronJobResponse)
async def update_cron_job(
    job_id: int,
    body: CronJobUpdateRequest,
) -> dict[str, Any]:
    patch = body.model_dump(exclude_unset=True)
    db = _get_db()
    with db.get_session() as session:
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cron job {job_id} not found",
            )

        if "schedule" in patch:
            patch["schedule"] = _validate_schedule(str(patch["schedule"]))
        if "job_type" in patch and patch["job_type"] is not None:
            patch["job_type"] = str(patch["job_type"]).strip().lower()

        next_job_type = patch.get("job_type", job.job_type)
        next_payload = patch.get("payload", job.payload) or {}
        if next_job_type == "webhook":
            _validate_webhook_target(next_payload)

        for key, value in patch.items():
            setattr(job, key, value)

        session.commit()
        session.refresh(job)
        return _serialize_job(job)


@router.delete("/jobs/{job_id}")
async def delete_cron_job(
    job_id: int,
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cron job {job_id} not found",
            )
        session.delete(job)
        session.commit()
        return {"ok": True, "id": job_id}


@router.post("/jobs/{job_id}/trigger", response_model=CronRunResponse)
async def trigger_cron_job(
    job_id: int,
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cron job {job_id} not found",
            )

        run = db_models.CronRun(
            job_id=job.id,
            status="queued",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return _serialize_run(run)


@router.get("/jobs/{job_id}/runs", response_model=list[CronRunResponse])
async def list_cron_runs(
    job_id: int,
) -> list[dict[str, Any]]:
    db = _get_db()
    with db.get_session() as session:
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cron job {job_id} not found",
            )
        runs = (
            session.query(db_models.CronRun)
            .filter_by(job_id=job_id)
            .order_by(db_models.CronRun.created_at.desc())
            .all()
        )
        return [_serialize_run(run) for run in runs]
