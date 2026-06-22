"""Tests for Personal Facts guardrail metadata persistence.

Tests the _extract_guardrail_metadata helper and verifies that classified
candidates produce correct guardrail_metadata payloads for the create_fact
boundary.  No Docker, Postgres, Redis, network, or model calls required.
"""

from __future__ import annotations

from backend.rag.personal_fact_extraction import _extract_guardrail_metadata
from guardian.personal_facts.guardrail_tokens import GuardrailReason


# ── 1. clean user-authored → reviewable, runtime_eligible=false ─────────────


def test_clean_user_candidate_metadata_is_reviewable_not_runtime_eligible():
    candidate = {
        "key": "user_location_city",
        "value": "Portland",
        "confidence": 0.92,
        "excerpt": "I live in Portland.",
        "_guardrail_disposition": "reviewable",
        "_guardrail_reasons": ["import_noise"],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": False,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert meta["disposition"] == "reviewable"
    assert meta["runtime_eligible"] is False
    assert meta["promotion_blocked"] is False
    assert meta["review_required"] is True


# ── 2. assistant-authored → source_role_assistant, promotion_blocked=true ──


def test_assistant_authored_candidate_metadata_has_source_role_assistant():
    candidate = {
        "key": "user_profession",
        "value": "chef",
        "confidence": 0.85,
        "excerpt": "The user is a professional chef.",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": [
            GuardrailReason.SOURCE_ROLE_ASSISTANT.value,
            GuardrailReason.IMPORT_NOISE.value,
        ],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert meta["disposition"] == "quarantine"
    assert meta["promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in meta["reasons"]
    assert GuardrailReason.IMPORT_NOISE.value in meta["reasons"]
    assert meta["runtime_eligible"] is False


# ── 3. ambiguous-role → source_role_ambiguous, promotion_blocked=true ────────


def test_ambiguous_role_candidate_metadata_has_source_role_ambiguous():
    candidate = {
        "key": "user_hobby",
        "value": "painting",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": [
            GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value,
            GuardrailReason.IMPORT_NOISE.value,
        ],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert meta["disposition"] == "quarantine"
    assert meta["promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value in meta["reasons"]


# ── 4. sentence-fragment → contains sentence_fragment_key ────────────────────


def test_sentence_fragment_candidate_metadata_has_sentence_fragment_key():
    candidate = {
        "key": "lives in",
        "value": "Portland",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": [
            GuardrailReason.SENTENCE_FRAGMENT_KEY.value,
            GuardrailReason.IMPORT_NOISE.value,
        ],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in meta["reasons"]
    assert meta["promotion_blocked"] is True
    assert meta["runtime_eligible"] is False


# ── 5. canonical reason token values preserved ──────────────────────────────


def test_canonical_reason_token_values_are_preserved_exactly():
    reasons = [
        GuardrailReason.SOURCE_ROLE_ASSISTANT.value,
        GuardrailReason.SENTENCE_FRAGMENT_KEY.value,
        GuardrailReason.LOW_CONFIDENCE.value,
        GuardrailReason.IMPORT_NOISE.value,
        GuardrailReason.MISSING_EVIDENCE.value,
    ]
    candidate = {
        "key": "user_test",
        "value": "test",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": list(reasons),
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert meta["reasons"] == reasons


# ── 6. runtime_eligible is always false ─────────────────────────────────────


def test_guardrail_metadata_never_marks_runtime_eligible():
    test_cases: list[dict] = [
        {
            "_guardrail_disposition": "reviewable",
            "_guardrail_reasons": [],
            "_guardrail_review_required": True,
            "_guardrail_promotion_blocked": False,
        },
        {
            "_guardrail_disposition": "quarantine",
            "_guardrail_reasons": ["source_role_assistant"],
            "_guardrail_review_required": True,
            "_guardrail_promotion_blocked": True,
        },
        {
            "_guardrail_disposition": "quarantine",
            "_guardrail_reasons": ["low_confidence"],
            "_guardrail_review_required": True,
            "_guardrail_promotion_blocked": False,
        },
        {
            "_guardrail_disposition": "reviewable",
            "_guardrail_reasons": ["import_noise"],
            "_guardrail_review_required": True,
            "_guardrail_promotion_blocked": False,
        },
    ]

    for candidate in test_cases:
        meta = _extract_guardrail_metadata(candidate)
        assert meta is not None
        assert meta["runtime_eligible"] is False, (
            f"runtime_eligible=True for {candidate['_guardrail_disposition']}"
        )


# ── 7. confidence does not override guardrail metadata ─────────────────────


def test_confidence_does_not_erase_guardrail_metadata():
    candidate = {
        "key": "user_nationality",
        "value": "French",
        "confidence": 0.99,
        "excerpt": "As a French citizen...",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": [GuardrailReason.SOURCE_ROLE_ASSISTANT.value],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    # High confidence does not erase the quarantine metadata.
    assert meta["disposition"] == "quarantine"
    assert meta["promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in meta["reasons"]
    assert meta["runtime_eligible"] is False


# ── 8. missing guardrail data returns None ──────────────────────────────────


def test_missing_guardrail_data_returns_none():
    candidate = {
        "key": "user_location",
        "value": "nowhere",
    }
    meta = _extract_guardrail_metadata(candidate)
    assert meta is None


def test_no_disposition_returns_none():
    candidate = {
        "key": "test",
        "value": "test",
        "_guardrail_reasons": ["some_reason"],
    }
    meta = _extract_guardrail_metadata(candidate)
    assert meta is None


# ── shape and type assertions ────────────────────────────────────────────────


def test_guardrail_metadata_has_correct_shape():
    candidate = {
        "key": "user_test",
        "value": "test_value",
        "_guardrail_disposition": "quarantine",
        "_guardrail_reasons": [
            GuardrailReason.SOURCE_ROLE_ASSISTANT.value,
            GuardrailReason.IMPORT_NOISE.value,
        ],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": True,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert isinstance(meta["disposition"], str)
    assert isinstance(meta["reasons"], list)
    assert isinstance(meta["runtime_eligible"], bool)
    assert isinstance(meta["review_required"], bool)
    assert isinstance(meta["promotion_blocked"], bool)


def test_empty_reasons_are_preserved():
    candidate = {
        "key": "user_test",
        "value": "test",
        "_guardrail_disposition": "reviewable",
        "_guardrail_reasons": [],
        "_guardrail_review_required": True,
        "_guardrail_promotion_blocked": False,
    }

    meta = _extract_guardrail_metadata(candidate)
    assert meta is not None
    assert meta["reasons"] == []
    assert meta["disposition"] == "reviewable"
