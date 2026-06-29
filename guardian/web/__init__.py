"""Remote Recall Search-as-RAG runtime seam.

This package implements the first thin, governed web-evidence lane for Codexify
Remote Recall. It is provider-neutral at the boundary and ships only the Groq
adapter as the first concrete execution surface.

The lane is gated and off by default. It may execute only when:

- the retrieval posture resolves to explicit ``global_search``
- ``REMOTE_RECALL_ENABLED`` is true
- provider-specific feature flags, credentials, and egress are all enabled

Raw web evidence never reaches synthesis: provider output must pass through the
Web Evidence Intake Gate (:mod:`guardian.web.evidence_gate`) before it is
eligible for completion-context injection.

See:
- docs/architecture/web-agent-spec.md
- docs/architecture/web-search-provider-adapter-contract.md
- docs/architecture/web-evidence-intake-gate-contract.md
- docs/architecture/adr/021-Web-Agent-Boundary-and-Retrieval-Contract.md
"""

from __future__ import annotations

from guardian.web.contracts import (
    SearchProviderRequest,
    SearchProviderResult,
    SearchResultItem,
    WebEvidenceEnvelope,
    WebEvidenceGateResult,
)
from guardian.web.evidence_gate import (
    intake_candidate,
    intake_results,
)
from guardian.web.remote_recall import (
    RemoteRecallOutcome,
    run_remote_recall,
)

__all__ = [
    "RemoteRecallOutcome",
    "SearchProviderRequest",
    "SearchProviderResult",
    "SearchResultItem",
    "WebEvidenceEnvelope",
    "WebEvidenceGateResult",
    "intake_candidate",
    "intake_results",
    "run_remote_recall",
]
