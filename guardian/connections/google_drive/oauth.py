"""Server-owned OAuth lifecycle for the Google Drive / Docs connection.

The Google authorization code exchange, refresh, and encrypted credential
storage are deliberately contained here.  Browser clients receive only an
authorization URL and safe connection status; token material and the PKCE
verifier never leave this module.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from guardian.connectors.oauth_crypto import decrypt_token, encrypt_token

PROVIDER_KEY = "google_drive"
MODE = "node_local"
AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
OAUTH_FLOW_TTL_SECONDS = 600
REQUEST_TIMEOUT_SECONDS = 15

# Drive metadata discovery needs the Drive metadata scope while Docs reads
# need the Docs read-only scope.  Both are read-only. Google currently labels
# drive.metadata.readonly restricted and documents.readonly sensitive, which
# is deployment/app-verification work rather than an excuse to ask for broad
# drive.readonly access.
GOOGLE_DRIVE_OAUTH_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
)

_flows: dict[str, dict[str, Any]] = {}


class GoogleDriveOAuthError(RuntimeError):
    error_code = "google_drive_oauth_error"


class GoogleDriveOAuthConfigurationError(GoogleDriveOAuthError):
    error_code = "google_drive_oauth_not_configured"


class GoogleDriveOAuthStateError(GoogleDriveOAuthError):
    error_code = "google_drive_oauth_state_invalid"


class GoogleDriveOAuthAuthorizationError(GoogleDriveOAuthError):
    error_code = "google_drive_authorization_failed"


class GoogleDriveOAuthTransportError(GoogleDriveOAuthError):
    error_code = "google_drive_oauth_transport_error"


class GoogleDriveOAuthProviderError(GoogleDriveOAuthError):
    error_code = "google_drive_oauth_provider_error"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _state_secret() -> str:
    for env_name in (
        "GUARDIAN_SESSION_SECRET",
        "GUARDIAN_JWT_SECRET",
        "GUARDIAN_API_KEY",
    ):
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value
    raise GoogleDriveOAuthConfigurationError("State signing secret is unavailable")


def _node_oauth_config() -> tuple[str, str, str]:
    client_id = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    redirect_uri = (os.getenv("GOOGLE_DRIVE_OAUTH_REDIRECT_URI") or "").strip()
    if not client_id or not client_secret or not redirect_uri:
        raise GoogleDriveOAuthConfigurationError(
            "Google Drive OAuth application configuration is incomplete"
        )
    return client_id, client_secret, redirect_uri


def node_oauth_configured() -> bool:
    """Return whether the node can truthfully launch this OAuth flow."""
    try:
        _node_oauth_config()
        _state_secret()
    except GoogleDriveOAuthConfigurationError:
        return False
    return True


def _encode_state(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(
        _state_secret().encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_state(state: str) -> dict[str, Any]:
    candidate = str(state or "").strip()
    if "." not in candidate:
        raise GoogleDriveOAuthStateError("OAuth state is malformed")
    encoded, received_signature = candidate.rsplit(".", 1)
    expected_signature = hmac.new(
        _state_secret().encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(received_signature, expected_signature):
        raise GoogleDriveOAuthStateError("OAuth state signature is invalid")
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except Exception as exc:
        raise GoogleDriveOAuthStateError("OAuth state cannot be decoded") from exc
    if not isinstance(payload, dict):
        raise GoogleDriveOAuthStateError("OAuth state payload is invalid")
    issued_at = int(payload.get("iat") or 0)
    if issued_at <= 0 or time.time() - issued_at > OAUTH_FLOW_TTL_SECONDS:
        raise GoogleDriveOAuthStateError("OAuth state has expired")
    user_id = str(payload.get("user_id") or "").strip()
    nonce = str(payload.get("nonce") or "").strip()
    if not user_id or not nonce:
        raise GoogleDriveOAuthStateError("OAuth state payload is incomplete")
    return {"user_id": user_id, "nonce": nonce, "iat": issued_at}


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


def _connection(db: Any, user_id: str) -> dict[str, Any] | None:
    return db.get_oauth_connection(user_id=user_id, provider=PROVIDER_KEY, mode=MODE)


def _persist(
    db: Any,
    *,
    user_id: str,
    scopes: list[str] | tuple[str, ...] = GOOGLE_DRIVE_OAUTH_SCOPES,
    status: str,
    encrypted_access_token: str | None = None,
    encrypted_refresh_token: str | None = None,
    expires_at: datetime | None = None,
    last_error: str | None = None,
    refreshed: bool = False,
) -> dict[str, Any]:
    return db.upsert_oauth_connection(
        user_id=user_id,
        provider=PROVIDER_KEY,
        mode=MODE,
        scopes=list(scopes),
        status=status,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=expires_at,
        last_refresh_at=_now_utc() if refreshed else None,
        last_error=last_error,
    )


def _expiry(token_data: dict[str, Any]) -> datetime | None:
    try:
        return _now_utc() + timedelta(seconds=int(token_data.get("expires_in")))
    except (TypeError, ValueError):
        return None


def _token_response(data: dict[str, str]) -> dict[str, Any]:
    try:
        response = requests.post(TOKEN_ENDPOINT, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise GoogleDriveOAuthTransportError("Google token request failed") from exc
    if response.status_code in {400, 401, 403}:
        raise GoogleDriveOAuthAuthorizationError("Google rejected the authorization")
    if response.status_code >= 400:
        raise GoogleDriveOAuthProviderError("Google token endpoint returned an error")
    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleDriveOAuthProviderError("Google token response was invalid") from exc
    if not isinstance(payload, dict):
        raise GoogleDriveOAuthProviderError("Google token response was invalid")
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleDriveOAuthProviderError("Google token response omitted an access token")
    return payload


def begin_oauth(db: Any, user_id: str) -> dict[str, Any]:
    """Create a server-owned Google authorization request and pending state."""
    client_id, _client_secret, redirect_uri = _node_oauth_config()
    verifier, challenge = _pkce_pair()
    nonce = secrets.token_urlsafe(24)
    now = int(time.time())
    _flows[nonce] = {
        "user_id": user_id,
        "verifier": verifier,
        "expires_at": now + OAUTH_FLOW_TTL_SECONDS,
    }
    state = _encode_state({"user_id": user_id, "nonce": nonce, "iat": now})
    existing = _connection(db, user_id) or {}
    _persist(
        db,
        user_id=user_id,
        status="pending",
        encrypted_access_token=existing.get("encrypted_access_token"),
        encrypted_refresh_token=existing.get("encrypted_refresh_token"),
        expires_at=existing.get("expires_at"),
    )
    parameters = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_DRIVE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return {
        "connection_id": PROVIDER_KEY,
        "authorization_url": f"{AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}",
        "expires_in_seconds": OAUTH_FLOW_TTL_SECONDS,
        "state": "authenticating",
    }


def _consume_flow(state: str) -> tuple[str, str]:
    payload = _decode_state(state)
    record = _flows.pop(payload["nonce"], None)
    if record is None or int(record.get("expires_at") or 0) < int(time.time()):
        raise GoogleDriveOAuthStateError("OAuth flow has expired")
    if str(record.get("user_id") or "") != payload["user_id"]:
        raise GoogleDriveOAuthStateError("OAuth state user binding is invalid")
    verifier = str(record.get("verifier") or "")
    if not verifier:
        raise GoogleDriveOAuthStateError("OAuth verifier is unavailable")
    return payload["user_id"], verifier


def complete_oauth(db: Any, *, state: str, code: str | None, error: str | None) -> str:
    """Exchange a validated code and persist encrypted node-owned tokens."""
    user_id, verifier = _consume_flow(state)
    if error:
        mark_connection_error(db, user_id, "google_drive_oauth_denied")
        raise GoogleDriveOAuthAuthorizationError("Google authorization was denied")
    if not code or not code.strip():
        mark_connection_error(db, user_id, "google_drive_oauth_provider_error")
        raise GoogleDriveOAuthProviderError("OAuth callback omitted a code")
    try:
        client_id, client_secret, redirect_uri = _node_oauth_config()
        token_data = _token_response(
            {
                "code": code.strip(),
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            }
        )
    except GoogleDriveOAuthError as exc:
        mark_connection_error(db, user_id, exc.error_code)
        raise
    refresh_token = token_data.get("refresh_token")
    _persist(
        db,
        user_id=user_id,
        status="pending",
        encrypted_access_token=encrypt_token(str(token_data["access_token"])),
        encrypted_refresh_token=encrypt_token(
            str(refresh_token) if isinstance(refresh_token, str) else None
        ),
        expires_at=_expiry(token_data),
        refreshed=True,
    )
    # The legacy generic Google row is quarantined and has no canonical
    # runtime owner. A successful canonical Google Drive authorization clears
    # it so one user is not left with two active OAuth authorities for this
    # same Google content domain.
    db.disconnect_oauth_connection(user_id=user_id, provider="google")
    return user_id


def _as_utc_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def mark_connection_error(db: Any, user_id: str, error_code: str) -> None:
    """Persist only a bounded failure code, retaining server-side tokens."""
    row = _connection(db, user_id)
    if row is None:
        return
    _persist(
        db,
        user_id=user_id,
        scopes=row.get("scopes") or GOOGLE_DRIVE_OAUTH_SCOPES,
        status="error",
        encrypted_access_token=row.get("encrypted_access_token"),
        encrypted_refresh_token=row.get("encrypted_refresh_token"),
        expires_at=_as_utc_datetime(row.get("expires_at")),
        last_error=error_code,
    )


def mark_connection_valid(db: Any, user_id: str) -> None:
    row = _connection(db, user_id)
    if row is None:
        raise GoogleDriveOAuthProviderError("OAuth credential disappeared")
    _persist(
        db,
        user_id=user_id,
        scopes=row.get("scopes") or GOOGLE_DRIVE_OAUTH_SCOPES,
        status="connected",
        encrypted_access_token=row.get("encrypted_access_token"),
        encrypted_refresh_token=row.get("encrypted_refresh_token"),
        expires_at=_as_utc_datetime(row.get("expires_at")),
    )


def access_token_for_user(db: Any, user_id: str) -> str:
    """Return a current access token inside the provider execution boundary."""
    row = _connection(db, user_id)
    if row is None or row.get("status") not in {"pending", "connected"}:
        raise GoogleDriveOAuthAuthorizationError("Google Drive is not connected")
    encrypted_access = row.get("encrypted_access_token")
    expires_at = _as_utc_datetime(row.get("expires_at"))
    if encrypted_access and (
        expires_at is None or expires_at > _now_utc() + timedelta(seconds=60)
    ):
        return decrypt_token(encrypted_access) or ""
    encrypted_refresh = row.get("encrypted_refresh_token")
    if not encrypted_refresh:
        mark_connection_error(db, user_id, "google_drive_refresh_required")
        raise GoogleDriveOAuthAuthorizationError("Google refresh authorization is required")
    try:
        refresh_token = decrypt_token(encrypted_refresh)
        if not refresh_token:
            raise GoogleDriveOAuthAuthorizationError("Google refresh credential is missing")
        client_id, client_secret, _redirect_uri = _node_oauth_config()
        token_data = _token_response(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )
    except GoogleDriveOAuthError as exc:
        mark_connection_error(db, user_id, exc.error_code)
        raise
    next_refresh = token_data.get("refresh_token")
    _persist(
        db,
        user_id=user_id,
        status="connected",
        encrypted_access_token=encrypt_token(str(token_data["access_token"])),
        encrypted_refresh_token=encrypt_token(
            str(next_refresh) if isinstance(next_refresh, str) else refresh_token
        ),
        expires_at=_expiry(token_data),
        refreshed=True,
    )
    return str(token_data["access_token"])


def disconnect(db: Any, user_id: str) -> bool:
    """Clear the local user-scoped grant; no Google provider mutation occurs."""
    return bool(db.disconnect_oauth_connection(user_id=user_id, provider=PROVIDER_KEY))


def safe_status(db: Any, user_id: str) -> dict[str, Any]:
    row = _connection(db, user_id)
    if row is None:
        return {
            "connection_id": PROVIDER_KEY,
            "state": "unconfigured",
            "node_configured": node_oauth_configured(),
            "scopes": list(GOOGLE_DRIVE_OAUTH_SCOPES),
            "error_kind": None,
        }
    raw_error = str(row.get("last_error") or "")
    error_kind = raw_error if raw_error.startswith("google_drive_") else None
    return {
        "connection_id": PROVIDER_KEY,
        "state": str(row.get("status") or "error"),
        "node_configured": node_oauth_configured(),
        "scopes": list(row.get("scopes") or GOOGLE_DRIVE_OAUTH_SCOPES),
        "expires_at": row.get("expires_at"),
        "last_refresh_at": row.get("last_refresh_at"),
        "error_kind": error_kind,
    }
