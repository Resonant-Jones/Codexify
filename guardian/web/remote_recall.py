"""Remote Recall orchestration helper.

Remote Recall is the governed Search-as-RAG web-evidence lane. This helper is
the single orchestration seam that:

- decides whether Search-as-RAG should execute for a given retrieval posture
- enforces config and egress gates before any provider adapter invocation
- calls the configured provider adapter
- passes every candidate result through the Web Evidence Intake Gate
- returns synthesis-eligible evidence plus blocked/diagnostic summaries

It executes **only** behind a policy-approved explicit ``global_search`` route.
Local, conversation, workspace, and ordinary broad-retrieval postures stay out
of scope. Remote Recall is retrieval evidence, not a separate answer oracle.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from guardian.context.retrieval_router_policy import (
    ContextAssemblyPolicy,
    is_global_search_posture,
)
from guardian.core.config import Settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.protocol_tokens import (
    RemoteRecallFailureReason,
    RemoteRecallSourceKind,
    RemoteRecallTraceEvent,
)
from guardian.web.contracts import (
    SearchProviderRequest,
    SearchProviderResult,
    WebEvidenceEnvelope,
    WebEvidenceGateResult,
)
from guardian.web.evidence_gate import intake_results
from guardian.web.groq_search_adapter import GroqSearchAdapter

logger = logging.getLogger(__name__)

# Maps a configured provider id to its adapter factory and source kind. Future
# adapters (wikipedia, arxiv, ...) plug in here without touching orchestration.
_PROVIDER_REGISTRY = {
    "groq": {
        "adapter": GroqSearchAdapter,
        "source_kind": RemoteRecallSourceKind.GROQ_WEB_SEARCH.value,
    },
}


@dataclass(frozen=True)
class RemoteRecallConfig:
    """Resolved Remote Recall operator configuration."""

    enabled: bool
    provider: str
    max_results: int
    timeout_seconds: float
    groq_web_search_enabled: bool


def resolve_remote_recall_config(settings: Settings) -> RemoteRecallConfig:
    return RemoteRecallConfig(
        enabled=bool(getattr(settings, "REMOTE_RECALL_ENABLED", False)),
        provider=str(getattr(settings, "REMOTE_RECALL_PROVIDER", "groq") or "groq")
        .strip()
        .lower(),
        max_results=int(getattr(settings, "REMOTE_RECALL_MAX_RESULTS", 5) or 5),
        timeout_seconds=float(
            getattr(settings, "REMOTE_RECALL_TIMEOUT_SECONDS", 20.0) or 20.0
        ),
        groq_web_search_enabled=bool(
            getattr(settings, "GROQ_WEB_SEARCH_ENABLED", False)
        ),
    )


@dataclass(frozen=True)
class RemoteRecallOutcome:
    """Outcome of one Remote Recall orchestration pass.

    ``evidence`` holds only synthesis-eligible envelopes. ``gate_results``
    preserves every gate decision (including blocked items) for trace/debug
    surfaces. ``failure_reason`` is a canonical
    :class:`RemoteRecallFailureReason` value when the lane did not yield
    evidence.
    """

    invoked: bool
    provider: str | None
    source_kind: str | None
    evidence: list[WebEvidenceEnvelope] = field(default_factory=list)
    gate_results: list[WebEvidenceGateResult] = field(default_factory=list)
    failure_reason: str | None = None
    trace_event: str = RemoteRecallTraceEvent.SKIPPED.value
    provider_result_status: str | None = None
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    def as_trace(self) -> dict[str, Any]:
        return {
            "invoked": self.invoked,
            "provider": self.provider,
            "source_kind": self.source_kind,
            "trace_event": self.trace_event,
            "failure_reason": self.failure_reason,
            "evidence_count": self.evidence_count,
            "eligible_count": self.evidence_count,
            "blocked_count": sum(
                1 for r in self.gate_results if not r.eligible_for_synthesis
            ),
            "provider_result_status": self.provider_result_status,
            "gate_decisions": [
                {
                    "evidence_id": r.envelope.evidence_id,
                    "gate_decision": r.gate_decision,
                    "block_reason": r.block_reason,
                    "prompt_injection_flags": list(r.prompt_injection_flags),
                    "url": r.envelope.url,
                    "content_hash": r.envelope.content_hash,
                }
                for r in self.gate_results
            ],
        }


def _skipped(
    failure_reason: RemoteRecallFailureReason,
    *,
    provider: str | None = None,
    source_kind: str | None = None,
) -> RemoteRecallOutcome:
    return RemoteRecallOutcome(
        invoked=False,
        provider=provider,
        source_kind=source_kind,
        failure_reason=failure_reason.value,
        trace_event=RemoteRecallTraceEvent.SKIPPED.value,
        trace={
            "failure_reason": failure_reason.value,
            "trace_event": RemoteRecallTraceEvent.SKIPPED.value,
        },
    )


def _should_execute(
    *,
    retrieval_policy: ContextAssemblyPolicy | None,
    config: RemoteRecallConfig,
    settings: Settings,
    provider: str,
) -> RemoteRecallFailureReason | None:
    """Return a failure reason when execution must be skipped, else None."""

    if not is_global_search_posture(retrieval_policy):
        return RemoteRecallFailureReason.NOT_GLOBAL_SEARCH_POSTURE
    if not config.enabled:
        return RemoteRecallFailureReason.DISABLED
    if bool(getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", True)):
        return RemoteRecallFailureReason.LOCAL_ONLY_MODE
    if provider not in _PROVIDER_REGISTRY:
        return RemoteRecallFailureReason.PROVIDER_UNAUTHORIZED
    if provider == "groq" and not config.groq_web_search_enabled:
        return RemoteRecallFailureReason.PROVIDER_NOT_CONFIGURED
    # Enforce egress before any adapter invocation. The specific reason is
    # resolved from the live settings so traces carry a canonical token.
    try:
        assert_egress_allowed(provider, settings=settings)
    except EgressDeniedError:
        if bool(getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", True)):
            return RemoteRecallFailureReason.LOCAL_ONLY_MODE
        if not bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS", False)):
            return RemoteRecallFailureReason.EGRESS_BLOCKED
        return RemoteRecallFailureReason.EGRESS_BLOCKED
    return None


async def run_remote_recall(
    *,
    query: str,
    retrieval_policy: ContextAssemblyPolicy | None,
    settings: Settings,
    user_id: str | None = None,
    thread_id: int | None = None,
    project_id: int | None = None,
    source_message_id: int | None = None,
    adapter: Any | None = None,
) -> RemoteRecallOutcome:
    """Run one Remote Recall Search-as-RAG pass.

    ``adapter`` may be injected for tests. When omitted, the provider's
    registered adapter is constructed from ``settings``.
    """

    config = resolve_remote_recall_config(settings)
    provider = config.provider
    registry_entry = _PROVIDER_REGISTRY.get(provider)
    source_kind = registry_entry["source_kind"] if registry_entry else None

    skip_reason = _should_execute(
        retrieval_policy=retrieval_policy,
        config=config,
        settings=settings,
        provider=provider,
    )
    if skip_reason is not None:
        logger.info(
            "[remote-recall] skipped provider=%s reason=%s",
            provider,
            skip_reason.value,
        )
        return _skipped(
            skip_reason, provider=provider, source_kind=source_kind
        )

    request = SearchProviderRequest(
        request_id=f"rr_{uuid.uuid4().hex}",
        query=str(query or ""),
        provider=provider,
        source_kind=source_kind or RemoteRecallSourceKind.GROQ_WEB_SEARCH.value,
        user_id=user_id,
        thread_id=thread_id,
        project_id=project_id,
        source_message_id=source_message_id,
        max_results=config.max_results,
    )

    if adapter is None:
        adapter = registry_entry["adapter"](settings)

    try:
        result: SearchProviderResult = adapter.invoke(request)
    except Exception as exc:
        logger.warning(
            "[remote-recall] adapter %s raised: %s", provider, exc
        )
        return RemoteRecallOutcome(
            invoked=True,
            provider=provider,
            source_kind=source_kind,
            failure_reason=RemoteRecallFailureReason.ADAPTER_ERROR.value,
            trace_event=RemoteRecallTraceEvent.BLOCKED.value,
            trace={
                "provider": provider,
                "source_kind": source_kind,
                "failure_reason": RemoteRecallFailureReason.ADAPTER_ERROR.value,
                "trace_event": RemoteRecallTraceEvent.BLOCKED.value,
            },
        )

    if result.blocked_reason or result.status == "error":
        return RemoteRecallOutcome(
            invoked=True,
            provider=provider,
            source_kind=source_kind,
            failure_reason=result.blocked_reason
            or RemoteRecallFailureReason.PROVIDER_UNAVAILABLE.value,
            provider_result_status=result.status,
            trace_event=RemoteRecallTraceEvent.BLOCKED.value,
            trace={
                "provider": provider,
                "source_kind": source_kind,
                "provider_result_status": result.status,
                "blocked_reason": result.blocked_reason,
                "trace_event": RemoteRecallTraceEvent.BLOCKED.value,
            },
        )

    eligible, gate_results = intake_results(
        result.results,
        request=request,
    )

    failure_reason: str | None = None
    if not eligible:
        failure_reason = RemoteRecallFailureReason.EMPTY_RESULT_SET.value

    trace_event = (
        RemoteRecallTraceEvent.COMPLETED.value
        if eligible
        else RemoteRecallTraceEvent.BLOCKED.value
    )

    return RemoteRecallOutcome(
        invoked=True,
        provider=provider,
        source_kind=source_kind,
        evidence=eligible,
        gate_results=gate_results,
        failure_reason=failure_reason,
        provider_result_status=result.status,
        trace_event=trace_event,
        trace={
            "provider": provider,
            "source_kind": source_kind,
            "provider_result_status": result.status,
            "raw_result_count": result.result_count,
            "eligible_count": len(eligible),
            "blocked_count": sum(
                1 for r in gate_results if not r.eligible_for_synthesis
            ),
            "trace_event": trace_event,
        },
    )


__all__ = [
    "RemoteRecallConfig",
    "RemoteRecallOutcome",
    "resolve_remote_recall_config",
    "run_remote_recall",
]
