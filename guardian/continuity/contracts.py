"""Continuity Protocol Suite — pure backend contract types.

This module is a **pure contract seam** for candidate continuity structures.
It defines inert, importable, deterministic dataclasses, candidate token
aliases, and pure validation helpers.

**Implementation status**: no runtime behavior exists.
**Persistence**: none. No DB reads/writes, no migrations, no schema constraints.
**Routes**: none. No API endpoints, no SSE, no HTTP handlers.
**Workers**: none. No queue consumption, no task publishing, no heartbeats.
**Graph**: none. No Neo4j writes/reads, no graph enrichment.
**Browser**: none. No browser capture, no automation, no tab binding.
**Sync**: none. No federation, no peer sync, no shared reality.
**Providers**: none. No model calls, no provider routing, no inference.
**Release**: not a release support claim. Candidate values only.

This is step 2 of ADR-030's approved implementation order (pure backend
contract types with no persistence), following the token-domain proposal in
``docs/architecture/continuity-token-domain-proposal.md``.
"""

from __future__ import annotations

from typing import Literal, Mapping, TypeAlias

# ── Candidate token type aliases ────────────────────────────────────────────
# These are NOT runtime token registries. They are inert type annotations for
# contract shape use only. Future tasks may promote some values into bounded
# backend/frontend registries, DB constraints, or API contracts.

ContextPacketKind: TypeAlias = Literal[
    "thread",
    "project_reality",
    "browser",
    "git",
    "artifact",
    "persona",
    "provider",
    "retrieval",
    "discovery",
    "open_loop",
    "rejected_path",
]

ContextPacketSensitivity: TypeAlias = Literal[
    "local",
    "private",
    "syncable",
    "shared",
    "restricted",
]

ContextPacketRetention: TypeAlias = Literal[
    "ephemeral",
    "session",
    "project",
    "account",
    "exportable",
    "expires",
]

RealityScope: TypeAlias = Literal[
    "thread",
    "task",
    "project",
    "workspace",
    "user",
    "node",
    "team",
    "dyad",
]

RealityCommitTrigger: TypeAlias = Literal[
    "manual",
    "semantic_delta",
    "heartbeat",
    "artifact_change",
    "git_commit_adjacent",
    "pause_thread",
    "resume_thread",
]

RealityCommitKind: TypeAlias = Literal[
    "state_update",
    "decision_added",
    "open_loop_added",
    "open_loop_resolved",
    "rejected_path_added",
    "artifact_linked",
    "assumption_changed",
    "risk_changed",
]

DiscoveryCommitTrigger: TypeAlias = Literal[
    "new_abstraction",
    "assumption_overturned",
    "concepts_merged",
    "architecture_direction_changed",
    "protocol_boundary_discovered",
    "product_thesis_sharpened",
]

OpenLoopStatus: TypeAlias = Literal[
    "open",
    "blocked",
    "deferred",
    "resolved",
    "stale",
    "cancelled",
]

RejectedPathStatus: TypeAlias = Literal[
    "rejected",
    "superseded",
    "reconsider_allowed",
    "do_not_reopen",
]

ProjectPulseSurfaceKind: TypeAlias = Literal[
    "where_was_i",
    "daily_brief",
    "recent_work",
    "last_commits",
    "open_loops",
    "active_threads",
    "paused_threads",
    "resume_actions",
]

BrowserContextPacketKind: TypeAlias = Literal[
    "page_identity",
    "selected_text",
    "visible_dom_digest",
    "page_summary",
    "tab_binding",
    "user_action",
]

GraphMountMode: TypeAlias = Literal[
    "disabled",
    "inspect_only",
    "enrichment_allowed",
    "preferred_enrichment",
]

ContinuityCacheState: TypeAlias = Literal[
    "missing",
    "fresh",
    "stale",
    "invalidated",
]

PinnedModelStateKind: TypeAlias = Literal[
    "not_pinned",
    "warming",
    "warm",
    "expired",
    "unavailable",
]

