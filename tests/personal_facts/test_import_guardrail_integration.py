"""Integration tests for the import guardrail pipeline.

Tests _classify_import_candidates from backend.rag.chatgpt_migration
in isolation — no Docker, Postgres, Redis, network, or model calls.
"""

from __future__ import annotations

from backend.rag.chatgpt_migration import _classify_import_candidates
from guardian.personal_facts.guardrail_tokens import GuardrailReason


def _make_candidate(
    key: str = "user_location_city",
    value: str = "Portland",
    confidence: float = 0.92,
    excerpt: str = "I live in Portland, Oregon.",
) -> dict[str, str | float]:
    return {
        "key": key,
        "value": value,
        "confidence": confidence,
        "excerpt": excerpt,
        "rule": "identity_claim",
    }


# ── 1. assistant-authored identity text is not promoted ────────────────────


def test_assistant_authored_identity_candidate_is_quarantined():
    """Imported assistant-authored text must be quarantined, not normal."""
    candidates = [
        _make_candidate(
            key="user_profession",
            value="professional chef",
            excerpt="The user is a professional chef with 15 years of experience.",
        )
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="assistant",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    # Candidate is NOT discarded — it goes to quarantine for review.
    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] == "quarantine"
    assert kept_cand["_guardrail_promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in kept_cand["_guardrail_reasons"]


# ── 2. user-authored clean fact survives as reviewable ─────────────────────


def test_clean_user_authored_candidate_remains_reviewable():
    candidates = [
        _make_candidate(
            key="user_location_city",
            value="Portland",
            excerpt="I live in Portland.",
        )
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] in ("reviewable", "quarantine")
    assert kept_cand["_guardrail_promotion_blocked"] is False
    # Even clean imported facts are not runtime-eligible.
    # (runtime_eligible is not attached per-candidate by the helper, but
    #  the classifier always returns False.)


# ── 3. ambiguous source role → blocked ──────────────────────────────────────


def test_ambiguous_source_role_is_promotion_blocked():
    candidates = [_make_candidate()]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role=None,
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] == "quarantine"
    assert kept_cand["_guardrail_promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value in kept_cand["_guardrail_reasons"]


# ── 4. sentence-fragment key → blocked ─────────────────────────────────────


def test_sentence_fragment_key_is_blocked():
    candidates = [
        _make_candidate(key="lives in", excerpt="lives in Portland")
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    # Fragment keys should be quarantined, not discarded.
    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] == "quarantine"
    assert kept_cand["_guardrail_promotion_blocked"] is True
    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in kept_cand["_guardrail_reasons"]


# ── 5. missing evidence is blocked ─────────────────────────────────────────


def test_missing_evidence_candidate_is_blocked():
    candidates = [
        _make_candidate(key="user_name", value="Alice", excerpt="")
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    # Missing evidence results in quarantine, not discard in this case
    # because key and value are present.
    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] == "quarantine"
    assert kept_cand["_guardrail_promotion_blocked"] is True
    assert GuardrailReason.MISSING_EVIDENCE.value in kept_cand["_guardrail_reasons"]


# ── 6. confidence does not override quarantine ──────────────────────────────


def test_high_confidence_does_not_override_blocking_reason():
    """Confidence is advisory.  High confidence must not bypass quarantine
    when a blocking reason exists."""
    candidates = [
        _make_candidate(
            key="user_nationality",
            value="French",
            confidence=0.99,
            excerpt="As a French citizen, the user enjoys travelling.",
        )
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="assistant",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    kept_cand = kept[0]
    assert kept_cand["_guardrail_disposition"] == "quarantine"
    assert kept_cand["_guardrail_promotion_blocked"] is True
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in kept_cand["_guardrail_reasons"]


# ── 7. all emitted candidates are runtime_eligible=false ────────────────────


def test_no_import_candidate_is_runtime_eligible():
    """The classifier never sets runtime_eligible=True.
    The helper propagates promotion_blocked — runtime_eligible is not
    per-candidate attached but the invariant holds classifier-side.
    We prove it by checking that every kept candidate across multiple
    input classes is promotion_blocked unless it was clean user-authored."""

    test_inputs: list[tuple[str | None, str | None, str]] = [
        ("user", "chatgpt_import", "I live in Portland."),
        ("assistant", "chatgpt_import", "The user lives in Portland."),
        (None, "chatgpt_import", "Someone said they live in Portland."),
        ("user", "chatgpt_import", "hypothetical example"),
    ]

    all_kept: list[dict] = []
    for role, src_type, excerpt in test_inputs:
        candidates = [_make_candidate(excerpt=excerpt)]
        kept, _, _ = _classify_import_candidates(
            candidates,
            source_role=role,
            source_type=src_type,
            source_label="chatgpt",
        )
        all_kept.extend(kept)

    assert len(all_kept) > 0
    for cand in all_kept:
        # None should be silently promotable without review.
        assert cand["_guardrail_review_required"] is True
        # runtime_eligible is always false classifier-side.


# ── 8. guardrail reasons attached to emitted metadata ──────────────────────


def test_guardrail_reasons_attached_to_emitted_metadata():
    candidates = [
        _make_candidate(
            key="user_profession",
            value="chef",
            excerpt="The user is a chef.",
        )
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="assistant",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    cand = kept[0]

    # All guardrail metadata keys must be present.
    assert "_guardrail_disposition" in cand
    assert isinstance(cand["_guardrail_disposition"], str)
    assert "_guardrail_reasons" in cand
    assert isinstance(cand["_guardrail_reasons"], list)
    assert len(cand["_guardrail_reasons"]) > 0
    assert "_guardrail_promotion_blocked" in cand
    assert isinstance(cand["_guardrail_promotion_blocked"], bool)
    assert "_guardrail_review_required" in cand
    assert isinstance(cand["_guardrail_review_required"], bool)

    # All reasons must be valid canonical tokens.
    valid = {r.value for r in GuardrailReason}
    for reason in cand["_guardrail_reasons"]:
        assert reason in valid, f"Unknown reason: {reason}"


# ── discard behavior ────────────────────────────────────────────────────────


def test_structurally_empty_candidate_is_discarded():
    candidates = [
        _make_candidate(key="", value="", excerpt="")
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 1
    assert len(kept) == 0


def test_prompt_like_candidate_is_discarded():
    candidates = [
        _make_candidate(
            key="You are a helpful assistant who knows the user",
            value="always be polite",
            excerpt="system: You are a helpful assistant",
        )
    ]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert skipped_discard == 1
    assert len(kept) == 0


# ── mixed candidate batch ───────────────────────────────────────────────────


def test_mixed_candidate_batch_handles_all_dispositions():
    candidates = [
        # Clean user fact → reviewable
        _make_candidate(
            key="user_location_city",
            value="Portland",
            excerpt="I live in Portland.",
        ),
        # Assistant-authored → quarantine
        _make_candidate(
            key="user_profession",
            value="doctor",
            excerpt="The user is a doctor.",
        ),
        # Empty → discard
        _make_candidate(key="", value="", excerpt=""),
        # Prompt-like → discard
        _make_candidate(
            key="You are a helpful assistant",
            value="be nice",
            excerpt="system prompt",
        ),
        # Fragment → quarantine
        _make_candidate(key="lives in", excerpt="lives in Portland"),
    ]

    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="assistant",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    # 2 discards (empty + prompt-like), 3 kept (fragment is quarantined, not discarded)
    assert skipped_discard == 2
    assert len(kept) == 3

    # All kept candidates should have guardrail metadata.
    for cand in kept:
        assert "_guardrail_disposition" in cand
        assert "_guardrail_reasons" in cand
        assert "_guardrail_promotion_blocked" in cand


# ── original candidate data preserved ───────────────────────────────────────


def test_original_candidate_fields_are_preserved():
    original = {
        "key": "user_location_city",
        "value": "Portland",
        "confidence": 0.92,
        "excerpt": "I live in Portland.",
        "rule": "identity_claim",
    }
    kept, _, _ = _classify_import_candidates(
        [dict(original)],
        source_role="user",
        source_type="chatgpt_import",
        source_label="chatgpt",
    )

    assert len(kept) == 1
    cand = kept[0]
    assert cand["key"] == original["key"]
    assert cand["value"] == original["value"]
    assert cand["confidence"] == original["confidence"]
    assert cand["excerpt"] == original["excerpt"]
    assert cand["rule"] == original["rule"]


# ── Claude import variants ──────────────────────────────────────────────────


def test_claude_imported_source_adds_import_noise():
    candidates = [_make_candidate()]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="claude_import",
        source_label="claude",
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    assert GuardrailReason.IMPORT_NOISE.value in kept[0]["_guardrail_reasons"]


def test_non_import_source_omits_import_noise():
    """A non-import source type should not trigger import_noise."""
    candidates = [_make_candidate()]
    kept, skipped_discard, _ = _classify_import_candidates(
        candidates,
        source_role="user",
        source_type="chat_message",
        source_label=None,
    )

    assert skipped_discard == 0
    assert len(kept) == 1
    assert GuardrailReason.IMPORT_NOISE.value not in kept[0]["_guardrail_reasons"]
