from __future__ import annotations

import pytest
from fastapi import HTTPException

from guardian.server import codexify_api


def test_oauth_begin_allowed_in_local_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setattr(
        codexify_api,
        "ensure_oauth_credentials",
        lambda: "/tmp/token.json",
    )

    response = codexify_api.oauth_begin()

    assert response["ok"] is True
    assert response["token"] == "/tmp/token.json"


def test_oauth_begin_rejected_in_remote_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")

    with pytest.raises(HTTPException) as exc:
        codexify_api.oauth_begin()

    assert exc.value.status_code == 403
    assert "local/dev-only" in str(exc.value.detail).lower()
