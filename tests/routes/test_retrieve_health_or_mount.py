from __future__ import annotations

import importlib
import os
from contextlib import contextmanager

from fastapi.testclient import TestClient

from guardian.core.config import (
    VECTOR_STORE_PROOF_STATUS_READY,
    resolve_vector_store_runtime,
)

_GUARDIAN_API_ENV_KEYS = (
    "GUARDIAN_API_KEY",
    "ENABLE_CONNECTOR_WORKER",
    "GUARDIAN_EXPOSURE_MODE",
    "CODEXIFY_SUPPORTED_PROFILE",
    "CODEXIFY_EMBEDDINGS_BACKEND",
    "CODEXIFY_VECTOR_STORE",
    "CODEXIFY_CHROMA_PATH",
    "CODEXIFY_COLLECTION",
)


class _FakeVectorStore:
    def __init__(self) -> None:
        self.runtime = resolve_vector_store_runtime()
        self.search_calls: list[dict[str, object]] = []

    def search(self, query: str, k: int = 5, namespace: str | None = None):
        self.search_calls.append(
            {"query": query, "k": k, "namespace": namespace}
        )
        if "fresh-sentinel" not in query:
            return []
        return [
            {
                "text": "fresh-sentinel from backend search",
                "meta": {"doc_id": "doc-1", "namespace": "thread:9"},
                "metadata": {"doc_id": "doc-1", "namespace": "thread:9"},
                "score": 0.99,
            }
        ]


def _snapshot_guardian_api_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _GUARDIAN_API_ENV_KEYS}


def _restore_guardian_api_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def _supported_profile_client(monkeypatch, tmp_path):
    snapshot = _snapshot_guardian_api_env()
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "supported"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "supported_retrieval_health")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    fake_store = _FakeVectorStore()

    def _init_services(_db):
        guardian_api.dependencies._vector_store = fake_store
        return fake_store, object()

    monkeypatch.setattr(guardian_api, "init_services", _init_services)
    client = TestClient(guardian_api.app)
    try:
        guardian_api.dependencies._vector_store = fake_store
        yield client, fake_store
    finally:
        client.close()
        from guardian.core import event_bus

        event_bus.reset()
        _restore_guardian_api_env(snapshot)
        if not os.environ.get("GUARDIAN_API_KEY"):
            os.environ["GUARDIAN_API_KEY"] = "test-api-key"
            try:
                importlib.reload(guardian_api)
            finally:
                _restore_guardian_api_env(snapshot)
        else:
            importlib.reload(guardian_api)


def test_supported_path_exposes_truthful_retrieval_health_surface(
    monkeypatch,
    tmp_path,
) -> None:
    with _supported_profile_client(monkeypatch, tmp_path) as (
        client,
        fake_store,
    ):
        response = client.get(
            "/api/health/retrieval",
            params={"q": "fresh-sentinel", "k": 2, "namespace": "thread:9"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == VECTOR_STORE_PROOF_STATUS_READY
        assert payload["ok"] is True
        assert payload["proof_capable"] is True
        assert payload["same_runtime_as_worker"] is True
        assert (
            payload["worker_write_runtime"] == payload["backend_search_runtime"]
        )
        assert payload["backend_store_source"] == "shared"
        assert payload["search"]["executed"] is True
        assert payload["search"]["match_count"] == 1
        assert (
            payload["search"]["matches"][0]["text"]
            == "fresh-sentinel from backend search"
        )
        assert fake_store.search_calls == [
            {"query": "fresh-sentinel", "k": 2, "namespace": "thread:9"}
        ]

        headers = {"X-API-Key": "test-api-key"}
        assert (
            client.get("/api/tools/manifest", headers=headers).status_code
            == 404
        )
