"""Provider-neutral Search-as-RAG contracts for Remote Recall.

These dataclasses define the stable boundary between web-evidence producers
(provider adapters) and downstream synthesis. They mirror the conceptual shapes
in ``docs/architecture/web-search-provider-adapter-contract.md`` and
``docs/architecture/web-evidence-intake-gate-contract.md`` without prescribing
provider-specific structure.

Only the Groq adapter is implemented in the first seam. ``source_kind`` is a
bounded token (see :class:`guardian.protocol_tokens.RemoteRecallSourceKind`) so
future adapters (Wikipedia, arXiv, Semantic Scholar, Brave, Google Custom
Search, local/private indexes) can plug into the same shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from guardian.protocol_tokens import (
    REMOTE_RECALL_SOURCE_KINDS,
    RemoteRecallSourceKind,
    WebEvidenceGateDecision,
)


def _normalize_source_kind(value: str | RemoteRecallSourceKind) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in REMOTE_RECALL_SOURCE_KINDS:
        raise ValueError(
            f"Unsupported Remote Recall source_kind: {value!r}"
        )
    return normalized


@dataclass(frozen=True)
class SearchProviderRequest:
    """Inbound normalized request for external indexed retrieval."""

    request_id: str
    query: str
    provider: str
    source_kind: str
    user_id: str | None = None
    thread_id: int | None = None
    project_id: int | None = None
    source_message_id: int | None = None
    max_results: int = 5
    locale: str | None = None
    time_window: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", _normalize_source_kind(self.source_kind))
        if not str(self.request_id or "").strip():
            raise ValueError("SearchProviderRequest.request_id is required")
        if not str(self.query or "").strip():
            raise ValueError("SearchProviderRequest.query is required")
        if not str(self.provider or "").strip():
            raise ValueError("SearchProviderRequest.provider is required")
        if self.max_results < 1:
            object.__setattr__(self, "max_results", 1)


@dataclass(frozen=True)
class SearchResultItem:
    """Single normalized search hit produced by a provider adapter.

    Provider adapters must normalize their native response into this shape before
    handing candidates to the Web Evidence Intake Gate. Raw provider objects must
    never leave the adapter boundary.
    """

    provider: str
    source_kind: str
    url: str
    title: str = ""
    snippet: str = ""
    text: str = ""
    rank: int = 0
    score: float | None = None
    retrieved_at: str = ""
    citation: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", _normalize_source_kind(self.source_kind))


@dataclass(frozen=True)
class SearchProviderResult:
    """Normalized provider response ready for downstream consumption.

    ``status`` is one of: ``ok``, ``empty``, ``error``. ``blocked_reason`` is a
    canonical :class:`RemoteRecallFailureReason` value when the adapter failed
    closed before returning results.
    """

    request_id: str
    provider: str
    source_kind: str
    status: str
    result_count: int = 0
    results: list[SearchResultItem] = field(default_factory=list)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", _normalize_source_kind(self.source_kind))


@dataclass(frozen=True)
class WebEvidenceEnvelope:
    """Synthesis-eligible (or blocked-but-traced) evidence envelope.

    Envelopes are produced by the Web Evidence Intake Gate. Only envelopes whose
    companion gate decision is ``eligible_for_synthesis`` may enter model
    synthesis context. Blocked envelopes are preserved for trace/diagnostics only
    and must not be injected into the completion context.
    """

    evidence_id: str
    request_id: str
    provider: str
    source_kind: str
    url: str
    title: str = ""
    snippet: str = ""
    text: str = ""
    rank: int = 0
    score: float | None = None
    retrieved_at: str = ""
    observed_at: str = ""
    content_hash: str = ""
    freshness_label: str | None = None
    citation: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    # Provenance fields needed by trace/debug surfaces.
    query: str = ""
    user_id: str | None = None
    thread_id: int | None = None
    project_id: int | None = None
    source_message_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", _normalize_source_kind(self.source_kind))

    def synthesis_text(self) -> str:
        """Return the stable text used for synthesis injection and hashing."""

        return str(self.snippet or self.text or "").strip()


@dataclass(frozen=True)
class WebEvidenceGateResult:
    """Gate decision payload for a single candidate evidence item.

    ``provenance`` survives even when an item is blocked so trace/debug surfaces
    can explain what was rejected and why.
    """

    envelope: WebEvidenceEnvelope
    gate_decision: str
    block_reason: str | None = None
    eligible_for_synthesis: bool = False
    prompt_injection_flags: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        decision = str(self.gate_decision or "").strip()
        if decision not in {
            WebEvidenceGateDecision.ELIGIBLE_FOR_SYNTHESIS.value,
            WebEvidenceGateDecision.BLOCKED.value,
            WebEvidenceGateDecision.NEEDS_HUMAN_REVIEW.value,
        }:
            raise ValueError(
                f"Unsupported web evidence gate decision: {self.gate_decision!r}"
            )
        object.__setattr__(self, "gate_decision", decision)
        eligible = (
            self.eligible_for_synthesis
            and decision == WebEvidenceGateDecision.ELIGIBLE_FOR_SYNTHESIS.value
        )
        object.__setattr__(self, "eligible_for_synthesis", eligible)


__all__ = [
    "SearchProviderRequest",
    "SearchProviderResult",
    "SearchResultItem",
    "WebEvidenceEnvelope",
    "WebEvidenceGateResult",
]
