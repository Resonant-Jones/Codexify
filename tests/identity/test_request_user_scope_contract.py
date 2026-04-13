from __future__ import annotations

import pytest

from guardian.core import dependencies


@pytest.fixture(autouse=True)
def _identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "local_user")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")


def test_request_user_scope_preserves_single_user_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")

    scope = dependencies.get_request_user_scope(x_user_id="spoofed_user")

    assert scope.account_id == "local_user"
    assert scope.principal_id == "local_user"
    assert scope.multi_user_enabled is False


def test_request_user_scope_honors_request_principal_in_multi_user_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")

    scope = dependencies.get_request_user_scope(x_user_id="alice")

    assert scope.account_id == "alice"
    assert scope.principal_id == "alice"
    assert scope.multi_user_enabled is True
