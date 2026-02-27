"""
Projects Routes
~~~~~~~~~~~~~~~

Project creation and management endpoints.
Includes default "General" project initialization.
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from guardian.core.default_project import (
    DEFAULT_PROJECT_NAME,
    canonicalize_default_project,
    is_default_project_name,
    normalize_projects_for_listing,
)

logger = logging.getLogger(__name__)

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import chatlog_db, require_api_key
except ImportError:
    chatlog_db = None

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key


# Helper: ensure default project exists at startup
def ensure_loose_threads_project():
    """
    Ensure the default 'General' project exists for unassigned threads.
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
def list_projects():
    """
    Return all projects as a list for compatibility with frontend /api/projects calls.
    """
    try:
        projects = chatlog_db.list_projects()
        projects = normalize_projects_for_listing(projects)
    except Exception as exc:
        logger.warning("[projects] failed to list projects: %s", exc)
        projects = []
    return projects


@router.post("")
@api_router.post("")
def create_project(body: ProjectCreate):
    """
    Create a new project.

    Args:
        body: Project name and optional description

    Returns:
        Created project dict with id, name, description
    """
    try:
        requested_name = (
            DEFAULT_PROJECT_NAME
            if is_default_project_name(body.name)
            else body.name
        )
        project_id = chatlog_db.create_project(
            requested_name, body.description or ""
        )
        return {
            "id": project_id,
            "name": requested_name,
            "description": body.description or "",
        }
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


@router.patch("/{project_id}")
@api_router.patch("/{project_id}")
def patch_project(project_id: int, body: Dict[str, object] = Body(...)):
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
    if isinstance(name, str) and is_default_project_name(name):
        name = DEFAULT_PROJECT_NAME
    try:
        chatlog_db.update_project(
            project_id,
            name=name if name is not None else None,
            description=description if description is not None else None,
        )
        return {"ok": True}
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


@router.delete("/{project_id}")
@api_router.delete("/{project_id}")
def delete_project_and_eject(project_id: int):
    """
    Delete a project and eject all threads back to the default project.

    Args:
        project_id: Project ID to delete

    Returns:
        Success status
    """
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
