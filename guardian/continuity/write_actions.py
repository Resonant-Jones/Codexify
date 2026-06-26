"""Continuity explicit write-action service — adapter-dependent seam.

This module implements the explicit Continuity write-action service for
Reality Stamp / Reality Commit MVP behaviour.  It writes **only** when
directly invoked with explicit input objects and an explicit
``ContinuityPersistenceAdapter`` dependency.

**Not wired into runtime.**  No routes, workers, command bus, chat
runtime, compiler auto-persistence, heartbeat writes, semantic-delta
writes, browser capture, graph writes, sync, export/restore, Project
Pulse, or provider calls.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal, TypeAlias

from guardian.continuity.compiler import compile_reality_state
from guardian.continuity.contracts import (
    ContextPacket,
    ContextPacketSensitivity,
    ContextPacketRetention,
    ContinuityProvenance,
    ContinuityScope,
    ContinuitySource,
    RealityCommit,
    RealityScope,
    RealityState,
)
from guardian.continuity.persistence import (
    ContinuityPersistenceAdapter,
    ContinuityPersistenceError,
    ContinuityPersistenceResult,
)


# ── Type aliases ────────────────────────────────────────────────────────────

ContinuityWriteActionKind: TypeAlias = Literal[
    "create_reality_stamp",
    "create_reality_commit",
    "compile_and_save_reality_state_from_explicit_packets",
    "link_state_to_packets",
]


# ── Action input dataclasses ────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class ContinuityActionActor:
    """Identity of the actor requesting a continuity write action."""

    actor_id: str
    actor_kind: str = "user"
    display_name: str | None = None


@dataclasses.dataclass(frozen=True)
class RealityStampInput:
    """Input for a create_reality_stamp action."""

    action_id: str
    actor: ContinuityActionActor
    packet_id: str
    schema_version: str
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
class RealityStateWriteInput:
    """Input for a compile_and_save_reality_state_from_explicit_packets action."""

    action_id: str
    actor: ContinuityActionActor
    packets: tuple[ContextPacket, ...]
    scope: RealityScope
    schema_version: str = "0.1"
    active_branch: str | None = None
    confidence: float | None = None
    link_relationship: str = "compiled_from"


@dataclasses.dataclass(frozen=True)
class RealityCommitWriteInput:
    """Input for a create_reality_commit action."""

    action_id: str
    actor: ContinuityActionActor
    commit: RealityCommit
    link_packet_ids: tuple[str, ...] = ()
    link_relationship: str = "compiled_from"


@dataclasses.dataclass(frozen=True)
class StatePacketLinkInput:
    """Input for a link_state_to_packets action."""

    action_id: str
    actor: ContinuityActionActor
    state_id: str
    packet_ids: tuple[str, ...]
    relationship: str = "compiled_from"


# ── Write receipt dataclass ─────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class ContinuityWriteReceipt:
    """Result of a single write action — success or failure.

    ``graph_used`` and ``runtime_event_published`` are always ``False``
    in this implementation.
    """

    action_id: str
    action_kind: ContinuityWriteActionKind
    success: bool
    created_packet_ids: tuple[str, ...] = ()
    created_state_ids: tuple[str, ...] = ()
    created_commit_ids: tuple[str, ...] = ()
    created_link_ids: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    persistence_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    graph_used: bool = False
    runtime_event_published: bool = False
    created_at: str | None = None

    @property
    def is_failure(self) -> bool:
        return not self.success

    @classmethod
    def _failed(
        cls,
        action_id: str,
        action_kind: ContinuityWriteActionKind,
        *,
        validation_errors: tuple[str, ...] = (),
        persistence_errors: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> ContinuityWriteReceipt:
        return cls(
            action_id=action_id,
            action_kind=action_kind,
            success=False,
            validation_errors=validation_errors,
            persistence_errors=persistence_errors,
            warnings=warnings,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def _ok(
        cls,
        action_id: str,
        action_kind: ContinuityWriteActionKind,
        *,
        created_packet_ids: tuple[str, ...] = (),
        created_state_ids: tuple[str, ...] = (),
        created_commit_ids: tuple[str, ...] = (),
        created_link_ids: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        provenance_refs: tuple[str, ...] = (),
    ) -> ContinuityWriteReceipt:
        return cls(
            action_id=action_id,
            action_kind=action_kind,
            success=True,
            created_packet_ids=created_packet_ids,
            created_state_ids=created_state_ids,
            created_commit_ids=created_commit_ids,
            created_link_ids=created_link_ids,
            warnings=warnings,
            provenance_refs=provenance_refs,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# ── Private helpers ─────────────────────────────────────────────────────────


def _persistence_errors_as_strings(
    errors: tuple[ContinuityPersistenceError, ...],
) -> tuple[str, ...]:
    return tuple(f"{e.code}: {e.message}" for e in errors)


def _record_ids(result: ContinuityPersistenceResult) -> tuple[str, ...]:
    return tuple(r.record_id for r in result.records)


# ── Service ─────────────────────────────────────────────────────────────────


class ContinuityWriteActionService:
    """Explicit write-action service for continuity MVP.

    Requires an explicit ``ContinuityPersistenceAdapter``.  Does not
    create sessions internally.  Does not call Redis, Neo4j, providers,
    routes, workers, or the compiler (except for the explicitly named
    ``compile_and_save_reality_state_from_explicit_packets`` action, and
    only with explicit packet inputs).
    """

    def __init__(self, adapter: ContinuityPersistenceAdapter) -> None:
        self._adapter = adapter

    # ── create_reality_stamp ───────────────────────────────────────────

    def create_reality_stamp(
        self, action: RealityStampInput
    ) -> ContinuityWriteReceipt:
        """Persist an explicit Context Packet from user/operator input."""
        packet = ContextPacket(
            packet_id=action.packet_id,
            schema_version=action.schema_version,
            kind="thread",
            scope=action.scope,
            source=action.source,
            created_at=action.created_at,
            summary=action.summary,
            payload=action.payload,
            metadata=action.metadata,
            provenance=action.provenance,
            sensitivity=action.sensitivity,
            retention=action.retention,
            integrity=action.integrity,
        )

        result = self._adapter.save_context_packet(packet)
        if result.is_failure:
            return ContinuityWriteReceipt._failed(
                action_id=action.action_id,
                action_kind="create_reality_stamp",
                validation_errors=_persistence_errors_as_strings(
                    result.validation_errors
                ),
                persistence_errors=_persistence_errors_as_strings(
                    result.db_errors
                ),
            )

        return ContinuityWriteReceipt._ok(
            action_id=action.action_id,
            action_kind="create_reality_stamp",
            created_packet_ids=_record_ids(result),
            provenance_refs=(
                action.packet_id,
                *action.provenance.source_packet_ids,
            ),
        )

    # ── compile_and_save_reality_state_from_explicit_packets ────────────

    def compile_and_save_reality_state_from_explicit_packets(
        self, action: RealityStateWriteInput
    ) -> ContinuityWriteReceipt:
        """Compile and persist a RealityState from explicit packets.

        Only *action.packets* are used.  No ambient context, retrieval,
        or model inference occurs.
        """
        compile_result = compile_reality_state(
            action.packets,
            scope=action.scope,
            schema_version=action.schema_version,
            active_branch=action.active_branch,
            confidence=action.confidence,
        )

        warnings = list(compile_result.warnings)

        if compile_result.errors:
            return ContinuityWriteReceipt._failed(
                action_id=action.action_id,
                action_kind="compile_and_save_reality_state_from_explicit_packets",
                validation_errors=tuple(compile_result.errors),
                warnings=tuple(warnings),
            )

        # Save the compiled state.
        save_result = self._adapter.save_reality_state(compile_result.state)
        if save_result.is_failure:
            return ContinuityWriteReceipt._failed(
                action_id=action.action_id,
                action_kind="compile_and_save_reality_state_from_explicit_packets",
                validation_errors=_persistence_errors_as_strings(
                    save_result.validation_errors
                ),
                persistence_errors=_persistence_errors_as_strings(
                    save_result.db_errors
                ),
                warnings=tuple(warnings),
            )

        state_id = save_result.records[0].record_id if save_result.records else ""

        # Link source packets to the saved state.
        link_ids: tuple[str, ...] = ()
        if compile_result.state.source_packet_ids:
            link_result = self._adapter.link_state_packets(
                state_id=state_id,
                packet_ids=compile_result.state.source_packet_ids,
                relationship=action.link_relationship,
            )
            link_ids = _record_ids(link_result)
            if link_result.is_failure:
                return ContinuityWriteReceipt._failed(
                    action_id=action.action_id,
                    action_kind="compile_and_save_reality_state_from_explicit_packets",
                    persistence_errors=_persistence_errors_as_strings(
                        link_result.db_errors
                    ),
                    warnings=tuple(warnings),
                )

        return ContinuityWriteReceipt._ok(
            action_id=action.action_id,
            action_kind="compile_and_save_reality_state_from_explicit_packets",
            created_state_ids=(state_id,) if state_id else (),
            created_link_ids=link_ids,
            warnings=tuple(warnings),
        )

    # ── create_reality_commit ──────────────────────────────────────────

    def create_reality_commit(
        self, action: RealityCommitWriteInput
    ) -> ContinuityWriteReceipt:
        """Persist an explicit Reality Commit."""
        result = self._adapter.save_reality_commit(action.commit)
        if result.is_failure:
            return ContinuityWriteReceipt._failed(
                action_id=action.action_id,
                action_kind="create_reality_commit",
                validation_errors=_persistence_errors_as_strings(
                    result.validation_errors
                ),
                persistence_errors=_persistence_errors_as_strings(
                    result.db_errors
                ),
            )

        commit_id = result.records[0].record_id if result.records else ""

        link_ids: tuple[str, ...] = ()
        if action.link_packet_ids and action.commit.new_state_id:
            link_result = self._adapter.link_state_packets(
                state_id=action.commit.new_state_id,
                packet_ids=action.link_packet_ids,
                relationship=action.link_relationship,
            )
            link_ids = _record_ids(link_result)
            if link_result.is_failure:
                return ContinuityWriteReceipt._failed(
                    action_id=action.action_id,
                    action_kind="create_reality_commit",
                    persistence_errors=_persistence_errors_as_strings(
                        link_result.db_errors
                    ),
                )

        return ContinuityWriteReceipt._ok(
            action_id=action.action_id,
            action_kind="create_reality_commit",
            created_commit_ids=(commit_id,) if commit_id else (),
            created_link_ids=link_ids,
        )

    # ── link_state_to_packets ──────────────────────────────────────────

    def link_state_to_packets(
        self, action: StatePacketLinkInput
    ) -> ContinuityWriteReceipt:
        """Create explicit provenance links between a state and its packets."""
        result = self._adapter.link_state_packets(
            state_id=action.state_id,
            packet_ids=action.packet_ids,
            relationship=action.relationship,
        )

        if result.is_failure:
            return ContinuityWriteReceipt._failed(
                action_id=action.action_id,
                action_kind="link_state_to_packets",
                validation_errors=_persistence_errors_as_strings(
                    result.validation_errors
                ),
                persistence_errors=_persistence_errors_as_strings(
                    result.db_errors
                ),
            )

        return ContinuityWriteReceipt._ok(
            action_id=action.action_id,
            action_kind="link_state_to_packets",
            created_link_ids=_record_ids(result),
        )


# ── Public exports ──────────────────────────────────────────────────────────

__all__ = [
    "ContinuityWriteActionKind",
    "ContinuityActionActor",
    "RealityStampInput",
    "RealityStateWriteInput",
    "RealityCommitWriteInput",
    "StatePacketLinkInput",
    "ContinuityWriteReceipt",
    "ContinuityWriteActionService",
]
