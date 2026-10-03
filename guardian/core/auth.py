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

from guardian.protocol_tokens import ErrorCode


ACCOUNT_SESSION_PURPOSE = "account_session"
OPERATOR_SESSION_PURPOSE = "operator_session"


def _unverified_session_purpose(token: object) -> str | None:
    """Read an opaque session or JWT purpose as presence evidence only.

    This parser deliberately does not verify the signature, expiry, subject,
    or session-store approval. It is used only to reject requests that present
    multiple credential classes before any credential or resource lookup.
    """
    if not isinstance(token, str):
        return None
    packed = token.strip()
    if not packed or len(packed) > 16_384:
        return None
    parts = packed.split(".")
    if len(parts) == 2:
        payload_b64 = parts[0]
    elif len(parts) == 3:
        # JWT claims occupy the middle segment. Header/signature inspection
        # and ordinary credential verification remain separate from presence.
        payload_b64 = parts[1]
    else:
        return None
    if not payload_b64:
        return None

    def reject_duplicate_claims(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        claims: dict[str, Any] = {}
        for key, value in pairs:
            if key in claims:
                raise ValueError("duplicate session claim")
            claims[key] = value
        return claims

    try:
        padded = payload_b64 + ("=" * (-len(payload_b64) % 4))
        payload = base64.b64decode(
            padded.encode("ascii"), altchars=b"-_", validate=True
        )
        claims = json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicate_claims
        )
    except (ValueError, RecursionError):
        return None

    if not isinstance(claims, dict):
        return None
    purpose = claims.get("purpose")
    if isinstance(purpose, str) and purpose in {
        ACCOUNT_SESSION_PURPOSE,
        OPERATOR_SESSION_PURPOSE,
    }:
        return purpose
    return None


def reject_mixed_principal_credentials(
    request: Request | None,
    *,
    enabled: bool,
    authorization: str | None = None,
    gc_session: str | None = None,
    operator_key_values: tuple[object, ...] = (),
) -> None:
    """Reject cross-principal credential presence before validation/lookups.

    The exact, unverified purpose claim is presence evidence only. Raw keys
    count as operator material only when the caller is an operator-auth seam;
    service-capability callers must leave ``operator_key_values`` empty.
    """
    if not enabled:
        return

    if request is not None:
        if authorization is None:
            authorization = request.headers.get("Authorization")
        if gc_session is None:
            gc_session = request.cookies.get("gc_session")

    authorization_value = (
        authorization.strip() if isinstance(authorization, str) else ""
    )
    session_cookie_value = (
        gc_session.strip() if isinstance(gc_session, str) else ""
    )
    guest_selector_present = bool(
        request is not None
        and "codexify_hosted_room_session" in request.cookies
    )

    # A guest selector combined with any other session-selector material is
    # mixed even when the other token is malformed or expired.
    if guest_selector_present and (authorization_value or session_cookie_value):
        _raise_mixed_principal_credentials()

    lanes: set[str] = set()
    if guest_selector_present:
        lanes.add("guest")
    bearer_token = ""
    if authorization_value.lower().startswith("bearer "):
        bearer_token = authorization_value[7:].strip()
    for token in (bearer_token, session_cookie_value):
        purpose = _unverified_session_purpose(token)
        if purpose == ACCOUNT_SESSION_PURPOSE:
            lanes.add("account")
        elif purpose == OPERATOR_SESSION_PURPOSE:
            lanes.add("operator")

    if any(isinstance(value, str) and value.strip() for value in operator_key_values):
        lanes.add("operator")

    if len(lanes) > 1:
        _raise_mixed_principal_credentials()


def reject_non_guest_bootstrap_credentials(request: Request, *, enabled: bool) -> None:
    """Exclude session-selector material from a guest-only bootstrap.

    Any nonempty Authorization or gc_session value would coexist with the
    issued guest cookie, including malformed or expired material. This narrow
    presence check grants no authority and performs no credential validation.
    """
    if enabled and any(
        value and value.strip()
        for value in (
            request.headers.get("Authorization"),
            request.cookies.get("gc_session"),
        )
    ):
        _raise_mixed_principal_credentials()


