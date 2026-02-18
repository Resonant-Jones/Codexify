"""Deterministic confidence scoring for delegated agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class StepConfidenceResult:
    score: float
    decision: str
    factors: dict[str, float]


@dataclass(frozen=True)
class TaskConfidenceResult:
    score: float
    decision: str
    factors: dict[str, float]


def classify_step_confidence(score: float) -> str:
    value = _clamp(score)
    if value >= 0.85:
        return "continue"
    if value >= 0.70:
        return "warn"
    if value >= 0.55:
        return "soft_escalate"
    return "hard_escalate"


def classify_task_confidence(score: float) -> str:
    value = _clamp(score)
    if value >= 0.85:
        return "autonomous_approve"
    if value >= 0.70:
        return "optional_audit"
    if value >= 0.55:
        return "audit_required"
    return "block_merge_human_required"


def compute_step_confidence(
    *,
    c_diff_risk: float,
    c_model_stability: float,
    c_tests: float = 1.0,
    c_schema: float = 1.0,
    c_spec_alignment: float = 1.0,
) -> StepConfidenceResult:
    factors = {
        "c_tests": _clamp(c_tests),
        "c_schema": _clamp(c_schema),
        "c_spec_alignment": _clamp(c_spec_alignment),
        "c_diff_risk": _clamp(c_diff_risk),
        "c_model_stability": _clamp(c_model_stability),
    }
    score = _clamp(
        (0.35 * factors["c_tests"])
        + (0.20 * factors["c_schema"])
        + (0.20 * factors["c_spec_alignment"])
        + (0.15 * factors["c_diff_risk"])
        + (0.10 * factors["c_model_stability"])
    )
    decision = classify_step_confidence(score)
    return StepConfidenceResult(score=score, decision=decision, factors=factors)


def _compute_convergence(step_scores: list[float]) -> float:
    if not step_scores:
        return 0.0
    if len(step_scores) == 1:
        return _clamp(step_scores[0])
    deltas = []
    for prev, cur in zip(step_scores[:-1], step_scores[1:]):
        deltas.append(abs(cur - prev))
    drift = mean(deltas) if deltas else 0.0
    return _clamp(1.0 - drift)


def compute_task_confidence(
    *,
    step_scores: list[float],
    c_risk: float,
    escalation_penalty: float,
    c_convergence: float | None = None,
) -> TaskConfidenceResult:
    if not step_scores:
        raise ValueError("step_scores must contain at least one value")

    normalized_steps = [_clamp(score) for score in step_scores]
    mean_step = _clamp(mean(normalized_steps))
    min_step = _clamp(min(normalized_steps))
    convergence = (
        _compute_convergence(normalized_steps)
        if c_convergence is None
        else _clamp(c_convergence)
    )
    risk = _clamp(c_risk)
    penalty = _clamp(escalation_penalty)
    score = _clamp(
        (0.40 * mean_step)
        + (0.25 * min_step)
        + (0.15 * convergence)
        + (0.10 * risk)
        + (0.10 * (1.0 - penalty))
    )
    decision = classify_task_confidence(score)
    factors = {
        "mean_step": mean_step,
        "min_step": min_step,
        "c_convergence": convergence,
        "c_risk": risk,
        "escalation_penalty": penalty,
    }
    return TaskConfidenceResult(score=score, decision=decision, factors=factors)


__all__ = [
    "StepConfidenceResult",
    "TaskConfidenceResult",
    "classify_step_confidence",
    "classify_task_confidence",
    "compute_step_confidence",
    "compute_task_confidence",
]
