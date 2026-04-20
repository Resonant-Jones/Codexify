"""Unified command bus routes (Phase 1)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from guardian.command_bus.contracts import InvokeRequest
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.manifest import build_manifest
from guardian.command_bus.store import CommandBusStore
from guardian.core.dependencies import get_current_user, require_api_key

router = APIRouter(
    prefix="/api/guardian/commands",
    tags=["Command Bus"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None
_store = CommandBusStore()


def configure_db(db: Any | None) -> None:
    """Configure DB handle for command bus persistence."""
    global _db, _store
    _db = db
    _store = CommandBusStore(db=db)


@router.get("/manifest")
async def get_manifest(request: Request) -> dict[str, Any]:
    manifest = build_manifest(request.app)
    return manifest.model_dump(mode="json")


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
