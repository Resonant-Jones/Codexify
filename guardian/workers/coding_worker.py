"""Worker for coding execution tasks via PiCodexRunnerAdapter."""

from __future__ import annotations

import logging
import os
from typing import Any

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.base import AgentExecutionRequest
from guardian.agents.events import build_coding_result_lineage_payload
from guardian.agents.store import AgentStore, store
from guardian.core import dependencies
from guardian.queue import task_events
from guardian.queue.redis_queue import dequeue_coding_execution, is_cancelled
from guardian.tasks.types import CodingExecutionTask, task_from_dict

logger = logging.getLogger(__name__)

WORKER_POLL_INTERVAL_SECONDS = float(
    os.getenv("CODING_WORKER_POLL_INTERVAL_SECONDS", "0.5")
)

_store: AgentStore = store

_SUCCESS_LIKE_CODING_RESULT_STATUSES = {
    "ok",
    "success",
    "succeeded",
    "completed",
    "partial",
    "partial_success",
    "partial-success",
}


def _normalize_coding_result_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    return value or "error"


def _is_success_like_coding_result(status: str) -> bool:
    return _normalize_coding_result_status(status) in _SUCCESS_LIKE_CODING_RESULT_STATUSES


def _normalize_artifacts(raw_artifacts: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if raw_artifacts is None:
        return normalized
    if isinstance(raw_artifacts, dict):
        raw_artifacts = [raw_artifacts]
    for item in raw_artifacts if isinstance(raw_artifacts, (list, tuple, set)) else [raw_artifacts]:
        if isinstance(item, dict):
            normalized.append(dict(item))
        else:
            normalized.append({"value": str(item)})
    return normalized


def _normalize_files_changed(
    raw_files_changed: Any,
    artifacts: list[dict[str, Any]],
) -> list[str]:
    if isinstance(raw_files_changed, (list, tuple, set)):
        normalized = [
            str(item).strip()
            for item in raw_files_changed
            if str(item).strip()
        ]
        if normalized:
            return normalized
    if isinstance(raw_files_changed, str) and raw_files_changed.strip():
        return [raw_files_changed.strip()]
    return [
        str(artifact.get("path", artifact.get("name", ""))).strip()
        for artifact in artifacts
        if str(artifact.get("path", artifact.get("name", ""))).strip()
    ]


def _coerce_optional_positive_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def configure_db(db: Any | None) -> None:
    """Bind the worker to a database-backed agent store."""
    global _store
    _store = AgentStore(db=db)


class CodingWorker:
    """Processes coding execution tasks from queue via PiCodexRunnerAdapter."""

    def __init__(self, agent_store: AgentStore | None = None):
        self.store = agent_store or _store

    def poll_once(self) -> bool:
        """Poll for and process one coding task. Returns True if task processed."""
        payload = dequeue_coding_execution(block=True, timeout=1)
        if not payload:
            return False

        task = task_from_dict(payload)
        if not isinstance(task, CodingExecutionTask):
            logger.warning(
                "[coding-worker] received non-CodingExecutionTask: %s",
                type(task).__name__,
            )
            return False

        try:
            self._process_task(task)
            return True
        except Exception as exc:
            logger.exception(
                "[coding-worker] task processing failed task_id=%s: %s",
                task.task_id,
                exc,
            )
            self._emit_failure(
                task,
                adapter_kind=None,
                error_message=str(exc),
                error_code="PROCESSING_ERROR",
            )
            return True

    def _process_task(self, task: CodingExecutionTask) -> None:
        """Process a single coding execution task."""
        # Check cancellation
        if is_cancelled(task.task_id):
            self._emit_cancelled(task)
            return

        deployment = self.store.get_deployment(task.deployment_id) or {}
        deployment_spec = dict(deployment.get("spec_json") or {})
        adapter_kind = str(deployment_spec.get("adapter_kind") or "").strip() or None

        # Emit running event
        self._emit_running(task, adapter_kind=adapter_kind)

        # Get adapter
        adapter = ADAPTERS.get("pi_codex_runner")
        if not adapter:
            self._emit_failure(
                task,
                adapter_kind=adapter_kind,
                error_message="pi_codex_runner adapter not configured",
                error_code="ADAPTER_NOT_FOUND",
            )
            return

        # Build execution request
        request = AgentExecutionRequest(
            prompt=task.instructions,
            cwd=task.cwd,
            timeout_seconds=task.timeout_seconds,
            metadata={
                "coding_task_id": task.coding_task_id,
                "attempt_id": task.attempt_id,
            },
        )

        # Execute
        result = adapter.execute(request)
        result_status = _normalize_coding_result_status(getattr(result, "status", ""))
        success_like = _is_success_like_coding_result(result_status)
        result_artifacts = _normalize_artifacts(getattr(result, "artifacts", []))
        files_changed = _normalize_files_changed(
            getattr(result, "files_changed", None),
            result_artifacts,
        )
        adapter_session_ref = getattr(result, "adapter_session_ref", None)
        error_code = getattr(result, "error_code", None)
        error_message = getattr(result, "error_message", None)
        if not error_message and not success_like:
            error_message = getattr(result, "summary", None)

        # Store result and inject into thread (per ADR-020)
        delivery = self.store.store_coding_result(
            run_id=task.run_id,
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            request_id=task.request_id or None,
            thread_id=task.thread_id,
            source_message_id=task.source_message_id,
            adapter_kind=adapter_kind,
            adapter_session_ref=adapter_session_ref,
            files_changed=files_changed,
            result_status=result_status,
            result_summary=getattr(result, "summary", ""),
            artifacts=result_artifacts,
            errors=list(getattr(result, "errors", []) or []),
            error_code=error_code,
            error_message=error_message,
        )

        if success_like and not bool(delivery.get("delivery_ok", False)):
            self._emit_failure(
                task,
                adapter_kind=adapter_kind,
                error_message=str(
                    delivery.get("delivery_reason")
                    or "coding result delivery failed"
                ),
                error_code="RESULT_DELIVERY_FAILED",
            )
            return

        # Emit terminal event
        terminal_event = "completed" if success_like else "failed"
        self._emit_terminal(
            task,
            event_type=terminal_event,
            result=result,
            adapter_kind=adapter_kind,
            result_status=result_status,
            files_changed=files_changed,
            artifacts=result_artifacts,
            adapter_session_ref=adapter_session_ref,
            delivery=delivery,
            error_code=error_code,
            error_message=error_message,
        )

    def _emit_running(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
    ) -> None:
        """Emit task.running event."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.running",
                {
                    **build_coding_result_lineage_payload(
                        run_id=task.run_id,
                        queue_task_id=task.task_id,
                        coding_task_id=task.coding_task_id,
                        attempt_id=task.attempt_id,
                        request_id=task.request_id or None,
                        source_thread_id=task.thread_id,
                        source_message_id=_coerce_optional_positive_int(
                            task.source_message_id
                        ),
                        adapter_kind=adapter_kind,
                    ),
                    "status": "running",
                },
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit running event: %s",
                exc,
            )

    def _emit_terminal(
        self,
        task: CodingExecutionTask,
        event_type: str,
        result: Any,
        *,
        adapter_kind: str | None,
        result_status: str,
        files_changed: list[str],
        artifacts: list[dict[str, Any]],
        adapter_session_ref: str | None,
        delivery: dict[str, Any],
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        """Emit terminal task event."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                f"task.{event_type}",
                {
                    **build_coding_result_lineage_payload(
                        run_id=task.run_id,
                        queue_task_id=task.task_id,
                        coding_task_id=task.coding_task_id,
                        attempt_id=task.attempt_id,
                        request_id=task.request_id or None,
                        source_thread_id=task.thread_id,
                        source_message_id=_coerce_optional_positive_int(
                            task.source_message_id
                        ),
                        adapter_kind=adapter_kind,
                    ),
                    "status": event_type,
                    "coding_result_status": result_status,
                    "result_captured_by_guardian": True,
                    "summary": getattr(result, "summary", ""),
                    "files_changed": files_changed,
                    "artifacts": artifacts,
                    "adapter_session_ref": adapter_session_ref,
                    "message_id": delivery.get("message_id"),
                    "delivery_ok": bool(delivery.get("delivery_ok", False)),
                    "delivery_reason": delivery.get("delivery_reason"),
                    "errors": list(getattr(result, "errors", []) or []),
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit terminal event: %s",
                exc,
            )

    def _emit_failure(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        error_message: str,
        error_code: str,
    ) -> None:
        """Emit task.failed event for unrecoverable errors."""
        self.store.update_run_status(
            run_id=task.run_id,
            status="failed",
            error=error_message,
        )
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.failed",
                {
                    **build_coding_result_lineage_payload(
                        run_id=task.run_id,
                        queue_task_id=task.task_id,
                        coding_task_id=task.coding_task_id,
                        attempt_id=task.attempt_id,
                        request_id=task.request_id or None,
                        source_thread_id=task.thread_id,
                        source_message_id=_coerce_optional_positive_int(
                            task.source_message_id
                        ),
                        adapter_kind=adapter_kind,
                    ),
                    "status": "failed",
                    "error_code": error_code,
                    "error_message": error_message,
                    "result_captured_by_guardian": False,
                },
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit failure event: %s",
                exc,
            )

    def _emit_cancelled(self, task: CodingExecutionTask) -> None:
        """Emit task.cancelled event."""
        self.store.update_run_status(run_id=task.run_id, status="cancelled")
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.cancelled",
                {
                    **build_coding_result_lineage_payload(
                        run_id=task.run_id,
                        queue_task_id=task.task_id,
                        coding_task_id=task.coding_task_id,
                        attempt_id=task.attempt_id,
                        request_id=task.request_id or None,
                        source_thread_id=task.thread_id,
                        source_message_id=_coerce_optional_positive_int(
                            task.source_message_id
                        ),
                    ),
                    "status": "cancelled",
                    "reason": "cancelled_before_execution",
                },
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit cancelled event: %s",
                exc,
            )


def _initialize_worker() -> None:
    db = dependencies.init_database()
    if db is None:
        raise RuntimeError("chatlog_db not configured")
    configure_db(db)


def run_worker_loop() -> None:
    """Run the coding worker indefinitely."""
    logger.info("[coding-worker] starting coding worker loop")
    _initialize_worker()
    worker = CodingWorker()

    while True:
        try:
            worker.poll_once()
        except Exception as exc:
            logger.exception("[coding-worker] poll error: %s", exc)


if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_worker_loop()
