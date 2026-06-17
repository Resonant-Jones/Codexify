"""Fact Candidate Extraction Pipeline for live chat messages.

This module connects live chat message ingestion to the personal facts
candidate extraction system. It runs as a non-blocking side-effect after
user message persistence: extraction failures are logged but never break
chat generation.

Design:
- Extract → Deduplicate → Persist (pending candidate) → Log

Candidates are stored as status="candidate" in personal_facts with
evidence rows linking back to the source chat message. Sensitivity and
durable-memory promotion remain separate, controlled paths.

The regex extraction rules mirror those in backend.rag.personal_fact_extraction
but are inlined here to avoid pulling in the full RAG dependency chain
(numpy, embedders, etc.) during import.
"""

from __future__ import annotations

import logging
import re as _re
from typing import Any

logger = logging.getLogger(__name__)

# ── Text normalization ──


def _clean_text(value: Any) -> str:
    """Normalize any value to a whitespace-collapsed string."""
    text = _re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.strip('"\u201c\u201d\u2018\u2019').strip()
    text = _re.sub(r"[.?!;,:]+$", "", text).strip()
    return text


def _slugify(value: Any) -> str:
    text = _clean_text(value).lower()
    text = _re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


# ── Constants ──

MAX_FACT_VALUE_LENGTH = 255

# Source type value compatible with the personal_fact_evidence
# check constraint: 'chatgpt_import', 'runtime_extraction', 'user_stated', 'user_corrected'
LIVE_CHAT_SOURCE_TYPE = "runtime_extraction"

# Sensitive key patterns that should be flagged but not silently dropped.
SENSITIVE_KEY_PREFIXES = frozenset(
    {
        "ssn",
        "password",
        "credit_card",
        "bank",
        "pin",
        "secret",
        "token",
    }
)

_ROLE_KEYWORDS = (
    "engineer",
    "developer",
    "designer",
    "doctor",
    "teacher",
    "student",
    "parent",
    "lawyer",
    "manager",
    "founder",
    "researcher",
    "writer",
    "artist",
    "musician",
    "consultant",
    "chef",
    "nurse",
    "architect",
    "scientist",
    "analyst",
    "specialist",
    "director",
    "marketer",
    "accountant",
    "therapist",
    "physician",
    "coach",
    "freelancer",
    "entrepreneur",
    "sales",
    "product manager",
    "data scientist",
    "software",
    "devops",
    "ops",
    "resident",
    "citizen",
    "native",
    "bilingual",
    "vegan",
    "vegetarian",
    "married",
    "single",
)

_CLAUSE_BOUNDARY = (
    r"(?=\s+(?:and|but|because|so|while|though|although)\s+"
    r"\b(?:i|you|my|your)\b|[.!?;,]|$)"
)

# ── Regex-based extraction rules ──
# Mirrors _FACT_RULES from backend.rag.personal_fact_extraction