ContinuityImplementationGate: TypeAlias = Literal[
    "token_domain_review",
    "storage_contract_review",
    "provenance_export_review",
    "retrieval_router_review",
    "identity_consent_review",
    "operator_truth_review",
    "graph_optionality_review",
    "ui_diagnostics_review",
    "migration_rollback_review",
    "proof_surface_review",
]

# ── Candidate value collections (frozen, immutable) ─────────────────────────

CONTEXT_PACKET_KIND_VALUES: tuple[ContextPacketKind, ...] = (
    "thread", "project_reality", "browser", "git", "artifact",
    "persona", "provider", "retrieval", "discovery", "open_loop",
    "rejected_path",
)

CONTEXT_PACKET_SENSITIVITY_VALUES: tuple[ContextPacketSensitivity, ...] = (
    "local", "private", "syncable", "shared", "restricted",
)

CONTEXT_PACKET_RETENTION_VALUES: tuple[ContextPacketRetention, ...] = (
    "ephemeral", "session", "project", "account", "exportable", "expires",
)

REALITY_SCOPE_VALUES: tuple[RealityScope, ...] = (
    "thread", "task", "project", "workspace", "user", "node", "team", "dyad",
)

REALITY_COMMIT_TRIGGER_VALUES: tuple[RealityCommitTrigger, ...] = (
    "manual", "semantic_delta", "heartbeat", "artifact_change",
    "git_commit_adjacent", "pause_thread", "resume_thread",
)

REALITY_COMMIT_KIND_VALUES: tuple[RealityCommitKind, ...] = (
    "state_update", "decision_added", "open_loop_added",
    "open_loop_resolved", "rejected_path_added", "artifact_linked",
    "assumption_changed", "risk_changed",
)

DISCOVERY_COMMIT_TRIGGER_VALUES: tuple[DiscoveryCommitTrigger, ...] = (
    "new_abstraction", "assumption_overturned", "concepts_merged",
    "architecture_direction_changed", "protocol_boundary_discovered",
    "product_thesis_sharpened",
)

OPEN_LOOP_STATUS_VALUES: tuple[OpenLoopStatus, ...] = (
    "open", "blocked", "deferred", "resolved", "stale", "cancelled",
)

REJECTED_PATH_STATUS_VALUES: tuple[RejectedPathStatus, ...] = (
    "rejected", "superseded", "reconsider_allowed", "do_not_reopen",
)

PROJECT_PULSE_SURFACE_KIND_VALUES: tuple[ProjectPulseSurfaceKind, ...] = (
    "where_was_i", "daily_brief", "recent_work", "last_commits",
    "open_loops", "active_threads", "paused_threads", "resume_actions",
)

BROWSER_CONTEXT_PACKET_KIND_VALUES: tuple[BrowserContextPacketKind, ...] = (
    "page_identity", "selected_text", "visible_dom_digest",
    "page_summary", "tab_binding", "user_action",
)

GRAPH_MOUNT_MODE_VALUES: tuple[GraphMountMode, ...] = (
    "disabled", "inspect_only", "enrichment_allowed", "preferred_enrichment",
)

CONTINUITY_CACHE_STATE_VALUES: tuple[ContinuityCacheState, ...] = (
    "missing", "fresh", "stale", "invalidated",
)

PINNED_MODEL_STATE_KIND_VALUES: tuple[PinnedModelStateKind, ...] = (
    "not_pinned", "warming", "warm", "expired", "unavailable",
)

CONTINUITY_IMPLEMENTATION_GATE_VALUES: tuple[ContinuityImplementationGate, ...] = (
    "token_domain_review", "storage_contract_review",
    "provenance_export_review", "retrieval_router_review",
    "identity_consent_review", "operator_truth_review",
    "graph_optionality_review", "ui_diagnostics_review",
    "migration_rollback_review", "proof_surface_review",
)

# ── Domain name → candidate values map ──────────────────────────────────────

