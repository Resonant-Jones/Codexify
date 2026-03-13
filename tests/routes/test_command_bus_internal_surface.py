import importlib
from contextlib import contextmanager

from fastapi.testclient import TestClient


@contextmanager
def _build_public_allowlist_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "public_allowlist")
    monkeypatch.setenv("GUARDIAN_PUBLIC_PROFILE", "connectors_runtime")
    monkeypatch.setenv(
        "GUARDIAN_PUBLIC_ROUTES_FILE", "config/public_routes.yaml"
    )
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


def test_public_allowlist_blocks_internal_command_bus_surface(
    monkeypatch,
) -> None:
    with _build_public_allowlist_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        response = client.get(
            "/api/guardian/commands/manifest", headers=headers
        )

        assert response.status_code == 403
        assert response.json() == {"ok": False, "error": "forbidden"}
