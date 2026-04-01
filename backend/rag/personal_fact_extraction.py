"""Heuristic personal-fact extraction for ChatGPT imports.

The importer keeps this module deliberately small and deterministic: it
extracts review-only fact candidates from imported conversation text and
persists them into the existing personal_facts / personal_fact_evidence
schema without auto-approving anything.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable

logger = logging.getLogger(__name__)

CHATGPT_IMPORT_SOURCE = "chatgpt_import"
CHATGPT_IMPORT_PROFILE = "chatgpt_v1_canonical"

_CLAUSE_BOUNDARY = (
    r"(?=\s+(?:and|but|because|so|while|though|although)\s+"
    r"\b(?:i|you|my|your)\b|[.!?;,]|$)"
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

_FACT_RULES = [
    (
        "name",
        "name",
        0.99,
        re.compile(
            rf"\b(?:my name is|call me|you can call me)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "location",
        "location",
        0.94,
        re.compile(
            rf"\b(?:i(?:'m| am)?\s+from|i live in|i(?:'m| am)?\s+based in|"
            rf"i(?:'m| am)?\s+located in|you(?:'re| are)\s+from|"
            rf"you live in|you(?:'re| are)\s+based in|you(?:'re| are)\s+located in)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "occupation",
        "occupation",
        0.86,
        re.compile(
            rf"\b(?:i work as|you work as)\s+(?:an?\s+)?"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "employer",
        "employer",
        0.88,
        re.compile(
            rf"\b(?:i work at|i work for|you work at|you work for)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "preference",
        "preference",
        0.78,
        re.compile(
            rf"\b(?:i prefer|i like|i enjoy|my preference is|"
            rf"you prefer|you like|you enjoy)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "pronouns",
        "pronouns",
        0.97,
        re.compile(
            rf"\b(?:my|your) pronouns are\s+(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "favorite",
        None,
        0.9,
        re.compile(
            rf"\b(?:my|your) favou?rite\s+(?P<label>.+?)\s+is\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
    (
        "identity_attribute",
        "identity_attribute",
        0.72,
        re.compile(
            rf"\b(?:i(?:'m| am)|you(?:'re| are))\s+(?:a|an)\s+"
            rf"(?P<value>.+?){_CLAUSE_BOUNDARY}",
            re.IGNORECASE,
        ),
    ),
]


def _normalize_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.strip("\"'“”‘’").strip()
    text = re.sub(r"[.?!;,:]+$", "", text).strip()
    return text


def _slugify(value: Any) -> str:
    text = _normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _looks_like_identity_attribute(value: str) -> bool:
    lowered = value.lower()
    if any(keyword in lowered for keyword in _ROLE_KEYWORDS):
        return True
    words = [word for word in lowered.split() if word]
    if 1 <= len(words) <= 4:
        return True
    return False


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        rows = value
    elif isinstance(value, tuple):
        rows = list(value)
    else:
        try:
            rows = list(value)
        except TypeError:
            return []
    return [row for row in rows if isinstance(row, dict)]


def _build_evidence_meta(
    *,
    message: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    source_created_at = message.get("source_created_at")
    if hasattr(source_created_at, "isoformat"):
        source_created_at = source_created_at.isoformat()
    imported_at = message.get("imported_at")
    if hasattr(imported_at, "isoformat"):
        imported_at = imported_at.isoformat()

    meta: dict[str, Any] = {
        "import_source": CHATGPT_IMPORT_SOURCE,
        "import_profile": CHATGPT_IMPORT_PROFILE,
        "origin": CHATGPT_IMPORT_SOURCE,
        "source": CHATGPT_IMPORT_SOURCE,
        "source_thread_id": message.get("source_thread_id"),
        "source_message_export_id": message.get("source_message_id"),
        "source_message_db_id": message.get("chatlog_message_id"),
        "source_role": message.get("role"),
        "source_content_type": message.get("content_type"),
        "turn_index": message.get("turn_index"),
        "source_created_at": source_created_at,
        "source_created_at_inferred": bool(
            message.get("source_created_at_inferred")
        ),
        "imported_at": imported_at,
        "fact_candidate_key": candidate.get("key"),
        "fact_candidate_value": candidate.get("value"),
        "detector_rule": candidate.get("rule"),
    }
    return {key: value for key, value in meta.items() if value is not None}


def extract_personal_fact_candidates(
    message: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return candidate personal facts inferred from an imported message."""
    text = _normalize_text(message.get("content") or message.get("text"))
    if not text:
        return []

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for rule_name, key, confidence, pattern in _FACT_RULES:
        for match in pattern.finditer(text):
            value = _normalize_text(match.groupdict().get("value"))
            if not value:
                continue
            if (
                rule_name == "identity_attribute"
                and not _looks_like_identity_attribute(value)
            ):
                continue

            candidate_key = key
            if rule_name == "favorite":
                label = _normalize_text(match.groupdict().get("label"))
                if not label:
                    continue
                candidate_key = f"favorite_{_slugify(label)}"

            signature = (candidate_key, value)
            if signature in seen:
                continue
            seen.add(signature)

            candidates.append(
                {
                    "key": candidate_key,
                    "value": value,
                    "confidence": confidence,
                    "excerpt": _normalize_text(match.group(0)),
                    "rule": rule_name,
                }
            )

    return candidates


