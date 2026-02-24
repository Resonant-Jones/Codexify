"""Signed approval token helpers for tools-lane confirmation flow."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

_TOKEN_VERSION = "1"
_TOKEN_AUDIENCE = "tools"
_DEFAULT_TTL_SECONDS = 15 * 60


class ApprovalTokenError(ValueError):
    """Raised when approval token issue/verify fails."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class VerifiedApprovalClaims(BaseModel):
    version: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    normalized_arguments: dict[str, Any]
    normalized_args_hash: str = Field(
        min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    policy_hash: str = Field(
        min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    policy_mode: str = Field(min_length=1)
    iat: int
    exp: int
    token_digest: str = Field(
        min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )

    model_config = ConfigDict(extra="forbid")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padded = raw + ("=" * (-len(raw) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise ApprovalTokenError(
            code="invalid_approval_token",
            message="approval token encoding is invalid",
        ) from exc


def _signing_key() -> bytes:
    for env_name in (
        "GUARDIAN_TOOLS_APPROVAL_SECRET",
        "GUARDIAN_SESSION_SECRET",
        "GUARDIAN_API_KEY",
    ):
        value = str(os.getenv(env_name) or "").strip()
        if value:
            return value.encode("utf-8")
    raise ApprovalTokenError(
        code="approval_secret_missing",
        message=(
            "approval token signing key is not configured "
            "(set GUARDIAN_TOOLS_APPROVAL_SECRET, GUARDIAN_SESSION_SECRET, or GUARDIAN_API_KEY)"
        ),
    )


def normalized_arguments_hash(normalized_arguments: dict[str, Any]) -> str:
    return hashlib.sha256(
        _canonical_json(normalized_arguments).encode("utf-8")
    ).hexdigest()


def compute_policy_hash(policy_payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _canonical_json(dict(policy_payload)).encode("utf-8")
    ).hexdigest()


def issue_approval_token(
    *,
    actor_id: str,
    tool_id: str,
    normalized_arguments: dict[str, Any],
    policy_hash: str,
    policy_mode: str,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> str:
    now = int(time.time())
    claims = {
        "version": _TOKEN_VERSION,
        "aud": _TOKEN_AUDIENCE,
        "actor_id": str(actor_id),
        "tool_id": str(tool_id),
        "normalized_arguments": dict(normalized_arguments or {}),
        "normalized_args_hash": normalized_arguments_hash(normalized_arguments),
        "policy_hash": str(policy_hash),
        "policy_mode": str(policy_mode),
        "iat": now,
        "exp": now + max(1, int(ttl_seconds)),
    }
    payload = _canonical_json(claims).encode("utf-8")
    signature = hmac.new(_signing_key(), payload, hashlib.sha256).digest()
    return f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"


def decode_approval_token(token: str) -> VerifiedApprovalClaims:
    raw = str(token or "").strip()
    if not raw or "." not in raw:
        raise ApprovalTokenError(
            code="invalid_approval_token",
            message="approval token is malformed",
        )

    payload_b64, signature_b64 = raw.split(".", 1)
    payload = _b64url_decode(payload_b64)
    provided_sig = _b64url_decode(signature_b64)
    expected_sig = hmac.new(_signing_key(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ApprovalTokenError(
            code="invalid_approval_token_signature",
            message="approval token signature is invalid",
        )

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise ApprovalTokenError(
            code="invalid_approval_token",
            message="approval token payload is invalid",
        ) from exc

    if not isinstance(decoded, dict):
        raise ApprovalTokenError(
            code="invalid_approval_token",
            message="approval token payload must be an object",
        )

    now = int(time.time())
    exp = int(decoded.get("exp") or 0)
    if exp < now:
        raise ApprovalTokenError(
            code="approval_token_expired",
            message="approval token has expired",
        )
    if str(decoded.get("aud") or "") != _TOKEN_AUDIENCE:
        raise ApprovalTokenError(
            code="approval_token_invalid_audience",
            message="approval token audience is invalid",
        )
    if str(decoded.get("version") or "") != _TOKEN_VERSION:
        raise ApprovalTokenError(
            code="approval_token_invalid_version",
            message="approval token version is not supported",
        )

    return VerifiedApprovalClaims(
        version=str(decoded["version"]),
        aud=str(decoded["aud"]),
        actor_id=str(decoded.get("actor_id") or ""),
        tool_id=str(decoded.get("tool_id") or ""),
        normalized_arguments=dict(decoded.get("normalized_arguments") or {}),
        normalized_args_hash=str(decoded.get("normalized_args_hash") or ""),
        policy_hash=str(decoded.get("policy_hash") or ""),
        policy_mode=str(decoded.get("policy_mode") or ""),
        iat=int(decoded.get("iat") or 0),
        exp=exp,
        token_digest=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )


def verify_approval_token(
    token: str,
    *,
    actor_id: str,
    tool_id: str,
    normalized_args: dict[str, Any],
    policy_hash: str,
) -> VerifiedApprovalClaims:
    claims = decode_approval_token(token)

    if claims.actor_id != actor_id:
        raise ApprovalTokenError(
            code="approval_token_actor_mismatch",
            message="approval token actor does not match caller",
        )
    if claims.tool_id != tool_id:
        raise ApprovalTokenError(
            code="approval_token_tool_mismatch",
            message="approval token tool does not match request",
        )

    expected_args_hash = normalized_arguments_hash(normalized_args)
    if claims.normalized_args_hash != expected_args_hash:
        raise ApprovalTokenError(
            code="approval_token_args_mismatch",
            message="approval token arguments do not match request",
        )
    if claims.policy_hash != policy_hash:
        raise ApprovalTokenError(
            code="approval_token_policy_mismatch",
            message="approval token policy binding does not match",
        )
    return claims


def approval_idempotency_key(token: str) -> str:
    digest = hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()
    return f"approval_{digest[:56]}"
