"""Explicit, operator-run guardrail metadata backfill for Personal Facts.

This module provides a pure planning seam for backfilling ``guardrail_metadata``
on existing Personal Facts candidate rows that were persisted before the
guardrail classifier was introduced.

It is intentionally free of:
- Database writes
- FastAPI imports
- Redis or network clients
- Model calls
- Frontend or importer entrypoints
- Side effects of any kind

The planning seam is deterministic and unit-testable.  The operator-run
script in ``scripts/personal_facts/backfill_guardrail_metadata.py`` calls
into this module for planning, then applies updates via narrow DB helpers
only when ``--apply`` is passed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from guardian.personal_facts.guardrail_policy import (
    CandidateInput,
    ClassificationResult,
    classify_personal_fact_candidate,
)

logger = logging.getLogger(__name__)

# ── public types ────────────────────────────────────────────────────────────


@dataclass
class BackfillPlan:
    """Output of a single-row backfill planning step."""

    fact_id: int
    eligible: bool = False
    skip_reason: str | None = None
    guardrail_metadata: dict[str, Any] | None = None
    classification: ClassificationResult | None = None


@dataclass
class BackfillSummary:
    """Aggregated summary of a backfill planning run."""

    total_eligible: int = 0
    total_would_update: int = 0
    skipped_already_has_metadata: int = 0
    skipped_not_candidate_like: int = 0
    skipped_malformed: int = 0
    reason_counts: dict[str, int] = field(default_factory=dict)
    plans: list[BackfillPlan] = field(default_factory=list)


# ── candidate-row shape constants ───────────────────────────────────────────

_CANDIDATE_LIKE_STATUSES = frozenset({"candidate", "disputed"})


# ── public planning helpers ─────────────────────────────────────────────────


def build_guardrail_backfill_candidate_input(
    row: dict[str, Any],
) -> CandidateInput | None:
    """Build an immutable CandidateInput from a persisted candidate row.

    Returns None if the row is too malformed to build a useful input.
    """
    try:
        key = str(row.get("key") or "").strip() or None
        value = str(row.get("value") or "").strip() or None
        if not key and not value:
            return None
    except Exception:
        return None

    confidence: float | None = None
    try:
        raw = row.get("confidence")
        if raw is not None:
            confidence = float(raw)
    except (TypeError, ValueError):
        pass

    source_role = _resolve_source_role(row)
    source_type = _resolve_source_type(row)
    source_label = _resolve_source_label(row)
    source_excerpt = _resolve_excerpt(row)

    return CandidateInput(
        key=key,
        value=value,
        confidence=confidence,
        source_role=source_role,
        source_type=source_type,
        source_label=source_label,
        source_excerpt=source_excerpt,
        source_timestamp=_resolve_timestamp(row),
    )


def plan_guardrail_metadata_backfill(
    rows: list[dict[str, Any]],
    *,
    force: bool = False,
) -> BackfillSummary:
    """Produce backfill plans for a list of candidate-like rows.

    Each row should be a dict with at least ``id``, ``key``, ``value``,
    ``status``, and optionally ``guardrail_metadata``, ``source_role``,
    ``source_type``, ``source_label``, ``confidence``, and evidence fields.

    Rows that already carry non-empty ``guardrail_metadata`` are skipped
    unless ``force=True``.
    """
    summary = BackfillSummary()

    for row in rows:
        plan = _plan_single_row(row, force=force)
        summary.plans.append(plan)

        if not plan.eligible:
            if plan.skip_reason == "already_has_metadata":
                summary.skipped_already_has_metadata += 1
            elif plan.skip_reason == "not_candidate_like":
                summary.skipped_not_candidate_like += 1
            elif plan.skip_reason == "malformed":
                summary.skipped_malformed += 1
            continue

        summary.total_eligible += 1

        if plan.guardrail_metadata is None:
            continue

        summary.total_would_update += 1

        if plan.classification is not None:
            for reason in plan.classification.reasons:
                summary.reason_counts[reason] = (
                    summary.reason_counts.get(reason, 0) + 1
                )

    return summary


# ── internal helpers ────────────────────────────────────────────────────────


def _plan_single_row(
    row: dict[str, Any],
    *,
    force: bool = False,
) -> BackfillPlan:
    fact_id = row.get("id")
    if fact_id is None:
        return BackfillPlan(fact_id=0, skip_reason="malformed")

    status = str(row.get("status") or "").strip().lower()

    # ── eligibility gate ────────────────────────────────────────────────
    if status not in _CANDIDATE_LIKE_STATUSES:
        return BackfillPlan(fact_id=fact_id, skip_reason="not_candidate_like")

    # Check for verified/active/archived facts — never backfill these.
    if status in ("verified", "active", "archived"):
        return BackfillPlan(fact_id=fact_id, skip_reason="not_candidate_like")

    # ── existing metadata gate ──────────────────────────────────────────
    existing_meta = row.get("guardrail_metadata")
    if _guardrail_metadata_is_non_empty(existing_meta) and not force:
        return BackfillPlan(
            fact_id=fact_id, skip_reason="already_has_metadata"
        )

    # ── build candidate input ───────────────────────────────────────────
    candidate_input = build_guardrail_backfill_candidate_input(row)
    if candidate_input is None:
        return BackfillPlan(fact_id=fact_id, skip_reason="malformed")

    # ── classify ────────────────────────────────────────────────────────
    classification = classify_personal_fact_candidate(candidate_input)

    # ── build metadata payload ──────────────────────────────────────────
    metadata: dict[str, Any] = {
        "disposition": classification.disposition,
        "reasons": list(classification.reasons),
        "runtime_eligible": False,  # invariant: candidate rows are never runtime-eligible
        "review_required": classification.review_required,
        "promotion_blocked": classification.promotion_blocked,
        # Mark as backfill-derived so operators can distinguish
        # backfilled metadata from import-time classification.
        "backfilled": True,
    }

    return BackfillPlan(
        fact_id=fact_id,
        eligible=True,
        guardrail_metadata=metadata,
        classification=classification,
    )


def _guardrail_metadata_is_non_empty(value: Any) -> bool:
    """Return True if *value* is a dict with at least one key."""
    if not isinstance(value, dict):
        return False
    return len(value) > 0


# ── row-field resolution helpers ────────────────────────────────────────────


def _resolve_source_role(row: dict[str, Any]) -> str | None:
    """Resolve source role from a candidate row.

    Checks multiple possible field names because older rows may encode the
    role in evidence_meta or other nested structures.
    """
    # Direct field on the row (set by newer persistence paths).
    direct = row.get("source_role")
    if direct and str(direct).strip():
        return str(direct).strip().lower()

    # Evidence metadata may carry role information.
    evidence_meta = row.get("evidence_meta")
    if isinstance(evidence_meta, dict):
        role = evidence_meta.get("source_role") or evidence_meta.get("role")
        if role and str(role).strip():
            return str(role).strip().lower()

    return None


def _resolve_source_type(row: dict[str, Any]) -> str | None:
    direct = row.get("source_type")
    if direct and str(direct).strip():
        return str(direct).strip().lower()

    evidence_meta = row.get("evidence_meta")
    if isinstance(evidence_meta, dict):
        st = (
            evidence_meta.get("source_type")
            or evidence_meta.get("import_source")
            or evidence_meta.get("origin")
        )
        if st and str(st).strip():
            return str(st).strip().lower()

    return None


def _resolve_source_label(row: dict[str, Any]) -> str | None:
    direct = row.get("source_label")
    if direct and str(direct).strip():
        return str(direct).strip().lower()

    evidence_meta = row.get("evidence_meta")
    if isinstance(evidence_meta, dict):
        label = (
            evidence_meta.get("source_label")
            or evidence_meta.get("import_source")
        )
        if label and str(label).strip():
            return str(label).strip().lower()

    return None


def _resolve_excerpt(row: dict[str, Any]) -> str | None:
    direct = row.get("source_excerpt") or row.get("excerpt")
    if direct and str(direct).strip():
        return str(direct).strip()

    return None


def _resolve_timestamp(row: dict[str, Any]) -> str | None:
    direct = row.get("source_timestamp") or row.get("created_at")
    if direct:
        try:
            return str(direct)
        except Exception:
            pass
    return None