_CANDIDATE_DOMAIN_MAP: Mapping[str, tuple[str, ...]] = {
    "ContextPacketKind": CONTEXT_PACKET_KIND_VALUES,
    "ContextPacketSensitivity": CONTEXT_PACKET_SENSITIVITY_VALUES,
    "ContextPacketRetention": CONTEXT_PACKET_RETENTION_VALUES,
    "RealityScope": REALITY_SCOPE_VALUES,
    "RealityCommitTrigger": REALITY_COMMIT_TRIGGER_VALUES,
    "RealityCommitKind": REALITY_COMMIT_KIND_VALUES,
    "DiscoveryCommitTrigger": DISCOVERY_COMMIT_TRIGGER_VALUES,
    "OpenLoopStatus": OPEN_LOOP_STATUS_VALUES,
    "RejectedPathStatus": REJECTED_PATH_STATUS_VALUES,
    "ProjectPulseSurfaceKind": PROJECT_PULSE_SURFACE_KIND_VALUES,
    "BrowserContextPacketKind": BROWSER_CONTEXT_PACKET_KIND_VALUES,
    "GraphMountMode": GRAPH_MOUNT_MODE_VALUES,
    "ContinuityCacheState": CONTINUITY_CACHE_STATE_VALUES,
    "PinnedModelStateKind": PINNED_MODEL_STATE_KIND_VALUES,
    "ContinuityImplementationGate": CONTINUITY_IMPLEMENTATION_GATE_VALUES,
}

# ── Pure dataclasses ────────────────────────────────────────────────────────

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class ContinuityScope:
    """Scope boundary for a continuity artifact."""

    user_id: str | None = None
    project_id: str | None = None
    thread_id: str | None = None
    task_id: str | None = None
    tab_id: str | None = None
    persona_id: str | None = None
    node_id: str | None = None
    team_id: str | None = None
    dyad_id: str | None = None


@dataclasses.dataclass(frozen=True)
class ContinuitySource:
    """Which surface emitted a continuity artifact."""

    system: str
    plugin: str | None = None
    provider: str | None = None
    origin_ref: str | None = None


@dataclasses.dataclass(frozen=True)
class ContinuityProvenance:
    """Traceable source chain for a continuity artifact."""

    source_packet_ids: tuple[str, ...] = ()
    source_commit_ids: tuple[str, ...] = ()
    source_message_ids: tuple[str, ...] = ()
    source_artifact_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ContextPacket:
    """Self-describing envelope for evidence passing between continuity surfaces."""

    packet_id: str
    schema_version: str
    kind: ContextPacketKind
    scope: ContinuityScope
    source: ContinuitySource
    created_at: str
    summary: str
    payload: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    metadata: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )
    sensitivity: ContextPacketSensitivity = "local"
    retention: ContextPacketRetention = "session"
    integrity: Mapping[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class DecisionRecord:
    """An accepted decision within Reality State."""

    decision_id: str
    summary: str
    accepted_at: str | None = None
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )


@dataclasses.dataclass(frozen=True)
class OpenLoopRecord:
    """An unresolved question, task, decision, or exploration."""

    loop_id: str
    summary: str
    status: OpenLoopStatus = "open"
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )


@dataclasses.dataclass(frozen=True)
class RejectedPathRecord:
    """A direction explicitly considered and discarded."""

    path_id: str
    summary: str
    status: RejectedPathStatus = "rejected"
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )


@dataclasses.dataclass(frozen=True)
class RealityState:
    """Compiled truth surface for a given scope."""

    state_id: str
    schema_version: str
    scope: RealityScope
    compiled_at: str
    source_packet_ids: tuple[str, ...]
    active_branch: str | None = None
    accepted_decisions: tuple[DecisionRecord, ...] = ()
    open_loops: tuple[OpenLoopRecord, ...] = ()
    rejected_paths: tuple[RejectedPathRecord, ...] = ()
    active_artifacts: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    confidence: float | None = None
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )
    expires_or_decays_at: str | None = None


