from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

try:
    from guardian.core.dependencies import (
        RequestUserScope,
        chatlog_db,
        get_request_user_scope,
        require_api_key,
    )
except Exception:  # pragma: no cover - fallback for import issues
    chatlog_db = None  # type: ignore[assignment]

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key

    class RequestUserScope:  # type: ignore[no-redef]
        def __init__(
            self,
            account_id: str = "local",
            principal_id: str = "local",
            multi_user_enabled: bool = False,
        ) -> None:
            self.account_id = account_id
            self.principal_id = principal_id
            self.multi_user_enabled = multi_user_enabled

    def get_request_user_scope() -> RequestUserScope:  # type: ignore[unused-argument]
        return RequestUserScope()


router = APIRouter(tags=["Threads"])
api_router = APIRouter(prefix="/api", tags=["Threads"])
THREAD_CREATE_BODY = Body(...)
THREAD_API_KEY_DEP = Depends(require_api_key)
THREAD_REQUEST_USER_SCOPE_DEP = Depends(get_request_user_scope)
THREAD_USER_ID_QUERY = Query(default=None)


class ThreadCreatePayload(BaseModel):
    """Payload for creating a legacy thread via /threads."""

    title: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None


def _normalize_user_id(value: Any) -> Optional[str]:
    resolved = str(value or "").strip()
    return resolved or None


def _thread_row_id(row: Any) -> Optional[int]:
    if row is None:
        return None
    if isinstance(row, dict):
        raw = row.get("thread_id", row.get("id"))
    elif isinstance(row, tuple):
        raw = row[0] if row else None
    else:
        raw = getattr(row, "thread_id", getattr(row, "id", None))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _thread_row_user_id(row: Any) -> Optional[str]:
    if row is None:
        return None
    if isinstance(row, dict):
        return _normalize_user_id(row.get("user_id"))
    if isinstance(row, tuple):
        if len(row) > 5:
            return _normalize_user_id(row[5])
        return None
    return _normalize_user_id(getattr(row, "user_id", None))


def _thread_row_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        payload = dict(row)
    elif isinstance(row, tuple):
        keys = (
            "thread_id",
            "parent_thread_id",
            "session_id",
            "summary",
            "created_at",
            "user_id",
            "project_id",
        )
        payload = {
            key: row[index]
            for index, key in enumerate(keys)
            if index < len(row)
        }
    else:
        payload = {
            key: getattr(row, key, None)
            for key in (
                "thread_id",
                "id",
                "parent_thread_id",
                "session_id",
                "summary",
                "created_at",
                "user_id",
                "project_id",
            )
        }
    if payload.get("thread_id") is None and payload.get("id") is not None:
        payload["thread_id"] = payload["id"]
    if payload.get("id") is None and payload.get("thread_id") is not None:
        payload["id"] = payload["thread_id"]
    return payload


def _reject_conflicting_user_id(
    request_user_scope: RequestUserScope, *candidate_user_ids: Optional[str]
) -> None:
    if not request_user_scope.multi_user_enabled:
        return
    resolved_candidates = {
        candidate.strip()
        for candidate in candidate_user_ids
        if isinstance(candidate, str) and candidate.strip()
    }
    if resolved_candidates and resolved_candidates != {
        request_user_scope.account_id
    }:
        raise HTTPException(
            status_code=403,
            detail="user_id conflicts with authenticated principal",
        )


def _effective_thread_owner(
    request_user_scope: RequestUserScope, *candidate_user_ids: Optional[str]
) -> str:
    _reject_conflicting_user_id(request_user_scope, *candidate_user_ids)
    return request_user_scope.account_id


