from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope
from guardian.core.repository_authority import AccountProjectMismatch, ProjectNotFound
from guardian.core.repository_search import (
    InvalidRepositorySearchQuery,
    RepositorySearchEnumerationFailed,
    RepositorySearchMatch,
    RepositorySearchResult,
    RepositorySearchUnavailable,
)
from guardian.routes import projects as projects_routes


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _Database:
    def __init__(self, session: _Session) -> None:
        self.session = session

    @contextmanager
    def get_session(self):
        yield self.session


def _scope(account_id: str = "account-a") -> RequestUserScope:
    return RequestUserScope(
        user_id=account_id,
        account_id=account_id,
        multi_user_enabled=True,
    )


def _result() -> RepositorySearchResult:
    return RepositorySearchResult(
        matches=(
            RepositorySearchMatch(
                path="src/example.py",
                line=42,
                snippet="needle is safely repository relative",
            ),
        ),
        count=1,
        truncated=False,
        stop_reason="completed",
        scanned_files=3,
        scanned_bytes=123,
        skipped_binary_files=0,
        skipped_oversized_files=0,
        skipped_sensitive_files=0,
        skipped_symlink_files=0,
    )


def test_search_route_is_api_only_with_exact_operation_and_input_surface() -> None:
    app = FastAPI()
    app.include_router(projects_routes.api_router)
    schema = app.openapi()
    operation = schema["paths"]["/api/projects/{project_id}/repository/search"][
        "get"
    ]

    assert operation["operationId"] == "repository.search"
    assert "/projects/{project_id}/repository/search" not in schema["paths"]
    parameters = {
        parameter["name"]: parameter
        for parameter in operation["parameters"]
    }
    assert {"project_id", "q", "limit"} <= set(parameters)
    assert parameters["project_id"]["in"] == "path"
    assert parameters["q"]["in"] == "query"
    assert parameters["q"]["required"] is True
    assert parameters["limit"]["in"] == "query"
    assert not {
        "account_id",
        "user_id",
        "binding_id",
        "repository_root",
        "discovery_root",
        "repoPath",
        "cwd",
        "mount",
    } & set(parameters)


def test_search_route_uses_scope_calls_service_and_never_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))
    captured: dict[str, object] = {}

    def search(received_session, **kwargs):
        captured["session"] = received_session
        captured.update(kwargs)
        return _result()

    monkeypatch.setattr(projects_routes, "search_project_repository", search)
    response = projects_routes.search_project_repository_route(
        42,
        q="needle",
        limit=5,
        request_user_scope=_scope(),
    )

    assert captured == {
        "session": session,
        "authenticated_account_id": "account-a",
        "project_id": 42,
        "query": "needle",
        "result_limit": 5,
    }
    assert response == {
        "ok": True,
        "matches": [
            {
                "path": "src/example.py",
                "line": 42,
                "snippet": "needle is safely repository relative",
            }
        ],
        "count": 1,
        "truncated": False,
        "stop_reason": "completed",
        "scanned_files": 3,
        "scanned_bytes": 123,
        "skipped_binary_files": 0,
        "skipped_oversized_files": 0,
        "skipped_sensitive_files": 0,
        "skipped_symlink_files": 0,
    }
    assert session.commits == 0
    assert session.rollbacks == 0
    assert "canonical_root" not in response
    assert "repository_root" not in response
    assert "account-a" not in repr(response)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (
            InvalidRepositorySearchQuery("bad /private/path"),
            400,
            "repository_search_invalid_query",
        ),
        (
            AccountProjectMismatch("other account"),
            403,
            "repository_search_forbidden",
        ),
        (
            ProjectNotFound("missing project"),
            404,
            "repository_search_project_not_found",
        ),
        (
            RepositorySearchUnavailable("stale /private/repository"),
            409,
            "repository_search_unavailable",
        ),
        (
            RepositorySearchEnumerationFailed("stderr /private/repository"),
            409,
            "repository_search_unavailable",
        ),
    ],
)
def test_search_errors_are_bounded_and_path_safe(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(projects_routes, "search_project_repository", fail)
    with pytest.raises(HTTPException) as exc_info:
        projects_routes.search_project_repository_route(
            8, q="needle", request_user_scope=_scope()
        )

    assert exc_info.value.status_code == status
    assert exc_info.value.detail["code"] == code
    assert "/private/repository" not in repr(exc_info.value.detail)
    assert session.commits == 0
    assert session.rollbacks == 0


def test_unexpected_search_error_is_generic_and_path_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))

    def fail(*_args, **_kwargs):
        raise RuntimeError("do not leak /private/repository")

    monkeypatch.setattr(projects_routes, "search_project_repository", fail)
    with pytest.raises(HTTPException) as exc_info:
        projects_routes.search_project_repository_route(
            8, q="needle", request_user_scope=_scope()
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "code": "repository_search_internal_error",
        "message": "Repository search could not be completed.",
    }
    assert session.commits == 0
    assert session.rollbacks == 0


def test_fastapi_rejects_out_of_range_route_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    app = FastAPI()
    app.include_router(projects_routes.api_router)
    client = TestClient(app)

    empty = client.get(
        "/api/projects/1/repository/search?q=",
        headers={"X-API-Key": "test-key"},
    )
    too_many = client.get(
        "/api/projects/1/repository/search?q=needle&limit=21",
        headers={"X-API-Key": "test-key"},
    )
    assert empty.status_code == 422
    assert too_many.status_code == 422
