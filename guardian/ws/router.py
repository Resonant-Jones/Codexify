"""Minimal websocket RPC route with auth-first dispatch."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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

logger = logging.getLogger(__name__)

PAYLOAD_TOO_LARGE_CLOSE_CODE = 4409

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])
manager = WSConnectionManager()


@router.websocket("/rpc")
async def websocket_rpc(websocket: WebSocket) -> None:
    """Authenticate websocket client and process minimal RPC request frames."""

    await websocket.accept()

    try:
        api_key = await authenticate_websocket(websocket)
    except WSAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await manager.register(websocket)
    ctx = {
        "connection": websocket,
        "manager": manager,
        "api_key": api_key,
    }
    try:
        while True:
            try:
                raw = await websocket.receive_text()
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
