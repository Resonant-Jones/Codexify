"""Pure interface contracts for future Guardian Evidence Packet reducers.

This module defines types and bounded vocabulary only. It does not reduce
evidence, generate packets, validate packets, or invoke any runtime service.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from guardian.evidence_packets.contracts import (
    false_authority_state,
    is_allowed_review_depth,
)

REDUCER_CONTRACT_VERSION = "guardian_evidence_packet_reducer_contract.v1"

ALLOWED_REDUCER_INPUT_CLASSES = frozenset({
    "static_docs",
    "static_fixtures",
    "validation_result",
    "command_run_snapshot",
    "command_run_event_snapshot",
    "receipt_metadata",
    "proof_index",
    "test_result_summary",
    "operator_supplied_context",
})

ALLOWED_REDUCER_OUTPUT_CLASSES = frozenset({
    "GuardianEvidencePacket",
    "GuardianEvidencePacketStaticValidationResult",
    "reducer_diagnostics_summary",
})

REDUCER_LIFECYCLE_STEPS = (
    "receive_bounded_evidence_input_set",
    "classify_input_classes",
    "assign_evidence_refs",
    "extract_candidate_claims",
    "bind_candidate_claims_to_evidence_refs",
    "mark_unsupported_blocked_inferred_or_not_evaluated_claims",
    "preserve_uncertainty",
    "preserve_forbidden_interpretations",
    "set_authority_locks",
    "select_next_gate_options",
    "produce_guardian_evidence_packet",
    "run_static_validation",
    "return_packet_plus_validation_result_for_human_review",
    "stop",
)
REDUCER_STOP_STEP = "stop"


@dataclass(frozen=True)
class ReducerInputRef:
    """A bounded, non-authoritative reference supplied to a future reducer."""

    input_id: str
    input_class: str
    source_ref: str
    evidence_posture: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not is_allowed_reducer_input_class(self.input_class):
            raise ValueError(f"Disallowed reducer input class: {self.input_class!r}")
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True)
class ReducerInputBundle:
    """A bounded set of reducer inputs and explicit operator context."""

    bundle_id: str
    review_depth: str
    inputs: tuple[ReducerInputRef, ...]
    operator_context: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not is_allowed_review_depth(self.review_depth):
            raise ValueError(f"Disallowed reducer review depth: {self.review_depth!r}")
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "operator_context", tuple(self.operator_context))


@dataclass(frozen=True)
class ReducerDiagnosticsSummary:
    """Bounded diagnostics about a future reducer pass, not packet truth."""

    reducer_contract_version: str
    lifecycle_steps_completed: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    limits: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        steps = tuple(self.lifecycle_steps_completed)
        if not lifecycle_is_prefix(steps):
            raise ValueError("lifecycle_steps_completed must be an ordered lifecycle prefix")
        object.__setattr__(self, "lifecycle_steps_completed", steps)
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "limits", tuple(self.limits))


@dataclass(frozen=True)
class ReducerResult:
    """A future reducer handoff bundle with no truth or execution semantics."""

    packet: Mapping[str, object] | None
    validation_result: Mapping[str, object] | None
    diagnostics: ReducerDiagnosticsSummary


def is_allowed_reducer_input_class(value: object) -> bool:
    """Return whether *value* is an allowed future reducer input class."""
    return isinstance(value, str) and value in ALLOWED_REDUCER_INPUT_CLASSES


def is_allowed_reducer_output_class(value: object) -> bool:
    """Return whether *value* is an allowed future reducer output class."""
    return isinstance(value, str) and value in ALLOWED_REDUCER_OUTPUT_CLASSES


def reducer_lifecycle_index(step: str) -> int:
    """Return the zero-based lifecycle index for *step*."""
    try:
        return REDUCER_LIFECYCLE_STEPS.index(step)
    except ValueError as exc:
        raise ValueError(f"Unknown reducer lifecycle step: {step!r}") from exc


def lifecycle_is_prefix(steps: tuple[str, ...]) -> bool:
    """Return whether *steps* is an ordered prefix of the reducer lifecycle."""
    normalized = tuple(steps)
    return normalized == REDUCER_LIFECYCLE_STEPS[:len(normalized)]


def reducer_default_authority_state() -> dict[str, bool]:
    """Return a fresh all-false authority state from the packet contract."""
    return false_authority_state()


def reducer_limits() -> tuple[str, ...]:
    """Return stable non-action boundaries for future reducer implementations."""
    return (
        "does not execute",
        "does not ingest",
        "does not write receipts",
        "does not mutate WorkOrders",
        "does not write Execution Ledger entries",
        "does not call command bus",
        "does not call Codex Runner",
        "does not invoke Pi Loop",
        "does not mutate source",
        "does not execute providers",
    )
