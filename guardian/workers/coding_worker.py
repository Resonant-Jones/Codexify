"""Worker for coding execution tasks via PiCodexRunnerAdapter."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from fnmatch import fnmatchcase
from typing import Any

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.base import AgentExecutionRequest
from guardian.agents.events import build_coding_result_lineage_payload
from guardian.agents.store import AgentStore, store
from guardian.agents.test_results import (
    NormalizedTestResult,
    normalize_subprocess_test_result,
    not_run_test_result,
)
from guardian.core import dependencies
from guardian.protocol_tokens import ErrorCode, TaskEventType
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

_ADAPTER_KIND_ALIASES = {
    "": "pi_codex_runner",
    "pi": "pi_codex_runner",
    "pi_sdk": "pi_codex_runner",
    "pi_codex_runner": "pi_codex_runner",
    "codex": "codex",
    "claudecode": "claudecode",
}

_VALIDATION_TIMEOUT_CAP_SECONDS = 120
_GIT_COMMAND_TIMEOUT_SECONDS = 5
_MUTATION_GUARD_PATH_LIMIT = 50


def _resolve_adapter_kind(raw_adapter_kind: Any) -> str:
    value = str(raw_adapter_kind or "").strip().lower()
    return _ADAPTER_KIND_ALIASES.get(value, value)


def _normalize_coding_result_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    return value or "error"


def _is_success_like_coding_result(status: str) -> bool:
    return (
        _normalize_coding_result_status(status)
        in _SUCCESS_LIKE_CODING_RESULT_STATUSES
    )


def _normalize_artifacts(raw_artifacts: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if raw_artifacts is None:
        return normalized
    if isinstance(raw_artifacts, dict):
        raw_artifacts = [raw_artifacts]
    for item in (
        raw_artifacts
        if isinstance(raw_artifacts, (list, tuple, set))
        else [raw_artifacts]
    ):
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
            str(item).strip() for item in raw_files_changed if str(item).strip()
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


def _coerce_permission_policy(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _run_git_command(
    *,
    repo_root: str,
    args: list[str],
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning(
            "[coding-worker] git inspection failed for %s: %s",
            repo_root,
            type(exc).__name__,
        )
        return None


def _git_repo_root(cwd: str | None) -> str | None:
    value = str(cwd or "").strip()
    if not value:
        return None
    completed = _run_git_command(
        repo_root=value,
        args=["rev-parse", "--show-toplevel"],
    )
    if completed is None or completed.returncode != 0:
        return None
    root = str(completed.stdout or "").strip()
    return root or None


def _parse_git_porcelain_entries(raw_output: str) -> list[str]:
    paths: list[str] = []
    entries = str(raw_output or "").split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        if not entry:
            index += 1
            continue
        if len(entry) < 4:
            index += 1
            continue
        status = entry[:2]
        path = entry[3:].strip()
        if status and status[0] in {"R", "C"}:
            if path:
                paths.append(path)
            if index + 1 < len(entries):
                new_path = entries[index + 1].strip()
                if new_path:
                    paths.append(new_path)
                index += 2
                continue
        if path:
            paths.append(path)
        index += 1
    deduped: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _run_git_porcelain_paths(repo_root: str) -> tuple[list[str], bool]:
    completed = _run_git_command(
        repo_root=repo_root,
        args=["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    if completed is None or completed.returncode != 0:
        return [], False
    return _parse_git_porcelain_entries(completed.stdout or ""), True


def _git_porcelain_paths(repo_root: str) -> list[str]:
    paths, _ok = _run_git_porcelain_paths(repo_root)
    return paths


def _changed_paths_since_preflight(
    repo_root: str,
    before: list[str],
    after: list[str],
) -> list[str]:
    del repo_root
    before_set = {str(path).strip() for path in before if str(path).strip()}
    changed: list[str] = []
    for path in after:
        normalized = str(path).strip()
        if (
            normalized
            and normalized not in before_set
            and normalized not in changed
        ):
            changed.append(normalized)
    return changed


def _path_allowed(path: str, allowed_paths: list[str]) -> bool:
    candidate = str(path or "").replace("\\", "/").strip()
    if not candidate:
        return False
    for raw_pattern in allowed_paths:
        pattern = str(raw_pattern or "").replace("\\", "/").strip()
        if not pattern:
            continue
        if os.path.isabs(pattern) or ".." in pattern.split("/"):
            continue
        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            if candidate == prefix or candidate.startswith(pattern):
                return True
            continue
        if candidate == pattern or fnmatchcase(candidate, pattern):
            return True
    return False


def _normalize_allowed_paths(raw_allowed_paths: Any) -> list[str]:
    if not isinstance(raw_allowed_paths, (list, tuple, set)):
        return []
    normalized: list[str] = []
    for item in raw_allowed_paths:
        pattern = str(item or "").replace("\\", "/").strip()
        if not pattern:
            continue
        if os.path.isabs(pattern) or ".." in pattern.split("/"):
            continue
        if pattern not in normalized:
            normalized.append(pattern)
    return normalized


def _bound_paths(
    paths: list[str],
    limit: int = _MUTATION_GUARD_PATH_LIMIT,
) -> tuple[list[str], int, bool]:
    bounded: list[str] = []
    for path in paths:
        normalized = str(path or "").replace("\\", "/").strip()
        if normalized and normalized not in bounded:
            bounded.append(normalized)
    total = len(bounded)
    truncated = total > limit
    return bounded[:limit], total, truncated


def _validation_timeout_seconds(task_timeout_seconds: int) -> int:
    return max(
        1, min(int(task_timeout_seconds or 0), _VALIDATION_TIMEOUT_CAP_SECONDS)
    )


def _build_validation_error_result(
    *,
    command: str,
    stdout: str = "",
    stderr: str = "",
    error_message: str,
    duration_seconds: float | None = None,
) -> NormalizedTestResult:
    return NormalizedTestResult(
        status="error",
        command=command,
        exit_code=None,
        tests_total=None,
        tests_passed=None,
        tests_failed=None,
        fail_signature=None,
        stdout_preview=stdout[:480],
        stderr_preview=stderr[:480],
        duration_seconds=duration_seconds,
        error_message=error_message,
    )


def _resolve_validation_command(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> str | None:
    command = task.validation_command or deployment_spec.get(
        "validation_command"
    )
    value = str(command or "").strip()
    return value or None


def _validation_permissions(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> dict[str, Any]:
    return _coerce_permission_policy(
        task.permission_policy
        or deployment_spec.get("permission_policy")
        or deployment_spec.get("permissionPolicy")
    )


def _resolve_max_validation_attempts(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> int:
    raw_candidates: tuple[Any, ...] = (
        task.max_validation_attempts,
        deployment_spec.get("max_validation_attempts"),
        os.getenv("CODING_WORKER_MAX_VALIDATION_ATTEMPTS"),
    )
    for raw in raw_candidates:
        value = _coerce_optional_positive_int(raw)
        if value is not None:
            return max(1, min(value, 10))
    return 3


def _validation_attempt_better(
    candidate: NormalizedTestResult,
    current_best: NormalizedTestResult | None,
) -> NormalizedTestResult:
    if current_best is None:
        return candidate
    if candidate.status == "passed" and current_best.status != "passed":
        return candidate
    if current_best.status == "passed":
        return current_best
    if (
        candidate.tests_failed is not None
        and current_best.tests_failed is not None
        and candidate.tests_failed < current_best.tests_failed
    ):
        return candidate
    return current_best


def _append_retry_feedback(prompt: str, feedback_blocks: list[str]) -> str:
    base = str(prompt or "").rstrip()
    feedback = "\n\n".join(block for block in feedback_blocks if block.strip())
    if not feedback:
        return base
    if not base:
        return feedback
    return f"{base}\n\n{feedback}"


def _run_validation_command(
    *,
    command: str,
    cwd: str,
    timeout_seconds: int,
) -> NormalizedTestResult:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return _build_validation_error_result(
            command=command,
            error_message=f"validation_command_parse_failed: {exc}",
        )
    if not argv:
        return _build_validation_error_result(
            command=command,
            error_message="validation_command_empty",
        )

    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        return _build_validation_error_result(
            command=command,
            error_message="validation_command_timeout",
            duration_seconds=elapsed,
        )
    except Exception as exc:
        elapsed = time.monotonic() - started
        return _build_validation_error_result(
            command=command,
            error_message=f"validation_command_error: {type(exc).__name__}",
            duration_seconds=elapsed,
        )

    elapsed = time.monotonic() - started
    return normalize_subprocess_test_result(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_seconds=elapsed,
    )


def _coerce_validation_result(
    validation_result: Any,
    *,
    validation_command: str,
    cwd: str,
) -> NormalizedTestResult:
    if isinstance(validation_result, NormalizedTestResult):
        return validation_result
    if isinstance(validation_result, subprocess.CompletedProcess):
        return normalize_subprocess_test_result(
            command=validation_command,
            exit_code=validation_result.returncode,
            stdout=validation_result.stdout or "",
            stderr=validation_result.stderr or "",
        )
    if hasattr(validation_result, "model_dump"):
        try:
            return NormalizedTestResult.model_validate(
                validation_result.model_dump()
            )
        except Exception:
            pass
    if isinstance(validation_result, dict):
        try:
            return NormalizedTestResult.model_validate(validation_result)
        except Exception:
            pass
    return not_run_test_result(
        reason="validation_result_unexpected",
        command=validation_command,
    )


def _validation_feedback_block(
    *,
    validation_command: str,
    validation_result: NormalizedTestResult,
) -> str:
    lines = [
        "Validation feedback:",
        f"- Failed for command: {validation_command}",
        f"- Status: {validation_result.status}",
    ]
    if validation_result.exit_code is not None:
        lines.append(f"- Exit code: {validation_result.exit_code}")
    if validation_result.fail_signature:
        lines.append(f"- Fail signature: {validation_result.fail_signature}")
    if validation_result.tests_failed is not None:
        lines.append(f"- Tests failed: {validation_result.tests_failed}")
    if validation_result.stdout_preview:
        lines.append(f"- Stdout: {validation_result.stdout_preview}")
    if validation_result.stderr_preview:
        lines.append(f"- Stderr: {validation_result.stderr_preview}")
    lines.append("- Fix only the original task scope.")
    return "\n".join(lines)


def _mutation_guard_metadata(
    *,
    enabled: bool,
    status: str,
    allowed_paths: list[str],
    changed_paths: list[str],
    disallowed_paths: list[str],
    error_code: str | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    bounded_allowed_paths, _allowed_total, _allowed_truncated = _bound_paths(
        allowed_paths
    )
    bounded_changed_paths, changed_total, changed_truncated = _bound_paths(
        changed_paths
    )
    (
        bounded_disallowed_paths,
        _disallowed_total,
        _disallowed_truncated,
    ) = _bound_paths(disallowed_paths)
    metadata: dict[str, Any] = {
        "mutation_guard_enabled": enabled,
        "mutation_guard_status": status,
        "allowed_paths": bounded_allowed_paths,
        "changed_paths": bounded_changed_paths,
        "disallowed_paths": bounded_disallowed_paths,
        "changed_paths_total": changed_total,
        "changed_paths_truncated": changed_truncated,
        "mutation_guard_error_code": error_code,
        "mutation_guard_warning": warning,
    }
    if _disallowed_truncated:
        metadata["disallowed_paths_truncated"] = True
    if _allowed_truncated:
        metadata["allowed_paths_truncated"] = True
    return metadata


def _git_mutation_guard_snapshot(
    *,
    cwd: str | None,
    allowed_paths: list[str],
) -> dict[str, Any]:
    repo_root = _git_repo_root(cwd)
    if repo_root is None:
        return {
            "enabled": bool(str(cwd or "").strip()),
            "repo_root": None,
            "verified": False,
            "before_paths": [],
            "before_ok": False,
            "allowed_paths": list(allowed_paths),
        }
    before_paths, before_ok = _run_git_porcelain_paths(repo_root)
    return {
        "enabled": True,
        "repo_root": repo_root,
        "verified": before_ok,
        "before_paths": before_paths,
        "before_ok": before_ok,
        "allowed_paths": list(allowed_paths),
    }


def _evaluate_mutation_guard(
    *,
    repo_root: str | None,
    before_paths: list[str],
    before_ok: bool,
    after_paths: list[str],
    after_ok: bool,
    allowed_paths: list[str],
    allow_write: bool,
) -> dict[str, Any]:
    if repo_root is None or not before_ok or not after_ok:
        return _mutation_guard_metadata(
            enabled=bool(repo_root),
            status="unverified",
            allowed_paths=allowed_paths,
            changed_paths=[],
            disallowed_paths=[],
            error_code=ErrorCode.MUTATION_SCOPE_UNVERIFIED.value,
            warning="mutation_scope_cannot_be_proven_without_git_porcelain",
        )

    changed_paths = _changed_paths_since_preflight(
        repo_root,
        before_paths,
        after_paths,
    )
    if not changed_paths:
        return _mutation_guard_metadata(
            enabled=True,
            status="clean",
            allowed_paths=allowed_paths,
            changed_paths=[],
            disallowed_paths=[],
        )

    disallowed_paths: list[str] = []
    if not allow_write:
        disallowed_paths = list(changed_paths)
    else:
        for path in changed_paths:
            if not _path_allowed(path, allowed_paths):
                disallowed_paths.append(path)

    if disallowed_paths:
        return _mutation_guard_metadata(
            enabled=True,
            status="mutation_scope_violation",
            allowed_paths=allowed_paths,
            changed_paths=changed_paths,
            disallowed_paths=disallowed_paths,
            error_code=ErrorCode.MUTATION_SCOPE_VIOLATION.value,
        )

    return _mutation_guard_metadata(
        enabled=True,
        status="within_allowed_paths",
        allowed_paths=allowed_paths,
        changed_paths=changed_paths,
        disallowed_paths=[],
    )


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
        adapter_kind = _resolve_adapter_kind(
            deployment_spec.get("adapter_kind")
        )
        validation_command = _resolve_validation_command(task, deployment_spec)
        permission_policy = _validation_permissions(task, deployment_spec)

        # Emit running event
        self._emit_running(task, adapter_kind=adapter_kind)

        # Get adapter
        adapter = ADAPTERS.get(adapter_kind)
        if not adapter:
            self._emit_failure(
                task,
                adapter_kind=adapter_kind,
                error_message=f"coding adapter not configured: {adapter_kind}",
                error_code="ADAPTER_NOT_FOUND",
            )
            return

        def _persist_and_emit_terminal(
            *,
            result: Any,
            result_status: str,
            summary: str,
            files_changed: list[str],
            artifacts: list[dict[str, Any]],
            adapter_session_ref: str | None,
            errors: list[str],
            error_code: str | None,
            error_message: str | None,
            validation_result: NormalizedTestResult | None = None,
        ) -> None:
            result_artifact_payload = list(artifacts)
            if validation_result is not None:
                result_artifact_payload = [
                    {
                        "validation_results": validation_result.model_dump(),
                        "validation_command": validation_command,
                        "validation_attempt_count": 1,
                    },
                    *result_artifact_payload,
                ]

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
                result_summary=summary,
                artifacts=result_artifact_payload,
                errors=errors,
                error_code=error_code,
                error_message=error_message,
            )

            if _is_success_like_coding_result(result_status) and not bool(
                delivery.get("delivery_ok", False)
            ):
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

            terminal_event = (
                "completed"
                if _is_success_like_coding_result(result_status)
                else "failed"
            )
            self._emit_terminal(
                task,
                event_type=terminal_event,
                result=result,
                adapter_kind=adapter_kind,
                result_status=result_status,
                summary=summary,
                files_changed=files_changed,
                artifacts=result_artifact_payload,
                adapter_session_ref=adapter_session_ref,
                delivery=delivery,
                errors=errors,
                error_code=error_code,
                error_message=error_message,
                validation_result=(
                    validation_result.model_dump()
                    if validation_result
                    else None
                ),
                validation_attempt_count=(
                    1 if validation_result is not None else None
                ),
            )

        if is_cancelled(task.task_id):
            self._emit_cancelled(task)
            return

        if validation_command:
            self._emit_attempt_started(
                task,
                adapter_kind=adapter_kind,
                validation_command=validation_command,
                validation_attempt_count=1,
            )

        request = AgentExecutionRequest(
            prompt=task.instructions,
            cwd=task.cwd,
            timeout_seconds=task.timeout_seconds,
            metadata={
                "coding_task_id": task.coding_task_id,
                "attempt_id": task.attempt_id,
                "attempt_index": 1,
            },
        )

        result = adapter.execute(request)
        result_status = _normalize_coding_result_status(
            getattr(result, "status", "")
        )
        success_like = _is_success_like_coding_result(result_status)
        result_artifacts = _normalize_artifacts(
            getattr(result, "artifacts", [])
        )
        files_changed = _normalize_files_changed(
            getattr(result, "files_changed", None),
            result_artifacts,
        )
        adapter_session_ref = getattr(result, "adapter_session_ref", None)
        error_code = getattr(result, "error_code", None)
        error_message = getattr(result, "error_message", None)
        if not error_message and not success_like:
            error_message = getattr(result, "summary", None)

        if not success_like:
            final_summary = getattr(result, "summary", "")
            final_errors = list(getattr(result, "errors", []) or [])
            _persist_and_emit_terminal(
                result=result,
                result_status=result_status,
                summary=final_summary,
                files_changed=files_changed,
                artifacts=result_artifacts,
                adapter_session_ref=adapter_session_ref,
                errors=final_errors,
                error_code=error_code,
                error_message=error_message
                or "coding adapter execution failed",
            )
            return

        final_summary = getattr(result, "summary", "")
        final_errors = list(getattr(result, "errors", []) or [])
        final_error_code = error_code
        final_error_message = error_message
        validation_result: NormalizedTestResult | None = None

        if validation_command:
            if not permission_policy.get("allow_shell"):
                validation_result = not_run_test_result(
                    reason="validation_shell_not_allowed",
                    command=validation_command,
                )
            elif not task.cwd:
                validation_result = not_run_test_result(
                    reason="validation_cwd_missing",
                    command=validation_command,
                )
            else:
                validation_result = _run_validation_command(
                    command=validation_command,
                    cwd=task.cwd,
                    timeout_seconds=_validation_timeout_seconds(
                        task.timeout_seconds
                    ),
                )
            validation_result = _coerce_validation_result(
                validation_result,
                validation_command=validation_command,
                cwd=task.cwd or "",
            )

            if validation_result.status in {"passed", "not_run"}:
                _persist_and_emit_terminal(
                    result=result,
                    result_status=result_status,
                    summary=final_summary,
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=final_errors,
                    error_code=final_error_code,
                    error_message=final_error_message,
                    validation_result=validation_result,
                )
                return

            final_summary = (
                f"{final_summary} | validation failed"
                if final_summary
                else "validation failed"
            )
            final_error_code = ErrorCode.VALIDATION_FAILED.value
            final_error_message = (
                validation_result.error_message or "validation failed"
            )
            final_errors = [*final_errors, "validation_failed"]
            validation_feedback = _validation_feedback_block(
                validation_command=validation_command,
                validation_result=validation_result,
            )
            self._emit_validation_failed(
                task,
                adapter_kind=adapter_kind,
                validation_result=validation_result,
                validation_feedback=validation_feedback,
            )
            _persist_and_emit_terminal(
                result=result,
                result_status="failed",
                summary=final_summary,
                files_changed=files_changed,
                artifacts=result_artifacts,
                adapter_session_ref=adapter_session_ref,
                errors=final_errors,
                error_code=final_error_code,
                error_message=final_error_message,
                validation_result=validation_result,
            )
            return

        _persist_and_emit_terminal(
            result=result,
            result_status=result_status,
            summary=final_summary,
            files_changed=files_changed,
            artifacts=result_artifacts,
            adapter_session_ref=adapter_session_ref,
            errors=final_errors,
            error_code=final_error_code,
            error_message=final_error_message,
        )
        return

    def _process_task(self, task: CodingExecutionTask) -> None:
        """Process a single coding execution task with bounded retries."""
        if is_cancelled(task.task_id):
            self._emit_cancelled(task)
            return

        deployment = self.store.get_deployment(task.deployment_id) or {}
        deployment_spec = dict(deployment.get("spec_json") or {})
        adapter_kind = _resolve_adapter_kind(
            deployment_spec.get("adapter_kind")
        )
        validation_command = _resolve_validation_command(task, deployment_spec)
        permission_policy = _validation_permissions(task, deployment_spec)
        allowed_paths = _normalize_allowed_paths(
            permission_policy.get("allowed_paths")
        )
        task_workdir = str(task.cwd or task.repo_root or "").strip() or None
        validation_attempt_budget = _resolve_max_validation_attempts(
            task, deployment_spec
        )
        if not validation_command:
            validation_attempt_budget = 1

        guard_snapshot = _git_mutation_guard_snapshot(
            cwd=task_workdir,
            allowed_paths=allowed_paths,
        )
        repo_root = guard_snapshot["repo_root"]
        before_paths = list(guard_snapshot["before_paths"])
        before_ok = bool(guard_snapshot["before_ok"])
        mutation_guard_enabled = bool(guard_snapshot["enabled"])
        validation_attempts: list[dict[str, Any]] = []
        best_validation_result: NormalizedTestResult | None = None

        def _guard_warning() -> str | None:
            if repo_root is None or not before_ok:
                return "mutation_scope_cannot_be_proven_without_git_porcelain"
            return None

        def _current_guard_metadata(
            *,
            status: str,
            changed_paths: list[str],
            disallowed_paths: list[str],
            error_code: str | None = None,
            warning: str | None = None,
        ) -> dict[str, Any]:
            return _mutation_guard_metadata(
                enabled=mutation_guard_enabled,
                status=status,
                allowed_paths=allowed_paths,
                changed_paths=changed_paths,
                disallowed_paths=disallowed_paths,
                error_code=error_code,
                warning=warning,
            )

        def _collect_after_guard() -> dict[str, Any]:
            if repo_root is None:
                return _current_guard_metadata(
                    status="unverified",
                    changed_paths=[],
                    disallowed_paths=[],
                    error_code=ErrorCode.MUTATION_SCOPE_UNVERIFIED.value,
                    warning=_guard_warning(),
                )
            after_paths, after_ok = _run_git_porcelain_paths(repo_root)
            return _evaluate_mutation_guard(
                repo_root=repo_root,
                before_paths=before_paths,
                before_ok=before_ok,
                after_paths=after_paths,
                after_ok=after_ok,
                allowed_paths=allowed_paths,
                allow_write=bool(permission_policy.get("allow_write")),
            )

        def _persist_and_emit_terminal(
            *,
            result: Any,
            result_status: str,
            summary: str,
            files_changed: list[str],
            artifacts: list[dict[str, Any]],
            adapter_session_ref: str | None,
            errors: list[str],
            error_code: str | None,
            error_message: str | None,
            validation_result: NormalizedTestResult | None = None,
            validation_attempt_count: int | None = None,
            validation_attempts: list[dict[str, Any]] | None = None,
            best_validation_result: NormalizedTestResult | None = None,
            mutation_guard: dict[str, Any] | None = None,
        ) -> None:
            terminal_artifacts = list(artifacts)
            if validation_result is not None:
                terminal_artifacts = [
                    {
                        "validation_results": validation_result.model_dump(),
                        "validation_attempt_count": validation_attempt_count,
                        "max_validation_attempts": validation_attempt_budget,
                        "validation_command": validation_command,
                        "best_validation_result": (
                            best_validation_result.model_dump()
                            if best_validation_result is not None
                            else None
                        ),
                        "validation_attempts": validation_attempts or [],
                    },
                    *terminal_artifacts,
                ]
            if mutation_guard is not None and validation_command:
                terminal_artifacts = [dict(mutation_guard), *terminal_artifacts]

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
                result_summary=summary,
                artifacts=terminal_artifacts,
                errors=errors,
                error_code=error_code,
                error_message=error_message,
            )

            if _is_success_like_coding_result(result_status) and not bool(
                delivery.get("delivery_ok", False)
            ):
                self._emit_failure(
                    task,
                    adapter_kind=adapter_kind,
                    error_message=str(
                        delivery.get("delivery_reason")
                        or "coding result delivery failed"
                    ),
                    error_code="RESULT_DELIVERY_FAILED",
                    mutation_guard=mutation_guard,
                )
                return

            terminal_event = (
                "completed"
                if _is_success_like_coding_result(result_status)
                else "failed"
            )
            self._emit_terminal(
                task,
                event_type=terminal_event,
                result=result,
                adapter_kind=adapter_kind,
                result_status=result_status,
                summary=summary,
                files_changed=files_changed,
                artifacts=terminal_artifacts,
                adapter_session_ref=adapter_session_ref,
                delivery=delivery,
                errors=errors,
                error_code=error_code,
                error_message=error_message,
                validation_result=(
                    validation_result.model_dump()
                    if validation_result is not None
                    else None
                ),
                validation_attempt_count=validation_attempt_count,
                validation_attempts=(
                    validation_attempts
                    if validation_attempts is not None
                    else None
                ),
                best_validation_result=(
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
                mutation_guard=mutation_guard,
            )

        self._emit_running(task, adapter_kind=adapter_kind)

        if repo_root is not None and before_ok and before_paths:
            guard = _current_guard_metadata(
                status="dirty_worktree_precheck_failed",
                changed_paths=before_paths,
                disallowed_paths=before_paths,
                error_code=ErrorCode.DIRTY_WORKTREE_PRECHECK_FAILED.value,
            )
            _persist_and_emit_terminal(
                result=None,
                result_status="failed",
                summary="dirty worktree precheck failed",
                files_changed=before_paths,
                artifacts=[],
                adapter_session_ref=None,
                errors=["dirty_worktree_precheck_failed"],
                error_code=ErrorCode.DIRTY_WORKTREE_PRECHECK_FAILED.value,
                error_message="dirty worktree precheck failed",
                mutation_guard=guard,
            )
            return

        adapter = ADAPTERS.get(adapter_kind)
        if not adapter:
            self._emit_failure(
                task,
                adapter_kind=adapter_kind,
                error_message=f"coding adapter not configured: {adapter_kind}",
                error_code="ADAPTER_NOT_FOUND",
                mutation_guard=_current_guard_metadata(
                    status="unverified"
                    if repo_root is None or not before_ok
                    else "clean",
                    changed_paths=[],
                    disallowed_paths=[],
                    error_code=(
                        ErrorCode.MUTATION_SCOPE_UNVERIFIED.value
                        if repo_root is None or not before_ok
                        else None
                    ),
                    warning=(
                        _guard_warning()
                        if repo_root is None or not before_ok
                        else None
                    ),
                ),
            )
            return

        validation_feedback_blocks: list[str] = []
        best_validation_result: NormalizedTestResult | None = None
        validation_attempts: list[dict[str, Any]] = []
        for attempt_index in range(1, validation_attempt_budget + 1):
            if is_cancelled(task.task_id):
                self._emit_cancelled(task)
                return

            attempt_prompt = (
                _append_retry_feedback(
                    task.instructions, validation_feedback_blocks
                )
                if validation_feedback_blocks
                else task.instructions
            )
            if validation_command:
                self._emit_attempt_started(
                    task,
                    adapter_kind=adapter_kind,
                    validation_command=validation_command,
                    validation_attempt_count=attempt_index,
                    max_validation_attempts=validation_attempt_budget,
                    mutation_guard=_current_guard_metadata(
                        status=(
                            "unverified"
                            if repo_root is None or not before_ok
                            else "clean"
                        ),
                        changed_paths=[],
                        disallowed_paths=[],
                        error_code=(
                            ErrorCode.MUTATION_SCOPE_UNVERIFIED.value
                            if repo_root is None or not before_ok
                            else None
                        ),
                        warning=(
                            _guard_warning()
                            if repo_root is None or not before_ok
                            else None
                        ),
                    ),
                )

            request = AgentExecutionRequest(
                prompt=attempt_prompt,
                cwd=task_workdir,
                timeout_seconds=task.timeout_seconds,
                metadata={
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
                    "attempt_index": attempt_index,
                    "max_validation_attempts": validation_attempt_budget,
                },
            )

            result = adapter.execute(request)
            result_status = _normalize_coding_result_status(
                getattr(result, "status", "")
            )
            success_like = _is_success_like_coding_result(result_status)
            result_artifacts = _normalize_artifacts(
                getattr(result, "artifacts", [])
            )
            files_changed = _normalize_files_changed(
                getattr(result, "files_changed", None),
                result_artifacts,
            )
            adapter_session_ref = getattr(result, "adapter_session_ref", None)
            error_code = getattr(result, "error_code", None)
            error_message = getattr(result, "error_message", None)
            if not error_message and not success_like:
                error_message = getattr(result, "summary", None)

            validation_result: NormalizedTestResult | None = None
            validation_attempt_count: int | None = None
            if success_like and validation_command:
                if not permission_policy.get("allow_shell"):
                    validation_result = not_run_test_result(
                        reason="validation_shell_not_allowed",
                        command=validation_command,
                    )
                elif not task_workdir:
                    validation_result = not_run_test_result(
                        reason="validation_cwd_missing",
                        command=validation_command,
                    )
                else:
                    validation_result = _run_validation_command(
                        command=validation_command,
                        cwd=task_workdir,
                        timeout_seconds=_validation_timeout_seconds(
                            task.timeout_seconds
                        ),
                    )
                validation_result = _coerce_validation_result(
                    validation_result,
                    validation_command=validation_command,
                    cwd=task_workdir or "",
                )
                validation_attempt_count = attempt_index
                validation_attempts.append(
                    {
                        "attempt_index": attempt_index,
                        "validation_result": validation_result.model_dump(),
                    }
                )
                best_validation_result = _validation_attempt_better(
                    validation_result,
                    best_validation_result,
                )

            mutation_guard = _collect_after_guard()

            if not success_like:
                final_errors = list(getattr(result, "errors", []) or [])
                final_error_code = error_code
                final_error_message = (
                    error_message or "coding adapter execution failed"
                )
                if (
                    mutation_guard.get("mutation_guard_status")
                    == "mutation_scope_violation"
                ):
                    final_errors.append("mutation_scope_violation")
                    final_error_code = mutation_guard.get(
                        "mutation_guard_error_code"
                    )
                    final_error_message = (
                        final_error_message or "mutation scope violated"
                    )
                elif (
                    mutation_guard.get("mutation_guard_status") == "unverified"
                ):
                    final_errors.append("mutation_scope_unverified")
                _persist_and_emit_terminal(
                    result=result,
                    result_status=result_status,
                    summary=getattr(result, "summary", ""),
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=final_errors,
                    error_code=final_error_code,
                    error_message=final_error_message,
                    mutation_guard=mutation_guard,
                )
                return

            if (
                mutation_guard.get("mutation_guard_status")
                == "mutation_scope_violation"
            ):
                final_errors = list(getattr(result, "errors", []) or [])
                final_errors.append("mutation_scope_violation")
                validation_failed_result = (
                    validation_result
                    if validation_result is not None
                    and validation_result.status not in {"passed", "not_run"}
                    else None
                )
                if validation_failed_result is not None:
                    validation_feedback = _validation_feedback_block(
                        validation_command=validation_command,
                        validation_result=validation_failed_result,
                    )
                    self._emit_validation_failed(
                        task,
                        adapter_kind=adapter_kind,
                        validation_result=validation_failed_result,
                        validation_feedback=validation_feedback,
                        validation_attempt_count=validation_attempt_count or 0,
                        max_validation_attempts=validation_attempt_budget,
                        best_validation_result=best_validation_result,
                        mutation_guard=mutation_guard,
                    )
                _persist_and_emit_terminal(
                    result=result,
                    result_status="failed",
                    summary=(
                        f"{getattr(result, 'summary', '')} | mutation scope violated"
                        if getattr(result, "summary", "")
                        else "mutation scope violated"
                    ),
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=final_errors,
                    error_code=mutation_guard.get("mutation_guard_error_code"),
                    error_message="mutation scope violated",
                    validation_result=validation_result,
                    validation_attempt_count=validation_attempt_count,
                    validation_attempts=list(validation_attempts),
                    best_validation_result=best_validation_result,
                    mutation_guard=mutation_guard,
                )
                return

            if validation_result is None or validation_result.status in {
                "passed",
                "not_run",
            }:
                _persist_and_emit_terminal(
                    result=result,
                    result_status=result_status,
                    summary=getattr(result, "summary", ""),
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=list(getattr(result, "errors", []) or []),
                    error_code=error_code,
                    error_message=error_message,
                    validation_result=validation_result,
                    validation_attempt_count=validation_attempt_count,
                    validation_attempts=list(validation_attempts),
                    best_validation_result=best_validation_result,
                    mutation_guard=mutation_guard,
                )
                return

            validation_feedback = _validation_feedback_block(
                validation_command=validation_command,
                validation_result=validation_result,
            )
            self._emit_validation_failed(
                task,
                adapter_kind=adapter_kind,
                validation_result=validation_result,
                validation_feedback=validation_feedback,
                validation_attempt_count=validation_attempt_count or 0,
                max_validation_attempts=validation_attempt_budget,
                best_validation_result=best_validation_result,
                mutation_guard=mutation_guard,
            )
            can_retry = (
                mutation_guard.get("mutation_guard_status")
                in {"clean", "within_allowed_paths"}
                and attempt_index < validation_attempt_budget
            )
            if can_retry:
                retry_feedback = (
                    f"Validation failed for {validation_command} "
                    f"on attempt {attempt_index}/{validation_attempt_budget}"
                )
                validation_feedback_blocks.append(validation_feedback)
                self._emit_retrying(
                    task,
                    adapter_kind=adapter_kind,
                    validation_result=validation_result,
                    validation_attempt_count=validation_attempt_count or 0,
                    next_validation_attempt_count=attempt_index + 1,
                    max_validation_attempts=validation_attempt_budget,
                    best_validation_result=best_validation_result,
                    retry_feedback=retry_feedback,
                    mutation_guard=mutation_guard,
                )
                continue

            final_errors = list(getattr(result, "errors", []) or [])
            final_errors.append("validation_failed")
            _persist_and_emit_terminal(
                result=result,
                result_status="failed",
                summary=(
                    f"{getattr(result, 'summary', '')} | validation failed"
                    if getattr(result, "summary", "")
                    else "validation failed"
                ),
                files_changed=files_changed,
                artifacts=result_artifacts,
                adapter_session_ref=adapter_session_ref,
                errors=final_errors,
                error_code=ErrorCode.VALIDATION_FAILED.value,
                error_message=validation_result.error_message
                or "validation failed",
                validation_result=validation_result,
                validation_attempt_count=validation_attempt_count,
                validation_attempts=list(validation_attempts),
                best_validation_result=best_validation_result,
                mutation_guard=mutation_guard,
            )
            return

        self._emit_failure(
            task,
            adapter_kind=adapter_kind,
            error_message="coding worker exhausted validation attempts",
            error_code="PROCESSING_ERROR",
            mutation_guard=_current_guard_metadata(
                status="unverified"
                if repo_root is None or not before_ok
                else "clean",
                changed_paths=[],
                disallowed_paths=[],
                error_code=(
                    ErrorCode.MUTATION_SCOPE_UNVERIFIED.value
                    if repo_root is None or not before_ok
                    else None
                ),
                warning=(
                    _guard_warning()
                    if repo_root is None or not before_ok
                    else None
                ),
            ),
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

    def _emit_attempt_started(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_command: str,
        validation_attempt_count: int,
        max_validation_attempts: int,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.attempt_started for a validation-bearing attempt."""
        try:
            payload = {
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
                "validation_attempt_count": validation_attempt_count,
                "max_validation_attempts": max_validation_attempts,
                "validation_command": validation_command,
            }
            if mutation_guard is not None:
                payload.update(mutation_guard)
            task_events.publish_with_visibility(
                task.run_id,
                TaskEventType.TASK_ATTEMPT_STARTED.value,
                payload,
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit attempt started event: %s",
                exc,
            )

    def _emit_validation_failed(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_result: NormalizedTestResult,
        validation_feedback: str,
        validation_attempt_count: int,
        max_validation_attempts: int,
        best_validation_result: NormalizedTestResult | None = None,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.validation_failed for a failed validation attempt."""
        try:
            payload = {
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
                "status": "validation_failed",
                "validation_result": validation_result.model_dump(),
                "validation_feedback": validation_feedback,
                "validation_attempt_count": validation_attempt_count,
                "max_validation_attempts": max_validation_attempts,
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
            }
            if mutation_guard is not None:
                payload.update(mutation_guard)
            task_events.publish_with_visibility(
                task.run_id,
                TaskEventType.TASK_VALIDATION_FAILED.value,
                payload,
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit validation failed event: %s",
                exc,
            )

    def _emit_retrying(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_result: NormalizedTestResult,
        validation_attempt_count: int,
        next_validation_attempt_count: int,
        max_validation_attempts: int,
        best_validation_result: NormalizedTestResult | None,
        retry_feedback: str,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.retrying with bounded retry feedback."""
        try:
            payload = {
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
                "status": "retrying",
                "validation_attempt_count": validation_attempt_count,
                "next_validation_attempt_count": next_validation_attempt_count,
                "max_validation_attempts": max_validation_attempts,
                "validation_result": validation_result.model_dump(),
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
                "retry_feedback": retry_feedback,
            }
            if mutation_guard is not None:
                payload.update(mutation_guard)
            task_events.publish_with_visibility(
                task.run_id,
                TaskEventType.TASK_RETRYING.value,
                payload,
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit retrying event: %s",
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
        summary: str,
        files_changed: list[str],
        artifacts: list[dict[str, Any]],
        adapter_session_ref: str | None,
        delivery: dict[str, Any],
        errors: list[str],
        error_code: str | None,
        error_message: str | None,
        validation_result: dict[str, Any] | None = None,
        validation_attempt_count: int | None = None,
        validation_attempts: list[dict[str, Any]] | None = None,
        best_validation_result: dict[str, Any] | None = None,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit terminal task event."""
        try:
            payload = {
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
                "summary": summary,
                "files_changed": files_changed,
                "artifacts": artifacts,
                "adapter_session_ref": adapter_session_ref,
                "message_id": delivery.get("message_id"),
                "delivery_ok": bool(delivery.get("delivery_ok", False)),
                "delivery_reason": delivery.get("delivery_reason"),
                "errors": errors,
                "error_code": error_code,
                "error_message": error_message,
                "validation_result": validation_result,
                "validation_attempt_count": validation_attempt_count,
                "validation_attempts": validation_attempts,
                "best_validation_result": best_validation_result,
            }
            if mutation_guard is not None:
                payload.update(mutation_guard)
            task_events.publish_with_visibility(
                task.run_id,
                f"task.{event_type}",
                payload,
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
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.failed event for unrecoverable errors."""
        self.store.update_run_status(
            run_id=task.run_id,
            status="failed",
            error=error_message,
        )
        try:
            payload = {
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
            }
            if mutation_guard is not None:
                payload.update(mutation_guard)
            task_events.publish_with_visibility(
                task.run_id,
                "task.failed",
                payload,
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
