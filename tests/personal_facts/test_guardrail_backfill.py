"""Tests for the Personal Facts guardrail metadata backfill planning seam.

These tests focus on the pure planning helpers in
``guardian/personal_facts/guardrail_backfill.py``.  No Docker, Postgres,
Redis, network, model calls, or frontend runtime required.
"""

from __future__ import annotations

import pytest

from guardian.personal_facts.guardrail_backfill import (
    BackfillPlan,
    BackfillSummary,
    build_guardrail_backfill_candidate_input,
    plan_guardrail_metadata_backfill,
)
from guardian.personal_facts.guardrail_tokens import GuardrailReason


# ── row builders ────────────────────────────────────────────────────────────


def _candidate_row(**overrides) -> dict:
    """Build a minimal candidate-like row dict with sensible defaults."""
    defaults: dict = {
        "id": 1,
        "user_id": "local",
        "key": "user_location_city",
        "value": "Portland",
        "status": "candidate",
        "confidence": 0.92,
        "is_active": True,
        "guardrail_metadata": None,
        "source_role": "user",
        "source_type": "chat_message",
        "source_label": None,
        "source_excerpt": "I live in Portland, Oregon.",
        "created_at": "2026-06-20T12:00:00Z",
    }
    defaults.update(overrides)
    return defaults


def _disputed_row(**overrides) -> dict:
    defaults = _candidate_row(status="disputed", **overrides)
    return defaults


def _verified_row(**overrides) -> dict:
    defaults = _candidate_row(status="verified", **overrides)
    return defaults


def _active_row(**overrides) -> dict:
    defaults = _candidate_row(status="active", **overrides)
    return defaults


def _archived_row(**overrides) -> dict:
    defaults = _candidate_row(status="archived", **overrides)
    return defaults


# ── 1. Candidate row without guardrail_metadata receives an update plan ─────


def test_candidate_without_metadata_gets_update_plan():
    rows = [_candidate_row(guardrail_metadata=None)]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    assert summary.total_would_update == 1
    assert summary.skipped_already_has_metadata == 0
    assert summary.skipped_not_candidate_like == 0

    plan = summary.plans[0]
    assert plan.eligible is True
    assert plan.guardrail_metadata is not None
    assert plan.guardrail_metadata["runtime_eligible"] is False
    assert plan.guardrail_metadata["backfilled"] is True
    assert isinstance(plan.guardrail_metadata["disposition"], str)
    assert isinstance(plan.guardrail_metadata["reasons"], list)
    assert isinstance(plan.guardrail_metadata["promotion_blocked"], bool)
    assert isinstance(plan.guardrail_metadata["review_required"], bool)


# ── 2. Candidate row with existing guardrail_metadata is skipped by default ─


def test_candidate_with_existing_metadata_is_skipped():
    existing_meta = {
        "disposition": "reviewable",
        "reasons": [],
        "runtime_eligible": False,
        "promotion_blocked": False,
        "review_required": True,
    }
    rows = [_candidate_row(guardrail_metadata=existing_meta)]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 0
    assert summary.skipped_already_has_metadata == 1
    assert summary.total_would_update == 0

    plan = summary.plans[0]
    assert plan.eligible is False
    assert plan.skip_reason == "already_has_metadata"


def test_candidate_with_existing_metadata_is_overwritten_with_force():
    existing_meta = {
        "disposition": "reviewable",
        "reasons": [],
        "runtime_eligible": False,
    }
    rows = [_candidate_row(guardrail_metadata=existing_meta)]
    summary = plan_guardrail_metadata_backfill(rows, force=True)

    assert summary.total_eligible == 1
    assert summary.total_would_update == 1
    assert summary.skipped_already_has_metadata == 0


# ── 3. Verified/active/runtime fact is skipped and not reclassified ─────────


@pytest.mark.parametrize(
    "row",
    [
        _verified_row(),
        _active_row(),
        _archived_row(guardrail_metadata=None),
    ],
)
def test_non_candidate_fact_is_skipped(row: dict):
    summary = plan_guardrail_metadata_backfill([row])

    assert summary.total_eligible == 0
    assert summary.skipped_not_candidate_like == 1
    assert summary.total_would_update == 0

    plan = summary.plans[0]
    assert plan.eligible is False
    assert plan.skip_reason == "not_candidate_like"
    assert plan.guardrail_metadata is None


# ── 4. Ambiguous source role → source_role_ambiguous, promotion_blocked ─────


def test_ambiguous_source_role_produces_source_role_ambiguous():
    rows = [
        _candidate_row(
            guardrail_metadata=None,
            source_role=None,
            source_type=None,
            source_label=None,
            source_excerpt="Some text without role information.",
        )
    ]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None
    assert GuardrailReason.SOURCE_ROLE_AMBIGUOUS.value in plan.guardrail_metadata["reasons"]
    assert plan.guardrail_metadata["promotion_blocked"] is True


# ── 5. Missing evidence → missing_evidence, promotion_blocked ───────────────


