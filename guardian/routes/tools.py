"""
Tools Routes
~~~~~~~~~~~~

Callable tools lane with canonical contracts, legacy compatibility adapters,
and manifest derivation from the command bus.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from guardian.cognition.system_profiles.resolver import switch_thread_profile
from guardian.command_bus.contracts import (
    ActorSpec,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.manifest import build_command_index
from guardian.core.dependencies import get_request_user_id, require_api_key
from guardian.tools.approval_tokens import (
    ApprovalTokenError,
    approval_idempotency_key,
    compute_policy_hash,
    decode_approval_token,
    issue_approval_token,
    verify_approval_token,
)
from guardian.tools.coercion import (
    ToolArgumentCoercionError,
    coerce_tool_arguments,
)
from guardian.tools.derive import derive_tools_from_command_manifest
from guardian.tools.policy import (
    apply_policy_mode,
    evaluate_tool_policy,
    get_policy_mode,
)
from guardian.tools.spec import (
    ToolApproveRequest,
    ToolCallRequest,
    ToolCallResponse,
    ToolManifestEnvelope,
    ToolPolicySummary,
    ToolSpec,
)

logger = logging.getLogger(__name__)

# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, Dict[str, Any]] = {}

DEPRECATION_PHASE = "1.5"
MANIFEST_REPLACED_BY = "/api/guardian/commands/manifest"
INVOKE_REPLACED_BY = "/api/guardian/commands/invoke"
APPROVE_REPLACED_BY = "/api/tools/approve"
_MANIFEST_CACHE_TTL_SECONDS = 5.0
_manifest_cache_app_id: int | None = None
_manifest_cache_expires_at = 0.0
_manifest_cache_index: dict[str, Any] = {}
_manifest_cache_commands: list[Any] = []
_manifest_cache_manifest: dict[str, Any] = {}
_MANIFEST_FORMAT_ENVELOPE = "envelope"
_MANIFEST_FORMAT_ARRAY = "array"


class ToolRequest(BaseModel):
    """
    Legacy local tools request model retained for profile-switch helper tests.
    """

    name: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    actor: dict[str, Any] | None = None
    tool_id: str | None = None
    command_id: str | None = None
    operation_id: str | None = None
    method: str | None = None
    path: str | None = None
    path_template: str | None = None
    arguments: dict[str, Any] | None = None
    idempotency_key: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)


# Import optional dependencies used by local profile-switch helper.
try:
    from guardian.core.dependencies import chatlog_db, event_bus
except ImportError:
    chatlog_db = None

    class _NoopEventBus:
        @staticmethod
        def emit_event(_topic: str, _payload: dict[str, Any]) -> None:
            return None

    event_bus = _NoopEventBus()


router = APIRouter(prefix="/tools", tags=["Tools"])
api_router = APIRouter(prefix="/api/tools", tags=["Tools"])


def _deprecation_headers(replaced_by: str) -> dict[str, str]:
    return {
        "X-Codexify-Deprecated": "true",
        "X-Codexify-Deprecation-Replaced-By": replaced_by,
        "X-Codexify-Deprecation-Phase": DEPRECATION_PHASE,
    }


def _apply_deprecation_headers(
    response: Response | None, replaced_by: str
) -> None:
    if response is None:
        return
    for key, value in _deprecation_headers(replaced_by).items():
        response.headers[key] = value


def _http_error(
    *, status_code: int, detail: Any, replaced_by: str
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=_deprecation_headers(replaced_by),
    )


def _raise_with_deprecation(
    exc: HTTPException, *, replaced_by: str
) -> HTTPException:
    headers = dict(exc.headers or {})
    headers.update(_deprecation_headers(replaced_by))
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.detail,
        headers=headers,
    )


def _log_shim_hit(
    *, request: Request | None, subject: str | None, command_id: str | None
) -> None:
    path = request.url.path if request is not None else "<direct>"
    logger.info(
        "legacy_tools_shim path=%s subject=%s command_id=%s",
        path,
        subject or "-",
        command_id or "-",
    )


def _resolve_auth_subject(request: Request | None) -> str | None:
    if request is None:
        return None
    try:
        derived = get_request_user_id(request.headers.get("X-User-Id"))
    except Exception:
        return None
    derived_str = str(derived or "").strip()
    return derived_str or None


def _resolve_actor(
    body: ToolCallRequest | ToolRequest, request: Request | None
) -> tuple[ActorSpec, str]:
    header_user = (
        request.headers.get("X-User-Id", "").strip() if request else ""
    ) or None
    auth_subject = header_user or _resolve_auth_subject(request)
    if not auth_subject:
        raise _http_error(
            status_code=401,
            detail={"error": "missing_identity_context"},
            replaced_by=INVOKE_REPLACED_BY,
        )

    if body.actor is not None:
        try:
            actor = ActorSpec.model_validate(body.actor)
        except ValidationError as exc:
            raise _http_error(
                status_code=400,
                detail={"error": "invalid_actor", "message": str(exc)},
                replaced_by=INVOKE_REPLACED_BY,
            ) from exc
        return actor, auth_subject

    return ActorSpec(kind="human", id=auth_subject), auth_subject


def _get_command_cache(
    app: Any,
) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    global _manifest_cache_app_id
    global _manifest_cache_expires_at
    global _manifest_cache_index
    global _manifest_cache_commands
    global _manifest_cache_manifest
    now = time.monotonic()
    app_id = id(app)
    cache_stale = (
        _manifest_cache_app_id != app_id
        or now >= _manifest_cache_expires_at
        or not _manifest_cache_index
    )
    if cache_stale:
        index, manifest = build_command_index(app)
        manifest_payload = manifest.model_dump(mode="json")
        _manifest_cache_app_id = app_id
        _manifest_cache_expires_at = now + _MANIFEST_CACHE_TTL_SECONDS
        _manifest_cache_index = index
        _manifest_cache_commands = list(manifest.commands)
        _manifest_cache_manifest = manifest_payload
    return (
        _manifest_cache_index,
        _manifest_cache_commands,
        _manifest_cache_manifest,
    )


def _get_tool_maps(
    manifest_payload: dict[str, Any],
) -> tuple[list[ToolSpec], dict[str, ToolSpec], dict[str, ToolSpec], dict[str, ToolSpec]]:
    tools = derive_tools_from_command_manifest(manifest_payload)
    tools_by_tool_id: dict[str, ToolSpec] = {}
    tools_by_command_id: dict[str, ToolSpec] = {}
    tools_by_openai_name: dict[str, ToolSpec] = {}
    for tool in tools:
        tools_by_tool_id[tool.tool_id] = tool
        tools_by_command_id[tool.command_id] = tool
        existing_openai = tools_by_openai_name.get(tool.openai_name)
        if existing_openai is not None and existing_openai.tool_id != tool.tool_id:
            raise _http_error(
                status_code=500,
                detail={
                    "error": "openai_name_collision",
                    "openai_name": tool.openai_name,
                    "tool_ids": [existing_openai.tool_id, tool.tool_id],
                },
                replaced_by=MANIFEST_REPLACED_BY,
            )
        tools_by_openai_name[tool.openai_name] = tool
    return tools, tools_by_tool_id, tools_by_command_id, tools_by_openai_name


def _path_matches_template(path_template: str, concrete_path: str) -> bool:
    template_segments = [s for s in path_template.split("/") if s]
    path_segments = [s for s in concrete_path.split("/") if s]
    if len(template_segments) != len(path_segments):
        return False
    for template_segment, path_segment in zip(template_segments, path_segments):
        if template_segment.startswith("{") and template_segment.endswith("}"):
            continue
        if template_segment != path_segment:
            return False
    return True


def _resolve_method_path_command_id(
    *, method: str, path_value: str, index: dict[str, Any], commands: list[Any]
) -> str | None:
    route_id = f"route::{method}::{path_value}"
    if route_id in index:
        return index[route_id].command_id
    if "{" in path_value:
        return None
    matches = [
        command.command_id
        for command in commands
        if command.method == method
        and _path_matches_template(command.path_template, path_value)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise _http_error(
            status_code=400,
            detail={
                "error": "ambiguous_path_match",
                "method": method,
                "path": path_value,
            },
            replaced_by=INVOKE_REPLACED_BY,
        )
    return None


def _try_map_legacy_request_to_command_id(
    body: ToolCallRequest, index: dict[str, Any], commands: list[Any]
) -> str | None:
    operation_id = (body.operation_id or "").strip()
    if operation_id:
        op_command_id = f"op::{operation_id}"
        command = index.get(op_command_id)
        if command is not None:
            return command.command_id

    method = (body.method or "").strip().upper()
    raw_path = (body.path_template or body.path or "").strip()
    if method and raw_path:
        resolved = _resolve_method_path_command_id(
            method=method,
            path_value=raw_path,
            index=index,
            commands=commands,
        )
        if resolved:
            return resolved

    name = (body.name or "").strip()
    if name:
        command = index.get(name)
        if command is not None:
            return command.command_id
        op_from_name = index.get(f"op::{name}")
        if op_from_name is not None:
            return op_from_name.command_id
        for entry in commands:
            if entry.operation_id == name:
                return entry.command_id
    return None


def _resolve_tool_and_command(
    *,
    body: ToolCallRequest,
    command_index: dict[str, Any],
    command_list: list[Any],
    manifest_payload: dict[str, Any],
) -> tuple[ToolSpec, Any]:
    _tools, tools_by_tool_id, tools_by_command_id, tools_by_openai_name = (
        _get_tool_maps(manifest_payload)
    )

    explicit_tool_id = (body.tool_id or "").strip()
    if explicit_tool_id:
        tool = tools_by_tool_id.get(explicit_tool_id)
        if tool is None:
            raise _http_error(
                status_code=400,
                detail={
                    "error": "unknown_tool_command",
                    "tool_id": explicit_tool_id,
                },
                replaced_by=INVOKE_REPLACED_BY,
            )
        command = command_index.get(tool.command_id)
        if command is None:
            raise _http_error(
                status_code=404,
                detail={
                    "error": "command_not_found",
                    "command_id": tool.command_id,
                },
                replaced_by=INVOKE_REPLACED_BY,
            )
        return tool, command

    explicit_command_id = (body.command_id or "").strip()
    if explicit_command_id:
        command = command_index.get(explicit_command_id)
        if command is None:
            raise _http_error(
                status_code=400,
                detail={
                    "error": "unknown_tool_command",
                    "command_id": explicit_command_id,
                },
                replaced_by=INVOKE_REPLACED_BY,
            )
        tool = tools_by_command_id.get(command.command_id)
        if tool is None:
            raise _http_error(
                status_code=404,
                detail={
                    "error": "tool_not_found_for_command",
                    "command_id": command.command_id,
                },
                replaced_by=INVOKE_REPLACED_BY,
            )
        return tool, command

    legacy_mapped_command_id = _try_map_legacy_request_to_command_id(
        body, command_index, command_list
    )
    if legacy_mapped_command_id:
        command = command_index[legacy_mapped_command_id]
        tool = tools_by_command_id.get(command.command_id)
        if tool is None:
            raise _http_error(
                status_code=404,
                detail={
                    "error": "tool_not_found_for_command",
                    "command_id": command.command_id,
                },
                replaced_by=INVOKE_REPLACED_BY,
            )
        return tool, command

    openai_name = (body.name or "").strip()
    if openai_name:
        tool = tools_by_openai_name.get(openai_name)
        if tool is not None:
            command = command_index.get(tool.command_id)
            if command is None:
                raise _http_error(
                    status_code=404,
                    detail={
                        "error": "command_not_found",
                        "command_id": tool.command_id,
                    },
                    replaced_by=INVOKE_REPLACED_BY,
                )
            return tool, command

    raise _http_error(
        status_code=400,
        detail={
            "error": "unknown_tool_command",
            "tool_id": body.tool_id,
            "command_id": body.command_id,
            "operation_id": body.operation_id,
            "name": body.name,
            "method": body.method,
            "path": body.path or body.path_template,
        },
        replaced_by=INVOKE_REPLACED_BY,
    )


def _extract_raw_arguments(body: ToolCallRequest) -> dict[str, Any]:
    if isinstance(body.arguments, dict) and body.arguments:
        return dict(body.arguments)
    if isinstance(body.args, dict) and body.args:
        return dict(body.args)
    if isinstance(body.arguments, dict):
        return dict(body.arguments)
    if isinstance(body.args, dict):
        return dict(body.args)
    return {}


def _policy_summary_from_decision(
    *, decision: Any, mode: str
) -> ToolPolicySummary:
    reasons: list[str] = []
    for reason in list(getattr(decision, "reason_codes", []) or []):
        reason_str = str(reason or "").strip()
        if reason_str and reason_str not in reasons:
            reasons.append(reason_str)
    decision_name = str(getattr(decision, "decision")) or "deny"
    if (
        decision_name == "require_confirmation"
        and "requires_confirmation" not in reasons
    ):
        reasons.append("requires_confirmation")
    return ToolPolicySummary(
        decision=decision_name,  # type: ignore[arg-type]
        reasons=reasons,
        mode=mode,  # type: ignore[arg-type]
    )


def _policy_hash_payload(
    *,
    tool: ToolSpec,
    policy: ToolPolicySummary,
) -> dict[str, Any]:
    return {
        "tool_id": tool.tool_id,
        "command_id": tool.command_id,
        "decision": policy.decision,
        "reasons": sorted(policy.reasons),
        "mode": policy.mode,
    }


def _invoke_arguments_from_normalized(
    normalized: dict[str, Any],
) -> InvokeArguments:
    return InvokeArguments(
        path_params=dict(normalized.get("path_params") or {}),
        query=dict(normalized.get("query") or {}),
        headers=dict(normalized.get("headers") or {}),
        body=normalized.get("body"),
    )


def _tool_call_from_invoke_response(
    *,
    invoke_response: dict[str, Any],
    policy: ToolPolicySummary,
    normalized_arguments: dict[str, Any],
    request_id: str | None,
    command_id: str,
) -> ToolCallResponse:
    invoke_status = str(invoke_response.get("status") or "failed")
    if invoke_status == "completed":
        status = "completed"
    elif invoke_status == "blocked":
        status = "blocked" if policy.decision != "deny" else "denied"
    else:
        status = "error"

    return ToolCallResponse(
        status=status,  # type: ignore[arg-type]
        policy=policy,
        run_id=(
            str(invoke_response.get("run_id"))
            if invoke_response.get("run_id")
            else None
        ),
        events_url=(
            str(invoke_response.get("events_url"))
            if invoke_response.get("events_url")
            else None
        ),
        result=invoke_response.get("inline_result"),
        error=invoke_response.get("error"),
        normalized_arguments=normalized_arguments,
        request_id=request_id,
        command_id=command_id,
    )


def _legacy_execute_payload(response: ToolCallResponse) -> dict[str, Any]:
    run_id = str(response.run_id or "")
    result_payload = (
        dict(response.result)
        if isinstance(response.result, dict)
        else ({"value": response.result} if response.result is not None else {})
    )

    if response.error:
        error_text = (
            response.error.get("code")
            if isinstance(response.error, dict)
            else str(response.error)
        )
        result_payload = dict(result_payload)
        result_payload.setdefault("error", error_text)
    else:
        error_text = None

    warnings: list[dict[str, Any]] = []
    if response.policy.mode == "warn" and response.policy.decision != "allow":
        warnings.append(
            {
                "decision": response.policy.decision,
                "reason_codes": list(response.policy.reasons),
            }
        )

    return {
        "job_id": run_id,
        "status": response.status,
        "result": result_payload,
        "run_id": response.run_id,
        "events_url": response.events_url,
        "command_id": response.command_id,
        "error": error_text,
        "policy_warnings": warnings,
        "approval_required": response.approval_required,
        "approval_token": response.approval_token,
    }


def _manifest_hash(manifest_payload: dict[str, Any]) -> str:
    stable_payload = dict(manifest_payload)
    stable_payload.pop("generated_at", None)
    serialized = json.dumps(
        stable_payload, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _derive_openai_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [tool.to_openai_function_tool() for tool in tools]


def build_tool_manifest_envelope(request: Request) -> ToolManifestEnvelope:
    _index, _commands, manifest_payload = _get_command_cache(request.app)
    tools, _, _, _ = _get_tool_maps(manifest_payload)
    return ToolManifestEnvelope(
        tool_manifest_version="2.0",
        manifest_version=str(manifest_payload.get("manifest_version", "1.0")),
        generated_at=str(manifest_payload.get("generated_at") or ""),
        command_manifest_hash=_manifest_hash(manifest_payload),
        tools=tools,
        openai_tools=_derive_openai_tools(tools),
    )


def _tools_array_compat_payload(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for tool in tools:
        payload.append(
            {
                "name": tool.name,
                "description": tool.description,
                "command_id": tool.command_id,
                "aliases": list(tool.aliases),
                "method": tool.method,
                "path_template": tool.path_template,
                "operation_id": tool.operation_id,
                "risk": tool.risk,
                "effect": tool.effect,
                "idempotency": tool.idempotency,
                "approval_mode": (
                    "blocked_phase1" if tool.requires_confirmation else "none"
                ),
                "args_schema": tool.input_schema,
                "tool_id": tool.tool_id,
                "openai_name": tool.openai_name,
            }
        )
    return payload


def _normalize_manifest_format(raw_format: str) -> str:
    normalized = str(raw_format or _MANIFEST_FORMAT_ENVELOPE).strip().lower()
    if not normalized:
        normalized = _MANIFEST_FORMAT_ENVELOPE
    if normalized in {_MANIFEST_FORMAT_ENVELOPE, _MANIFEST_FORMAT_ARRAY}:
        return normalized
    raise _http_error(
        status_code=400,
        detail={
            "error": "invalid_manifest_format",
            "message": "format must be one of: envelope, array",
            "received": raw_format,
            "supported": [_MANIFEST_FORMAT_ENVELOPE, _MANIFEST_FORMAT_ARRAY],
        },
        replaced_by=MANIFEST_REPLACED_BY,
    )


def _run_legacy_tool_locally(body: ToolRequest) -> dict[str, Any]:
    result: dict[str, Any]
    args = body.args or {}

    if body.name in {"guardian.profile.switch", "set_profile"}:
        thread_id = _coerce_thread_id(args.get("thread_id"))
        profile_id = str(args.get("profile_id") or "").strip()
        if thread_id is None:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "thread_id is required for guardian.profile.switch",
            }
        elif not profile_id:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "profile_id is required",
            }
        elif chatlog_db is None:
            result = {
                "ok": False,
                "tool": body.name,
                "error": "chat_db_unavailable",
                "thread_id": thread_id,
                "profile_id": profile_id,
            }
        else:
            try:
                resolved = switch_thread_profile(
                    thread_id=thread_id,
                    profile_id=profile_id,
                    chatlog_db=chatlog_db,
                )
                result = {
                    "ok": True,
                    "tool": body.name,
                    "thread_id": thread_id,
                    "active_profile_id": resolved.active_profile_id,
                    "provider_override": resolved.provider_override,
                    "model_override": resolved.model_override,
                }
                try:
                    event_bus.emit_event(
                        "thread.profile.switched",
                        {
                            "thread_id": thread_id,
                            "active_profile_id": resolved.active_profile_id,
                            "provider_override": resolved.provider_override,
                            "model_override": resolved.model_override,
                        },
                    )
                except Exception:
                    logger.debug(
                        "Tools.execute profile switch event emit failed",
                        exc_info=True,
                    )
            except Exception as exc:
                result = {
                    "ok": False,
                    "tool": body.name,
                    "error": str(exc),
                    "thread_id": thread_id,
                    "profile_id": profile_id,
                }
    else:
        result = {"ok": True, "tool": body.name, "args": args}
    return result


def _coerce_thread_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def tools_execute(body: ToolRequest, api_key: str = Depends(require_api_key)):
    """
    Legacy local helper used by profile-switch tests.
    """

    jid = str(uuid4())
    result = _run_legacy_tool_locally(body)
    JOBS[jid] = {"status": "done", "result": result}
    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
    return {"job_id": jid, "status": "done", "result": result}


def _store_job_snapshot(response: ToolCallResponse) -> None:
    if not response.run_id:
        return
    payload = (
        dict(response.result)
        if isinstance(response.result, dict)
        else ({"value": response.result} if response.result is not None else {})
    )
    if response.error:
        payload = dict(payload)
        payload["error"] = response.error
    JOBS[response.run_id] = {"status": response.status, "result": payload}


async def _execute_tools_call(
    *,
    body: ToolCallRequest,
    request: Request,
    response: Response,
    legacy: bool,
) -> ToolCallResponse | JSONResponse:
    _apply_deprecation_headers(response, INVOKE_REPLACED_BY)
    actor, auth_subject = _resolve_actor(body, request)
    command_index, command_list, manifest_payload = _get_command_cache(
        request.app
    )
    mapped_command_id: str | None = None
    try:
        tool_spec, command = _resolve_tool_and_command(
            body=body,
            command_index=command_index,
            command_list=command_list,
            manifest_payload=manifest_payload,
        )
        mapped_command_id = command.command_id
        raw_args = _extract_raw_arguments(body)
        normalized_args = coerce_tool_arguments(tool_spec, raw_args)
    except ToolArgumentCoercionError as exc:
        raise _http_error(
            status_code=400,
            detail={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            replaced_by=INVOKE_REPLACED_BY,
        ) from exc
    finally:
        _log_shim_hit(
            request=request,
            subject=auth_subject,
            command_id=mapped_command_id,
        )

    policy_mode = get_policy_mode(os.environ)
    policy_decision = evaluate_tool_policy(
        actor.model_dump(mode="json"),
        command.model_dump(mode="json"),
        normalized_args,
        os.environ,
    )
    policy_outcome = apply_policy_mode(
        policy_decision,
        mode=policy_mode,
        confirmation_granted=False,
    )
    policy = _policy_summary_from_decision(
        decision=policy_decision,
        mode=policy_outcome.mode,
    )

    if body.mode == "plan":
        planned = ToolCallResponse(
            status="planned",
            policy=policy,
            normalized_arguments=normalized_args,
            request_id=body.request_id,
            command_id=command.command_id,
        )
        if legacy:
            logger.warning(
                "legacy_tools_execute_response_mode path=%s subject=%s",
                request.url.path,
                auth_subject or "-",
            )
            return JSONResponse(
                content=_legacy_execute_payload(planned),
                headers=_deprecation_headers(INVOKE_REPLACED_BY),
            )
        return planned

    if policy.decision == "require_confirmation":
        policy_hash = compute_policy_hash(
            _policy_hash_payload(tool=tool_spec, policy=policy)
        )
        approval_token = issue_approval_token(
            actor_id=auth_subject,
            tool_id=tool_spec.tool_id,
            normalized_arguments=normalized_args,
            policy_hash=policy_hash,
            policy_mode=policy.mode,
        )
        blocked = ToolCallResponse(
            status="blocked",
            policy=policy,
            approval_required=True,
            approval_token=approval_token,
            normalized_arguments=normalized_args,
            request_id=body.request_id,
            command_id=command.command_id,
            error={"code": "approval_required"},
        )
        if legacy:
            logger.warning(
                "legacy_tools_execute_response_mode path=%s subject=%s",
                request.url.path,
                auth_subject or "-",
            )
            return JSONResponse(
                content=_legacy_execute_payload(blocked),
                headers=_deprecation_headers(INVOKE_REPLACED_BY),
            )
        return blocked

    if policy_outcome.blocked:
        denied = ToolCallResponse(
            status="denied",
            policy=policy,
            normalized_arguments=normalized_args,
            request_id=body.request_id,
            command_id=command.command_id,
            error={
                "code": "policy_denied",
                "reasons": list(policy.reasons),
            },
        )
        if legacy:
            logger.warning(
                "legacy_tools_execute_response_mode path=%s subject=%s",
                request.url.path,
                auth_subject or "-",
            )
            return JSONResponse(
                content=_legacy_execute_payload(denied),
                headers=_deprecation_headers(INVOKE_REPLACED_BY),
            )
        return denied

    invoke_payload = InvokeRequest(
        invoke_version="1.0",
        command_id=command.command_id,
        actor=actor,
        arguments=_invoke_arguments_from_normalized(normalized_args),
        idempotency_key=body.idempotency_key,
    )
    inbound_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "x-api-key", "x-user-id", "cookie"}
    }

    from guardian.routes import command_bus as command_bus_routes

    try:
        invoke_response = await execute_invoke(
            payload=invoke_payload,
            auth_subject=auth_subject,
            inbound_headers=inbound_headers,
            store=command_bus_routes._store,
            app=request.app,
            execution_lane="tools",
            allow_write_execution=False,
            confirmation_granted=False,
        )
    except HTTPException as exc:
        raise _raise_with_deprecation(exc, replaced_by=INVOKE_REPLACED_BY)

    final_response = _tool_call_from_invoke_response(
        invoke_response=invoke_response,
        policy=policy,
        normalized_arguments=normalized_args,
        request_id=body.request_id,
        command_id=command.command_id,
    )
    _store_job_snapshot(final_response)
    if legacy:
        logger.warning(
            "legacy_tools_execute_response_mode path=%s subject=%s",
            request.url.path,
            auth_subject or "-",
        )
        return JSONResponse(
            content=_legacy_execute_payload(final_response),
            headers=_deprecation_headers(INVOKE_REPLACED_BY),
        )
    return final_response


async def _approve_tools_call(
    *,
    body: ToolApproveRequest,
    request: Request,
    response: Response,
    legacy: bool,
) -> ToolCallResponse | JSONResponse:
    _apply_deprecation_headers(response, APPROVE_REPLACED_BY)
    auth_subject = _resolve_auth_subject(request)
    if not auth_subject:
        raise _http_error(
            status_code=401,
            detail={"error": "missing_identity_context"},
            replaced_by=APPROVE_REPLACED_BY,
        )

    try:
        decoded_claims = decode_approval_token(body.approval_token)
    except ApprovalTokenError as exc:
        raise _http_error(
            status_code=400,
            detail={"error": exc.code, "message": exc.message},
            replaced_by=APPROVE_REPLACED_BY,
        ) from exc

    actor = ActorSpec(kind="human", id=auth_subject)
    command_index, command_list, manifest_payload = _get_command_cache(
        request.app
    )
    _tools, tools_by_tool_id, _tools_by_command_id, _tools_by_openai_name = (
        _get_tool_maps(manifest_payload)
    )
    tool_spec = tools_by_tool_id.get(decoded_claims.tool_id)
    if tool_spec is None:
        raise _http_error(
            status_code=404,
            detail={
                "error": "tool_not_found",
                "tool_id": decoded_claims.tool_id,
            },
            replaced_by=APPROVE_REPLACED_BY,
        )
    command = command_index.get(tool_spec.command_id)
    if command is None:
        raise _http_error(
            status_code=404,
            detail={
                "error": "command_not_found",
                "command_id": tool_spec.command_id,
            },
            replaced_by=APPROVE_REPLACED_BY,
        )

    try:
        normalized_args = coerce_tool_arguments(
            tool_spec, decoded_claims.normalized_arguments
        )
    except ToolArgumentCoercionError as exc:
        raise _http_error(
            status_code=400,
            detail={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            replaced_by=APPROVE_REPLACED_BY,
        ) from exc

    policy_mode = get_policy_mode(os.environ)
    policy_decision = evaluate_tool_policy(
        actor.model_dump(mode="json"),
        command.model_dump(mode="json"),
        normalized_args,
        os.environ,
    )
    policy_outcome = apply_policy_mode(
        policy_decision,
        mode=policy_mode,
        confirmation_granted=True,
    )
    policy = _policy_summary_from_decision(
        decision=policy_decision,
        mode=policy_outcome.mode,
    )
    expected_policy_hash = compute_policy_hash(
        _policy_hash_payload(tool=tool_spec, policy=policy)
    )

    try:
        verified_claims = verify_approval_token(
            body.approval_token,
            actor_id=auth_subject,
            tool_id=tool_spec.tool_id,
            normalized_args=normalized_args,
            policy_hash=expected_policy_hash,
        )
    except ApprovalTokenError as exc:
        status_code = (
            403
            if exc.code
            in {
                "approval_token_actor_mismatch",
                "approval_token_tool_mismatch",
                "approval_token_args_mismatch",
                "approval_token_policy_mismatch",
            }
            else 400
        )
        raise _http_error(
            status_code=status_code,
            detail={"error": exc.code, "message": exc.message},
            replaced_by=APPROVE_REPLACED_BY,
        ) from exc

    _log_shim_hit(
        request=request,
        subject=auth_subject,
        command_id=command.command_id,
    )

    if policy_outcome.blocked:
        denied = ToolCallResponse(
            status="denied",
            policy=policy,
            normalized_arguments=normalized_args,
            request_id=body.request_id,
            command_id=command.command_id,
            error={"code": "policy_denied", "reasons": list(policy.reasons)},
        )
        if legacy:
            logger.warning(
                "legacy_tools_approve_response_mode path=%s subject=%s",
                request.url.path,
                auth_subject or "-",
            )
            return JSONResponse(
                content=_legacy_execute_payload(denied),
                headers=_deprecation_headers(APPROVE_REPLACED_BY),
            )
        return denied

    invoke_payload = InvokeRequest(
        invoke_version="1.0",
        command_id=command.command_id,
        actor=actor,
        arguments=_invoke_arguments_from_normalized(normalized_args),
        idempotency_key=approval_idempotency_key(body.approval_token),
    )
    inbound_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "x-api-key", "x-user-id", "cookie"}
    }

    from guardian.routes import command_bus as command_bus_routes

    try:
        invoke_response = await execute_invoke(
            payload=invoke_payload,
            auth_subject=auth_subject,
            inbound_headers=inbound_headers,
            store=command_bus_routes._store,
            app=request.app,
            execution_lane="tools",
            allow_write_execution=True,
            confirmation_granted=True,
        )
    except HTTPException as exc:
        raise _raise_with_deprecation(exc, replaced_by=APPROVE_REPLACED_BY)

    final_response = _tool_call_from_invoke_response(
        invoke_response=invoke_response,
        policy=policy,
        normalized_arguments=normalized_args,
        request_id=body.request_id,
        command_id=command.command_id,
    )
    # Expose deterministic behavior evidence for clients observing replay safety.
    final_response.result = (
        dict(final_response.result)
        if isinstance(final_response.result, dict)
        else final_response.result
    )
    if isinstance(final_response.result, dict):
        final_response.result.setdefault(
            "approval_idempotency_key",
            approval_idempotency_key(body.approval_token),
        )
        final_response.result.setdefault(
            "approval_token_digest", verified_claims.token_digest
        )

    _store_job_snapshot(final_response)
    if legacy:
        logger.warning(
            "legacy_tools_approve_response_mode path=%s subject=%s",
            request.url.path,
            auth_subject or "-",
        )
        return JSONResponse(
            content=_legacy_execute_payload(final_response),
            headers=_deprecation_headers(APPROVE_REPLACED_BY),
        )
    return final_response


@router.get("/manifest", response_model=ToolManifestEnvelope)
def tools_manifest(
    request: Request,
    response: Response,
    manifest_format: str = Query(
        default=_MANIFEST_FORMAT_ENVELOPE, alias="format"
    ),
    api_key: str = Depends(require_api_key),
) -> ToolManifestEnvelope | JSONResponse:
    _ = api_key
    _apply_deprecation_headers(response, MANIFEST_REPLACED_BY)
    subject = (
        request.headers.get("X-User-Id", "").strip() or None
    ) or _resolve_auth_subject(request)
    _log_shim_hit(request=request, subject=subject, command_id=None)
    resolved_format = _normalize_manifest_format(manifest_format)
    envelope = build_tool_manifest_envelope(request)
    if resolved_format == _MANIFEST_FORMAT_ENVELOPE:
        return envelope

    logger.warning(
        "legacy_tools_manifest_format_array path=%s subject=%s",
        request.url.path,
        subject or "-",
    )
    return JSONResponse(
        content=_tools_array_compat_payload(envelope.tools),
        headers=_deprecation_headers(MANIFEST_REPLACED_BY),
    )


@router.post("/execute", response_model=ToolCallResponse)
async def tools_execute_route(
    body: ToolCallRequest,
    request: Request,
    response: Response,
    legacy: bool = Query(default=False),
    api_key: str = Depends(require_api_key),
):
    _ = api_key
    return await _execute_tools_call(
        body=body, request=request, response=response, legacy=legacy
    )


@router.post("/approve", response_model=ToolCallResponse)
async def tools_approve_route(
    body: ToolApproveRequest,
    request: Request,
    response: Response,
    legacy: bool = Query(default=False),
    api_key: str = Depends(require_api_key),
):
    _ = api_key
    return await _approve_tools_call(
        body=body, request=request, response=response, legacy=legacy
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
def tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Return job status/result for a previous tools.execute call."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return {
        "job_id": job_id,
        "status": str(job.get("status") or "unknown"),
        "result": job.get("result") or {},
    }


@api_router.get("/manifest", response_model=ToolManifestEnvelope)
def api_tools_manifest(
    request: Request,
    response: Response,
    manifest_format: str = Query(
        default=_MANIFEST_FORMAT_ENVELOPE, alias="format"
    ),
    api_key: str = Depends(require_api_key),
) -> ToolManifestEnvelope | JSONResponse:
    """Compat alias for GET /tools/manifest."""
    return tools_manifest(
        request,
        response,
        manifest_format=manifest_format,
        api_key=api_key,
    )


@api_router.post("/execute", response_model=ToolCallResponse)
async def api_tools_execute(
    body: ToolCallRequest,
    request: Request,
    response: Response,
    legacy: bool = Query(default=False),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /tools/execute."""
    return await tools_execute_route(
        body,
        request=request,
        response=response,
        legacy=legacy,
        api_key=api_key,
    )


@api_router.post("/approve", response_model=ToolCallResponse)
async def api_tools_approve(
    body: ToolApproveRequest,
    request: Request,
    response: Response,
    legacy: bool = Query(default=False),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /tools/approve."""
    return await tools_approve_route(
        body,
        request=request,
        response=response,
        legacy=legacy,
        api_key=api_key,
    )


@api_router.get("/jobs/{job_id}", response_model=JobStatus)
def api_tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Compat alias for GET /tools/jobs/{job_id}."""
    return tools_job_status(job_id, api_key=api_key)
