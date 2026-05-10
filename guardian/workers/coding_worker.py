"""Worker for coding execution tasks via PiCodexRunnerAdapter."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.base import AgentExecutionRequest
from guardian.agents.commit_gate import (
    CommitGateError,
    CommitGateResult,
    commit_after_green,
)
from guardian.agents.events import build_coding_result_lineage_payload
from guardian.agents.store import AgentStore, store
from guardian.agents.test_results import (
    NormalizedTestResult,
    normalize_subprocess_test_result,
    not_run_test_result,
)
from guardian.agents.worktree_lease_store import (
    WorktreeLeaseNotFound,
    WorktreeLeaseStore,
    WorktreeLeaseStoreError,
)
from guardian.agents.worktree_leases import (
    is_active_lease_status,
    validate_lease_contract,
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
_VALIDATION_ATTEMPTS_DEFAULT = 1
_VALIDATION_ATTEMPTS_CAP = 3
_GIT_COMMAND_TIMEOUT_SECONDS = 5
_MUTATION_GUARD_PATH_LIMIT = 50
_DEFAULT_COMMIT_MESSAGE_PREFIX = "Guardian commit-after-green"


@dataclass(frozen=True)
class LeaseExecutionContext:
    lease_id: str
    branch_name: str
    worktree_path: str
    lease_required: bool


def _token_value(enum_cls: Any, name: str, fallback: str) -> str:
    token = getattr(enum_cls, name, None)
    return str(getattr(token, "value", token or fallback))


def _error_value(name: str, fallback: str | None = None) -> str:
    return _token_value(ErrorCode, name, fallback or name)


def _task_event_value(name: str, fallback: str) -> str:
    return _token_value(TaskEventType, name, fallback)


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _lease_metadata(lease_ctx: LeaseExecutionContext | None) -> dict[str, Any]:
    if lease_ctx is None:
        return {}
    return {
        "worktree_lease_id": lease_ctx.lease_id,
        "branch_name": lease_ctx.branch_name,
        "worktree_path": lease_ctx.worktree_path,
        "lease_required": lease_ctx.lease_required,
    }


def _merge_payload(
    payload: dict[str, Any],
    lease_ctx: LeaseExecutionContext | None = None,
    mutation_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(payload)
    merged.update(_lease_metadata(lease_ctx))
    if mutation_guard is not None:
        merged.update(mutation_guard)
    return merged


def _resolve_commit_after_validation(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> bool:
    return bool(
        task.commit_after_validation
        or deployment_spec.get("commit_after_validation")
        or deployment_spec.get("commitAfterValidation")
        or False
    )


def _resolve_commit_message(
    task: CodingExecutionTask,
    deployment_spec: dict[str, Any],
) -> str | None:
    return _coerce_optional_text(
        task.commit_message
        or deployment_spec.get("commit_message")
        or deployment_spec.get("commitMessage")
    )


def _resolve_human_review_requirement(
    task: CodingExecutionTask,
    deployment_spec: dict[str, Any],
) -> bool:
    if task.require_human_review_before_merge is not True:
        return bool(task.require_human_review_before_merge)
    if "require_human_review_before_merge" in deployment_spec:
        return bool(deployment_spec.get("require_human_review_before_merge"))
    if "requireHumanReviewBeforeMerge" in deployment_spec:
        return bool(deployment_spec.get("requireHumanReviewBeforeMerge"))
    return True


def _default_commit_message(task: CodingExecutionTask) -> str:
    task_id = _coerce_optional_text(task.coding_task_id) or "unknown-task"
    attempt_id = _coerce_optional_text(task.attempt_id) or "attempt"
    return f"{_DEFAULT_COMMIT_MESSAGE_PREFIX}: {task_id} ({attempt_id})"


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
        if not entry or len(entry) < 4:
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


def _resolve_validation_attempt_budget(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> int:
    raw_candidates: tuple[Any, ...] = (
        task.max_validation_attempts,
        deployment_spec.get("max_validation_attempts"),
        deployment_spec.get("maxValidationAttempts"),
        os.getenv("CODING_WORKER_MAX_VALIDATION_ATTEMPTS"),
    )
    for raw in raw_candidates:
        value = _coerce_optional_positive_int(raw)
        if value is not None:
            return max(
                _VALIDATION_ATTEMPTS_DEFAULT,
                min(value, _VALIDATION_ATTEMPTS_CAP),
            )
    return _VALIDATION_ATTEMPTS_DEFAULT


def _resolve_max_validation_attempts(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> int:
    return _resolve_validation_attempt_budget(task, deployment_spec)


def _validation_permissions(
    task: CodingExecutionTask, deployment_spec: dict[str, Any]
) -> dict[str, Any]:
    return _coerce_permission_policy(
        task.permission_policy
        or deployment_spec.get("permission_policy")
        or deployment_spec.get("permissionPolicy")
    )


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
    del cwd
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


def _build_validation_feedback(
    *,
    validation_command: str,
    validation_result: NormalizedTestResult,
    validation_attempt_count: int,
    max_validation_attempts: int,
    attempt_index: int,
) -> str:
    lines = [
        "Validation feedback:",
        f"- Attempt {validation_attempt_count}/{max_validation_attempts}",
        f"- Next adapter attempt: {attempt_index}",
        f"- Command: {validation_command}",
        f"- Status: {validation_result.status}",
    ]
    if validation_result.exit_code is not None:
        lines.append(f"- Exit code: {validation_result.exit_code}")
    if validation_result.fail_signature:
        lines.append(f"- Fail signature: {validation_result.fail_signature}")
    if validation_result.tests_failed is not None:
        lines.append(f"- Tests failed: {validation_result.tests_failed}")
    if validation_result.error_message:
        lines.append(f"- Error: {validation_result.error_message}")
    if validation_result.stdout_preview:
        lines.append(f"- Stdout: {validation_result.stdout_preview}")
    if validation_result.stderr_preview:
        lines.append(f"- Stderr: {validation_result.stderr_preview}")
    lines.append("- Repair the previous attempt and preserve unrelated files.")
    return "\n".join(lines)


def _validation_feedback_block(
    *,
    validation_command: str,
    validation_result: NormalizedTestResult,
    validation_attempt_count: int = 1,
    max_validation_attempts: int = 1,
    attempt_index: int = 1,
) -> str:
    return _build_validation_feedback(
        validation_command=validation_command,
        validation_result=validation_result,
        validation_attempt_count=validation_attempt_count,
        max_validation_attempts=max_validation_attempts,
        attempt_index=attempt_index,
    )


def _build_retry_prompt(
    original_prompt: str,
    test_result: NormalizedTestResult,
    attempt_number: int,
    *,
    validation_command: str,
    validation_attempt_count: int,
    max_validation_attempts: int,
) -> str:
    feedback = _build_validation_feedback(
        validation_command=validation_command,
        validation_result=test_result,
        validation_attempt_count=validation_attempt_count,
        max_validation_attempts=max_validation_attempts,
        attempt_index=attempt_number,
    )
    base = str(original_prompt or "").rstrip()
    if not base:
        return feedback
    return f"{base}\n\n{feedback}"


def _validation_stop_reason_for_result(
    *,
    validation_command: str | None,
    validation_result: NormalizedTestResult | None,
    validation_attempt_count: int,
    max_validation_attempts: int,
    previous_fail_signature: str | None = None,
) -> str | None:
    if validation_result is None:
        return "validation_not_configured" if validation_command else None
    if validation_result.status == "passed":
        return "validation_passed"
    if validation_result.status == "not_run":
        return validation_result.error_message or "validation_not_run"
    if validation_result.status == "error":
        return validation_result.error_message or "validation_error"
    if (
        previous_fail_signature
        and validation_result.fail_signature
        and validation_result.fail_signature == previous_fail_signature
    ):
        return "repeated_fail_signature"
    if validation_attempt_count >= max_validation_attempts:
        return "max_validation_attempts_reached"
    return "validation_retrying"


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
    bounded_allowed_paths, _allowed_total, allowed_truncated = _bound_paths(
        allowed_paths
    )
    bounded_changed_paths, changed_total, changed_truncated = _bound_paths(
        changed_paths
    )
    bounded_disallowed_paths, _disallowed_total, disallowed_truncated = (
        _bound_paths(disallowed_paths)
    )
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
    if disallowed_truncated:
        metadata["disallowed_paths_truncated"] = True
    if allowed_truncated:
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
            error_code=_error_value("MUTATION_SCOPE_UNVERIFIED"),
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
            error_code=_error_value("MUTATION_SCOPE_VIOLATION"),
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
        """Poll for and process one coding task. Returns True if processed."""
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

    def _make_lease_store(self) -> WorktreeLeaseStore:
        return WorktreeLeaseStore(db=getattr(self.store, "db", None))

    def _read_lease(
        self, lease_store: WorktreeLeaseStore, lease_id: str
    ) -> Any | None:
        if hasattr(lease_store, "get_lease"):
            return lease_store.get_lease(lease_id)
        if hasattr(lease_store, "get"):
            return lease_store.get(lease_id)
        raise WorktreeLeaseStoreError("worktree lease store has no get method")

    def _heartbeat_or_fail(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        lease_ctx: LeaseExecutionContext,
        lease_store: WorktreeLeaseStore,
        reason: str,
    ) -> bool:
        try:
            lease_store.heartbeat(lease_ctx.lease_id)
            return True
        except WorktreeLeaseStoreError as exc:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_HEARTBEAT_FAILED"),
                error_message=(
                    f"worktree lease heartbeat failed ({reason}): {exc}"
                ),
                lease_id=lease_ctx.lease_id,
                lease_required=lease_ctx.lease_required,
                branch_name=lease_ctx.branch_name,
                worktree_path=lease_ctx.worktree_path,
            )
            return False

    def _emit_lease_failure(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        error_code: str,
        error_message: str,
        lease_id: str | None = None,
        lease_required: bool = False,
        branch_name: str | None = None,
        worktree_path: str | None = None,
    ) -> None:
        artifacts = [
            {
                "stop_reason": "worktree_lease_preflight_failed",
                "worktree_lease_id": lease_id,
                "branch_name": branch_name,
                "worktree_path": worktree_path,
                "lease_required": lease_required,
            }
        ]
        self.store.store_coding_result(
            run_id=task.run_id,
            coding_task_id=task.coding_task_id,
            attempt_id=task.attempt_id,
            request_id=task.request_id or None,
            thread_id=task.thread_id,
            source_message_id=_coerce_optional_positive_int(
                task.source_message_id
            ),
            result_status="failed",
            result_summary=error_message,
            adapter_kind=adapter_kind,
            files_changed=[],
            artifacts=artifacts,
            errors=[error_code],
            error_code=error_code,
            error_message=error_message,
            worktree_lease_id=lease_id,
            lease_required=lease_required,
            lease_branch_name=branch_name,
            lease_worktree_path=worktree_path,
        )
        self._emit_failure(
            task,
            adapter_kind=adapter_kind,
            error_message=error_message,
            error_code=error_code,
            result_captured_by_guardian=True,
            lease_id=lease_id,
            branch_name=branch_name,
            worktree_path=worktree_path,
            lease_required=lease_required,
        )

    def _resolve_lease_context(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        deployment_spec: dict[str, Any],
        commit_after_validation: bool,
    ) -> tuple[LeaseExecutionContext | None, WorktreeLeaseStore | None, str | None, bool]:
        task_workdir = str(task.cwd or task.repo_root or "").strip() or None
        lease_required = bool(
            task.require_worktree_lease
            or deployment_spec.get("require_worktree_lease", False)
            or deployment_spec.get("requireWorktreeLease", False)
        )
        lease_id = _coerce_optional_text(
            task.worktree_lease_id
            or deployment_spec.get("worktree_lease_id")
            or deployment_spec.get("worktreeLeaseId")
        )

        if commit_after_validation and lease_id is None:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("GIT_WORKTREE_REQUIRED"),
                error_message=(
                    "commit_after_validation requires an active worktree lease"
                ),
                lease_id=None,
                lease_required=True,
            )
            return None, None, task_workdir, False

        if not lease_required and lease_id is None:
            return None, None, task_workdir, True

        if not lease_id:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_REQUIRED"),
                error_message="worktree lease is required but missing",
                lease_id=None,
                lease_required=lease_required,
            )
            return None, None, task_workdir, False

        lease_store = self._make_lease_store()
        try:
            lease = self._read_lease(lease_store, lease_id)
        except WorktreeLeaseNotFound:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_NOT_FOUND"),
                error_message=f"unknown worktree_lease_id: {lease_id}",
                lease_id=lease_id,
                lease_required=lease_required,
            )
            return None, None, task_workdir, False
        except WorktreeLeaseStoreError as exc:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_INVALID"),
                error_message=f"failed to resolve worktree lease: {exc}",
                lease_id=lease_id,
                lease_required=lease_required,
            )
            return None, None, task_workdir, False

        if lease is None:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_NOT_FOUND"),
                error_message=f"unknown worktree_lease_id: {lease_id}",
                lease_id=lease_id,
                lease_required=lease_required,
            )
            return None, None, task_workdir, False

        lease_validation = validate_lease_contract(lease)
        if not lease_validation.ok:
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_INVALID"),
                error_message=(
                    lease_validation.reason
                    or "worktree lease contract validation failed"
                ),
                lease_id=lease.lease_id,
                lease_required=lease_required,
                branch_name=lease.branch_name,
                worktree_path=lease.worktree_path,
            )
            return None, None, task_workdir, False

        if not is_active_lease_status(lease.status):
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_NOT_ACTIVE"),
                error_message=f"worktree lease is not active: {lease.status}",
                lease_id=lease.lease_id,
                lease_required=lease_required,
                branch_name=lease.branch_name,
                worktree_path=lease.worktree_path,
            )
            return None, None, task_workdir, False

        if not os.path.exists(lease.worktree_path):
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_PATH_UNAVAILABLE"),
                error_message=(
                    f"worktree lease path does not exist: {lease.worktree_path}"
                ),
                lease_id=lease.lease_id,
                lease_required=lease_required,
                branch_name=lease.branch_name,
                worktree_path=lease.worktree_path,
            )
            return None, None, task_workdir, False

        if not os.path.isdir(lease.worktree_path):
            self._emit_lease_failure(
                task,
                adapter_kind=adapter_kind,
                error_code=_error_value("WORKTREE_LEASE_PATH_UNAVAILABLE"),
                error_message=(
                    f"worktree lease path is not a directory: {lease.worktree_path}"
                ),
                lease_id=lease.lease_id,
                lease_required=lease_required,
                branch_name=lease.branch_name,
                worktree_path=lease.worktree_path,
            )
            return None, None, task_workdir, False

        lease_ctx = LeaseExecutionContext(
            lease_id=lease.lease_id,
            branch_name=lease.branch_name,
            worktree_path=lease.worktree_path,
            lease_required=lease_required,
        )
        if not self._heartbeat_or_fail(
            task,
            adapter_kind=adapter_kind,
            lease_ctx=lease_ctx,
            lease_store=lease_store,
            reason="pre_execution",
        ):
            return None, None, task_workdir, False
        return lease_ctx, lease_store, lease.worktree_path, True

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
        validation_attempt_budget = _resolve_validation_attempt_budget(
            task, deployment_spec
        )
        if not validation_command:
            validation_attempt_budget = 1
        commit_after_validation = _resolve_commit_after_validation(
            task, deployment_spec
        )
        commit_message_override = _resolve_commit_message(task, deployment_spec)
        require_human_review_before_merge = _resolve_human_review_requirement(
            task, deployment_spec
        )

        lease_ctx, lease_store, effective_cwd, lease_ok = (
            self._resolve_lease_context(
                task,
                adapter_kind=adapter_kind,
                deployment_spec=deployment_spec,
                commit_after_validation=commit_after_validation,
            )
        )
        if not lease_ok:
            return

        self._emit_running(task, adapter_kind=adapter_kind, lease_ctx=lease_ctx)

        guard_snapshot = _git_mutation_guard_snapshot(
            cwd=effective_cwd,
            allowed_paths=allowed_paths,
        )
        repo_root = guard_snapshot["repo_root"]
        before_paths = list(guard_snapshot["before_paths"])
        before_ok = bool(guard_snapshot["before_ok"])
        mutation_guard_enabled = bool(guard_snapshot["enabled"])

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
                    error_code=_error_value("MUTATION_SCOPE_UNVERIFIED"),
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

        validation_attempts: list[dict[str, Any]] = []
        best_validation_result: NormalizedTestResult | None = None
        previous_fail_signature: str | None = None

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
            validation_stop_reason: str | None = None,
            final_validation_status: str | None = None,
            final_fail_signature: str | None = None,
            validation_attempts_payload: list[dict[str, Any]] | None = None,
            max_validation_attempts: int | None = None,
            commit_after_validation: bool = False,
            commit_hash: str | None = None,
            commit_status: str | None = None,
            commit_reason_code: str | None = None,
            merge_ready: bool = False,
            human_review_required: bool = True,
            require_human_review_before_merge: bool = True,
            mutation_guard: dict[str, Any] | None = None,
        ) -> None:
            result_artifact_payload = list(artifacts)
            if validation_result is not None:
                result_artifact_payload = [
                    {
                        "validation_results": validation_result.model_dump(),
                        "validation_attempt_count": validation_attempt_count,
                        "validation_stop_reason": validation_stop_reason,
                        "final_validation_status": final_validation_status,
                        "final_fail_signature": final_fail_signature,
                        "max_validation_attempts": max_validation_attempts,
                        "validation_command": validation_command,
                        "best_validation_result": (
                            best_validation_result.model_dump()
                            if best_validation_result is not None
                            else None
                        ),
                        "validation_attempts": list(
                            validation_attempts_payload or []
                        ),
                        "commit_after_validation": commit_after_validation,
                        "commit_hash": commit_hash,
                        "commit_status": commit_status,
                        "commit_reason_code": commit_reason_code,
                        "merge_ready": merge_ready,
                        "human_review_required": human_review_required,
                        "require_human_review_before_merge": (
                            require_human_review_before_merge
                        ),
                    },
                    *result_artifact_payload,
                ]
            elif commit_after_validation:
                result_artifact_payload = [
                    {
                        "commit_after_validation": commit_after_validation,
                        "commit_hash": commit_hash,
                        "commit_status": commit_status,
                        "commit_reason_code": commit_reason_code,
                        "merge_ready": merge_ready,
                        "human_review_required": human_review_required,
                        "require_human_review_before_merge": (
                            require_human_review_before_merge
                        ),
                    },
                    *result_artifact_payload,
                ]
            if mutation_guard is not None:
                result_artifact_payload = [
                    dict(mutation_guard),
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
                worktree_lease_id=(lease_ctx.lease_id if lease_ctx else None),
                lease_required=(lease_ctx.lease_required if lease_ctx else False),
                lease_branch_name=(lease_ctx.branch_name if lease_ctx else None),
                lease_worktree_path=(
                    lease_ctx.worktree_path if lease_ctx else None
                ),
                commit_after_validation=commit_after_validation,
                commit_hash=commit_hash,
                commit_status=commit_status,
                commit_reason_code=commit_reason_code,
                merge_ready=merge_ready,
                human_review_required=human_review_required,
                require_human_review_before_merge=(
                    require_human_review_before_merge
                ),
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
                    lease_ctx=lease_ctx,
                    result_captured_by_guardian=True,
                    mutation_guard=mutation_guard,
                )
                return

            terminal_event = (
                "completed"
                if _is_success_like_coding_result(result_status)
                else "failed"
            )
            validation_dump = (
                validation_result.model_dump()
                if validation_result is not None
                else None
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
                validation_results=validation_dump,
                validation_attempt_count=validation_attempt_count,
                validation_attempts=validation_attempts_payload,
                validation_stop_reason=validation_stop_reason,
                final_validation_status=final_validation_status,
                final_fail_signature=final_fail_signature,
                best_validation_result=(
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
                max_validation_attempts=max_validation_attempts,
                lease_ctx=lease_ctx,
                commit_after_validation=commit_after_validation,
                commit_hash=commit_hash,
                commit_status=commit_status,
                commit_reason_code=commit_reason_code,
                merge_ready=merge_ready,
                human_review_required=human_review_required,
                require_human_review_before_merge=(
                    require_human_review_before_merge
                ),
                mutation_guard=mutation_guard,
            )

        if repo_root is not None and before_ok and before_paths:
            guard = _current_guard_metadata(
                status="dirty_worktree_precheck_failed",
                changed_paths=before_paths,
                disallowed_paths=before_paths,
                error_code=_error_value("DIRTY_WORKTREE_PRECHECK_FAILED"),
            )
            _persist_and_emit_terminal(
                result=None,
                result_status="failed",
                summary="dirty worktree precheck failed",
                files_changed=before_paths,
                artifacts=[],
                adapter_session_ref=None,
                errors=["dirty_worktree_precheck_failed"],
                error_code=_error_value("DIRTY_WORKTREE_PRECHECK_FAILED"),
                error_message="dirty worktree precheck failed",
                commit_after_validation=commit_after_validation,
                commit_status=(
                    "skipped" if commit_after_validation else "not_requested"
                ),
                commit_reason_code=(
                    "DIRTY_WORKTREE_PRECHECK_FAILED"
                    if commit_after_validation
                    else None
                ),
                merge_ready=False,
                human_review_required=True,
                require_human_review_before_merge=(
                    require_human_review_before_merge
                ),
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
                lease_ctx=lease_ctx,
                mutation_guard=_current_guard_metadata(
                    status=(
                        "unverified"
                        if repo_root is None or not before_ok
                        else "clean"
                    ),
                    changed_paths=[],
                    disallowed_paths=[],
                    error_code=(
                        _error_value("MUTATION_SCOPE_UNVERIFIED")
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

        for attempt_index in range(1, validation_attempt_budget + 1):
            if is_cancelled(task.task_id):
                self._emit_cancelled(task)
                return

            if validation_command:
                self._emit_attempt_started(
                    task,
                    adapter_kind=adapter_kind,
                    validation_command=validation_command,
                    validation_attempt_count=attempt_index,
                    max_validation_attempts=validation_attempt_budget,
                    lease_ctx=lease_ctx,
                    mutation_guard=_current_guard_metadata(
                        status=(
                            "unverified"
                            if repo_root is None or not before_ok
                            else "clean"
                        ),
                        changed_paths=[],
                        disallowed_paths=[],
                        error_code=(
                            _error_value("MUTATION_SCOPE_UNVERIFIED")
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

            attempt_prompt = task.instructions
            if previous_fail_signature and validation_attempts:
                last_result = NormalizedTestResult.model_validate(
                    validation_attempts[-1]["validation_result"]
                )
                attempt_prompt = _build_retry_prompt(
                    task.instructions,
                    last_result,
                    attempt_index,
                    validation_command=validation_command or "",
                    validation_attempt_count=attempt_index - 1,
                    max_validation_attempts=validation_attempt_budget,
                )

            if lease_ctx is not None and lease_store is not None:
                if not self._heartbeat_or_fail(
                    task,
                    adapter_kind=adapter_kind,
                    lease_ctx=lease_ctx,
                    lease_store=lease_store,
                    reason="before_adapter",
                ):
                    return

            request = AgentExecutionRequest(
                prompt=attempt_prompt,
                cwd=effective_cwd,
                timeout_seconds=task.timeout_seconds,
                metadata={
                    "coding_task_id": task.coding_task_id,
                    "attempt_id": task.attempt_id,
                    "attempt_index": attempt_index,
                    "max_validation_attempts": validation_attempt_budget,
                    **_lease_metadata(lease_ctx),
                },
            )

            result = adapter.execute(request)

            if lease_ctx is not None and lease_store is not None:
                if not self._heartbeat_or_fail(
                    task,
                    adapter_kind=adapter_kind,
                    lease_ctx=lease_ctx,
                    lease_store=lease_store,
                    reason="after_adapter",
                ):
                    return

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

            final_summary = getattr(result, "summary", "")
            final_errors = list(getattr(result, "errors", []) or [])
            final_error_code = error_code
            final_error_message = error_message
            final_commit_hash: str | None = None
            final_commit_status: str | None = (
                "skipped" if commit_after_validation else "not_requested"
            )
            final_commit_reason_code: str | None = (
                "VALIDATION_NOT_CONFIGURED" if commit_after_validation else None
            )
            final_merge_ready = False
            final_human_review_required = require_human_review_before_merge
            final_validation_result: NormalizedTestResult | None = None
            final_validation_status: str | None = None
            final_fail_signature: str | None = None
            validation_stop_reason: str | None = None
            validation_attempt_count: int | None = None

            if not success_like:
                mutation_guard = _collect_after_guard()
                if (
                    mutation_guard.get("mutation_guard_status")
                    == "mutation_scope_violation"
                ):
                    final_errors = [*final_errors, "mutation_scope_violation"]
                    final_error_code = mutation_guard.get(
                        "mutation_guard_error_code"
                    )
                    final_error_message = "mutation scope violated"
                elif (
                    mutation_guard.get("mutation_guard_status") == "unverified"
                ):
                    final_errors = [*final_errors, "mutation_scope_unverified"]
                _persist_and_emit_terminal(
                    result=result,
                    result_status=result_status,
                    summary=final_summary,
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=final_errors,
                    error_code=final_error_code,
                    error_message=(
                        final_error_message or "coding adapter execution failed"
                    ),
                    commit_after_validation=commit_after_validation,
                    commit_status=final_commit_status,
                    commit_reason_code=final_commit_reason_code,
                    merge_ready=False,
                    human_review_required=True,
                    require_human_review_before_merge=(
                        require_human_review_before_merge
                    ),
                    mutation_guard=mutation_guard,
                )
                return

            if validation_command:
                if not permission_policy.get("allow_shell"):
                    final_validation_result = not_run_test_result(
                        reason="validation_shell_not_allowed",
                        command=validation_command,
                    )
                elif not effective_cwd:
                    final_validation_result = not_run_test_result(
                        reason="validation_cwd_missing",
                        command=validation_command,
                    )
                else:
                    if lease_ctx is not None and lease_store is not None:
                        if not self._heartbeat_or_fail(
                            task,
                            adapter_kind=adapter_kind,
                            lease_ctx=lease_ctx,
                            lease_store=lease_store,
                            reason="before_validation",
                        ):
                            return
                    self._emit_validation_started(
                        task,
                        adapter_kind=adapter_kind,
                        validation_command=validation_command,
                        validation_attempt_count=attempt_index,
                        max_validation_attempts=validation_attempt_budget,
                        lease_ctx=lease_ctx,
                    )
                    try:
                        raw_validation_result = _run_validation_command(
                            command=validation_command,
                            cwd=effective_cwd,
                            timeout_seconds=_validation_timeout_seconds(
                                task.timeout_seconds
                            ),
                        )
                    except Exception as exc:
                        raw_validation_result = _build_validation_error_result(
                            command=validation_command,
                            error_message=(
                                f"validation_command_error: {type(exc).__name__}"
                            ),
                        )
                    final_validation_result = _coerce_validation_result(
                        raw_validation_result,
                        validation_command=validation_command,
                        cwd=effective_cwd,
                    )
                    if lease_ctx is not None and lease_store is not None:
                        if not self._heartbeat_or_fail(
                            task,
                            adapter_kind=adapter_kind,
                            lease_ctx=lease_ctx,
                            lease_store=lease_store,
                            reason="after_validation",
                        ):
                            return

                validation_attempt_count = attempt_index
                validation_attempts.append(
                    {
                        "attempt_index": attempt_index,
                        "validation_result": final_validation_result.model_dump(),
                    }
                )
                best_validation_result = _validation_attempt_better(
                    final_validation_result,
                    best_validation_result,
                )
                final_validation_status = final_validation_result.status
                final_fail_signature = final_validation_result.fail_signature
                validation_stop_reason = _validation_stop_reason_for_result(
                    validation_command=validation_command,
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count,
                    max_validation_attempts=validation_attempt_budget,
                    previous_fail_signature=previous_fail_signature,
                )

            mutation_guard = _collect_after_guard()

            if (
                mutation_guard.get("mutation_guard_status")
                == "mutation_scope_violation"
            ):
                _persist_and_emit_terminal(
                    result=result,
                    result_status="failed",
                    summary=(
                        f"{final_summary} | mutation scope violated"
                        if final_summary
                        else "mutation scope violated"
                    ),
                    files_changed=files_changed,
                    artifacts=result_artifacts,
                    adapter_session_ref=adapter_session_ref,
                    errors=[*final_errors, "mutation_scope_violation"],
                    error_code=mutation_guard.get("mutation_guard_error_code"),
                    error_message="mutation scope violated",
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count,
                    validation_stop_reason=validation_stop_reason,
                    final_validation_status=final_validation_status,
                    final_fail_signature=final_fail_signature,
                    validation_attempts_payload=list(validation_attempts),
                    max_validation_attempts=validation_attempt_budget,
                    commit_after_validation=commit_after_validation,
                    commit_status=(
                        "skipped" if commit_after_validation else "not_requested"
                    ),
                    commit_reason_code=(
                        _error_value("MUTATION_SCOPE_VIOLATION")
                        if commit_after_validation
                        else None
                    ),
                    merge_ready=False,
                    human_review_required=True,
                    require_human_review_before_merge=(
                        require_human_review_before_merge
                    ),
                    mutation_guard=mutation_guard,
                )
                return

            if final_validation_result is None:
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
                    commit_after_validation=commit_after_validation,
                    commit_status=final_commit_status,
                    commit_reason_code=final_commit_reason_code,
                    merge_ready=False,
                    human_review_required=final_human_review_required,
                    require_human_review_before_merge=(
                        require_human_review_before_merge
                    ),
                    mutation_guard=mutation_guard if validation_command else None,
                )
                return

            if final_validation_result.status == "passed":
                self._emit_validation_passed(
                    task,
                    adapter_kind=adapter_kind,
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count or 0,
                    max_validation_attempts=validation_attempt_budget,
                    lease_ctx=lease_ctx,
                )
                if commit_after_validation:
                    if lease_ctx is None:
                        _persist_and_emit_terminal(
                            result=result,
                            result_status="failed",
                            summary=(
                                f"{final_summary} | commit-after-validation requires a lease-bound run"
                                if final_summary
                                else "commit-after-validation requires a lease-bound run"
                            ),
                            files_changed=files_changed,
                            artifacts=result_artifacts,
                            adapter_session_ref=adapter_session_ref,
                            errors=[
                                *final_errors,
                                _error_value("GIT_WORKTREE_REQUIRED"),
                            ],
                            error_code=_error_value("GIT_WORKTREE_REQUIRED"),
                            error_message=(
                                "commit_after_validation requires an active worktree lease"
                            ),
                            validation_result=final_validation_result,
                            validation_attempt_count=validation_attempt_count,
                            validation_stop_reason=validation_stop_reason,
                            final_validation_status=final_validation_status,
                            final_fail_signature=final_fail_signature,
                            validation_attempts_payload=list(validation_attempts),
                            max_validation_attempts=validation_attempt_budget,
                            commit_after_validation=True,
                            commit_hash=None,
                            commit_status="failed",
                            commit_reason_code=_error_value("GIT_WORKTREE_REQUIRED"),
                            merge_ready=False,
                            human_review_required=True,
                            require_human_review_before_merge=(
                                require_human_review_before_merge
                            ),
                            mutation_guard=mutation_guard,
                        )
                        return

                    if lease_store is not None:
                        if not self._heartbeat_or_fail(
                            task,
                            adapter_kind=adapter_kind,
                            lease_ctx=lease_ctx,
                            lease_store=lease_store,
                            reason="before_commit",
                        ):
                            return
                    resolved_commit_message = (
                        commit_message_override or _default_commit_message(task)
                    )
                    try:
                        commit_gate_result = commit_after_green(
                            lease_ctx.worktree_path,
                            resolved_commit_message,
                            lease_ctx.branch_name,
                        )
                    except CommitGateError as exc:
                        _persist_and_emit_terminal(
                            result=result,
                            result_status="failed",
                            summary=(
                                f"{final_summary} | commit gate execution failed"
                                if final_summary
                                else "commit gate execution failed"
                            ),
                            files_changed=files_changed,
                            artifacts=result_artifacts,
                            adapter_session_ref=adapter_session_ref,
                            errors=[
                                *final_errors,
                                _error_value("GIT_COMMIT_FAILED"),
                            ],
                            error_code=_error_value("GIT_COMMIT_FAILED"),
                            error_message=str(exc),
                            validation_result=final_validation_result,
                            validation_attempt_count=validation_attempt_count,
                            validation_stop_reason=validation_stop_reason,
                            final_validation_status=final_validation_status,
                            final_fail_signature=final_fail_signature,
                            validation_attempts_payload=list(validation_attempts),
                            max_validation_attempts=validation_attempt_budget,
                            commit_after_validation=True,
                            commit_hash=None,
                            commit_status="failed",
                            commit_reason_code=_error_value("GIT_COMMIT_FAILED"),
                            merge_ready=False,
                            human_review_required=True,
                            require_human_review_before_merge=(
                                require_human_review_before_merge
                            ),
                            mutation_guard=mutation_guard,
                        )
                        return
                    except Exception as exc:
                        _persist_and_emit_terminal(
                            result=result,
                            result_status="failed",
                            summary=(
                                f"{final_summary} | commit gate execution failed"
                                if final_summary
                                else "commit gate execution failed"
                            ),
                            files_changed=files_changed,
                            artifacts=result_artifacts,
                            adapter_session_ref=adapter_session_ref,
                            errors=[
                                *final_errors,
                                _error_value("GIT_COMMIT_FAILED"),
                            ],
                            error_code=_error_value("GIT_COMMIT_FAILED"),
                            error_message=str(exc),
                            validation_result=final_validation_result,
                            validation_attempt_count=validation_attempt_count,
                            validation_stop_reason=validation_stop_reason,
                            final_validation_status=final_validation_status,
                            final_fail_signature=final_fail_signature,
                            validation_attempts_payload=list(validation_attempts),
                            max_validation_attempts=validation_attempt_budget,
                            commit_after_validation=True,
                            commit_hash=None,
                            commit_status="failed",
                            commit_reason_code=_error_value("GIT_COMMIT_FAILED"),
                            merge_ready=False,
                            human_review_required=True,
                            require_human_review_before_merge=(
                                require_human_review_before_merge
                            ),
                            mutation_guard=mutation_guard,
                        )
                        return

                    final_commit_hash = commit_gate_result.commit_hash
                    final_commit_status = commit_gate_result.status
                    final_commit_reason_code = commit_gate_result.reason_code
                    if commit_gate_result.files_changed:
                        files_changed = list(commit_gate_result.files_changed)
                    if commit_gate_result.committed:
                        final_merge_ready = True
                        final_human_review_required = (
                            require_human_review_before_merge
                        )
                    elif (
                        commit_gate_result.reason_code
                        == _error_value("GIT_NO_CHANGES_TO_COMMIT")
                    ):
                        final_merge_ready = False
                        final_human_review_required = True
                    else:
                        _persist_and_emit_terminal(
                            result=result,
                            result_status="failed",
                            summary=(
                                f"{final_summary} | commit gate failed"
                                if final_summary
                                else "commit gate failed"
                            ),
                            files_changed=files_changed,
                            artifacts=result_artifacts,
                            adapter_session_ref=adapter_session_ref,
                            errors=[
                                *final_errors,
                                final_commit_reason_code
                                or _error_value("GIT_COMMIT_FAILED"),
                            ],
                            error_code=(
                                final_commit_reason_code
                                or _error_value("GIT_COMMIT_FAILED")
                            ),
                            error_message=(
                                commit_gate_result.message
                                or "commit gate failed"
                            ),
                            validation_result=final_validation_result,
                            validation_attempt_count=validation_attempt_count,
                            validation_stop_reason=validation_stop_reason,
                            final_validation_status=final_validation_status,
                            final_fail_signature=final_fail_signature,
                            validation_attempts_payload=list(validation_attempts),
                            max_validation_attempts=validation_attempt_budget,
                            commit_after_validation=True,
                            commit_hash=final_commit_hash,
                            commit_status=final_commit_status,
                            commit_reason_code=final_commit_reason_code,
                            merge_ready=False,
                            human_review_required=True,
                            require_human_review_before_merge=(
                                require_human_review_before_merge
                            ),
                            mutation_guard=mutation_guard,
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
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count,
                    validation_stop_reason=validation_stop_reason,
                    final_validation_status=final_validation_status,
                    final_fail_signature=final_fail_signature,
                    validation_attempts_payload=list(validation_attempts),
                    max_validation_attempts=validation_attempt_budget,
                    commit_after_validation=commit_after_validation,
                    commit_hash=final_commit_hash,
                    commit_status=final_commit_status,
                    commit_reason_code=final_commit_reason_code,
                    merge_ready=final_merge_ready,
                    human_review_required=final_human_review_required,
                    require_human_review_before_merge=(
                        require_human_review_before_merge
                    ),
                    mutation_guard=mutation_guard,
                )
                return

            if final_validation_result.status == "not_run":
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
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count,
                    validation_stop_reason=validation_stop_reason,
                    final_validation_status=final_validation_status,
                    final_fail_signature=final_fail_signature,
                    validation_attempts_payload=list(validation_attempts),
                    max_validation_attempts=validation_attempt_budget,
                    commit_after_validation=commit_after_validation,
                    commit_hash=None,
                    commit_status=(
                        "skipped" if commit_after_validation else "not_requested"
                    ),
                    commit_reason_code=(
                        "VALIDATION_NOT_RUN" if commit_after_validation else None
                    ),
                    merge_ready=False,
                    human_review_required=True,
                    require_human_review_before_merge=(
                        require_human_review_before_merge
                    ),
                    mutation_guard=mutation_guard,
                )
                return

            self._emit_validation_failed(
                task,
                adapter_kind=adapter_kind,
                validation_result=final_validation_result,
                validation_attempt_count=validation_attempt_count or 0,
                max_validation_attempts=validation_attempt_budget,
                validation_stop_reason=validation_stop_reason,
                final_validation_status=final_validation_status,
                final_fail_signature=final_fail_signature,
                lease_ctx=lease_ctx,
                best_validation_result=best_validation_result,
                mutation_guard=mutation_guard,
            )

            if final_validation_result.status == "failed" and (
                validation_stop_reason == "validation_retrying"
            ):
                retry_feedback = _build_retry_prompt(
                    task.instructions,
                    final_validation_result,
                    attempt_index + 1,
                    validation_command=validation_command or "",
                    validation_attempt_count=validation_attempt_count or 0,
                    max_validation_attempts=validation_attempt_budget,
                )
                self._emit_validation_retrying(
                    task,
                    adapter_kind=adapter_kind,
                    validation_result=final_validation_result,
                    validation_attempt_count=validation_attempt_count or 0,
                    next_validation_attempt_count=attempt_index + 1,
                    max_validation_attempts=validation_attempt_budget,
                    validation_stop_reason=validation_stop_reason,
                    retry_feedback=retry_feedback,
                    lease_ctx=lease_ctx,
                    best_validation_result=best_validation_result,
                    mutation_guard=mutation_guard,
                )
                previous_fail_signature = final_fail_signature
                continue

            final_errors = [*final_errors, "validation_failed"]
            final_error_code = _error_value("VALIDATION_FAILED")
            if final_validation_result.status == "error":
                final_error_message = (
                    final_validation_result.error_message
                    or "validation execution error"
                )
                commit_reason = "VALIDATION_ERROR"
                summary_suffix = "validation execution error"
            else:
                final_error_message = (
                    final_validation_result.error_message
                    or f"validation failed after {validation_attempt_count} attempt(s)"
                )
                commit_reason = "VALIDATION_FAILED"
                summary_suffix = (
                    f"validation failed after {validation_attempt_count} attempt(s)"
                )
            _persist_and_emit_terminal(
                result=result,
                result_status="failed",
                summary=(
                    f"{final_summary} | {summary_suffix}"
                    if final_summary
                    else summary_suffix
                ),
                files_changed=files_changed,
                artifacts=result_artifacts,
                adapter_session_ref=adapter_session_ref,
                errors=final_errors,
                error_code=final_error_code,
                error_message=final_error_message,
                validation_result=final_validation_result,
                validation_attempt_count=validation_attempt_count,
                validation_stop_reason=validation_stop_reason,
                final_validation_status=final_validation_status,
                final_fail_signature=final_fail_signature,
                validation_attempts_payload=list(validation_attempts),
                max_validation_attempts=validation_attempt_budget,
                commit_after_validation=commit_after_validation,
                commit_hash=None,
                commit_status=(
                    "skipped" if commit_after_validation else "not_requested"
                ),
                commit_reason_code=(commit_reason if commit_after_validation else None),
                merge_ready=False,
                human_review_required=True,
                require_human_review_before_merge=(
                    require_human_review_before_merge
                ),
                mutation_guard=mutation_guard,
            )
            return

        self._emit_failure(
            task,
            adapter_kind=adapter_kind,
            error_message="coding worker exhausted validation attempts",
            error_code="PROCESSING_ERROR",
            lease_ctx=lease_ctx,
        )

    def _emit_running(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        lease_ctx: LeaseExecutionContext | None = None,
    ) -> None:
        """Emit task.running event."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.running",
                _merge_payload(
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
                    lease_ctx,
                ),
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
        lease_ctx: LeaseExecutionContext | None = None,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.attempt_started for a validation-bearing attempt."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                _task_event_value(
                    "TASK_ATTEMPT_STARTED", "task.attempt_started"
                ),
                _merge_payload(
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
                        "validation_attempt_count": validation_attempt_count,
                        "max_validation_attempts": max_validation_attempts,
                        "validation_command": validation_command,
                    },
                    lease_ctx,
                    mutation_guard,
                ),
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit attempt started event: %s",
                exc,
            )

    def _emit_validation_started(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_command: str,
        validation_attempt_count: int,
        max_validation_attempts: int,
        lease_ctx: LeaseExecutionContext | None = None,
    ) -> None:
        """Emit task.validation_started for an upcoming validation run."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                _task_event_value(
                    "TASK_VALIDATION_STARTED", "task.validation_started"
                ),
                _merge_payload(
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
                        "status": "validation_started",
                        "validation_attempt_count": validation_attempt_count,
                        "max_validation_attempts": max_validation_attempts,
                        "validation_command": validation_command,
                    },
                    lease_ctx,
                ),
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit validation started event: %s",
                exc,
            )

    def _emit_validation_passed(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_result: NormalizedTestResult,
        validation_attempt_count: int,
        max_validation_attempts: int,
        lease_ctx: LeaseExecutionContext | None = None,
    ) -> None:
        """Emit task.validation_passed for a successful validation attempt."""
        try:
            task_events.publish_with_visibility(
                task.run_id,
                _task_event_value(
                    "TASK_VALIDATION_PASSED", "task.validation_passed"
                ),
                _merge_payload(
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
                        "status": "validation_passed",
                        "validation_attempt_count": validation_attempt_count,
                        "max_validation_attempts": max_validation_attempts,
                        "validation_results": validation_result.model_dump(),
                        "validation_result": validation_result.model_dump(),
                    },
                    lease_ctx,
                ),
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit validation passed event: %s",
                exc,
            )

    def _emit_validation_failed(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_result: NormalizedTestResult,
        validation_attempt_count: int,
        max_validation_attempts: int,
        validation_stop_reason: str | None = None,
        final_validation_status: str | None = None,
        final_fail_signature: str | None = None,
        lease_ctx: LeaseExecutionContext | None = None,
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
                "validation_attempt_count": validation_attempt_count,
                "max_validation_attempts": max_validation_attempts,
                "validation_stop_reason": validation_stop_reason,
                "final_validation_status": final_validation_status,
                "final_fail_signature": final_fail_signature,
                "validation_results": validation_result.model_dump(),
                "validation_result": validation_result.model_dump(),
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
            }
            task_events.publish_with_visibility(
                task.run_id,
                _task_event_value(
                    "TASK_VALIDATION_FAILED", "task.validation_failed"
                ),
                _merge_payload(payload, lease_ctx, mutation_guard),
            )
        except Exception as exc:
            logger.warning(
                "[coding-worker] failed to emit validation failed event: %s",
                exc,
            )

    def _emit_validation_retrying(
        self,
        task: CodingExecutionTask,
        *,
        adapter_kind: str | None,
        validation_result: NormalizedTestResult,
        validation_attempt_count: int,
        next_validation_attempt_count: int,
        max_validation_attempts: int,
        validation_stop_reason: str | None,
        retry_feedback: str,
        lease_ctx: LeaseExecutionContext | None = None,
        best_validation_result: NormalizedTestResult | None = None,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.validation_retrying with bounded retry feedback."""
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
                "status": "validation_retrying",
                "validation_attempt_count": validation_attempt_count,
                "next_validation_attempt_count": next_validation_attempt_count,
                "max_validation_attempts": max_validation_attempts,
                "validation_stop_reason": validation_stop_reason,
                "validation_results": validation_result.model_dump(),
                "validation_result": validation_result.model_dump(),
                "best_validation_result": (
                    best_validation_result.model_dump()
                    if best_validation_result is not None
                    else None
                ),
                "retry_feedback": retry_feedback,
            }
            task_events.publish_with_visibility(
                task.run_id,
                _task_event_value(
                    "TASK_VALIDATION_RETRYING", "task.validation_retrying"
                ),
                _merge_payload(payload, lease_ctx, mutation_guard),
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
        validation_results: dict[str, Any] | None = None,
        validation_attempt_count: int | None = None,
        validation_attempts: list[dict[str, Any]] | None = None,
        validation_stop_reason: str | None = None,
        final_validation_status: str | None = None,
        final_fail_signature: str | None = None,
        best_validation_result: dict[str, Any] | None = None,
        max_validation_attempts: int | None = None,
        lease_ctx: LeaseExecutionContext | None = None,
        commit_after_validation: bool = False,
        commit_hash: str | None = None,
        commit_status: str | None = None,
        commit_reason_code: str | None = None,
        merge_ready: bool = False,
        human_review_required: bool = True,
        require_human_review_before_merge: bool = True,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit terminal task event."""
        del result
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
                "validation_results": validation_results,
                "validation_result": validation_results,
                "validation_attempt_count": validation_attempt_count,
                "validation_attempts": validation_attempts,
                "validation_stop_reason": validation_stop_reason,
                "final_validation_status": final_validation_status,
                "final_fail_signature": final_fail_signature,
                "best_validation_result": best_validation_result,
                "max_validation_attempts": max_validation_attempts,
                "commit_after_validation": commit_after_validation,
                "commit_hash": commit_hash,
                "commit_status": commit_status,
                "commit_reason_code": commit_reason_code,
                "merge_ready": merge_ready,
                "human_review_required": human_review_required,
                "require_human_review_before_merge": (
                    require_human_review_before_merge
                ),
            }
            task_events.publish_with_visibility(
                task.run_id,
                f"task.{event_type}",
                _merge_payload(payload, lease_ctx, mutation_guard),
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
        lease_ctx: LeaseExecutionContext | None = None,
        result_captured_by_guardian: bool = False,
        lease_id: str | None = None,
        branch_name: str | None = None,
        worktree_path: str | None = None,
        lease_required: bool | None = None,
        mutation_guard: dict[str, Any] | None = None,
    ) -> None:
        """Emit task.failed event for unrecoverable errors."""
        self.store.update_run_status(
            run_id=task.run_id,
            status="failed",
            error=error_message,
        )
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
            "result_captured_by_guardian": result_captured_by_guardian,
        }
        if lease_id is not None:
            payload["worktree_lease_id"] = lease_id
        if branch_name is not None:
            payload["branch_name"] = branch_name
        if worktree_path is not None:
            payload["worktree_path"] = worktree_path
        if lease_required is not None:
            payload["lease_required"] = lease_required
        try:
            task_events.publish_with_visibility(
                task.run_id,
                "task.failed",
                _merge_payload(payload, lease_ctx, mutation_guard),
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_worker_loop()
