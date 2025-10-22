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
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import Cookie, Depends, Header, HTTPException, Request, status


@dataclass(frozen=True)
class AuthenticatedUser:
    """Minimal auth context returned by dependencies."""

    id: str
    kind: str


def _session_secret() -> bytes:
    """
    Resolve the signing secret for session tokens.

    Preference order:
    - GUARDIAN_SESSION_SECRET
    - GUARDIAN_API_KEY
    - static "dev-secret" fallback (local dev only)
    """
    secret = (
        os.getenv("GUARDIAN_SESSION_SECRET")
        or os.getenv("GUARDIAN_API_KEY")
        or "dev-secret"
    )
    return secret.encode("utf-8")


def issue_session_token(
    subject: str = "web", ttl_seconds: int = 24 * 3600
) -> Tuple[str, int]:
    """
    Issue an HMAC-signed opaque session token.

    Returns `(token, expires_at_epoch_seconds)`.
    """
    now = int(time.time())
    exp = now + int(ttl_seconds)
    nonce = secrets.token_urlsafe(10)
    payload = f"{subject}.{exp}.{nonce}".encode("utf-8")
    sig = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
    packed = base64.urlsafe_b64encode(payload + b"." + sig).decode("ascii")
    return packed, exp


def verify_session_token(token: str) -> Tuple[bool, Optional[str]]:
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
    x_api_key: Optional[str],
    authorization: Optional[str],
    gc_session: Optional[str],
) -> Optional[str]:
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
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    gc_session: Optional[str] = Cookie(default=None, alias="gc_session"),
    x_guardian_key: Optional[str] = Header(default=None, alias="X-Guardian-Key"),
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