def test_missing_evidence_produces_missing_evidence():
    rows = [
        _candidate_row(
            guardrail_metadata=None,
            source_role="user",
            source_excerpt=None,
            source_type=None,
        )
    ]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None
    assert GuardrailReason.MISSING_EVIDENCE.value in plan.guardrail_metadata["reasons"]
    assert plan.guardrail_metadata["promotion_blocked"] is True


# ── 6. Assistant-authored → source_role_assistant, promotion_blocked ────────


def test_assistant_authored_source_role_produces_source_role_assistant():
    rows = [
        _candidate_row(
            guardrail_metadata=None,
            source_role="assistant",
            key="user_profession",
            value="professional chef",
            source_excerpt="The user is a professional chef with 15 years of experience.",
        )
    ]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None
    assert GuardrailReason.SOURCE_ROLE_ASSISTANT.value in plan.guardrail_metadata["reasons"]
    assert plan.guardrail_metadata["promotion_blocked"] is True


# ── 7. Sentence-fragment key → sentence_fragment_key behavior ───────────────


def test_sentence_fragment_key_produces_sentence_fragment_key():
    rows = [
        _candidate_row(
            guardrail_metadata=None,
            key="lives in",
            value="Portland",
            source_role="user",
        )
    ]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None
    assert GuardrailReason.SENTENCE_FRAGMENT_KEY.value in plan.guardrail_metadata["reasons"]
    assert plan.guardrail_metadata["promotion_blocked"] is True


# ── 8. Backfill plan never sets runtime_eligible=true ───────────────────────


def test_backfill_plan_never_sets_runtime_eligible_true():
    test_rows = [
        _candidate_row(
            guardrail_metadata=None,
            source_role="user",
            key="user_location_city",
            value="Portland",
            source_excerpt="I live in Portland.",
            source_type="chat_message",
        ),
        _candidate_row(
            guardrail_metadata=None,
            source_role="assistant",
            key="user_profession",
            value="chef",
            source_excerpt="The user is a chef.",
        ),
        _candidate_row(
            guardrail_metadata=None,
            source_role=None,
            key="user_hobby",
            value="painting",
        ),
        _disputed_row(guardrail_metadata=None, source_role="user"),
    ]

    summary = plan_guardrail_metadata_backfill(test_rows)
    for plan in summary.plans:
        if plan.eligible and plan.guardrail_metadata is not None:
            assert plan.guardrail_metadata["runtime_eligible"] is False, (
                f"runtime_eligible=True for fact_id={plan.fact_id}"
            )


# ── 9. Backfill plan does not alter key, value, status, confidence, evidence ─


def test_backfill_plan_does_not_include_mutable_fields_in_metadata():
    """The guardrail_metadata payload must not carry key/value/status/confidence."""
    rows = [_candidate_row(guardrail_metadata=None)]
    summary = plan_guardrail_metadata_backfill(rows)

    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None

    forbidden_keys = {"key", "value", "status", "confidence", "evidence", "source"}
    for key in forbidden_keys:
        assert key not in plan.guardrail_metadata, (
            f"guardrail_metadata must not contain '{key}'"
        )


# ── 10. Dry-run summary aggregates correctly ────────────────────────────────


def test_dry_run_summary_aggregates_deterministically():
    rows = [
        _candidate_row(id=1, guardrail_metadata=None),
        _candidate_row(id=2, guardrail_metadata={"disposition": "reviewable"}),
        _verified_row(id=3, guardrail_metadata=None),
        _archived_row(id=4, guardrail_metadata=None),
        _candidate_row(
            id=5,
            guardrail_metadata=None,
            source_role="assistant",
            key="user_profession",
            value="chef",
        ),
    ]

    summary = plan_guardrail_metadata_backfill(rows)

    # Eligible: row 1 (clean candidate) + row 5 (assistant candidate) = 2
    assert summary.total_eligible == 2
    # Would update: both eligible rows have metadata = 2
    assert summary.total_would_update == 2
    # Skipped already has: row 2 = 1
    assert summary.skipped_already_has_metadata == 1
    # Skipped not candidate-like: row 3 (verified) + row 4 (archived) = 2
    assert summary.skipped_not_candidate_like == 2
    # Malformed: 0
    assert summary.skipped_malformed == 0

    # Reason count: row 1 (user-authored, clean) → no reasons (reviewable)
    # Row 5 (assistant) → source_role_assistant
    assert summary.reason_counts.get(GuardrailReason.SOURCE_ROLE_ASSISTANT.value, 0) >= 1


# ── 11. Malformed input row does not crash planning, fails closed ───────────


def test_malformed_row_is_skipped_with_reason():
    rows: list[dict] = [
        {},  # no id, no key, no value
        {"id": 99, "status": "candidate", "guardrail_metadata": None},  # no key/value
    ]

    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.skipped_malformed == 2
    assert summary.total_eligible == 0
    assert summary.total_would_update == 0

    for plan in summary.plans:
        assert plan.eligible is False
        assert plan.guardrail_metadata is None


