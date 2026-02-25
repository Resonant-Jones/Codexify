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

logger = logging.getLogger(__name__)

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import chatlog_db, require_api_key
except ImportError:
    chatlog_db = None
    require_api_key = lambda x: x


# Helper: ensure default project exists at startup
def ensure_loose_threads_project():
    """
    Ensure the default 'General' project exists for unassigned threads.
    This function should be called during application startup, not at import time.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        chatlog_db.ensure_project(
            "General", "Default bucket for unassigned threads"
        )
        logger.info("[projects] Ensured General project exists")
        return True
    except Exception as e:
        logger.warning("[projects] Failed to ensure General project: %s", e)
        return False


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


router = APIRouter(prefix="/projects", tags=["Projects"])
api_router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("")
@api_router.get("")
def list_projects():
    """
    Return all projects as a list for compatibility with frontend /api/projects calls.
    """
    try:
        projects = chatlog_db.list_projects()
    except Exception as exc:
        logger.warning("[projects] failed to list projects: %s", exc)
        projects = []
    return projects


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
