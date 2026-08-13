"""Whoosh'd/DeepSeek tester Hosted Room route posture and registration proof.

Loads the real Guardian application under the canonical friends/family
tester supported profile (v1-whooshd-deepseek-web) and proves that the
existing Hosted Room owner and guest routers are actually mounted, without
promoting unrelated quarantined route families.

Route-profile activation only: this does not qualify Hosted Rooms, guest
sessions, Guardian invocation, or any collaboration surface for release.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def whooshd_deepseek_guardian_api(monkeypatch, tmp_path):
    """Load the real application with the canonical tester supported profile."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
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


def test_whooshd_deepseek_profile_registers_hosted_room_routers_in_openapi(
    whooshd_deepseek_guardian_api,
) -> None:
    guardian_api = whooshd_deepseek_guardian_api

    enabled_labels = guardian_api.app.state.supported_profile_enabled_labels
    assert {"hosted_rooms", "hosted_room_guest"} <= enabled_labels

    openapi_paths = set(guardian_api.app.openapi().get("paths", {}))

    # Representative owner routes from guardian/routes/hosted_rooms.py
    for owner_path in {
        "/api/hosted-rooms",
        "/api/hosted-rooms/{room_id}",
        "/api/hosted-rooms/{room_id}/messages",
    }:
        assert owner_path in openapi_paths

    # Representative guest routes from guardian/routes/hosted_room_guest.py
    for guest_path in {
        "/api/hosted-room-invitations/exchange",
        "/api/hosted-room-session",
        "/api/hosted-room-session/messages",
    }:
        assert guest_path in openapi_paths


def test_whooshd_deepseek_profile_keeps_existing_guardian_invocation_routes(
    whooshd_deepseek_guardian_api,
) -> None:
    """The existing Guardian invocation routes are part of the mounted router
    families and remain exactly what the current routers expose."""
    guardian_api = whooshd_deepseek_guardian_api

    openapi_paths = set(guardian_api.app.openapi().get("paths", {}))

    assert (
        "/api/hosted-rooms/{room_id}/actors/{participant_id}/invoke"
        in openapi_paths
    )
    assert (
        "/api/hosted-room-session/actors/{participant_id}/invoke"
        in openapi_paths
    )


def test_whooshd_deepseek_profile_does_not_promote_quarantined_families(
    whooshd_deepseek_guardian_api,
) -> None:
    """Enabling the Hosted Room labels must not promote federation,
    collaboration, connector, flow, tool, or orchestration surfaces."""
    guardian_api = whooshd_deepseek_guardian_api

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

    # Representative router prefixes for the quarantined route families.
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
