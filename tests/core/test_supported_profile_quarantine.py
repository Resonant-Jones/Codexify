import importlib
from contextlib import contextmanager

from fastapi.testclient import TestClient


@contextmanager
def _build_supported_profile_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    client = TestClient(guardian_api.app)
    try:
        yield client
    finally:
        client.close()
        from guardian.core import event_bus

        event_bus.reset()
        importlib.reload(guardian_api)


def test_supported_profile_quarantines_legacy_tools_and_hides_command_bus_schema(
    monkeypatch,
) -> None:
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        assert (
            client.get("/api/tools/manifest", headers=headers).status_code
            == 404
        )
        assert client.get("/tools/manifest", headers=headers).status_code == 404

        command_manifest = client.get(
            "/api/guardian/commands/manifest", headers=headers
        )
        assert command_manifest.status_code == 200

        openapi = client.get("/openapi.json").json()
        assert "/api/guardian/commands/manifest" not in openapi.get("paths", {})
        assert "/api/tools/manifest" not in openapi.get("paths", {})
        assert "/tools/manifest" not in openapi.get("paths", {})
