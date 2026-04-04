"""Backend delegation routes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.delegation_service import (
    QUEUE_NAME,
    DelegationConflictError,
    DelegationNotFoundError,
    DelegationService,
)
from guardian.core.dependencies import require_api_key
from guardian.protocol_tokens import AcceptanceStatus, DelegationEventType
from guardian.queue import task_events
from guardian.queue.redis_queue import cancel as cancel_task
from guardian.queue.redis_queue import enqueue
from guardian.tasks.types import DelegationDraftRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/delegations",
    tags=["Delegations"],
    dependencies=[Depends(require_api_key)],
)

_service = DelegationService()


def configure_db(db: Any | None) -> None:
    """Configure the delegation service with the current GuardianDB."""

    _service.configure_db(db)


def get_service() -> DelegationService:
    return _service


class DelegationDraftBody(BaseModel):
    thread_id: int | None = None
    conversation_id: str | None = None
    project_id: int | None = None
    repo_path: str = Field(min_length=1)
    executor: str = Field(min_length=1)
    user_intent: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


def _approval_metadata(
    *,
    publish_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    publish_result = publish_result or {}
    ok = True if not publish_result else bool(publish_result.get("ok"))
    status = (
        AcceptanceStatus.ACCEPTED.value
        if ok
        else AcceptanceStatus.ACCEPTED_DEGRADED.value
    )
    warnings: list[str] = []
    if not ok:
        warning = str(
            publish_result.get("error") or "task_event_publish_failed"
        )
        warnings.append(warning)
    return {
        "status": status,
        "warnings": warnings,
        "task_event_publish_ok": ok,
        "task_event_visibility_scope": publish_result.get("visibility_scope"),
        "task_event_id": publish_result.get("event_id"),
    }


def _delegation_event_payload(
    *,
    packet_id: str,
    job: Any,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "delegation_id": job.delegation_id,
        "packet_id": packet_id,
        "task_id": job.task_id,
        "status": job.status,
        "thread_id": job.thread_id,
        "conversation_id": job.conversation_id,
        "project_id": job.project_id,
        "repo_path": job.repo_path,
        "executor": job.executor,
        "task_prompt": job.task_prompt,
        "tags": list(job.tags),
    }
    if extra:
        payload.update(extra)
    return payload


def _publish_event_best_effort(
    task_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        return task_events.publish_with_visibility(task_id, event_type, payload)
    except Exception as exc:
        visibility_scope = task_events.classify_event_visibility(event_type)
        return {
            "ok": False,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": visibility_scope,
            "terminal_visibility": visibility_scope == "terminal",
            "execution_continued": True,
            "event_id": None,
            "failure_class": exc.__class__.__name__,
            "error": str(exc),
        }


@router.post("/draft", status_code=201)
async def create_delegation_draft(
    body: DelegationDraftBody,
) -> dict[str, Any]:
    request = DelegationDraftRequest(
        thread_id=body.thread_id,
        conversation_id=body.conversation_id,
        project_id=body.project_id,
        repo_path=body.repo_path,
        executor=body.executor,
        user_intent=body.user_intent,
        tags=list(body.tags),
        context=dict(body.context or {}),
    )
    packet = _service.draft_packet(request)
    return {"ok": True, "packet": packet.to_dict()}


@router.post("/{packet_id}/approve", status_code=201)
async def approve_delegation_packet(packet_id: str) -> dict[str, Any]:
    try:
        approval = _service.approve_packet(packet_id)
    except DelegationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DelegationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    publish_result: dict[str, Any] | None = None
    if approval.enqueue_required:
        try:
            enqueue(approval.task, QUEUE_NAME)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="delegation_enqueue_failed",
            ) from exc

        job = _service.mark_job_queued(approval.job.delegation_id)
        publish_result = _publish_event_best_effort(
            job.task_id,
            DelegationEventType.CREATED.value,
            _delegation_event_payload(
                packet_id=approval.packet.packet_id,
                job=job,
                extra={
                    "event_name": DelegationEventType.CREATED.value,
                    "acceptance_status": AcceptanceStatus.ACCEPTED.value,
                },
            ),
        )
    else:
        job = approval.job

    return {
        "ok": True,
        "packet_id": approval.packet.packet_id,
        "delegation_id": job.delegation_id,
        "task_id": job.task_id,
        "status": job.status,
        "acceptance_metadata": _approval_metadata(
            publish_result=publish_result,
        ),
    }


@router.get("/{delegation_id}/events")
async def stream_delegation_events(
    request: Request,
    delegation_id: str,
    last_id_query: str = Query("0-0", alias="last_id"),
    last_event_id_header: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    job = _service.get_job(delegation_id)
    if job is None:
        raise HTTPException(status_code=404, detail="delegation_not_found")

    # Delegation events reuse the existing task-event Redis stream. The
    # delegation/job row stores the backing task_id, so we bridge here instead
    # of introducing a new websocket or transport surface.
    task_id = job.task_id

    async def event_stream() -> AsyncGenerator[str, None]:
        last_id = str(last_event_id_header or last_id_query or "0-0")
        if "-" not in last_id:
            last_id = "0-0"
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0
        block_ms = int(os.getenv("TASK_EVENT_BLOCK_MS", "15000"))

        while True:
            if await request.is_disconnected():
                break

            try:
                events = await asyncio.to_thread(
                    task_events.read_events,
                    task_id,
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
                    if (
                        task_events.classify_event_visibility(
                            event.get("type") or ""
                        )
                        == "terminal"
                    ):
                        return

                heartbeat_elapsed = 0.0
            else:
                heartbeat_elapsed += block_ms / 1000.0
                if heartbeat_elapsed >= heartbeat_interval:
                    yield ": ping\n\n"
                    heartbeat_elapsed = 0.0

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{delegation_id}/cancel")
async def cancel_delegation(
    delegation_id: str,
) -> dict[str, Any]:
    try:
        result = _service.cancel_delegation(delegation_id)
    except DelegationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job = result.job
    publish_result: dict[str, Any] | None = None
    if result.changed:
        try:
            cancel_task(job.task_id)
        except Exception as exc:
            logger.warning(
                "[delegations] best-effort task cancel failed delegation_id=%s task_id=%s err=%s",
                delegation_id,
                job.task_id,
                exc,
            )

        publish_result = _publish_event_best_effort(
            job.task_id,
            DelegationEventType.CANCELLED.value,
            _delegation_event_payload(
                packet_id=job.packet_id,
                job=job,
                extra={
                    "event_name": DelegationEventType.CANCELLED.value,
                    "reason": "cancelled_by_request",
                },
            ),
        )

    return {
        "ok": True,
        "delegation_id": job.delegation_id,
        "task_id": job.task_id,
        "status": job.status,
        "event_published": bool(publish_result and publish_result.get("ok")),
        "event_visibility_scope": (
            publish_result.get("visibility_scope") if publish_result else None
        ),
    }


@router.post("/{delegation_id}/cancel")
async def cancel_delegation(delegation_id: str) -> dict[str, Any]:
    try:
        result = _service.cancel_delegation(delegation_id)
    except DelegationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job = result.job
    event_result: dict[str, Any] | None = None
    if result.changed:
        try:
            cancel_task(job.task_id)
        except Exception:
            pass
        event_result = _publish_event_best_effort(
            job.task_id,
            DelegationEventType.CANCELLED.value,
            _delegation_event_payload(
                packet_id=job.packet_id,
                job=job,
                extra={
                    "event_name": DelegationEventType.CANCELLED.value,
                    "reason": "cancel_requested",
                },
            ),
        )

    return {
        "ok": True,
        "delegation_id": job.delegation_id,
        "task_id": job.task_id,
        "status": job.status,
        "event_published": bool(event_result and event_result.get("ok")),
        "event_visibility_scope": (
            event_result.get("visibility_scope") if event_result else None
        ),
    }


__all__ = ["configure_db", "get_service", "router"]
