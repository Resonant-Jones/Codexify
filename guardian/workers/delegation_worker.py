"""Stub worker for queued delegation tasks."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from guardian.core.delegation_service import (
    QUEUE_NAME,
    DelegationNotFoundError,
    DelegationService,
)
from guardian.protocol_tokens import DelegationEventType, DelegationJobStatus
from guardian.queue import task_events
from guardian.queue.redis_queue import clear_cancelled, dequeue, is_cancelled
from guardian.tasks.types import DelegationTask, task_from_dict

logger = logging.getLogger(__name__)

WORKER_POLL_INTERVAL_SECONDS = float(
    os.getenv("DELEGATION_WORKER_POLL_INTERVAL_SECONDS", "0.5")
)

_service = DelegationService()


def configure_db(db: Any | None) -> None:
    """Bind the worker to a database-backed delegation service."""

    _service.configure_db(db)


def get_service() -> DelegationService:
    return _service


def _safe_publish(
    task_id: str, event_type: str, data: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(data or {})
    try:
        return task_events.publish_with_visibility(task_id, event_type, payload)
    except Exception as exc:
        visibility_scope = task_events.classify_event_visibility(event_type)
        logger.warning(
            "[delegation-worker] publish failed task_id=%s event_type=%s err=%s",
            task_id,
            event_type,
            exc,
        )
        return {
            "ok": False,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": visibility_scope,
            "terminal_visibility": visibility_scope == "terminal",
            "execution_continued": True,
            "event_id": None,
            "failure_class": exc.__class__.__name__,
            "error": str(exc),
        }


def process_delegation_task(
    task: DelegationTask,
    *,
    service: DelegationService | None = None,
) -> dict[str, Any]:
    """Process a queued delegation task with a stub executor result."""

    svc = service or _service
    job = svc.get_job(task.delegation_id)
    if job is None:
        raise DelegationNotFoundError(
            f"delegation_not_found:{task.delegation_id}"
        )

    try:
        if is_cancelled(task.task_id):
            cancelled = svc.cancel_delegation(task.delegation_id)
            if cancelled.changed:
                cancellation_payload = {
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": "cancelled_before_execution",
                }
                _safe_publish(
                    task.task_id,
                    DelegationEventType.CANCELLED.value,
                    cancellation_payload,
                )
            summary = svc.build_summary_packet(
                cancelled.job,
                status=DelegationJobStatus.CANCELLED.value,
                summary="Delegation cancelled before execution.",
                result={"mode": "stub", "cancelled": True},
                metadata={
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "executor": task.executor,
                },
                error_message="cancelled_before_execution",
            )
            return summary.to_dict()

        running_job = svc.mark_job_running(task.delegation_id)
        if running_job.is_terminal():
            logger.info(
                "[delegation-worker] terminal delegation skipped delegation_id=%s task_id=%s status=%s",
                task.delegation_id,
                task.task_id,
                running_job.status,
            )
            return running_job.to_dict()
        running_payload = {
            "delegation_id": task.delegation_id,
            "task_id": task.task_id,
            "status": DelegationJobStatus.RUNNING.value,
            "executor": task.executor,
            "repo_path": task.repo_path,
        }
        _safe_publish(
            task.task_id,
            DelegationEventType.RUNNING.value,
            running_payload,
        )

        progress_payload = {
            "delegation_id": task.delegation_id,
            "task_id": task.task_id,
            "status": DelegationJobStatus.RUNNING.value,
            "progress": 50,
            "message": "Delegation worker stub in progress.",
        }
        _safe_publish(
            task.task_id,
            DelegationEventType.PROGRESS.value,
            progress_payload,
        )

        if is_cancelled(task.task_id):
            cancelled = svc.cancel_delegation(task.delegation_id)
            if cancelled.changed:
                cancellation_payload = {
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": "cancelled_during_execution",
                }
                _safe_publish(
                    task.task_id,
                    DelegationEventType.CANCELLED.value,
                    cancellation_payload,
                )
            summary = svc.build_summary_packet(
                cancelled.job,
                status=DelegationJobStatus.CANCELLED.value,
                summary="Delegation cancelled during execution.",
                result={"mode": "stub", "cancelled": True},
                metadata={
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "executor": task.executor,
                },
                error_message="cancelled_during_execution",
            )
            return summary.to_dict()

        summary = svc.build_summary_packet(
            running_job,
            status=DelegationJobStatus.COMPLETED.value,
            summary="Delegation worker stub completed.",
            result={
                "mode": "stub",
                "delegation_id": task.delegation_id,
                "task_id": task.task_id,
                "packet_id": task.packet_id,
            },
            metadata={
                "executor": task.executor,
                "repo_path": task.repo_path,
                "tags": list(task.tags),
            },
        )
        svc.mark_job_completed(task.delegation_id, summary=summary)
        completed_payload = summary.to_dict()
        _safe_publish(
            task.task_id,
            DelegationEventType.COMPLETED.value,
            completed_payload,
        )
        return completed_payload
    finally:
        clear_cancelled(task.task_id)


def run_once(
    *, service: DelegationService | None = None
) -> dict[str, Any] | None:
    """Consume a single delegation task from the queue if one is present."""

    raw = dequeue(QUEUE_NAME, block=False)
    if not raw:
        return None
    try:
        task = task_from_dict(raw)
    except Exception as exc:
        logger.warning(
            "[delegation-worker] skipping malformed payload err=%s",
            exc,
        )
        return None
    if not isinstance(task, DelegationTask):
        logger.debug(
            "[delegation-worker] ignoring non-delegation payload type=%s",
            getattr(task, "type", None),
        )
        return None
    return process_delegation_task(task, service=service)


def run_forever(*, service: DelegationService | None = None) -> None:
    """Block on the delegation queue and process tasks until interrupted."""

    svc = service or _service
    while True:
        raw = dequeue(QUEUE_NAME, block=True, timeout=1)
        if not raw:
            time.sleep(WORKER_POLL_INTERVAL_SECONDS)
            continue
        try:
            task = task_from_dict(raw)
        except Exception as exc:
            logger.warning(
                "[delegation-worker] skipping malformed payload err=%s",
                exc,
            )
            continue
        if not isinstance(task, DelegationTask):
            continue
        try:
            process_delegation_task(task, service=svc)
        except Exception as exc:
            logger.exception(
                "[delegation-worker] failed delegation_id=%s task_id=%s err=%s",
                getattr(task, "delegation_id", None),
                getattr(task, "task_id", None),
                exc,
            )


__all__ = [
    "configure_db",
    "get_service",
    "process_delegation_task",
    "run_forever",
    "run_once",
]
