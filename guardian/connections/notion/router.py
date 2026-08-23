"""Provider-specific setup and read routes for the Notion connection."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from guardian.connections.notion import credentials
from guardian.connections.notion.service import (
    NotionAuthorizationError,
    NotionClient,
    NotionError,
    NotionNotConfiguredError,
    NotionObjectNotFoundError,
    NotionTransportError,
)
from guardian.core.dependencies import get_request_user_id, require_api_key

setup_router = APIRouter(
    prefix="/api/connect/notion",
    tags=["Notion Connection"],
    dependencies=[Depends(require_api_key)],
)
operations_router = APIRouter(
    prefix="/api/knowledge/notion",
    tags=["Notion Knowledge"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None
_OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F-]{32,36}$")


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
    if db is None or not hasattr(db, "get_session"):
        raise HTTPException(
            status_code=503, detail={"error": "notion_connection_storage_unavailable"}
        )
    return db


class NotionConfigureRequest(BaseModel):
    settings: dict[str, str] = Field(default_factory=dict)


def _validation_http_error(exc: NotionError) -> HTTPException:
    if isinstance(exc, NotionAuthorizationError):
        return HTTPException(
            status_code=401, detail={"error": exc.error_code}
        )
    if isinstance(exc, NotionTransportError):
        return HTTPException(
            status_code=503, detail={"error": exc.error_code}
        )
    return HTTPException(status_code=502, detail={"error": exc.error_code})


def _configured_client(db: Any, user_id: str) -> NotionClient:
    token = credentials.configured_token(db, user_id)
    if not token:
        raise NotionNotConfiguredError("No Notion credential is configured")
    return NotionClient(token)


def _safe_status(db: Any, user_id: str) -> dict[str, Any]:
    return {
        "connection_id": "notion",
        "validation": credentials.status_projection(db, user_id),
    }


@setup_router.post("/configure")
def configure_notion(
    payload: NotionConfigureRequest,
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    token = str(payload.settings.get("integration_token") or "").strip()
    if not token or len(token) > 4096:
        raise HTTPException(
            status_code=422,
            detail={"error": "notion_integration_token_required"},
        )
    db = _get_db()
    credentials.configure_token(db, user_id, token)
    return _safe_status(db, user_id)


@setup_router.post("/validate")
def validate_notion(
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    db = _get_db()
    try:
        _configured_client(db, user_id).validate()
    except NotionNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail={"error": exc.error_code}) from exc
    except NotionAuthorizationError as exc:
        credentials.mark_validation(
            db, user_id, credentials.VALIDATION_AUTHORIZATION_ERROR
        )
        raise _validation_http_error(exc) from exc
    except NotionTransportError as exc:
        credentials.mark_validation(
            db, user_id, credentials.VALIDATION_TRANSPORT_ERROR
        )
        raise _validation_http_error(exc) from exc
    except NotionError as exc:
        credentials.mark_validation(db, user_id, credentials.VALIDATION_PROVIDER_ERROR)
        raise _validation_http_error(exc) from exc
    credentials.mark_validation(db, user_id, credentials.VALIDATION_VALID)
    return _safe_status(db, user_id)


@setup_router.get("/status")
def notion_status(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    return _safe_status(_get_db(), user_id)


@setup_router.post("/disconnect")
def disconnect_notion(user_id: str = Depends(get_request_user_id)) -> dict[str, Any]:
    removed = credentials.disconnect(_get_db(), user_id)
    return {"connection_id": "notion", "removed": removed}


def _valid_object_id(object_id: str) -> str:
    candidate = str(object_id or "").strip()
    if not _OBJECT_ID_RE.fullmatch(candidate):
        raise HTTPException(status_code=422, detail={"error": "invalid_notion_object_id"})
    return candidate


@operations_router.get("/search", operation_id="notion_content_search")
def notion_content_search(
    query: str = Query(min_length=1, max_length=500),
    cursor: str | None = Query(default=None, max_length=1024),
    limit: int = Query(default=25, ge=1, le=50),
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise HTTPException(
            status_code=422, detail={"error": "notion_search_query_required"}
        )
    db = _get_db()
    try:
        return _configured_client(db, user_id).search(
            query=query, cursor=cursor, limit=limit
        )
    except NotionNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail={"error": exc.error_code}) from exc
    except NotionError as exc:
        raise _validation_http_error(exc) from exc


@operations_router.get("/read/{object_id}", operation_id="notion_content_read")
def notion_content_read(
    object_id: str,
    user_id: str = Depends(get_request_user_id),
) -> dict[str, Any]:
    object_id = _valid_object_id(object_id)
    db = _get_db()
    try:
        return _configured_client(db, user_id).read_page(object_id)
    except NotionNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail={"error": exc.error_code}) from exc
    except NotionObjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": exc.error_code}) from exc
    except NotionError as exc:
        raise _validation_http_error(exc) from exc
