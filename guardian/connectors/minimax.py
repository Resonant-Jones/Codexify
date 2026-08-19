"""MiniMax Global OAuth connection-setup lifecycle.

This module implements one bounded MiniMax Global OAuth setup slice for the
Connections control plane:

  POST /api/connect/minimax/start
  POST /api/connect/minimax/poll
  POST /api/connect/minimax/disconnect

It is strictly an authentication/setup lifecycle. It does NOT bind MiniMax
OAuth credentials into the inference runtime, does NOT alter the canonical
provider-registry authority, and does NOT widen the active provider
posture. Credentials are encrypted at rest using
``guardian.connectors.oauth_crypto`` and persisted in the existing
``oauth_connections`` table under provider ``minimax_oauth`` / mode
``node_local``.

Design notes (verified MiniMax Global OAuth UX is the device / user-code
shape, but exact endpoints / client-registration values are operator-supplied
through configuration to avoid borrowing any other application's identity):

* Authorization endpoint, token endpoint, and client identity are read from
  the documented node configuration. Defaults are intentionally absent so
  that a node without legitimate MiniMax OAuth application configuration
  continues to report setup unavailable, never launching a broken flow.
* PKCE (S256) and a random ``state`` value are generated server-side. The
  PKCE verifier is never returned to the browser.
* The user code + verification URI returned by the upstream authorization
  endpoint are projected to the browser only as opaque flow metadata.
* The browser only polls this module's poll route; it never polls the
  upstream provider directly. Tokens are decrypted server-side, never
  serialized to the browser.
* Host allowlists bound upstream requests to known MiniMax Global hosts.
  Arbitrary caller-supplied upstream URLs are rejected.
* All upstream requests use explicit timeouts and bounded body reads. No
  raw upstream body is ever returned to the browser.
* The process-local flow registry is coordination-only, TTL-bounded, and
  user-bound. It is never durable authority.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from guardian.connectors.oauth_crypto import (
    decrypt_token,
    encrypt_token,
)
from guardian.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connect/minimax", tags=["Connections"])

# ---------- canonical constants ---------------------------------

_PROVIDER = "minimax_oauth"
_MODE = "node_local"

# TTL for in-process OAuth flow state.
_FLOW_TTL_SECONDS = 600
# Minimum polling cadence enforced between consecutive upstream polls.
_POLL_INTERVAL_SECONDS = 2
# Bounded body read for upstream HTTP requests.
_UPSTREAM_TIMEOUT_SECONDS = 15
_UPSTREAM_MAX_RESPONSE_BYTES = 16 * 1024

# Host allowlist. Only requests to these MiniMax Global hosts are accepted.
# The list is conservative on purpose; arbitrary caller-supplied URLs are
# rejected. Operators who legitimately register Codexify with MiniMax may
# need to extend this list through documented configuration.
_DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = (
    "api.minimax.io",
    "api.minimaxi.com",
    "auth.minimax.io",
    "auth.minimaxi.com",
)


# ---------- configuration -------------------------------------


def _is_host_allowed(host: str) -> bool:
    """Return True iff host is a member of the configured allowlist."""

    candidate = (host or "").strip().lower()
    if not candidate:
        return False
    allowed = {h.strip().lower() for h in _allowed_hosts()}
    return candidate in allowed


def _allowed_hosts() -> tuple[str, ...]:
    """Resolve the host allowlist from configuration.

    The default is ``_DEFAULT_ALLOWED_HOSTS``. Operators may extend the
    allowlist through ``MINIMAX_OAUTH_ALLOWED_HOSTS`` (comma-separated).
    """

    raw = (os.getenv("MINIMAX_OAUTH_ALLOWED_HOSTS") or "").strip()
    if not raw:
        return _DEFAULT_ALLOWED_HOSTS
    extras = tuple(
        h.strip().lower()
        for h in raw.split(",")
        if h.strip()
    )
    return _DEFAULT_ALLOWED_HOSTS + extras


def _node_oauth_config() -> tuple[str, str, str]:
    """Resolve the MiniMax OAuth node configuration.

    Returns ``(authorize_url, token_url, client_id)`` iff every required
    value is configured. Raises ``HTTPException(503)`` otherwise. We never
    fall back to borrowed values from other applications.
    """

    authorize_url = (os.getenv("MINIMAX_OAUTH_AUTHORIZE_URL") or "").strip()
    token_url = (os.getenv("MINIMAX_OAUTH_TOKEN_URL") or "").strip()
    client_id = (os.getenv("MINIMAX_OAUTH_CLIENT_ID") or "").strip()
    if not authorize_url or not token_url or not client_id:
        raise HTTPException(
            status_code=503,
            detail=(
                "MiniMax OAuth is not configured on this node. Set "
                "MINIMAX_OAUTH_AUTHORIZE_URL, MINIMAX_OAUTH_TOKEN_URL, and "
                "MINIMAX_OAUTH_CLIENT_ID with the Codexify-owned application "
                "registration before initiating setup."
            ),
        )
    # Reject arbitrary caller-supplied URLs by validating hosts.
    for url_value in (authorize_url, token_url):
        try:
            host = url_value.split("://", 1)[1].split("/", 1)[0].split(
                ":", 1
            )[0]
        except IndexError:
            raise HTTPException(
                status_code=503,
                detail="MiniMax OAuth endpoint URL is malformed.",
            )
        if not _is_host_allowed(host):
            raise HTTPException(
                status_code=503,
                detail=(
                    f"MiniMax OAuth endpoint host {host!r} is not in the "
                    "configured allowlist. Refusing to send a request."
                ),
            )
    return authorize_url, token_url, client_id


# ---------- ephemeral flow registry ---------------------------

_flows_lock = threading.Lock()
_flows: dict[str, dict[str, Any]] = {}


def _new_flow_id() -> str:
    return secrets.token_urlsafe(24)


def _store_flow(flow_id: str, record: dict[str, Any]) -> None:
    with _flows_lock:
        _flows[flow_id] = record


def _get_flow(flow_id: str) -> dict[str, Any] | None:
    now = time.time()
    with _flows_lock:
        record = _flows.get(flow_id)
        if record is None:
            return None
        if now - float(record["created_at"]) > _FLOW_TTL_SECONDS:
            del _flows[flow_id]
            return None
        return record


def _drop_flow(flow_id: str) -> None:
    with _flows_lock:
        _flows.pop(flow_id, None)


# ---------- PKCE helpers --------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _pkce_pair() -> tuple[str, str]:
    """Return a fresh PKCE (verifier, challenge) pair using S256."""

    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(
        hashlib.sha256(verifier.encode("ascii")).digest()
    )
    return verifier, challenge


# ---------- upstream HTTP helpers -----------------------------


def _bounded_post(
    url: str,
    *,
    data: dict[str, str],
    timeout: int = _UPSTREAM_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST to an allowlisted upstream with bounded read and timeouts."""

    try:
        response = requests.post(url, data=data, timeout=timeout)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax OAuth upstream request failed: {exc.__class__.__name__}",
        ) from exc
    raw = response.content[:_UPSTREAM_MAX_RESPONSE_BYTES]
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="MiniMax OAuth upstream returned non-JSON body.",
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="MiniMax OAuth upstream returned an error.",
        )
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=502,
            detail="MiniMax OAuth upstream returned an unexpected payload shape.",
        )
    return body


