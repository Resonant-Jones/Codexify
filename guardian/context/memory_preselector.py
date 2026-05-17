"""Scoped deterministic preselector over memory-header metadata.

This module is intentionally pure and read-only. It performs deterministic
filtering and scoring over candidate headers without any runtime side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

IdentityDepth = Literal["none", "light", "deep"]
MemoryCandidateKind = Literal[
    "episodic",
    "semantic",
    "fact",
    "document",
    "artifact",
]
MemorySuppressionReason = Literal[
    "missing_user_scope",
    "user_scope_mismatch",
    "project_scope_mismatch",
    "thread_scope_mismatch",
    "persona_scope_mismatch",
    "diary_excluded",
    "identity_depth_exceeded",
    "silo_not_allowed",
    "score_too_low",
    "not_relevant",
]

_IDENTITY_DEPTH_ORDER: dict[str, int] = {
    "none": 0,
    "light": 1,
    "deep": 2,
}

_MAX_LIMIT = 50
_MIN_LIMIT = 1


@dataclass(frozen=True)
class MemoryCandidateHeader:
    candidate_id: str
    user_id: str
    kind: MemoryCandidateKind | str
    title: str | None = None
    summary: str | None = None
    tags: tuple[str, ...] = ()
    silo: str | None = None
    project_id: str | None = None
    thread_id: str | None = None
    persona_id: str | None = None
    identity_depth: IdentityDepth | str = "light"
    diary_excluded: bool = False
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MemoryPreselectorRequest:
    query: str
    user_id: str
    project_id: str | None = None
    thread_id: str | None = None
    persona_id: str | None = None
    allowed_silos: tuple[str, ...] = ()
    identity_depth: IdentityDepth | str = "light"
    include_diary_excluded: bool = False
    limit: int = 20
    min_score: int = 1


@dataclass(frozen=True)
class SelectedMemoryCandidate:
    candidate_id: str
    score: int
    matched_terms: tuple[str, ...]
    boost_hints: tuple[str, ...] = ()
    header: MemoryCandidateHeader | None = None


@dataclass(frozen=True)
class SuppressedMemoryCandidate:
    candidate_id: str
    reason: MemorySuppressionReason | str
    detail: str = ""


@dataclass(frozen=True)
class MemoryPreselectorResult:
    selected: tuple[SelectedMemoryCandidate, ...]
    suppressed: tuple[SuppressedMemoryCandidate, ...]


@dataclass(frozen=True)
class _ScoredCandidate:
    selected: SelectedMemoryCandidate


def select_memory_candidates(
    candidates: Sequence[MemoryCandidateHeader],
    request: MemoryPreselectorRequest,
) -> MemoryPreselectorResult:
    limit = _clamp_limit(request.limit)
    min_score = _normalize_min_score(request.min_score)
    query_terms = _tokenize_query(request.query)
    request_user_id = _normalize_text(request.user_id)
    request_project_id = _normalize_optional_text(request.project_id)
    request_thread_id = _normalize_optional_text(request.thread_id)
    request_persona_id = _normalize_optional_text(request.persona_id)
    allowed_silos = {
        _normalize_text(value)
        for value in request.allowed_silos
        if _normalize_text(value)
    }
    request_depth = _normalize_request_identity_depth(request.identity_depth)

    suppressed: list[SuppressedMemoryCandidate] = []
    selected_scored: list[_ScoredCandidate] = []

    if not request_user_id:
        for candidate in candidates:
            suppressed.append(
                SuppressedMemoryCandidate(
                    candidate_id=candidate.candidate_id,
                    reason="missing_user_scope",
                    detail="request user_id is required",
                )
            )
        return MemoryPreselectorResult(selected=(), suppressed=tuple(suppressed))

    for candidate in candidates:
        suppression = _scope_and_policy_suppression(
            candidate=candidate,
            request_user_id=request_user_id,
            request_project_id=request_project_id,
            request_thread_id=request_thread_id,
            request_persona_id=request_persona_id,
            allowed_silos=allowed_silos,
            request_depth=request_depth,
            include_diary_excluded=request.include_diary_excluded,
        )
        if suppression is not None:
            suppressed.append(suppression)
            continue

        if not query_terms:
            suppressed.append(
                SuppressedMemoryCandidate(
                    candidate_id=candidate.candidate_id,
                    reason="not_relevant",
                    detail="blank query provided",
                )
            )
            continue

        score, matched_terms, boost_hints = _score_candidate(
            candidate,
            query_terms=query_terms,
            request_project_id=request_project_id,
            request_thread_id=request_thread_id,
            request_persona_id=request_persona_id,
            allowed_silos=allowed_silos,
        )
        if not matched_terms:
            suppressed.append(
                SuppressedMemoryCandidate(
                    candidate_id=candidate.candidate_id,
                    reason="not_relevant",
                    detail="candidate did not match query terms",
                )
            )
            continue
        if score < min_score:
            suppressed.append(
                SuppressedMemoryCandidate(
                    candidate_id=candidate.candidate_id,
                    reason="score_too_low",
                    detail=f"score {score} is below min_score {min_score}",
                )
            )
            continue

        selected_scored.append(
            _ScoredCandidate(
                selected=SelectedMemoryCandidate(
                    candidate_id=candidate.candidate_id,
                    score=score,
                    matched_terms=tuple(sorted(matched_terms)),
                    boost_hints=tuple(sorted(boost_hints)),
                    header=candidate,
                )
            )
        )

    selected_sorted = sorted(
        selected_scored,
        key=lambda item: (-item.selected.score, item.selected.candidate_id),
    )

    selected = [item.selected for item in selected_sorted[:limit]]
    for item in selected_sorted[limit:]:
        suppressed.append(
            SuppressedMemoryCandidate(
                candidate_id=item.selected.candidate_id,
                reason="score_too_low",
                detail=f"candidate rank exceeded limit {limit}",
            )
        )

    return MemoryPreselectorResult(
        selected=tuple(selected),
        suppressed=tuple(suppressed),
    )


def _scope_and_policy_suppression(
    *,
    candidate: MemoryCandidateHeader,
    request_user_id: str,
    request_project_id: str | None,
    request_thread_id: str | None,
    request_persona_id: str | None,
    allowed_silos: set[str],
    request_depth: int,
    include_diary_excluded: bool,
) -> SuppressedMemoryCandidate | None:
    candidate_user_id = _normalize_text(candidate.user_id)
    if candidate_user_id != request_user_id:
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="user_scope_mismatch",
            detail="candidate user_id does not match request user_id",
        )

    candidate_project_id = _normalize_optional_text(candidate.project_id)
    if (
        request_project_id
        and candidate_project_id is not None
        and candidate_project_id != request_project_id
    ):
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="project_scope_mismatch",
            detail="candidate project_id is outside request project scope",
        )

    candidate_thread_id = _normalize_optional_text(candidate.thread_id)
    if (
        request_thread_id
        and candidate_thread_id is not None
        and candidate_thread_id != request_thread_id
    ):
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="thread_scope_mismatch",
            detail="candidate thread_id is outside request thread scope",
        )

    candidate_persona_id = _normalize_optional_text(candidate.persona_id)
    if (
        request_persona_id
        and candidate_persona_id is not None
        and candidate_persona_id != request_persona_id
    ):
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="persona_scope_mismatch",
            detail="candidate persona_id is outside request persona scope",
        )

    candidate_silo = _normalize_optional_text(candidate.silo)
    if allowed_silos and candidate_silo not in allowed_silos:
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="silo_not_allowed",
            detail="candidate silo is outside allowed_silos",
        )

    if candidate.diary_excluded and not include_diary_excluded:
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="diary_excluded",
            detail="candidate excluded by diary policy",
        )

    candidate_depth = _normalize_candidate_identity_depth(candidate.identity_depth)
    if candidate_depth is None or candidate_depth > request_depth:
        return SuppressedMemoryCandidate(
            candidate_id=candidate.candidate_id,
            reason="identity_depth_exceeded",
            detail="candidate identity depth exceeds request allowance",
        )

    return None


def _score_candidate(
    candidate: MemoryCandidateHeader,
    *,
    query_terms: tuple[str, ...],
    request_project_id: str | None,
    request_thread_id: str | None,
    request_persona_id: str | None,
    allowed_silos: set[str],
) -> tuple[int, set[str], set[str]]:
    candidate_id = _normalize_text(candidate.candidate_id).lower()
    title = _normalize_optional_text(candidate.title, default="")
    summary = _normalize_optional_text(candidate.summary, default="")
    tags = tuple(_normalize_text(tag).lower() for tag in candidate.tags)
    silo = _normalize_optional_text(candidate.silo, default="")
    kind = _normalize_text(candidate.kind).lower()

    score = 0
    matched_terms: set[str] = set()
    boost_hints: set[str] = set()

    title_lower = title.lower()
    summary_lower = summary.lower()
    silo_lower = silo.lower()

    for term in query_terms:
        term_matched = False

        if term == candidate_id:
            score += 120
            term_matched = True
        elif term in candidate_id:
            score += 90
            term_matched = True

        if term in title_lower:
            score += 60
            boost_hints.add("title_match")
            term_matched = True

        if any(term in tag for tag in tags):
            score += 55
            boost_hints.add("tag_match")
            term_matched = True

        if term in summary_lower:
            score += 25
            boost_hints.add("summary_match")
            term_matched = True

        if term in silo_lower:
            score += 15
            boost_hints.add("silo_match")
            term_matched = True

        if term in kind:
            score += 10
            term_matched = True

        if term_matched:
            matched_terms.add(term)

    if (
        request_project_id
        and _normalize_optional_text(candidate.project_id) == request_project_id
    ):
        boost_hints.add("same_project")
    if (
        request_thread_id
        and _normalize_optional_text(candidate.thread_id) == request_thread_id
    ):
        boost_hints.add("same_thread")
    if (
        request_persona_id
        and _normalize_optional_text(candidate.persona_id) == request_persona_id
    ):
        boost_hints.add("same_persona")
    if allowed_silos and _normalize_optional_text(candidate.silo) in allowed_silos:
        boost_hints.add("silo_match")

    return score, matched_terms, boost_hints


def _tokenize_query(query: str) -> tuple[str, ...]:
    terms = [
        piece.strip().lower()
        for piece in str(query).split()
        if piece.strip()
    ]
    return tuple(terms)


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_optional_text(
    value: object | None, *, default: str | None = None
) -> str | None:
    normalized = _normalize_text(value)
    if normalized:
        return normalized
    return default


def _clamp_limit(limit: int) -> int:
    if limit < _MIN_LIMIT:
        return _MIN_LIMIT
    if limit > _MAX_LIMIT:
        return _MAX_LIMIT
    return limit


def _normalize_min_score(min_score: int) -> int:
    return max(0, min_score)


def _normalize_request_identity_depth(depth: IdentityDepth | str) -> int:
    normalized = _normalize_text(depth).lower()
    if normalized in _IDENTITY_DEPTH_ORDER:
        return _IDENTITY_DEPTH_ORDER[normalized]
    return _IDENTITY_DEPTH_ORDER["none"]


def _normalize_candidate_identity_depth(
    depth: IdentityDepth | str,
) -> int | None:
    normalized = _normalize_text(depth).lower()
    return _IDENTITY_DEPTH_ORDER.get(normalized)


__all__ = [
    "IdentityDepth",
    "MemoryCandidateHeader",
    "MemoryCandidateKind",
    "MemoryPreselectorRequest",
    "MemoryPreselectorResult",
    "MemorySuppressionReason",
    "SelectedMemoryCandidate",
    "SuppressedMemoryCandidate",
    "select_memory_candidates",
]

