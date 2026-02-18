from __future__ import annotations

from guardian.agents.retry_policy import (
    AttemptMetrics,
    RetryConfig,
    evaluate_retry_decision,
)

DEFAULT_CFG = RetryConfig(
    max_attempts=5,
    min_attempts_before_abort=2,
    no_progress_window=2,
    max_same_signature_repeats=2,
    regression_limit=2,
)


def test_retry_escalates_on_no_progress_window() -> None:
    history = [
        AttemptMetrics(
            fail_count=3,
            fail_signature="sig-a",
            diff_added=10,
            diff_deleted=2,
            error_category="tests_failed",
            progress_made=False,
        )
    ]
    current = AttemptMetrics(
        fail_count=3,
        fail_signature="sig-b",
        diff_added=1,
        diff_deleted=0,
        error_category="tests_failed",
    )

    decision = evaluate_retry_decision(
        attempt_index=2,
        current=current,
        history=history,
        config=DEFAULT_CFG,
    )

    assert decision.escalate is True
    assert decision.should_retry is False
    assert decision.reason == "no_progress_window"


def test_retry_escalates_on_same_signature_repeats() -> None:
    history = [
        AttemptMetrics(
            fail_count=4,
            fail_signature="same",
            diff_added=1,
            diff_deleted=0,
            error_category="tests_failed",
            progress_made=True,
        ),
        AttemptMetrics(
            fail_count=4,
            fail_signature="same",
            diff_added=1,
            diff_deleted=0,
            error_category="tests_failed",
            progress_made=True,
        ),
    ]
    current = AttemptMetrics(
        fail_count=4,
        fail_signature="same",
        diff_added=1,
        diff_deleted=0,
        error_category="tests_failed",
    )

    decision = evaluate_retry_decision(
        attempt_index=3,
        current=current,
        history=history,
        config=DEFAULT_CFG,
    )

    assert decision.escalate is True
    assert decision.should_retry is False
    assert decision.reason == "same_signature_repeat"


def test_retry_escalates_on_regression_limit() -> None:
    history = [
        AttemptMetrics(
            fail_count=1,
            fail_signature="sig-best",
            diff_added=2,
            diff_deleted=1,
            error_category="tests_failed",
            progress_made=True,
        ),
        AttemptMetrics(
            fail_count=2,
            fail_signature="sig-next",
            diff_added=2,
            diff_deleted=1,
            error_category="tests_failed",
            progress_made=True,
        ),
    ]
    current = AttemptMetrics(
        fail_count=4,
        fail_signature="sig-regressed",
        diff_added=20,
        diff_deleted=5,
        error_category="tests_failed",
    )

    decision = evaluate_retry_decision(
        attempt_index=3,
        current=current,
        history=history,
        config=DEFAULT_CFG,
    )

    assert decision.escalate is True
    assert decision.should_retry is False
    assert decision.reason == "regression_limit"
