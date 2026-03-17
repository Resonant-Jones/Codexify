import importlib
import os
from contextlib import contextmanager

from fastapi.testclient import TestClient

_GUARDIAN_API_ENV_KEYS = (
    "GUARDIAN_API_KEY",
    "ENABLE_CONNECTOR_WORKER",
    "GUARDIAN_EXPOSURE_MODE",
    "GUARDIAN_PUBLIC_PROFILE",
    "GUARDIAN_PUBLIC_ROUTES_FILE",
    "CODEXIFY_SUPPORTED_PROFILE",
)


def _snapshot_guardian_api_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _GUARDIAN_API_ENV_KEYS}


def _restore_guardian_api_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def _build_public_allowlist_client(monkeypatch):
    snapshot = _snapshot_guardian_api_env()
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
        _restore_guardian_api_env(snapshot)
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