# ---------- authorization request -----------------------------


def _request_user_code(
    *,
    authorize_url: str,
    client_id: str,
    state: str,
    challenge: str,
) -> dict[str, Any]:
    """Issue the MiniMax OAuth authorization request and parse it.

    The MiniMax Global OAuth contract is the device / user-code shape:
    the upstream returns ``user_code`` + ``verification_uri`` + ``expires_in``
    + ``interval``. Required fields are validated defensively; missing or
    malformed responses fail closed.
    """

    params = {
        "client_id": client_id,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    data = urlencode(params)
    full_url = f"{authorize_url}?{data}"
    body = _bounded_post(full_url, data={})
    user_code = str(body.get("user_code") or "").strip()
    verification_uri = str(body.get("verification_uri") or "").strip()
    interval_raw = body.get("interval")
    expires_in = body.get("expires_in")
    if not user_code or not verification_uri:
        raise HTTPException(
            status_code=502,
            detail=(
                "MiniMax OAuth authorization response is missing "
                "user_code or verification_uri."
            ),
        )
    try:
        interval = int(str(interval_raw)) if interval_raw is not None else _POLL_INTERVAL_SECONDS
    except (TypeError, ValueError):
        interval = _POLL_INTERVAL_SECONDS
    if interval < _POLL_INTERVAL_SECONDS:
        interval = _POLL_INTERVAL_SECONDS
    try:
        ttl = int(str(expires_in)) if expires_in is not None else _FLOW_TTL_SECONDS
    except (TypeError, ValueError):
        ttl = _FLOW_TTL_SECONDS
    if ttl <= 0 or ttl > _FLOW_TTL_SECONDS:
        ttl = _FLOW_TTL_SECONDS
    return {
        "user_code": user_code,
        "verification_uri": verification_uri,
        "interval": interval,
        "expires_in": ttl,
    }


# ---------- token exchange / refresh --------------------------


def _exchange_or_pending(
    *,
    token_url: str,
    client_id: str,
    state: str,
    verifier: str,
) -> dict[str, Any]:
    """Call the MiniMax token endpoint. Returns success dict or pending dict."""

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": verifier,
        "state": state,
    }
    try:
        response = requests.post(
            token_url, data=data, timeout=_UPSTREAM_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax OAuth token endpoint failed: {exc.__class__.__name__}",
        ) from exc
    raw = response.content[:_UPSTREAM_MAX_RESPONSE_BYTES]
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="MiniMax OAuth token endpoint returned non-JSON body.",
        ) from exc
    if response.status_code == 400:
        # Pending responses for device/user-code flows. We surface only the
        # canonical "pending" classification; raw provider error text is not
        # serialized.
        error_kind = str(body.get("error") or "").strip().lower()
        if error_kind in {"authorization_pending", "slow_down", "pending"}:
            return {"status": "pending"}
        if error_kind in {"expired_token", "access_denied"}:
            return {"status": "error", "kind": error_kind}
    if response.status_code >= 400:
        return {"status": "error", "kind": "provider_error"}
    access = body.get("access_token")
    refresh = body.get("refresh_token")
    if not isinstance(access, str) or not access:
        return {"status": "error", "kind": "missing_access_token"}
    return {
        "status": "connected",
        "access_token": access,
        "refresh_token": refresh if isinstance(refresh, str) and refresh else None,
        "expires_in": body.get("expires_in"),
        "scopes": body.get("scope"),
    }


