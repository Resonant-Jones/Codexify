"""Worker for queued delegation tasks."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from guardian.core.delegation_service import (
    QUEUE_NAME,
    DelegationConflictError,
    DelegationNotFoundError,
    DelegationService,
)
from guardian.core.executors.base import (
    CodexifyExecutorRequest,
    ExecutorEscalationEvent,
    ExecutorFailure,
    ExecutorProgressEvent,
    ExecutorTerminalResult,
)
from guardian.core.executors.registry import get_executor_entry
from guardian.protocol_tokens import (
    DelegationEventType,
    DelegationJobStatus,
    ErrorCode,
    ExecutorEventType,
)
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
    request: CodexifyExecutorRequest | None = None

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


def _delegation_lineage(
    job: Any,
    task: DelegationTask,
    request: CodexifyExecutorRequest | None = None,
) -> dict[str, Any]:
    request_id = getattr(request, "request_id", None) or job.delegation_id
    thread_id = getattr(request, "thread_id", None)
    if thread_id is None:
        thread_id = job.thread_id
    source_message_id = getattr(request, "source_message_id", None)
    if source_message_id is None:
        source_message_id = getattr(task, "source_message_id", None)
    project_id = getattr(request, "project_id", None)
    if project_id is None:
        project_id = job.project_id
    executor_id = getattr(request, "executor_id", None) or job.executor
    title = getattr(request, "title", None) or job.task_prompt
    tags = list(getattr(request, "tags", None) or job.tags or [])
    return {
        "request_id": request_id,
        "delegation_id": job.delegation_id,
        "task_id": job.task_id,
        "packet_id": job.packet_id,
        "thread_id": thread_id,
        "source_message_id": source_message_id,
        "project_id": project_id,
        "executor_id": executor_id,
        "title": title,
        "tags": tags,
        "repo_path": job.repo_path,
    }


def _executor_event_payload(
    *,
    job: Any,
    task: DelegationTask,
    request: CodexifyExecutorRequest,
    event: Any,
) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any]
    if isinstance(event, (ExecutorProgressEvent, ExecutorEscalationEvent)):
        payload = dict(event.to_dict())
    elif hasattr(event, "to_dict"):
        payload = dict(event.to_dict())  # type: ignore[call-arg]
    elif isinstance(event, dict):
        payload = dict(event)
    else:
        payload = {
            "text": getattr(event, "text", ""),
            "stream": getattr(event, "stream", "stdout"),
            "sequence": getattr(event, "sequence", None),
        }
    event_type = (
        str(
            payload.get("event_type")
            or payload.get("eventType")
            or getattr(event, "event_type", "")
            or ExecutorEventType.PROGRESS.value
        ).strip()
        or ExecutorEventType.PROGRESS.value
    )
    status = (
        DelegationJobStatus.COMPLETED.value
        if event_type == ExecutorEventType.COMPLETED.value
        else DelegationJobStatus.FAILED.value
        if event_type == ExecutorEventType.FAILED.value
        else DelegationJobStatus.CANCELLED.value
        if event_type == ExecutorEventType.CANCELLED.value
        else DelegationJobStatus.RUNNING.value
    )
    lineage = _delegation_lineage(job, task, request)
    payload.update(
        {
            "event_type": event_type,
            "eventType": event_type,
            "event_name": event_type,
            "status": status,
            **lineage,
        }
    )
    if event_type == ExecutorEventType.ESCALATION.value:
        payload.setdefault("escalation", getattr(event, "escalation", None))
    return event_type, payload


def _build_failure_summary(
    *,
    service: DelegationService,
    job: Any,
    task: DelegationTask,
    message: str,
    error_code: str,
    failure_class: str,
    request: CodexifyExecutorRequest | None = None,
) -> tuple[ExecutorFailure, dict[str, Any]]:
    lineage = _delegation_lineage(job, task, request)
    failure = ExecutorFailure(
        error_code=error_code,
        failure_class=failure_class,
        message=message,
        request_id=lineage["request_id"],
        thread_id=lineage["thread_id"],
        source_message_id=lineage["source_message_id"],
        project_id=lineage["project_id"],
        executor_id=lineage["executor_id"],
        kind=failure_class,
        details={
            "delegation_id": job.delegation_id,
            "task_id": job.task_id,
            "packet_id": job.packet_id,
            "executor": job.executor,
        },
        provenance={
            "request_id": lineage["request_id"],
            "delegation_id": job.delegation_id,
            "task_id": job.task_id,
            "thread_id": lineage["thread_id"],
            "source_message_id": lineage["source_message_id"],
            "project_id": lineage["project_id"],
            "executor_id": lineage["executor_id"],
            "kind": failure_class,
        },
    )
    summary = service.build_summary_packet(
        job,
        status=DelegationJobStatus.FAILED.value,
        summary=message,
        result={
            "failure": failure.to_dict(),
            **lineage,
            "error_code": error_code,
        },
        metadata={
            "failure": failure.to_dict(),
            **lineage,
            "error_code": error_code,
        },
        error_message=message,
    )
    return failure, summary


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
                    **_delegation_lineage(job, task),
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": "cancelled_before_execution",
                    "event_name": DelegationEventType.CANCELLED.value,
                    "event_type": DelegationEventType.CANCELLED.value,
                    "eventType": DelegationEventType.CANCELLED.value,
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
                    **_delegation_lineage(job, task),
                    "cancelled": True,
                    "reason": "cancelled_before_execution",
                    "packet_id": job.packet_id,
                    "task_id": task.task_id,
                },
                metadata={
                    **_delegation_lineage(job, task),
                    "executor": job.executor,
                },
                error_message="cancelled_before_execution",
            )
            return summary.to_dict()

        packet = svc.get_packet(job.packet_id)
        request: CodexifyExecutorRequest | None = None
        try:
            registry_entry = get_executor_entry(job.executor)
            executor = svc.resolve_executor(registry_entry.executor_id)
            request = svc.build_executor_request(
                job,
                packet=packet,
                task=task,
            )
        except KeyError:
            message = f"Unsupported executor id: {job.executor or '<missing>'}"
            _failure, summary = _build_failure_summary(
                service=svc,
                job=job,
                task=task,
                message=message,
                error_code=ErrorCode.DELEGATION_EXECUTOR_UNSUPPORTED.value,
                failure_class="UnsupportedExecutorError",
            )
            svc.mark_job_failed(
                task.delegation_id,
                error_message=message,
                summary=summary,
            )
            failed_payload = summary.to_dict()
            _safe_publish(
                task.task_id,
                DelegationEventType.FAILED.value,
                failed_payload,
            )
            return failed_payload
        except DelegationConflictError as exc:
            message = str(exc) or f"Unsupported executor id: {job.executor}"
            _failure, summary = _build_failure_summary(
                service=svc,
                job=job,
                task=task,
                message=message,
                error_code=ErrorCode.DELEGATION_EXECUTOR_UNSUPPORTED.value,
                failure_class=exc.__class__.__name__,
            )
            svc.mark_job_failed(
                task.delegation_id,
                error_message=message,
                summary=summary,
            )
            failed_payload = summary.to_dict()
            _safe_publish(
                task.task_id,
                DelegationEventType.FAILED.value,
                failed_payload,
            )
            return failed_payload

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
            **_delegation_lineage(job, task, request),
            "status": DelegationJobStatus.RUNNING.value,
            "event_name": DelegationEventType.RUNNING.value,
            "event_type": DelegationEventType.RUNNING.value,
            "eventType": DelegationEventType.RUNNING.value,
            "executor": job.executor,
        }
        _safe_publish(
            task.task_id,
            DelegationEventType.RUNNING.value,
            running_payload,
        )

        def _publish_progress(chunk: Any) -> None:
            if request is None:
                return
            event_type, progress_payload = _executor_event_payload(
                job=job,
                task=task,
                request=request,
                event=chunk,
            )
            text_value = str(
                progress_payload.get("text")
                or progress_payload.get("message")
                or ""
            ).strip()
            if (
                event_type == ExecutorEventType.PROGRESS.value
                and not text_value
            ):
                return
            _safe_publish(task.task_id, event_type, progress_payload)

        executor_result: ExecutorTerminalResult = executor.execute(
            request,
            on_output=_publish_progress,
            should_stop=lambda: is_cancelled(task.task_id),
        )

        if executor_result.status == DelegationJobStatus.CANCELLED.value:
            cancelled = svc.cancel_delegation(task.delegation_id)
            if cancelled.changed:
                cancellation_payload = {
                    **_delegation_lineage(job, task, request),
                    "status": DelegationJobStatus.CANCELLED.value,
                    "reason": executor_result.error_message
                    or "cancelled_during_execution",
                    "event_name": DelegationEventType.CANCELLED.value,
                    "event_type": DelegationEventType.CANCELLED.value,
                    "eventType": DelegationEventType.CANCELLED.value,
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
                    **_delegation_lineage(job, task, request),
                    "executor": job.executor,
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
        _failure, summary = _build_failure_summary(
            service=svc,
            job=job,
            task=task,
            message=str(exc),
            error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
            failure_class=exc.__class__.__name__,
            request=request,
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
