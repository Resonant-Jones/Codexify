"""
Admin Routes
~~~~~~~~~~~~

Diagnostic and administrative endpoints including health checks,
session token management, and configuration debugging.

Admin-protected endpoints require:
- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN
- Optional local debug bypass with explicit dev-mode opt-in
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.auth import issue_session_token, verify_session_token
    from guardian.core.dependencies import (
        DB_BACKEND,
        GUARDIAN_PROVIDER,
        PG_DSN,
        _mask_dsn,
        allowed_origins,
        chatlog_db,
        get_current_user,
        get_database_dsn,
        get_groq_chat,
        require_api_key,
    )
except ImportError as e:
    logger.warning(f"[admin] Import warning: {e}")
    chatlog_db = None
    require_api_key = lambda x: x
    issue_session_token = None
    PG_DSN = None
    DB_BACKEND = "postgres"
    GUARDIAN_PROVIDER = "unknown"
    _mask_dsn = lambda value: value
    get_current_user = lambda: "local"
    allowed_origins = []
    get_groq_chat = lambda: None
    get_database_dsn = lambda: None


class SessionRequest(BaseModel):
    ttl_seconds: int | None = None


class CapabilityIssueRequest(BaseModel):
    actions: list[str]
    namespace: str | None = None
    resource: str | None = None
    ttl_seconds: int = 300
    max_calls: int = 5


TRUE_VALUES = {"true", "1", "yes", "on"}
LOCAL_AUTH_MODES = {"", "local", "localhost", "loopback"}
REMOTE_AUTH_MODES = {
    "remote",
    "cloud",
    "hosted",
    "public",
    "prod",
    "production",
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUE_VALUES


def _is_local_auth_boundary() -> bool:
    exposure_mode = (
        (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
    )
    if exposure_mode == "public_allowlist":
        return False

    auth_mode = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
    if auth_mode in REMOTE_AUTH_MODES:
        return False
    if auth_mode in LOCAL_AUTH_MODES:
        return True

    logger.warning(
        "[admin] Unknown GUARDIAN_AUTH_MODE=%r; treating as remote for safety",
        auth_mode,
    )
    return False


def _debug_admin_bypass_enabled() -> bool:
    # DEBUG bypass is only allowed inside the local auth boundary.
    return _env_bool("DEBUG", default=False) and _is_local_auth_boundary()


def _session_cookie_secure_flag() -> bool:
    # Secure by default. Local HTTP cookies are only allowed with explicit
    # dev mode opt-in inside the local auth boundary.
    if _is_local_auth_boundary() and _env_bool(
        "GUARDIAN_DEV_MODE", default=False
    ):
        return False
    return True


def require_admin(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Enforce admin-level access control for sensitive diagnostic endpoints.

    Access is granted if ANY of the following conditions are met:
    1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
    2. Local debug bypass is enabled via env: DEBUG=true inside the local auth boundary
    3. Future: User role verification (when RBAC is fully implemented)

    Args:
        x_admin_token: Admin token from X-Admin-Token header
        x_api_key: Regular API key (for context/logging)

    Returns:
        str: Access method used ("admin_token", "debug_local_opt_in")

    Raises:
        HTTPException: 403 if access is denied

    Logs:
        - Info: Successful admin access with method used
        - Warning: Failed admin access attempts
    """
    admin_token = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
    debug_mode = _env_bool("DEBUG", default=False)
    dev_mode = _env_bool("GUARDIAN_DEV_MODE", default=False)
    local_auth_boundary = _is_local_auth_boundary()

    # Method 1: Check X-Admin-Token header.
    if x_admin_token and admin_token:
        if secrets.compare_digest(x_admin_token, admin_token):
            logger.info(
                "[admin] Admin access granted via X-Admin-Token (token=%s...)",
                x_admin_token[:8] if len(x_admin_token) > 8 else "short",
            )
            return "admin_token"

    # Method 2: Local DEBUG bypass (local boundary only).
    if _debug_admin_bypass_enabled():
        logger.info(
            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
            x_api_key[:8] + "..."
            if x_api_key and len(x_api_key) > 8
            else "none",
        )
        return "debug_mode"

    # Method 3: Future - User role verification
    # if user_role == "admin":
    #     return "user_role"

    # Access denied - log the attempt
    logger.warning(
        "[admin] Admin access DENIED "
        "(admin_token_configured=%s, admin_token_provided=%s, debug_mode=%s, "
        "dev_mode=%s, local_boundary=%s, api_key=%s)",
        bool(admin_token),
        bool(x_admin_token),
        debug_mode,
        dev_mode,
        local_auth_boundary,
        x_api_key[:8] + "..." if x_api_key and len(x_api_key) > 8 else "none",
    )

    raise HTTPException(
        status_code=403,
        detail={
            "error": "Admin access required",
            "message": "This endpoint requires admin privileges. "
            "Provide X-Admin-Token or enable local debug opt-in "
            "(DEBUG + GUARDIAN_DEV_MODE in local auth mode).",
            "required": "X-Admin-Token header (preferred) or explicit local debug opt-in",
        },
    )


router = APIRouter(tags=["Admin"])


# =========================
# Health & Ping Endpoints
# =========================


@router.get("/ping", summary="Health check endpoint")
def ping():
    """Simple health check endpoint to verify that the Guardian API is awake."""
    logger.debug("Ping request received")
    return {"status": "Guardian awake!"}


