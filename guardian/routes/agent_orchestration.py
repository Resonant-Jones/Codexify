"""Agent orchestration routes for delegated multi-agent runs."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, AsyncGenerator

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from guardian.agents.events import AgentEventPublisher, publisher
from guardian.agents.store import AgentStore, store
from guardian.core.dependencies import require_api_key
from guardian.queue import task_events

router = APIRouter(
    prefix="/api/agents",
    tags=["Agent Orchestration"],
    dependencies=[Depends(require_api_key)],
)
chat_router = APIRouter(
    tags=["Agent Orchestration"],
    dependencies=[Depends(require_api_key)],
)

_store: AgentStore = store
_event_publisher: AgentEventPublisher = publisher


def configure_db(db: Any | None) -> None:
    _store.configure_db(db)
    _event_publisher.configure_db(db)


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class AgentPlanRequest(BaseModel):
    prompt: str = Field(min_length=1)
    thread_id: int | None = None
    proposed_steps: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class AgentDeploymentRequest(BaseModel):
    flow_id: str = Field(min_length=1)
    thread_id: int | None = None
    spec: dict[str, Any] = Field(default_factory=dict)
    spec_hash: str | None = None
    trust_state: str = "supervised"

    model_config = ConfigDict(extra="forbid")


class AgentRunStartRequest(BaseModel):
    runtime_target: str = "container"
    supervised: bool = True

    model_config = ConfigDict(extra="forbid")


@router.post("/plans")
async def create_plan(body: AgentPlanRequest) -> dict[str, Any]:
    spec = {
        "prompt": body.prompt,
        "thread_id": body.thread_id,
        "steps": body.proposed_steps,
    }
    plan_hash = _stable_hash(spec)
    return {
        "ok": True,
        "plan_id": f"plan_{plan_hash[:16]}",
        "spec_hash": plan_hash,
        "spec": spec,
    }


@router.post("/deployments")
async def create_deployment(body: AgentDeploymentRequest) -> dict[str, Any]:
    spec = dict(body.spec or {})
    spec_hash = body.spec_hash or _stable_hash(spec)
    deployment = _store.create_deployment(
        flow_id=body.flow_id,
        thread_id=body.thread_id,
        spec_json=spec,
        spec_hash=spec_hash,
        trust_state=body.trust_state,
    )
    return {"ok": True, "deployment": deployment}


@router.post("/deployments/{deployment_id}/runs")
async def start_run(
    deployment_id: str,
    body: AgentRunStartRequest = Body(default_factory=AgentRunStartRequest),
) -> dict[str, Any]:
    deployment = _store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="deployment_not_found")
    if not body.supervised and deployment.get("trust_state") != "unlocked":
        raise HTTPException(
            status_code=403,
            detail="unsupervised_run_requires_unlocked_deployment",
        )

    run = _store.create_run(
        deployment_id=deployment_id,
        thread_id=deployment.get("thread_id"),
        runtime_target=body.runtime_target,
        rollback_mode="auto",
        status="running",
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={"deployment_id": deployment_id, "run_id": run["run_id"]},
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="started",
        payload={"deployment_id": deployment_id, "run_id": run["run_id"]},
    )
    return {"ok": True, "run": run}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, Any]:
    run = _store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    _store.update_run_status(run_id=run_id, status="canceled")
    _event_publisher.emit(
        run_id=run_id,
        event_type="canceled",
        payload={"run_id": run_id},
    )
    return {"ok": True, "run_id": run_id, "status": "canceled"}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    run = _store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"ok": True, "run": run}


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    request: Request,
    run_id: str,
    last_id_query: str = Query("0-0", alias="last_id"),
    last_event_id_header: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        last_id = str(last_event_id_header or last_id_query or "0-0")
        if "-" not in last_id:
            last_id = "0-0"
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0
        block_ms = 15000

        while True:
            if await request.is_disconnected():
                break
            try:
                events = await asyncio.to_thread(
                    task_events.read_events,
                    run_id,
                    last_id,
                    block_ms=block_ms,
                    count=100,
                )
            except Exception:
                await asyncio.sleep(1)
                continue

            if events:
                for event_id, event in events:
                    data_str = json.dumps(event.get("data") or {}, default=str)
                    yield f"id: {event_id}\n"
                    yield f"event: {event.get('type') or 'task.event'}\n"
                    yield f"data: {data_str}\n\n"
                    last_id = event_id
                heartbeat_elapsed = 0.0
            else:
                heartbeat_elapsed += block_ms / 1000.0
                if heartbeat_elapsed >= heartbeat_interval:
                    yield ": ping\n\n"
                    heartbeat_elapsed = 0.0

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/chat/{thread_id}/agent-runs")
async def list_thread_runs(thread_id: int) -> dict[str, Any]:
    runs = _store.list_runs_for_thread(thread_id)
    return {"ok": True, "thread_id": thread_id, "runs": runs}


@chat_router.get("/api/chat/{thread_id}/agent-runs")
async def list_thread_runs_via_chat(thread_id: int) -> dict[str, Any]:
    runs = _store.list_runs_for_thread(thread_id)
    return {"ok": True, "thread_id": thread_id, "runs": runs}
