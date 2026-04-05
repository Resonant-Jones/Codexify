"""Worker for queued delegation tasks."""

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
from guardian.core.executors.base import ExecutorRequest, ExecutorResult
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
    """Process a queued delegation task through the Codex executor."""

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
                    "packet_id": job.packet_id,
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": "cancelled_before_execution",
                    "event_name": DelegationEventType.CANCELLED.value,
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
                result={
                    "cancelled": True,
                    "reason": "cancelled_before_execution",
                    "packet_id": job.packet_id,
                    "task_id": task.task_id,
                },
                metadata={
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "executor": job.executor,
                    "repo_path": job.repo_path,
                    "tags": list(job.tags),
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
            "packet_id": job.packet_id,
            "status": DelegationJobStatus.RUNNING.value,
            "executor": job.executor,
            "repo_path": job.repo_path,
            "event_name": DelegationEventType.RUNNING.value,
        }
        _safe_publish(
            task.task_id,
            DelegationEventType.RUNNING.value,
            running_payload,
        )

        executor = svc.resolve_executor(job.executor)
        request = ExecutorRequest(
            delegation_id=task.delegation_id,
            task_id=task.task_id,
            repo_path=job.repo_path,
            executor=job.executor,
            task_prompt=job.task_prompt,
            context=dict(job.context),
            tags=list(job.tags),
            thread_id=job.thread_id,
            project_id=job.project_id,
        )

        def _publish_progress(chunk: Any) -> None:
            if not getattr(chunk, "text", "").strip():
                return
            progress_payload = {
                "delegation_id": task.delegation_id,
                "task_id": task.task_id,
                "packet_id": job.packet_id,
                "status": DelegationJobStatus.RUNNING.value,
                "event_name": DelegationEventType.PROGRESS.value,
                "stream": getattr(chunk, "stream", "stdout"),
                "sequence": getattr(chunk, "sequence", None),
                "message": chunk.text,
                "text": chunk.text,
            }
            _safe_publish(
                task.task_id,
                DelegationEventType.PROGRESS.value,
                progress_payload,
            )

        executor_result: ExecutorResult = executor.execute(
            request,
            on_output=_publish_progress,
            should_stop=lambda: is_cancelled(task.task_id),
        )

        if executor_result.status == DelegationJobStatus.CANCELLED.value:
            cancelled = svc.cancel_delegation(task.delegation_id)
            if cancelled.changed:
                cancellation_payload = {
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "packet_id": job.packet_id,
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": executor_result.error_message
                    or "cancelled_during_execution",
                    "event_name": DelegationEventType.CANCELLED.value,
                }
                _safe_publish(
                    task.task_id,
                    DelegationEventType.CANCELLED.value,
                    cancellation_payload,
                )
            summary = svc.build_summary_packet(
                cancelled.job,
                status=DelegationJobStatus.CANCELLED.value,
                summary=executor_result.summary
                or "Delegation cancelled during execution.",
                result=executor_result.to_dict(),
                metadata={
                    "delegation_id": task.delegation_id,
                    "task_id": task.task_id,
                    "executor": job.executor,
                    "repo_path": job.repo_path,
                    "tags": list(job.tags),
                    "executor_failure": (
                        executor_result.failure.to_dict()
                        if executor_result.failure is not None
                        else None
                    ),
                },
                error_message=executor_result.error_message
                or "cancelled_during_execution",
            )
            return summary.to_dict()

        summary = svc.normalize_executor_result(
            running_job,
            executor_result,
            packet=svc.get_packet(job.packet_id),
        )
        if executor_result.status == DelegationJobStatus.FAILED.value:
            svc.mark_job_failed(
                task.delegation_id,
                error_message=summary.error_message
                or executor_result.error_message
                or "delegation_failed",
                summary=summary,
            )
            failed_payload = summary.to_dict()
            _safe_publish(
                task.task_id,
                DelegationEventType.FAILED.value,
                failed_payload,
            )
            return failed_payload

        svc.mark_job_completed(task.delegation_id, summary=summary)
        completed_payload = summary.to_dict()
        _safe_publish(
            task.task_id,
            DelegationEventType.COMPLETED.value,
            completed_payload,
        )
        return completed_payload
    except Exception as exc:
        logger.exception(
            "[delegation-worker] unexpected executor failure delegation_id=%s task_id=%s",
            task.delegation_id,
            task.task_id,
        )
        summary = svc.build_summary_packet(
            job,
            status=DelegationJobStatus.FAILED.value,
            summary=str(exc),
            result={
                "failure": {
                    "error_code": "DELEGATION_EXECUTOR_SPAWN_FAILED",
                    "failure_class": exc.__class__.__name__,
                    "message": str(exc),
                },
                "task_id": task.task_id,
                "packet_id": job.packet_id,
                "executor": job.executor,
            },
            metadata={
                "delegation_id": task.delegation_id,
                "task_id": task.task_id,
                "executor": job.executor,
                "repo_path": job.repo_path,
                "tags": list(job.tags),
            },
            error_message=str(exc),
        )
        svc.mark_job_failed(
            task.delegation_id,
            error_message=str(exc),
            summary=summary,
        )
        failed_payload = summary.to_dict()
        _safe_publish(
            task.task_id,
            DelegationEventType.FAILED.value,
            failed_payload,
        )
        return failed_payload
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
