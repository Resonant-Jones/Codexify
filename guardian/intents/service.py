"""Intent spine dispatch helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from guardian.command_bus.contracts import InvokeRequest
from guardian.command_bus.invoke import execute_invoke
from guardian.intents.contracts import (
    GuardianIntentDispatchResult,
    GuardianIntentRequest,
)
from guardian.routes import command_bus as command_bus_routes


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


async def dispatch_guardian_intent(
    *,
    intent: GuardianIntentRequest,
    auth_subject: str,
    inbound_headers: dict[str, str],
    app: Any,
) -> GuardianIntentDispatchResult:
    if intent.intent_kind != "command_bus.invoke":
        raise HTTPException(
            status_code=422,
            detail="unsupported_intent_kind",
        )

    if intent.policy.approval_required and intent.approval_state != "approved":
        return GuardianIntentDispatchResult(
            intent_id=intent.intent_id,
            status="blocked",
            dispatch_target="command_bus",
            intent_kind=intent.intent_kind,
            source_surface=intent.source_surface,
            rejection_reason="approval_required",
            execution_state="blocked",
            provenance_json=_build_provenance_json(intent),
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
