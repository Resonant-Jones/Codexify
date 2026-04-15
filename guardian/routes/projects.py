"""
Projects Routes
~~~~~~~~~~~~~~~

Project creation and management endpoints.
Includes default "General" project initialization.
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from guardian.core.default_project import (
    DEFAULT_PROJECT_NAME,
    canonicalize_default_project,
    is_default_project_name,
    normalize_projects_for_listing,
)

logger = logging.getLogger(__name__)

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import (
        RequestUserScope,
        chatlog_db,
        get_request_user_scope,
        get_single_user_id,
        require_api_key,
    )
except ImportError:
    chatlog_db = None
    RequestUserScope = object  # type: ignore[assignment]

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key

    def get_request_user_scope():  # type: ignore[unused-argument]
        return None

    def get_single_user_id() -> str:  # type: ignore[unused-argument]
        return "local"


# Helper: ensure default project exists at startup
def ensure_loose_threads_project():
    """
    Ensure the default 'General' project exists for threads without a specified project.
    This function should be called during application startup, not at import time.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the canonical default project exists (named "General" via DEFAULT_PROJECT_NAME)
        project_id = canonicalize_default_project(chatlog_db, logger=logger)
        if project_id is None:
            logger.warning("[projects] Failed to resolve default project")
            return False
        logger.info(
            "[projects] Ensured default project '%s' (id=%s) exists",
            DEFAULT_PROJECT_NAME,
            project_id,
        )
        return True
    except Exception as e:
        logger.warning("[projects] Failed to ensure default project: %s", e)
        return False


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    user_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


_PROJECT_OWNER_SENTINEL = "__codexify_project_owner__"


def _request_account_id(request_user_scope: RequestUserScope) -> str:
    account_id = str(
        getattr(request_user_scope, "account_id", "") or ""
    ).strip()
    return account_id or get_single_user_id()


def _resolve_project_owner_hint(
    raw_user_id: str | None,
    request_user_scope: RequestUserScope,
) -> str:
    requested_user_id = str(raw_user_id or "").strip()
    account_id = _request_account_id(request_user_scope)
    if getattr(request_user_scope, "multi_user_enabled", False):
        if requested_user_id and requested_user_id != account_id:
            raise HTTPException(
                status_code=403,
                detail="Requested user_id does not match the authenticated account",
            )
        return account_id
    return requested_user_id or account_id


