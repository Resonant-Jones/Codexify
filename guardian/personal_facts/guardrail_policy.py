"""Pure Personal Facts guardrail classifier — no side effects, no integrations.

This module implements the candidate classification rules from
docs/architecture/personal-facts-guardrails-contract.md.

It is intentionally free of:
- Database imports
- FastAPI imports
- Extractor imports
- Network calls
- Model calls
- Side effects
"""

from __future__ import annotations

from dataclasses import dataclass, field

from guardian.personal_facts.guardrail_tokens import GuardrailReason

# ── conservative thresholds ────────────────────────────────────────────────
_CONFIDENCE_LOW_THRESHOLD = 0.5
_MAX_KEY_LENGTH = 300
_SYSTEM_LIKE_ROLES = frozenset({"system", "developer", "tool"})
_IMPORT_SOURCE_TYPES = frozenset({"chatgpt_import", "claude_import"})
_IMPORT_SOURCE_LABELS = frozenset(
    {"chatgpt_import", "claude_import", "openai_export", "chatgpt"}
)
_HYPOTHETICAL_MARKERS = (
    "for example",
    "imagine if",
    "suppose",
    "what if",
    "for instance",
    "as an example",
    "say you",
    "let's say",
)
_QUOTED_MARKERS = ('"', '"', "'", "'", "\u201c", "\u201d", "\u2018", "\u2019")
_SENSITIVE_IDENTITY_PATTERNS = (
    "race",
    "ethnicity",
    "religion",
    "sexual orientation",
    "gender identity",
    "political affiliation",
    "medical condition",
    "health condition",
    "disability",
    "age is",
    "born in",
    "social security",
    "passport number",
    "credit card",
)
_PROMPT_LIKE_PREFIXES = (
    "you are",
    "you're a",
    "you are a",
    "act as",
    "you should",
    "you must",
    "i want you to",
    "please respond",
    "your role is",
    "system:",
    "assistant:",
)


# ── public types ────────────────────────────────────────────────────────────


@dataclass
class CandidateInput:
    """Input shape for candidate classification.

    All fields are optional because extraction may produce partial records.
    """

    key: str | None = None
    value: str | None = None
    confidence: float | None = None
    source_role: str | None = None
    source_type: str | None = None
    source_label: str | None = None
    source_excerpt: str | None = None
    source_timestamp: str | None = None


@dataclass
class ClassificationResult:
    """Output shape for candidate classification."""

    disposition: str = "reviewable"
    reasons: list[str] = field(default_factory=list)
    runtime_eligible: bool = False
    review_required: bool = True
    promotion_blocked: bool = False


# ── pure classification ─────────────────────────────────────────────────────


def classify_personal_fact_candidate(
    candidate: CandidateInput,
) -> ClassificationResult:
    """Classify a personal fact candidate without side effects.

    Returns a ClassificationResult with disposition, reasons, and
    eligibility flags.  This function never sets runtime_eligible=True
    because verified runtime eligibility is out of scope for candidate
    classification — only the verified-active lifecycle gate can grant it.
    """
    result = ClassificationResult()

    _check_source_role(candidate, result)
    _check_evidence(candidate, result)
    _check_shape(candidate, result)
    _check_content_flags(candidate, result)
    _check_import_noise(candidate, result)
    _check_confidence(candidate, result)
    _check_sensitive_claim(candidate, result)

    # After all checks, compute disposition and review posture.
    result.review_required = (
        len(result.reasons) > 0 or result.disposition != "discard"
    )

    if result.disposition == "discard":
        pass  # already terminal
    elif result.promotion_blocked:
        result.disposition = "quarantine"
    elif any(
        r in result.reasons
        for r in (
            GuardrailReason.LOW_CONFIDENCE.value,
            GuardrailReason.IMPORT_NOISE.value,
            GuardrailReason.SENSITIVE_IDENTITY_LIKE_CLAIM.value,
        )
    ):
        result.disposition = "quarantine"
    elif not result.reasons:
        result.disposition = "reviewable"
        result.review_required = True
    else:
        result.disposition = "reviewable"

    result.runtime_eligible = False
    return result


# ── internal check helpers ──────────────────────────────────────────────────


