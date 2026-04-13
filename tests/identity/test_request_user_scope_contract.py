from __future__ import annotations

import pytest

from guardian.core.dependencies import (
    get_request_user_id,
    get_request_user_scope,
)


def test_request_user_id_ignores_x_user_id_without_multi_user(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "local")

    assert get_request_user_id(x_user_id="spoofed-user") == "local"


def test_request_user_scope_preserves_resolved_principal_in_single_user_mode(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "local")

    scope = get_request_user_scope("resolved-user")

    assert scope.account_id == "resolved-user"
    assert scope.multi_user_enabled is False


def test_request_user_id_honors_x_user_id_when_multi_user_enabled(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "local")

    assert get_request_user_id(x_user_id="operator-a") == "operator-a"


def test_request_user_scope_marks_multi_user_mode(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")

    scope = get_request_user_scope("operator-b")

    assert scope.account_id == "operator-b"
    assert scope.multi_user_enabled is True
