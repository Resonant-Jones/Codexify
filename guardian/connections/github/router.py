"""Opt-in account-owned GitHub Knowledge setup and bounded read operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from guardian.connections.credential_routes import CredentialSetupRoute
from guardian.connections import knowledge_oauth
from guardian.connections.github import credentials
from guardian.connections.github.service import (
    GitHubClient,
    GitHubError,
    GitHubAuthorizationError,
    GitHubScopeError,
    GitHubNotConfiguredError,
    GitHubObjectNotFoundError,
    GitHubTransportError,
)
from guardian.core.dependencies import get_account_user_id, require_account_session

setup_router = APIRouter(
    route_class=CredentialSetupRoute,
    prefix="/api/connect/github-knowledge",
    tags=["GitHub Knowledge Setup"],
    dependencies=[Depends(require_account_session)],
)
operations_router = APIRouter(
    prefix="/api/knowledge/github",
    tags=["GitHub Knowledge"],
    dependencies=[Depends(require_account_session)],
)
_db: Any | None = None


def configure_db(db: Any | None) -> None:
    global _db
    _db = db


def _get_db() -> Any:
    if _db is None or not hasattr(_db, "get_session"):
        raise HTTPException(
            503, detail={"error": "github_connection_storage_unavailable"}
        )
    return _db


class GitHubConfigureRequest(BaseModel):
    token: Any = Field(default=None, repr=False)
    repositories: list[str] = Field(min_length=1, max_length=20)


def _error(exc: GitHubError) -> HTTPException:
    status = 502
    if isinstance(exc, GitHubNotConfiguredError):
        status = 409
    elif isinstance(exc, GitHubScopeError):
        status = 403
    elif isinstance(exc, GitHubAuthorizationError):
        status = 401
    elif isinstance(exc, GitHubObjectNotFoundError):
        status = 404
    elif isinstance(exc, GitHubTransportError):
        status = 503
    return HTTPException(status, detail={"error": exc.error_code})


def configured_client(db: Any, user_id: str) -> GitHubClient:
    connection = credentials.configured_connection(db, user_id)
    if connection is None:
        raise GitHubNotConfiguredError("No GitHub credential configured")
    token, repositories = connection
    return GitHubClient(token, repositories)


def _status(db: Any, user_id: str) -> dict[str, Any]:
    return {
        "connection_id": "github_knowledge",
        "validation": credentials.status_projection(db, user_id),
    }


@setup_router.post("/configure")
def configure_github(
    payload: GitHubConfigureRequest, user_id: str = Depends(get_account_user_id)
) -> dict[str, Any]:
    if knowledge_oauth.enabled():
        raise HTTPException(409, detail={"error": "knowledge_oauth_required"})
    token = payload.token.strip() if isinstance(payload.token, str) else ""
    if not token or len(token) > 4096:
        raise HTTPException(422, detail={"error": "github_token_required"})
    try:
        # Construction validates the repository scope without contacting GitHub.
        GitHubClient(token, payload.repositories)
    except (GitHubError, ValueError):
        raise HTTPException(
            422, detail={"error": "github_repository_scope_invalid"}
        ) from None
    credentials.configure_token(_get_db(), user_id, token, payload.repositories)
    return _status(_get_db(), user_id)


@setup_router.get("/status")
def github_status(user_id: str = Depends(get_account_user_id)) -> dict[str, Any]:
    return _status(_get_db(), user_id)


@setup_router.post("/validate")
def validate_github(user_id: str = Depends(get_account_user_id)) -> dict[str, Any]:
    db = _get_db()
    connection = credentials.configured_connection(db, user_id)
    if connection is None:
        raise _error(GitHubNotConfiguredError("No GitHub credential configured"))
    try:
        GitHubClient(*connection).validate()
    except GitHubError as exc:
        if not isinstance(exc, GitHubNotConfiguredError):
            state = credentials.VALIDATION_PROVIDER_ERROR
            if isinstance(exc, GitHubAuthorizationError):
                state = credentials.VALIDATION_AUTHORIZATION_ERROR
            elif isinstance(exc, GitHubTransportError):
                state = credentials.VALIDATION_TRANSPORT_ERROR
            credentials.mark_validation(
                db, user_id, state, expected_connection=connection
            )
        raise _error(exc) from None
    credentials.mark_validation(
        db, user_id, credentials.VALIDATION_VALID, expected_connection=connection
    )
    return _status(db, user_id)


@setup_router.post("/disconnect")
def disconnect_github(user_id: str = Depends(get_account_user_id)) -> dict[str, Any]:
    return {
        "connection_id": "github_knowledge",
        "removed": credentials.disconnect(_get_db(), user_id),
    }


@operations_router.get("/search", operation_id="github_content_search")
def github_content_search(
    repository: str = Query(min_length=3, max_length=201),
    query: str = Query(min_length=1, max_length=500),
    page: int = Query(default=1, ge=1, le=10),
    limit: int = Query(default=25, ge=1, le=50),
    user_id: str = Depends(get_account_user_id),
) -> dict[str, Any]:
    try:
        return configured_client(_get_db(), user_id).search(
            repository=repository, query=query, page=page, limit=limit
        )
    except GitHubError as exc:
        raise _error(exc) from None
    except ValueError:
        raise HTTPException(422, detail={"error": "github_arguments_invalid"}) from None


@operations_router.get(
    "/read/{owner}/{repo}/{number}", operation_id="github_content_read"
)
def github_content_read(
    owner: str, repo: str, number: int, user_id: str = Depends(get_account_user_id)
) -> dict[str, Any]:
    try:
        return configured_client(_get_db(), user_id).read_issue(
            repository=f"{owner}/{repo}", number=number
        )
    except GitHubError as exc:
        raise _error(exc) from None
    except ValueError:
        raise HTTPException(422, detail={"error": "github_arguments_invalid"}) from None
