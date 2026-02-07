"""WebSocket authentication helpers."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from fastapi import HTTPException, WebSocket

from guardian.core.dependencies import verify_api_key
from guardian.ws.protocol import enforce_payload_size

AUTH_FAILURE_CLOSE_CODE = 4401
VALIDATION_FAILURE_CLOSE_CODE = 4400


@dataclass
class WSAuthError(Exception):
    """Raised when websocket authentication fails."""

    code: int
    reason: str


def _validate_api_key(token: str) -> str:
    try:
        return verify_api_key(x_api_key=token, authorization=None)
    except HTTPException as exc:
        raise WSAuthError(
            code=AUTH_FAILURE_CLOSE_CODE,
            reason="unauthorized",
        ) from exc


async def authenticate_websocket(
    websocket: WebSocket,
    *,
    timeout_seconds: float = 5.0,
) -> str:
    """
    Authenticate websocket connection via query param or initial auth frame.

    Query param precedence:
    - api_key
    - token

    Initial auth frame format:
    {"type":"auth","api_key":"..."} or {"type":"auth","token":"..."}
    """

    query_token = (
        websocket.query_params.get("api_key")
        or websocket.query_params.get("token")
        or ""
    ).strip()
    if query_token:
        return _validate_api_key(query_token)

    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise WSAuthError(
            code=AUTH_FAILURE_CLOSE_CODE,
            reason="auth_timeout",
        ) from exc

    try:
        enforce_payload_size(raw)
        payload = json.loads(raw)
    except Exception as exc:
        raise WSAuthError(
            code=VALIDATION_FAILURE_CLOSE_CODE,
            reason="invalid_auth_frame",
        ) from exc

    if not isinstance(payload, dict) or payload.get("type") != "auth":
        raise WSAuthError(
            code=AUTH_FAILURE_CLOSE_CODE,
            reason="auth_required",
        )

    frame_token = str(payload.get("api_key") or payload.get("token") or "").strip()
    if not frame_token:
        raise WSAuthError(
            code=AUTH_FAILURE_CLOSE_CODE,
            reason="missing_api_key",
        )

    return _validate_api_key(frame_token)