def _refresh_token(
    *,
    refresh_token: str,
    client_id: str,
    token_url: str,
) -> dict[str, Any]:
    """Call the MiniMax refresh endpoint; never serialize tokens."""

    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    try:
        response = requests.post(
            token_url, data=data, timeout=_UPSTREAM_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"MiniMax OAuth refresh failed: {exc.__class__.__name__}"
        ) from exc
    raw = response.content[:_UPSTREAM_MAX_RESPONSE_BYTES]
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("MiniMax OAuth refresh returned non-JSON body.") from exc
    if response.status_code >= 400:
        raise RuntimeError("MiniMax OAuth refresh was rejected by the provider.")
    access = body.get("access_token")
    if not isinstance(access, str) or not access:
        raise RuntimeError("MiniMax OAuth refresh did not return access_token.")
    return {
        "access_token": access,
        "refresh_token": body.get("refresh_token"),
        "expires_in": body.get("expires_in"),
    }


# ---------- persistence (existing oauth_connections table) ----


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at_from(expires_in: Any) -> datetime | None:
    if expires_in is None:
        return None
    try:
        seconds = int(str(expires_in))
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return _now_utc() + timedelta(seconds=seconds)


def _persist(
    *,
    user_id: str,
    status: str,
    scopes: list[str],
    encrypted_access_token: str | None = None,
    encrypted_refresh_token: str | None = None,
    expires_at: datetime | None = None,
    last_error: str | None = None,
    set_last_refresh: bool = False,
) -> None:
    """Persist the connection under (user_id, provider, mode)."""

    from guardian.core.db import load_guardian_db_from_env

    db = load_guardian_db_from_env()
    if db is None:
        raise RuntimeError("Guardian database is not configured.")
    db.upsert_oauth_connection(
        user_id=user_id,
        provider=_PROVIDER,
        mode=_MODE,
        scopes=scopes,
        status=status,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=expires_at,
        last_refresh_at=_now_utc() if set_last_refresh else None,
        last_error=last_error,
    )


# ---------- routes --------------------------------------------


class PollRequest(BaseModel):
    flow_id: str


class DisconnectRequest(BaseModel):
    pass


