"""Friends-and-family Hosted Room route posture and registration proof."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def friends_family_guardian_api(monkeypatch, tmp_path):
    """Load the real application with the tester supported profile."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-friends-family-web")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
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


def test_tester_profile_registers_hosted_room_routers_in_openapi(
    friends_family_guardian_api,
) -> None:
    guardian_api = friends_family_guardian_api

    enabled_labels = guardian_api.app.state.supported_profile_enabled_labels
    assert {"hosted_rooms", "hosted_room_guest"} <= enabled_labels

    openapi_paths = set(guardian_api.app.openapi().get("paths", {}))
    assert (
        "/api/hosted-rooms/{room_id}/actors/{participant_id}/invoke"
        in openapi_paths
    )
    assert (
        "/api/hosted-room-session/actors/{participant_id}/invoke"
        in openapi_paths
    )