def test_missing_id_row_is_skipped():
    rows = [
        _candidate_row(id=None, guardrail_metadata=None),  # type: ignore[arg-type]
    ]
    summary = plan_guardrail_metadata_backfill(rows)
    assert summary.skipped_malformed == 1


# ── 12. Disputed facts are eligible for backfill ────────────────────────────


def test_disputed_fact_without_metadata_is_eligible():
    rows = [_disputed_row(guardrail_metadata=None)]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.total_eligible == 1
    plan = summary.plans[0]
    assert plan.eligible is True
    assert plan.guardrail_metadata is not None


# ── build_guardrail_backfill_candidate_input ────────────────────────────────


def test_build_candidate_input_from_row_extracts_fields():
    row = _candidate_row(
        key="user_location_city",
        value="Portland",
        confidence=0.92,
        source_role="user",
        source_type="chat_message",
        source_label=None,
        source_excerpt="I live in Portland.",
    )
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is not None
    assert ci.key == "user_location_city"
    assert ci.value == "Portland"
    assert ci.confidence == 0.92
    assert ci.source_role == "user"
    assert ci.source_type == "chat_message"
    assert ci.source_excerpt == "I live in Portland."


def test_build_candidate_input_resolves_role_from_evidence_meta():
    row = _candidate_row(
        source_role=None,
        source_type=None,
        evidence_meta={
            "source_role": "user",
            "import_source": "chatgpt_import",
        },
    )
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is not None
    assert ci.source_role == "user"
    assert ci.source_type == "chatgpt_import"
    assert ci.source_label == "chatgpt_import"


def test_build_candidate_input_returns_none_for_empty_row():
    row = {"key": "", "value": ""}
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is None


def test_build_candidate_input_handles_missing_confidence():
    row = _candidate_row(confidence=None)
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is not None
    assert ci.confidence is None


# ── BackfillPlan dataclass shape ────────────────────────────────────────────


def test_backfill_plan_dataclass_shape():
    plan = BackfillPlan(
        fact_id=42,
        eligible=True,
        guardrail_metadata={"disposition": "reviewable"},
    )
    assert plan.fact_id == 42
    assert plan.eligible is True
    assert plan.skip_reason is None
    assert plan.guardrail_metadata is not None


def test_backfill_summary_dataclass_shape():
    summary = BackfillSummary(
        total_eligible=5,
        total_would_update=5,
        skipped_already_has_metadata=2,
        skipped_not_candidate_like=3,
        skipped_malformed=1,
        reason_counts={"source_role_assistant": 2, "missing_evidence": 1},
    )
    assert summary.total_eligible == 5
    assert summary.skipped_already_has_metadata == 2
    assert summary.reason_counts["source_role_assistant"] == 2


# ── Import-aware source type → import_noise ─────────────────────────────────


def test_imported_source_type_produces_import_noise():
    rows = [
        _candidate_row(
            guardrail_metadata=None,
            source_role="user",
            source_type="chatgpt_import",
            source_label="chatgpt_import",
        )
    ]
    summary = plan_guardrail_metadata_backfill(rows)
    plan = summary.plans[0]
    assert plan.guardrail_metadata is not None
    assert GuardrailReason.IMPORT_NOISE.value in plan.guardrail_metadata["reasons"]


# ── force flag is reflected in all plans ───────────────────────────────────


def test_force_flag_updates_rows_with_existing_metadata():
    rows = [
        _candidate_row(id=1, guardrail_metadata={"disposition": "quarantine", "reasons": ["old_reason"]}),
        _candidate_row(id=2, guardrail_metadata=None),
    ]
    summary = plan_guardrail_metadata_backfill(rows, force=True)

    # Both should be eligible with force.
    assert summary.total_eligible == 2
    assert summary.total_would_update == 2
    assert summary.skipped_already_has_metadata == 0


# ── disputed row with existing metadata is skipped by default ───────────────


def test_disputed_with_existing_metadata_skipped():
    existing = {"disposition": "quarantine", "reasons": ["test"]}
    rows = [_disputed_row(guardrail_metadata=existing)]
    summary = plan_guardrail_metadata_backfill(rows)

    assert summary.skipped_already_has_metadata == 1
    assert summary.total_eligible == 0


# ── evidence_meta fallback for source_role ──────────────────────────────────


def test_source_role_resolved_from_evidence_meta_role_field():
    row = _candidate_row(
        source_role=None,
        evidence_meta={"role": "assistant", "import_source": "chatgpt_import"},
    )
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is not None
    assert ci.source_role == "assistant"


def test_source_type_resolved_from_evidence_meta_origin():
    row = _candidate_row(
        source_type=None,
        source_label=None,
        evidence_meta={"origin": "chatgpt_import"},
    )
    ci = build_guardrail_backfill_candidate_input(row)
    assert ci is not None
    assert ci.source_type == "chatgpt_import"