_FACT_RULES = [
    (
        "name",
        "name",
        0.99,
        _re.compile(
            rf"\b(?:my name is|call me|you can call me)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "location",
        "location",
        0.94,
        _re.compile(
            rf"\b(?:i(?:'m| am)?\s+from|i live in|i(?:'m| am)?\s+based in|"
            rf"i(?:'m| am)?\s+located in|you(?:'re| are)\s+from|"
            rf"you live in|you(?:'re| are)\s+based in|you(?:'re| are)\s+located in)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "occupation",
        "occupation",
        0.86,
        _re.compile(
            rf"\b(?:i work as|you work as)\s+(?:an?\s+)?"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "employer",
        "employer",
        0.88,
        _re.compile(
            rf"\b(?:i work at|i work for|you work at|you work for)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "preference",
        "preference",
        0.78,
        _re.compile(
            rf"\b(?:i prefer|i like|i enjoy|my preference is|"
            rf"you prefer|you like|you enjoy)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "pronouns",
        "pronouns",
        0.97,
        _re.compile(
            rf"\b(?:my|your) pronouns are\s+(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "favorite",
        None,
        0.9,
        _re.compile(
            rf"\b(?:my|your) favou?rite\s+(?P<label>.+?)\s+is\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
    (
        "identity_attribute",
        "identity_attribute",
        0.72,
        _re.compile(
            rf"\b(?:i(?:'m| am)|you(?:'re| are))\s+(?:a|an)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            _re.IGNORECASE,
        ),
    ),
]


# ── Helpers ──


def _looks_like_identity_attribute(value: str) -> bool:
    lowered = value.lower()
    if any(keyword in lowered for keyword in _ROLE_KEYWORDS):
        return True
    words = [word for word in lowered.split() if word]
    if 1 <= len(words) <= 4:
        return True
    return False


def _is_sensitive_candidate(key: str) -> bool:
    """Return True if the candidate key suggests a sensitive category."""
    normalized = str(key or "").strip().lower()
    return any(
        normalized.startswith(prefix) or prefix in normalized
        for prefix in SENSITIVE_KEY_PREFIXES
    )


def _build_evidence_meta(
    *,
    user_id: str,
    thread_id: int,
    message_id: int,
    persona_id: str | None,
    project_id: int | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build evidence metadata for a live-chat extracted fact candidate."""
    meta: dict[str, Any] = {
        "source": "chat",
        "source_type": LIVE_CHAT_SOURCE_TYPE,
        "user_id": user_id,
        "thread_id": thread_id,
        "source_message_id": message_id,
        "detector_rule": candidate.get("rule"),
        "fact_candidate_key": candidate.get("key"),
        "fact_candidate_value": candidate.get("value"),
    }
    if persona_id:
        meta["persona_id"] = persona_id
    if project_id is not None:
        meta["project_id"] = project_id
    return {key: value for key, value in meta.items() if value is not None}


# ── Extraction ──


def _extract_candidates_from_text(text: str) -> list[dict[str, Any]]:
    """Extract fact candidates from raw text using regex rules.

    Mirrors the extraction logic in backend.rag.personal_fact_extraction
    but works on raw text and has no external dependencies.
    """
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for rule_name, key, confidence, pattern in _FACT_RULES:
        for match in pattern.finditer(cleaned):
            value = _clean_text(match.groupdict().get("value"))
            if not value:
                continue

            if (
                rule_name == "identity_attribute"
                and not _looks_like_identity_attribute(value)
            ):
                continue

            candidate_key = key
            if rule_name == "favorite":
                label = _clean_text(match.groupdict().get("label"))
                if not label:
                    continue
                candidate_key = f"favorite_{_slugify(label)}"

            # Truncate to DB column width.
            if len(value) > MAX_FACT_VALUE_LENGTH:
                value = value[:MAX_FACT_VALUE_LENGTH]

            excerpt = _clean_text(match.group(0))

            signature = (candidate_key, value)
            if signature in seen:
                continue
            seen.add(signature)

            candidates.append(
                {
                    "key": candidate_key,
                    "value": value,
                    "confidence": confidence,
                    "excerpt": excerpt,
                    "rule": rule_name,
                }
            )

    return candidates


# ── Pipeline ──


def process_user_message(
    chatlog_db: Any,
    *,
    user_id: str,
    thread_id: int,
    message_id: int,
    persona_id: str | None = None,
    project_id: int | None = None,
    text: str,
) -> dict[str, int]:
    """Extract and persist fact candidates from a live chat user message.

    Call this synchronously after user message persistence. Errors are
    caught and logged internally so failures do not propagate.

    Args:
        chatlog_db: The chatlog database instance.
        user_id: The user who sent the message.
        thread_id: The chat thread ID.
        message_id: The persisted message ID.
        persona_id: The active persona ID, if any.
        project_id: The project ID, if any.
        text: The user message text.

    Returns:
        Stats dict with counts: candidates_found, candidates_created,
        candidates_skipped_duplicate, candidates_skipped_sensitive,
        evidence_created, failures.
    """
    stats: dict[str, int] = {
        "candidates_found": 0,
        "candidates_created": 0,
        "candidates_skipped_duplicate": 0,
        "candidates_skipped_sensitive": 0,
        "evidence_created": 0,
        "failures": 0,
    }

    if not text or not text.strip():
        logger.debug(
            "Fact candidate extraction skipped: empty user message text"
        )
        return stats

    logger.debug(
        "Fact candidate extraction started user_id=%s thread_id=%s message_id=%s",
        user_id,
        thread_id,
        message_id,
    )

    # Step 1: extract candidates from text
    candidates = _extract_candidates_from_text(text)
    stats["candidates_found"] = len(candidates)

    if not candidates:
        logger.debug(
            "Fact candidate extraction: no candidates found in message_id=%s",
            message_id,
        )
        return stats

    logger.info(
        "Fact candidate extraction produced %d candidates from message_id=%s",
        len(candidates),
        message_id,
    )

    # Step 2: persist each candidate
    create_fact = getattr(chatlog_db, "create_fact", None)
    list_facts = getattr(chatlog_db, "list_facts", None)
    add_fact_evidence = getattr(chatlog_db, "add_fact_evidence", None)

    if not callable(create_fact):
        logger.warning(
            "Fact candidate persistence skipped: chatlog_db lacks create_fact"
        )
        return stats

    for candidate in candidates:
        key = _clean_text(candidate.get("key")).lower()
        value = _clean_text(candidate.get("value"))

        if not key or not value:
            continue

        # Sensitivity check — log but don't block
        if _is_sensitive_candidate(key):
            logger.warning(
                "Fact candidate flagged as sensitive key=%s user_id=%s message_id=%s",
                key,
                user_id,
                message_id,
            )
            stats["candidates_skipped_sensitive"] += 1
            # Continue — we still store for review, just with a flag

        # Deduplication: check if an active fact with this key already exists.
        # We check ALL active facts (any status) to avoid duplicate keys.
        if callable(list_facts):
            try:
                existing = list_facts(user_id, active_only=True, limit=1000)
                existing_for_key = [
                    f
                    for f in (existing or [])
                    if isinstance(f, dict)
                    and str(f.get("key") or "").strip().lower() == key
                    and f.get("is_active", True)
                ]
            except Exception:
                logger.debug(
                    "Fact candidate dedup check failed for key=%s",
                    key,
                    exc_info=True,
                )
                existing_for_key = []
        else:
            existing_for_key = []

        if existing_for_key:
            logger.debug(
                "Fact candidate skipped: active fact already exists for key=%s user_id=%s",
                key,
                user_id,
            )
            stats["candidates_skipped_duplicate"] += 1
            continue

        # Create fact as candidate
        confidence = float(candidate.get("confidence", 0.5))
        try:
            confidence = min(max(confidence, 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.5

        try:
            fact_id = create_fact(
                user_id,
                key,
                value,
                status="candidate",
                confidence=confidence,
            )
            stats["candidates_created"] += 1
        except Exception:
            logger.warning(
                "Fact candidate create failed key=%s user_id=%s message_id=%s",
                key,
                user_id,
                message_id,
                exc_info=True,
            )
            stats["failures"] += 1
            continue

        # Add evidence row linking to source message
        if callable(add_fact_evidence) and fact_id is not None:
            evidence_meta = _build_evidence_meta(
                user_id=user_id,
                thread_id=thread_id,
                message_id=message_id,
                persona_id=persona_id,
                project_id=project_id,
                candidate=candidate,
            )
            excerpt = _clean_text(
                candidate.get("excerpt") or candidate.get("value")
            )
            try:
                add_fact_evidence(
                    fact_id,
                    int(message_id),
                    excerpt,
                    modality="text",
                    confidence=confidence,
                    source_type=LIVE_CHAT_SOURCE_TYPE,
                    evidence_meta=evidence_meta,
                )
                stats["evidence_created"] += 1
            except Exception:
                logger.warning(
                    "Fact candidate evidence creation failed fact_id=%s key=%s message_id=%s",
                    fact_id,
                    key,
                    message_id,
                    exc_info=True,
                )

    logger.info(
        "Fact candidate persistence complete: found=%d created=%d skipped_dup=%d skipped_sensitive=%d evidence=%d failures=%d message_id=%s",
        stats["candidates_found"],
        stats["candidates_created"],
        stats["candidates_skipped_duplicate"],
        stats["candidates_skipped_sensitive"],
        stats["evidence_created"],
        stats["failures"],
        message_id,
    )

    return stats


__all__ = [
    "LIVE_CHAT_SOURCE_TYPE",
    "MAX_FACT_VALUE_LENGTH",
    "process_user_message",
]
