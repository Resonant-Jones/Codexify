"""Real app mounting: Preview setup is not provider execution authority."""

import importlib

import pytest
from fastapi.testclient import TestClient
from fastapi import routing as fastapi_routing

from guardian.core.dependencies import require_account_session
from guardian.core.supported_profile import load_supported_profile


@pytest.mark.parametrize(
    "mode,oauth,provider_flags,expected",
    [
        ("private_preview", "1", "1", True),
        ("private_preview", "0", "1", False),
        ("private_preview", "1", "0", False),
        ("local_safe", "1", "1", False),
    ],
)
def test_preview_mounts_only_opted_in_oauth(
    monkeypatch, mode, oauth, provider_flags, expected
):
    import guardian.guardian_api as api

    with monkeypatch.context() as env:
        env.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
        env.setenv("CODEXIFY_BETA_CORE_ONLY", "1")
        env.setenv("GUARDIAN_EXPOSURE_MODE", mode)
        env.setenv("GUARDIAN_API_KEY", "synthetic-operator-key")
        env.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", oauth)
        env.setenv("CODEXIFY_ENABLE_CONNECTIONS_ROUTES", "1")
        env.setenv("CODEXIFY_ENABLE_GITHUB_KNOWLEDGE_ROUTES", provider_flags)
        env.setenv("CODEXIFY_ENABLE_NOTION_KNOWLEDGE_ROUTES", provider_flags)
        # Even an explicit pilot opt-in cannot override the Preview quarantine.
        env.setenv("CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT", "1")
        api = importlib.reload(api)
        try:
            routes = {
                r.path: r
                for r in getattr(fastapi_routing, "iter_route_contexts", lambda routes: routes)(api.app.routes)
                if hasattr(r, "path")
            }
            assert "/api/connections" in routes
            for provider in ("notion", "github-knowledge"):
                prefix = f"/api/connect/{provider}"
                assert (f"{prefix}/oauth/start" in routes) is expected
                assert (f"{prefix}/oauth/callback" in routes) is expected
                assert f"{prefix}/configure" not in routes
                assert f"{prefix}/validate" not in routes
                assert f"{prefix}/disconnect" not in routes
                if expected:
                    route = routes[f"{prefix}/oauth/start"]
                    assert require_account_session in {
                        d.call for d in route.dependant.dependencies
                    }
            assert not any(p.startswith("/api/knowledge/") for p in routes)
            assert "/api/connectors" not in routes
            assert not any(
                p.startswith(("/api/connect/", "/api/connections", "/api/knowledge/"))
                for p in api.app.openapi()["paths"]
            )
            mounted = api.app.state.supported_profile_enabled_labels
            assert ("notion_setup" in mounted) is expected
            assert ("github_knowledge_setup" in mounted) is expected
            # No DB, provider, or real account is used by this callback refusal.
            if expected:
                client = TestClient(api.app)
                try:
                    response = client.get(
                        "/api/connect/notion/oauth/callback?code=SYNTHETIC_CODE&state=SYNTHETIC_STATE"
                    )
                    assert response.status_code == 400
                    assert "SYNTHETIC" not in response.text
                finally:
                    client.close()
        finally:
            from guardian.core import event_bus

            event_bus.reset()
    importlib.reload(api)


def test_profile_keeps_operations_quarantined():
    manifest = load_supported_profile("v1-whooshd-deepseek-web")
    for label in ("connections", "notion_setup", "github_knowledge_setup"):
        assert manifest.route_status(label) == "internal_only"
    for label in ("notion_knowledge", "github_knowledge", "connectors"):
        assert manifest.route_status(label) == "quarantined"
