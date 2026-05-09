"""Bounded coding-worker validation loop.

This module keeps the retry boundary local and supervised. It does not create
git commits or mutate route acceptance semantics; it only retries validation
after a success-like adapter result when policy allows shell execution.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal, Protocol

from guardian.agents.adapters.base import (
    AgentExecutionRequest,
    AgentRunEnvelope,
)
from guardian.agents.coding_agent_contracts import CodingAgentResult
from guardian.agents.events import AgentEventPublisher
from guardian.agents.events import publisher as default_publisher
from guardian.agents.store import AgentStore
from guardian.agents.store import store as default_store
from guardian.agents.test_results import (
    NormalizedTestResult,
    normalize_subprocess_test_result,
    not_run_test_result,
)
from guardian.protocol_tokens import ErrorCode, TaskEventType
from guardian.tasks.types import CodingExecutionTask

CodingWorkerStatus = Literal["completed", "failed"]

_DEFAULT_MAX_VALIDATION_ATTEMPTS = 3
_MIN_VALIDATION_ATTEMPTS = 1
_MAX_VALIDATION_ATTEMPTS = 10
_PROMPT_FEEDBACK_LIMIT = 640


class CodingAdapter(Protocol):
    name: str

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        ...


ValidationRunner = Callable[
    [str, str | None, int | None], subprocess.CompletedProcess[str]
]
AdapterResolver = Callable[[str], CodingAdapter | None]


@dataclass(frozen=True)
class CodingWorkerOutcome:
    status: CodingWorkerStatus
    attempts: int
    coding_result: CodingAgentResult | None = None
    validation_result: NormalizedTestResult | None = None
    best_validation_result: NormalizedTestResult | None = None
    error_code: str | None = None
    error_message: str | None = None


def resolve_max_validation_attempts(
    task_limit: int | None = None,
    env_value: Any | None = None,
) -> int:
    raw_value = task_limit if task_limit is not None else env_value
    if raw_value is None:
        raw_value = os.getenv("CODING_WORKER_MAX_VALIDATION_ATTEMPTS")
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = _DEFAULT_MAX_VALIDATION_ATTEMPTS
    return max(_MIN_VALIDATION_ATTEMPTS, min(_MAX_VALIDATION_ATTEMPTS, value))


def _bounded_text(text: str | None, limit: int = _PROMPT_FEEDBACK_LIMIT) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return value if len(value) <= limit else value[:limit]


def _is_success_like(result: AgentRunEnvelope) -> bool:
    status = str(getattr(result, "status", "") or "").strip().lower()
    return status in {"ok", "completed", "success", "succeeded"}


def _run_default_validation(
    command: str,
    cwd: str | None,
    timeout_seconds: int | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or None,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )


def _result_to_feedback_block(
    *,
    validation_command: str,
    result: NormalizedTestResult,
) -> str:
    lines = [
        "Validation failed. Fix only the original task scope.",
        f"Validation command: {validation_command}",
        f"Validation status: {result.status}",
        f"Exit code: {result.exit_code}",
    ]
    if result.fail_signature:
        lines.append(f"Fail signature: {result.fail_signature}")
    if result.error_message:
        lines.append(
            f"Error message: {_bounded_text(result.error_message, 240)}"
        )
    if result.stdout_preview:
        lines.append("Stdout preview:")
        lines.append(_bounded_text(result.stdout_preview))
    if result.stderr_preview:
        lines.append("Stderr preview:")
        lines.append(_bounded_text(result.stderr_preview))
    return "\n".join(lines)


def _best_validation_result(
    current: NormalizedTestResult,
    best: NormalizedTestResult | None,
) -> NormalizedTestResult:
    if best is None:
        return current
    if current.status == "passed" and best.status != "passed":
        return current
    if best.status == "passed" and current.status != "passed":
        return best
    if current.tests_failed is not None and best.tests_failed is not None:
        if current.tests_failed < best.tests_failed:
            return current
        if current.tests_failed > best.tests_failed:
            return best
    return best


def _validation_timeout_result(
    *,
    command: str,
    timeout_seconds: int | None,
    exc: subprocess.TimeoutExpired,
) -> NormalizedTestResult:
    return NormalizedTestResult(
        status="error",
        command=command,
        exit_code=None,
        stdout_preview=_bounded_text(
            exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout
        ),
        stderr_preview=_bounded_text(
            exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
        ),
        duration_seconds=float(timeout_seconds)
        if timeout_seconds is not None
        else None,
        error_message=(
            f"validation timed out after {timeout_seconds}s"
            if timeout_seconds is not None
            else "validation timed out"
        ),
    )


class CodingWorker:
    def __init__(
        self,
        *,
        store: AgentStore | None = None,
        event_publisher: AgentEventPublisher | None = None,
        adapter_resolver: AdapterResolver | None = None,
        validation_runner: ValidationRunner | None = None,
        env: dict[str, Any] | None = None,
    ) -> None:
        self._store = store or default_store
        self._event_publisher = event_publisher or default_publisher
        self._adapter_resolver = adapter_resolver
        self._validation_runner = validation_runner or _run_default_validation
        self._env = dict(env or os.environ)

    def _emit(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self._event_publisher.emit(
            run_id=run_id, event_type=event_type, payload=payload
        )

    def _resolve_adapter(self, adapter_kind: str) -> CodingAdapter | None:
        if self._adapter_resolver is None:
            return None
        return self._adapter_resolver(adapter_kind)

    def _store_success(
        self,
        *,
        run_id: str,
        task: CodingExecutionTask,
        attempt_index: int,
        adapter_result: AgentRunEnvelope,
        validation_result: NormalizedTestResult | None,
        best_validation_result: NormalizedTestResult | None,
    ) -> CodingAgentResult:
        coding_result = CodingAgentResult(
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            status="completed",
            summary=(
                str(adapter_result.summary or "").strip()
                or "Coding task completed"
            ),
            files_changed=tuple(),
            artifacts=tuple(),
            logs_summary=(
                "Validation passed"
                if validation_result is None
                else f"Validation passed after {attempt_index} attempt(s)"
            ),
            error_code=None,
            error_message=None,
            adapter_session_ref=None,
        )
        self._store.store_coding_result(
            run_id=run_id,
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            result_json={
                "attempt_count": attempt_index,
                "adapter_kind": task.adapter_kind,
                "coding_result": asdict(coding_result),
                "validation_result": (
                    validation_result.model_dump()
                    if validation_result is not None
                    else None
                ),
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
                "validation_command": task.validation_command,
            },
        )
        if hasattr(self._store, "update_run_status"):
            self._store.update_run_status(run_id=run_id, status="succeeded")
        return coding_result

    def _store_failure(
        self,
        *,
        run_id: str,
        task: CodingExecutionTask,
        attempt_index: int,
        summary: str,
        error_code: str | None,
        error_message: str | None,
    ) -> CodingAgentResult:
        if hasattr(self._store, "update_run_status"):
            self._store.update_run_status(
                run_id=run_id,
                status="failed",
                error=error_code or error_message,
            )
        return CodingAgentResult(
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            status="failed_fatal",
            summary=summary,
            files_changed=tuple(),
            artifacts=tuple(),
            logs_summary=f"Attempts exhausted after {attempt_index} attempt(s)",
            error_code=error_code,
            error_message=error_message,
            adapter_session_ref=None,
        )

    def _process_task(self, task: CodingExecutionTask) -> CodingWorkerOutcome:
        run_id = task.run_id or task.coding_task_id or task.task_id
        max_attempts = resolve_max_validation_attempts(
            task.max_validation_attempts,
            self._env.get("CODING_WORKER_MAX_VALIDATION_ATTEMPTS"),
        )
        adapter = self._resolve_adapter(task.adapter_kind)
        if adapter is None:
            coding_result = self._store_failure(
                run_id=run_id,
                task=task,
                attempt_index=1,
                summary="Unknown coding adapter",
                error_code=ErrorCode.CODING_ADAPTER_NOT_FOUND.value,
                error_message=f"unknown adapter '{task.adapter_kind}'",
            )
            self._emit(
                run_id=run_id,
                event_type=TaskEventType.TASK_FAILED.value,
                payload={
                    "coding_task_id": task.coding_task_id,
                    "attempt_count": 1,
                    "error_code": ErrorCode.CODING_ADAPTER_NOT_FOUND.value,
                    "error_message": f"unknown adapter '{task.adapter_kind}'",
                },
            )
            return CodingWorkerOutcome(
                status="failed",
                attempts=1,
                coding_result=coding_result,
                error_code=ErrorCode.CODING_ADAPTER_NOT_FOUND.value,
                error_message=f"unknown adapter '{task.adapter_kind}'",
            )

        prompt = task.instructions
        best_validation_result: NormalizedTestResult | None = None
        for attempt_index in range(1, max_attempts + 1):
            self._emit(
                run_id=run_id,
                event_type=TaskEventType.TASK_ATTEMPT_STARTED.value,
                payload={
                    "coding_task_id": task.coding_task_id,
                    "attempt_index": attempt_index,
                    "max_attempts": max_attempts,
                    "adapter_kind": task.adapter_kind,
                },
            )
            try:
                adapter_result = adapter.execute(
                    AgentExecutionRequest(
                        prompt=prompt,
                        cwd=task.repo_root,
                        timeout_seconds=(
                            task.permission_policy.max_runtime_seconds
                        ),
                        metadata={
                            "coding_task_id": task.coding_task_id,
                            "attempt_index": attempt_index,
                            "run_id": run_id,
                        },
                    )
                )
            except Exception as exc:
                coding_result = self._store_failure(
                    run_id=run_id,
                    task=task,
                    attempt_index=attempt_index,
                    summary="Adapter execution raised an exception",
                    error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
                    error_message=str(exc),
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_FAILED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "error_code": ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
                        "error_message": str(exc),
                    },
                )
                return CodingWorkerOutcome(
                    status="failed",
                    attempts=attempt_index,
                    coding_result=coding_result,
                    error_code=ErrorCode.DELEGATION_EXECUTOR_SPAWN_FAILED.value,
                    error_message=str(exc),
                )

            if not _is_success_like(adapter_result):
                coding_result = self._store_failure(
                    run_id=run_id,
                    task=task,
                    attempt_index=attempt_index,
                    summary="Adapter execution failed",
                    error_code=ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value,
                    error_message=str(
                        adapter_result.errors[0]
                        if getattr(adapter_result, "errors", None)
                        else adapter_result.summary
                        or "adapter execution failed"
                    ),
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_FAILED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "error_code": ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value,
                        "adapter_result": adapter_result.model_dump(),
                    },
                )
                return CodingWorkerOutcome(
                    status="failed",
                    attempts=attempt_index,
                    coding_result=coding_result,
                    error_code=ErrorCode.DELEGATION_EXECUTOR_NONZERO_EXIT.value,
                    error_message=str(
                        adapter_result.summary or "adapter execution failed"
                    ),
                )

            if not task.validation_command:
                coding_result = self._store_success(
                    run_id=run_id,
                    task=task,
                    attempt_index=attempt_index,
                    adapter_result=adapter_result,
                    validation_result=None,
                    best_validation_result=None,
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_COMPLETED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "validation_result": None,
                    },
                )
                return CodingWorkerOutcome(
                    status="completed",
                    attempts=attempt_index,
                    coding_result=coding_result,
                )

            if not task.permission_policy.allow_shell:
                validation_result = not_run_test_result(
                    "shell execution disallowed by permission policy",
                    command=task.validation_command,
                )
                best_validation_result = _best_validation_result(
                    validation_result, best_validation_result
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_VALIDATION_FAILED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "validation_result": validation_result.model_dump(),
                        "best_validation_result": (
                            best_validation_result.model_dump()
                            if best_validation_result is not None
                            else None
                        ),
                        "retryable": False,
                    },
                )
                coding_result = self._store_failure(
                    run_id=run_id,
                    task=task,
                    attempt_index=attempt_index,
                    summary="Validation command blocked by policy",
                    error_code=ErrorCode.VALIDATION_FAILED.value,
                    error_message=validation_result.error_message,
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_FAILED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "error_code": ErrorCode.VALIDATION_FAILED.value,
                        "validation_result": validation_result.model_dump(),
                        "best_validation_result": (
                            best_validation_result.model_dump()
                            if best_validation_result is not None
                            else None
                        ),
                    },
                )
                return CodingWorkerOutcome(
                    status="failed",
                    attempts=attempt_index,
                    coding_result=coding_result,
                    validation_result=validation_result,
                    best_validation_result=best_validation_result,
                    error_code=ErrorCode.VALIDATION_FAILED.value,
                    error_message=validation_result.error_message,
                )

            try:
                validation_proc = self._validation_runner(
                    task.validation_command,
                    task.repo_root,
                    task.permission_policy.max_runtime_seconds,
                )
                validation_result = normalize_subprocess_test_result(
                    command=task.validation_command,
                    exit_code=int(validation_proc.returncode),
                    stdout=str(validation_proc.stdout or ""),
                    stderr=str(validation_proc.stderr or ""),
                    duration_seconds=None,
                )
            except subprocess.TimeoutExpired as exc:
                validation_result = _validation_timeout_result(
                    command=task.validation_command,
                    timeout_seconds=task.permission_policy.max_runtime_seconds,
                    exc=exc,
                )

            best_validation_result = _best_validation_result(
                validation_result, best_validation_result
            )

            if validation_result.status == "passed":
                coding_result = self._store_success(
                    run_id=run_id,
                    task=task,
                    attempt_index=attempt_index,
                    adapter_result=adapter_result,
                    validation_result=validation_result,
                    best_validation_result=best_validation_result,
                )
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_COMPLETED.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_count": attempt_index,
                        "validation_result": validation_result.model_dump(),
                        "best_validation_result": (
                            best_validation_result.model_dump()
                            if best_validation_result is not None
                            else None
                        ),
                    },
                )
                return CodingWorkerOutcome(
                    status="completed",
                    attempts=attempt_index,
                    coding_result=coding_result,
                    validation_result=validation_result,
                    best_validation_result=best_validation_result,
                )

            self._emit(
                run_id=run_id,
                event_type=TaskEventType.TASK_VALIDATION_FAILED.value,
                payload={
                    "coding_task_id": task.coding_task_id,
                    "attempt_count": attempt_index,
                    "validation_result": validation_result.model_dump(),
                    "best_validation_result": (
                        best_validation_result.model_dump()
                        if best_validation_result is not None
                        else None
                    ),
                    "retryable": attempt_index < max_attempts,
                },
            )

            if attempt_index < max_attempts:
                self._emit(
                    run_id=run_id,
                    event_type=TaskEventType.TASK_RETRYING.value,
                    payload={
                        "coding_task_id": task.coding_task_id,
                        "attempt_index": attempt_index,
                        "next_attempt_index": attempt_index + 1,
                        "max_attempts": max_attempts,
                        "validation_result": validation_result.model_dump(),
                    },
                )
                feedback_block = _result_to_feedback_block(
                    validation_command=task.validation_command,
                    result=validation_result,
                )
                prompt = f"{task.instructions}\n\n{feedback_block}"
                continue

            coding_result = self._store_failure(
                run_id=run_id,
                task=task,
                attempt_index=attempt_index,
                summary="Validation attempts exhausted",
                error_code=ErrorCode.VALIDATION_FAILED.value,
                error_message=(
                    validation_result.error_message or "validation failed"
                ),
            )
            self._emit(
                run_id=run_id,
                event_type=TaskEventType.TASK_FAILED.value,
                payload={
                    "coding_task_id": task.coding_task_id,
                    "attempt_count": attempt_index,
                    "error_code": ErrorCode.VALIDATION_FAILED.value,
                    "validation_result": validation_result.model_dump(),
                    "best_validation_result": (
                        best_validation_result.model_dump()
                        if best_validation_result is not None
                        else None
                    ),
                },
            )
            return CodingWorkerOutcome(
                status="failed",
                attempts=attempt_index,
                coding_result=coding_result,
                validation_result=validation_result,
                best_validation_result=best_validation_result,
                error_code=ErrorCode.VALIDATION_FAILED.value,
                error_message=validation_result.error_message
                or "validation failed",
            )

        coding_result = self._store_failure(
            run_id=run_id,
            task=task,
            attempt_index=max_attempts,
            summary="Validation attempts exhausted",
            error_code=ErrorCode.VALIDATION_FAILED.value,
            error_message="validation failed",
        )
        self._emit(
            run_id=run_id,
            event_type=TaskEventType.TASK_FAILED.value,
            payload={
                "coding_task_id": task.coding_task_id,
                "attempt_count": max_attempts,
                "error_code": ErrorCode.VALIDATION_FAILED.value,
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
            },
        )
        return CodingWorkerOutcome(
            status="failed",
            attempts=max_attempts,
            coding_result=coding_result,
            best_validation_result=best_validation_result,
            error_code=ErrorCode.VALIDATION_FAILED.value,
            error_message="validation failed",
        )


__all__ = [
    "AdapterResolver",
    "CodingAdapter",
    "CodingWorker",
    "CodingWorkerOutcome",
    "CodingWorkerStatus",
    "ValidationRunner",
    "resolve_max_validation_attempts",
]
