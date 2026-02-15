import importlib
import os
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient


def _write_allowlist_file(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "version: 1",
                "",
                "profiles:",
                "  minimal_health:",
                "    allow:",
                "      - method: GET",
                "        path: /health",
                "      - method: GET",
                "        path: /ping",
            ]
        ),
        encoding="utf-8",
    )
    return path


@contextmanager
def _build_client(
    *,
    mode: str,
    profile: str,
    routes_file: Path,
    monkeypatch,
) -> TestClient:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", mode)
    monkeypatch.setenv("GUARDIAN_PUBLIC_PROFILE", profile)
    monkeypatch.setenv("GUARDIAN_PUBLIC_ROUTES_FILE", str(routes_file))
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    client = TestClient(guardian_api.app)
    try:
        yield client
    finally:
        client.close()
        # Reset module-global app wiring for the rest of the suite.
        os.environ["GUARDIAN_EXPOSURE_MODE"] = "local_safe"
        os.environ["ENABLE_CONNECTOR_WORKER"] = "0"
        os.environ.pop("GUARDIAN_PUBLIC_ROUTES_FILE", None)
        os.environ.pop("GUARDIAN_PUBLIC_PROFILE", None)
        from guardian.core import event_bus

        event_bus.reset()
        importlib.reload(guardian_api)


def test_public_allowlist_allows_health_and_denies_non_allowlisted_routes(
    monkeypatch, tmp_path: Path
) -> None:
    routes_file = _write_allowlist_file(tmp_path / "public_routes.yaml")

    with _build_client(
        mode="public_allowlist",
        profile="minimal_health",
        routes_file=routes_file,
        monkeypatch=monkeypatch,
    ) as client:
        health_resp = client.get("/health")
        assert health_resp.status_code == 200

        denied_resp = client.get("/docs")
        assert denied_resp.status_code == 403
        assert denied_resp.json() == {"ok": False, "error": "forbidden"}


def test_local_safe_mode_does_not_gate_non_allowlisted_routes(
    monkeypatch, tmp_path: Path
) -> None:
    routes_file = _write_allowlist_file(tmp_path / "public_routes.yaml")

    with _build_client(
        mode="local_safe",
        profile="minimal_health",
        routes_file=routes_file,
        monkeypatch=monkeypatch,
    ) as client:
        resp = client.get("/docs")
        assert resp.status_code != 403


def test_malformed_allowlist_fails_closed_with_deny_all(
    monkeypatch, tmp_path: Path
) -> None:
    malformed = tmp_path / "malformed_public_routes.yaml"
    malformed.write_text("version: [", encoding="utf-8")

    with _build_client(
        mode="public_allowlist",
        profile="minimal_health",
        routes_file=malformed,
        monkeypatch=monkeypatch,
    ) as client:
        health_resp = client.get("/health")
        assert health_resp.status_code == 403
        assert health_resp.json() == {"ok": False, "error": "forbidden"}

        denied_resp = client.get("/docs")
        assert denied_resp.status_code == 403
        assert denied_resp.json() == {"ok": False, "error": "forbidden"}
