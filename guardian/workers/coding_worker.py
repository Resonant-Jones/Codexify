"""Worker for coding execution tasks via PiCodexRunnerAdapter."""

from __future__ import annotations

import logging
import os
from typing import Any

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.base import AgentExecutionRequest
from guardian.agents.store import AgentStore, store
from guardian.queue import task_events
from guardian.queue.redis_queue import dequeue_coding_execution, is_cancelled
from guardian.tasks.types import CodingExecutionTask, task_from_dict

logger = logging.getLogger(__name__)

WORKER_POLL_INTERVAL_SECONDS = float(
    os.getenv("CODING_WORKER_POLL_INTERVAL_SECONDS", "0.5")
)


class CodingWorker:
    """Processes coding execution tasks from queue via PiCodexRunnerAdapter."""

    def __init__(self, agent_store: AgentStore | None = None):
        self.store = agent_store or AgentStore()

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

        # Emit running event
        self._emit_running(task)

        # Get adapter
        adapter = ADAPTERS.get("pi_codex_runner")
        if not adapter:
            self._emit_failure(
                task,
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

        # Store result and inject into thread (per ADR-020)
        self.store.store_coding_result(
            run_id=task.run_id,
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            thread_id=task.thread_id,
            source_message_id=task.source_message_id,
            result_status=result.status,
            result_summary=result.summary,
            artifacts=result.artifacts,
            errors=result.errors,
        )

        # Emit terminal event
        terminal_event = "completed" if result.status == "ok" else "failed"
        self._emit_terminal(task, terminal_event, result)

    def _emit_running(self, task: CodingExecutionTask) -> None:
        """Emit task.running event."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.running",
                {
                    "run_id": task.run_id,
                    "queue_task_id": task.task_id,
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
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
    ) -> None:
        """Emit terminal task event."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                f"task.{event_type}",
                {
                    "run_id": task.run_id,
                    "queue_task_id": task.task_id,
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
                    "status": event_type,
                    "summary": getattr(result, "summary", ""),
                    "artifacts": getattr(result, "artifacts", []),
                    "errors": getattr(result, "errors", []),
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
        error_message: str,
        error_code: str,
    ) -> None:
        """Emit task.failed event for unrecoverable errors."""
        self.store.update_run_status(run_id=task.run_id, status="failed")
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.failed",
                {
                    "run_id": task.run_id,
                    "queue_task_id": task.task_id,
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
                    "status": "failed",
                    "error_code": error_code,
                    "error_message": error_message,
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
                    "run_id": task.run_id,
                    "queue_task_id": task.task_id,
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
                    "status": "cancelled",
                    "reason": "cancelled_before_execution",
                },
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit cancelled event: %s",
                exc,
            )


def run_worker_loop() -> None:
    """Run the coding worker indefinitely."""
    logger.info("[coding-worker] starting coding worker loop")
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
