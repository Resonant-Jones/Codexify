"""Stage 2G pre-request tool-capability projection for one Whoosh'd target.

This module owns a narrow pre-request eligibility snapshot.  It consumes
already-parsed current Whoosh'd inventory evidence together with the
existing Stage 2F.1b qualification comparator and an explicit
caller-supplied exposure decision.  It does not advertise a capability,
grant command authority, or wire into the chat completion flow.

The projection function is pure: it takes the parsed inventory snapshot and
the qualification record, never the network, filesystem, package metadata,
or Markdown proof documents.  Two independent evaluations with different
inventory snapshots never share cached state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from guardian.providers.whooshd_control_plane import (
    WhooshdRuntimeInventoryEvidence,
)
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
    WhooshdQualificationComparison,
    WhooshdQualificationOutcome,
    WhooshdQualificationRecord,
    compare_whooshd_inventory_qualification,
)

WhooshdToolCapabilityOutcome = Literal["eligible", "ineligible"]

_INELIGIBLE = "ineligible"
_ELIGIBLE = "eligible"


@dataclass(frozen=True)
class WhooshdToolCapabilityProjection:
    """Bounded one-snapshot explanation of pre-request tool eligibility.

    The projection is intentionally narrow: it names the target identity, the
    qualification outcome, the readiness state, and the exposure decision.
    It deliberately does not copy the full attestation material, persist any
    state, or expose raw paths/timestamps/credentials.
    """

    outcome: WhooshdToolCapabilityOutcome
    invocation_model_id: str
    runtime_kind: str
    adapter_name: str
    qualification_outcome: WhooshdQualificationOutcome
    runtime_ready: bool
    exposure_allowed: bool
    reason: str
    qualification_reason: str


def _deny(
    *,
    inventory: WhooshdRuntimeInventoryEvidence | None,
    comparison: WhooshdQualificationComparison,
    exposure_allowed: bool,
    reason: str,
) -> WhooshdToolCapabilityProjection:
    """Build the bounded denial projection with a stable identity fallback."""

    if inventory is None:
        return WhooshdToolCapabilityProjection(
            outcome=_INELIGIBLE,
            invocation_model_id="",
            runtime_kind="",
            adapter_name="",
            qualification_outcome=comparison.outcome,
            runtime_ready=False,
            exposure_allowed=exposure_allowed,
            reason=reason,
            qualification_reason=comparison.reason,
        )
    return WhooshdToolCapabilityProjection(
        outcome=_INELIGIBLE,
        invocation_model_id=inventory.invocation_model_id,
        runtime_kind=inventory.runtime_kind,
        adapter_name=inventory.adapter_name,
        qualification_outcome=comparison.outcome,
        runtime_ready=inventory.is_ready(),
        exposure_allowed=exposure_allowed,
        reason=reason,
        qualification_reason=comparison.reason,
    )


def project_whooshd_tool_capability(
    *,
    inventory: WhooshdRuntimeInventoryEvidence | None,
    record: WhooshdQualificationRecord | None = None,
    exposure_allowed: bool,
) -> WhooshdToolCapabilityProjection:
    """Return the Stage 2G pre-request tool eligibility snapshot.

    The function is pure; it never calls the network, filesystem, package
    metadata, or the Command Bus.  It consumes only already-parsed inventory
    evidence plus the frozen qualification record.

    Positive eligibility requires every element of the capability equation
    below to hold for the same exact target:

    - the parsed inventory entry names the exact qualified target;
    - the inventory copy of the attestation is internally consistent
      (re-canonicalized material reproduces the producer-emitted digest);
    - the comparison against the frozen record is ``MATCH``;
    - current readiness reports ``loaded=True`` and ``model_lifecycle="ready"``;
    - the caller explicitly supplies ``exposure_allowed=True``.

    ``exposure_allowed`` has no permissive default; callers must pass it
    explicitly to prove the positive path.
    """

    resolved_record = record or STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    comparison = compare_whooshd_inventory_qualification(
        resolved_record, inventory
    )
    if inventory is None:
        return _deny(
            inventory=None,
            comparison=comparison,
            exposure_allowed=exposure_allowed,
            reason="inventory_missing",
        )
    if comparison.outcome is not WhooshdQualificationOutcome.MATCH:
        return _deny(
            inventory=inventory,
            comparison=comparison,
            exposure_allowed=exposure_allowed,
            reason=f"qualification_{comparison.outcome.value.lower()}",
        )
    if not inventory.is_ready():
        return _deny(
            inventory=inventory,
            comparison=comparison,
            exposure_allowed=exposure_allowed,
            reason="runtime_not_ready",
        )
    if not exposure_allowed:
        return _deny(
            inventory=inventory,
            comparison=comparison,
            exposure_allowed=False,
            reason="exposure_denied",
        )
    return WhooshdToolCapabilityProjection(
        outcome=_ELIGIBLE,
        invocation_model_id=inventory.invocation_model_id,
        runtime_kind=inventory.runtime_kind,
        adapter_name=inventory.adapter_name,
        qualification_outcome=WhooshdQualificationOutcome.MATCH,
        runtime_ready=True,
        exposure_allowed=True,
        reason="qualified_identity_match",
        qualification_reason=comparison.reason,
    )
