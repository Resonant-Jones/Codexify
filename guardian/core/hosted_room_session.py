"""Hosted Room guest-session contract.

Issues, decodes, and validates purpose-scoped HMAC-signed guest session
tokens.  Each token binds exactly one room, one participant, and one
originating invitation.  Every authorized request revalidates persistence
truth — no server-side session table is required.

Token domain separation is enforced via a dedicated ``subject`` claim
(``hosted_room_guest_session``).  Tokens minted for any other purpose
(including normal account sessions) are rejected even if their HMAC is
valid.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request, Response

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

_SESSION_SUBJECT = "hosted_room_guest_session"
_SESSION_COOKIE_NAME = "codexify_hosted_room_session"
_DEFAULT_SESSION_TTL_SECONDS = 24 * 3600  # 24 hours
_TOKEN_VERSION = 1  # for forward-compatible payload evolution


# ── Principal ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HostedRoomGuestPrincipal:
    """Resolved guest authority for exactly one room and one participant."""

    room_id: str
    room_slug: str
    participant_id: str
    invitation_id: str
    issued_at: int  # epoch seconds
    expires_at: int  # epoch seconds


# ── Secret resolution ────────────────────────────────────────────────────


def _session_secret() -> bytes:
    """Resolve the signing secret for Hosted Room session tokens.

    Uses the same secret source as normal account sessions
    (``GUARDIAN_SESSION_SECRET``) so operators do not need a second
    cryptographic secret, while domain separation at the token-payload
    level prevents cross-purpose token reuse.
    """
    dev_mode = os.getenv("DEV_MODE", "").lower() in ("1", "true", "yes")
    secret = os.getenv("GUARDIAN_SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")
    if dev_mode:
        return b"dev-secret"
    raise ValueError(
        "GUARDIAN_SESSION_SECRET must be set in production. "
        "Set DEV_MODE=true for local development only."
    )


# ── Cookie policy ────────────────────────────────────────────────────────


def _is_local_auth_boundary() -> bool:
    return os.getenv("GUARDIAN_AUTH_MODE", "").strip().lower() == "local"


def _session_cookie_secure_flag() -> bool:
    """Secure by default; local HTTP in dev mode only."""
    if _is_local_auth_boundary() and os.getenv(
        "GUARDIAN_DEV_MODE", ""
    ).strip().lower() in ("1", "true", "yes"):
        return False
    return True


def _cookie_max_age(expires_at_epoch: int) -> int:
    now = int(time.time())
    remaining = max(0, expires_at_epoch - now)
    return remaining


# ── Token issuance ───────────────────────────────────────────────────────


def issue_guest_session_token(
    *,
    room_id: str,
    room_slug: str,
    participant_id: str,
    invitation_id: str,
    invitation_expires_at: datetime | None = None,
    ttl_seconds: int = _DEFAULT_SESSION_TTL_SECONDS,
) -> tuple[str, int]:
    """Issue a domain-separated Hosted Room guest-session token.

    Returns ``(token, expires_at_epoch_seconds)``.

    The effective TTL is bounded by the invitation expiry when one is
    present.
    """
    now = int(time.time())
    effective_ttl = ttl_seconds
    if invitation_expires_at is not None:
        inv_exp = int(invitation_expires_at.timestamp())
        max_from_inv = max(0, inv_exp - now)
        effective_ttl = min(effective_ttl, max_from_inv)

    exp = now + effective_ttl
    nonce = secrets.token_urlsafe(10)

    payload = json.dumps(
        {
            "v": _TOKEN_VERSION,
            "subject": _SESSION_SUBJECT,
            "room_id": room_id,
            "room_slug": room_slug,
            "participant_id": participant_id,
            "invitation_id": invitation_id,
            "iat": now,
            "exp": exp,
            "nonce": nonce,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    sig = hmac.new(_session_secret(), payload, hashlib.sha256).digest()

    packed = ".".join(
        (
            base64.urlsafe_b64encode(payload).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(sig).decode("ascii").rstrip("="),
        )
    )
    return packed, exp


# ── Token decoding and validation ────────────────────────────────────────


def _urlsafe_b64decode(raw_text: str) -> bytes | None:
    padded = raw_text + ("=" * (-len(raw_text) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return None


def decode_guest_session_token(token: str) -> dict[str, Any]:
    """Decode the claims from a Hosted Room session token.

    Returns the payload dict on success.

    Raises ``HTTPException(401)`` when the token is malformed, expired,
    tampered, signed with the wrong key, or has an incorrect subject.
    """
    packed = (token or "").strip()
    if not packed or "." not in packed:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    try:
        payload_b64, sig_b64 = packed.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    payload_bytes = _urlsafe_b64decode(payload_b64)
    sig_bytes = _urlsafe_b64decode(sig_b64)

    if payload_bytes is None or sig_bytes is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    # Constant-time signature verification
    expected_sig = hmac.new(
        _session_secret(), payload_bytes, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected_sig, sig_bytes):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    try:
        claims = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    # ── Domain separation: reject non-guest-session tokens ─────────────
    subject = str(claims.get("subject") or "")
    if subject != _SESSION_SUBJECT:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )

    # ── Expiry ────────────────────────────────────────────────────────
    exp = int(claims.get("exp") or 0)
    if exp < int(time.time()):
        raise HTTPException(
            status_code=401,
            detail={"error": "session_expired", "message": "Session has expired"},
        )

    # ── Required claims ───────────────────────────────────────────────
    for field in ("room_id", "participant_id", "invitation_id", "room_slug"):
        value = str(claims.get(field) or "").strip()
        if not value:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_session", "message": "Invalid session"},
            )

    return claims


def decode_principal(token: str) -> HostedRoomGuestPrincipal:
    """Decode and validate a session token, returning a typed principal."""
    claims = decode_guest_session_token(token)
    return HostedRoomGuestPrincipal(
        room_id=str(claims["room_id"]),
        room_slug=str(claims["room_slug"]),
        participant_id=str(claims["participant_id"]),
        invitation_id=str(claims["invitation_id"]),
        issued_at=int(claims.get("iat") or 0),
        expires_at=int(claims.get("exp") or 0),
    )


# ── Cookie helpers ───────────────────────────────────────────────────────


def extract_session_token_from_request(request: Request) -> str | None:
    """Extract the Hosted Room session token from the canonical cookie."""
    raw = request.cookies.get(_SESSION_COOKIE_NAME)
    if not raw:
        return None
    token = raw.strip()
    return token or None


def set_session_cookie(
    response: Response,
    token: str,
    expires_at_epoch: int,
) -> None:
    """Set the Hosted Room session cookie with repository-standard attributes."""
    response.set_cookie(
        _SESSION_COOKIE_NAME,
        token,
        max_age=_cookie_max_age(expires_at_epoch),
        httponly=True,
        samesite="Lax",
        secure=_session_cookie_secure_flag(),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the Hosted Room session cookie."""
    response.delete_cookie(
        _SESSION_COOKIE_NAME,
        httponly=True,
        samesite="Lax",
        secure=_session_cookie_secure_flag(),
        path="/",
    )