def _check_source_role(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    role = (candidate.source_role or "").strip().lower()

    if not role:
        _add_reason(result, GuardrailReason.SOURCE_ROLE_AMBIGUOUS, block=True)
        return

    if role == "assistant":
        _add_reason(result, GuardrailReason.SOURCE_ROLE_ASSISTANT, block=True)
    elif role in _SYSTEM_LIKE_ROLES:
        _add_reason(
            result, GuardrailReason.SOURCE_ROLE_SYSTEM_LIKE, block=True
        )
    elif role not in ("user",):
        _add_reason(result, GuardrailReason.SOURCE_ROLE_AMBIGUOUS, block=True)


def _check_evidence(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    key = (candidate.key or "").strip()
    value = (candidate.value or "").strip()
    excerpt = (candidate.source_excerpt or "").strip()

    if not key and not value:
        result.disposition = "discard"
        _add_reason(result, GuardrailReason.MISSING_EVIDENCE, block=True)
        return

    if not excerpt:
        _add_reason(result, GuardrailReason.MISSING_EVIDENCE, block=True)


def _check_shape(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    key = (candidate.key or "").strip()
    value = (candidate.value or "").strip()

    # ── key checks ──
    if not key:
        _add_reason(
            result, GuardrailReason.SENTENCE_FRAGMENT_KEY, block=True
        )
    elif len(key) > _MAX_KEY_LENGTH:
        _add_reason(result, GuardrailReason.EXCESSIVE_KEY_LENGTH, block=True)
    elif _is_prompt_like(key):
        result.disposition = "discard"
        _add_reason(
            result, GuardrailReason.SENTENCE_FRAGMENT_KEY, block=True
        )
        return
    elif _is_sentence_fragment(key):
        _add_reason(
            result, GuardrailReason.SENTENCE_FRAGMENT_KEY, block=True
        )

    # ── value checks ──
    if not value:
        _add_reason(
            result, GuardrailReason.INCOMPLETE_VALUE_FRAGMENT, block=True
        )
    elif _is_incomplete_fragment(value):
        _add_reason(
            result, GuardrailReason.INCOMPLETE_VALUE_FRAGMENT, block=True
        )


def _check_content_flags(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    excerpt = (candidate.source_excerpt or "").strip().lower()

    if not excerpt:
        return

    if _is_quoted_or_hypothetical(excerpt):
        _add_reason(
            result, GuardrailReason.QUOTED_OR_HYPOTHETICAL, block=True
        )


def _check_import_noise(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    source_type = (candidate.source_type or "").strip().lower()
    source_label = (candidate.source_label or "").strip().lower()

    is_imported = (
        source_type in _IMPORT_SOURCE_TYPES
        or source_label in _IMPORT_SOURCE_LABELS
    )

    if is_imported:
        _add_reason(result, GuardrailReason.IMPORT_NOISE, block=False)


def _check_confidence(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    if candidate.confidence is None:
        _add_reason(result, GuardrailReason.LOW_CONFIDENCE, block=False)
        return

    if candidate.confidence < _CONFIDENCE_LOW_THRESHOLD:
        _add_reason(result, GuardrailReason.LOW_CONFIDENCE, block=False)


def _check_sensitive_claim(
    candidate: CandidateInput, result: ClassificationResult
) -> None:
    text = f"{(candidate.key or '')} {(candidate.value or '')}".lower().strip()

    if not text:
        return

    for pattern in _SENSITIVE_IDENTITY_PATTERNS:
        if pattern in text:
            _add_reason(
                result,
                GuardrailReason.SENSITIVE_IDENTITY_LIKE_CLAIM,
                block=False,
            )
            return


# ── shape detectors ─────────────────────────────────────────────────────────


def _is_sentence_fragment(text: str) -> bool:
    """Return True if *text* looks like a freeform sentence fragment.

    Structured domain keys (underscore_separated, dot.separated, or
    kebab-case identifiers with no spaces) are NOT treated as fragments
    because they are canonical domain labels, not freeform statements.
    """
    text = text.strip()
    if not text:
        return True

    # Identifier-style keys (no spaces, underscored/dotted/kebab) are
    # canonical domain labels, not sentence fragments.
    if " " not in text and ("_" in text or "-" in text or "." in text):
        return False

    # Fewer than 4 words is almost certainly a fragment.
    words = text.split()
    if len(words) < 4:
        return True

    # No capital letter at start suggests fragment.
    if text[0].islower():
        return True

    # Ends mid-word or with connector suggests cut-off.
    if text.rstrip(".").endswith(
        (" and", " or", " but", " the", " a", " an", " in", " to", " of", " for", " is")
    ):
        return True

    # Trailing ellipsis or dash
    if text.rstrip().endswith(("\u2026", "-", "\u2014")):
        return True

    return False


def _is_incomplete_fragment(text: str) -> bool:
    """Return True if *text* appears to be a cut-off or incomplete value.

    Short but complete values (e.g., "Portland", "French") are NOT
    flagged.  Only text with trailing ellipsis, dash, or other cut-off
    indicators is treated as incomplete.
    """
    text = text.strip()
    if not text:
        return True

    # Trailing ellipsis or dash suggests cut-off.
    if text.rstrip().endswith(("\u2026", "-", "\u2014", "...")):
        return True

    return False


def _is_prompt_like(text: str) -> bool:
    """Return True if *text* reads like a system prompt or instruction."""
    lower = text.strip().lower()
    for prefix in _PROMPT_LIKE_PREFIXES:
        if lower.startswith(prefix):
            return True
    return False


def _is_quoted_or_hypothetical(excerpt: str) -> bool:
    """Return True if *excerpt* appears to be quoted or hypothetical."""
    lower = excerpt.strip().lower()

    for marker in _HYPOTHETICAL_MARKERS:
        if marker in lower:
            return True

    stripped = excerpt.strip()

    # If the entire excerpt is wrapped in matching quote pairs.
    if len(stripped) >= 4:
        for q in _QUOTED_MARKERS:
            if stripped.startswith(q) and stripped.endswith(q):
                return True

    # If the excerpt contains quoted speech patterns ("X said", "X wrote").
    if any(
        phrase in lower
        for phrase in (" said", " wrote", " replied", " asked", " noted")
    ):
        return True

    # If the excerpt contains quote characters it is likely quoting someone.
    for q in _QUOTED_MARKERS:
        if q in stripped:
            return True

    return False


# ── helpers ─────────────────────────────────────────────────────────────────


def _add_reason(
    result: ClassificationResult,
    reason: GuardrailReason,
    *,
    block: bool = False,
) -> None:
    reason_str = reason.value if isinstance(reason, GuardrailReason) else str(reason)
    if reason_str not in result.reasons:
        result.reasons.append(reason_str)
    if block:
        result.promotion_blocked = True
