"""Provider-specific OAuth setup and read routes for Google Drive / Docs."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from guardian.connections.google_drive import oauth
from guardian.connections.google_drive.service import (
    GoogleDriveAuthorizationError,
    GoogleDriveClient,
    GoogleDriveError,
    GoogleDriveObjectNotFoundError,
    GoogleDriveTransportError,
    GoogleDriveUnsupportedObjectError,
)
from guardian.core.dependencies import get_request_user_id, require_api_key

setup_router = APIRouter(prefix="/api/connect/google-drive", tags=["Google Drive Connection"])
operations_router = APIRouter(
    prefix="/api/knowledge/google-drive",
    tags=["Google Drive Knowledge"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None
_OBJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def configure_db(db: Any | None) -> None:
    global _db
    _db = db


def _get_db() -> Any:
    if _db is not None:
        return _db
    try:
        from guardian.core import dependencies as core_dependencies

        db = getattr(core_dependencies, "chatlog_db", None)
    except Exception:  # pragma: no cover - defensive import path
        db = None
    if db is None or not hasattr(db, "get_oauth_connection"):
        raise HTTPException(
            status_code=503, detail={"error": "google_drive_connection_storage_unavailable"}
        )
    return db


def _oauth_http_error(exc: oauth.GoogleDriveOAuthError) -> HTTPException:
    status_code = 401 if isinstance(exc, oauth.GoogleDriveOAuthAuthorizationError) else 503
    if isinstance(exc, oauth.GoogleDriveOAuthStateError):
        status_code = 400
    if isinstance(exc, oauth.GoogleDriveOAuthProviderError):
        status_code = 502
    if isinstance(exc, oauth.GoogleDriveOAuthConfigurationError):
        status_code = 503
    return HTTPException(status_code=status_code, detail={"error": exc.error_code})


def _provider_http_error(exc: GoogleDriveError) -> HTTPException:
    if isinstance(exc, GoogleDriveObjectNotFoundError):
        return HTTPException(status_code=404, detail={"error": exc.error_code})
    if isinstance(exc, GoogleDriveUnsupportedObjectError):
        return HTTPException(status_code=422, detail={"error": exc.error_code})
    if isinstance(exc, GoogleDriveAuthorizationError):
        return HTTPException(status_code=401, detail={"error": exc.error_code})
    if isinstance(exc, GoogleDriveTransportError):
        return HTTPException(status_code=503, detail={"error": exc.error_code})
    return HTTPException(status_code=502, detail={"error": exc.error_code})


def _client_for_user(db: Any, user_id: str) -> GoogleDriveClient:
    try:
        access_token = oauth.access_token_for_user(db, user_id)
    except oauth.GoogleDriveOAuthError as exc:
        raise _oauth_http_error(exc) from exc
    if not access_token:
        raise HTTPException(status_code=409, detail={"error": "google_drive_not_configured"})
    return GoogleDriveClient(access_token)


def _validate(db: Any, user_id: str) -> dict[str, Any]:
    try:
        _client_for_user(db, user_id).validate()
    except HTTPException as exc:
        error = (exc.detail or {}).get("error") if isinstance(exc.detail, dict) else ""
        if isinstance(error, str) and error.startswith("google_drive_"):
            oauth.mark_connection_error(db, user_id, error)
        raise
    except GoogleDriveError as exc:
        oauth.mark_connection_error(db, user_id, exc.error_code)
        raise _provider_http_error(exc) from exc
    oauth.mark_connection_valid(db, user_id)
    return oauth.safe_status(db, user_id)


@setup_router.post("/start", dependencies=[Depends(require_api_key)])
def start_google_drive_oauth(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    """Start a server-generated, browser-mediated OAuth authorization flow."""
    db = _get_db()
    try:
        return oauth.begin_oauth(db, user_id)
    except oauth.GoogleDriveOAuthError as exc:
        raise _oauth_http_error(exc) from exc


@setup_router.get("/callback")
def google_drive_oauth_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Complete Google callback server-side; Google cannot carry our API key."""
    db = _get_db()
    try:
        user_id = oauth.complete_oauth(db, state=state, code=code, error=error)
    except oauth.GoogleDriveOAuthError as exc:
        raise _oauth_http_error(exc) from exc
    status = _validate(db, user_id)
    return {"ok": True, "connection_id": "google_drive", "status": status}


@setup_router.get("/status", dependencies=[Depends(require_api_key)])
def google_drive_status(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    return oauth.safe_status(_get_db(), user_id)


@setup_router.post("/validate", dependencies=[Depends(require_api_key)])
def validate_google_drive(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    return _validate(_get_db(), user_id)


@setup_router.post("/disconnect", dependencies=[Depends(require_api_key)])
def disconnect_google_drive(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    removed = oauth.disconnect(_get_db(), user_id)
    return {"connection_id": "google_drive", "removed": removed}


def _valid_object_id(object_id: str) -> str:
    candidate = str(object_id or "").strip()
    if not _OBJECT_ID_RE.fullmatch(candidate):
        raise HTTPException(status_code=422, detail={"error": "invalid_google_drive_object_id"})
    return candidate


@operations_router.get("/search", operation_id="google_drive_content_search")
def google_drive_content_search(
    query: str = Query(min_length=1, max_length=500),
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=25, ge=1, le=50),
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise HTTPException(status_code=422, detail={"error": "google_drive_search_query_required"})
    db = _get_db()
    try:
        return _client_for_user(db, user_id).search(query=query, cursor=cursor, limit=limit)
    except HTTPException:
        raise
    except GoogleDriveError as exc:
        oauth.mark_connection_error(db, user_id, exc.error_code)
        raise _provider_http_error(exc) from exc


@operations_router.get("/read/{object_id}", operation_id="google_drive_content_read")
def google_drive_content_read(
    object_id: str,
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    object_id = _valid_object_id(object_id)
    db = _get_db()
    try:
        return _client_for_user(db, user_id).read_document(object_id)
    except HTTPException:
        raise
    except GoogleDriveError as exc:
        oauth.mark_connection_error(db, user_id, exc.error_code)
        raise _provider_http_error(exc) from exc
