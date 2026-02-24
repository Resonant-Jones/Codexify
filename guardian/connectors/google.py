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
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from guardian.connectors.oauth_crypto import decrypt_token, encrypt_token
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import get_current_user

router = APIRouter(prefix="/api/connect/google", tags=["connectors"])

_SUPPORTED_MODES = {"node_local", "relay_broker"}
_SUPPORTED_CONNECTOR_MODES = {"node_local", "hybrid", "relay_only"}
_STATE_TTL_SECONDS = 600
_PROVIDER = "google"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "email",
    "profile",
]
_cached_guardian_db = None


class DisconnectRequest(BaseModel):
    mode: str | None = None


def _get_guardian_db():
    global _cached_guardian_db
    if _cached_guardian_db is None:
        try:
            _cached_guardian_db = load_guardian_db_from_env()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Database initialization failed: {exc}",
            ) from exc
    if _cached_guardian_db is None:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Set GUARDIAN_DATABASE_URL or DATABASE_URL.",
        )
    return _cached_guardian_db


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
    raise HTTPException(
        status_code=500,
        detail=(
            "Missing state signing secret. Configure GUARDIAN_SESSION_SECRET, "
            "GUARDIAN_JWT_SECRET, or GUARDIAN_API_KEY."
        ),
    )


def _connector_mode() -> str:
    mode = (os.getenv("GOOGLE_CONNECTOR_MODE") or "hybrid").strip().lower()
    if mode in _SUPPORTED_CONNECTOR_MODES:
        return mode
    return "hybrid"


def _normalize_mode(mode: str | None) -> str:
    normalized = (mode or "node_local").strip().lower()
    if normalized not in _SUPPORTED_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Expected one of: {sorted(_SUPPORTED_MODES)}",
        )
    return normalized


def _enforce_mode_allowed(requested_mode: str) -> None:
    runtime_mode = _connector_mode()
    if runtime_mode == "hybrid":
        return
    if runtime_mode == "node_local" and requested_mode == "relay_broker":
        raise HTTPException(
            status_code=403,
            detail="GOOGLE_CONNECTOR_MODE=node_local does not allow relay_broker.",
        )
    if runtime_mode == "relay_only" and requested_mode == "node_local":
        raise HTTPException(
            status_code=403,
            detail="GOOGLE_CONNECTOR_MODE=relay_only does not allow node_local.",
        )


def _node_local_oauth_config() -> tuple[str, str, str]:
    client_id = (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
    redirect_uri = (
        os.getenv("GOOGLE_OAUTH_REDIRECT")
        or "http://localhost:8888/api/connect/google/callback"
    ).strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "Node-local Google OAuth is not configured. Set "
                "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET."
            ),
        )
    return client_id, client_secret, redirect_uri


def _relay_broker_url() -> str:
    url = (os.getenv("GOOGLE_RELAY_BROKER_URL") or "").strip()
    if not url:
        raise HTTPException(
            status_code=503,
            detail=(
                "Relay broker mode is not configured. Set GOOGLE_RELAY_BROKER_URL."
            ),
        )
    return url


