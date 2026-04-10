"""Canonical retrieval-posture contract for backend diagnostics surfaces.

This module stays pure and normalizes already-canonical posture inputs into a
small snapshot that can be reused by trace, help, and diagnostics consumers.
"""

from __future__ import annotations

from typing import Any, TypedDict

from guardian.context.retrieval_router_policy import QueryIntent

_SOURCE_MODES = frozenset({"project", "personal_knowledge"})
_RETRIEVAL_OVERRIDE_MODES = frozenset({"none", "project", "personal_knowledge"})
_WIDEN_REASONS = frozenset(
    {
        "none",
        "insufficient_thread_hits",
        "low_confidence_thread_hits",
        "explicit_personal_knowledge",
        "boundary_blocked",
    }
)
_BOUNDARY_LABEL_BY_SOURCE_MODE = {
    "project": "same_user_same_project",
    "personal_knowledge": "same_user_only",
}
_CONVERSATION_BOUNDARY_LABEL = QueryIntent.CONVERSATION_ONLY.value


class RetrievalPostureSnapshot(TypedDict):
    source_mode: str
    boundary_label: str
    retrieval_override_mode: str
    widen_reason: str
    conversation_only: bool


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value).strip().lower()
    except Exception:
        return ""


def _normalize_source_mode(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized if normalized in _SOURCE_MODES else "project"


def _normalize_retrieval_override_mode(value: Any) -> str:
    candidate = value
    if isinstance(value, dict):
        candidate = value.get("mode")
        if candidate is None:
            candidate = value.get("retrieval_override_mode")
    normalized = _normalize_text(candidate)
    return normalized if normalized in _RETRIEVAL_OVERRIDE_MODES else "none"


def _normalize_widen_reason(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized if normalized in _WIDEN_REASONS else "none"


def _normalize_conversation_only(value: Any) -> bool:
    return value is True


def build_retrieval_posture_snapshot(
    *,
    source_mode: Any = None,
    retrieval_override: Any = None,
    widen_reason: Any = None,
    conversation_only: Any = None,
) -> RetrievalPostureSnapshot:
    normalized_source_mode = _normalize_source_mode(source_mode)
    normalized_conversation_only = _normalize_conversation_only(
        conversation_only
    )
    return {
        "source_mode": normalized_source_mode,
        "boundary_label": (
            _CONVERSATION_BOUNDARY_LABEL
            if normalized_conversation_only
            else _BOUNDARY_LABEL_BY_SOURCE_MODE[normalized_source_mode]
        ),
        "retrieval_override_mode": _normalize_retrieval_override_mode(
            retrieval_override
        ),
        "widen_reason": _normalize_widen_reason(widen_reason),
        "conversation_only": normalized_conversation_only,
    }


__all__ = [
    "RetrievalPostureSnapshot",
    "build_retrieval_posture_snapshot",
]
