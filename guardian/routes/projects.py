"""
Projects Routes
~~~~~~~~~~~~~~~

Project creation and management endpoints.
Includes default "General" project initialization.
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from guardian.core.default_project import (
    DEFAULT_PROJECT_NAME,
    canonicalize_default_project,
    is_default_project_name,
    normalize_projects_for_listing,
)
from guardian.core.project_lifecycle import (
    ProjectLifecycleError,
    require_mutable_project_container,
    require_project_deletable,
)
from guardian.core.repository_authority import (
    ActiveBindingAlreadyExists,
    AccountProjectMismatch,
    ProjectNotFound,
)
from guardian.core.repository_discovery import RepositoryDiscoveryError
from guardian.core.repository_import import (
    CandidateActorMismatch,
    CandidateNotFound,
    CandidateRevalidationFailed,
    InvalidImportTarget,
    RepositoryAlreadyLinked,
    RepositoryBindingAmbiguous,
    RepositoryBindingOwnedByAnotherAccount,
    RepositoryImportError,
    import_explicit_repository_candidate,
)
from guardian.core.repository_search import (
    InvalidRepositorySearchQuery,
    RepositorySearchEnumerationFailed,
    RepositorySearchError,
    RepositorySearchUnavailable,
    search_project_repository,
)

logger = logging.getLogger(__name__)

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.auth_dependencies import (  # noqa: F401
        get_current_user_id,
    )
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

    def get_current_user_id(request):  # type: ignore[unused-argument]
        return get_single_user_id()


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


class RepositoryCandidateImportRequest(BaseModel):
    """Authenticated human/API import request; never a model tool schema."""

    discovery_root: str
    candidate_relative_path: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


_PROJECT_OWNER_SENTINEL = "__codexify_project_owner__"


def _request_account_id(
    request_user_scope: RequestUserScope,
) -> str:
    account_id = str(
        getattr(request_user_scope, "account_id", "") or ""
    ).strip()
    if account_id:
        return account_id

    user_id = str(getattr(request_user_scope, "user_id", "") or "").strip()
    if user_id:
        return user_id

    return get_single_user_id()


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


def _project_lifecycle_error_response(
    exc: ProjectLifecycleError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"ok": False, "error": exc.code, "message": exc.message},
    )


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
    request: Request = None,
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
        owner_id = _resolve_project_owner_hint(
            body.user_id,
            request_user_scope,
        )
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
        if getattr(request_user_scope, "multi_user_enabled", False):
            project_id = chatlog_db.create_project(
                requested_name, persisted_description, user_id=owner_id
            )
        else:
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


def _repository_import_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, (InvalidImportTarget, RepositoryDiscoveryError)):
        return HTTPException(
            status_code=400,
            detail={
                "code": "repository_import_invalid_request",
                "message": "Repository import request is invalid.",
            },
        )
    if isinstance(exc, (AccountProjectMismatch, CandidateActorMismatch)):
        return HTTPException(
            status_code=403,
            detail={
                "code": "repository_import_forbidden",
                "message": "Repository import is not authorized for this account.",
            },
        )
    if isinstance(exc, (CandidateNotFound, ProjectNotFound)):
        return HTTPException(
            status_code=404,
            detail={
                "code": "repository_import_candidate_not_found",
                "message": "Selected repository candidate was not found.",
            },
        )
    if isinstance(
        exc,
        (
            CandidateRevalidationFailed,
            RepositoryAlreadyLinked,
            RepositoryBindingAmbiguous,
            RepositoryBindingOwnedByAnotherAccount,
            ActiveBindingAlreadyExists,
        ),
    ):
        return HTTPException(
            status_code=409,
            detail={
                "code": "repository_import_conflict",
                "message": "Repository import conflicts with current authority.",
            },
        )
    if isinstance(exc, RepositoryImportError):
        return HTTPException(
            status_code=400,
            detail={
                "code": "repository_import_invalid_request",
                "message": "Repository import request is invalid.",
            },
        )
    return HTTPException(
        status_code=500,
        detail={
            "code": "repository_import_internal_error",
            "message": "Repository import could not be completed.",
        },
    )


@api_router.post("/repository-import")
def import_repository_candidate_route(
    body: RepositoryCandidateImportRequest,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Explicit authenticated candidate import; route owns commit or rollback."""
    account_id = _request_account_id(request_user_scope)
    if chatlog_db is None or not hasattr(chatlog_db, "get_session"):
        raise _repository_import_error_response(RuntimeError("database unavailable"))

    try:
        with chatlog_db.get_session() as session:
            try:
                result = import_explicit_repository_candidate(
                    session,
                    authenticated_account_id=account_id,
                    discovery_root=body.discovery_root,
                    candidate_relative_path=body.candidate_relative_path,
                    project_id=body.project_id,
                    project_name=body.project_name,
                    project_description=body.project_description,
                )
                session.commit()
            except (
                InvalidImportTarget,
                RepositoryDiscoveryError,
                AccountProjectMismatch,
                ProjectNotFound,
                CandidateActorMismatch,
                CandidateNotFound,
                CandidateRevalidationFailed,
                RepositoryAlreadyLinked,
                RepositoryBindingAmbiguous,
                RepositoryBindingOwnedByAnotherAccount,
                ActiveBindingAlreadyExists,
                RepositoryImportError,
            ) as exc:
                session.rollback()
                raise _repository_import_error_response(exc) from None
            except Exception:
                session.rollback()
                logger.error("[projects] repository import failed")
                raise _repository_import_error_response(
                    RuntimeError("repository import failed")
                ) from None
    except HTTPException:
        raise
    except Exception:
        logger.error("[projects] repository import session failed")
        raise _repository_import_error_response(
            RuntimeError("repository import session failed")
        ) from None

    return {
        "ok": True,
        "project_id": result.project_id,
        "binding_id": result.binding_id,
        "created_project": result.created_project,
        "reused_existing": result.reused_existing,
        "source_class": result.source_class,
    }