@dataclasses.dataclass(frozen=True)
class RealityCommit:
    """A durable snapshot of Reality State at a point in time."""

    commit_id: str
    schema_version: str
    scope: RealityScope
    kind: RealityCommitKind
    trigger: RealityCommitTrigger
    title: str
    summary: str
    created_at: str
    source_packet_ids: tuple[str, ...] = ()
    previous_state_id: str | None = None
    new_state_id: str | None = None
    provenance: ContinuityProvenance = dataclasses.field(
        default_factory=ContinuityProvenance
    )


# ── Pure helper functions ───────────────────────────────────────────────────


def candidate_values_for(domain_name: str) -> tuple[str, ...]:
    """Return the candidate value tuple for a named domain.

    Returns an empty tuple for unknown domains.
    """
    return _CANDIDATE_DOMAIN_MAP.get(domain_name, ())


def is_candidate_value(domain_name: str, value: str) -> bool:
    """Return True if *value* is a candidate for *domain_name*."""
    return value in candidate_values_for(domain_name)


def _non_empty(value: str, label: str) -> str | None:
    if not value or not value.strip():
        return f"{label} must be non-empty"
    return None


def _in_candidates(value: str, domain: str, label: str) -> str | None:
    if not is_candidate_value(domain, value):
        candidates = ", ".join(candidate_values_for(domain))
        return f"{label} '{value}' is not a candidate {domain} value; candidates: [{candidates}]"
    return None


def validate_context_packet(packet: ContextPacket) -> tuple[str, ...]:
    """Validate a ContextPacket structurally.

    Returns a tuple of error strings (empty when valid).
    Does not perform IO, DB, Redis, graph, provider, or route operations.
    """
    errors: list[str] = []

    err = _non_empty(packet.packet_id, "packet_id")
    if err:
        errors.append(err)

    err = _non_empty(packet.schema_version, "schema_version")
    if err:
        errors.append(err)

    err = _in_candidates(
        str(packet.kind), "ContextPacketKind", "kind"
    )
    if err:
        errors.append(err)

    err = _in_candidates(
        str(packet.sensitivity), "ContextPacketSensitivity", "sensitivity"
    )
    if err:
        errors.append(err)

    err = _in_candidates(
        str(packet.retention), "ContextPacketRetention", "retention"
    )
    if err:
        errors.append(err)

    err = _non_empty(packet.summary, "summary")
    if err:
        errors.append(err)

    err = _non_empty(packet.source.system, "source.system")
    if err:
        errors.append(err)

    return tuple(errors)


def validate_reality_state(state: RealityState) -> tuple[str, ...]:
    """Validate a RealityState structurally.

    Returns a tuple of error strings (empty when valid).
    Does not perform IO, DB, Redis, graph, provider, or route operations.
    """
    errors: list[str] = []

    err = _non_empty(state.state_id, "state_id")
    if err:
        errors.append(err)

    err = _non_empty(state.schema_version, "schema_version")
    if err:
        errors.append(err)

    err = _in_candidates(str(state.scope), "RealityScope", "scope")
    if err:
        errors.append(err)

    err = _non_empty(state.compiled_at, "compiled_at")
    if err:
        errors.append(err)

    if not state.source_packet_ids:
        errors.append("source_packet_ids must contain at least one entry")

    if state.confidence is not None and not (0.0 <= state.confidence <= 1.0):
        errors.append(
            f"confidence must be between 0.0 and 1.0, got {state.confidence}"
        )

    for i, decision in enumerate(state.accepted_decisions):
        err = _non_empty(decision.decision_id, f"accepted_decisions[{i}].decision_id")
        if err:
            errors.append(err)

    for i, loop in enumerate(state.open_loops):
        err = _non_empty(loop.loop_id, f"open_loops[{i}].loop_id")
        if err:
            errors.append(err)
        err = _in_candidates(str(loop.status), "OpenLoopStatus", f"open_loops[{i}].status")
        if err:
            errors.append(err)

    for i, path in enumerate(state.rejected_paths):
        err = _non_empty(path.path_id, f"rejected_paths[{i}].path_id")
        if err:
            errors.append(err)
        err = _in_candidates(str(path.status), "RejectedPathStatus", f"rejected_paths[{i}].status")
        if err:
            errors.append(err)

    return tuple(errors)


