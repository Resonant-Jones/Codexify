"""Continuity Phase A persistence adapter — explicit DB session seam.

This module implements the persistence adapter for the four Phase A
continuity tables.  It writes **only** when directly invoked with an
explicit SQLAlchemy session by tests or future approved call sites.

**Not wired into runtime.**  No routes, workers, compiler auto-persistence,
graph writes, browser capture, sync, export/restore, or provider calls.
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.continuity.contracts import (
    ContextPacket,
    ContinuityProvenance,
    ContinuityScope,
    ContinuitySource,
    DecisionRecord,
    OpenLoopRecord,
    RealityCommit,
    RealityScope,
    RealityState,
    RejectedPathRecord,
    candidate_values_for,
    validate_context_packet,
    validate_reality_commit,
    validate_reality_state,
)
from guardian.db.models import (
    ContinuityContextPacket,
    ContinuityRealityCommit,
    ContinuityRealityState,
    ContinuityStatePacketLink,
)

# ── Result / error dataclasses ──────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class StoredContinuityRecord:
    """Record of a single successful persistence operation."""

    record_id: str
    table: str
    operation: str
    provenance_refs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ContinuityPersistenceError:
    """A validation or database error from a persistence operation."""

    code: str
    message: str
    field: str | None = None


@dataclasses.dataclass(frozen=True)
class ContinuityPersistenceResult:
    """Result of a persistence operation — success or failure."""

    success: bool
    operation: str
    records: tuple[StoredContinuityRecord, ...] = ()
    validation_errors: tuple[ContinuityPersistenceError, ...] = ()
    db_errors: tuple[ContinuityPersistenceError, ...] = ()

    @property
    def is_failure(self) -> bool:
        return not self.success

    @classmethod
    def failed(
        cls,
        operation: str,
        *,
        validation_errors: tuple[ContinuityPersistenceError, ...] = (),
        db_errors: tuple[ContinuityPersistenceError, ...] = (),
    ) -> ContinuityPersistenceResult:
        return cls(
            success=False,
            operation=operation,
            validation_errors=validation_errors,
            db_errors=db_errors,
        )

    @classmethod
    def ok(
        cls,
        operation: str,
        *,
        records: tuple[StoredContinuityRecord, ...] = (),
    ) -> ContinuityPersistenceResult:
        return cls(success=True, operation=operation, records=records)


# ── Serialization helpers ───────────────────────────────────────────────────


def _ensure_uuid(value: str) -> str:
    """Return *value* if it already looks like a UUID, else generate one."""
    if value and len(value) >= 32:
        return value
    return uuid.uuid4().hex


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert a dataclass or primitive to a JSON-safe dict."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: _to_json_safe(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
        }
    if isinstance(obj, tuple):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    # Fallback: try str, but prefer not to quietly lose structure.
    return str(obj)


def _scope_to_columns(scope: ContinuityScope) -> dict[str, str | None]:
    """Extract scope ID columns from a ContinuityScope dataclass."""
    return {
        "user_id": scope.user_id,
        "project_id": scope.project_id,
        "thread_id": scope.thread_id,
        "task_id": scope.task_id,
        "tab_id": scope.tab_id,
        "persona_id": scope.persona_id,
        "node_id": scope.node_id,
        "team_id": scope.team_id,
        "dyad_id": scope.dyad_id,
    }


def _source_to_columns(source: ContinuitySource) -> dict[str, str | None]:
    return {
        "source_system": source.system,
        "source_plugin": source.plugin,
        "source_provider": source.provider,
        "origin_ref": source.origin_ref,
    }


def _provenance_to_dict(prov: ContinuityProvenance) -> dict[str, Any]:
    return {
        "source_packet_ids": list(prov.source_packet_ids),
        "source_commit_ids": list(prov.source_commit_ids),
        "source_message_ids": list(prov.source_message_ids),
        "source_artifact_ids": list(prov.source_artifact_ids),
    }


def _records_to_json(records: Sequence[Any]) -> list[dict[str, Any]]:
    return [_to_json_safe(r) for r in records]


# ── Adapter ─────────────────────────────────────────────────────────────────


class ContinuityPersistenceAdapter:
    """Explicit persistence adapter for Phase A continuity tables.

    Requires an explicit SQLAlchemy session.  Does not create sessions
    internally.  Does not connect to Redis, Neo4j, providers, routes,
    workers, or the compiler.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Write helpers ──────────────────────────────────────────────────

    def _check_validation(
        self,
        errors: tuple[str, ...],
        operation: str,
    ) -> ContinuityPersistenceResult | None:
        """Return a failed result if *errors* is non-empty, else None."""
        if errors:
            return ContinuityPersistenceResult.failed(
                operation=operation,
                validation_errors=tuple(
                    ContinuityPersistenceError(
                        code="VALIDATION_FAILED",
                        message=e,
                    )
                    for e in errors
                ),
            )
        return None

    def _commit_one(
        self,
        row: Any,
        table: str,
        operation: str,
    ) -> ContinuityPersistenceResult:
        """Commit a single row and return a success result."""
        try:
            self._session.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            return ContinuityPersistenceResult.failed(
                operation=operation,
                db_errors=(
                    ContinuityPersistenceError(
                        code="INTEGRITY_ERROR",
                        message=str(exc.orig) if exc.orig else str(exc),
                    ),
                ),
            )
        except Exception as exc:
            self._session.rollback()
            return ContinuityPersistenceResult.failed(
                operation=operation,
                db_errors=(
                    ContinuityPersistenceError(
                        code="DB_ERROR",
                        message=str(exc),
                    ),
                ),
            )
        return ContinuityPersistenceResult.ok(
            operation=operation,
            records=(
                StoredContinuityRecord(
                    record_id=getattr(row, "id", ""),
                    table=table,
                    operation=operation,
                ),
            ),
        )

    def _commit_many(
        self,
        rows: Sequence[Any],
        table: str,
        operation: str,
    ) -> ContinuityPersistenceResult:
        """Commit multiple rows atomically."""
        try:
            for row in rows:
                self._session.add(row)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            return ContinuityPersistenceResult.failed(
                operation=operation,
                db_errors=(
                    ContinuityPersistenceError(
                        code="INTEGRITY_ERROR",
                        message=str(exc.orig) if exc.orig else str(exc),
                    ),
                ),
            )
        except Exception as exc:
            self._session.rollback()
            return ContinuityPersistenceResult.failed(
                operation=operation,
                db_errors=(
                    ContinuityPersistenceError(
                        code="DB_ERROR",
                        message=str(exc),
                    ),
                ),
            )
        return ContinuityPersistenceResult.ok(
            operation=operation,
            records=tuple(
                StoredContinuityRecord(
                    record_id=getattr(r, "id", ""),
                    table=table,
                    operation=operation,
                )
                for r in rows
            ),
        )

    # ── save_context_packet ────────────────────────────────────────────

    def save_context_packet(
        self, packet: ContextPacket
    ) -> ContinuityPersistenceResult:
        """Validate and persist a single ContextPacket."""
        v_errors = validate_context_packet(packet)
        failed = self._check_validation(v_errors, "save_context_packet")
        if failed is not None:
            return failed

        scope_cols = _scope_to_columns(packet.scope)
        source_cols = _source_to_columns(packet.source)

        row = ContinuityContextPacket(
            id=_ensure_uuid(packet.packet_id),
            schema_version=packet.schema_version,
            kind=str(packet.kind),
            **scope_cols,
            **source_cols,
            created_at=packet.created_at,  # string → DB handles cast
            summary=packet.summary,
            payload_json=_to_json_safe(packet.payload),
            metadata_json=_to_json_safe(packet.metadata),
            provenance_json=_provenance_to_dict(packet.provenance),
            sensitivity=str(packet.sensitivity),
            retention=str(packet.retention),
            integrity_json=_to_json_safe(packet.integrity),
        )
        return self._commit_one(
            row, "continuity_context_packets", "save_context_packet"
        )

    # ── save_reality_state ─────────────────────────────────────────────

    def save_reality_state(
        self, state: RealityState
    ) -> ContinuityPersistenceResult:
        """Validate and persist a single RealityState."""
        v_errors = validate_reality_state(state)
        failed = self._check_validation(v_errors, "save_reality_state")
        if failed is not None:
            return failed

        row = ContinuityRealityState(
            id=_ensure_uuid(state.state_id),
            schema_version=state.schema_version,
            scope=str(state.scope),
            user_id=None,
            compiled_at=state.compiled_at,
            active_branch=state.active_branch,
            source_packet_ids_json=list(state.source_packet_ids),
            state_json=_to_json_safe(state),
            accepted_decisions_json=_records_to_json(state.accepted_decisions),
            open_loops_json=_records_to_json(state.open_loops),
            rejected_paths_json=_records_to_json(state.rejected_paths),
            active_artifacts_json=list(state.active_artifacts),
            assumptions_json=list(state.assumptions),
            risks_json=list(state.risks),
            next_actions_json=list(state.next_actions),
            confidence=state.confidence,
            provenance_json=_provenance_to_dict(state.provenance),
            expires_or_decays_at=state.expires_or_decays_at,
            created_at=state.compiled_at,
        )
        return self._commit_one(
            row, "continuity_reality_states", "save_reality_state"
        )

    # ── save_reality_commit ────────────────────────────────────────────

    def save_reality_commit(
        self, commit: RealityCommit
    ) -> ContinuityPersistenceResult:
        """Validate and persist a single RealityCommit."""
        v_errors = validate_reality_commit(commit)
        failed = self._check_validation(v_errors, "save_reality_commit")
        if failed is not None:
            return failed

        row = ContinuityRealityCommit(
            id=_ensure_uuid(commit.commit_id),
            schema_version=commit.schema_version,
            scope=str(commit.scope),
            kind=str(commit.kind),
            trigger=str(commit.trigger),
            title=commit.title,
            summary=commit.summary,
            user_id=None,
            source_packet_ids_json=list(commit.source_packet_ids),
            previous_state_id=commit.previous_state_id,
            new_state_id=commit.new_state_id,
            provenance_json=_provenance_to_dict(commit.provenance),
            created_at=commit.created_at,
        )
        return self._commit_one(
            row, "continuity_reality_commits", "save_reality_commit"
        )

    # ── link_state_packets ─────────────────────────────────────────────

    def link_state_packets(
        self,
        state_id: str,
        packet_ids: Sequence[str],
        relationship: str = "compiled_from",
    ) -> ContinuityPersistenceResult:
        """Create state-packet provenance links atomically."""
        if not state_id or not state_id.strip():
            return ContinuityPersistenceResult.failed(
                operation="link_state_packets",
                validation_errors=(
                    ContinuityPersistenceError(
                        code="VALIDATION_FAILED",
                        message="state_id must be non-empty",
                        field="state_id",
                    ),
                ),
            )
        if not relationship or not relationship.strip():
            return ContinuityPersistenceResult.failed(
                operation="link_state_packets",
                validation_errors=(
                    ContinuityPersistenceError(
                        code="VALIDATION_FAILED",
                        message="relationship must be non-empty",
                        field="relationship",
                    ),
                ),
            )

        filtered_ids = [pid for pid in packet_ids if pid and pid.strip()]
        if not filtered_ids:
            return ContinuityPersistenceResult.failed(
                operation="link_state_packets",
                validation_errors=(
                    ContinuityPersistenceError(
                        code="VALIDATION_FAILED",
                        message="at least one non-empty packet_id required",
                        field="packet_ids",
                    ),
                ),
            )

        rows = [
            ContinuityStatePacketLink(
                id=uuid.uuid4().hex,
                state_id=state_id,
                packet_id=pid,
                relationship=relationship,
                created_at=None,  # server handles default
            )
            for pid in filtered_ids
        ]

        return self._commit_many(
            rows, "continuity_state_packet_links", "link_state_packets"
        )

    # ── Read methods ───────────────────────────────────────────────────

    def load_reality_state(
        self, state_id: str
    ) -> RealityState | None:
        """Load a single RealityState by ID (non-deleted only).

        Returns None if not found or soft-deleted.
        """
        from sqlalchemy import select

        row = self._session.execute(
            select(ContinuityRealityState).where(
                ContinuityRealityState.id == state_id,
                ContinuityRealityState.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if row is None:
            return None

        state_dict = row.state_json or {}
        return _dict_to_reality_state(state_dict)

    def load_latest_reality_state(
        self,
        scope: RealityScope,
        scope_ids: ContinuityScope,
    ) -> RealityState | None:
        """Load the most recent non-deleted RealityState for a scope.

        Filters by project_id when scope is 'project', thread_id when
        'thread', etc.  Falls back to the most recent non-deleted state
        matching the scope type if specific scope IDs are all None.
        """
        from sqlalchemy import select

        stmt = select(ContinuityRealityState).where(
            ContinuityRealityState.scope == str(scope),
            ContinuityRealityState.deleted_at.is_(None),
        )

        # Build scope-specific filter
        if scope == "project" and scope_ids.project_id:
            stmt = stmt.where(
                ContinuityRealityState.project_id == scope_ids.project_id
            )
        elif scope == "thread" and scope_ids.thread_id:
            stmt = stmt.where(
                ContinuityRealityState.thread_id == scope_ids.thread_id
            )
        elif scope == "user" and scope_ids.user_id:
            stmt = stmt.where(
                ContinuityRealityState.user_id == scope_ids.user_id
            )

        stmt = stmt.order_by(
            ContinuityRealityState.compiled_at.desc(),
            ContinuityRealityState.created_at.desc(),
        ).limit(1)

        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        state_dict = row.state_json or {}
        return _dict_to_reality_state(state_dict)

    def list_reality_commits(
        self,
        scope_ids: ContinuityScope,
        limit: int = 50,
    ) -> tuple[RealityCommit, ...]:
        """List non-deleted RealityCommits for a scope, newest first."""
        from sqlalchemy import select

        stmt = select(ContinuityRealityCommit).where(
            ContinuityRealityCommit.deleted_at.is_(None),
        )

        if scope_ids.project_id:
            stmt = stmt.where(
                ContinuityRealityCommit.project_id == scope_ids.project_id
            )

        if scope_ids.thread_id:
            stmt = stmt.where(
                ContinuityRealityCommit.thread_id == scope_ids.thread_id
            )

        stmt = stmt.order_by(
            ContinuityRealityCommit.created_at.desc()
        ).limit(max(1, min(limit, 500)))

        rows = self._session.execute(stmt).scalars().all()
        results: list[RealityCommit] = []
        for row in rows:
            source_pids = tuple(row.source_packet_ids_json or [])
            prov_dict = row.provenance_json or {}
            results.append(
                RealityCommit(
                    commit_id=row.id,
                    schema_version=row.schema_version,
                    scope=row.scope,  # type: ignore[arg-type]
                    kind=row.kind,  # type: ignore[arg-type]
                    trigger=row.trigger,  # type: ignore[arg-type]
                    title=row.title,
                    summary=row.summary,
                    created_at=str(row.created_at) if row.created_at else "",
                    source_packet_ids=source_pids,
                    previous_state_id=row.previous_state_id,
                    new_state_id=row.new_state_id,
                    provenance=ContinuityProvenance(
                        source_packet_ids=tuple(
                            prov_dict.get("source_packet_ids", [])
                        ),
                        source_commit_ids=tuple(
                            prov_dict.get("source_commit_ids", [])
                        ),
                        source_message_ids=tuple(
                            prov_dict.get("source_message_ids", [])
                        ),
                        source_artifact_ids=tuple(
                            prov_dict.get("source_artifact_ids", [])
                        ),
                    ),
                )
            )
        return tuple(results)


# ── Deserialization ─────────────────────────────────────────────────────────


def _dict_to_reality_state(d: dict[str, Any]) -> RealityState:
    """Reconstruct a RealityState from a persisted dict."""

    def _to_decisions(
        raw: list[dict[str, Any]] | None,
    ) -> tuple[DecisionRecord, ...]:
        if not raw:
            return ()
        return tuple(
            DecisionRecord(
                decision_id=r.get("decision_id", ""),
                summary=r.get("summary", ""),
                accepted_at=r.get("accepted_at"),
                provenance=ContinuityProvenance(
                    source_packet_ids=tuple(
                        r.get("provenance", {}).get("source_packet_ids", [])
                    ),
                ),
            )
            for r in raw
        )

    def _to_loops(
        raw: list[dict[str, Any]] | None,
    ) -> tuple[OpenLoopRecord, ...]:
        if not raw:
            return ()
        return tuple(
            OpenLoopRecord(
                loop_id=r.get("loop_id", ""),
                summary=r.get("summary", ""),
                status=r.get("status", "open"),  # type: ignore[arg-type]
                provenance=ContinuityProvenance(
                    source_packet_ids=tuple(
                        r.get("provenance", {}).get("source_packet_ids", [])
                    ),
                ),
            )
            for r in raw
        )

    def _to_paths(
        raw: list[dict[str, Any]] | None,
    ) -> tuple[RejectedPathRecord, ...]:
        if not raw:
            return ()
        return tuple(
            RejectedPathRecord(
                path_id=r.get("path_id", ""),
                summary=r.get("summary", ""),
                status=r.get("status", "rejected"),  # type: ignore[arg-type]
                provenance=ContinuityProvenance(
                    source_packet_ids=tuple(
                        r.get("provenance", {}).get("source_packet_ids", [])
                    ),
                ),
            )
            for r in raw
        )

    prov_raw = d.get("provenance", {}) or {}

    return RealityState(
        state_id=d.get("state_id", ""),
        schema_version=d.get("schema_version", "0.1"),
        scope=d.get("scope", "project"),  # type: ignore[arg-type]
        compiled_at=d.get("compiled_at", ""),
        source_packet_ids=tuple(d.get("source_packet_ids", [])),
        active_branch=d.get("active_branch"),
        accepted_decisions=_to_decisions(d.get("accepted_decisions")),
        open_loops=_to_loops(d.get("open_loops")),
        rejected_paths=_to_paths(d.get("rejected_paths")),
        active_artifacts=tuple(d.get("active_artifacts", [])),
        assumptions=tuple(d.get("assumptions", [])),
        risks=tuple(d.get("risks", [])),
        next_actions=tuple(d.get("next_actions", [])),
        confidence=d.get("confidence"),
        provenance=ContinuityProvenance(
            source_packet_ids=tuple(prov_raw.get("source_packet_ids", [])),
            source_commit_ids=tuple(prov_raw.get("source_commit_ids", [])),
            source_message_ids=tuple(prov_raw.get("source_message_ids", [])),
            source_artifact_ids=tuple(prov_raw.get("source_artifact_ids", [])),
        ),
        expires_or_decays_at=d.get("expires_or_decays_at"),
    )


# ── Public exports ──────────────────────────────────────────────────────────

__all__ = [
    "StoredContinuityRecord",
    "ContinuityPersistenceError",
    "ContinuityPersistenceResult",
    "ContinuityPersistenceAdapter",
]