def _raise_mixed_principal_credentials() -> None:
    raise HTTPException(
        status_code=400,
        detail={
            "error": ErrorCode.MIXED_PRINCIPAL_CREDENTIALS.value,
            "message": "Conflicting authentication contexts",
        },
    )


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
    subject: str = "web",
    ttl_seconds: int = 24 * 3600,
    *,
    purpose: str,
) -> tuple[str, int]:
    """
    Issue an HMAC-signed opaque session token.

    Returns `(token, expires_at_epoch_seconds)`.
    """
    purpose_value = str(purpose or "").strip()
    if not purpose_value:
        raise ValueError("purpose is required")

    now = int(time.time())
    exp = now + int(ttl_seconds)
    nonce = secrets.token_urlsafe(10)
    payload = json.dumps(
        {
            "subject": subject,
            "exp": exp,
            "nonce": nonce,
            "purpose": purpose_value,
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


def _verified_session_token_claims(token: str) -> dict[str, Any] | None:
    """Return structurally valid claims from a signed current-format token."""
    try:
        packed = (token or "").strip()
        if not packed or packed.count(".") != 1:
            return None
        payload_b64, sig_b64 = packed.split(".", 1)

        def decode(raw_text: str) -> bytes | None:
            padded = raw_text + ("=" * (-len(raw_text) % 4))
            try:
                return base64.urlsafe_b64decode(padded.encode("ascii"))
            except Exception:
                return None

        payload = decode(payload_b64)
        signature = decode(sig_b64)
        if payload is None or signature is None:
            return None
        expected_signature = hmac.new(
            _session_secret(), payload, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        claims = json.loads(payload.decode("utf-8"))
        subject = str(claims.get("subject") or "").strip()
        nonce = str(claims.get("nonce") or "").strip()
        purpose = str(claims.get("purpose") or "").strip()
        int(claims.get("exp") or 0)
        if not subject or not nonce or not purpose:
            return None
        return claims
    except Exception:
        return None


def get_verified_session_token_purpose(token: str) -> str | None:
    """Read a signed token's class for failure classification only.

    Expiry is intentionally not checked here: an expired signed token still
    identifies which credential lane was presented. Callers must use
    ``verify_session_token_for_purpose`` to authorize a request.
    """
    claims = _verified_session_token_claims(token)
    if claims is None:
        return None
    return str(claims.get("purpose") or "").strip() or None


def verify_session_token_for_purpose(
    token: str, expected_purpose: str
) -> bool:
    """Validate a current-format signed session token for one exact purpose.

    Unlike the compatibility verifier below, this validator requires the
    canonical two-part HMAC format and all current claims, including nonce
    and purpose. Legacy purpose-less tokens cannot cross this boundary.
    """
    claims = _verified_session_token_claims(token)
    if claims is None:
        return False
    try:
        return bool(
            str(claims.get("purpose") or "").strip() == expected_purpose
            and int(claims.get("exp") or 0) >= int(time.time())
        )
    except Exception:
        return False


def resolve_account_session_subject(token: str) -> str:
    """Validate an account credential before consulting its session mapping.

    A stored mapping is evidence of session approval, never a substitute for
    the signed subject or the exact account-session purpose.
    """
    if not verify_session_token_for_purpose(token, ACCOUNT_SESSION_PURPOSE):
        raise HTTPException(status_code=401, detail="Account session required")

    valid, subject = verify_session_token(token)
    if not valid or not subject:
        raise HTTPException(status_code=401, detail="Account session required")

    from guardian.core.session_store import get_session_store

    stored_user_id = get_session_store().verify(token)
    if stored_user_id and stored_user_id != subject:
        raise HTTPException(status_code=401, detail="Account session mismatch")
    return subject


def verify_session_token(token: str) -> tuple[bool, str | None]:
    """
    Validate an opaque session token issued by `issue_session_token`.

    Returns `(valid, subject)`.
    """

    def _urlsafe_b64decode(raw_text: str) -> bytes | None:
        padded = raw_text + ("=" * (-len(raw_text) % 4))
        try:
            return base64.urlsafe_b64decode(padded.encode("ascii"))
        except Exception:
            return None

    try:
        packed = token.strip()
        if not packed:
            return False, None

        if "." in packed:
            payload_b64, sig_b64 = packed.split(".", 1)
            payload = _urlsafe_b64decode(payload_b64)
            sig = _urlsafe_b64decode(sig_b64)
            if payload is not None and sig is not None:
                digest = hmac.new(
                    _session_secret(),
                    payload,
                    hashlib.sha256,
                ).digest()
                if hmac.compare_digest(sig, digest):
                    decoded = json.loads(payload.decode("utf-8"))
                    subject = str(decoded.get("subject") or "").strip()
                    exp = int(decoded.get("exp") or 0)
                    if subject and exp >= int(time.time()):
                        return True, subject

        raw = base64.urlsafe_b64decode(
            (packed + ("=" * (-len(packed) % 4))).encode("ascii")
        )
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
    from guardian.core.dependencies import _auth_mode
    from guardian.core.preview_access import is_private_preview, role_for_preview_email

    if is_private_preview() or _auth_mode() == "remote":
        reject_mixed_principal_credentials(
            request,
            enabled=True,
            authorization=authorization,
            gc_session=gc_session,
        )
        from guardian.core.auth_dependencies import extract_session_token

        token = extract_session_token(authorization, gc_session)
        subject = resolve_account_session_subject(token or "")
        if is_private_preview():
            from guardian.core.session_store import get_session_store

            if get_session_store().verify(token) != subject or not role_for_preview_email(subject):
                raise HTTPException(status_code=401, detail="Private preview account required")
        return f"session:{subject}"

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
    from guardian.core.dependencies import _auth_mode
    from guardian.core.preview_access import is_private_preview

    if is_private_preview() or _auth_mode() == "remote":
        # require_auth has already validated the exact account purpose and
        # preview policy. Caller-supplied identity cannot replace that subject.
        user_id = auth_identity.removeprefix("session:")
    else:
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
