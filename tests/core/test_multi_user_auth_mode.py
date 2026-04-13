import importlib

import pytest
from fastapi import HTTPException

from guardian.core.auth import issue_session_token


def _reload_auth_modules(monkeypatch, **env_overrides):
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


def test_multi_user_mode_default_off_preserves_single_user_fallback(
    monkeypatch,
):
    core_config, dependencies = _reload_auth_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="false",
    )

    assert core_config.get_settings().CODEXIFY_MULTI_USER_ENABLED is False

    current_user = dependencies.get_current_user(api_key="api-key")

    assert current_user == "single-user"


def test_multi_user_mode_enabled_rejects_missing_authenticated_subject(
    monkeypatch,
):
    core_config, dependencies = _reload_auth_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="true",
    )

    assert core_config.get_settings().CODEXIFY_MULTI_USER_ENABLED is True

    with pytest.raises(HTTPException) as exc_info:
        dependencies.get_current_user(api_key="api-key")

    assert exc_info.value.status_code == 401
    assert "multi-user" in str(exc_info.value.detail).lower()
    assert "session/jwt" in str(exc_info.value.detail).lower()


def test_multi_user_mode_enabled_accepts_resolved_authenticated_subject(
    monkeypatch,
):
    core_config, dependencies = _reload_auth_modules(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_MULTI_USER_ENABLED="true",
        GUARDIAN_SESSION_SECRET="multi-user-session-secret",
        GUARDIAN_AUTH_MODE="remote",
    )

    assert core_config.get_settings().CODEXIFY_MULTI_USER_ENABLED is True

    session_token, _expires = issue_session_token(
        subject="resolved-user",
        ttl_seconds=60,
    )

    assert (
        dependencies._resolve_authenticated_subject(
            f"Bearer {session_token}",
            None,
        )
        == "resolved-user"
    )

    monkeypatch.setattr(
        dependencies,
        "_resolve_authenticated_subject",
        lambda *_args, **_kwargs: "resolved-user",
    )

    current_user = dependencies.get_current_user(api_key="api-key")

    assert current_user == "resolved-user"
