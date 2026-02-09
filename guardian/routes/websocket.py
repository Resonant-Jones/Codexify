"""Canonical websocket RPC route with audit logging."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from guardian.core.config import settings
from guardian.db.models import WSAuditLog
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

_db: Any | None = None


def configure_db(db: Any) -> None:
    """Configure the database service used for websocket audit rows."""

    global _db
    _db = db


class _NoopSession:
    def add(self, _: Any) -> None:
        return

    def commit(self) -> None:
        return

    def rollback(self) -> None:
        return

    def close(self) -> None:
        return


class _NoopDB:
    def SessionLocal(self) -> _NoopSession:
        return _NoopSession()


def _get_db() -> Any:
    return _db if _db is not None else _NoopDB()


def _identity_from_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    token = str(api_key).strip()
    if not token:
        return None
    if len(token) <= 8:
        return f"api_key:{token}"
    return f"api_key:{token[:4]}...{token[-4:]}"


def _stable_params_hash(params: dict[str, Any] | None) -> str:
    payload = json.dumps(
        params or {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _raw_payload_hash(raw: str | bytes) -> str:
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(data).hexdigest()


def _duration_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _write_ws_audit(
    *,
    connection_id: str,
    identity: str | None,
    method: str,
    params_hash: str,
    status: str,
    duration_ms: int,
) -> None:
    db = _get_db()
    session_factory = getattr(db, "SessionLocal", None)
    if not callable(session_factory):
        return
    session = session_factory()
    try:
        session.add(
            WSAuditLog(
                connection_id=connection_id,
                identity=identity,
                method=method,
                params_hash=params_hash,
                status=status,
                duration_ms=duration_ms,
            )
        )
        session.commit()
    except Exception as exc:
        try:
            session.rollback()
        except Exception:
            pass
        logger.warning("[ws.audit] failed to persist audit row: %s", exc)
    finally:
        try:
            session.close()
        except Exception:
            pass


@router.websocket("/rpc")
async def websocket_rpc(websocket: WebSocket) -> None:
    """Authenticate websocket client and process RPC request frames."""

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
    connection_id = f"ws-{id(websocket)}"
    identity = _identity_from_api_key(api_key)
    rate_limit_key = f"api_key:{api_key}" if api_key else connection_id
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

            started = time.perf_counter()
            method_name = "<invalid>"
            params_hash = _raw_payload_hash(raw)

            try:
                request = parse_request_frame(raw)
                method_name = request.method
                params_hash = _stable_params_hash(request.params)
            except PayloadTooLargeError:
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
                )
                await websocket.close(
                    code=PAYLOAD_TOO_LARGE_CLOSE_CODE,
                    reason="payload_too_large",
                )
                return
            except ProtocolError:
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
                )
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
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
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
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
                )
                continue
            except RPCPermissionDeniedError as exc:
                response = error_response(
                    request_id=request.id,
                    code="permission_denied",
                    message=str(exc),
                )
                await websocket.send_json(response.model_dump())
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
                )
                continue
            except Exception as exc:
                logger.warning("[ws.rpc] method %s failed: %s", request.method, exc)
                response = error_response(
                    request_id=request.id,
                    code="method_error",
                    message=str(exc),
                )
                await websocket.send_json(response.model_dump())
                _write_ws_audit(
                    connection_id=connection_id,
                    identity=identity,
                    method=method_name,
                    params_hash=params_hash,
                    status="error",
                    duration_ms=_duration_ms(started),
                )
                continue

            await websocket.send_json(
                {
                    "type": "response",
                    "id": request.id,
                    "result": result,
                    "error": None,
                }
            )
            _write_ws_audit(
                connection_id=connection_id,
                identity=identity,
                method=method_name,
                params_hash=params_hash,
                status="ok",
                duration_ms=_duration_ms(started),
            )
    finally:
        await manager.unregister(websocket)
