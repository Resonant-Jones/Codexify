"""Continuity Compiler — pure deterministic contract harness.

This module is a **pure contract harness** for the Continuity Compiler
compilation seam. It transforms explicit in-memory ``ContextPacket`` inputs
into an inert ``RealityState`` output using deterministic, side-effect-free
functions.

**Implementation status**: contract harness only; no runtime behavior exists.
**Persistence**: none. No DB reads/writes, no migrations, no schema constraints.
**Routes**: none. No API endpoints.
**Workers**: none. No queue consumption, no task publishing, no heartbeats.
**Graph**: none. No Neo4j writes/reads, no graph enrichment.
**Browser**: none. No browser capture, no automation.
**Sync**: none. No federation, no peer sync.
**Providers**: none. No model calls, no provider routing, no inference.
**Retrieval**: none. No vector search, no context broker, no RAG.
**Release**: not a release support claim.

This is step 3 of ADR-030's approved implementation order (deterministic
compiler I/O shape tests), following the pure backend contract types in
``guardian.continuity.contracts``.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from guardian.continuity.contracts import (
    ContextPacket,
    ContinuityProvenance,
    DecisionRecord,
    OpenLoopRecord,
    RealityScope,
    RealityState,
    RejectedPathRecord,
    validate_context_packet,
    validate_reality_state,
)


# ── Compile result ──────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class ContinuityCompileResult:
    """The result of a single compile_reality_state call.

    ``state`` — the compiled RealityState (always present, even on empty input).
    ``errors`` — structural validation errors from validate_reality_state, or a
        no-valid-packets message when no usable packets were found.
    ``warnings`` — per-packet validation warnings for packets that failed
        individual validate_context_packet checks.
    ``ignored_packet_ids`` — IDs of packets that failed validation and were
        excluded from compilation.
    """

    state: RealityState
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    ignored_packet_ids: tuple[str, ...] = ()


# ── Pure helpers ────────────────────────────────────────────────────────────


def packet_sort_key(packet: ContextPacket) -> tuple[str, str]:
    """Return a deterministic sort key: (created_at, packet_id).

    Does not parse dates. Does not mutate packets.
    """
    return (packet.created_at, packet.packet_id)


def extract_string_sequence(
    payload: Mapping[str, Any], key: str
) -> tuple[str, ...]:
    """Extract a tuple of non-empty strings from *payload*[*key*].

    Accepts a single string or a list/tuple of strings.
    Ignores non-string values. Strips whitespace. Preserves order.
    Does not deduplicate.
    """
    raw = payload.get(key)
    if raw is None:
        return ()

    if isinstance(raw, str):
        stripped = raw.strip()
        return (stripped,) if stripped else ()

    if isinstance(raw, (list, tuple)):
        result: list[str] = []
        for item in raw:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    result.append(stripped)
        return tuple(result)

    return ()


def dedupe_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return a tuple of unique values preserving first-occurrence order.

    Empty strings are excluded.
    """
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return tuple(result)


def derive_compiled_at(packets: Sequence[ContextPacket]) -> str:
    """Return the latest ``created_at`` string after deterministic sorting.

    If no packets exist, returns an empty string.
    """
    if not packets:
        return ""
    sorted_packets = sorted(packets, key=packet_sort_key)
    return sorted_packets[-1].created_at


def derive_state_id(
    scope: RealityScope, source_packet_ids: Sequence[str]
) -> str:
    """Return a deterministic state ID of the form ``reality-{scope}-{digest}``.

    The digest is a SHA-256 hash over (scope, *sorted(source_packet_ids))
    truncated to the first 16 hex characters. No randomness, no current time.
    """
    payload = scope + "\n" + "\n".join(sorted(source_packet_ids))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"reality-{scope}-{digest[:16]}"


# ── Compilation ─────────────────────────────────────────────────────────────


