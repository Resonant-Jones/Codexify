from __future__ import annotations

import pytest

from guardian.agents.confidence import (
    classify_step_confidence,
    classify_task_confidence,
    compute_step_confidence,
    compute_task_confidence,
)


def test_step_confidence_formula_and_continue_band() -> None:
    result = compute_step_confidence(
        c_tests=1.0,
        c_schema=1.0,
        c_spec_alignment=1.0,
        c_diff_risk=0.8,
        c_model_stability=0.9,
    )

    # 0.35 + 0.20 + 0.20 + 0.15*0.8 + 0.10*0.9 = 0.96
    assert result.score == pytest.approx(0.96, rel=1e-6)
    assert result.decision == "continue"


def test_step_confidence_band_mapping() -> None:
    assert classify_step_confidence(0.90) == "continue"
    assert classify_step_confidence(0.80) == "warn"
    assert classify_step_confidence(0.60) == "soft_escalate"
    assert classify_step_confidence(0.20) == "hard_escalate"


def test_task_confidence_rollup_and_optional_audit_band() -> None:
    result = compute_task_confidence(
        step_scores=[0.90, 0.80],
        c_risk=0.70,
        escalation_penalty=0.20,
    )

    # mean=0.85, min=0.80, convergence=(1-0.10)=0.90
    expected = (
        (0.40 * 0.85)
        + (0.25 * 0.80)
        + (0.15 * 0.90)
        + (0.10 * 0.70)
        + (0.10 * 0.80)
    )
    assert result.score == pytest.approx(expected, rel=1e-6)
    assert result.decision == "optional_audit"


def test_task_confidence_threshold_mapping() -> None:
    assert classify_task_confidence(0.90) == "autonomous_approve"
    assert classify_task_confidence(0.75) == "optional_audit"
    assert classify_task_confidence(0.60) == "audit_required"
    assert classify_task_confidence(0.30) == "block_merge_human_required"
