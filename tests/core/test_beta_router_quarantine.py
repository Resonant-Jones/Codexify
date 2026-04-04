import importlib
from contextlib import contextmanager

from fastapi.testclient import TestClient

from guardian.vector import store as vector_store_module


@contextmanager
def _build_beta_core_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_BETA_CORE_ONLY", "1")

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


def test_beta_core_only_quarantines_non_core_routers(monkeypatch) -> None:
    with _build_beta_core_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        class _NoopVectorStore:
            def __init__(self) -> None:
                self.items: list[dict[str, object]] = []

            def add_texts(self, items):
                self.items.extend(items)
                return len(items)

        quarantined_paths = [
            "/api/connectors",
            "/api/federation/manifest",
            "/api/flows",
            "/api/tools/manifest",
            "/api/guardian/commands/manifest",
            "/api/cron/jobs",
            "/api/codex/entries",
            "/dev/plugins",
            "/api/ui/session",
        ]
        for path in quarantined_paths:
            response = client.get(path, headers=headers)
            assert response.status_code == 404, (
                f"expected 404 for quarantined path {path}, "
                f"got {response.status_code}"
            )

        # Core surfaces must remain mounted in beta core-only mode.
        assert client.get("/health").status_code != 404
        assert (
            client.get("/api/chat/threads", headers=headers).status_code != 404
        )
        assert (
            client.get(
                "/api/upload-chatgpt-export", headers=headers
            ).status_code
            != 404
        )
        assert (
            client.post("/api/media/documents", headers=headers).status_code
            != 404
        )
        monkeypatch.setattr(
            vector_store_module, "VectorStore", _NoopVectorStore
        )
        assert (
            client.post(
                "/api/embeddings",
                headers=headers,
                json={"texts": ["beta-core check"], "embedder": "dummy"},
            ).status_code
            != 404
        )