def _repository_search_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidRepositorySearchQuery):
        return HTTPException(
            status_code=400,
            detail={
                "code": "repository_search_invalid_query",
                "message": "Repository search query is invalid.",
            },
        )
    if isinstance(exc, AccountProjectMismatch):
        return HTTPException(
            status_code=403,
            detail={
                "code": "repository_search_forbidden",
                "message": "Repository search is not authorized for this account.",
            },
        )
    if isinstance(exc, ProjectNotFound):
        return HTTPException(
            status_code=404,
            detail={
                "code": "repository_search_project_not_found",
                "message": "Project was not found.",
            },
        )
    if isinstance(
        exc,
        (
            RepositorySearchUnavailable,
            RepositorySearchEnumerationFailed,
        ),
    ):
        return HTTPException(
            status_code=409,
            detail={
                "code": "repository_search_unavailable",
                "message": "Repository search is unavailable.",
            },
        )
    if isinstance(exc, RepositorySearchError):
        return HTTPException(
            status_code=409,
            detail={
                "code": "repository_search_unavailable",
                "message": "Repository search is unavailable.",
            },
        )
    return HTTPException(
        status_code=500,
        detail={
            "code": "repository_search_internal_error",
            "message": "Repository search could not be completed.",
        },
    )


@api_router.get(
    "/{project_id}/repository/search",
    operation_id="repository.search",
)
def search_project_repository_route(
    project_id: int,
    q: str = Query(..., min_length=1, max_length=256),
    limit: int = Query(20, ge=1, le=20),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Search only the authenticated Project's resolved repository binding."""
    account_id = _request_account_id(request_user_scope)
    if chatlog_db is None or not hasattr(chatlog_db, "get_session"):
        raise _repository_search_error_response(
            RuntimeError("database unavailable")
        )

    try:
        with chatlog_db.get_session() as session:
            try:
                result = search_project_repository(
                    session,
                    authenticated_account_id=account_id,
                    project_id=project_id,
                    query=q,
                    result_limit=limit,
                )
            except (
                InvalidRepositorySearchQuery,
                AccountProjectMismatch,
                ProjectNotFound,
                RepositorySearchUnavailable,
                RepositorySearchEnumerationFailed,
                RepositorySearchError,
            ) as exc:
                raise _repository_search_error_response(exc) from None
            except Exception:
                logger.error("[projects] repository search failed")
                raise _repository_search_error_response(
                    RuntimeError("repository search failed")
                ) from None
    except HTTPException:
        raise
    except Exception:
        logger.error("[projects] repository search session failed")
        raise _repository_search_error_response(
            RuntimeError("repository search session failed")
        ) from None

    return {"ok": True, **result.to_payload()}


@router.patch("/{project_id}")
@api_router.patch("/{project_id}")
def patch_project(
    project_id: int,
    body: Dict[str, object] = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Update an existing project's name, description, or archive state.

    Args:
        project_id: Project ID to update
        body: Updated fields (name, description)

    Returns:
        Success status
    """
    name = body.get("name")
    description = body.get("description")
    archived = body.get("archived")
    project = _require_project_account_scope(project_id, request_user_scope)
    if (
        isinstance(name, str)
        and is_default_project_name(name)
        and not project.get("system_role")
    ):
        name = DEFAULT_PROJECT_NAME
    if archived is not None and not isinstance(archived, bool):
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": "invalid_project_archive_state",
                "message": "archived must be a boolean",
            },
        )
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
        if archived is not None:
            require_mutable_project_container(project)
        chatlog_db.update_project(
            project_id,
            name=name if name is not None else None,
            description=description if description is not None else None,
        )
        if archived is not None:
            chatlog_db.archive_project(project_id, archived)
        return {"ok": True}
    except ProjectLifecycleError as exc:
        return _project_lifecycle_error_response(exc)
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
    Delete an archived ordinary Project and eject its threads to General.

    Args:
        project_id: Project ID to delete

    Returns:
        Success status
    """
    try:
        project = _require_project_account_scope(project_id, request_user_scope)
        require_project_deletable(project)
        deleted = chatlog_db.delete_project(project_id)
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "Project not found"},
            )
        return {"ok": True}
    except ProjectLifecycleError as exc:
        return _project_lifecycle_error_response(exc)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": str(e)}
        )


# Backward-compatible alias kept for older imports.
def ensure_default_project():
    return ensure_loose_threads_project()
