"""Regression tests for the restored LOCAL_RUNTIME_PRESET Settings field.

Proves that:
1. LOCAL_RUNTIME_PRESET is retained by Pydantic (not dropped by extra="ignore").
2. LOCAL_COMPAT_FIRST boolean parsing follows the existing convention.
3. A matching profile configuration passes the profile-contract check.
4. A genuine mismatch still fails closed.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all profile-contract env vars so tests start clean."""
    for key in (
        "LOCAL_RUNTIME_PRESET",
        "LOCAL_COMPAT_FIRST",
        "LOCAL_PROVIDER_DISPLAY_NAME",
        "LOCAL_PROVIDER_VENDOR",
        "LOCAL_BASE_URL",
        "LOCAL_API_KEY",
        "CODEXIFY_EGRESS_ALLOWLIST",
        "LLM_PROVIDER",
        "ALLOW_CLOUD_PROVIDERS",
        "CODEXIFY_LOCAL_ONLY_MODE",
        "CODEXIFY_CONFIG_SOURCE",
        "CODEXIFY_SUPPORTED_PROFILE",
        "GUARDIAN_API_KEY",
        "GUARDIAN_API_KEYS",
        "GUARDIAN_DATABASE_URL",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "AI_BACKEND",
    ):
        monkeypatch.delenv(key, raising=False)


def _build_settings(**overrides):
    """Build a fresh Settings instance with the given overrides."""
    from guardian.core.config import Settings

    return Settings(**overrides)


def test_local_runtime_preset_retained():
    """LOCAL_RUNTIME_PRESET is declared on Settings and survives parsing."""
    s = _build_settings(LOCAL_RUNTIME_PRESET="whooshd-mlx")
    assert s.LOCAL_RUNTIME_PRESET == "whooshd-mlx"


def test_local_runtime_preset_default_overrideable():
    """Default can be explicitly set to empty."""
    s = _build_settings(LOCAL_RUNTIME_PRESET="")
    assert s.LOCAL_RUNTIME_PRESET == ""


def test_local_compat_first_bool_from_string():
    """LOCAL_COMPAT_FIRST accepts truthy strings."""
    assert _build_settings(LOCAL_COMPAT_FIRST="1").LOCAL_COMPAT_FIRST is True
    assert _build_settings(LOCAL_COMPAT_FIRST="true").LOCAL_COMPAT_FIRST is True
    assert _build_settings(LOCAL_COMPAT_FIRST="0").LOCAL_COMPAT_FIRST is False


def test_provider_display_name_retained():
    """LOCAL_PROVIDER_DISPLAY_NAME survives extra=ignore."""
    s = _build_settings(LOCAL_PROVIDER_DISPLAY_NAME="Whoosh'd")
    assert s.LOCAL_PROVIDER_DISPLAY_NAME == "Whoosh'd"


def test_provider_vendor_retained():
    """LOCAL_PROVIDER_VENDOR survives extra=ignore."""
    s = _build_settings(LOCAL_PROVIDER_VENDOR="whooshd")
    assert s.LOCAL_PROVIDER_VENDOR == "whooshd"


def test_matching_profile_passes_provider_contract_check():
    """A complete matching config passes the supported-profile contract."""
    from guardian.core.supported_profile import (
        get_active_supported_profile,
        supported_profile_actual_provider_contract,
        validate_supported_profile_runtime,
    )

    manifest = get_active_supported_profile()
    if manifest is None:
        pytest.skip("No supported profile manifest available")

    s = _build_settings(
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_RUNTIME_PRESET="whooshd-mlx",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_API_KEY="local",
        LOCAL_COMPAT_FIRST=True,
        LOCAL_PROVIDER_DISPLAY_NAME="Whoosh'd",
        LOCAL_PROVIDER_VENDOR="whooshd",
        CODEXIFY_EGRESS_ALLOWLIST="",
    )

    mismatches = validate_supported_profile_runtime(
        manifest, settings=s
    )
    assert not mismatches, f"Unexpected mismatches: {mismatches}"


def test_mismatched_runtime_preset_fails_closed():
    """A wrong LOCAL_RUNTIME_PRESET still fails the contract check."""
    from guardian.core.supported_profile import (
        get_active_supported_profile,
        validate_supported_profile_runtime,
    )

    manifest = get_active_supported_profile()
    if manifest is None:
        pytest.skip("No supported profile manifest available")

    s = _build_settings(
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_RUNTIME_PRESET="ollama",  # wrong — profile expects whooshd-mlx
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_API_KEY="local",
        LOCAL_COMPAT_FIRST=True,
        LOCAL_PROVIDER_DISPLAY_NAME="Whoosh'd",
        LOCAL_PROVIDER_VENDOR="whooshd",
        CODEXIFY_EGRESS_ALLOWLIST="",
    )

    mismatches = validate_supported_profile_runtime(
        manifest, settings=s
    )
    assert mismatches, "Expected a mismatch for wrong LOCAL_RUNTIME_PRESET"
