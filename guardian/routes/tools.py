"""
Tools Routes
~~~~~~~~~~~~

Minimal tools execution dispatcher and job status endpoints.
"""

import logging
import time
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError

from guardian.cognition.system_profiles.resolver import switch_thread_profile
from guardian.command_bus.contracts import (
    ActorSpec,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.manifest import build_command_index
from guardian.core.dependencies import get_request_user_id

logger = logging.getLogger(__name__)

# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, Dict[str, Any]] = {}

DEPRECATION_PHASE = "1.5"
MANIFEST_REPLACED_BY = "/api/guardian/commands/manifest"
INVOKE_REPLACED_BY = "/api/guardian/commands/invoke"
_MANIFEST_CACHE_TTL_SECONDS = 5.0
_manifest_cache_app_id: int | None = None
_manifest_cache_expires_at = 0.0
_manifest_cache_index: dict[str, Any] = {}
_manifest_cache_commands: list[Any] = []


class ToolRequest(BaseModel):
    name: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    actor: dict[str, Any] | None = None
    command_id: str | None = None
    operation_id: str | None = None
    method: str | None = None
    path: str | None = None
    path_template: str | None = None
    arguments: dict[str, Any] | None = None
    idempotency_key: str | None = None


class ToolResponse(BaseModel):
    job_id: str
    status: str = "done"
    result: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    events_url: str | None = None
    command_id: str | None = None
    error: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)


# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import (
        chatlog_db,
        event_bus,
        require_api_key,
    )
except ImportError:
    # Fallback for standalone usage
    def require_api_key(api_key: str = None):
        return api_key

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
        derived = get_request_user_id(None)
    except Exception:
        return None
    derived_str = str(derived or "").strip()
    return derived_str or None


