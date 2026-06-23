"""Tests for Personal Facts guardrail override semantics.

Tests _is_guardrail_override_allowed and the approve_candidate route
integration with override_guardrail.
"""

from __future__ import annotations

import pytest

from guardian.routes.personal_facts import (
    _is_guardrail_override_allowed,
    _is_guardrail_approval_blocked,
)


# ── helpers ──


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
    return dict(kw)


def _blocked_fact(**overrides) -> dict:
    meta = _gm(
        disposition="quarantine",
        reasons=["source_role_assistant"],
        runtime_eligible=False,
        review_required=True,
        promotion_blocked=True,
    )
    meta.update(overrides.get("guardrail_metadata", {}))
    overrides.pop("guardrail_metadata", None)
    return _fact({**overrides, "guardrail_metadata": meta})


# ── 1. blocked without override_guardrail ───────────────────────────────────


def test_blocked_candidate_still_blocked_without_override_guardrail():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value=None,
        original_key="user_location",
        original_value="Portland",
        override_guardrail=False,
        override_note=None,
    )
    assert allowed is False
    assert reason == "override_guardrail_not_set"


# ── 2. blocked with override_guardrail=false ─────────────────────────────────


def test_blocked_candidate_still_blocked_with_override_guardrail_false():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value=None,
        original_key="user_location",
        original_value="Portland",
        override_guardrail=False,
        override_note="user confirms this is correct",
    )
    assert allowed is False
    assert reason == "override_guardrail_not_set"


# ── 3. override without edit fails ──────────────────────────────────────────


def test_override_without_edit_or_note_fails():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value=None,
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note=None,
    )
    assert allowed is False
    assert reason == "override_requires_edit_or_note"


# ── 4. successful override with edited value ────────────────────────────────


def test_override_succeeds_with_edited_value_and_note():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value="Portland, Oregon",
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note="User corrected the city name",
    )
    assert allowed is True
    assert reason is None


def test_override_succeeds_with_edited_key():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key="user_city",
        edited_value="Portland",
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note="Corrected the key name",
    )
    assert allowed is True
    assert reason is None


def test_override_succeeds_with_note_only():
    """User explicitly confirms the value as-is with a note."""
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value="Portland",
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note="I confirm this is my location",
    )
    assert allowed is True
    assert reason is None


# ── 5. malformed metadata fails closed ──────────────────────────────────────


def test_malformed_metadata_cannot_be_overridden():
    fact = _fact({"guardrail_metadata": "not-a-dict"})
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value="Portland, Oregon",
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note="corrected",
    )
    assert allowed is False
    assert reason == "guardrail_metadata_malformed"


# ── 6. clean candidate without guardrail block approves normally ────────────


def test_clean_candidate_override_check_passes():
    fact = _fact()  # no guardrail_metadata at all
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value=None,
        original_key="user_location",
        original_value="Portland",
        override_guardrail=False,
        override_note=None,
    )
    assert allowed is True
    assert reason is None


def test_clean_candidate_not_blocked_by_approval_check():
    fact = _fact()
    blocked, reason = _is_guardrail_approval_blocked(fact)
    assert blocked is False
    assert reason is None


# ── 7. non-blocking metadata does not require override ─────────────────────


def test_non_blocking_metadata_does_not_require_override():
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
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=None,
        edited_value=None,
        original_key="user_location",
        original_value="Portland",
        override_guardrail=False,
        override_note=None,
    )
    assert allowed is True
    assert reason is None


# ── 8. override with key edit only ─────────────────────────────────────────


def test_override_with_key_change_only():
    fact = _blocked_fact(
        key="bad_key",
        guardrail_metadata={
            "disposition": "quarantine",
            "reasons": ["sentence_fragment_key"],
            "runtime_eligible": False,
            "review_required": True,
            "promotion_blocked": True,
        },
    )
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key="user_location_city",
        edited_value="Portland",
        original_key="bad_key",
        original_value="Portland",
        override_guardrail=True,
        override_note="Fixed the fragment key",
    )
    assert allowed is True
    assert reason is None


# ── 9. override with empty edit strings fails ──────────────────────────────


def test_override_with_empty_edited_strings_fails():
    fact = _blocked_fact()
    allowed, reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key="",
        edited_value="",
        original_key="user_location",
        original_value="Portland",
        override_guardrail=True,
        override_note="  ",
    )
    assert allowed is False
    assert reason == "override_requires_edit_or_note"
