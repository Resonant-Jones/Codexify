"""Minimal websocket RPC route with auth-first dispatch."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from guardian.core.config import settings
from guardian.ws.auth import (
    VALIDATION_FAILURE_CLOSE_CODE,
    WSAuthError,
    authenticate_websocket,
)
from guardian.ws.manager import WSConnectionManager
from guardian.ws.methods import (
    RPCPermissionDeniedError,
    UnknownRPCMethodError,
    dispatch_rpc_method,
)
from guardian.ws.protocol import (
    PayloadTooLargeError,
    ProtocolError,
    error_response,
    parse_request_frame,
)
from guardian.ws.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

PAYLOAD_TOO_LARGE_CLOSE_CODE = 4409
IDLE_TIMEOUT_CLOSE_CODE = 4408
MAX_CONNECTIONS_CLOSE_CODE = 4429

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])
manager = WSConnectionManager()
rate_limiter = TokenBucketRateLimiter(
    capacity=settings.WS_RPC_RATE_LIMIT_CAPACITY,
    refill_per_second=settings.WS_RPC_RATE_LIMIT_REFILL_PER_SECOND,
    namespace=settings.WS_RPC_RATE_LIMIT_NAMESPACE,
)


@router.websocket("/rpc")
async def websocket_rpc(websocket: WebSocket) -> None:
    """Authenticate websocket client and process minimal RPC request frames."""

    await websocket.accept()

    try:
        api_key = await authenticate_websocket(websocket)
    except WSAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    if settings.WS_RPC_MAX_CONNECTIONS > 0:
        if manager.connection_count() >= settings.WS_RPC_MAX_CONNECTIONS:
            await websocket.close(
                code=MAX_CONNECTIONS_CLOSE_CODE,
                reason="max_connections_exceeded",
            )
            return

    await manager.register(websocket)
    rate_limit_key = f"api_key:{api_key}" if api_key else f"connection:{id(websocket)}"
    idle_timeout_seconds = max(0.0, float(settings.WS_RPC_IDLE_TIMEOUT_SECONDS))
    ctx = {
        "connection": websocket,
        "manager": manager,
        "api_key": api_key,
    }
    try:
        while True:
            try:
                if idle_timeout_seconds > 0:
                    raw = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=idle_timeout_seconds,
                    )
                else:
                    raw = await websocket.receive_text()
            except asyncio.TimeoutError:
                await websocket.close(
                    code=IDLE_TIMEOUT_CLOSE_CODE,
                    reason="idle_timeout",
                )
                return
            except WebSocketDisconnect:
                return

            try:
                request = parse_request_frame(raw)
            except PayloadTooLargeError:
                await websocket.close(
                    code=PAYLOAD_TOO_LARGE_CLOSE_CODE,
                    reason="payload_too_large",
                )
                return
            except ProtocolError:
                await websocket.close(
                    code=VALIDATION_FAILURE_CLOSE_CODE,
                    reason="invalid_request_frame",
                )
                return

            decision = await rate_limiter.allow(rate_limit_key)
            if not decision.allowed:
                error = {
                    "code": "rate_limited",
                    "message": "rate limit exceeded",
                }
                if decision.retry_after_seconds is not None:
                    error["retry_after_seconds"] = round(
                        decision.retry_after_seconds, 4
                    )
                await websocket.send_json(
                    {
                        "type": "response",
                        "id": request.id,
                        "result": None,
                        "error": error,
                    }
                )
                continue

            try:
                result = await dispatch_rpc_method(
                    request.method,
                    request.params,
                    ctx,
                )
            except UnknownRPCMethodError:
                response = error_response(
                    request_id=request.id,
                    code="unknown_method",
                    message=f"Unknown method: {request.method}",
                )
                await websocket.send_json(response.model_dump())
                continue
            except RPCPermissionDeniedError as exc:
                response = error_response(
                    request_id=request.id,
                    code="permission_denied",
                    message=str(exc),
                )
                await websocket.send_json(response.model_dump())
                continue
            except Exception as exc:
                logger.warning("[ws.rpc] method %s failed: %s", request.method, exc)
                response = error_response(
                    request_id=request.id,
                    code="method_error",
                    message=str(exc),
                )
                await websocket.send_json(response.model_dump())
                continue

            await websocket.send_json(
                {
                    "type": "response",
                    "id": request.id,
                    "result": result,
                    "error": None,
                }
            )
    finally:
        await manager.unregister(websocket)
