"""Pure dry-run skeleton for future Guardian Evidence Packet reducers.

The skeleton demonstrates lifecycle stop semantics only. It does not inspect
evidence, generate packets, validate packets, or invoke any external surface.
"""

from __future__ import annotations

from guardian.evidence_packets.reducer_contracts import (
    REDUCER_CONTRACT_VERSION,
    ReducerDiagnosticsSummary,
    ReducerInputBundle,
    ReducerResult,
    reducer_limits,
)

DRY_RUN_STOP_REASON = "dry_run_no_reduction"
DRY_RUN_WARNING = (
    "Reducer dry-run skeleton does not produce GuardianEvidencePacket output."
)


def dry_run_reducer(input_bundle: ReducerInputBundle) -> ReducerResult:
    """Return bounded stop diagnostics without reducing *input_bundle*."""
    if not isinstance(input_bundle, ReducerInputBundle):
        raise TypeError("dry_run_reducer requires a ReducerInputBundle")

    diagnostics = ReducerDiagnosticsSummary(
        reducer_contract_version=REDUCER_CONTRACT_VERSION,
        lifecycle_steps_completed=(
            "receive_bounded_evidence_input_set",
            "classify_input_classes",
            "stop",
        ),
        warnings=(DRY_RUN_WARNING,),
        limits=reducer_limits() + (f"stop reason: {DRY_RUN_STOP_REASON}",),
    )
    return ReducerResult(
        packet=None,
        validation_result=None,
        diagnostics=diagnostics,
    )