def _resolve_actor(
    body: ToolRequest, request: Request | None
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


def _get_command_cache(app: Any) -> tuple[dict[str, Any], list[Any]]:
    global _manifest_cache_app_id
    global _manifest_cache_expires_at
    global _manifest_cache_index
    global _manifest_cache_commands
    now = time.monotonic()
    app_id = id(app)
    cache_stale = (
        _manifest_cache_app_id != app_id
        or now >= _manifest_cache_expires_at
        or not _manifest_cache_index
    )
    if cache_stale:
        index, manifest = build_command_index(app)
        _manifest_cache_app_id = app_id
        _manifest_cache_expires_at = now + _MANIFEST_CACHE_TTL_SECONDS
        _manifest_cache_index = index
        _manifest_cache_commands = list(manifest.commands)
    return _manifest_cache_index, _manifest_cache_commands


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


def _map_legacy_request_to_command_id(
    body: ToolRequest, index: dict[str, Any], commands: list[Any]
) -> str:
    command_id = (body.command_id or "").strip()
    if command_id:
        command = index.get(command_id)
        if command is not None:
            return command.command_id
        raise _http_error(
            status_code=400,
            detail={"error": "unknown_tool_command", "command_id": command_id},
            replaced_by=INVOKE_REPLACED_BY,
        )

    operation_id = (body.operation_id or "").strip()
    if operation_id:
        op_command_id = f"op::{operation_id}"
        command = index.get(op_command_id)
        if command is not None:
            return command.command_id
        raise _http_error(
            status_code=400,
            detail={
                "error": "unknown_tool_command",
                "operation_id": operation_id,
            },
            replaced_by=INVOKE_REPLACED_BY,
        )

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

    raise _http_error(
        status_code=400,
        detail={
            "error": "unknown_tool_command",
            "name": body.name,
            "method": body.method,
            "path": body.path or body.path_template,
        },
        replaced_by=INVOKE_REPLACED_BY,
    )


def _invoke_arguments_from_legacy(
    body: ToolRequest, *, command: Any
) -> InvokeArguments:
    arguments = body.arguments if isinstance(body.arguments, dict) else {}
    if arguments:
        return InvokeArguments(
            path_params=dict(arguments.get("path_params") or {}),
            query=dict(arguments.get("query") or {}),
            headers=dict(arguments.get("headers") or {}),
            body=arguments.get("body"),
        )

    args = dict(body.args or {})
    path_params = (
        dict(args.get("path_params"))
        if isinstance(args.get("path_params"), dict)
        else {}
    )
    query = (
        dict(args.get("query")) if isinstance(args.get("query"), dict) else {}
    )
    headers = (
        dict(args.get("headers"))
        if isinstance(args.get("headers"), dict)
        else {}
    )
    payload_body = args.get("body") if "body" in args else None

    has_transport_shapes = any(
        key in args for key in {"path_params", "query", "headers", "body"}
    )
    if not has_transport_shapes and args:
        if command.method in {"GET", "HEAD"}:
            query = args
        else:
            payload_body = args

    return InvokeArguments(
        path_params=path_params,
        query=query,
        headers=headers,
        body=payload_body,
    )


def _legacy_manifest_payload(request: Request) -> list[dict[str, Any]]:
    _index, commands = _get_command_cache(request.app)
    payload: list[dict[str, Any]] = []
    for command in commands:
        payload.append(
            {
                "name": command.command_id,
                "description": f"{command.method} {command.path_template}",
                "command_id": command.command_id,
                "aliases": list(command.aliases),
                "method": command.method,
                "path_template": command.path_template,
                "operation_id": command.operation_id,
                "risk": command.risk,
                "effect": command.effect,
                "idempotency": command.idempotency,
                "approval_mode": command.approval_mode,
                "args_schema": command.input_schema,
            }
        )
    return payload


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
    Minimal tools dispatcher. For now, just echoes args and marks job done.
    Replace with real tool routing/execution as needed.

    Args:
        body: Tool execution request with name and arguments

    Returns:
        Job ID for tracking execution
    """
    jid = str(uuid4())
    result = _run_legacy_tool_locally(body)
    JOBS[jid] = {"status": "done", "result": result}
    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
    return {"job_id": jid, "status": "done", "result": result}


@router.get("/manifest")
def tools_manifest(
    request: Request,
    response: Response,
    api_key: str = Depends(require_api_key),
) -> list[dict[str, Any]]:
    _ = api_key
    _apply_deprecation_headers(response, MANIFEST_REPLACED_BY)
    subject = (
        request.headers.get("X-User-Id", "").strip() or None
    ) or _resolve_auth_subject(request)
    _log_shim_hit(request=request, subject=subject, command_id=None)
    return _legacy_manifest_payload(request)


@router.post("/execute", response_model=ToolResponse)
async def tools_execute_route(
    body: ToolRequest,
    request: Request,
    response: Response,
    api_key: str = Depends(require_api_key),
):
    _ = api_key
    _apply_deprecation_headers(response, INVOKE_REPLACED_BY)

    actor, auth_subject = _resolve_actor(body, request)
    command_index, command_list = _get_command_cache(request.app)
    mapped_command_id: str | None = None
    try:
        mapped_command_id = _map_legacy_request_to_command_id(
            body, command_index, command_list
        )
        command = command_index[mapped_command_id]
    finally:
        _log_shim_hit(
            request=request,
            subject=auth_subject,
            command_id=mapped_command_id,
        )

    invoke_payload = InvokeRequest(
        invoke_version="1.0",
        command_id=command.command_id,
        actor=actor,
        arguments=_invoke_arguments_from_legacy(body, command=command),
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
        )
    except HTTPException as exc:
        raise _raise_with_deprecation(exc, replaced_by=INVOKE_REPLACED_BY)

    run_id = str(invoke_response.get("run_id") or "")
    status = str(invoke_response.get("status") or "unknown")
    result_payload = invoke_response.get("inline_result")
    if not isinstance(result_payload, dict):
        result_payload = {}
    if invoke_response.get("error"):
        result_payload = dict(result_payload)
        result_payload["error"] = invoke_response["error"]

    JOBS[run_id] = {"status": status, "result": result_payload}
    return {
        "job_id": run_id,
        "status": status,
        "result": result_payload,
        "run_id": run_id,
        "events_url": invoke_response.get("events_url"),
        "command_id": command.command_id,
        "error": invoke_response.get("error"),
    }


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


@api_router.get("/manifest")
def api_tools_manifest(
    request: Request,
    response: Response,
    api_key: str = Depends(require_api_key),
) -> list[dict[str, Any]]:
    """Compat alias for GET /tools/manifest."""
    return tools_manifest(request, response, api_key=api_key)


@api_router.post("/execute", response_model=ToolResponse)
async def api_tools_execute(
    body: ToolRequest,
    request: Request,
    response: Response,
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /tools/execute."""
    return await tools_execute_route(
        body,
        request=request,
        response=response,
        api_key=api_key,
    )


@api_router.get("/jobs/{job_id}", response_model=JobStatus)
def api_tools_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """Compat alias for GET /tools/jobs/{job_id}."""
    return tools_job_status(job_id, api_key=api_key)
