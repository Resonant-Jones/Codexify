"""Cron scheduler tick logic: due job scan -> run row -> queue payload."""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core import event_bus
from guardian.core.db import GuardianDB
from guardian.db import models as db_models
from guardian.queue.redis_queue import enqueue

logger = logging.getLogger(__name__)

CRON_QUEUE_NAME = os.getenv("CRON_QUEUE_NAME", "codexify:queue:cron")
SCHEDULER_POLL_SECONDS = max(
    1, int(os.getenv("CRON_SCHEDULER_POLL_SECONDS", "30"))
)
_INTERVAL_RE = re.compile(r"^\*/([1-9]\d*) \* \* \* \*$")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _schedule_interval(schedule: str) -> timedelta | None:
    value = (schedule or "").strip().lower()
    if value == "@hourly":
        return timedelta(hours=1)
    if value == "@daily":
        return timedelta(days=1)
    if value == "@weekly":
        return timedelta(days=7)
    if value == "@monthly":
        return timedelta(days=30)
    match = _INTERVAL_RE.match(value)
    if match:
        return timedelta(minutes=int(match.group(1)))
    return None


def _is_due(
    *,
    schedule: str,
    created_at: datetime | None,
    last_run_at: datetime | None,
    now: datetime,
) -> bool:
    interval = _schedule_interval(schedule)
    if interval is None:
        return False

    if last_run_at is None:
        anchor = _coerce_utc(created_at) or now
        return now >= anchor
    return now >= (_coerce_utc(last_run_at) + interval)


def _resolve_db(db: GuardianDB | None) -> GuardianDB:
    if db is not None:
        return db
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def _default_enqueue(payload: dict[str, Any], queue_name: str) -> None:
    enqueue(payload, queue_name)


def tick_once(
    *,
    db: GuardianDB | None = None,
    now: datetime | None = None,
    queue_name: str = CRON_QUEUE_NAME,
    enqueue_fn: Callable[[dict[str, Any], str], None] | None = None,
    emit_events: bool = True,
) -> list[int]:
    """Queue due cron runs once and return queued run ids."""

    effective_now = _coerce_utc(now) or _utc_now()
    resolved_db = _resolve_db(db)
    publish = enqueue_fn or _default_enqueue
    queued_run_ids: list[int] = []

    with resolved_db.get_session() as session:
        jobs = (
            session.query(db_models.CronJob)
            .filter(db_models.CronJob.is_enabled.is_(True))
            .all()
        )
        for job in jobs:
            last_run = (
                session.query(db_models.CronRun)
                .filter(db_models.CronRun.job_id == job.id)
                .order_by(db_models.CronRun.created_at.desc())
                .first()
            )
            last_run_at = last_run.created_at if last_run else None
            if not _is_due(
                schedule=job.schedule,
                created_at=job.created_at,
                last_run_at=last_run_at,
                now=effective_now,
            ):
                continue

            run = db_models.CronRun(job_id=job.id, status="queued")
            session.add(run)
            session.commit()
            session.refresh(run)

            message = {
                "type": "cron.execute",
                "cron_run_id": run.id,
                "cron_job_id": job.id,
                "job_type": job.job_type,
                "payload": job.payload or {},
                "queued_at": effective_now.isoformat(),
            }
            publish(message, queue_name)
            queued_run_ids.append(run.id)

            if emit_events:
                event_bus.emit_event(
                    "cron.run.queued",
                    {
                        "run_id": run.id,
                        "job_id": job.id,
                        "job_type": job.job_type,
                        "status": "queued",
                    },
                )

    return queued_run_ids


def run_forever(
    *,
    db: GuardianDB | None = None,
    queue_name: str = CRON_QUEUE_NAME,
    poll_seconds: int = SCHEDULER_POLL_SECONDS,
) -> None:
    logger.info(
        "[cron-scheduler] started queue=%s poll_seconds=%s",
        queue_name,
        poll_seconds,
    )
    while True:
        try:
            run_ids = tick_once(db=db, queue_name=queue_name)
            if run_ids:
                logger.info("[cron-scheduler] queued runs=%s", run_ids)
        except Exception as exc:
            logger.warning("[cron-scheduler] tick failed err=%s", exc)
        time.sleep(poll_seconds)


__all__ = ["CRON_QUEUE_NAME", "run_forever", "tick_once"]
