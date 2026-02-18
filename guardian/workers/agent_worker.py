"""Deterministic delegated-agent worker primitives."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from guardian.agents.confidence import (
    compute_step_confidence,
    compute_task_confidence,
)
from guardian.agents.events import AgentEventPublisher, publisher
from guardian.agents.retry_policy import (
    AttemptMetrics,
    RetryConfig,
    evaluate_retry_decision,
)
from guardian.agents.store import AgentStore, deterministic_worktree_id, store
from guardian.core.config import Settings, get_settings
from guardian.core.orchestrator.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttemptEvaluation:
    schema_valid: bool
    tests_passed: bool
    spec_alignment_ok: bool
    fail_count: int
    fail_signature: str
    diff_added: int
    diff_deleted: int
    error_category: str
    diff_risk: float = 1.0
    model_stability: float = 1.0
    model_self_confidence: float | None = None
    stderr_excerpt: str | None = None


@dataclass(frozen=True)
class StepExecutionResult:
    status: str
    attempts: int
    commit_a_hash: str | None = None
    commit_b_hash: str | None = None
    escalation_reason: str | None = None
    preserved_worktree: bool = False


class CommitBackend(Protocol):
    def commit_mutation(self, *, worktree_path: str, message: str) -> str:
        ...

    def commit_validation_boundary(
        self, *, worktree_path: str, message: str, allow_empty: bool
    ) -> str:
        ...


def _run_git(
    args: list[str],
    *,
    cwd: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


class GitCommitBackend:
    """Git-backed commit boundary helper."""

    def __init__(
        self,
        run_cmd: Callable[..., subprocess.CompletedProcess[str]] = _run_git,
    ) -> None:
        self._run_cmd = run_cmd

    def _head_hash(self, *, worktree_path: str) -> str:
        proc = self._run_cmd(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            check=True,
        )
        return (proc.stdout or "").strip()

    def commit_mutation(self, *, worktree_path: str, message: str) -> str:
        self._run_cmd(["git", "add", "-A"], cwd=worktree_path, check=True)
        self._run_cmd(
            ["git", "commit", "-m", message],
            cwd=worktree_path,
            check=True,
        )
        return self._head_hash(worktree_path=worktree_path)

    def commit_validation_boundary(
        self, *, worktree_path: str, message: str, allow_empty: bool
    ) -> str:
        args = ["git", "commit", "-m", message]
        if allow_empty:
            args.insert(2, "--allow-empty")
        self._run_cmd(args, cwd=worktree_path, check=True)
        return self._head_hash(worktree_path=worktree_path)


def _progress_made(
    *,
    current: AttemptEvaluation,
    history: list[AttemptMetrics],
) -> bool:
    if not history:
        return False
    prev = history[-1]
    if current.fail_count < prev.fail_count:
        return True
    rank = {
        "spec_alignment_violation": 0,
        "schema_invalid": 1,
        "tests_failed": 2,
        "unknown": 3,
    }
    prev_rank = rank.get(prev.error_category, 3)
    cur_rank = rank.get(current.error_category, 3)
    return cur_rank < prev_rank


def _settings_retry_config(settings: Settings) -> RetryConfig:
    return RetryConfig(
        max_attempts=int(settings.AGENT_MAX_ATTEMPTS),
        min_attempts_before_abort=int(settings.AGENT_MIN_ATTEMPTS_BEFORE_ABORT),
        no_progress_window=int(settings.AGENT_NO_PROGRESS_WINDOW),
        max_same_signature_repeats=int(
            settings.AGENT_MAX_SAME_SIGNATURE_REPEATS
        ),
        regression_limit=int(settings.AGENT_REGRESSION_LIMIT),
    )


def _emit(
    event_publisher: AgentEventPublisher,
    *,
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    event_publisher.emit(
        run_id=run_id,
        event_type=event_type,
        payload=payload,
    )


def _persist_escalation(
    *,
    telemetry_store: AgentStore,
    event_publisher: AgentEventPublisher,
    run_id: str,
    step_index: int,
    reason_code: str,
    reason: str,
    severity: str,
    preserved_worktree: bool,
) -> None:
    telemetry_store.add_escalation(
        run_id=run_id,
        step_index=step_index,
        severity=severity,
        reason_code=reason_code,
        reason=reason,
        preserved_worktree=preserved_worktree,
        payload={"reason_code": reason_code, "step_index": step_index},
    )
    _emit(
        event_publisher,
        run_id=run_id,
        event_type="escalated",
        payload={
            "step_index": step_index,
            "reason_code": reason_code,
            "reason": reason,
            "severity": severity,
            "preserved_worktree": preserved_worktree,
        },
    )


def process_mutating_step(
    *,
    deployment_id: str,
    run_id: str,
    step_index: int,
    step_id: str,
    primitive: str,
    worktree_path: str,
    attempt_executor: Callable[[int], AttemptEvaluation],
    telemetry_store: AgentStore | None = None,
    event_publisher: AgentEventPublisher | None = None,
    settings: Settings | None = None,
    commit_backend: CommitBackend | None = None,
    validator_hook: Callable[[int], None] | None = None,
) -> StepExecutionResult:
    """Execute one mutating step with adaptive retries and strict commit doctrine."""
    resolved_store = telemetry_store or store
    resolved_events = event_publisher or publisher
    resolved_settings = settings or get_settings()
    resolved_commits = commit_backend or GitCommitBackend()
    retry_cfg = _settings_retry_config(resolved_settings)

    resolved_store.create_step(
        run_id=run_id,
        step_index=step_index,
        step_id=step_id,
        primitive=primitive,
        is_mutating=True,
    )
    _emit(
        resolved_events,
        run_id=run_id,
        event_type="started",
        payload={"step_index": step_index, "step_id": step_id},
    )

    history: list[AttemptMetrics] = []

    for attempt_index in range(1, retry_cfg.max_attempts + 1):
        if resolved_settings.AGENT_VALIDATOR_MODEL_ENABLED and validator_hook:
            validator_hook(attempt_index)

        attempt = attempt_executor(attempt_index)
        progress = _progress_made(current=attempt, history=history)
        attempt_status = (
            "succeeded"
            if (
                attempt.schema_valid
                and attempt.tests_passed
                and attempt.spec_alignment_ok
            )
            else "failed"
        )

        if not attempt.spec_alignment_ok:
            attempt_status = "escalated"

        resolved_store.add_attempt(
            run_id=run_id,
            step_index=step_index,
            attempt_index=attempt_index,
            status=attempt_status,
            fail_count=attempt.fail_count,
            fail_signature=attempt.fail_signature,
            diff_added=attempt.diff_added,
            diff_deleted=attempt.diff_deleted,
            error_category=attempt.error_category,
            progress_made=progress,
            stderr_excerpt=attempt.stderr_excerpt,
        )

        if not attempt.spec_alignment_ok:
            resolved_store.update_step_status(
                run_id=run_id,
                step_index=step_index,
                status="escalated",
                schema_valid=attempt.schema_valid,
                spec_alignment_ok=False,
                tests_passed=attempt.tests_passed,
            )
            resolved_store.update_run_status(run_id=run_id, status="escalated")
            _persist_escalation(
                telemetry_store=resolved_store,
                event_publisher=resolved_events,
                run_id=run_id,
                step_index=step_index,
                reason_code="spec_alignment_violation",
                reason="Spec alignment violation detected",
                severity="hard",
                preserved_worktree=True,
            )
            return StepExecutionResult(
                status="escalated",
                attempts=attempt_index,
                escalation_reason="spec_alignment_violation",
                preserved_worktree=True,
            )

        if attempt.schema_valid and attempt.tests_passed:
            step_conf = compute_step_confidence(
                c_diff_risk=attempt.diff_risk,
                c_model_stability=attempt.model_stability,
                c_tests=1.0,
                c_schema=1.0,
                c_spec_alignment=1.0,
            )
            resolved_store.add_confidence_report(
                run_id=run_id,
                step_index=step_index,
                scope="step",
                confidence=step_conf.score,
                decision=step_conf.decision,
                factors=step_conf.factors,
                model_self_confidence=attempt.model_self_confidence,
            )

            if step_conf.decision in {"soft_escalate", "hard_escalate"}:
                severity = (
                    "soft" if step_conf.decision == "soft_escalate" else "hard"
                )
                resolved_store.update_step_status(
                    run_id=run_id,
                    step_index=step_index,
                    status="escalated",
                    schema_valid=True,
                    spec_alignment_ok=True,
                    tests_passed=True,
                )
                resolved_store.update_run_status(
                    run_id=run_id, status="escalated"
                )
                _persist_escalation(
                    telemetry_store=resolved_store,
                    event_publisher=resolved_events,
                    run_id=run_id,
                    step_index=step_index,
                    reason_code=step_conf.decision,
                    reason=("Confidence gate blocked autonomous continuation"),
                    severity=severity,
                    preserved_worktree=True,
                )
                return StepExecutionResult(
                    status="escalated",
                    attempts=attempt_index,
                    escalation_reason=step_conf.decision,
                    preserved_worktree=True,
                )

            task_conf = compute_task_confidence(
                step_scores=[step_conf.score],
                c_risk=attempt.diff_risk,
                escalation_penalty=0.0,
            )
            resolved_store.add_confidence_report(
                run_id=run_id,
                step_index=None,
                scope="task",
                confidence=task_conf.score,
                decision=task_conf.decision,
                factors=task_conf.factors,
                model_self_confidence=attempt.model_self_confidence,
            )

            # Commit doctrine: only after passing tests/schema/spec.
            commit_a = resolved_commits.commit_mutation(
                worktree_path=worktree_path,
                message=f"TASK-{step_id}: mutation",
            )
            commit_b = resolved_commits.commit_validation_boundary(
                worktree_path=worktree_path,
                message=f"TASK-{step_id}: validation-boundary",
                allow_empty=bool(
                    resolved_settings.AGENT_VALIDATION_COMMIT_ALLOW_EMPTY
                ),
            )
            resolved_store.add_artifact(
                run_id=run_id,
                step_index=step_index,
                artifact_type="commit_a_hash",
                content_json={"hash": commit_a},
            )
            resolved_store.add_artifact(
                run_id=run_id,
                step_index=step_index,
                artifact_type="commit_b_hash",
                content_json={"hash": commit_b},
            )
            resolved_store.update_step_status(
                run_id=run_id,
                step_index=step_index,
                status="succeeded",
                schema_valid=True,
                spec_alignment_ok=True,
                tests_passed=True,
            )
            resolved_store.update_run_status(run_id=run_id, status="succeeded")
            _emit(
                resolved_events,
                run_id=run_id,
                event_type="step_succeeded",
                payload={
                    "step_index": step_index,
                    "commit_a_hash": commit_a,
                    "commit_b_hash": commit_b,
                },
            )
            _emit(
                resolved_events,
                run_id=run_id,
                event_type="succeeded",
                payload={
                    "step_index": step_index,
                    "commit_a_hash": commit_a,
                    "commit_b_hash": commit_b,
                },
            )
            return StepExecutionResult(
                status="succeeded",
                attempts=attempt_index,
                commit_a_hash=commit_a,
                commit_b_hash=commit_b,
                preserved_worktree=False,
            )

        _emit(
            resolved_events,
            run_id=run_id,
            event_type="attempt_failed",
            payload={
                "step_index": step_index,
                "attempt_index": attempt_index,
                "fail_count": attempt.fail_count,
                "fail_signature": attempt.fail_signature,
                "error_category": attempt.error_category,
            },
        )

        current_metrics = AttemptMetrics(
            fail_count=attempt.fail_count,
            fail_signature=attempt.fail_signature,
            diff_added=attempt.diff_added,
            diff_deleted=attempt.diff_deleted,
            error_category=attempt.error_category,
            progress_made=progress,
        )
        decision = evaluate_retry_decision(
            attempt_index=attempt_index,
            current=current_metrics,
            history=history,
            config=retry_cfg,
            spec_alignment_violation=False,
        )
        history.append(current_metrics)

        if decision.escalate:
            resolved_store.update_step_status(
                run_id=run_id,
                step_index=step_index,
                status="escalated",
                schema_valid=attempt.schema_valid,
                spec_alignment_ok=True,
                tests_passed=attempt.tests_passed,
            )
            resolved_store.update_run_status(run_id=run_id, status="escalated")
            _persist_escalation(
                telemetry_store=resolved_store,
                event_publisher=resolved_events,
                run_id=run_id,
                step_index=step_index,
                reason_code=decision.reason,
                reason="Adaptive retry policy escalated step",
                severity="soft",
                preserved_worktree=True,
            )
            return StepExecutionResult(
                status="escalated",
                attempts=attempt_index,
                escalation_reason=decision.reason,
                preserved_worktree=True,
            )

        if not decision.should_retry:
            break

        _emit(
            resolved_events,
            run_id=run_id,
            event_type="attempt_progress",
            payload={
                "step_index": step_index,
                "attempt_index": attempt_index,
                "decision": decision.reason,
            },
        )

    resolved_store.update_step_status(
        run_id=run_id,
        step_index=step_index,
        status="failed",
        schema_valid=False,
        spec_alignment_ok=True,
        tests_passed=False,
    )
    resolved_store.update_run_status(run_id=run_id, status="failed")
    _emit(
        resolved_events,
        run_id=run_id,
        event_type="failed",
        payload={"step_index": step_index, "reason": "max_attempts_exhausted"},
    )
    return StepExecutionResult(
        status="failed",
        attempts=retry_cfg.max_attempts,
        escalation_reason="max_attempts_exhausted",
        preserved_worktree=False,
    )


def apply_worktree_cleanup_policy(
    *,
    workspace_manager: WorkspaceManager,
    task_worktree_id: str,
    result: StepExecutionResult,
    settings: Settings | None = None,
) -> None:
    resolved = settings or get_settings()
    should_cleanup = bool(resolved.AGENT_AUTO_ROLLBACK_ON_FAIL)
    if result.status == "failed" and should_cleanup:
        workspace_manager.cleanup_worktree(task_worktree_id)
        return
    # Escalated runs intentionally preserve worktree for manual review.


def create_mutating_worktree(
    *,
    workspace_manager: WorkspaceManager,
    deployment_id: str,
    run_id: str,
    step_index: int,
    base_branch: str,
    campaign_id: str,
) -> tuple[str, str]:
    task_worktree_id = deterministic_worktree_id(
        deployment_id=deployment_id,
        run_id=run_id,
        step_index=step_index,
    )
    path = workspace_manager.create_worktree(
        task_id=task_worktree_id,
        base_branch=base_branch,
        campaign_id=campaign_id,
        force=True,
    )
    return task_worktree_id, str(Path(path).resolve())


__all__ = [
    "AttemptEvaluation",
    "CommitBackend",
    "GitCommitBackend",
    "StepExecutionResult",
    "apply_worktree_cleanup_policy",
    "create_mutating_worktree",
    "process_mutating_step",
]