def _encode_state(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    b64 = base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")
    sig = hmac.new(
        _state_secret().encode("utf-8"),
        b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{b64}.{sig}"


def _decode_state(value: str) -> dict[str, Any]:
    raw = (value or "").strip()
    if "." not in raw:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    b64, sig = raw.rsplit(".", 1)
    expected = hmac.new(
        _state_secret().encode("utf-8"),
        b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    padded = b64 + "=" * (-len(b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid OAuth state."
        ) from exc

    issued_at = int(payload.get("iat") or 0)
    if issued_at <= 0 or time.time() - issued_at > _STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="OAuth state expired.")

    mode = str(payload.get("mode") or "").strip()
    user_id = str(payload.get("user_id") or "").strip()
    if mode not in _SUPPORTED_MODES or not user_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    return payload


def _exchange_code_for_token(
    code: str,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    response = requests.post(_TOKEN_ENDPOINT, data=data, timeout=15)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"Google token exchange failed: {response.text[:300]}",
        )
    return response.json()


def _refresh_access_token(
    refresh_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(_TOKEN_ENDPOINT, data=data, timeout=15)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"Google token refresh failed: {response.text[:300]}",
        )
    return response.json()


def _persist_connection(
    *,
    user_id: str,
    mode: str,
    scopes: list[str],
    status: str,
    encrypted_access_token: str | None = None,
    encrypted_refresh_token: str | None = None,
    relay_grant_id: str | None = None,
    expires_at: datetime | None = None,
    last_error: str | None = None,
    set_last_refresh: bool = False,
) -> dict[str, Any]:
    db = _get_guardian_db()
    try:
        return db.upsert_oauth_connection(
            user_id=user_id,
            provider=_PROVIDER,
            mode=mode,
            scopes=scopes,
            status=status,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            relay_grant_id=relay_grant_id,
            expires_at=expires_at,
            last_refresh_at=_now_utc() if set_last_refresh else None,
            last_error=last_error,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"OAuth persistence unavailable: {exc}",
        ) from exc


def _scopes_from_token_data(token_data: dict[str, Any]) -> list[str]:
    scope_raw = str(token_data.get("scope") or "").strip()
    if not scope_raw:
        return list(_SCOPES)
    return sorted({part for part in scope_raw.split(" ") if part})


def _to_datetime_from_expires_in(expires_in: Any) -> datetime | None:
    try:
        ttl = int(expires_in)
    except (TypeError, ValueError):
        return None
    return _now_utc() + timedelta(seconds=ttl)


@router.get("/start")
def start_connect(
    mode: str = Query(
        default="node_local", pattern="^(node_local|relay_broker)$"
    ),
    current_user: str = Depends(get_current_user),
):
    requested_mode = _normalize_mode(mode)
    _enforce_mode_allowed(requested_mode)

    state_payload = {
        "user_id": current_user,
        "mode": requested_mode,
        "nonce": secrets.token_hex(16),
        "iat": int(time.time()),
    }
    signed_state = _encode_state(state_payload)

    if requested_mode == "relay_broker":
        broker_url = _relay_broker_url()
        audience = (os.getenv("GOOGLE_RELAY_AUDIENCE") or "").strip()
        redirect_uri = (
            os.getenv("GOOGLE_OAUTH_REDIRECT")
            or "http://localhost:8888/api/connect/google/callback"
        ).strip()
        params = {
            "provider": "google",
            "state": signed_state,
            "callback_url": redirect_uri,
        }
        if audience:
            params["audience"] = audience
        join_char = "&" if "?" in broker_url else "?"
        return RedirectResponse(f"{broker_url}{join_char}{urlencode(params)}")

    client_id, _client_secret, redirect_uri = _node_local_oauth_config()
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "redirect_uri": redirect_uri,
        "state": signed_state,
    }
    url = f"{_AUTH_ENDPOINT}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
def callback(
    state: str,
    code: str | None = None,
    relay_grant_id: str | None = None,
    error: str | None = None,
):
    state_payload = _decode_state(state)
    user_id = str(state_payload["user_id"])
    mode = _normalize_mode(str(state_payload["mode"]))
    _enforce_mode_allowed(mode)

    if error:
        _persist_connection(
            user_id=user_id,
            mode=mode,
            scopes=[],
            status="error",
            last_error=error,
        )
        raise HTTPException(
            status_code=400, detail=f"OAuth callback error: {error}"
        )

    if mode == "relay_broker":
        grant_id = (relay_grant_id or "").strip()
        if not grant_id and code:
            # Broker implementations may return a short one-time code.
            grant_id = f"broker_code:{code[:48]}"
        if not grant_id:
            raise HTTPException(
                status_code=400,
                detail="Relay broker callback missing relay_grant_id or code.",
            )
        row = _persist_connection(
            user_id=user_id,
            mode="relay_broker",
            scopes=[],
            status="connected",
            relay_grant_id=grant_id,
            encrypted_access_token=None,
            encrypted_refresh_token=None,
            expires_at=None,
            set_last_refresh=False,
        )
        return {
            "ok": True,
            "provider": _PROVIDER,
            "mode": "relay_broker",
            "status": row.get("status"),
            "custody": "relay",
            "relay_grant_id": row.get("relay_grant_id"),
        }

    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code.")
    client_id, client_secret, redirect_uri = _node_local_oauth_config()
    token_data = _exchange_code_for_token(
        code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    encrypted_access = encrypt_token(token_data.get("access_token"))
    encrypted_refresh = encrypt_token(token_data.get("refresh_token"))
    scopes = _scopes_from_token_data(token_data)
    row = _persist_connection(
        user_id=user_id,
        mode="node_local",
        scopes=scopes,
        status="connected",
        encrypted_access_token=encrypted_access,
        encrypted_refresh_token=encrypted_refresh,
        expires_at=_to_datetime_from_expires_in(token_data.get("expires_in")),
        set_last_refresh=True,
    )
    return {
        "ok": True,
        "provider": _PROVIDER,
        "mode": "node_local",
        "status": row.get("status"),
        "scopes": row.get("scopes") or [],
        "expires_at": row.get("expires_at"),
        "custody": "node",
    }


@router.get("/status")
def status(
    mode: str = Query(
        default="node_local", pattern="^(node_local|relay_broker)$"
    ),
    current_user: str = Depends(get_current_user),
):
    requested_mode = _normalize_mode(mode)
    _enforce_mode_allowed(requested_mode)
    db = _get_guardian_db()
    row = db.get_oauth_connection(
        user_id=current_user,
        provider=_PROVIDER,
        mode=requested_mode,
    )
    if not row:
        return {
            "provider": _PROVIDER,
            "mode": requested_mode,
            "status": "disconnected",
            "connected": False,
            "scopes": [],
        }

    expires_at = row.get("expires_at")
    should_refresh = (
        requested_mode == "node_local"
        and row.get("status") == "connected"
        and expires_at is not None
        and expires_at <= _now_utc() + timedelta(seconds=60)
        and bool(row.get("encrypted_refresh_token"))
    )
    if should_refresh:
        client_id, client_secret, _redirect_uri = _node_local_oauth_config()
        try:
            refresh_token = decrypt_token(row.get("encrypted_refresh_token"))
            if refresh_token:
                token_data = _refresh_access_token(
                    refresh_token,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                access_token = encrypt_token(token_data.get("access_token"))
                next_refresh = token_data.get("refresh_token") or refresh_token
                row = _persist_connection(
                    user_id=current_user,
                    mode="node_local",
                    scopes=_scopes_from_token_data(token_data),
                    status="connected",
                    encrypted_access_token=access_token,
                    encrypted_refresh_token=encrypt_token(next_refresh),
                    expires_at=_to_datetime_from_expires_in(
                        token_data.get("expires_in")
                    ),
                    set_last_refresh=True,
                )
        except Exception as exc:
            row = _persist_connection(
                user_id=current_user,
                mode="node_local",
                scopes=row.get("scopes") or [],
                status="error",
                encrypted_access_token=row.get("encrypted_access_token"),
                encrypted_refresh_token=row.get("encrypted_refresh_token"),
                relay_grant_id=row.get("relay_grant_id"),
                expires_at=row.get("expires_at"),
                last_error=str(exc),
            )

    return {
        "provider": _PROVIDER,
        "mode": row.get("mode"),
        "status": row.get("status"),
        "connected": row.get("status") == "connected",
        "scopes": row.get("scopes") or [],
        "expires_at": row.get("expires_at"),
        "last_refresh_at": row.get("last_refresh_at"),
        "last_error": row.get("last_error"),
        "relay_grant_id": row.get("relay_grant_id"),
        "custody": "relay" if row.get("mode") == "relay_broker" else "node",
    }


@router.post("/disconnect")
def disconnect(
    payload: DisconnectRequest | None = None,
    current_user: str = Depends(get_current_user),
):
    requested_mode = (
        _normalize_mode(payload.mode) if payload and payload.mode else None
    )
    if requested_mode:
        _enforce_mode_allowed(requested_mode)
    db = _get_guardian_db()
    count = db.disconnect_oauth_connection(
        user_id=current_user,
        provider=_PROVIDER,
        mode=requested_mode,
    )
    return {
        "ok": True,
        "disconnected": count,
        "provider": _PROVIDER,
        "mode": requested_mode,
    }
