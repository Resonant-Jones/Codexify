"""
Shared authentication helpers for Guardian services.

This module centralizes simple API-key and session-token based
authentication logic so routers can depend on a consistent
`require_user` dependency without importing the heavyweight
`guardian.guardian_api` module (avoiding circular imports).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import Cookie, Depends, Header, HTTPException, Request, status


@dataclass(frozen=True)
class AuthenticatedUser:
    """Minimal auth context returned by dependencies."""

    id: str
    kind: str


def _session_secret() -> bytes:
    """
    Resolve the signing secret for session tokens.

    In production (DEV_MODE != true), this REQUIRES explicit configuration.
    In dev mode, falls back to "dev-secret" for local development convenience.

    Set DEV_MODE=true in your local .env for development only.
    """
    # Check if we're in dev mode
    dev_mode = os.getenv("DEV_MODE", "").lower() in ("1", "true", "yes")

    secret = os.getenv("GUARDIAN_SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")

    # Only allow fallback in dev mode
    if dev_mode:
        return b"dev-secret"

    # Production: fail fast with clear message
    raise ValueError(
        "GUARDIAN_SESSION_SECRET must be set in production. "
        "Set DEV_MODE=true for local development only."
    )


def issue_session_token(
    subject: str = "web", ttl_seconds: int = 24 * 3600
) -> tuple[str, int]:
    """
    Issue an HMAC-signed opaque session token.

    Returns `(token, expires_at_epoch_seconds)`.
    """
    now = int(time.time())
    exp = now + int(ttl_seconds)
    nonce = secrets.token_urlsafe(10)
    payload = f"{subject}.{exp}.{nonce}".encode()
    sig = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
    packed = base64.urlsafe_b64encode(payload + b"." + sig).decode("ascii")
    return packed, exp


def verify_session_token(token: str) -> tuple[bool, str | None]:
    """
    Validate an opaque session token issued by `issue_session_token`.

    Returns `(valid, subject)`.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        parts = raw.split(b".")
        if len(parts) != 4:
            return False, None
        subject = parts[0].decode("utf-8", "ignore")
        exp = int(parts[1].decode("utf-8", "ignore"))
        payload = b".".join(parts[:3])
        sig = parts[3]
        digest = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, digest) or exp < int(time.time()):
            return False, None
        return True, subject
    except Exception:
        return False, None


def extract_auth_identity(
    x_api_key: str | None,
    authorization: str | None,
    gc_session: str | None,
) -> str | None:
    """
    Determine the identity of an authenticated caller.

    Accepts API keys as well as session tokens (Authorization header or cookie).
    """
    expected = os.getenv("GUARDIAN_API_KEY") or ""
    if x_api_key and secrets.compare_digest(x_api_key, expected):
        return "api-key"
    if authorization and authorization.startswith("Bearer "):
        ok, sub = verify_session_token(authorization[7:].strip())
        if ok:
            return f"session:{sub or 'web'}"
    if gc_session:
        ok, sub = verify_session_token(gc_session)
        if ok:
            return f"session-cookie:{sub or 'web'}"
    return None


def require_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    gc_session: str | None = Cookie(default=None, alias="gc_session"),
    x_guardian_key: str | None = Header(default=None, alias="X-Guardian-Key"),
) -> str:
    """
    FastAPI dependency enforcing that a request is authenticated.

    Returns the identity descriptor string on success, raises 401 on failure.
    """
    candidate_key = x_api_key or x_guardian_key
    ident = extract_auth_identity(candidate_key, authorization, gc_session)
    if ident:
        return ident
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
    )


def require_user(
    request: Request,
    identity: str = Header(default=None, alias="X-Guardian-Identity"),
    auth_identity: str = Depends(require_auth),  # type: ignore[name-defined]
) -> AuthenticatedUser:
    """
    Dependency returning an `AuthenticatedUser`.

    - Uses `require_auth` to ensure the caller is authenticated.
    - Optionally allows a user identifier to be supplied via the
      `X-Guardian-Identity` header; otherwise falls back to the auth identity.
    """
    user_id = identity or auth_identity
    return AuthenticatedUser(id=user_id, kind=auth_identity)


def _canonical_trust_policy_json(
    policy_json: str,
) -> tuple[str, dict[str, Any]]:
    payload = json.loads(policy_json)
    if not isinstance(payload, dict):
        raise ValueError("Trust policy must be a JSON object")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return canonical, payload


def _policy_hmac_key(signing_key: str | None = None) -> bytes | None:
    resolved = (
        signing_key
        or os.getenv("GUARDIAN_FEDERATION_POLICY_SIGNING_KEY")
        or os.getenv("GUARDIAN_SESSION_SECRET")
        or os.getenv("GUARDIAN_API_KEY")
    )
    if not resolved:
        return None
    return resolved.encode("utf-8")


def _decode_sig(sig: str) -> bytes | None:
    raw = (sig or "").strip()
    if not raw:
        return None
    padded = raw + ("=" * (-len(raw) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return None


def sign_federation_trust_policy(policy_json: str, signing_key: str) -> str:
    """
    Produce a base64url HMAC-SHA256 signature for a federation trust policy.
    """
    canonical, _payload = _canonical_trust_policy_json(policy_json)
    digest = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_federation_trust_policy(
    policy_json: str | None,
    signature: str | None,
    *,
    signing_key: str | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """
    Validate a signed federation trust policy.

    Returns:
        (is_valid, parsed_policy_or_none)
    """
    if not policy_json or not signature:
        return False, None

    key = _policy_hmac_key(signing_key)
    if key is None:
        return False, None

    try:
        canonical, payload = _canonical_trust_policy_json(policy_json)
    except Exception:
        return False, None

    expected = hmac.new(
        key,
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    provided = _decode_sig(signature)
    if provided is None:
        return False, None
    if not hmac.compare_digest(expected, provided):
        return False, None

    return True, payload
