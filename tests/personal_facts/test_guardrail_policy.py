"""Tests for the Personal Facts guardrail classification policy.

Covers all fixture classes from
docs/architecture/personal-facts-guardrails-contract.md section 17.
"""

from __future__ import annotations

import pytest

from guardian.personal_facts.guardrail_policy import (
    CandidateInput,
    ClassificationResult,
    classify_personal_fact_candidate,
)
from guardian.personal_facts.guardrail_tokens import GuardrailReason


def _make_candidate(**overrides) -> CandidateInput:
    """Build a clean user-authored candidate with sensible defaults."""
    defaults: dict[str, str | float | None] = {
        "key": "user_location_city",
        "value": "Portland",
        "confidence": 0.92,
        "source_role": "user",
        "source_type": "chat_message",
        "source_label": None,
        "source_excerpt": "I live in Portland, Oregon.",
        "source_timestamp": "2026-06-20T12:00:00Z",
    }
    defaults.update(overrides)
    return CandidateInput(**defaults)  # type: ignore[arg-type]


# ── 1. clean user-authored fact ─────────────────────────────────────────────


def test_clean_user_authored_fact_is_reviewable_but_not_runtime_eligible():
    candidate = _make_candidate()
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition == "reviewable"
    assert result.runtime_eligible is False
    assert result.review_required is True
    assert result.promotion_blocked is False


# ── 2. assistant-authored identity claim ────────────────────────────────────


def test_assistant_authored_claim_is_quarantined():
    candidate = _make_candidate(
        source_role="assistant",
        key="user_profession",
        value="professional chef",
        source_excerpt="The user is a professional chef with 15 years of experience.",
    )
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition in ("quarantine", "discard")
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 3. ambiguous source role ────────────────────────────────────────────────


def test_ambiguous_source_role_is_quarantined():
    candidate = _make_candidate(source_role=None)
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition in ("quarantine", "discard")
    assert GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_unknown_source_role_is_quarantined():
    candidate = _make_candidate(source_role="bot")
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition in ("quarantine", "discard")
    assert GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 4. system-like source role ──────────────────────────────────────────────


@pytest.mark.parametrize("role", ["system", "developer", "tool"])
def test_system_like_source_role_is_quarantined(role: str):
    candidate = _make_candidate(source_role=role)
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition in ("quarantine", "discard")
    assert GuardrailReason.SOURCE_ROLE_SYSTEM_LIKE.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 5. quoted or hypothetical source text ───────────────────────────────────


