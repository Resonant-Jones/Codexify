"""Intent spine dispatch helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from guardian.command_bus.contracts import InvokeRequest
from guardian.command_bus.invoke import execute_invoke
from guardian.cron.models import CronJobCreateRequest
from guardian.intents.contracts import (
    GuardianCommandBusIntentTarget,
    GuardianCronCreateIntentTarget,
    GuardianIntentDispatchResult,
    GuardianIntentRequest,
)
from guardian.routes import command_bus as command_bus_routes
from guardian.routes import cron as cron_routes


def _build_provenance_json(intent: GuardianIntentRequest) -> dict[str, Any]:
    payload = intent.model_dump(mode="json")
    return {
        "intent_envelope": payload,
        "intent_id": intent.intent_id,
        "source_surface": intent.source_surface,
        "intent_kind": intent.intent_kind,
        "requested_at": intent.requested_at,
    }


def _build_invoke_request(intent: GuardianIntentRequest) -> InvokeRequest:
    if not isinstance(intent.target, GuardianCommandBusIntentTarget):
        raise HTTPException(
            status_code=422,
            detail="command_bus intent target is invalid",
        )
    invoke_idempotency_key = (
        intent.target.idempotency_key or ""
    ).strip() or intent.intent_id
    return InvokeRequest(
        invoke_version="1.0",
        command_id=intent.target.command_id,
        actor=intent.actor,
        arguments=intent.target.arguments,
        idempotency_key=invoke_idempotency_key,
        provenance_json=_build_provenance_json(intent),
    )


def _build_cron_create_request(
    intent: GuardianIntentRequest,
) -> CronJobCreateRequest:
    target = intent.target
    if not isinstance(target, GuardianCronCreateIntentTarget):
        raise HTTPException(
            status_code=422,
            detail="cron intent target is invalid",
        )
    return CronJobCreateRequest(
        name=str(target.name),
        schedule=str(target.schedule),
        job_type=str(target.job_type),
        payload=dict(target.payload or {}),
        is_enabled=bool(target.is_enabled),
    )


async def dispatch_guardian_intent(
    *,
    intent: GuardianIntentRequest,
    auth_subject: str,
    inbound_headers: dict[str, str],
    app: Any,
) -> GuardianIntentDispatchResult:
    if intent.policy.approval_required and intent.approval_state != "approved":
        return GuardianIntentDispatchResult(
            intent_id=intent.intent_id,
            status="blocked",
            dispatch_target=(
                "cron" if intent.intent_kind == "cron.create" else "command_bus"
            ),
            intent_kind=intent.intent_kind,
            source_surface=intent.source_surface,
            rejection_reason="approval_required",
            execution_state="blocked",
            provenance_json=_build_provenance_json(intent),
        )

    if intent.intent_kind == "cron.create":
        cron_request = _build_cron_create_request(intent)
        result = await cron_routes.create_cron_job(cron_request)
        receipt_ref = (
            f"cron_job_{result.get('id')}"
            if result.get("id") is not None
            else intent.receipt_ref or ""
        )
        return GuardianIntentDispatchResult(
            intent_id=intent.intent_id,
            status="accepted",
            dispatch_target="cron",
            intent_kind=intent.intent_kind,
            source_surface=intent.source_surface,
            receipt_ref=receipt_ref or None,
            downstream_result_json=dict(result),
            execution_state="accepted",
            provenance_json=_build_provenance_json(intent),
        )

    if intent.intent_kind != "command_bus.invoke":
        raise HTTPException(
            status_code=422,
            detail="unsupported_intent_kind",
        )

    invoke_request = _build_invoke_request(intent)
    result = await execute_invoke(
        payload=invoke_request,
        auth_subject=auth_subject,
        inbound_headers=inbound_headers,
        store=command_bus_routes._store,
        app=app,
        execution_lane="tools",
        allow_write_execution=intent.policy.allow_write_execution,
        confirmation_granted=intent.approval_state == "approved",
    )

    status = str(result.get("status") or "queued")
    receipt_ref = str(result.get("run_id") or intent.receipt_ref or "")
    if status == "blocked":
        normalized_status = "blocked"
        execution_state: str | None = "blocked"
    elif status in {"queued", "running", "completed"}:
        normalized_status = "accepted"
        execution_state = "accepted"
    else:
        normalized_status = "failed"
        execution_state = "failed"
    return GuardianIntentDispatchResult(
        intent_id=intent.intent_id,
        status=normalized_status,
        dispatch_target="command_bus",
        intent_kind=intent.intent_kind,
        source_surface=intent.source_surface,
        receipt_ref=receipt_ref or None,
        downstream_result_json=dict(result),
        execution_state=execution_state,
        provenance_json=_build_provenance_json(intent),
    )