def validate_reality_commit(commit: RealityCommit) -> tuple[str, ...]:
    """Validate a RealityCommit structurally.

    Returns a tuple of error strings (empty when valid).
    Does not perform IO, DB, Redis, graph, provider, or route operations.
    """
    errors: list[str] = []

    err = _non_empty(commit.commit_id, "commit_id")
    if err:
        errors.append(err)

    err = _non_empty(commit.schema_version, "schema_version")
    if err:
        errors.append(err)

    err = _in_candidates(str(commit.scope), "RealityScope", "scope")
    if err:
        errors.append(err)

    err = _in_candidates(str(commit.kind), "RealityCommitKind", "kind")
    if err:
        errors.append(err)

    err = _in_candidates(str(commit.trigger), "RealityCommitTrigger", "trigger")
    if err:
        errors.append(err)

    err = _non_empty(commit.title, "title")
    if err:
        errors.append(err)

    err = _non_empty(commit.summary, "summary")
    if err:
        errors.append(err)

    err = _non_empty(commit.created_at, "created_at")
    if err:
        errors.append(err)

    has_packets = bool(commit.source_packet_ids)
    has_commit_prov = bool(commit.provenance.source_commit_ids)
    has_msg_prov = bool(commit.provenance.source_message_ids)
    has_artifact_prov = bool(commit.provenance.source_artifact_ids)

    if not has_packets and not has_commit_prov and not has_msg_prov and not has_artifact_prov:
        errors.append(
            "RealityCommit must have source_packet_ids or at least one provenance reference "
            "(source_commit_ids, source_message_ids, or source_artifact_ids)"
        )

    return tuple(errors)


# ── Public export list ──────────────────────────────────────────────────────

__all__ = [
    # Type aliases
    "ContextPacketKind",
    "ContextPacketSensitivity",
    "ContextPacketRetention",
    "RealityScope",
    "RealityCommitTrigger",
    "RealityCommitKind",
    "DiscoveryCommitTrigger",
    "OpenLoopStatus",
    "RejectedPathStatus",
    "ProjectPulseSurfaceKind",
    "BrowserContextPacketKind",
    "GraphMountMode",
    "ContinuityCacheState",
    "PinnedModelStateKind",
    "ContinuityImplementationGate",
    # Dataclasses
    "ContinuityScope",
    "ContinuitySource",
    "ContinuityProvenance",
    "ContextPacket",
    "DecisionRecord",
    "OpenLoopRecord",
    "RejectedPathRecord",
    "RealityState",
    "RealityCommit",
    # Candidate value tuples
    "CONTEXT_PACKET_KIND_VALUES",
    "CONTEXT_PACKET_SENSITIVITY_VALUES",
    "CONTEXT_PACKET_RETENTION_VALUES",
    "REALITY_SCOPE_VALUES",
    "REALITY_COMMIT_TRIGGER_VALUES",
    "REALITY_COMMIT_KIND_VALUES",
    "DISCOVERY_COMMIT_TRIGGER_VALUES",
    "OPEN_LOOP_STATUS_VALUES",
    "REJECTED_PATH_STATUS_VALUES",
    "PROJECT_PULSE_SURFACE_KIND_VALUES",
    "BROWSER_CONTEXT_PACKET_KIND_VALUES",
    "GRAPH_MOUNT_MODE_VALUES",
    "CONTINUITY_CACHE_STATE_VALUES",
    "PINNED_MODEL_STATE_KIND_VALUES",
    "CONTINUITY_IMPLEMENTATION_GATE_VALUES",
    # Helpers
    "candidate_values_for",
    "is_candidate_value",
    "validate_context_packet",
    "validate_reality_state",
    "validate_reality_commit",
]
