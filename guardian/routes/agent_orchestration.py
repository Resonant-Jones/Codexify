"""Agent orchestration routes for delegated multi-agent runs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
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

from guardian.agents.coding_agent_contracts import (
    CodingAgentResult,
    CodingAgentTaskEnvelope,
)
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

ALLOWED_RUNTIME_TARGETS = {"container", "terminal"}


def configure_db(db: Any | None) -> None:
    _store.configure_db(db)
    _event_publisher.configure_db(db)


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _coerce_optional_positive_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


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


class CodingExecutionRequest(BaseModel):
    run_id: str = Field(min_length=1)
    coding_task_id: str = Field(min_length=1)
    campaign_id: str | None = None
    work_order_id: str | None = None
    thread_id: str = Field(min_length=1)
    source_message_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    project_id: int | None = None
    adapter_kind: str = Field(default="pi_codex_runner", min_length=1)
    instructions: str = Field(min_length=1)
    repo_root: str | None = None
    context_summary: str | None = None
    permission_policy: dict[str, Any] = Field(default_factory=dict)
    # Optional single validation command; the worker runs it once if allowed.
    validation_command: str | None = None
    max_validation_attempts: int = Field(default=1, ge=1, le=3)
    worktree_lease_id: str | None = None
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    commit_message: str | None = None
    require_human_review_before_merge: bool = True

    model_config = ConfigDict(extra="forbid")


def build_coding_execution_task_payload(
    body: CodingExecutionRequest,
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    if "permission_policy" not in payload:
        payload["permission_policy"] = {}
    return payload


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
    runtime_target = (body.runtime_target or "container").strip()
    if runtime_target not in ALLOWED_RUNTIME_TARGETS:
        raise HTTPException(status_code=400, detail="invalid_runtime_target")

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
        runtime_target=runtime_target,
        rollback_mode="auto",
        status="running",
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={
            "deployment_id": deployment_id,
            "run_id": run["run_id"],
            "runtime_target": runtime_target,
        },
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="started",
        payload={
            "deployment_id": deployment_id,
            "run_id": run["run_id"],
            "runtime_target": runtime_target,
        },
    )
    return {"ok": True, "run": run}


@router.post("/coding/execute")
async def execute_coding_task(
    envelope: CodingAgentTaskEnvelope,
) -> dict[str, Any]:
    """Execute a coding task via a registered coding adapter.

    Takes a CodingAgentTaskEnvelope per ADR-020 and routes to the
    requested adapter kind.

    Returns immediately with run_id. Poll /api/agents/runs/{run_id}/events for progress.
    """
    # Create deployment to track this coding task and preserve the requested
    # adapter kind in Guardian-owned intake state.
    flow_id = f"coding_{envelope.coding_task_id}"
    deployment = _store.create_deployment(
        flow_id=flow_id,
        thread_id=int(envelope.thread_id) if envelope.thread_id else None,
        spec_json={
            "coding_task_id": envelope.coding_task_id,
            "campaign_id": envelope.campaign_id,
            "work_order_id": envelope.work_order_id,
            "adapter_kind": envelope.adapter_kind,
            "validation_command": envelope.validation_command,
            "max_validation_attempts": envelope.max_validation_attempts,
            "worktree_lease_id": envelope.worktree_lease_id,
            "require_worktree_lease": envelope.require_worktree_lease,
            "commit_after_validation": envelope.commit_after_validation,
            "commit_message": envelope.commit_message,
            "require_human_review_before_merge": (
                envelope.require_human_review_before_merge
            ),
            "source_thread_id": int(envelope.thread_id)
            if envelope.thread_id
            else None,
            "source_message_id": _coerce_optional_positive_int(
                envelope.source_message_id
            ),
            "user_id": envelope.user_id,
            "project_id": envelope.project_id,
            "attempt_id": envelope.attempt_id,
            "instructions": envelope.instructions,
            "repo_root": envelope.repo_root,
            "context_summary": envelope.context_summary,
            "permission_policy": {
                "allow_shell": envelope.permission_policy.allow_shell,
                "allow_network": envelope.permission_policy.allow_network,
                "allow_write": envelope.permission_policy.allow_write,
                "allowed_paths": list(envelope.permission_policy.allowed_paths),
                "max_runtime_seconds": envelope.permission_policy.max_runtime_seconds,
            },
        },
        spec_hash=_stable_hash(
            {
                "coding_task_id": envelope.coding_task_id,
                "campaign_id": envelope.campaign_id,
                "work_order_id": envelope.work_order_id,
                "attempt_id": envelope.attempt_id,
                "adapter_kind": envelope.adapter_kind,
                "validation_command": envelope.validation_command,
                "max_validation_attempts": envelope.max_validation_attempts,
                "worktree_lease_id": envelope.worktree_lease_id,
                "require_worktree_lease": envelope.require_worktree_lease,
                "commit_after_validation": envelope.commit_after_validation,
                "commit_message": envelope.commit_message,
                "require_human_review_before_merge": (
                    envelope.require_human_review_before_merge
                ),
            }
        ),
        trust_state="supervised",
    )

    # Create run for tracking
    # The DB only tracks the execution surface here; the worker resolves the
    # requested registered adapter at execution time.
    run = _store.create_run(
        deployment_id=deployment["deployment_id"],
        thread_id=deployment.get("thread_id"),
        runtime_target="container",
        rollback_mode="auto",
        status="queued",
    )

    # Emit created event
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={
            "coding_task_id": envelope.coding_task_id,
            "attempt_id": envelope.attempt_id,
            "deployment_id": deployment["deployment_id"],
        },
    )

    # Enqueue for async processing via CodingWorker
    from guardian.queue.redis_queue import enqueue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    task_payload = {
        "run_id": run["run_id"],
        "deployment_id": deployment["deployment_id"],
        "instructions": envelope.instructions,
        "cwd": envelope.repo_root,
        "timeout_seconds": envelope.permission_policy.max_runtime_seconds,
        "coding_task_id": envelope.coding_task_id,
        "campaign_id": envelope.campaign_id,
        "work_order_id": envelope.work_order_id,
        "attempt_id": envelope.attempt_id,
        "thread_id": int(envelope.thread_id) if envelope.thread_id else None,
        "source_message_id": _coerce_optional_positive_int(
            envelope.source_message_id
        ),
        "source_thread_id": int(envelope.thread_id)
        if envelope.thread_id
        else None,
        "user_id": envelope.user_id,
        "project_id": envelope.project_id,
        "validation_command": envelope.validation_command,
        "max_validation_attempts": envelope.max_validation_attempts,
        "worktree_lease_id": envelope.worktree_lease_id,
        "require_worktree_lease": envelope.require_worktree_lease,
        "commit_after_validation": envelope.commit_after_validation,
        "commit_message": envelope.commit_message,
        "require_human_review_before_merge": (
            envelope.require_human_review_before_merge
        ),
        "permission_policy": {
            "allow_shell": envelope.permission_policy.allow_shell,
            "allow_network": envelope.permission_policy.allow_network,
            "allow_write": envelope.permission_policy.allow_write,
            "allowed_paths": list(envelope.permission_policy.allowed_paths),
            "max_runtime_seconds": envelope.permission_policy.max_runtime_seconds,
        },
        "origin": "coding_execute_route",
    }
    enqueue_coding_execution(task_payload)

    return {
        "ok": True,
        "run_id": run["run_id"],
        "deployment_id": deployment["deployment_id"],
        "coding_task_id": envelope.coding_task_id,
        "campaign_id": envelope.campaign_id,
        "work_order_id": envelope.work_order_id,
    }


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
