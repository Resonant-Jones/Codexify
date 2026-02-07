"""Minimal websocket RPC route with auth-first dispatch."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from guardian.ws.auth import (
    VALIDATION_FAILURE_CLOSE_CODE,
    WSAuthError,
    authenticate_websocket,
)
from guardian.ws.protocol import (
    PayloadTooLargeError,
    ProtocolError,
    RPCResponse,
    parse_request_frame,
)

logger = logging.getLogger(__name__)

PAYLOAD_TOO_LARGE_CLOSE_CODE = 4409

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])


@router.websocket("/rpc")
async def websocket_rpc(websocket: WebSocket) -> None:
    """Authenticate websocket client and process minimal RPC request frames."""

    await websocket.accept()

    try:
        await authenticate_websocket(websocket)
    except WSAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

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

        if request.method == "ping":
            response = RPCResponse(id=request.id, result={"ok": True})
            await websocket.send_json(response.model_dump())
            continue

        response = RPCResponse(
            id=request.id,
            error={"code": "unknown_method", "message": "Unknown method"},
        )
        await websocket.send_json(response.model_dump())
