"""Ephemeral, cited Migration Chronicle preview generation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from guardian.services.chronicle_interpretation_authorization import (
    ChronicleInterpretationGrant,
)
from guardian.services.chronicle_model_exposure import (
    LocalModelUnavailable,
    ModelExposureError,
    ReviewedEvidenceReference,
    authorize_reviewed_evidence,
    build_local_evidence_messages,
    invoke_local_model,
    validate_preview_output,
)
from guardian.services.imported_history_evidence import ImportedHistoryEvidence


class ChroniclePreviewError(Exception):
    """Content-free preview failure."""


class ChroniclePreviewUnavailable(Exception):
    """Local model service is unavailable; no source content is exposed."""


def generate_chronicle_preview(
    grant: ChronicleInterpretationGrant,
    evidence: ImportedHistoryEvidence,
    reviewed: Sequence[ReviewedEvidenceReference],
    *,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Authorize, expose, invoke local inference, and validate one preview."""
    try:
        exposed = authorize_reviewed_evidence(grant, evidence, reviewed)
        messages = build_local_evidence_messages(exposed)
        raw = invoke_local_model(messages, transport=transport)
        output = validate_preview_output(raw, exposed)
    except LocalModelUnavailable:
        raise ChroniclePreviewUnavailable("Local model unavailable") from None
    except ModelExposureError as exc:
        raise ChroniclePreviewError(str(exc)) from None
    generated_at = datetime.now(timezone.utc).isoformat()
    coverage = asdict(evidence.coverage)
    coverage["selected_thread_ids"] = list(evidence.selected_thread_ids)
    coverage["permitted_origins"] = [
        origin.value for origin in evidence.permitted_origins
    ]
    return {
        "derived": True,
        "ephemeral": True,
        "project_id": grant.project_id,
        "selected_thread_ids": list(grant.thread_ids),
        "selected_origins": [origin.value for origin in grant.origins],
        "read_at": evidence.read_at,
        "generated_at": generated_at,
        "model": {"provider": "local", "tools_enabled": False},
        "summary": output["summary"],
        "observations": output["observations"],
        "coverage": coverage,
        "uncertainty": [
            "This is a bounded imported-history window, not a complete archive summary.",
            "Historical statements are evidence of what was said and do not install present preferences or activity.",
        ],
    }