def _find_existing_fact(
    chatlog_db,
    *,
    user_id: str,
    key: str,
) -> dict[str, Any] | None:
    list_facts = getattr(chatlog_db, "list_facts", None)
    if not callable(list_facts):
        return None

    try:
        rows = _coerce_dict_rows(
            list_facts(user_id, active_only=True, limit=50000)
        )
    except Exception as exc:
        logger.warning("Unable to list facts for import dedupe: %s", exc)
        return None

    for row in rows:
        if str(row.get("key") or "").strip() != key:
            continue
        if not row.get("is_active", True):
            continue
        return row
    return None


def _existing_evidence_matches(
    evidence_rows: Iterable[dict[str, Any]],
    *,
    message_db_id: Any,
    source_thread_id: Any,
    source_message_export_id: Any,
) -> bool:
    message_db_id_str = str(message_db_id or "").strip()
    thread_id_str = str(source_thread_id or "").strip()
    export_id_str = str(source_message_export_id or "").strip()

    for row in evidence_rows:
        if str(row.get("source_type") or "") != CHATGPT_IMPORT_SOURCE:
            continue
        if str(row.get("source_message_id") or "").strip() != message_db_id_str:
            continue
        meta = row.get("evidence_meta")
        if not isinstance(meta, dict):
            continue
        if (
            thread_id_str
            and str(meta.get("source_thread_id") or "").strip() != thread_id_str
        ):
            continue
        if (
            export_id_str
            and str(meta.get("source_message_export_id") or "").strip()
            != export_id_str
        ):
            continue
        return True
    return False


