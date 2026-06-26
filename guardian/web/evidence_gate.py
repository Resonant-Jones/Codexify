"""Web Evidence Intake Gate for Remote Recall.

This gate is the shared pre-synthesis boundary for all web-derived evidence. It
normalizes provider output into a stable envelope, computes a deterministic
content hash, rejects empty or malformed items, screens for obvious
prompt-injection smuggling, preserves provenance even when an item is blocked,
and returns only eligible evidence to synthesis.

Remote content is always treated as data, never as executable, system, or
developer instruction. The first gate is heuristic and deterministic: no
model-based classifier is introduced here.

See: docs/architecture/web-evidence-intake-gate-contract.md
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse

from guardian.protocol_tokens import (
    RemoteRecallFailureReason,
    WebEvidenceGateDecision,
)
from guardian.web.contracts import (
    SearchProviderRequest,
    SearchResultItem,
    WebEvidenceEnvelope,
    WebEvidenceGateResult,
)

# Conservative, deterministic prompt-injection smuggling phrases. This is a
# heuristic first line of defense only; it blocks obvious instruction smuggling
# and is not a complete injection classifier.
_PROMPT_INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "ignore the above",
    "ignore your instructions",
    "disregard the above",
    "disregard previous",
    "disregard your instructions",
    "system prompt:",
    "system:",
    "reveal your system prompt",
    "reveal your instructions",
    "you are now",
    "act as",
    "new instructions:",
    "from now on",
    "do not follow",
    "forget your rules",
    "override your",
    "<system",
    "</system",
)

# Flag returned when an obvious injection phrase is detected.
_INJECTION_FLAG = "prompt_injection_phrase"
_MALFORMED_URL_FLAG = "malformed_url"
_EMPTY_EVIDENCE_FLAG = "empty_evidence"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_content_hash(
    *,
    url: str,
    title: str,
    snippet: str,
    text: str,
    provider: str,
    source_kind: str,
) -> str:
    """Compute a deterministic SHA-256 hash over stable evidence fields.

    The hash intentionally excludes volatile metadata (rank, score, timestamps)
    so the same source content resolves to the same hash regardless of retrieval
    ordering or timing.
    """

    stable = "\n".join(
        (
            str(source_kind or "").strip().lower(),
            str(provider or "").strip().lower(),
            str(url or "").strip(),
            str(title or "").strip(),
            str(snippet or "").strip(),
            str(text or "").strip(),
        )
    )
    digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return digest


def _is_valid_web_url(url: str) -> bool:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    return bool(parsed.netloc.strip())


def screen_prompt_injection(text: str) -> list[str]:
    """Return a list of prompt-injection flag tokens for obvious smuggling.

    Returns an empty list when no obvious instruction-smuggling phrase is
    present. This is a conservative heuristic, not a complete classifier.
    """

    haystack = " ".join(str(text or "").strip().lower().split())
    if not haystack:
        return []
    flags: list[str] = []
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern in haystack:
            flags.append(_INJECTION_FLAG)
            break
    return flags


def _freshness_label(retrieved_at: str) -> str | None:
    raw = str(retrieved_at or "").strip()
    if not raw:
        return None
    return "observed"


def intake_candidate(
    item: SearchResultItem,
    *,
    request: SearchProviderRequest,
    observed_at: str | None = None,
) -> WebEvidenceGateResult:
    """Run one candidate through the intake gate and return its decision.

    Provenance is preserved on the returned result even when the item is
    blocked, so trace/debug surfaces can explain what was rejected and why.
    """

    url = str(item.url or "").strip()
    title = str(item.title or "").strip()
    snippet = str(item.snippet or "").strip()
    text = str(item.text or "").strip()
    evidence_text = snippet or text
    content_hash = compute_content_hash(
        url=url,
        title=title,
        snippet=snippet,
        text=text,
        provider=item.provider,
        source_kind=item.source_kind,
    )
    observed = str(observed_at or "").strip() or _utc_now_iso()

    envelope = WebEvidenceEnvelope(
        evidence_id=f"we_{uuid.uuid5(uuid.NAMESPACE_URL, content_hash).hex}",
        request_id=request.request_id,
        provider=item.provider,
        source_kind=item.source_kind,
        url=url,
        title=title,
        snippet=snippet,
        text=text,
        rank=item.rank,
        score=item.score,
        retrieved_at=str(item.retrieved_at or "").strip() or observed,
        observed_at=observed,
        content_hash=content_hash,
        freshness_label=_freshness_label(item.retrieved_at),
        citation=dict(item.citation or {}),
        provider_metadata=dict(item.provider_metadata or {}),
        query=request.query,
        user_id=request.user_id,
        thread_id=request.thread_id,
        project_id=request.project_id,
        source_message_id=request.source_message_id,
    )

    provenance = {
        "evidence_id": envelope.evidence_id,
        "request_id": request.request_id,
        "provider": envelope.provider,
        "source_kind": envelope.source_kind,
        "source_url": envelope.url,
        "query": request.query,
        "rank": envelope.rank,
        "content_hash": envelope.content_hash,
        "user_id": envelope.user_id,
        "thread_id": envelope.thread_id,
        "project_id": envelope.project_id,
        "source_message_id": envelope.source_message_id,
    }

    flags: list[str] = []
    block_reason: str | None = None

    if not title and not evidence_text:
        flags.append(_EMPTY_EVIDENCE_FLAG)
        block_reason = RemoteRecallFailureReason.NORMALIZATION_FAILED.value
        return WebEvidenceGateResult(
            envelope=envelope,
            gate_decision=WebEvidenceGateDecision.BLOCKED.value,
            block_reason=block_reason,
            eligible_for_synthesis=False,
            prompt_injection_flags=flags,
            provenance=provenance,
        )

    if not _is_valid_web_url(url):
        flags.append(_MALFORMED_URL_FLAG)
        block_reason = RemoteRecallFailureReason.NORMALIZATION_FAILED.value
        return WebEvidenceGateResult(
            envelope=envelope,
            gate_decision=WebEvidenceGateDecision.BLOCKED.value,
            block_reason=block_reason,
            eligible_for_synthesis=False,
            prompt_injection_flags=flags,
            provenance=provenance,
        )

    # Screen the combined visible text for obvious instruction smuggling. Web
    # evidence is data; untrusted instructions must never become executable,
    # system, or developer instructions.
    injection_flags = screen_prompt_injection(f"{title} {evidence_text}")
    if injection_flags:
        return WebEvidenceGateResult(
            envelope=envelope,
            gate_decision=WebEvidenceGateDecision.BLOCKED.value,
            block_reason=RemoteRecallFailureReason.SAFETY_SCREEN_BLOCKED.value,
            eligible_for_synthesis=False,
            prompt_injection_flags=injection_flags,
            provenance=provenance,
        )

    return WebEvidenceGateResult(
        envelope=envelope,
        gate_decision=WebEvidenceGateDecision.ELIGIBLE_FOR_SYNTHESIS.value,
        block_reason=None,
        eligible_for_synthesis=True,
        prompt_injection_flags=[],
        provenance=provenance,
    )


def intake_results(
    items: Iterable[SearchResultItem],
    *,
    request: SearchProviderRequest,
    observed_at: str | None = None,
) -> tuple[list[WebEvidenceEnvelope], list[WebEvidenceGateResult]]:
    """Run all candidates through the gate.

    Returns ``(eligible_envelopes, all_gate_results)``. ``eligible_envelopes``
    contains only synthesis-eligible evidence, in input order. ``all_gate_results``
    preserves blocked/diagnostic decisions for trace surfaces.
    """

    eligible: list[WebEvidenceEnvelope] = []
    results: list[WebEvidenceGateResult] = []
    for item in items:
        decision = intake_candidate(item, request=request, observed_at=observed_at)
        results.append(decision)
        if decision.eligible_for_synthesis:
            eligible.append(decision.envelope)
    return eligible, results


__all__ = [
    "compute_content_hash",
    "intake_candidate",
    "intake_results",
    "screen_prompt_injection",
]
