"""Private-preview user-to-user messaging route posture and registration proof.

Loads the real Guardian application under the canonical private-preview
supported profile (v1-whooshd-deepseek-web) and proves that the existing
People messaging route family and the existing share-link route family are
both actually mounted, without promoting unrelated quarantined route
families.

Route-profile activation only: this does not qualify People messaging or
share links for release, and it does not widen default Beta support.
"""

from __future__ import annotations

import importlib

import pytest

from guardian.core.supported_profile import load_supported_profile


@pytest.fixture
def private_preview_guardian_api(monkeypatch, tmp_path):
    """Load the real application with the canonical private-preview profile."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    try:
        yield guardian_api
    finally:
        monkeypatch.setenv(
            "CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp"
        )
        importlib.reload(guardian_api)


def test_private_preview_profile_manifest_admits_messaging_and_share() -> None:
    """The profile manifest is the route gate for the private-preview lane."""
    manifest = load_supported_profile("v1-whooshd-deepseek-web")

    assert manifest.route_status("direct_messages") == "enabled"
    assert manifest.route_status("share") == "enabled"


def test_private_preview_profile_registers_messaging_and_share_routers(
    private_preview_guardian_api,
) -> None:
    guardian_api = private_preview_guardian_api

    enabled_labels = guardian_api.app.state.supported_profile_enabled_labels
    assert {"direct_messages", "share"} <= enabled_labels

    openapi_paths = set(guardian_api.app.openapi().get("paths", {}))

    # Representative People messaging routes from guardian/routes/direct_messages.py
    for dm_path in {
        "/api/direct-messages/profiles",
        "/api/direct-messages/relationships",
        "/api/direct-messages/conversations",
        "/api/direct-messages/requests",
    }:
        assert dm_path in openapi_paths

    # Representative share routes from guardian/routes/share.py
    for share_path in {"/api/share", "/api/share/{token}"}:
        assert share_path in openapi_paths


def test_private_preview_profile_keeps_high_blast_families_quarantined(
    private_preview_guardian_api,
) -> None:
    """Admitting People messaging and share links must not promote the
    federation, collaboration, connector, flow, tool, or orchestration
    families."""
    guardian_api = private_preview_guardian_api

    enabled_labels = guardian_api.app.state.supported_profile_enabled_labels
    for label in {
        "federation",
        "collaboration",
        "connectors",
        "flows",
        "tools",
        "api_tools",
        "agent",
        "agent_orchestration",
        "agent_orchestration_chat",
    }:
        assert label not in enabled_labels

    openapi_paths = set(guardian_api.app.openapi().get("paths", {}))
    for quarantined_prefix in {
        "/api/federation",
        "/api/collab",
        "/api/connectors",
        "/api/flows",
        "/api/agents",
    }:
        assert not any(
            path.startswith(quarantined_prefix) for path in openapi_paths
        )


def test_share_read_path_remains_a_bearer_credential(private_preview_guardian_api) -> None:
    """`GET /api/share/{token}` deliberately carries no Guardian auth
    dependency: the link token is the credential. This pins the documented
    posture so the bearer semantics cannot be silently widened."""
    guardian_api = private_preview_guardian_api

    share_read = next(
        route
        for route in guardian_api.app.routes
        if getattr(route, "path", "") == "/api/share/{token}"
    )

    dependencies = list(
        getattr(getattr(share_read, "dependant", None), "dependencies", []) or []
    )
    assert dependencies == []
