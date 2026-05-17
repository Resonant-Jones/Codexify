"""Unified command bus routes (Phase 1)."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from typing import Any, AsyncGenerator, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from guardian.command_bus.contracts import InvokeRequest
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.manifest import build_manifest
from guardian.command_bus.search import (
    CommandSearchQuery,
    records_from_manifest,
    search_commands,
)
from guardian.command_bus.store import CommandBusStore
from guardian.core.dependencies import get_current_user, require_api_key
from guardian.extensions.activation import (
    activate_capability_for_owner_and_profile,
    activate_capability_for_owner_and_project,
    activate_capability_for_owner_only,
    activate_capability_for_owner_project_profile,
)
from guardian.extensions.contracts import (
    CapabilityActivationContextToken,
    CapabilityActivationDecision,
    CapabilityActivationRequest,
)
from guardian.extensions.resolver import EffectiveCapabilityResolver
from guardian.extensions.store import ExtensionProposalStore

router = APIRouter(
    prefix="/api/guardian/commands",
    tags=["Command Bus"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None
_store = CommandBusStore()
_extension_store = ExtensionProposalStore()
_activation_resolver = EffectiveCapabilityResolver(_extension_store)


def configure_db(db: Any | None) -> None:
    """Configure DB handle for command bus persistence."""
    global _db, _store, _extension_store, _activation_resolver
    _db = db
    _store = CommandBusStore(db=db)
    _extension_store = ExtensionProposalStore(db=db)
    _activation_resolver = EffectiveCapabilityResolver(_extension_store)


def get_store() -> CommandBusStore:
    """Return the active command-bus store."""
    return _store


@router.get("/manifest")
async def get_manifest(request: Request) -> dict[str, Any]:
    manifest = build_manifest(request.app)
    return manifest.model_dump(mode="json")


@router.get("/search")
async def search_command_manifest(
    request: Request,
    q: str = Query(default=""),
    limit: int = Query(default=20),
) -> dict[str, Any]:
    manifest = build_manifest(request.app)
    records = records_from_manifest(manifest)
    search_query = CommandSearchQuery(query=q, limit=limit)
    results = search_commands(records, search_query)
    bounded_limit = max(1, min(50, int(limit or 20)))
    return {
        "query": q,
        "limit": bounded_limit,
        "count": len(results),
        "results": [asdict(result) for result in results],
    }


@router.post("/invoke")
async def invoke_command(
    payload: InvokeRequest,
    request: Request,
    auth_subject: str = Depends(get_current_user),
) -> dict[str, Any]:
    inbound_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "x-api-key", "x-user-id", "cookie"}
    }
    return await execute_invoke(
        payload=payload,
        auth_subject=auth_subject,
        inbound_headers=inbound_headers,
        store=_store,
        app=request.app,
        execution_lane="tools",
        allow_write_execution=True,
        confirmation_granted=False,
    )


def _inspect_activation(
    *,
    request: CapabilityActivationRequest,
    resolver: EffectiveCapabilityResolver,
) -> CapabilityActivationDecision:
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_ONLY.value
    ):
        return activate_capability_for_owner_only(
            account_id=request.account_id,
            requested_command_id=request.requested_command_id,
            requested_permissions=request.requested_permissions,
            resolver=resolver,
            request_metadata=request.request_metadata,
            source_thread_id=request.source_thread_id,
            source_message_id=request.source_message_id,
            requested_at=request.requested_at,
        )
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_PROJECT.value
    ):
        return activate_capability_for_owner_and_project(
            account_id=request.account_id,
            project_id=request.project_id
            if request.project_id is not None
            else 0,
            requested_command_id=request.requested_command_id,
            requested_permissions=request.requested_permissions,
            resolver=resolver,
            request_metadata=request.request_metadata,
            source_thread_id=request.source_thread_id,
            source_message_id=request.source_message_id,
            requested_at=request.requested_at,
        )
    if (
        request.activation_context_token
        == CapabilityActivationContextToken.OWNER_PROFILE.value
    ):
        return activate_capability_for_owner_and_profile(
            account_id=request.account_id,
            profile_id=request.profile_id or "",
            requested_command_id=request.requested_command_id,
            requested_permissions=request.requested_permissions,
            resolver=resolver,
            request_metadata=request.request_metadata,
            source_thread_id=request.source_thread_id,
            source_message_id=request.source_message_id,
            requested_at=request.requested_at,
        )
    return activate_capability_for_owner_project_profile(
        account_id=request.account_id,
        project_id=request.project_id if request.project_id is not None else 0,
        profile_id=request.profile_id or "",
        requested_command_id=request.requested_command_id,
        requested_permissions=request.requested_permissions,
        resolver=resolver,
        request_metadata=request.request_metadata,
        source_thread_id=request.source_thread_id,
        source_message_id=request.source_message_id,
        requested_at=request.requested_at,
    )


@router.get("/activation/inspect")
async def inspect_activation(
    account_id: str = Query(...),
    requested_command_id: str = Query(...),
    activation_context_token: str = Query(...),
    project_id: int | None = Query(default=None),
    profile_id: str | None = Query(default=None),
    requested_permissions_json: str | None = Query(default=None),
    request_metadata_json: str | None = Query(default=None),
    source_thread_id: int | None = Query(default=None),
    source_message_id: int | None = Query(default=None),
    requested_at: str | None = Query(default=None),
    auth_subject: str = Depends(get_current_user),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "account_id": account_id,
        "requested_command_id": requested_command_id,
        "activation_context_token": activation_context_token,
        "project_id": project_id,
        "profile_id": profile_id,
        "source_thread_id": source_thread_id,
        "source_message_id": source_message_id,
        "requested_at": requested_at,
    }
    if requested_permissions_json is not None:
        try:
            payload["requested_permissions_json"] = json.loads(
                requested_permissions_json
            )
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="requested_permissions_json must be valid JSON",
            ) from exc
    else:
        payload["requested_permissions_json"] = []
    if request_metadata_json is not None:
        try:
            payload["request_metadata_json"] = json.loads(request_metadata_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="request_metadata_json must be valid JSON",
            ) from exc
    else:
        payload["request_metadata_json"] = {}

    try:
        request = CapabilityActivationRequest.from_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if request.account_id != auth_subject:
        raise HTTPException(status_code=403, detail="forbidden")

    decision = _inspect_activation(
        request=request,
        resolver=_activation_resolver,
    )
    payload = decision.to_payload()
    if payload.get("dispatch_envelope_json") is None:
        payload.pop("dispatch_envelope_json", None)
    return payload


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    auth_subject: str = Depends(get_current_user),
) -> StreamingResponse:
    run = _store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    if str(run.get("auth_subject") or "") != auth_subject:
        raise HTTPException(status_code=403, detail="forbidden")

    async def event_stream() -> AsyncGenerator[str, None]:
        current_seq = int(after_seq or 0)
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0
        poll_interval = 0.5

        while True:
            if await request.is_disconnected():
                break

            events = _store.list_events_after(
                run_id=run_id,
                after_seq=current_seq,
                limit=200,
            )
            if events:
                for event in events:
                    seq = int(event.get("sequence") or 0)
                    event_type = str(event.get("event_type") or "run.event")
                    payload = event.get("payload_json") or {}
                    payload_str = json.dumps(payload, default=str)
                    yield f"id: {seq}\n"
                    yield f"event: {event_type}\n"
                    yield f"data: {payload_str}\n\n"
                    current_seq = max(current_seq, seq)
                heartbeat_elapsed = 0.0
            else:
                heartbeat_elapsed += poll_interval
                if heartbeat_elapsed >= heartbeat_interval:
                    yield ": ping\n\n"
                    heartbeat_elapsed = 0.0

            await asyncio.sleep(poll_interval)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
