"""Invoke orchestrator for command bus execution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from guardian.command_bus.contracts import (
    INVOKE_VERSION,
    MAX_PAYLOAD_BYTES,
    InvokeExternalPolicyRule,
    InvokePermissionProfile,
    InvokeRequest,
)
from guardian.connectors.external_transport_policy import (
    CommandTuple,
    ExternalPolicyDecision,
    ExternalPolicyRequest,
    ExternalPolicyRule,
    evaluate_external_transport_policy,
)
from guardian.command_bus.permission_profiles import (
    PermissionProfile,
    PermissionProfileRequest,
    evaluate_permission_profile,
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


def _optional_text(raw: object) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _derive_command_class(
    command: Any, profile_payload: InvokePermissionProfile
) -> str:
    explicit = _optional_text(profile_payload.request_command_class)
    if explicit is not None:
        return explicit

    effect = _optional_text(getattr(command, "effect", None))
    if effect in {"read", "write"}:
        return str(effect)

    method = str(getattr(command, "method", "GET")).upper()
    if method in {"GET", "HEAD"}:
        return "read"
    return "write"


def _build_permission_profile(
    profile_payload: InvokePermissionProfile,
) -> PermissionProfile:
    return PermissionProfile(
        profile_id=profile_payload.profile_id,
        actor_id=profile_payload.actor_id,
        subject_id=profile_payload.subject_id,
        task_id=profile_payload.task_id,
        project_id=profile_payload.project_id,
        thread_id=profile_payload.thread_id,
        allowed_command_classes=tuple(
            profile_payload.allowed_command_classes
        ),
        denied_command_classes=tuple(profile_payload.denied_command_classes),
        allowed_command_ids=tuple(profile_payload.allowed_command_ids),
        denied_command_ids=tuple(profile_payload.denied_command_ids),
        filesystem_access=profile_payload.filesystem_access,
        allowed_write_roots=tuple(
            Path(path) for path in profile_payload.allowed_write_roots
        ),
        shell_allowed=profile_payload.shell_allowed,
        shell_read_only=profile_payload.shell_read_only,
        allowed_shell_commands=tuple(profile_payload.allowed_shell_commands),
        network_allowed=profile_payload.network_allowed,
        connector_allowed=profile_payload.connector_allowed,
    )


def _build_permission_profile_request(
    *,
    payload: InvokeRequest,
    profile_payload: InvokePermissionProfile,
    command: Any,
    auth_subject: str,
    fallback_task_id: str,
) -> PermissionProfileRequest:
    task_id = (
        _optional_text(profile_payload.request_task_id)
        or _optional_text(payload.idempotency_key)
        or fallback_task_id
    )
    project_id = _optional_text(profile_payload.request_project_id)
    thread_id = _optional_text(profile_payload.request_thread_id)

    return PermissionProfileRequest(
        actor_id=payload.actor.id,
        subject_id=auth_subject,
        task_id=task_id,
        command_id=str(getattr(command, "command_id", payload.command_id)),
        command_class=_derive_command_class(command, profile_payload),
        project_id=project_id,
        thread_id=thread_id,
        requested_write_paths=tuple(profile_payload.requested_write_paths),
        uses_shell=profile_payload.uses_shell,
        shell_command=profile_payload.shell_command,
        shell_mutates=profile_payload.shell_mutates,
        uses_network=profile_payload.uses_network,
        uses_connector=profile_payload.uses_connector,
    )


_EXTERNAL_POLICY_TRIGGER_FIELDS: frozenset[str] = frozenset(
    {
        "external_transport",
        "external_target_url",
        "external_policy_rules",
        "external_command_namespace",
        "external_command_name",
        "external_connector_name",
    }
)


def _invoke_fields_set(payload: InvokeRequest) -> set[str]:
    raw_set = getattr(payload, "model_fields_set", None)
    if isinstance(raw_set, set):
        return raw_set
    legacy_set = getattr(payload, "__fields_set__", None)
    if isinstance(legacy_set, set):
        return legacy_set
    return set()


def _external_policy_is_triggered(payload: InvokeRequest) -> bool:
    fields_set = _invoke_fields_set(payload)
    return any(
        field_name in fields_set
        for field_name in _EXTERNAL_POLICY_TRIGGER_FIELDS
    )


def _build_external_policy_command_tuple(
    payload: InvokeRequest,
) -> CommandTuple | None:
    namespace = _optional_text(payload.external_command_namespace)
    name = _optional_text(payload.external_command_name)
    if namespace is None or name is None:
        return None
    return CommandTuple(namespace=namespace, name=name)


def _build_external_policy_rules(
    policy_rules: tuple[InvokeExternalPolicyRule, ...],
) -> list[ExternalPolicyRule]:
    rules: list[ExternalPolicyRule] = []
    for rule in policy_rules:
        command = None
        namespace = _optional_text(rule.command_namespace)
        name = _optional_text(rule.command_name)
        if namespace is not None and name is not None:
            command = CommandTuple(namespace=namespace, name=name)
        rules.append(
            ExternalPolicyRule(
                effect=rule.effect,
                connector_name=rule.connector_name,
                transport=rule.transport,
                command=command,
                url_host_pattern=rule.url_host_pattern,
                url_scheme=rule.url_scheme,
                project_id=rule.project_id,
                thread_id=rule.thread_id,
                reason=rule.reason,
            )
        )
    return rules


def _build_external_policy_request(
    *,
    payload: InvokeRequest,
    auth_subject: str,
) -> ExternalPolicyRequest:
    connector_name = _optional_text(payload.external_connector_name) or ""
    return ExternalPolicyRequest(
        actor_id=payload.actor.id,
        subject_id=auth_subject,
        connector_name=connector_name,
        transport=payload.external_transport or "",
        command=_build_external_policy_command_tuple(payload),
        target_url=payload.external_target_url,
        project_id=_optional_text(payload.external_project_id),
        thread_id=_optional_text(payload.external_thread_id),
    )


async def execute_invoke(
    *,
    payload: InvokeRequest,
    auth_subject: str,
    inbound_headers: dict[str, str],
    store: CommandBusStore,
    app: Any,
    execution_lane: str = "raw",
    allow_write_execution: bool = False,
    confirmation_granted: bool = False,
) -> dict[str, Any]:
    if execution_lane != "tools":
        # Write unlock is tools-lane only; raw/public lane stays read-only.
        allow_write_execution = False
        confirmation_granted = False

    validate_invoke_version(payload.invoke_version)
    validate_actor_claim(
        actor_id=payload.actor.id,
        delegated_by=payload.actor.delegated_by,
        auth_subject=auth_subject,
    )

    args_dict = payload.arguments.model_dump(mode="json", exclude_none=False)
    provenance_json = dict(payload.provenance_json or {})
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
        confirmation_granted=confirmation_granted,
    )

    permission_profile_decision = None
    external_policy_decision: ExternalPolicyDecision | None = None
    pre_dispatch_blocked_reason: str | None = None
    if payload.permission_profile is not None:
        profile = _build_permission_profile(payload.permission_profile)
        permission_request = _build_permission_profile_request(
            payload=payload,
            profile_payload=payload.permission_profile,
            command=command,
            auth_subject=auth_subject,
            fallback_task_id=f"invoke_{uuid4().hex[:16]}",
        )
        permission_profile_decision = evaluate_permission_profile(
            profile,
            permission_request,
        )
        if not permission_profile_decision.allowed:
            pre_dispatch_blocked_reason = (
                f"permission_profile_denied:{permission_profile_decision.code}"
            )
    if _external_policy_is_triggered(payload):
        external_policy_request = _build_external_policy_request(
            payload=payload,
            auth_subject=auth_subject,
        )
        external_policy_rules = _build_external_policy_rules(
            payload.external_policy_rules
        )
        external_policy_decision = evaluate_external_transport_policy(
            external_policy_request,
            external_policy_rules,
        )
        if (
            not external_policy_decision.allowed
            and pre_dispatch_blocked_reason is None
        ):
            pre_dispatch_blocked_reason = (
                "external_transport_policy_denied:"
                f"{external_policy_decision.code}"
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
    created_payload: dict[str, Any] = {
        "command_id": command.command_id,
        "status": "queued",
        "provenance_json": provenance_json,
        "policy": {
            "mode": invoke_policy.mode,
            "decision": invoke_policy.decision,
            "reason_codes": invoke_policy.reason_codes,
            "warnings": invoke_policy.warnings,
        },
    }
    if permission_profile_decision is not None:
        created_payload["permission_profile"] = {
            "code": permission_profile_decision.code,
            "reason": permission_profile_decision.reason,
            "blocked_before_dispatch": (
                not permission_profile_decision.allowed
            ),
        }
    if external_policy_decision is not None:
        created_payload["external_transport_policy"] = {
            "code": external_policy_decision.code,
            "reason": external_policy_decision.reason,
            "blocked_before_dispatch": (
                not external_policy_decision.allowed
            ),
        }
    store.append_event(
        run_id=run_id,
        event_type="run.created",
        payload=created_payload,
    )

    is_readonly_command = command.effect == "read" and command.method in {
        "GET",
        "HEAD",
    }
    should_execute = is_readonly_command or (
        allow_write_execution and command.effect == "write"
    )
    blocked_reason: str | None = pre_dispatch_blocked_reason

    # Explicit recursion guard, including future alias paths.
    if blocked_reason is None:
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
        blocked_payload: dict[str, Any] = {
            "reason": blocked_reason,
            "provenance_json": provenance_json,
            "policy": {
                "mode": invoke_policy.mode,
                "decision": invoke_policy.decision,
                "reason_codes": invoke_policy.reason_codes,
            },
        }
        if permission_profile_decision is not None:
            blocked_payload["permission_profile"] = {
                "code": permission_profile_decision.code,
                "reason": permission_profile_decision.reason,
                "blocked_before_dispatch": (
                    not permission_profile_decision.allowed
                ),
            }
        if external_policy_decision is not None:
            blocked_payload["external_transport_policy"] = {
                "code": external_policy_decision.code,
                "reason": external_policy_decision.reason,
                "blocked_before_dispatch": (
                    not external_policy_decision.allowed
                ),
            }
        store.append_event(
            run_id=run_id,
            event_type="run.blocked",
            payload=blocked_payload,
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
        if permission_profile_decision is not None:
            blocked_response["permission_profile"] = {
                "code": permission_profile_decision.code,
                "reason": permission_profile_decision.reason,
                "blocked_before_dispatch": (
                    not permission_profile_decision.allowed
                ),
            }
        if external_policy_decision is not None:
            blocked_response["external_transport_policy"] = {
                "code": external_policy_decision.code,
                "reason": external_policy_decision.reason,
                "blocked_before_dispatch": (
                    not external_policy_decision.allowed
                ),
            }
        if invoke_policy.warnings:
            blocked_response["warning"] = invoke_policy.warnings[0]
        return blocked_response

    store.update_run(run_id=run_id, status="running")
    store.append_event(
        run_id=run_id,
        event_type="run.started",
        payload={
            "command_id": command.command_id,
            "status": "running",
            "provenance_json": provenance_json,
        },
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
                "confirmation_granted": confirmation_granted,
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
                payload={
                    "reason": error_text,
                    "provenance_json": provenance_json,
                },
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
            payload={
                "error": error_text,
                "provenance_json": provenance_json,
            },
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
        payload={
            "status_code": execution_result.get("status_code"),
            "provenance_json": provenance_json,
        },
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