@router.get("/healthz", summary="DB health and table existence")
def healthz():
    """
    Returns DB target and existence of projects/chat_threads for quick diagnostics.
    """
    db_target = get_database_dsn()
    db_target_masked = _mask_dsn(db_target) if db_target else None
    projects_exists = False
    threads_exists = False
    try:
        projects_exists = chatlog_db.table_exists("projects")
        threads_exists = chatlog_db.table_exists("chat_threads")
    except Exception as e:
        logger.warning("/healthz check failed: %s", e)
    return {
        "db_target": db_target_masked,
        "backend": DB_BACKEND,
        "projects_table_exists": projects_exists,
        "chat_threads_table_exists": threads_exists,
    }


# =========================
# Session Token Management
# =========================


@router.post(
    "/auth/session",
    tags=["Auth"],
    summary="Exchange API key for a short-lived session token",
)
def create_session(
    body: SessionRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Exchange API key for a short-lived JWT session token.

    Args:
        body: Request with optional TTL override
        x_api_key: API key from X-API-Key header

    Returns:
        Session token and expiration timestamp
    """
    expected = os.getenv("GUARDIAN_API_KEY") or ""
    if not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(
            status_code=401, detail="API key required to mint session"
        )
    token, exp = issue_session_token(
        subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600
    )
    return {"token": token, "expires": exp}


@router.post(
    "/auth/session/cookie",
    tags=["Auth"],
    summary="Mint a session token and set it as an HttpOnly cookie",
)
def create_session_cookie(
    response: Response,
    body: SessionRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Exchange API key for a session token and set it as an HttpOnly cookie.

    Args:
        response: FastAPI response object for cookie setting
        body: Request with optional TTL override
        x_api_key: API key from X-API-Key header

    Returns:
        Success status and expiration timestamp
    """
    expected = os.getenv("GUARDIAN_API_KEY") or ""
    if not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(
            status_code=401, detail="API key required to mint session"
        )
    token, exp = issue_session_token(
        subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600
    )
    max_age = body.ttl_seconds or 24 * 3600
    secure_cookie = _session_cookie_secure_flag()
    response.set_cookie(
        "gc_session",
        token,
        max_age=max_age,
        httponly=True,
        samesite="Lax",
        secure=secure_cookie,
    )
    return {"ok": True, "expires": exp}


@router.post(
    "/api/capabilities/issue",
    tags=["Auth"],
    summary="Issue short-lived capability grants for local flows",
)
def issue_capabilities(
    body: CapabilityIssueRequest,
    api_key: str = Depends(require_api_key),
    current_user: str = Depends(get_current_user),
):
    """
    Issue in-memory capability grants for authenticated local flows.

    TODO: Replace in-memory grant storage with persistent encrypted storage.
    """
    _ = api_key
    actions = [a.strip() for a in (body.actions or []) if (a or "").strip()]
    if not actions:
        raise HTTPException(status_code=422, detail="actions must be non-empty")
    if body.ttl_seconds <= 0:
        raise HTTPException(status_code=422, detail="ttl_seconds must be > 0")
    if body.max_calls <= 0:
        raise HTTPException(status_code=422, detail="max_calls must be > 0")

    normalized_user = (current_user or "local").strip().lower() or "local"
    owner_namespace = f"user:{normalized_user}"
    namespace = (body.namespace or owner_namespace).strip() or owner_namespace
    if namespace != owner_namespace:
        raise HTTPException(
            status_code=403,
            detail="namespace must match authenticated user namespace",
        )

    resource = (body.resource or f"ns:{namespace}").strip()
    if not resource.startswith(f"ns:{namespace}"):
        raise HTTPException(
            status_code=403,
            detail="resource must stay inside authenticated namespace",
        )

    from guardian.routes import codexify_router

    grants: list[dict[str, object]] = []
    for action in actions:
        token = secrets.token_urlsafe(24)
        codexify_router.register_capability_grant(
            token,
            action=action,
            resource=resource,
            ttl_seconds=body.ttl_seconds,
            max_calls=body.max_calls,
        )
        grants.append(
            {
                "action": action,
                "token": token,
                "resource": resource,
                "ttl_seconds": body.ttl_seconds,
                "max_calls": body.max_calls,
            }
        )

    return {"namespace": namespace, "grants": grants}


# =========================
# Diagnostic Endpoints
# =========================


@router.get(
    "/authz/debug",
    tags=["Diag"],
    summary="Echo masked API key received in header (admin-only)",
)
def authz_debug(
    access_method: str = Depends(require_admin),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Return the masked API key received via X-API-Key, masked for safety.
    This endpoint requires admin privileges.
    """
    key = x_api_key or ""
    masked = (key[:4] + "…" + key[-4:]) if len(key) > 8 else key
    return {"received_api_key": masked}


@router.get(
    "/debug/config",
    tags=["Diag"],
    summary="Return masked config for debugging (admin-only)",
)
def debug_config(access_method: str = Depends(require_admin)):
    """
    Return a small, masked snapshot of runtime config useful for local debugging.
    This endpoint requires admin privileges.
    """
    env = os.getenv("GUARDIAN_ENV", "development")
    api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
    masked_key = (
        (api_key[:4] + "…" + api_key[-4:])
        if api_key and len(api_key) > 8
        else api_key
    )
    db_target = PG_DSN
    return {
        "env": env,
        "db_target": db_target,
        "db_backend": DB_BACKEND,
        "provider": GUARDIAN_PROVIDER,
        "allowed_origins": allowed_origins,
        "masked_api_key": masked_key,
        "groq_available": bool(get_groq_chat()),
    }
