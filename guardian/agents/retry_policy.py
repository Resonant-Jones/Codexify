"""Adaptive retry policy for delegated agent mutating steps."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _stable_text_lines(lines: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in lines or []:
        clean = " ".join(str(raw).strip().split())
        if clean:
            out.append(clean)
    return out


def build_fail_signature(
    failing_tests: list[str] | None,
    stderr_lines: list[str] | None,
) -> str:
    tests = sorted(set(_stable_text_lines(failing_tests)))
    stderr = _stable_text_lines(stderr_lines)[:20]
    payload = "\n".join([*tests, "---", *stderr])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:24]


def _error_rank(value: str | None) -> int:
    ranks = {
        "spec_alignment_violation": 0,
        "schema_invalid": 1,
        "tests_failed": 2,
        "unknown": 3,
    }
    key = str(value or "unknown").strip().lower()
    return ranks.get(key, ranks["unknown"])


@dataclass(frozen=True)
class AttemptMetrics:
    fail_count: int
    fail_signature: str
    diff_added: int
    diff_deleted: int
    error_category: str
    progress_made: bool = False


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 5
    min_attempts_before_abort: int = 2
    no_progress_window: int = 2
    max_same_signature_repeats: int = 2
    regression_limit: int = 2


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    escalate: bool
    reason: str


def _count_same_signature_suffix(
    history: list[AttemptMetrics], current_signature: str
) -> int:
    count = 0
    for item in reversed(history):
        if item.fail_signature != current_signature:
            break
        count += 1
    return count


def _no_progress_suffix(history: list[AttemptMetrics]) -> int:
    count = 0
    for item in reversed(history):
        if item.progress_made:
            break
        count += 1
    return count


def _is_progress(
    current: AttemptMetrics,
    previous: AttemptMetrics | None,
    best_fail_count: int | None,
) -> bool:
    if previous is not None:
        if current.fail_count < previous.fail_count:
            return True
        if _error_rank(current.error_category) < _error_rank(
            previous.error_category
        ):
            return True
    if best_fail_count is not None and current.fail_count < best_fail_count:
        return True
    return False


def evaluate_retry_decision(
    *,
    attempt_index: int,
    current: AttemptMetrics,
    history: list[AttemptMetrics],
    config: RetryConfig,
    spec_alignment_violation: bool = False,
) -> RetryDecision:
    if spec_alignment_violation:
        return RetryDecision(
            should_retry=False,
            escalate=True,
            reason="spec_alignment_violation",
        )

    best_fail_count = min(
        (item.fail_count for item in history),
        default=None,
    )
    previous = history[-1] if history else None
    progress = _is_progress(current, previous, best_fail_count)
    current_with_progress = AttemptMetrics(
        fail_count=current.fail_count,
        fail_signature=current.fail_signature,
        diff_added=current.diff_added,
        diff_deleted=current.diff_deleted,
        error_category=current.error_category,
        progress_made=progress,
    )
    extended = [*history, current_with_progress]
    min_reached = attempt_index >= config.min_attempts_before_abort

    if min_reached:
        no_progress = _no_progress_suffix(extended)
        if no_progress >= config.no_progress_window:
            return RetryDecision(
                should_retry=False,
                escalate=True,
                reason="no_progress_window",
            )

        same_sig = _count_same_signature_suffix(
            extended, current.fail_signature
        )
        if same_sig > config.max_same_signature_repeats:
            return RetryDecision(
                should_retry=False,
                escalate=True,
                reason="same_signature_repeat",
            )

        if best_fail_count is not None and (
            current.fail_count > best_fail_count + config.regression_limit
        ):
            return RetryDecision(
                should_retry=False,
                escalate=True,
                reason="regression_limit",
            )

    if attempt_index >= config.max_attempts:
        return RetryDecision(
            should_retry=False,
            escalate=False,
            reason="max_attempts_exhausted",
        )

    return RetryDecision(should_retry=True, escalate=False, reason="retry")


__all__ = [
    "AttemptMetrics",
    "RetryConfig",
    "RetryDecision",
    "build_fail_signature",
    "evaluate_retry_decision",
]
