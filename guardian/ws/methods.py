"""RPC method registry and initial websocket RPC methods."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from fastapi import HTTPException

from guardian.ws.manager import WSConnectionManager

RPCHandler = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass(frozen=True)
class RPCMethodSpec:
    """RPC method metadata and handler."""

    name: str
    handler: RPCHandler
    requires_auth: bool = True
    admin_only: bool = False


class UnknownRPCMethodError(ValueError):
    """Raised when client calls an unknown RPC method."""


class RPCPermissionDeniedError(PermissionError):
    """Raised when caller lacks permission for a method."""


METHOD_REGISTRY: dict[str, RPCMethodSpec] = {}


def rpc_method(
    name: str,
    *,
    requires_auth: bool = True,
    admin_only: bool = False,
) -> Callable[[RPCHandler], RPCHandler]:
    """Register an RPC method handler in the global registry."""

    def _decorator(func: RPCHandler) -> RPCHandler:
        METHOD_REGISTRY[name] = RPCMethodSpec(
            name=name,
            handler=func,
            requires_auth=requires_auth,
            admin_only=admin_only,
        )
        return func

    return _decorator


def _coerce_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_admin(api_key: str | None) -> bool:
    if not api_key:
        return False
    expected = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
    if not expected:
        return False
    return api_key == expected


def _require_manager(ctx: dict[str, Any]) -> WSConnectionManager:
    manager = ctx.get("manager")
    if not isinstance(manager, WSConnectionManager):
        raise ValueError("manager unavailable")
    return manager


def _require_connection(ctx: dict[str, Any]) -> Any:
    connection = ctx.get("connection")
    if connection is None:
        raise ValueError("connection unavailable")
    return connection


@rpc_method("ping", requires_auth=True, admin_only=False)
async def rpc_ping(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    _ = params
    _ = ctx
    return {"ok": True}


@rpc_method("subscribe", requires_auth=True, admin_only=False)
async def rpc_subscribe(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    topic = str(params.get("topic") or "").strip()
    if not topic:
        raise ValueError("topic is required")
    manager = _require_manager(ctx)
    connection = _require_connection(ctx)
    await manager.subscribe(connection, topic)
    return {"subscribed": topic}


@rpc_method("unsubscribe", requires_auth=True, admin_only=False)
async def rpc_unsubscribe(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    topic = str(params.get("topic") or "").strip()
    if not topic:
        raise ValueError("topic is required")
    manager = _require_manager(ctx)
    connection = _require_connection(ctx)
    await manager.unsubscribe(connection, topic)
    return {"unsubscribed": topic}


@rpc_method("health.status", requires_auth=True, admin_only=False)
async def rpc_health_status(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    _ = params
    _ = ctx
    return {"status": "ok"}


@rpc_method("thread.list", requires_auth=True, admin_only=True)
def rpc_thread_list(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    _ = params
    _ = ctx
    from guardian.routes import chat as chat_routes

    response = chat_routes.chat_list_threads(api_key=ctx.get("api_key"))
    if isinstance(response, dict):
        return response
    return {"ok": True, "threads": response}


@rpc_method("chat.send", requires_auth=True, admin_only=False)
async def rpc_chat_send(
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    from guardian.routes import chat as chat_routes

    thread_id = int(params.get("thread_id") or 0)
    if thread_id <= 0:
        raise ValueError("thread_id must be a positive integer")
    request = chat_routes.ChatCompletionRequest(
        model=params.get("model"),
        max_context=params.get("max_context"),
        provider=params.get("provider"),
        system_override=params.get("system_override"),
        depth_mode=params.get("depth_mode"),
    )
    try:
        response = await chat_routes.chat_complete(
            thread_id=thread_id,
            body=request,
            api_key=ctx.get("api_key"),
        )
    except HTTPException as exc:
        raise ValueError(str(exc.detail)) from exc
    if isinstance(response, dict):
        return response
    return {"ok": True, "result": response}


async def dispatch_rpc_method(
    method: str,
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> Any:
    """Resolve and execute an RPC method with policy checks."""

    spec = METHOD_REGISTRY.get(method)
    if spec is None:
        raise UnknownRPCMethodError(method)

    api_key = ctx.get("api_key")
    if spec.requires_auth and not api_key:
        raise RPCPermissionDeniedError("authentication_required")
    if spec.admin_only and not _is_admin(api_key):
        raise RPCPermissionDeniedError("admin_required")

    result = spec.handler(params or {}, ctx)
    if inspect.isawaitable(result):
        return await result
    return result
