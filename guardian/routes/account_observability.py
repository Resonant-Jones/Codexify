"""Guardian-owned foreground presence and retention routes."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request

from guardian.account_observability.presence import (
    HeartbeatError,
    SubjectResolutionError,
    record_heartbeat,
)
from guardian.account_observability.retention import run_cleanup
from guardian.account_observability.schemas import (
    HeartbeatRequest,
    HeartbeatResponse,
    RetentionCleanupReceipt,
)
from guardian.account_observability.tokens import GUEST_ID_COOKIE_NAME
from guardian.core.auth_dependencies import (
    extract_session_token,
    resolve_session_user_id,
)
from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.dependencies import (
    get_current_user,
    get_request_user_id,
    require_api_key,
    verify_api_key,
)
from guardian.routes.admin import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Account Observability"])
_db: GuardianDB | None = None


def configure_db(db: GuardianDB) -> None:
    """Bind the application GuardianDB using the existing router convention."""

    global _db
    _db = db


def _get_db() -> GuardianDB:
    if _db is not None:
        return _db
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return db


def _guest_cookie_id(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    try:
        return str(UUID(candidate))
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail="Invalid guest identity"
        ) from exc


def _resolve_subject(
    request: Request,
    *,
    authorization: str | None,
    gc_session: str | None,
    x_api_key: str | None,
    guest_id_cookie: str | None,
) -> tuple[str | None, str | None]:
    """Resolve one trusted account or server-issued guest identity."""

    guest_id = _guest_cookie_id(guest_id_cookie)
    session_token = extract_session_token(authorization, gc_session)
    if session_token:
        account_id = resolve_session_user_id(authorization, gc_session)
        if not account_id:
            raise HTTPException(
                status_code=401, detail="Invalid or expired session"
            )
        if guest_id is not None:
            raise HTTPException(
                status_code=422, detail="Ambiguous presence subject"
            )
        return account_id, None

    if x_api_key:
        verify_api_key(
            request=request,
            x_api_key=x_api_key,
            authorization=authorization,
            gc_session=gc_session,
        )
        account_id = get_request_user_id(
            request=request,
            authorization=authorization,
            gc_session=gc_session,
        )
        if guest_id is not None:
            raise HTTPException(
                status_code=422, detail="Ambiguous presence subject"
            )
        return account_id, None

    if guest_id is not None:
        return None, guest_id
    raise HTTPException(
        status_code=401,
        detail="Authenticated account or valid guest identity required",
    )


@router.post(
    "/api/account-observability/heartbeat",
    response_model=HeartbeatResponse,
)
def heartbeat(
    _body: HeartbeatRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    gc_session: str | None = Cookie(default=None, alias="gc_session"),
    guest_id_cookie: str
    | None = Cookie(default=None, alias=GUEST_ID_COOKIE_NAME),
) -> HeartbeatResponse:
    """Accept one explicit foreground heartbeat; other traffic implies nothing."""

    user_id, guest_id = _resolve_subject(
        request,
        authorization=authorization,
        gc_session=gc_session,
        x_api_key=x_api_key,
        guest_id_cookie=guest_id_cookie,
    )
    db = _get_db()
    try:
        with db.get_session() as session:
            result = record_heartbeat(
                session, user_id=user_id, guest_id=guest_id
            )
            session.commit()
    except SubjectResolutionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except HeartbeatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return HeartbeatResponse(
        active=result.active,
        active_window_seconds=result.active_window_seconds,
        idle_expiry_seconds=result.idle_expiry_seconds,
        server_time=result.server_time,
    )


def _operator_dependencies(
    _api_key: str = Depends(require_api_key),
    _admin: str = Depends(require_admin),
    _current_user: str = Depends(get_current_user),
) -> None:
    return None


@router.post(
    "/api/operator/account-observability/retention/cleanup",
    response_model=RetentionCleanupReceipt,
)
def retention_cleanup(
    _operator: None = Depends(_operator_dependencies),
) -> RetentionCleanupReceipt:
    """Run deterministic cleanup through the explicit operator seam."""

    db = _get_db()
    try:
        with db.get_session() as session:
            receipt = run_cleanup(session)
            session.commit()
    except Exception as exc:
        logger.exception("[account_observability] retention cleanup failed")
        raise HTTPException(
            status_code=500, detail="Retention cleanup failed"
        ) from exc

    return RetentionCleanupReceipt(**receipt.as_dict())


__all__ = ["configure_db", "heartbeat", "retention_cleanup", "router"]