def persist_personal_fact_candidates(
    chatlog_db,
    *,
    user_id: str,
    message: dict[str, Any],
    candidates: Iterable[dict[str, Any]],
) -> dict[str, int]:
    """Persist candidate facts into the existing review-state tables.

    The importer is intentionally conservative:
    - new keys become `candidate` facts,
    - existing candidate facts get another evidence row,
    - active non-candidate facts are left untouched,
    - duplicate evidence for the same import message is skipped.
    """
    message_db_id = message.get("chatlog_message_id")
    source_thread_id = message.get("source_thread_id")
    source_message_export_id = message.get("source_message_id")

    if message_db_id is None:
        logger.debug("Skipping fact persistence: missing chatlog_message_id")
        return {
            "candidates": 0,
            "facts_created": 0,
            "facts_reused": 0,
            "evidence_created": 0,
            "duplicates_skipped": 0,
            "non_candidate_skipped": 0,
        }

    create_fact = getattr(chatlog_db, "create_fact", None)
    add_fact_evidence = getattr(chatlog_db, "add_fact_evidence", None)
    list_fact_evidence = getattr(chatlog_db, "list_fact_evidence", None)
    if not callable(create_fact) or not callable(add_fact_evidence):
        logger.debug(
            "Skipping fact persistence: chatlog_db lacks fact write methods"
        )
        return {
            "candidates": 0,
            "facts_created": 0,
            "facts_reused": 0,
            "evidence_created": 0,
            "duplicates_skipped": 0,
            "non_candidate_skipped": 0,
        }

    stats = {
        "candidates": 0,
        "facts_created": 0,
        "facts_reused": 0,
        "evidence_created": 0,
        "duplicates_skipped": 0,
        "non_candidate_skipped": 0,
    }

    for raw_candidate in candidates:
        stats["candidates"] += 1
        key = _normalize_text(raw_candidate.get("key")).lower()
        value = _normalize_text(raw_candidate.get("value"))
        if not key or not value:
            continue

        confidence_raw = raw_candidate.get("confidence", 0.5)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(max(confidence, 0.0), 1.0)

        existing_fact = _find_existing_fact(
            chatlog_db, user_id=user_id, key=key
        )
        if (
            existing_fact
            and str(existing_fact.get("status") or "") != "candidate"
        ):
            stats["non_candidate_skipped"] += 1
            continue

        fact_id: Any = None
        if existing_fact:
            fact_id = existing_fact.get("id")
            stats["facts_reused"] += 1
        else:
            try:
                fact_id = create_fact(
                    user_id,
                    key,
                    value,
                    status="candidate",
                    confidence=confidence,
                )
                stats["facts_created"] += 1
            except Exception as exc:
                logger.debug(
                    "ChatGPT personal-fact create failed for key=%s: %s",
                    key,
                    exc,
                )
                existing_fact = _find_existing_fact(
                    chatlog_db, user_id=user_id, key=key
                )
                if not existing_fact:
                    continue
                if str(existing_fact.get("status") or "") != "candidate":
                    stats["non_candidate_skipped"] += 1
                    continue
                fact_id = existing_fact.get("id")
                stats["facts_reused"] += 1

        if fact_id is None:
            continue

        if callable(list_fact_evidence):
            try:
                evidence_rows = _coerce_dict_rows(list_fact_evidence(fact_id))
            except Exception as exc:
                logger.debug(
                    "Unable to list fact evidence for dedupe fact_id=%s: %s",
                    fact_id,
                    exc,
                )
                evidence_rows = []
        else:
            evidence_rows = []

        if _existing_evidence_matches(
            evidence_rows,
            message_db_id=message_db_id,
            source_thread_id=source_thread_id,
            source_message_export_id=source_message_export_id,
        ):
            stats["duplicates_skipped"] += 1
            continue

        evidence_meta = _build_evidence_meta(
            message=message,
            candidate={
                "key": key,
                "value": value,
                "rule": raw_candidate.get("rule"),
            },
        )

        excerpt = _normalize_text(raw_candidate.get("excerpt") or value)
        try:
            add_fact_evidence(
                fact_id,
                int(message_db_id),
                excerpt,
                modality="text",
                confidence=confidence,
                source_type=CHATGPT_IMPORT_SOURCE,
                evidence_meta=evidence_meta,
            )
            stats["evidence_created"] += 1
        except Exception as exc:
            logger.warning(
                "Failed to persist ChatGPT personal-fact evidence fact_id=%s key=%s: %s",
                fact_id,
                key,
                exc,
            )

    return stats


__all__ = [
    "CHATGPT_IMPORT_PROFILE",
    "CHATGPT_IMPORT_SOURCE",
    "extract_personal_fact_candidates",
    "persist_personal_fact_candidates",
]
