"""Developer / operator continuity write route.

This route is a **developer-operator-only** surface that invokes the
explicit Continuity write-action service from explicit request payloads.
It is the first narrow runtime caller approved by
``docs/architecture/continuity-runtime-invocation-boundary-contract.md``.

**Not** a chat hook, worker, compiler auto-persistence, graph endpoint,
browser capture, sync surface, Project Pulse, or export/restore path.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from guardian.continuity.contracts import (
    ContinuityProvenance,
    ContinuityScope,
    ContinuitySource,
)
from guardian.continuity.persistence import ContinuityPersistenceAdapter
from guardian.continuity.write_actions import (
    ContinuityActionActor,
    ContinuityWriteActionService,
    ContinuityWriteReceipt,
    RealityStampInput,
)
from guardian.core.dependencies import get_database_dsn, require_api_key
from guardian.db.models import (
    ContinuityContextPacket,
    ContinuityRealityCommit,
    ContinuityRealityState,
    ContinuityStatePacketLink,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/operator/continuity", tags=["continuity-operator"])


# ── Pydantic models ─────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class RealityStampRequest(BaseModel):
    """Explicit request payload for creating a Reality Stamp."""

    action_id: str
    actor_id: str
    actor_kind: str = "user"
    display_name: str | None = None
    packet_id: str
    schema_version: str = "0.1"
    user_id: str | None = None
    project_id: str | None = None
    thread_id: str | None = None
    task_id: str | None = None
    tab_id: str | None = None
    persona_id: str | None = None
    node_id: str | None = None
    team_id: str | None = None
    dyad_id: str | None = None
    source_system: str = "developer_operator_route"
    source_plugin: str | None = None
    source_provider: str | None = None
    origin_ref: str | None = None
    created_at: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_packet_ids: list[str] = Field(default_factory=list)
    source_commit_ids: list[str] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    sensitivity: str = "local"
    retention: str = "session"
    integrity: dict[str, Any] = Field(default_factory=dict)


class RealityStampResponse(BaseModel):
    """Response mirroring ContinuityWriteReceipt for a Reality Stamp."""

    action_id: str
    action_kind: str
    success: bool
    created_packet_ids: list[str] = Field(default_factory=list)
    created_state_ids: list[str] = Field(default_factory=list)
    created_commit_ids: list[str] = Field(default_factory=list)
    created_link_ids: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    persistence_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    graph_used: bool = False
    runtime_event_published: bool = False
    created_at: str | None = None


# ── Helper ──────────────────────────────────────────────────────────────────


def _receipt_to_response(receipt: ContinuityWriteReceipt) -> RealityStampResponse:
    return RealityStampResponse(
        action_id=receipt.action_id,
        action_kind=str(receipt.action_kind),
        success=receipt.success,
        created_packet_ids=list(receipt.created_packet_ids),
        created_state_ids=list(receipt.created_state_ids),
        created_commit_ids=list(receipt.created_commit_ids),
        created_link_ids=list(receipt.created_link_ids),
        validation_errors=list(receipt.validation_errors),
        persistence_errors=list(receipt.persistence_errors),
        warnings=list(receipt.warnings),
        provenance_refs=list(receipt.provenance_refs),
        graph_used=receipt.graph_used,
        runtime_event_published=receipt.runtime_event_published,
        created_at=receipt.created_at,
    )


# ── Route ───────────────────────────────────────────────────────────────────


@router.post("/reality-stamp", response_model=RealityStampResponse)
def create_reality_stamp(
    request: RealityStampRequest,
    api_key: str = Depends(require_api_key),
) -> RealityStampResponse:
    """Create a Reality Stamp (persisted Context Packet) from explicit input.

    Requires explicit API-key authentication.  All input fields must be
    explicit — no ambient chat context, retrieval, model inference,
    browser capture, or graph enrichment is used.
    """
    dsn = get_database_dsn()
    if not dsn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    engine = create_engine(dsn, echo=False)
    session = Session(engine)
    adapter = ContinuityPersistenceAdapter(session)
    service = ContinuityWriteActionService(adapter)

    try:
        scope = ContinuityScope(
            user_id=request.user_id,
            project_id=request.project_id,
            thread_id=request.thread_id,
            task_id=request.task_id,
            tab_id=request.tab_id,
            persona_id=request.persona_id,
            node_id=request.node_id,
            team_id=request.team_id,
            dyad_id=request.dyad_id,
        )
        source = ContinuitySource(
            system=request.source_system,
            plugin=request.source_plugin,
            provider=request.source_provider,
            origin_ref=request.origin_ref,
        )
        provenance = ContinuityProvenance(
            source_packet_ids=tuple(request.source_packet_ids),
            source_commit_ids=tuple(request.source_commit_ids),
            source_message_ids=tuple(request.source_message_ids),
            source_artifact_ids=tuple(request.source_artifact_ids),
        )
        actor = ContinuityActionActor(
            actor_id=request.actor_id,
            actor_kind=request.actor_kind,
            display_name=request.display_name,
        )

        action = RealityStampInput(
            action_id=request.action_id,
            actor=actor,
            packet_id=request.packet_id,
            schema_version=request.schema_version,
            scope=scope,
            source=source,
            created_at=request.created_at,
            summary=request.summary,
            payload=request.payload,
            metadata=request.metadata,
            provenance=provenance,
            sensitivity=request.sensitivity,  # type: ignore[arg-type]
            retention=request.retention,  # type: ignore[arg-type]
            integrity=request.integrity,
        )

        receipt = service.create_reality_stamp(action)

        if not receipt.success:
            status_code = (
                400 if receipt.validation_errors else 500
            )
            raise HTTPException(
                status_code=status_code,
                detail={
                    "validation_errors": receipt.validation_errors,
                    "persistence_errors": receipt.persistence_errors,
                },
            )

        return _receipt_to_response(receipt)

    finally:
        session.close()


# ── Readback models ─────────────────────────────────────────────────────────


class ContextPacketReadbackResponse(BaseModel):
    """Response for a single context packet readback."""

    packet_id: str
    found: bool
    schema_version: str | None = None
    kind: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    summary: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    sensitivity: str | None = None
    retention: str | None = None
    integrity: dict[str, Any] = Field(default_factory=dict)
    deleted: bool = False
    graph_used: bool = False
    runtime_event_published: bool = False
    read_at: str | None = None


# ── Readback route ──────────────────────────────────────────────────────────


@router.get(
    "/context-packets/{packet_id}",
    response_model=ContextPacketReadbackResponse,
)
def read_context_packet(
    packet_id: str,
    api_key: str = Depends(require_api_key),
) -> ContextPacketReadbackResponse:
    """Read a single Context Packet by exact packet ID.

    Requires explicit API-key authentication.  Reads exactly one row —
    no list, search, retrieval, graph, compiler, or write behaviour.
    Soft-deleted records are treated as not found.
    """
    from datetime import datetime, timezone

    dsn = get_database_dsn()
    if not dsn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    engine = create_engine(dsn, echo=False)
    session = Session(engine)

    try:
        row = (
            session.query(ContinuityContextPacket)
            .filter(
                ContinuityContextPacket.id == packet_id,
                ContinuityContextPacket.deleted_at.is_(None),
            )
            .first()
        )

        if row is None:
            return ContextPacketReadbackResponse(
                packet_id=packet_id,
                found=False,
                read_at=datetime.now(timezone.utc).isoformat(),
            )

        return ContextPacketReadbackResponse(
            packet_id=row.id,
            found=True,
            schema_version=row.schema_version,
            kind=row.kind,
            scope={
                "user_id": row.user_id,
                "project_id": row.project_id,
                "thread_id": row.thread_id,
                "task_id": row.task_id,
                "tab_id": row.tab_id,
                "persona_id": row.persona_id,
                "node_id": row.node_id,
                "team_id": row.team_id,
                "dyad_id": row.dyad_id,
            },
            source={
                "system": row.source_system,
                "plugin": row.source_plugin,
                "provider": row.source_provider,
                "origin_ref": row.origin_ref,
            },
            created_at=str(row.created_at) if row.created_at else None,
            summary=row.summary,
            payload=row.payload_json or {},
            metadata=row.metadata_json or {},
            provenance=row.provenance_json or {},
            sensitivity=row.sensitivity,
            retention=row.retention,
            integrity=row.integrity_json or {},
            deleted=False,
            graph_used=False,
            runtime_event_published=False,
            read_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.exception("Failed to read context packet %s", packet_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "read_failed", "message": str(exc)},
        )

    finally:
        session.close()


# ── Diagnostics models ──────────────────────────────────────────────────────


class ContinuityOperatorDiagnosticsResponse(BaseModel):
    """Aggregate gate/profile/count diagnostics for the continuity operator loop."""

    profile_name: str = "unknown"
    supported_beta_quarantined: bool = True
    test_profile_enabled: bool = False
    feature_flag_enabled: bool = False
    write_route_available: bool = False
    readback_route_available: bool = False
    auth_required: bool = True
    write_action_kind: str = "create_reality_stamp"
    readback_mode: str = "exact_context_packet_id"
    context_packet_count: int = 0
    state_count: int = 0
    commit_count: int = 0
    state_packet_link_count: int = 0
    last_context_packet_created_at: str | None = None
    graph_used: bool = False
    runtime_event_published: bool = False
    project_pulse_enabled: bool = False
    export_restore_enabled: bool = False
    diagnostics_generated_at: str | None = None
    warnings: list[str] = Field(default_factory=list)


# ── Diagnostics route ───────────────────────────────────────────────────────


@router.get(
    "/diagnostics",
    response_model=ContinuityOperatorDiagnosticsResponse,
)
def operator_diagnostics(
    api_key: str = Depends(require_api_key),
) -> ContinuityOperatorDiagnosticsResponse:
    """Report aggregate continuity operator gate/profile/count truth.

    Requires explicit API-key authentication.  Returns counts, gate
    posture, and hard-false flags only — no raw payloads, no record
    listing, no graph, no compiler, no writes, no Project Pulse, and
    no export/restore semantics.
    """
    import os
    from datetime import datetime, timezone

    from sqlalchemy import func

    dsn = get_database_dsn()
    if not dsn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    engine = create_engine(dsn, echo=False)
    session = Session(engine)
    warnings: list[str] = []

    try:
        # ── Profile / gate posture ─────────────────────────────────────

        active_profile = os.getenv("CODEXIFY_SUPPORTED_PROFILE", "")
        if not active_profile:
            active_profile = "v1-local-core-web-mcp"
            warnings.append(
                "CODEXIFY_SUPPORTED_PROFILE not set; assuming default"
            )

        flag_on = os.getenv(
            "CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES", ""
        ).strip().lower() in ("true", "1", "yes")

        profile_name = active_profile or "unknown"
        supported_beta = profile_name == "v1-local-core-web-mcp"
        test_profile = profile_name == "test-continuity"

        # ── Aggregate counts ──────────────────────────────────────────

        packet_count = (
            session.query(func.count(ContinuityContextPacket.id))
            .filter(ContinuityContextPacket.deleted_at.is_(None))
            .scalar()
            or 0
        )
        state_count = (
            session.query(func.count(ContinuityRealityState.id))
            .filter(ContinuityRealityState.deleted_at.is_(None))
            .scalar()
            or 0
        )
        commit_count = (
            session.query(func.count(ContinuityRealityCommit.id))
            .filter(ContinuityRealityCommit.deleted_at.is_(None))
            .scalar()
            or 0
        )
        link_count = (
            session.query(func.count(ContinuityStatePacketLink.id))
            .scalar()
            or 0
        )

        last_created = (
            session.query(func.max(ContinuityContextPacket.created_at))
            .filter(ContinuityContextPacket.deleted_at.is_(None))
            .scalar()
        )

        return ContinuityOperatorDiagnosticsResponse(
            profile_name=profile_name,
            supported_beta_quarantined=supported_beta,
            test_profile_enabled=test_profile,
            feature_flag_enabled=flag_on,
            write_route_available=flag_on and not supported_beta,
            readback_route_available=flag_on and not supported_beta,
            auth_required=True,
            write_action_kind="create_reality_stamp",
            readback_mode="exact_context_packet_id",
            context_packet_count=packet_count,
            state_count=state_count,
            commit_count=commit_count,
            state_packet_link_count=link_count,
            last_context_packet_created_at=(
                str(last_created) if last_created else None
            ),
            graph_used=False,
            runtime_event_published=False,
            project_pulse_enabled=False,
            export_restore_enabled=False,
            diagnostics_generated_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

    except Exception as exc:
        logger.exception("Failed to collect continuity diagnostics")
        raise HTTPException(
            status_code=500,
            detail={"error": "diagnostics_failed", "message": str(exc)},
        )

    finally:
        session.close()