def _encode_project_description(description: str | None, owner_id: str) -> str:
    return json.dumps(
        {
            _PROJECT_OWNER_SENTINEL: True,
            "owner_user_id": owner_id,
            "description": (description or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _decode_project_description(description: Any) -> tuple[str | None, str]:
    text = str(description or "")
    if not text:
        return None, ""

    try:
        payload = json.loads(text)
    except Exception:
        return None, text

    if not isinstance(payload, dict) or not payload.get(
        _PROJECT_OWNER_SENTINEL
    ):
        return None, text

    owner_id = str(payload.get("owner_user_id") or "").strip() or None
    decoded_description = str(payload.get("description") or "")
    return owner_id, decoded_description


def _normalize_project_row(project: Any) -> dict[str, Any]:
    row = dict(project or {})
    owner_id = str(row.get("owner_user_id") or row.get("user_id") or "").strip()
    decoded_owner_id, description = _decode_project_description(
        row.get("description")
    )
    if decoded_owner_id:
        owner_id = decoded_owner_id
    if owner_id:
        row["description"] = description
        row["owner_user_id"] = owner_id
    return row


def _project_is_visible_to_scope(
    project: Any,
    request_user_scope: RequestUserScope,
) -> bool:
    if not getattr(request_user_scope, "multi_user_enabled", False):
        return True

    account_id = _request_account_id(request_user_scope)
    row = _normalize_project_row(project)
    owner_id = str(row.get("owner_user_id") or row.get("user_id") or "").strip()
    return bool(owner_id) and owner_id == account_id


def _get_project_record(project_id: int) -> dict[str, Any] | None:
    try:
        projects = chatlog_db.list_projects() or []
    except Exception:
        return None

    for project in projects:
        row = _normalize_project_row(project)
        try:
            row_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        if row_id == int(project_id):
            return row
    return None


def _require_project_account_scope(
    project_id: int,
    request_user_scope: RequestUserScope,
) -> dict[str, Any]:
    project = _get_project_record(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if getattr(request_user_scope, "multi_user_enabled", False):
        account_id = _request_account_id(request_user_scope)
        owner_id = str(
            project.get("owner_user_id") or project.get("user_id") or ""
        ).strip()
        if owner_id != account_id:
            raise HTTPException(
                status_code=403,
                detail="Project does not belong to the authenticated account",
            )

    return project


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Depends(require_api_key)],
)
api_router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
    dependencies=[Depends(require_api_key)],
)


@router.get("")
@api_router.get("")
def list_projects(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Return all projects as a list for compatibility with frontend /api/projects calls.
    """
    try:
        projects = chatlog_db.list_projects() or []
        if getattr(request_user_scope, "multi_user_enabled", False):
            projects = [
                _normalize_project_row(project)
                for project in projects
                if _project_is_visible_to_scope(project, request_user_scope)
            ]
        else:
            projects = [_normalize_project_row(project) for project in projects]
        projects = normalize_projects_for_listing(projects)
        projects = [
            {
                key: value
                for key, value in project.items()
                if key != "owner_user_id"
            }
            for project in projects
        ]
    except Exception as exc:
        logger.warning("[projects] failed to list projects: %s", exc)
        projects = []
    return projects


@router.post("")
@api_router.post("")
def create_project(
    body: ProjectCreate,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Create a new project.

    Args:
        body: Project name and optional description

    Returns:
        Created project dict with id, name, description
    """
    try:
        owner_id = _resolve_project_owner_hint(body.user_id, request_user_scope)
        requested_name = (
            DEFAULT_PROJECT_NAME
            if is_default_project_name(body.name)
            else body.name
        )
        persisted_description = body.description or ""
        if getattr(request_user_scope, "multi_user_enabled", False):
            persisted_description = _encode_project_description(
                persisted_description, owner_id
            )
        project_id = chatlog_db.create_project(
            requested_name, persisted_description
        )
        return {
            "id": project_id,
            "name": requested_name,
            "description": body.description or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


@router.patch("/{project_id}")
@api_router.patch("/{project_id}")
def patch_project(
    project_id: int,
    body: Dict[str, object] = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Update an existing project's name or description.

    Args:
        project_id: Project ID to update
        body: Updated fields (name, description)

    Returns:
        Success status
    """
    name = body.get("name")
    description = body.get("description")
    project = _require_project_account_scope(project_id, request_user_scope)
    if isinstance(name, str) and is_default_project_name(name):
        name = DEFAULT_PROJECT_NAME
    if getattr(request_user_scope, "multi_user_enabled", False):
        account_id = _request_account_id(request_user_scope)
        current_owner = str(
            project.get("owner_user_id") or project.get("user_id") or ""
        ).strip()
        if not current_owner:
            raise HTTPException(
                status_code=403,
                detail="Project does not belong to the authenticated account",
            )
        if description is None:
            description = project.get("description")
        _, decoded_description = _decode_project_description(description)
        description = _encode_project_description(
            decoded_description, account_id
        )
    try:
        chatlog_db.update_project(
            project_id,
            name=name if name is not None else None,
            description=description if description is not None else None,
        )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


@router.delete("/{project_id}")
@api_router.delete("/{project_id}")
def delete_project_and_eject(
    project_id: int,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Delete a project and eject all threads back to the default project.

    Args:
        project_id: Project ID to delete

    Returns:
        Success status
    """
    _require_project_account_scope(project_id, request_user_scope)
    # Eject threads from this project first
    try:
        chatlog_db.eject_threads_from_project(project_id)
    except Exception as e:
        logger.warning("eject threads failed: %s", e)
    # Delete project row
    try:
        deleted = chatlog_db.delete_project(project_id)
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "Project not found"},
            )
        return {"ok": True}
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


# Backward-compatible alias kept for older imports.
def ensure_default_project():
    return ensure_loose_threads_project()
