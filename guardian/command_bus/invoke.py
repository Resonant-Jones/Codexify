"""Invoke orchestrator for command bus execution."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException

from guardian.command_bus.contracts import (
    INVOKE_VERSION,
    MAX_PAYLOAD_BYTES,
    InvokeRequest,
)
from guardian.command_bus.loopback_http_adapter import (
    execute_loopback_request,
    is_recursion_blocked,
    render_path,
)
from guardian.command_bus.manifest import build_command_index
from guardian.command_bus.redaction_policy import (
    canonical_json,
    compute_args_hash,
    redact_arguments,
)
from guardian.command_bus.store import CommandBusStore, IdempotencyConflictError
from guardian.tools.policy import (
    apply_policy_mode,
    evaluate_tool_policy,
    get_policy_mode,
)


def validate_invoke_version(version: str) -> None:
    if version != INVOKE_VERSION:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_invoke_version",
                "requested": version,
                "supported_invoke_versions": [INVOKE_VERSION],
            },
        )


def validate_actor_claim(
    *, actor_id: str, delegated_by: str | None, auth_subject: str
) -> None:
    if actor_id == auth_subject:
        return
    if delegated_by and delegated_by == auth_subject:
        return
    raise HTTPException(
        status_code=403,
        detail={
            "error": "actor_claim_not_permitted",
            "auth_subject": auth_subject,
        },
    )


def _response_from_existing_run(
    *,
    run: dict[str, Any],
    manifest_version: str,
    fallback_invoke_version: str,
) -> dict[str, Any]:
    run_id = str(run.get("run_id") or "")
    status = str(run.get("status") or "queued")
    response: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "invoke_version": str(
            run.get("invoke_version") or fallback_invoke_version
        ),
        "manifest_version": manifest_version,
        "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
        "policy_warnings": [],
    }

    result_json = run.get("result_json")
    if status == "completed" and result_json is not None:
        response["inline_result"] = result_json
    if run.get("error_text") is not None:
        response["error"] = str(run["error_text"])
    return response


async def execute_invoke(
    *,
    payload: InvokeRequest,
    auth_subject: str,
    inbound_headers: dict[str, str],
    store: CommandBusStore,
    app: Any,
) -> dict[str, Any]:
    validate_invoke_version(payload.invoke_version)
    validate_actor_claim(
        actor_id=payload.actor.id,
        delegated_by=payload.actor.delegated_by,
        auth_subject=auth_subject,
    )

    args_dict = payload.arguments.model_dump(mode="json", exclude_none=False)
    encoded_size = len(canonical_json(args_dict).encode("utf-8"))
    if encoded_size > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "payload_too_large",
                "max_payload_bytes": MAX_PAYLOAD_BYTES,
            },
        )

    index, manifest = build_command_index(app)
    command = index.get(payload.command_id)
    if command is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "command_not_found",
                "command_id": payload.command_id,
            },
        )

    idempotency_key = (payload.idempotency_key or "").strip() or None
    if idempotency_key:
        existing_run = store.get_run_by_idempotency_key(
            command.command_id,
            idempotency_key,
        )
        if existing_run is not None:
            if str(existing_run.get("auth_subject") or "") != auth_subject:
                raise HTTPException(
                    status_code=403,
                    detail={"error": "idempotency_key_not_permitted"},
                )
            return _response_from_existing_run(
                run=existing_run,
                manifest_version=manifest.manifest_version,
                fallback_invoke_version=payload.invoke_version,
            )

    policy_mode = get_policy_mode(os.environ)
    invoke_policy = apply_policy_mode(
        evaluate_tool_policy(
            payload.actor.model_dump(mode="json"),
            command.model_dump(mode="json"),
            args_dict,
            os.environ,
        ),
        mode=policy_mode,
    )

    args_hash = compute_args_hash(args_dict)
    args_redacted = redact_arguments(command.command_id, args_dict)
    try:
        run = store.create_run(
            command_id=command.command_id,
            status="queued",
            actor_kind=payload.actor.kind,
            actor_id=payload.actor.id,
            actor_session_id=payload.actor.session_id,
            delegated_by=payload.actor.delegated_by,
            auth_subject=auth_subject,
            invoke_version=payload.invoke_version,
            idempotency_key=idempotency_key,
            args_hash=args_hash,
            args_redacted=args_redacted,
        )
    except IdempotencyConflictError as exc:
        existing_run = exc.existing_run
        if str(existing_run.get("auth_subject") or "") != auth_subject:
            raise HTTPException(
                status_code=403,
                detail={"error": "idempotency_key_not_permitted"},
            ) from exc
        return _response_from_existing_run(
            run=existing_run,
            manifest_version=manifest.manifest_version,
            fallback_invoke_version=payload.invoke_version,
        )
    run_id = run["run_id"]
    store.append_event(
        run_id=run_id,
        event_type="run.created",
        payload={
            "command_id": command.command_id,
            "status": "queued",
            "policy": {
                "mode": invoke_policy.mode,
                "decision": invoke_policy.decision,
                "reason_codes": invoke_policy.reason_codes,
                "warnings": invoke_policy.warnings,
            },
        },
    )

    should_execute = command.effect == "read" and command.method in {
        "GET",
        "HEAD",
    }
    blocked_reason: str | None = None

    # Explicit recursion guard, including future alias paths.
    try:
        rendered = render_path(
            command.path_template, args_dict.get("path_params") or {}
        )
    except Exception as exc:
        blocked_reason = f"invalid_path_params: {exc}"
    else:
        if is_recursion_blocked(rendered):
            blocked_reason = "recursion_guard_blocked"

    if invoke_policy.blocked and blocked_reason is None:
        reasons = ",".join(
            invoke_policy.reason_codes or [invoke_policy.decision]
        )
        blocked_reason = f"policy_{invoke_policy.decision}:{reasons}"

    if not should_execute and blocked_reason is None:
        blocked_reason = "phase1_write_blocked"

    if blocked_reason is not None:
        store.update_run(
            run_id=run_id, status="blocked", error_text=blocked_reason
        )
        store.append_event(
            run_id=run_id,
            event_type="run.blocked",
            payload={
                "reason": blocked_reason,
                "policy": {
                    "mode": invoke_policy.mode,
                    "decision": invoke_policy.decision,
                    "reason_codes": invoke_policy.reason_codes,
                },
            },
        )
        blocked_response = {
            "run_id": run_id,
            "status": "blocked",
            "invoke_version": payload.invoke_version,
            "manifest_version": manifest.manifest_version,
            "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
            "error": blocked_reason,
            "policy_warnings": invoke_policy.warnings,
        }
        if invoke_policy.warnings:
            blocked_response["warning"] = invoke_policy.warnings[0]
        return blocked_response

    store.update_run(run_id=run_id, status="running")
    store.append_event(
        run_id=run_id,
        event_type="run.started",
        payload={"command_id": command.command_id, "status": "running"},
    )

    try:
        execution_result = await execute_loopback_request(
            method=command.method,
            path_template=command.path_template,
            path_params=args_dict.get("path_params") or {},
            query=args_dict.get("query") or {},
            headers=args_dict.get("headers") or {},
            body=args_dict.get("body"),
            inbound_headers=inbound_headers,
            policy_context={
                "actor": payload.actor.model_dump(mode="json"),
                "effect": command.effect,
                "risk": command.risk,
                "approval_mode": command.approval_mode,
                "requires_confirmation": command.approval_mode != "none",
                "policy_mode": policy_mode,
            },
        )
    except Exception as exc:
        error_text = str(exc)
        is_policy_or_guard_block = (
            error_text.startswith("policy_blocked:")
            or error_text == "recursion_guard_blocked"
            or "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE" in error_text
            or "GUARDIAN_API_BASE" in error_text
        )
        if is_policy_or_guard_block:
            store.update_run(
                run_id=run_id, status="blocked", error_text=error_text
            )
            store.append_event(
                run_id=run_id,
                event_type="run.blocked",
                payload={"reason": error_text},
            )
            blocked_response = {
                "run_id": run_id,
                "status": "blocked",
                "invoke_version": payload.invoke_version,
                "manifest_version": manifest.manifest_version,
                "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
                "error": error_text,
                "policy_warnings": invoke_policy.warnings,
            }
            if invoke_policy.warnings:
                blocked_response["warning"] = invoke_policy.warnings[0]
            return blocked_response

        store.update_run(run_id=run_id, status="failed", error_text=error_text)
        store.append_event(
            run_id=run_id,
            event_type="run.failed",
            payload={"error": error_text},
        )
        failed_response = {
            "run_id": run_id,
            "status": "failed",
            "invoke_version": payload.invoke_version,
            "manifest_version": manifest.manifest_version,
            "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
            "error": error_text,
            "policy_warnings": invoke_policy.warnings,
        }
        if invoke_policy.warnings:
            failed_response["warning"] = invoke_policy.warnings[0]
        return failed_response

    store.update_run(
        run_id=run_id, status="completed", result_json=execution_result
    )
    store.append_event(
        run_id=run_id,
        event_type="run.completed",
        payload={"status_code": execution_result.get("status_code")},
    )
    return {
        "run_id": run_id,
        "status": "completed",
        "invoke_version": payload.invoke_version,
        "manifest_version": manifest.manifest_version,
        "events_url": f"/api/guardian/commands/runs/{run_id}/events?after_seq=0",
        "inline_result": execution_result,
        "policy_warnings": invoke_policy.warnings,
    }
