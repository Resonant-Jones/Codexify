"""Authentication routes for session-backed login."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Cookie, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from guardian.account_observability.invites import (
    complete_registration_attribution,
    record_invite_audit,
)
from guardian.account_observability.presence import end_account_presence
from guardian.account_observability.tokens import (
    ATTRIBUTION_COOKIE_NAME,
    AccountObservabilityInviteAuditAction,
)
from guardian.core.auth import issue_session_token
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import resolve_session_user_id
from guardian.core.passwords import hash_password, verify_password
from guardian.core.preview_access import (
    is_private_preview,
    normalize_preview_email,
    role_for_preview_email,
)
from guardian.core.request_correlation import normalize_request_id
from guardian.core.session_store import (
    DEFAULT_SESSION_TTL_SECONDS,
    get_session_store,
)
from guardian.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])
api_router = APIRouter(prefix="/api/auth", tags=["Auth"])


class AuthRegisterRequest(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(extra="ignore")


class AuthLoginRequest(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(extra="ignore")


def _auth_db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Authentication database unavailable",
        )
    return db


def _normalize_username(username: str) -> str:
    value = str(username or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="username is required")
    return value


def _normalize_password(password: str) -> str:
    value = str(password or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="password is required")
    return value


def _get_user_by_username(session: Any, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def _resolve_token_from_request(
    authorization: str | None,
    gc_session: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    if gc_session:
        token = gc_session.strip()
        if token:
            return token
    return None


def _registration_request_id(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None)
    normalized, _ = normalize_request_id(
        state_id or request.headers.get("X-Request-ID")
    )
    request.state.request_id = normalized
    return normalized


def _record_registration_attribution_audit_best_effort(
    db: Any,
    *,
    user_id: str,
    invite_id: str,
    request_id: str,
) -> None:
    try:
        with db.get_session() as audit_session:
            record_invite_audit(
                audit_session,
                action=AccountObservabilityInviteAuditAction.REGISTRATION_ATTRIBUTED.value,
                invite_id=invite_id,
                actor_id=user_id,
                request_id=request_id,
                result="attributed",
            )
            audit_session.commit()
    except Exception as exc:
        logger.warning(
            "[account_observability] registration_audit_failed user_id=%s invite_id=%s request_id=%s error_class=%s",
            user_id,
            invite_id,
            request_id,
            type(exc).__name__,
        )


@router.post("/register")
@api_router.post("/register")
def register_user(
    body: AuthRegisterRequest,
    request: Request,
    attribution_guest_id: str
    | None = Cookie(default=None, alias=ATTRIBUTION_COOKIE_NAME),
) -> dict[str, Any]:
    if is_private_preview():
        # Preview users are provisioned by the operator, never self-registered.
        raise HTTPException(status_code=404, detail="Not found")
    username = _normalize_username(body.username)
    password = _normalize_password(body.password)

    db = _auth_db()
    with db.get_session() as session:
        existing = _get_user_by_username(session, username)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Username already exists",
            )

        user = User(
            id=username,
            username=username,
            password_hash=hash_password(password),
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # Canonical account creation is already committed. Attribution is a
    # separate, best-effort observability transaction and cannot roll it back.
    try:
        with db.get_session() as observability_session:
            conversion = complete_registration_attribution(
                observability_session,
                user_id=user.id,
                guest_cookie=attribution_guest_id,
                registered_at=user.created_at,
            )
            observability_session.commit()
        if conversion.attributed and conversion.invite_id:
            _record_registration_attribution_audit_best_effort(
                db,
                user_id=user.id,
                invite_id=conversion.invite_id,
                request_id=_registration_request_id(request),
            )
    except Exception as exc:
        logger.warning(
            "[account_observability] registration_attribution_failed user_id=%s error_class=%s",
            user.id,
            type(exc).__name__,
        )

    return {
        "ok": True,
        "user_id": user.id,
        "username": user.username,
    }


@router.post("/login")
@api_router.post("/login")
def login_user(body: AuthLoginRequest) -> dict[str, Any]:
    username = _normalize_username(body.username)
    password = _normalize_password(body.password)

    preview_role = None
    if is_private_preview():
        username = normalize_preview_email(username)
        preview_role = role_for_preview_email(username)
        if not username or preview_role is None:
            raise HTTPException(
                status_code=401, detail="Invalid username or password"
            )

    db = _auth_db()
    with db.get_session() as session:
        user = _get_user_by_username(session, username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password",
            )

        if preview_role is not None and user.role != preview_role:
            user.role = preview_role
            session.commit()

        token, expires_at = issue_session_token(
            subject=user.id, ttl_seconds=DEFAULT_SESSION_TTL_SECONDS
        )
        get_session_store().store(
            token,
            user.id,
            DEFAULT_SESSION_TTL_SECONDS,
        )

    return {
        "token": token,
        "user_id": user.id,
        "expires_at": expires_at,
    }


@router.post("/logout")
@api_router.post("/logout")
def logout_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    gc_session: str | None = Cookie(default=None, alias="gc_session"),
) -> dict[str, Any]:
    token = _resolve_token_from_request(authorization, gc_session)
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    try:
        user_id = resolve_session_user_id(authorization, gc_session)
    except Exception as exc:
        user_id = None
        logger.warning(
            "[account_observability] logout_presence_lookup_failed error_class=%s",
            type(exc).__name__,
        )
    get_session_store().revoke(token)
    if user_id:
        try:
            with _auth_db().get_session() as session:
                end_account_presence(session, user_id)
                session.commit()
        except Exception as exc:
            # Logout remains successful; idle expiry is authoritative when the
            # optional observability database write cannot complete.
            logger.warning(
                "[account_observability] logout_presence_end_failed error_class=%s",
                type(exc).__name__,
            )
    return {"ok": True}