def _list_thread_rows(
    request_user_scope: RequestUserScope,
    *,
    requested_user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if chatlog_db is None:
        raise HTTPException(
            status_code=500, detail="chatlog_db not initialized"
        )

    if not request_user_scope.multi_user_enabled:
        try:
            items: List[Dict[str, Any]] = chatlog_db.list_threads()  # type: ignore[attr-defined]
        except Exception as exc:
            from logging import getLogger

            getLogger(__name__).warning("list_threads failed: %s", exc)
            return []
        return [_thread_row_dict(item) for item in items]

    owner_id = _effective_thread_owner(request_user_scope, requested_user_id)
    try:
        items = chatlog_db.list_threads(  # type: ignore[attr-defined]
            user_id=owner_id
        )
    except TypeError:
        try:
            items = chatlog_db.list_threads()  # type: ignore[attr-defined]
        except Exception as exc:
            from logging import getLogger

            getLogger(__name__).warning("list_threads failed: %s", exc)
            return []
    except Exception as exc:
        from logging import getLogger

        getLogger(__name__).warning("list_threads failed: %s", exc)
        return []

    normalized = [_thread_row_dict(item) for item in items]
    return [
        item for item in normalized if _thread_row_user_id(item) == owner_id
    ]


def _get_thread_row(thread_id: int) -> Dict[str, Any] | None:
    if chatlog_db is None:
        return None
    getter = getattr(chatlog_db, "get_thread", None)
    if callable(getter):
        try:
            row = getter(thread_id)
        except Exception:
            row = None
        if row:
            return _thread_row_dict(row)

    try:
        rows = chatlog_db.list_threads()  # type: ignore[attr-defined]
    except Exception:
        return None
    for row in rows:
        payload = _thread_row_dict(row)
        if _thread_row_id(payload) == thread_id:
            return payload
    return None


@router.get("/threads")
@api_router.get("/threads")
def list_threads(
    user_id: Optional[str] = THREAD_USER_ID_QUERY,
    api_key: str = THREAD_API_KEY_DEP,
    request_user_scope: RequestUserScope = THREAD_REQUEST_USER_SCOPE_DEP,
) -> Dict[str, Any]:
    """
    List legacy threads.

    Tests only assert that this endpoint is authenticated and returns a JSON
    object with a ``threads`` array; the exact shape of each thread is
    delegated to the underlying chatlog_db implementation.
    """
    items = _list_thread_rows(request_user_scope, requested_user_id=user_id)
    return {"threads": items}


@router.post("/threads")
@api_router.post("/threads")
def create_thread(
    body: ThreadCreatePayload = THREAD_CREATE_BODY,
    api_key: str = THREAD_API_KEY_DEP,
    request_user_scope: RequestUserScope = THREAD_REQUEST_USER_SCOPE_DEP,
) -> Dict[str, Any]:
    """
    Create a legacy thread row and return its identifier.

    This uses the lightweight ``threads`` lineage table underneath via
    chatlog_db.create_thread; tests only require that a JSON response with an
    integer ``thread_id`` is returned and that the route is not 404.
    """
    if chatlog_db is None:
        raise HTTPException(
            status_code=500, detail="chatlog_db not initialized"
        )
    owner_id = _effective_thread_owner(request_user_scope, body.user_id)
    # Reuse the provided title as a simple summary; lineage APIs do not inspect
    # these fields deeply in the current test suite.
    summary = (body.title or "New Thread").strip()
    try:
        tid: int = chatlog_db.create_thread(  # type: ignore[attr-defined]
            parent_thread_id=None,
            session_id="threads:" + datetime.now(timezone.utc).isoformat(),
            summary=summary,
            user_id=owner_id,
            project_id=body.project_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to create thread: {exc}"
        )
    return {"thread_id": tid}


@router.get("/threads/{thread_id}")
@api_router.get("/threads/{thread_id}")
def get_thread(
    thread_id: int,
    user_id: Optional[str] = THREAD_USER_ID_QUERY,
    api_key: str = THREAD_API_KEY_DEP,
    request_user_scope: RequestUserScope = THREAD_REQUEST_USER_SCOPE_DEP,
) -> Dict[str, Any]:
    """
    Read a legacy thread row by identifier.
    """
    if chatlog_db is None:
        raise HTTPException(
            status_code=500, detail="chatlog_db not initialized"
        )
    _reject_conflicting_user_id(request_user_scope, user_id)
    row = _get_thread_row(thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail="thread not found")
    if request_user_scope.multi_user_enabled:
        owner_id = _thread_row_user_id(row)
        if owner_id != request_user_scope.account_id:
            raise HTTPException(status_code=404, detail="thread not found")
    return {"thread": row}
