"""Cron worker: queue consumer -> executor -> run status transitions."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core import event_bus
from guardian.core.db import GuardianDB
from guardian.cron.executor import execute_cron_job
from guardian.db import models as db_models
from guardian.queue.redis_queue import dequeue

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CRON_QUEUE_NAME", "codexify:queue:cron")
_MAX_ERROR_LENGTH = 512


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_db(db: GuardianDB | None) -> GuardianDB:
    if db is not None:
        return db
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def _truncate_error(error: str) -> str:
    value = error.strip()
    if len(value) <= _MAX_ERROR_LENGTH:
        return value
    return f"{value[:_MAX_ERROR_LENGTH - 3]}..."


def process_cron_message(
    payload: dict[str, Any] | None,
    *,
    db: GuardianDB | None = None,
    executor: Callable[..., dict[str, Any]] | None = None,
    emit_events: bool = True,
) -> bool:
    """Process one queued cron message and return True on success."""

    if not isinstance(payload, dict):
        logger.warning("[cron-worker] invalid payload=%r", payload)
        return False

    try:
        run_id = int(payload.get("cron_run_id"))
        job_id = int(payload.get("cron_job_id"))
    except (TypeError, ValueError):
        logger.warning("[cron-worker] missing run/job ids payload=%r", payload)
        return False

    resolved_db = _resolve_db(db)

    with resolved_db.get_session() as session:
        run = session.query(db_models.CronRun).filter_by(id=run_id).first()
        if run is None:
            logger.warning("[cron-worker] run not found id=%s", run_id)
            return False
        job = session.query(db_models.CronJob).filter_by(id=job_id).first()
        if job is None:
            run.status = "failed"
            run.finished_at = _utc_now()
            run.error = "cron job not found"
            session.commit()
            return False

        run.status = "running"
        run.started_at = _utc_now()
        run.finished_at = None
        run.error = None
        session.commit()

    if emit_events:
        event_bus.emit_event(
            "cron.run.started",
            {"run_id": run_id, "job_id": job_id, "status": "running"},
        )

    task_executor = executor or execute_cron_job
    result: dict[str, Any] | None = None
    error_message: str | None = None
    succeeded = False
    try:
        result = task_executor(
            job_type=str(payload.get("job_type") or ""),
            payload=payload.get("payload"),
        )
        succeeded = True
    except Exception as exc:
        error_message = _truncate_error(str(exc) or exc.__class__.__name__)

    with resolved_db.get_session() as session:
        run = session.query(db_models.CronRun).filter_by(id=run_id).first()
        if run is None:
            logger.warning(
                "[cron-worker] run disappeared before finalize id=%s", run_id
            )
            return False
        run.finished_at = _utc_now()
        if succeeded:
            run.status = "succeeded"
            run.result = result
            run.error = None
        else:
            run.status = "failed"
            run.result = None
            run.error = error_message
        session.commit()

    if emit_events:
        topic = "cron.run.succeeded" if succeeded else "cron.run.failed"
        event_bus.emit_event(
            topic,
            {
                "run_id": run_id,
                "job_id": job_id,
                "status": "succeeded" if succeeded else "failed",
                "error": error_message,
            },
        )

    return succeeded


def run_forever(*, db: GuardianDB | None = None) -> None:
    logger.info("[cron-worker] worker started queue=%s", QUEUE_NAME)
    while True:
        try:
            payload = dequeue(QUEUE_NAME, block=True, timeout=5)
        except RedisTimeoutError:
            logger.debug("[cron-worker] redis idle timeout; continuing")
            continue
        except Exception as exc:
            logger.warning("[cron-worker] dequeue error; continuing: %s", exc)
            time.sleep(1.0)
            continue

        if not payload:
            continue
        process_cron_message(payload, db=db)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
