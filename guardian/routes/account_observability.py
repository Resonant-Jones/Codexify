"""Account observability routes: heartbeat, invite lifecycle, and retention.

This module provides:
- Operator invite CRUD and public invite resolution (Slice 2)
- Foreground presence heartbeat for accounts and guests (Slice 3)
- Retention cleanup trigger (Slice 3)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from guardian.account_observability.contracts import (
    HeartbeatRequest,
    HeartbeatResponse,
    InviteCreateRequest,
    InviteCreateResponse,
    InviteListResponse,
    InviteMetadataResponse,
    InviteResolutionRequest,
    InviteResolutionResponse,
    RetentionCleanupReceipt,
)
from guardian.account_observability.invites import (
    InviteConflictError,
    InviteNotFoundError,
    InviteValidationError,
    create_invite,
    disable_invite,
    invite_fragment,
    invite_metadata,
    list_invites,
    record_invite_audit,
    resolve_invite,
    revoke_invite,
)
from guardian.account_observability.presence import (
    HeartbeatError,
    SubjectResolutionError,
    end_account_presence,
    end_guest_presence,
    record_heartbeat,
)
from guardian.account_observability.retention import run_cleanup
from guardian.account_observability.tokens import (
    ATTRIBUTION_COOKIE_MAX_AGE_SECONDS,
    ATTRIBUTION_COOKIE_NAME,
    PRESENCE_ACTIVE_WINDOW_SECONDS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
    AccountObservabilityInviteAuditAction,
    AccountObservabilityInvitePublicError,
)
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import get_current_user, require_api_key
from guardian.core.request_correlation import normalize_request_id
from guardian.routes.admin import _session_cookie_secure_flag, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Account Observability"])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _db_or_503() -> Any:
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return db


def _request_id(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None)
    normalized, _ = normalize_request_id(
        state_id or request.headers.get("X-Request-ID")
    )
    request.state.request_id = normalized
    return normalized


def _audit_best_effort(
    db: Any,
    *,
    action: str,
    invite_id: str,
    actor_id: str,
    request_id: str,
) -> None:
    try:
        with db.get_session() as audit_session:
            record_invite_audit(
                audit_session,
                action=action,
                invite_id=invite_id,
                actor_id=actor_id,
                request_id=request_id,
            )
            audit_session.commit()
    except Exception as exc:
        logger.warning(
            "[account_observability] audit_write_failed action=%s invite_id=%s"
            " actor_id=%s request_id=%s error_class=%s",
            action,
            invite_id,
            actor_id,
            request_id,
            type(exc).__name__,
        )


def _operator_dependencies(
    api_key: str = Depends(require_api_key),
    access_method: str = Depends(require_admin),
    current_user: str = Depends(get_current_user),
) -> tuple[str, str, str]:
    """Require service auth plus the existing operator/admin boundary."""
    return api_key, access_method, current_user


# ---------------------------------------------------------------------------
# Slice 2: Invite lifecycle routes (operator + public)
# ---------------------------------------------------------------------------


@router.post(
    "/api/operator/account-observability/invites",
    response_model=InviteCreateResponse,
    status_code=201,
)
def create_operator_invite(
    body: InviteCreateRequest,
    request: Request,
    operator: tuple[str, str, str] = Depends(_operator_dependencies),
) -> InviteCreateResponse:
    db = _db_or_503()
    _, _, actor_id = operator
    try:
        with db.get_session() as session:
            row, raw_token = create_invite(
                session,
                created_by_user_id=actor_id,
                name=body.name,
                campaign_label=body.campaign_label,
                placement_label=body.placement_label,
                expires_at=body.expires_at,
            )
            session.commit()
            session.refresh(row)
    except InviteValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InviteConflictError as exc:
        raise HTTPException(status_code=409, detail="Invite creation conflict") from exc

    _audit_best_effort(
        db,
        action=AccountObservabilityInviteAuditAction.CREATED.value,
        invite_id=row.invite_id,
        actor_id=actor_id,
        request_id=_request_id(request),
    )
    return InviteCreateResponse(
        **invite_metadata(row),
        raw_token=raw_token,
        invite_fragment=invite_fragment(raw_token),
    )


@router.get(
    "/api/operator/account-observability/invites",
    response_model=InviteListResponse,
)
def list_operator_invites(
    operator: tuple[str, str, str] = Depends(_operator_dependencies),
) -> InviteListResponse:
    _ = operator
    db = _db_or_503()
    with db.get_session() as session:
        rows = list_invites(session)
        return InviteListResponse(
            invites=[
                InviteMetadataResponse(**invite_metadata(row)) for row in rows
            ]
        )


def _transition_invite(
    invite_id: str,
    request: Request,
    *,
    action: str,
    transition: Any,
    operator: tuple[str, str, str],
) -> InviteMetadataResponse:
    db = _db_or_503()
    _, _, actor_id = operator
    try:
        with db.get_session() as session:
            row = transition(session, invite_id)
            session.commit()
            session.refresh(row)
    except InviteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Invite not found") from exc
    except InviteConflictError as exc:
        raise HTTPException(status_code=409, detail="Invalid invite transition") from exc

    _audit_best_effort(
        db,
        action=action,
        invite_id=row.invite_id,
        actor_id=actor_id,
        request_id=_request_id(request),
    )
    return InviteMetadataResponse(**invite_metadata(row))


@router.post(
    "/api/operator/account-observability/invites/{invite_id}/disable",
    response_model=InviteMetadataResponse,
)
def disable_operator_invite(
    invite_id: str,
    request: Request,
    operator: tuple[str, str, str] = Depends(_operator_dependencies),
) -> InviteMetadataResponse:
    return _transition_invite(
        invite_id,
        request,
        action=AccountObservabilityInviteAuditAction.DISABLED.value,
        transition=disable_invite,
        operator=operator,
    )


@router.post(
    "/api/operator/account-observability/invites/{invite_id}/revoke",
    response_model=InviteMetadataResponse,
)
def revoke_operator_invite(
    invite_id: str,
    request: Request,
    operator: tuple[str, str, str] = Depends(_operator_dependencies),
) -> InviteMetadataResponse:
    return _transition_invite(
        invite_id,
        request,
        action=AccountObservabilityInviteAuditAction.REVOKED.value,
        transition=revoke_invite,
        operator=operator,
    )


@router.post(
    "/api/account-observability/invites/resolve",
    response_model=InviteResolutionResponse,
)
def resolve_public_invite(
    body: InviteResolutionRequest,
    response: Response,
    guest_cookie: str | None = Cookie(default=None, alias=ATTRIBUTION_COOKIE_NAME),
) -> Response | InviteResolutionResponse:
    db = _db_or_503()
    with db.get_session() as session:
        result = resolve_invite(
            session,
            token=body.token,
            guest_cookie=guest_cookie,
        )
        if not result.available:
            return Response(
                content=(
                    '{"error":"'
                    f"{AccountObservabilityInvitePublicError.UNAVAILABLE.value}"
                    '"}'
                ),
                status_code=404,
                media_type="application/json",
            )
        session.commit()

    response.set_cookie(
        ATTRIBUTION_COOKIE_NAME,
        result.guest_id or "",
        max_age=ATTRIBUTION_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_session_cookie_secure_flag(),
        path="/",
    )
    return InviteResolutionResponse(result=result.result)


# ---------------------------------------------------------------------------
# Slice 3: Foreground presence heartbeat
# ---------------------------------------------------------------------------


def _resolve_subject_from_request(
    request: Request,
    gc_session: str | None = Cookie(default=None, alias="gc_session"),
) -> tuple[str | None, str | None]:
    """Resolve account or guest identity from trusted server context.

    Returns (user_id, guest_id) where exactly one is non-None.
    Account identity is resolved via the existing get_current_user dependency.
    Guest identity is resolved via the existing gc_session cookie convention.
    """
    from guardian.core.dependencies import (
        get_request_user_id,
    )

    # Try authenticated account first
    auth_header = request.headers.get("Authorization")
    x_user_id = request.headers.get("X-User-Id")

    try:
        user_id = get_request_user_id(
            request=request,
            x_user_id=x_user_id,
            authorization=auth_header,
            gc_session=gc_session,
        )
        if user_id and user_id.strip() and user_id not in ("local", "system", "service"):
            return user_id.strip(), None
    except Exception:
        pass

    # Try guest identity from gc_session cookie
    if gc_session:
        from guardian.core.dependencies import (
            resolve_session_user_id,
            extract_session_token,
        )
        session_token = extract_session_token(auth_header, gc_session)
        if session_token:
            try:
                guest_user_id = resolve_session_user_id(auth_header, gc_session)
                if guest_user_id and guest_user_id.strip():
                    return None, guest_user_id.strip()
            except Exception:
                pass

        # If gc_session doesn't resolve to a user, treat it as a guest cookie
        # The guest_id is the cookie value itself if it looks like a UUID
        import re
        cookie_val = str(gc_session).strip().strip('"')
        if re.match(r"^[0-9a-fA-F-]{36}$", cookie_val):
            return None, cookie_val

    return None, None


@router.post(
    "/api/account-observability/heartbeat",
    response_model=HeartbeatResponse,
)
def submit_heartbeat(
    body: HeartbeatRequest,
    request: Request,
    gc_session: str | None = Cookie(default=None, alias="gc_session"),
) -> HeartbeatResponse:
    """Accept a foreground presence heartbeat.

    The subject is resolved exclusively from trusted server context:
    - Authenticated accounts via existing auth dependencies.
    - Guests via valid server-issued guest cookie.

    Client-supplied account/guest IDs in the body are rejected (schema forbids them).
    The heartbeat carries no analytics dimensions.
    """
    db = _db_or_503()
    user_id, guest_id = _resolve_subject_from_request(request, gc_session)

    if not user_id and not guest_id:
        raise HTTPException(
            status_code=401,
            detail="authenticated account or valid guest identity required",
        )
    if user_id and guest_id:
        raise HTTPException(
            status_code=422,
            detail="ambiguous subject: cannot heartbeat as both account and guest",
        )

    try:
        with db.get_session() as session:
            result = record_heartbeat(
                session,
                user_id=user_id,
                guest_id=guest_id,
            )
            session.commit()
    except SubjectResolutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HeartbeatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return HeartbeatResponse(
        active=result.active,
        active_window_seconds=result.active_window_seconds,
        idle_expiry_seconds=result.idle_expiry_seconds,
        server_time=result.server_time,
    )


# ---------------------------------------------------------------------------
# Slice 3: Retention cleanup trigger (operator-only, dry-run-capable)
# ---------------------------------------------------------------------------


@router.post(
    "/api/operator/account-observability/retention/cleanup",
    response_model=RetentionCleanupReceipt,
)
def trigger_retention_cleanup(
    request: Request,
    dry_run: bool = False,
    operator: tuple[str, str, str] = Depends(_operator_dependencies),
) -> RetentionCleanupReceipt:
    """Trigger deterministic retention cleanup.

    Requires operator authentication (API key + admin session).
    Supports dry_run=True for inspection without mutation.
    """
    _ = operator
    db = _db_or_503()
    try:
        with db.get_session() as session:
            receipt = run_cleanup(session, dry_run=dry_run)
            if not dry_run:
                session.commit()
    except Exception as exc:
        logger.exception("[retention] cleanup failed")
        raise HTTPException(
            status_code=500,
            detail=f"Retention cleanup failed: {exc}",
        ) from exc

    return RetentionCleanupReceipt(
        execution_timestamp=receipt.execution_timestamp,
        cutoff_presence_30d=receipt.cutoff_presence_30d,
        cutoff_idle_30m=receipt.cutoff_idle_30m,
        cutoff_guest_lineage_90d=receipt.cutoff_guest_lineage_90d,
        expired_session_count=receipt.expired_session_count,
        deleted_presence_count=receipt.deleted_presence_count,
        deleted_guest_count=receipt.deleted_guest_count,
        deferred_guest_count=receipt.deferred_guest_count,
        deferred_guest_reason=receipt.deferred_guest_reason,
        dry_run=receipt.dry_run,
    )


__all__ = ["router"]
