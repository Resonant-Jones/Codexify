"""
Admin Routes
~~~~~~~~~~~~

Diagnostic and administrative endpoints including health checks,
session token management, and configuration debugging.

Admin-protected endpoints require:
- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
- DEBUG=true environment variable (development only)
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
        API_KEY,
        DB_BACKEND,
        GUARDIAN_PROVIDER,
        PG_DSN,
        allowed_origins,
        chatlog_db,
        get_database_dsn,
        get_groq_chat,
        require_api_key,
    )
except ImportError as e:
    logger.warning(f"[admin] Import warning: {e}")
    chatlog_db = None
    require_api_key = lambda x: x
    issue_session_token = None
    API_KEY = None
    PG_DSN = None
    DB_BACKEND = "postgres"
    GUARDIAN_PROVIDER = "unknown"
    allowed_origins = []
    get_groq_chat = lambda: None
    get_database_dsn = lambda: None


class SessionRequest(BaseModel):
    ttl_seconds: int | None = None


# Admin token from environment (optional, for stricter access control)
ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def require_admin(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Enforce admin-level access control for sensitive diagnostic endpoints.

    Access is granted if ANY of the following conditions are met:
    1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
    2. DEBUG=true environment variable is set (development only)
    3. Future: User role verification (when RBAC is fully implemented)

    Args:
        x_admin_token: Admin token from X-Admin-Token header
        x_api_key: Regular API key (for context/logging)

    Returns:
        str: Access method used ("admin_token", "debug_mode")

    Raises:
        HTTPException: 403 if access is denied

    Logs:
        - Info: Successful admin access with method used
        - Warning: Failed admin access attempts
    """
    # Method 1: Check X-Admin-Token header
    if x_admin_token and ADMIN_TOKEN:
        if secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
            logger.info(
                "[admin] Admin access granted via X-Admin-Token (token=%s...)",
                x_admin_token[:8] if len(x_admin_token) > 8 else "short",
            )
            return "admin_token"

    # Method 2: Check DEBUG mode (development only)
    if DEBUG_MODE:
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
        "[admin] Admin access DENIED - missing admin token or debug mode "
        "(admin_token_provided=%s, debug_mode=%s, api_key=%s)",
        bool(x_admin_token),
        DEBUG_MODE,
        x_api_key[:8] + "..." if x_api_key and len(x_api_key) > 8 else "none",
    )

    raise HTTPException(
        status_code=403,
        detail={
            "error": "Admin access required",
            "message": "This endpoint requires admin privileges. "
            "Provide X-Admin-Token header or enable DEBUG mode.",
            "required": "X-Admin-Token header or DEBUG=true environment",
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
    projects_exists = False
    threads_exists = False
    try:
        projects_exists = chatlog_db.table_exists("projects")
        threads_exists = chatlog_db.table_exists("chat_threads")
    except Exception as e:
        logger.warning("/healthz check failed: %s", e)
    return {
        "db_target": db_target,
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
    # NOTE: set secure=True when serving over HTTPS
    response.set_cookie(
        "gc_session",
        token,
        max_age=max_age,
        httponly=True,
        samesite="Lax",
        secure=False,
    )
    return {"ok": True, "expires": exp}


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
    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
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
    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
    """
    env = os.getenv("GUARDIAN_ENV", "development")
    masked_key = (
        (API_KEY[:4] + "…" + API_KEY[-4:])
        if API_KEY and len(API_KEY) > 8
        else API_KEY
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