@router.post("/start")
def start_connect(current_user: str = Depends(get_current_user)) -> dict:
    """Begin a MiniMax OAuth setup flow.

    Returns safe browser-facing flow metadata: opaque ``flow_id``,
    verification URI, user code, and TTL. The PKCE verifier is never
    returned.
    """

    authorize_url, _token_url, client_id = _node_oauth_config()
    state = secrets.token_urlsafe(24)
    verifier, challenge = _pkce_pair()
    upstream = _request_user_code(
        authorize_url=authorize_url,
        client_id=client_id,
        state=state,
        challenge=challenge,
    )
    flow_id = _new_flow_id()
    _store_flow(
        flow_id,
        {
            "user_id": current_user,
            "state": state,
            "verifier": verifier,
            "client_id": client_id,
            "interval": upstream["interval"],
            "expires_at": _now_utc()
            + timedelta(seconds=upstream["expires_in"]),
            "created_at": time.time(),
            "started_at": time.time(),
            "last_poll": 0.0,
            "verification_uri": upstream["verification_uri"],
        },
    )
    # Best-effort pending projection so the catalog immediately reflects
    # authenticating state for this user, without revealing tokens.
    try:
        _persist(
            user_id=current_user,
            status="pending",
            scopes=[],
        )
    except Exception as exc:  # pragma: no cover - DB degraded
        logger.warning(
            "[minimax-oauth] pending projection failed kind=%s",
            exc.__class__.__name__,
        )
    return {
        "provider": _PROVIDER,
        "flow_id": flow_id,
        "verification_uri": upstream["verification_uri"],
        "user_code": upstream["user_code"],
        "expires_at": (
            _now_utc() + timedelta(seconds=upstream["expires_in"])
        ).isoformat(),
        "poll_interval_seconds": upstream["interval"],
    }


@router.post("/poll")
def poll_connect(
    payload: PollRequest,
    current_user: str = Depends(get_current_user),
) -> dict:
    """Poll the upstream token endpoint for an in-flight MiniMax OAuth flow.

    Browser polls only this route; tokens never leave the server.
    """

    flow_id = (payload.flow_id or "").strip()
    if not flow_id:
        raise HTTPException(status_code=400, detail="Missing flow_id.")
    record = _get_flow(flow_id)
    if record is None:
        raise HTTPException(status_code=410, detail="OAuth flow has expired.")
    if record["user_id"] != current_user:
        # Cross-user polling must fail closed without leaking existence.
        raise HTTPException(status_code=404, detail="OAuth flow not found.")
    if _now_utc() >= record["expires_at"]:
        _drop_flow(flow_id)
        try:
            _persist(
                user_id=current_user,
                status="error",
                scopes=[],
                last_error="flow_expired",
            )
        except Exception:  # pragma: no cover
            pass
        raise HTTPException(status_code=410, detail="OAuth flow has expired.")
    now = time.time()
    last_marker = float(record.get("last_poll") or record.get("started_at") or 0.0)
    if now - last_marker < float(record["interval"]):
        raise HTTPException(
            status_code=429,
            detail="Polling cadence not yet satisfied.",
        )
    record["last_poll"] = now
    if record.get("started_at") is None:
        record["started_at"] = now
    _token_url = (os.getenv("MINIMAX_OAUTH_TOKEN_URL") or "").strip()
    if not _token_url:
        # Should be guarded by _node_oauth_config at start, but fail closed.
        _drop_flow(flow_id)
        raise HTTPException(status_code=503, detail="MiniMax OAuth is not configured.")
    try:
        result = _exchange_or_pending(
            token_url=_token_url,
            client_id=record["client_id"],
            state=record["state"],
            verifier=record["verifier"],
        )
    except HTTPException:
        # Malformed/non-JSON upstream bodies fail closed at the exchange
        # layer. Drop the flow so the user can retry cleanly.
        _drop_flow(flow_id)
        raise
    status = str(result.get("status") or "")
    if status == "pending":
        return {"provider": _PROVIDER, "flow_id": flow_id, "status": "authenticating"}
    if status == "error":
        _drop_flow(flow_id)
        kind = str(result.get("kind") or "provider_error")
        try:
            _persist(
                user_id=current_user,
                status="error",
                scopes=[],
                last_error=kind,
            )
        except Exception:  # pragma: no cover
            pass
        return {"provider": _PROVIDER, "flow_id": flow_id, "status": "error", "kind": kind}
    # Connected: encrypt and persist.
    encrypted_access = encrypt_token(result.get("access_token"))
    encrypted_refresh = encrypt_token(result.get("refresh_token"))
    expires_at = _expires_at_from(result.get("expires_in"))
    scopes_raw = result.get("scopes")
    if isinstance(scopes_raw, str):
        scopes = sorted({s for s in scopes_raw.split() if s})
    elif isinstance(scopes_raw, list):
        scopes = sorted({str(s) for s in scopes_raw if s})
    else:
        scopes = []
    try:
        _persist(
            user_id=current_user,
            status="connected",
            scopes=scopes,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            expires_at=expires_at,
            set_last_refresh=True,
        )
    except RuntimeError as exc:
        _drop_flow(flow_id)
        raise HTTPException(
            status_code=503,
            detail=f"OAuth persistence unavailable: {exc}",
        ) from exc
    _drop_flow(flow_id)
    return {
        "provider": _PROVIDER,
        "flow_id": flow_id,
        "status": "connected",
        "scopes": scopes,
    }


