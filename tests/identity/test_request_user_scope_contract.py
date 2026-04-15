import importlib

import pytest
from fastapi import HTTPException

from guardian.core.auth import issue_session_token


def _reload_identity_modules(monkeypatch, **env_overrides):
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    for key, value in env_overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    import guardian.core.config as core_config
    import guardian.core.dependencies as dependencies

    core_config = importlib.reload(core_config)
    dependencies = importlib.reload(dependencies)
    return core_config, dependencies


def test_single_user_mode_remains_compatible(monkeypatch):
    core_config, dependencies = _reload_identity_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="false",
    )

    assert core_config.get_settings().CODEXIFY_MULTI_USER_ENABLED is False

    scope = dependencies.get_request_user_scope()

    assert scope.user_id == "single-user"
    assert scope.subject_id is None
    assert scope.account_id is None
    assert dependencies.get_current_user(api_key="api-key") == "single-user"


def test_multi_user_authenticated_subject_resolves_to_stable_account_id(
    monkeypatch,
):
    core_config, dependencies = _reload_identity_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="true",
        GUARDIAN_SESSION_SECRET="request-scope-session-secret",
        GUARDIAN_AUTH_MODE="remote",
    )

    assert core_config.get_settings().CODEXIFY_MULTI_USER_ENABLED is True

    session_token, _expires = issue_session_token(
        subject="subject-123",
        ttl_seconds=60,
    )

    monkeypatch.setattr(
        dependencies,
        "_resolve_account_id_for_subject",
        lambda subject_id: f"account::{subject_id}",
    )

    scope = dependencies.get_request_user_scope(
        authorization=f"Bearer {session_token}"
    )

    assert scope.subject_id == "subject-123"
    assert scope.account_id == "account::subject-123"
    assert scope.user_id == "account::subject-123"
    assert (
        dependencies.get_request_user_id(
            authorization=f"Bearer {session_token}"
        )
        == "subject-123"
    )


def test_multi_user_missing_principal_mapping_fails_closed(monkeypatch):
    _, dependencies = _reload_identity_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="true",
        GUARDIAN_SESSION_SECRET="request-scope-session-secret",
        GUARDIAN_AUTH_MODE="remote",
    )

    session_token, _expires = issue_session_token(
        subject="subject-404",
        ttl_seconds=60,
    )

    monkeypatch.setattr(
        dependencies,
        "_resolve_account_id_for_subject",
        lambda subject_id: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        dependencies.get_request_user_scope(
            authorization=f"Bearer {session_token}"
        )

    assert exc_info.value.status_code == 401
    assert "stable account_id" in str(exc_info.value.detail).lower()
