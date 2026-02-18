from __future__ import annotations

import pytest
from pydantic import ValidationError

import guardian.config.core as core


def test_secret_store_requirement_disabled_allows_unavailable_store(
    monkeypatch,
):
    monkeypatch.setattr(
        core,
        "_secret_store_available",
        lambda _store: (False, "unavailable"),
    )

    settings = core.get_settings_no_env(
        CODEXIFY_SECRET_STORE="keychain",
        CODEXIFY_REQUIRE_SECRET_STORE=False,
    )

    assert settings.CODEXIFY_SECRET_STORE == "keychain"
    assert settings.CODEXIFY_REQUIRE_SECRET_STORE is False


def test_secret_store_requirement_env_store_passes():
    settings = core.get_settings_no_env(
        CODEXIFY_SECRET_STORE="env",
        CODEXIFY_REQUIRE_SECRET_STORE=True,
    )

    assert settings.CODEXIFY_SECRET_STORE == "env"
    assert settings.CODEXIFY_REQUIRE_SECRET_STORE is True


def test_secret_store_requirement_fails_closed(monkeypatch):
    monkeypatch.setattr(
        core,
        "_secret_store_available",
        lambda _store: (False, "missing backend"),
    )

    with pytest.raises(ValidationError) as exc:
        core.get_settings_no_env(
            CODEXIFY_SECRET_STORE="keychain",
            CODEXIFY_REQUIRE_SECRET_STORE=True,
        )

    assert "CODEXIFY_REQUIRE_SECRET_STORE=true" in str(exc.value)
    assert "missing backend" in str(exc.value)
