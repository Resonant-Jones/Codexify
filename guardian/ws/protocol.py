"""WebSocket RPC protocol models and validation helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

MAX_PAYLOAD_BYTES = int(os.getenv("GUARDIAN_WS_MAX_PAYLOAD_BYTES", "65536"))


class ProtocolError(ValueError):
    """Raised when a client frame fails protocol validation."""


class PayloadTooLargeError(ProtocolError):
    """Raised when a raw websocket message exceeds configured size."""


class RPCRequest(BaseModel):
    """Client -> server request frame."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["request"] = "request"
    id: str = Field(min_length=1, max_length=128)
    method: str = Field(min_length=1, max_length=128)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def _validate_method(cls, value: str) -> str:
        method = value.strip()
        if not method:
            raise ValueError("method must be non-empty")
        return method


class RPCResponse(BaseModel):
    """Server -> client response frame."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["response"] = "response"
    id: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class RPCEvent(BaseModel):
    """Server -> client async event frame."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["event"] = "event"
    topic: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


def enforce_payload_size(
    raw: str | bytes, max_bytes: int = MAX_PAYLOAD_BYTES
) -> None:
    """Fail fast on oversized websocket payloads before JSON parsing."""

    size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
    if size > max_bytes:
        raise PayloadTooLargeError(
            f"payload exceeds {max_bytes} bytes (received {size})"
        )


def parse_request_frame(raw: str | bytes) -> RPCRequest:
    """Parse and validate a request frame from raw websocket payload."""

    enforce_payload_size(raw)
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid JSON frame") from exc
    if not isinstance(payload, dict):
        raise ProtocolError("frame must be a JSON object")
    if payload.get("type") != "request":
        raise ProtocolError("frame type must be 'request'")
    try:
        return RPCRequest.model_validate(payload)
    except ValidationError as exc:
        raise ProtocolError("request frame validation failed") from exc


def error_response(
    *,
    request_id: str | None,
    code: str,
    message: str,
) -> RPCResponse:
    """Build a structured protocol error response."""

    return RPCResponse(
        id=request_id,
        error={
            "code": code,
            "message": message,
        },
    )
