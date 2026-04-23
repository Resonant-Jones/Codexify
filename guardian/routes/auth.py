"""Authentication routes for session-backed login."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Cookie, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from guardian.core.auth import issue_session_token
from guardian.core.db import load_guardian_db_from_env
from guardian.core.passwords import hash_password, verify_password
from guardian.core.session_store import (
    DEFAULT_SESSION_TTL_SECONDS,
    get_session_store,
)
from guardian.db.models import User

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


@router.post("/register")
@api_router.post("/register")
def register_user(body: AuthRegisterRequest) -> dict[str, Any]:
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

    db = _auth_db()
    with db.get_session() as session:
        user = _get_user_by_username(session, username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password",
            )

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
    get_session_store().revoke(token)
    return {"ok": True}