def compile_reality_state(
    packets: Sequence[ContextPacket],
    *,
    scope: RealityScope,
    schema_version: str = "0.1",
    active_branch: str | None = None,
    confidence: float | None = None,
) -> ContinuityCompileResult:
    """Compile a sequence of ContextPackets into a RealityState.

    This is a pure, deterministic function. It performs no IO, calls no
    providers, performs no retrieval, reads no files, and inspects no browser
    state.

    Only explicit structured payload fields are read. The compiler does not
    infer facts from ``summary``, call models, or summarise text.

    Parameters
    ----------
    packets: Sequence of ContextPacket to compile.
    scope: The RealityScope for the output RealityState.
    schema_version: Passed through to RealityState.schema_version.
    active_branch: Passed through to RealityState.active_branch.
    confidence: Passed through to RealityState.confidence.

    Returns
    -------
    ContinuityCompileResult with the compiled state, plus any errors, warnings,
    and ignored packet IDs.
    """
    warnings: list[str] = []
    ignored: list[str] = []

    # Validate and filter packets.
    valid_packets: list[ContextPacket] = []
    for packet in packets:
        packet_errors = validate_context_packet(packet)
        if packet_errors:
            ignored.append(packet.packet_id)
            for err in packet_errors:
                warnings.append(f"packet {packet.packet_id}: {err}")
        else:
            valid_packets.append(packet)

    # Empty / no-valid-packets case.
    if not valid_packets:
        state = RealityState(
            state_id=derive_state_id(scope, ()),
            schema_version=schema_version,
            scope=scope,
            compiled_at="",
            source_packet_ids=(),
            active_branch=active_branch,
            confidence=confidence,
        )
        return ContinuityCompileResult(
            state=state,
            errors=("no valid packets to compile",),
            warnings=tuple(warnings),
            ignored_packet_ids=tuple(ignored),
        )

    # Sort valid packets deterministically.
    sorted_packets = sorted(valid_packets, key=packet_sort_key)
    source_packet_ids = tuple(p.packet_id for p in sorted_packets)

    # Collect simple string fields from all packets.
    all_artifacts: list[str] = []
    all_assumptions: list[str] = []
    all_risks: list[str] = []
    all_next_actions: list[str] = []

    # Collect structured records.
    all_decisions: list[DecisionRecord] = []
    all_open_loops: list[OpenLoopRecord] = []
    all_rejected_paths: list[RejectedPathRecord] = []

    for packet in sorted_packets:
        # Simple string sequences.
        all_artifacts.extend(extract_string_sequence(packet.payload, "active_artifacts"))
        all_assumptions.extend(extract_string_sequence(packet.payload, "assumptions"))
        all_risks.extend(extract_string_sequence(packet.payload, "risks"))
        all_next_actions.extend(extract_string_sequence(packet.payload, "next_actions"))

        # Accepted decisions.
        decision_strings = extract_string_sequence(packet.payload, "accepted_decisions")
        for idx_str, text in enumerate(decision_strings):
            decision_id = f"decision-{len(all_decisions) + 1}"
            all_decisions.append(
                DecisionRecord(
                    decision_id=decision_id,
                    summary=text,
                    accepted_at=packet.created_at,
                    provenance=ContinuityProvenance(
                        source_packet_ids=(packet.packet_id,),
                        **{
                            k: v
                            for k, v in dataclasses.asdict(packet.provenance).items()
                            if v
                        },
                    ),
                )
            )

        # Open loops.
        loop_strings = extract_string_sequence(packet.payload, "open_loops")
        for idx_str, text in enumerate(loop_strings):
            loop_id = f"loop-{len(all_open_loops) + 1}"
            all_open_loops.append(
                OpenLoopRecord(
                    loop_id=loop_id,
                    summary=text,
                    status="open",
                    provenance=ContinuityProvenance(
                        source_packet_ids=(packet.packet_id,),
                        **{
                            k: v
                            for k, v in dataclasses.asdict(packet.provenance).items()
                            if v
                        },
                    ),
                )
            )

        # Rejected paths.
        path_strings = extract_string_sequence(packet.payload, "rejected_paths")
        for idx_str, text in enumerate(path_strings):
            path_id = f"path-{len(all_rejected_paths) + 1}"
            all_rejected_paths.append(
                RejectedPathRecord(
                    path_id=path_id,
                    summary=text,
                    status="rejected",
                    provenance=ContinuityProvenance(
                        source_packet_ids=(packet.packet_id,),
                        **{
                            k: v
                            for k, v in dataclasses.asdict(packet.provenance).items()
                            if v
                        },
                    ),
                )
            )

    # Build RealityState.
    state = RealityState(
        state_id=derive_state_id(scope, source_packet_ids),
        schema_version=schema_version,
        scope=scope,
        compiled_at=derive_compiled_at(sorted_packets),
        source_packet_ids=source_packet_ids,
        active_branch=active_branch,
        accepted_decisions=tuple(all_decisions),
        open_loops=tuple(all_open_loops),
        rejected_paths=tuple(all_rejected_paths),
        active_artifacts=dedupe_preserving_order(all_artifacts),
        assumptions=dedupe_preserving_order(all_assumptions),
        risks=dedupe_preserving_order(all_risks),
        next_actions=dedupe_preserving_order(all_next_actions),
        confidence=confidence,
    )

    # Validate and collect errors.
    state_errors = validate_reality_state(state)

    return ContinuityCompileResult(
        state=state,
        errors=state_errors,
        warnings=tuple(warnings),
        ignored_packet_ids=tuple(ignored),
    )


# ── Public export list ──────────────────────────────────────────────────────

__all__ = [
    "ContinuityCompileResult",
    "compile_reality_state",
    "packet_sort_key",
    "extract_string_sequence",
    "dedupe_preserving_order",
    "derive_compiled_at",
    "derive_state_id",
]
