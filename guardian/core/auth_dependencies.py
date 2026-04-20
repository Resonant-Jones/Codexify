"""Session-backed request identity helpers."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from guardian.core.session_store import get_session_store


def extract_session_token(
    authorization: str | None = None,
    gc_session: str | None = None,
) -> str | None:
    if not isinstance(authorization, str):
        authorization = None
    if not isinstance(gc_session, str):
        gc_session = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    if gc_session:
        token = gc_session.strip()
        if token:
            return token
    return None


def resolve_session_user_id(
    authorization: str | None = None,
    gc_session: str | None = None,
) -> str | None:
    token = extract_session_token(authorization, gc_session)
    if not token:
        return None
    return get_session_store().verify(token)


def get_current_user_id(request: Request) -> str:
    token = extract_session_token(
        request.headers.get("Authorization"),
        request.cookies.get("gc_session"),
    )
    if token:
        user_id = get_session_store().verify(token)
        if user_id:
            return user_id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    from guardian.core.dependencies import get_single_user_id

    return get_single_user_id()
