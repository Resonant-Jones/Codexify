"""Activation tests for the Memory Vault read surface (UMS-05B3).

Proves that the qualified GET-only Memory Vault router is registered
through Guardian's canonical route control plane as ``internal_only`` on
exactly the three intended web profiles, remains quarantined elsewhere, is
hidden from public OpenAPI, and can be disabled by its feature flag.

This suite inspects route-control posture only. It does not reproduce the
B1 persistence semantics (proven by
``tests/services/test_memory_vault_read_projection.py``) or the B2 HTTP
adapter semantics (proven by ``tests/routes/test_memory_vault.py``).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from guardian.core.supported_profile import load_supported_profile

ADMITTED_PROFILES = {
    "v1-local-core-web-mcp",
    "v1-friends-family-web",
    "v1-whooshd-deepseek-web",
}

VAULT_PATHS = {
    "/api/memory-vault/items",
    "/api/memory-vault/items/canonical/{memory_id}",
    "/api/memory-vault/items/compatibility/{source_kind}/{source_id}",
}

_PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "supported_profiles"


def _all_profile_names() -> set[str]:
    return {p.stem for p in _PROFILES_DIR.glob("*.yaml")}


# ---------------------------------------------------------------------------
# Manifest posture.
# ---------------------------------------------------------------------------


def test_admitted_profiles_mark_memory_vault_internal_only() -> None:
    for name in sorted(ADMITTED_PROFILES):
        manifest = load_supported_profile(name)
        assert manifest.route_status("memory_vault") == "internal_only"
        assert "memory_vault" not in manifest.enabled_routes
        assert "memory_vault" in manifest.internal_only_routes
        assert "memory_vault" not in manifest.quarantined_routes


def test_other_profiles_quarantine_memory_vault() -> None:
    others = _all_profile_names() - ADMITTED_PROFILES
    assert others, "expected at least one non-admitted supported profile"
    for name in sorted(others):
        manifest = load_supported_profile(name)
        assert manifest.route_status("memory_vault") == "quarantined"


def test_legacy_memory_posture_unchanged() -> None:
    """The legacy ``memory`` route family remains quarantined everywhere."""
    for name in sorted(_all_profile_names()):
        manifest = load_supported_profile(name)
        assert manifest.route_status("memory") == "quarantined"


# ---------------------------------------------------------------------------
# Runtime control plane.
# ---------------------------------------------------------------------------


@pytest.fixture
def load_guardian_api(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import guardian.guardian_api as guardian_api

    def _load(profile: str, *, flag: str | None = None):
        monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
        monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
        monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
        monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
        monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", profile)
        if flag is None:
            monkeypatch.delenv("CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES", raising=False)
        else:
            monkeypatch.setenv("CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES", flag)
        return importlib.reload(guardian_api)

    try:
        yield _load
    finally:
        monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
        monkeypatch.delenv("CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES", raising=False)
        importlib.reload(guardian_api)


def _mounted_paths(app) -> set[str]:
    return {
        getattr(route, "path", None)
        for route in app.routes
        if isinstance(getattr(route, "path", None), str)
    }


def test_admitted_profile_mounts_vault_routes_internally(
    load_guardian_api,
) -> None:
    guardian_api = load_guardian_api("v1-local-core-web-mcp")
    app = guardian_api.app

    assert "memory_vault" in app.state.supported_profile_enabled_labels
    assert VAULT_PATHS <= _mounted_paths(app)

    # Internal-only: hidden from public OpenAPI, recorded as hidden paths.
    openapi_paths = set(app.openapi().get("paths", {}))
    assert not (VAULT_PATHS & openapi_paths)
    assert VAULT_PATHS <= set(app.state.supported_profile_hidden_paths)


def test_feature_flag_false_disables_vault_route(load_guardian_api) -> None:
    guardian_api = load_guardian_api("v1-local-core-web-mcp", flag="false")
    app = guardian_api.app

    assert "memory_vault" not in app.state.supported_profile_enabled_labels
    assert not (VAULT_PATHS & _mounted_paths(app))


def test_quarantine_outranks_feature_flag(load_guardian_api) -> None:
    guardian_api = load_guardian_api("v1-user-profile-accent-proof", flag="true")
    app = guardian_api.app

    assert "memory_vault" not in app.state.supported_profile_enabled_labels
    assert not (VAULT_PATHS & _mounted_paths(app))


def test_vault_routes_are_get_only(load_guardian_api) -> None:
    guardian_api = load_guardian_api("v1-local-core-web-mcp")
    app = guardian_api.app

    vault_routes = [
        route for route in app.routes if getattr(route, "path", None) in VAULT_PATHS
    ]
    assert len(vault_routes) == len(VAULT_PATHS)
    for route in vault_routes:
        assert set(route.methods) == {"GET"}
