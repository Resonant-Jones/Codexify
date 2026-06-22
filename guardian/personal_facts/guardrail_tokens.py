"""Canonical guardrail reason tokens for the Personal Facts candidate lifecycle.

These tokens implement the reason taxonomy from
docs/architecture/personal-facts-guardrails-contract.md.

Any reason label that crosses backend, tests, frontend, API responses,
or docs must live here before implementation spreads it.
"""

from __future__ import annotations

from enum import Enum


class GuardrailReason(str, Enum):
    """Canonical reason labels for Personal Facts candidate classification."""

    # --- Source-role reasons ---
    SOURCE_ROLE_ASSISTANT = "source_role_assistant"
    SOURCE_ROLE_SYSTEM_LIKE = "source_role_system_like"
    SOURCE_ROLE_AMBIGUOUS = "source_role_ambiguous"

    # --- Content-shape reasons ---
    QUOTED_OR_HYPOTHETICAL = "quoted_or_hypothetical"
    SENTENCE_FRAGMENT_KEY = "sentence_fragment_key"
    EXCESSIVE_KEY_LENGTH = "excessive_key_length"
    INVALID_FACT_DOMAIN = "invalid_fact_domain"
    INCOMPLETE_VALUE_FRAGMENT = "incomplete_value_fragment"

    # --- Lifecycle reasons ---
    STALE_OR_TIME_SENSITIVE = "stale_or_time_sensitive"
    CONTRADICTION_POSSIBLE = "contradiction_possible"
    SENSITIVE_IDENTITY_LIKE_CLAIM = "sensitive_identity_like_claim"

    # --- Evidence reasons ---
    MISSING_EVIDENCE = "missing_evidence"
    LOW_CONFIDENCE = "low_confidence"

    # --- Import reasons ---
    IMPORT_NOISE = "import_noise"

    # --- Review posture ---
    USER_REVIEW_REQUIRED = "user_review_required"
