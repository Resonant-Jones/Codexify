from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from guardian.core.dependencies import RequestUserScope
from guardian.core.repository_authority import AccountProjectMismatch
from guardian.core.repository_import import (
    CandidateNotFound,
    CandidateRevalidationFailed,
    RepositoryAlreadyLinked,
    RepositoryBindingOwnedByAnotherAccount,
    RepositoryImportResult,
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


def _body(**overrides: object) -> projects_routes.RepositoryCandidateImportRequest:
    payload: dict[str, object] = {
        "discovery_root": "/private/selected-root",
        "candidate_relative_path": "nested/repository",
        "project_name": "Imported Project",
        "project_description": "Safe description",
    }
    payload.update(overrides)
    return projects_routes.RepositoryCandidateImportRequest.model_validate(payload)


def test_repository_import_route_is_api_only_and_request_surface_is_bounded() -> None:
    api_paths = {
        (route.path, tuple(sorted(route.methods)))
        for route in projects_routes.api_router.routes
    }
    legacy_paths = {
        (route.path, tuple(sorted(route.methods)))
        for route in projects_routes.router.routes
    }
    assert ("/api/projects/repository-import", ("POST",)) in api_paths
    assert not any(path.endswith("repository-import") for path, _ in legacy_paths)
    assert set(
        projects_routes.RepositoryCandidateImportRequest.model_json_schema()[
            "properties"
        ]
    ) == {
        "discovery_root",
        "candidate_relative_path",
        "project_id",
        "project_name",
        "project_description",
    }
    with pytest.raises(ValidationError):
        projects_routes.RepositoryCandidateImportRequest.model_validate(
            {
                "discovery_root": "/private/selected-root",
                "candidate_relative_path": ".",
                "project_name": "Imported Project",
                "user_id": "body-controlled-owner",
            }
        )


def test_successful_new_project_import_passes_scope_identity_and_commits_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))
    calls: dict[str, object] = {}

    def import_candidate(received_session, **kwargs):
        calls["session"] = received_session
        calls.update(kwargs)
        return RepositoryImportResult(
            project_id=17,
            binding_id="binding-17",
            created_project=True,
            reused_existing=False,
        )

    monkeypatch.setattr(
        projects_routes, "import_explicit_repository_candidate", import_candidate
    )

    response = projects_routes.import_repository_candidate_route(
        _body(),
        request_user_scope=_scope(),
    )

    assert response == {
        "ok": True,
        "project_id": 17,
        "binding_id": "binding-17",
        "created_project": True,
        "reused_existing": False,
        "source_class": "external_linked",
    }
    assert calls["session"] is session
    assert calls["authenticated_account_id"] == "account-a"
    assert calls["discovery_root"] == "/private/selected-root"
    assert calls["candidate_relative_path"] == "nested/repository"
    assert session.commits == 1
    assert session.rollbacks == 0
    assert "/private/selected-root" not in repr(response)
    assert "canonical_root" not in response
    assert "discovery_root" not in response


def test_successful_existing_project_link_returns_only_bounded_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))
    monkeypatch.setattr(
        projects_routes,
        "import_explicit_repository_candidate",
        lambda *_args, **_kwargs: RepositoryImportResult(
            project_id=5,
            binding_id="binding-5",
            created_project=False,
            reused_existing=True,
        ),
    )

    response = projects_routes.import_repository_candidate_route(
        _body(project_id=5, project_name=None, project_description=None),
        request_user_scope=_scope(),
    )

    assert response["project_id"] == 5
    assert response["created_project"] is False
    assert response["reused_existing"] is True
    assert set(response) == {
        "ok",
        "project_id",
        "binding_id",
        "created_project",
        "reused_existing",
        "source_class",
    }
    assert session.commits == 1


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (AccountProjectMismatch("foreign project"), 403, "repository_import_forbidden"),
        (CandidateNotFound("missing candidate"), 404, "repository_import_candidate_not_found"),
        (CandidateRevalidationFailed("stale candidate"), 409, "repository_import_conflict"),
        (RepositoryAlreadyLinked("already linked"), 409, "repository_import_conflict"),
        (
            RepositoryBindingOwnedByAnotherAccount("foreign account id=88"),
            409,
            "repository_import_conflict",
        ),
    ],
)
def test_known_failures_rollback_with_bounded_path_safe_response(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(
        projects_routes, "import_explicit_repository_candidate", fail
    )
    with pytest.raises(HTTPException) as exc_info:
        projects_routes.import_repository_candidate_route(
            _body(discovery_root="/private/selected-root"),
            request_user_scope=_scope(),
        )

    assert exc_info.value.status_code == status
    assert exc_info.value.detail["code"] == code
    assert "/private/selected-root" not in repr(exc_info.value.detail)
    assert "foreign account id=88" not in repr(exc_info.value.detail)
    assert session.commits == 0
    assert session.rollbacks == 1


def test_unexpected_failure_rolls_back_and_is_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))

    def fail(*_args, **_kwargs):
        raise RuntimeError("leaked /private/selected-root")

    monkeypatch.setattr(
        projects_routes, "import_explicit_repository_candidate", fail
    )
    with pytest.raises(HTTPException) as exc_info:
        projects_routes.import_repository_candidate_route(
            _body(), request_user_scope=_scope()
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "code": "repository_import_internal_error",
        "message": "Repository import could not be completed.",
    }
    assert session.commits == 0
    assert session.rollbacks == 1


def test_import_route_uses_request_scope_not_body_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(projects_routes, "chatlog_db", _Database(session))
    captured = SimpleNamespace(account_id=None)

    def import_candidate(*_args, **kwargs):
        captured.account_id = kwargs["authenticated_account_id"]
        return RepositoryImportResult(
            project_id=2,
            binding_id="binding-2",
            created_project=True,
            reused_existing=False,
        )

    monkeypatch.setattr(
        projects_routes, "import_explicit_repository_candidate", import_candidate
    )
    projects_routes.import_repository_candidate_route(
        _body(), request_user_scope=_scope("scope-owned-account")
    )
    assert captured.account_id == "scope-owned-account"