@router.post("/disconnect")
def disconnect(
    current_user: str = Depends(get_current_user),
) -> dict:
    """Disconnect the current user's MiniMax OAuth connection."""

    from guardian.core.db import load_guardian_db_from_env

    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    count = db.disconnect_oauth_connection(
        user_id=current_user, provider=_PROVIDER, mode=_MODE
    )
    return {"provider": _PROVIDER, "mode": _MODE, "disconnected": int(count or 0)}


@router.get("/status")
def connection_status(current_user: str = Depends(get_current_user)) -> dict:
    """Read-only status of the current user's MiniMax OAuth connection.

    No tokens are ever serialized.
    """

    from guardian.core.db import load_guardian_db_from_env

    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    row = db.get_oauth_connection(
        user_id=current_user, provider=_PROVIDER, mode=_MODE
    )
    if not row:
        return {
            "provider": _PROVIDER,
            "mode": _MODE,
            "status": "disconnected",
            "connected": False,
        }
    return {
        "provider": _PROVIDER,
        "mode": row.get("mode") or _MODE,
        "status": row.get("status") or "disconnected",
        "connected": row.get("status") == "connected",
        "scopes": list(row.get("scopes") or []),
        "expires_at": (
            row["expires_at"].isoformat() if row.get("expires_at") else None
        ),
        "last_refresh_at": (
            row["last_refresh_at"].isoformat()
            if row.get("last_refresh_at")
            else None
        ),
    }


# ---------- provider-owned refresh helper ---------------------


def refresh_minimax_oauth(
    *,
    user_id: str,
    encrypted_refresh_token: str,
) -> dict[str, Any]:
    """Refresh the current user's MiniMax OAuth access token.

    This helper exists for a future OAuth-to-runtime binding task. It is
    not invoked by any inference path today. It must NEVER serialize
    credentials.
    """

    client_id = (os.getenv("MINIMAX_OAUTH_CLIENT_ID") or "").strip()
    token_url = (os.getenv("MINIMAX_OAUTH_TOKEN_URL") or "").strip()
    if not client_id or not token_url:
        raise RuntimeError("MiniMax OAuth is not configured on this node.")
    refresh_token = decrypt_token(encrypted_refresh_token)
    if not refresh_token:
        raise RuntimeError("Stored MiniMax OAuth refresh token is missing.")
    result = _refresh_token(
        refresh_token=refresh_token,
        client_id=client_id,
        token_url=token_url,
    )
    new_refresh = result.get("refresh_token")
    # Preserve the existing refresh token when the provider omits one.
    encrypted_access = encrypt_token(result.get("access_token"))
    encrypted_refresh = (
        encrypt_token(new_refresh)
        if isinstance(new_refresh, str) and new_refresh
        else encrypted_refresh_token
    )
    _persist(
        user_id=user_id,
        status="connected",
        scopes=[],
        encrypted_access_token=encrypted_access,
        encrypted_refresh_token=encrypted_refresh,
        expires_at=_expires_at_from(result.get("expires_in")),
        set_last_refresh=True,
    )
    return {
        "provider": _PROVIDER,
        "mode": _MODE,
        "status": "connected",
    }


# ---------- node configuration helper -------------------------


def node_oauth_configured() -> bool:
    """Return True iff this node has a complete MiniMax OAuth configuration.

    Used by catalog projection and frontend gating. Never raises.
    """

    try:
        _node_oauth_config()
        return True
    except HTTPException:
        return False