"""Canonical retrieval-router policy contract for Guardian orchestration.

This module defines stable tokens and a pure policy resolver for the runtime
retrieval contract. It does not execute retrieval directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QueryIntent(str, Enum):
    CONVERSATION_ONLY = "conversation_only"
    DIRECT_QA = "direct_qa"
    MEMORY_RECALL = "memory_recall"
    TIMELINE_RECALL = "timeline_recall"
    PROVENANCE = "provenance"
    EXPLORATORY = "exploratory"
    EXPLICIT_GLOBAL_SEARCH = "explicit_global_search"
    SCOPE_LOCKED_LOCAL = "scope_locked_local"
    RELATIONSHIP_TRACE = "relationship_trace"


class RetrievalDepth(str, Enum):
    AUTO = "auto"
    SHALLOW = "shallow"
    NORMAL = "normal"
    DEEP = "deep"
    DIAGNOSTIC = "diagnostic"


class ScopeMode(str, Enum):
    CONVERSATION = "conversation"
    LOCAL = "local"
    GLOBAL = "global"


class TimeMode(str, Enum):
    NONE = "none"
    RECENT = "recent"
    CHRONOLOGICAL = "chronological"


class GraphAllowance(str, Enum):
    DISALLOW = "disallow"
    ALLOW_ENRICHMENT = "allow_enrichment"
    PREFER_ENRICHMENT = "prefer_enrichment"


class EscalationStep(str, Enum):
    THREAD_MESSAGES = "thread_messages"
    THREAD_SEMANTIC = "thread_semantic"
    PROJECT_DOCS = "project_docs"
    MEMORY = "memory"
    ADJACENT_LOCAL = "adjacent_local"
    GRAPH_ENRICHMENT = "graph_enrichment"
    GLOBAL_SEARCH = "global_search"


@dataclass(frozen=True)
class PolicyRule:
    intent: QueryIntent
    summary: str
    retrieval_needed: bool
    default_scope: ScopeMode
    time_mode: TimeMode
    graph_allowance: GraphAllowance
    depth_bias: RetrievalDepth
    escalation_order: tuple[EscalationStep, ...]
    allow_global_fallback: bool
    stop_condition: str


@dataclass(frozen=True)
class RetrievalPlan:
    query: str
    intent: QueryIntent
    effective_depth: RetrievalDepth
    default_scope: ScopeMode
    time_mode: TimeMode
    graph_allowance: GraphAllowance
    escalation_order: tuple[EscalationStep, ...]
    retrieval_needed: bool
    allow_global_fallback: bool
    reasons: tuple[str, ...]
    active_thread_id: int | None = None
    active_project_id: int | None = None
    active_persona: str | None = None


SOURCE_MODE_PROJECT = "project"
SOURCE_MODE_PERSONAL_KNOWLEDGE = "personal_knowledge"
SOURCE_MODE_CONVERSATION = "conversation"
SOURCE_MODE_OBSIDIAN_ONLY = "obsidian_only"

SOURCE_MODES: tuple[str, ...] = (
    SOURCE_MODE_PROJECT,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_OBSIDIAN_ONLY,
)

RETRIEVAL_OVERRIDE_NONE = "none"
RETRIEVAL_OVERRIDE_PROJECT = SOURCE_MODE_PROJECT
RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE = SOURCE_MODE_PERSONAL_KNOWLEDGE
RETRIEVAL_OVERRIDE_CONVERSATION = SOURCE_MODE_CONVERSATION

RETRIEVAL_OVERRIDE_MODES: tuple[str, ...] = (
    RETRIEVAL_OVERRIDE_NONE,
    RETRIEVAL_OVERRIDE_PROJECT,
    RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE,
    RETRIEVAL_OVERRIDE_CONVERSATION,
)

WIDEN_REASON_NONE = "none"
WIDEN_REASON_INSUFFICIENT_THREAD_HITS = "insufficient_thread_hits"
WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS = "low_confidence_thread_hits"
WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE = "explicit_personal_knowledge"

WIDEN_REASONS: tuple[str, ...] = (
    WIDEN_REASON_NONE,
    WIDEN_REASON_INSUFFICIENT_THREAD_HITS,
    WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS,
    WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE,
)

SOURCE_MODE_BOUNDARY_ACTIVE_CONVERSATION_ONLY = "active_conversation_only"
SOURCE_MODE_BOUNDARY_SAME_USER_ONLY = "same_user_only"
SOURCE_MODE_BOUNDARY_SAME_USER_SAME_PROJECT = "same_user_same_project"

SOURCE_MODE_BOUNDARY_LABELS: dict[str, str] = {
    SOURCE_MODE_PROJECT: SOURCE_MODE_BOUNDARY_SAME_USER_SAME_PROJECT,
    SOURCE_MODE_PERSONAL_KNOWLEDGE: SOURCE_MODE_BOUNDARY_SAME_USER_ONLY,
    SOURCE_MODE_CONVERSATION: SOURCE_MODE_BOUNDARY_ACTIVE_CONVERSATION_ONLY,
    SOURCE_MODE_OBSIDIAN_ONLY: SOURCE_MODE_BOUNDARY_SAME_USER_ONLY,
}


QUERY_INTENTS: frozenset[str] = frozenset(
    intent.value for intent in QueryIntent
)
RETRIEVAL_DEPTHS: frozenset[str] = frozenset(
    depth.value for depth in RetrievalDepth
)
SCOPE_MODES: frozenset[str] = frozenset(scope.value for scope in ScopeMode)
TIME_MODES: frozenset[str] = frozenset(mode.value for mode in TimeMode)
GRAPH_ALLOWANCES: frozenset[str] = frozenset(
    allowance.value for allowance in GraphAllowance
)
ESCALATION_STEPS: frozenset[str] = frozenset(
    step.value for step in EscalationStep
)

_EMPTY_ESCALATION: tuple[EscalationStep, ...] = ()


def normalize_source_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"obsidian", SOURCE_MODE_OBSIDIAN_ONLY}:
        return SOURCE_MODE_OBSIDIAN_ONLY
    if normalized in SOURCE_MODES:
        return normalized
    return SOURCE_MODE_PROJECT


def is_supported_source_mode(value: object) -> bool:
    return str(value or "").strip().lower() in SOURCE_MODES


def normalize_retrieval_override_mode(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in RETRIEVAL_OVERRIDE_MODES:
        return normalized
    return None


def is_supported_retrieval_override_mode(value: object) -> bool:
    return str(value or "").strip().lower() in RETRIEVAL_OVERRIDE_MODES


def normalize_widen_reason(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in WIDEN_REASONS:
        return normalized
    return WIDEN_REASON_NONE


def is_supported_widen_reason(value: object) -> bool:
    return str(value or "").strip().lower() in WIDEN_REASONS


def source_mode_boundary_label(value: object) -> str:
    return SOURCE_MODE_BOUNDARY_LABELS[normalize_source_mode(value)]


ROUTER_POLICY: dict[QueryIntent, PolicyRule] = {
    QueryIntent.CONVERSATION_ONLY: PolicyRule(
        intent=QueryIntent.CONVERSATION_ONLY,
        summary="Answer from the active conversation without retrieval.",
        retrieval_needed=False,
        default_scope=ScopeMode.CONVERSATION,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.DISALLOW,
        depth_bias=RetrievalDepth.SHALLOW,
        escalation_order=_EMPTY_ESCALATION,
        allow_global_fallback=False,
        stop_condition="Stop at the active conversation.",
    ),
    QueryIntent.DIRECT_QA: PolicyRule(
        intent=QueryIntent.DIRECT_QA,
        summary="Use ordinary local retrieval for targeted questions.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.DISALLOW,
        depth_bias=RetrievalDepth.NORMAL,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
            EscalationStep.ADJACENT_LOCAL,
        ),
        allow_global_fallback=False,
        stop_condition="Stop on first sufficient local evidence set.",
    ),
    QueryIntent.MEMORY_RECALL: PolicyRule(
        intent=QueryIntent.MEMORY_RECALL,
        summary="Favor memory-backed local recall.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.RECENT,
        graph_allowance=GraphAllowance.DISALLOW,
        depth_bias=RetrievalDepth.DEEP,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.MEMORY,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
        ),
        allow_global_fallback=False,
        stop_condition="Stop once memory-backed recall is sufficient.",
    ),
    QueryIntent.TIMELINE_RECALL: PolicyRule(
        intent=QueryIntent.TIMELINE_RECALL,
        summary="Preserve chronological ordering for timeline reconstruction.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.CHRONOLOGICAL,
        graph_allowance=GraphAllowance.DISALLOW,
        depth_bias=RetrievalDepth.DEEP,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.MEMORY,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
        ),
        allow_global_fallback=False,
        stop_condition="Stop once a coherent ordered timeline exists.",
    ),
    QueryIntent.PROVENANCE: PolicyRule(
        intent=QueryIntent.PROVENANCE,
        summary="Explain source and lineage with graph as optional enrichment.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.PREFER_ENRICHMENT,
        depth_bias=RetrievalDepth.NORMAL,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
            EscalationStep.GRAPH_ENRICHMENT,
            EscalationStep.ADJACENT_LOCAL,
        ),
        allow_global_fallback=False,
        stop_condition="Stop once source or lineage can be explained.",
    ),
    QueryIntent.EXPLORATORY: PolicyRule(
        intent=QueryIntent.EXPLORATORY,
        summary="Spend a larger evidence budget for broad exploration.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.ALLOW_ENRICHMENT,
        depth_bias=RetrievalDepth.DEEP,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
            EscalationStep.MEMORY,
            EscalationStep.ADJACENT_LOCAL,
            EscalationStep.GLOBAL_SEARCH,
        ),
        allow_global_fallback=True,
        stop_condition="Stop when the configured evidence budget is exhausted.",
    ),
    QueryIntent.EXPLICIT_GLOBAL_SEARCH: PolicyRule(
        intent=QueryIntent.EXPLICIT_GLOBAL_SEARCH,
        summary="Broaden search posture because the user asked explicitly.",
        retrieval_needed=True,
        default_scope=ScopeMode.GLOBAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.ALLOW_ENRICHMENT,
        depth_bias=RetrievalDepth.DEEP,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
            EscalationStep.ADJACENT_LOCAL,
            EscalationStep.GLOBAL_SEARCH,
        ),
        allow_global_fallback=True,
        stop_condition="Stop after the explicit broadened search pass.",
    ),
    QueryIntent.SCOPE_LOCKED_LOCAL: PolicyRule(
        intent=QueryIntent.SCOPE_LOCKED_LOCAL,
        summary="Keep retrieval strictly local and do not widen scope.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.DISALLOW,
        depth_bias=RetrievalDepth.NORMAL,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.PROJECT_DOCS,
        ),
        allow_global_fallback=False,
        stop_condition="Stop without adjacent or global expansion.",
    ),
    QueryIntent.RELATIONSHIP_TRACE: PolicyRule(
        intent=QueryIntent.RELATIONSHIP_TRACE,
        summary="Trace relationships with graph as preferred enrichment.",
        retrieval_needed=True,
        default_scope=ScopeMode.LOCAL,
        time_mode=TimeMode.NONE,
        graph_allowance=GraphAllowance.PREFER_ENRICHMENT,
        depth_bias=RetrievalDepth.DEEP,
        escalation_order=(
            EscalationStep.THREAD_MESSAGES,
            EscalationStep.THREAD_SEMANTIC,
            EscalationStep.GRAPH_ENRICHMENT,
            EscalationStep.PROJECT_DOCS,
            EscalationStep.ADJACENT_LOCAL,
        ),
        allow_global_fallback=False,
        stop_condition="Stop once the relationship path is explainable.",
    ),
}

_EXPLICIT_GLOBAL_SEARCH_HINTS = (
    "search everywhere",
    "search globally",
    "global search",
    "across all projects",
    "across everything",
    "search across all",
    "look everywhere",
)
_SCOPE_LOCKED_LOCAL_HINTS = (
    "only in this thread",
    "only in this project",
    "stay local",
    "keep it local",
    "local only",
    "no global search",
    "do not expand",
    "don't expand",
)
_RELATIONSHIP_TRACE_HINTS = (
    "relationship between",
    "relation between",
    "linked to",
    "connected to",
    "trace relationship",
    "how does ",
)
_PROVENANCE_HINTS = (
    "provenance",
    "where did",
    "source of",
    "cite",
    "citation",
    "came from",
)
_TIMELINE_RECALL_HINTS = (
    "timeline",
    "chronological",
    "when did",
    "what happened first",
    "what happened before",
    "sequence of events",
    "over time",
)
_MEMORY_RECALL_HINTS = (
    "remember",
    "recall",
    "what do you know about",
    "what did i say",
    "previously",
    "last time we",
)
_EXPLORATORY_HINTS = (
    "explore",
    "brainstorm",
    "survey",
    "map out",
    "look around",
    "broad search",
    "compare options",
)
_CONVERSATION_ONLY_EXACT = frozenset(
    {
        "",
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "cool",
        "sounds good",
        "how are you",
    }
)
_CONVERSATION_ONLY_PREFIXES = ("hi ", "hello ", "hey ", "thanks ", "thank ")


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def _coerce_query_intent(value: QueryIntent | str) -> QueryIntent:
    if isinstance(value, QueryIntent):
        return value
    normalized = str(value or "").strip().lower()
    try:
        return QueryIntent(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported query intent: {value!r}") from exc


def _coerce_retrieval_depth(
    value: RetrievalDepth | str | None,
) -> RetrievalDepth:
    if value is None:
        return RetrievalDepth.AUTO
    if isinstance(value, RetrievalDepth):
        return value
    normalized = str(value or "").strip().lower()
    if not normalized:
        return RetrievalDepth.AUTO
    try:
        return RetrievalDepth(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported retrieval depth: {value!r}") from exc


def classify_query_intent(query: str) -> QueryIntent:
    """Deterministic placeholder intent classifier for policy scaffolding."""
    normalized = " ".join(str(query or "").strip().lower().split())

    if _contains_any(normalized, _EXPLICIT_GLOBAL_SEARCH_HINTS):
        return QueryIntent.EXPLICIT_GLOBAL_SEARCH
    if _contains_any(normalized, _SCOPE_LOCKED_LOCAL_HINTS):
        return QueryIntent.SCOPE_LOCKED_LOCAL
    if _contains_any(normalized, _RELATIONSHIP_TRACE_HINTS):
        return QueryIntent.RELATIONSHIP_TRACE
    if _contains_any(normalized, _PROVENANCE_HINTS):
        return QueryIntent.PROVENANCE
    if _contains_any(normalized, _TIMELINE_RECALL_HINTS):
        return QueryIntent.TIMELINE_RECALL
    if _contains_any(normalized, _MEMORY_RECALL_HINTS):
        return QueryIntent.MEMORY_RECALL
    if _contains_any(normalized, _EXPLORATORY_HINTS):
        return QueryIntent.EXPLORATORY
    if normalized in _CONVERSATION_ONLY_EXACT or normalized.startswith(
        _CONVERSATION_ONLY_PREFIXES
    ):
        return QueryIntent.CONVERSATION_ONLY
    return QueryIntent.DIRECT_QA


def resolve_retrieval_plan(
    query: str,
    user_depth: RetrievalDepth | str | None,
    *,
    intent: QueryIntent | str | None = None,
    active_thread_id: int | None = None,
    active_project_id: int | None = None,
    active_persona: str | None = None,
) -> RetrievalPlan:
    """Resolve a pure retrieval plan from canonical policy tokens."""
    reasons: list[str] = []

    if intent is None:
        resolved_intent = classify_query_intent(query)
        reasons.append(
            f"intent classified from deterministic scaffold: {resolved_intent.value}"
        )
    else:
        resolved_intent = _coerce_query_intent(intent)
        reasons.append(
            f"intent accepted from explicit token: {resolved_intent.value}"
        )

    rule = ROUTER_POLICY[resolved_intent]
    requested_depth = _coerce_retrieval_depth(user_depth)

    if active_thread_id is not None:
        reasons.append(f"active thread context available: {active_thread_id}")
    if active_project_id is not None:
        reasons.append(f"active project context available: {active_project_id}")
    if active_persona:
        reasons.append(f"active persona context available: {active_persona}")

    if not rule.retrieval_needed:
        effective_depth = RetrievalDepth.SHALLOW
        reasons.append("policy marks retrieval as unnecessary for this intent.")
        if requested_depth != RetrievalDepth.AUTO:
            reasons.append(
                "conversation-only intent collapses explicit depth to shallow."
            )
        return RetrievalPlan(
            query=str(query or ""),
            intent=resolved_intent,
            effective_depth=effective_depth,
            default_scope=rule.default_scope,
            time_mode=rule.time_mode,
            graph_allowance=rule.graph_allowance,
            escalation_order=_EMPTY_ESCALATION,
            retrieval_needed=False,
            allow_global_fallback=False,
            reasons=tuple(reasons),
            active_thread_id=active_thread_id,
            active_project_id=active_project_id,
            active_persona=active_persona,
        )

    if requested_depth == RetrievalDepth.AUTO:
        effective_depth = rule.depth_bias
        reasons.append(
            "depth resolved from auto to policy bias: "
            f"{effective_depth.value}"
        )
    else:
        effective_depth = requested_depth
        reasons.append(
            f"explicit depth preserved from caller: {effective_depth.value}"
        )

    reasons.append(
        f"default scope resolved from policy: {rule.default_scope.value}"
    )
    reasons.append(f"time mode resolved from policy: {rule.time_mode.value}")
    reasons.append(
        "graph allowance resolved from policy: " f"{rule.graph_allowance.value}"
    )

    return RetrievalPlan(
        query=str(query or ""),
        intent=resolved_intent,
        effective_depth=effective_depth,
        default_scope=rule.default_scope,
        time_mode=rule.time_mode,
        graph_allowance=rule.graph_allowance,
        escalation_order=rule.escalation_order,
        retrieval_needed=rule.retrieval_needed,
        allow_global_fallback=rule.allow_global_fallback,
        reasons=tuple(reasons),
        active_thread_id=active_thread_id,
        active_project_id=active_project_id,
        active_persona=active_persona,
    )


__all__ = [
    "ESCALATION_STEPS",
    "GRAPH_ALLOWANCES",
    "RETRIEVAL_OVERRIDE_CONVERSATION",
    "RETRIEVAL_OVERRIDE_MODES",
    "RETRIEVAL_OVERRIDE_NONE",
    "RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE",
    "RETRIEVAL_OVERRIDE_PROJECT",
    "QUERY_INTENTS",
    "RETRIEVAL_DEPTHS",
    "SOURCE_MODE_BOUNDARY_ACTIVE_CONVERSATION_ONLY",
    "SOURCE_MODE_BOUNDARY_LABELS",
    "SOURCE_MODE_BOUNDARY_SAME_USER_ONLY",
    "SOURCE_MODE_BOUNDARY_SAME_USER_SAME_PROJECT",
    "SOURCE_MODE_CONVERSATION",
    "SOURCE_MODE_OBSIDIAN_ONLY",
    "SOURCE_MODE_PERSONAL_KNOWLEDGE",
    "SOURCE_MODE_PROJECT",
    "SOURCE_MODES",
    "SCOPE_MODES",
    "TIME_MODES",
    "WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE",
    "WIDEN_REASON_INSUFFICIENT_THREAD_HITS",
    "WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS",
    "WIDEN_REASON_NONE",
    "WIDEN_REASONS",
    "EscalationStep",
    "GraphAllowance",
    "PolicyRule",
    "QueryIntent",
    "ROUTER_POLICY",
    "RetrievalDepth",
    "RetrievalPlan",
    "ScopeMode",
    "TimeMode",
    "classify_query_intent",
    "is_supported_retrieval_override_mode",
    "is_supported_source_mode",
    "is_supported_widen_reason",
    "normalize_retrieval_override_mode",
    "normalize_source_mode",
    "normalize_widen_reason",
    "resolve_retrieval_plan",
    "source_mode_boundary_label",
]
