"""Tests for Personal Facts approval guardrails.

Covers the _is_guardrail_approval_blocked helper and the approve
candidate route integration.
"""

from __future__ import annotations

import pytest

from guardian.routes.personal_facts import _is_guardrail_approval_blocked


# ── Helpers ──


def _fact(overrides: dict | None = None) -> dict:
    base: dict = {
        "id": 1,
        "user_id": "local",
        "key": "user_location",
        "value": "Portland",
        "status": "candidate",
        "confidence": 0.92,
        "is_active": True,
    }
    if overrides:
        base.update(overrides)
    return base


def _gm(**kw) -> dict:
    """Build guardrail_metadata dict."""
    return dict(kw)


# ── 1. clean reviewable → not blocked ──────────────────────────────────────


def test_clean_reviewable_candidate_is_not_blocked():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="reviewable",
                reasons=["import_noise"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False
    assert reason is None


# ── 2. promotion_blocked=true → blocked ─────────────────────────────────────


def test_promotion_blocked_true_cannot_be_approved():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["source_role_assistant"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=True,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "promotion_blocked"


# ── 3. source_role_assistant → blocked ─────────────────────────────────────


def test_source_role_assistant_reason_blocks_approval():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["source_role_assistant", "import_noise"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "source_role_assistant"


# ── 4. source_role_ambiguous → blocked ─────────────────────────────────────


def test_source_role_ambiguous_reason_blocks_approval():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["source_role_ambiguous"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "source_role_ambiguous"


# ── 5. missing_evidence → blocked ───────────────────────────────────────────


def test_missing_evidence_reason_blocks_approval():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["missing_evidence"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "missing_evidence"


# ── 6. malformed metadata → fails closed ────────────────────────────────────


def test_malformed_metadata_fails_closed():
    fact = _fact({"guardrail_metadata": "not-a-dict"})
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "guardrail_metadata_malformed"


def test_null_metadata_does_not_crash():
    fact = _fact({"guardrail_metadata": None})
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False
    assert reason is None


# ── 7. no guardrail_metadata → preserves existing behavior ──────────────────


def test_no_guardrail_metadata_preserves_existing_behavior():
    fact = _fact()
    assert "guardrail_metadata" not in fact
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False
    assert reason is None


# ── 8. quoted_or_hypothetical → blocked ─────────────────────────────────────


def test_quoted_or_hypothetical_reason_blocks_approval():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["quoted_or_hypothetical"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "quoted_or_hypothetical"


# ── 9. source_role_system_like → blocked ────────────────────────────────────


def test_source_role_system_like_reason_blocks_approval():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="quarantine",
                reasons=["source_role_system_like"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "source_role_system_like"


# ── Non-blocking reasons do not block ───────────────────────────────────────


def test_non_blocking_reason_does_not_block():
    """Reasons like import_noise, low_confidence, stale are not direct blockers."""
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="reviewable",
                reasons=["import_noise", "low_confidence"],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False
    assert reason is None


# ── Edge cases ──────────────────────────────────────────────────────────────


def test_empty_reasons_list_is_not_blocked():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                disposition="reviewable",
                reasons=[],
                runtime_eligible=False,
                review_required=True,
                promotion_blocked=False,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False


def test_reasons_not_a_list_is_safe():
    fact = _fact(
        {
            "guardrail_metadata": {
                "disposition": "quarantine",
                "reasons": "not-a-list",
                "promotion_blocked": False,
            }
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    # reasons is not a list so no blocking reasons found; not blocked
    assert blocked is False


def test_missing_disposition_but_promotion_blocked():
    fact = _fact(
        {
            "guardrail_metadata": _gm(
                reasons=["source_role_assistant"],
                promotion_blocked=True,
            )
        }
    )
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is True
    assert reason == "promotion_blocked"