def test_quoted_text_is_promotion_blocked():
    candidate = _make_candidate(
        source_excerpt='"I\'m moving to Seattle next month," she said.',
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.QUOTED_OR_HYPOTHETICAL.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_hypothetical_text_is_promotion_blocked():
    candidate = _make_candidate(
        source_excerpt="Imagine if I worked at a bakery for example.",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.QUOTED_OR_HYPOTHETICAL.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 6. sentence-fragment key ────────────────────────────────────────────────


def test_sentence_fragment_key_is_blocked():
    candidate = _make_candidate(key="lives in")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_empty_key_is_blocked():
    candidate = _make_candidate(key="")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in result.reasons
    assert result.promotion_blocked is True


def test_lowercase_start_key_is_blocked():
    candidate = _make_candidate(key="user lives in Portland")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in result.reasons
    assert result.promotion_blocked is True


# ── 7. excessive key length ─────────────────────────────────────────────────


def test_excessive_key_length_is_blocked():
    long_key = "User has a very long and detailed personal history that spans many years and includes numerous specific details about their background, education, professional experience, family relationships, geographic movements, personal preferences, hobbies, interests, belief systems, and future aspirations that cannot be reasonably reduced to a single canonical fact key and should therefore be rejected by the shape guardrail."
    candidate = _make_candidate(key=long_key)
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.EXCESSIVE_KEY_LENGTH.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 8. incomplete value fragment ────────────────────────────────────────────


def test_incomplete_value_fragment_is_blocked():
    candidate = _make_candidate(value="works at the...")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.INCOMPLETE_VALUE_FRAGMENT.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_empty_value_is_blocked():
    candidate = _make_candidate(value="")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.INCOMPLETE_VALUE_FRAGMENT.value in result.reasons
    assert result.promotion_blocked is True


# ── 9. missing evidence ─────────────────────────────────────────────────────


def test_missing_evidence_blocks_promotion():
    candidate = _make_candidate(source_excerpt=None)
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.MISSING_EVIDENCE.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_empty_key_and_value_is_discarded():
    candidate = _make_candidate(key="", value="", source_excerpt="")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.MISSING_EVIDENCE.value in result.reasons
    assert result.disposition == "discard"
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 10. low confidence ──────────────────────────────────────────────────────


def test_low_confidence_adds_low_confidence_and_not_runtime_eligible():
    candidate = _make_candidate(confidence=0.3)
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.LOW_CONFIDENCE.value in result.reasons
    assert result.runtime_eligible is False


def test_none_confidence_adds_low_confidence():
    candidate = _make_candidate(confidence=None)
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.LOW_CONFIDENCE.value in result.reasons
    assert result.runtime_eligible is False


def test_high_confidence_does_not_override_quarantine():
    """Confidence is advisory — high confidence must not bypass quarantine
    when a blocking reason exists."""
    candidate = _make_candidate(
        confidence=0.99,
        source_role="assistant",
        key="user_nationality",
        value="French",
        source_excerpt="As a French citizen, the user enjoys travelling.",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False
    # High confidence must not enable runtime eligibility.
    assert 0.99 > 0.9  # confidence is high
    assert result.runtime_eligible is False


# ── 11. imported ChatGPT / OpenAI source ────────────────────────────────────


def test_imported_chatgpt_source_adds_import_noise_and_requires_review():
    candidate = _make_candidate(
        source_type="chatgpt_import",
        source_label="chatgpt_import",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.IMPORT_NOISE.value in result.reasons
    assert result.review_required is True
    assert result.runtime_eligible is False


def test_imported_claude_source_adds_import_noise():
    candidate = _make_candidate(
        source_type="claude_import",
        source_label="claude_import",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.IMPORT_NOISE.value in result.reasons
    assert result.review_required is True
    assert result.runtime_eligible is False


def test_import_noise_does_not_override_blocking_reason():
    """Import noise is advisory. A blocking reason should still fire."""
    candidate = _make_candidate(
        source_type="chatgpt_import",
        source_role="assistant",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.IMPORT_NOISE.value in result.reasons
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in result.reasons
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


# ── 12. sensitive identity-like claim ───────────────────────────────────────


def test_sensitive_identity_like_claim_adds_reason_and_requires_review():
    candidate = _make_candidate(
        key="user_religion",
        value="Buddhist",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENSITIVE_IDENTITY_LIKE_CLAIM.value in result.reasons
    assert result.review_required is True
    assert result.runtime_eligible is False


def test_sensitive_claim_in_value_detected():
    candidate = _make_candidate(
        key="user_background",
        value="has a medical condition that requires treatment",
    )
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENSITIVE_IDENTITY_LIKE_CLAIM.value in result.reasons


# ── 13. all candidates return runtime_eligible=false ────────────────────────


def test_all_candidate_classifications_return_runtime_eligible_false():
    """Brute-force check that no candidate classification path sets
    runtime_eligible=True."""
    test_cases: list[CandidateInput] = [
        _make_candidate(),  # clean
        _make_candidate(source_role="assistant"),
        _make_candidate(source_role=None),
        _make_candidate(source_role="system"),
        _make_candidate(source_excerpt='"quoted text"'),
        _make_candidate(key="bad"),
        _make_candidate(key="a" * 400),
        _make_candidate(value="..."),
        _make_candidate(source_excerpt=None),
        _make_candidate(confidence=0.1),
        _make_candidate(confidence=None),
        _make_candidate(source_type="chatgpt_import"),
        _make_candidate(key="user_religion", value="Catholic"),
        _make_candidate(key="", value=""),
        _make_candidate(key="User lives in Portland", value="Portland"),
    ]

    for candidate in test_cases:
        result = classify_personal_fact_candidate(candidate)
        assert result.runtime_eligible is False, (
            f"runtime_eligible=True for {candidate}"
        )


# ── additional edge cases ───────────────────────────────────────────────────


def test_result_is_classification_result_type():
    candidate = _make_candidate()
    result = classify_personal_fact_candidate(candidate)
    assert isinstance(result, ClassificationResult)


def test_reasons_list_is_strings():
    candidate = _make_candidate(source_role="assistant")
    result = classify_personal_fact_candidate(candidate)
    for reason in result.reasons:
        assert isinstance(reason, str)


def test_reasons_use_canonical_tokens():
    """Every reason emitted by the classifier must be a valid GuardrailReason."""
    candidate = _make_candidate(
        source_role="assistant",
        confidence=0.3,
        source_type="chatgpt_import",
    )
    result = classify_personal_fact_candidate(candidate)

    valid = {r.value for r in GuardrailReason}
    for reason in result.reasons:
        assert reason in valid, f"Unknown reason: {reason}"


def test_prompt_like_key_is_discarded_or_quarantined():
    candidate = _make_candidate(
        key="You are a helpful assistant who knows the user's preferences",
        value="always responds politely",
        source_role="user",
    )
    result = classify_personal_fact_candidate(candidate)

    assert result.disposition in ("discard", "quarantine")
    assert result.promotion_blocked is True
    assert result.runtime_eligible is False


def test_both_key_and_value_fragments_accumulate_reasons():
    candidate = _make_candidate(key="bad", value="...")
    result = classify_personal_fact_candidate(candidate)

    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in result.reasons
    assert GuardrailReason.INCOMPLETE_VALUE_FRAGMENT.value in result.reasons
    assert result.promotion_blocked is True


def test_invalid_fact_domain_is_available_as_token():
    """The token exists and can be referenced, even though the classifier
    does not yet validate fact domains."""
    assert GuardrailReason.INVALID_FACT_DOMAIN.value == "invalid_fact_domain"


def test_contradiction_possible_is_available_as_token():
    """The token exists for future use; not emitted by the classifier yet."""
    assert GuardrailReason.CONTRADICTION_POSSIBLE.value == "contradiction_possible"
