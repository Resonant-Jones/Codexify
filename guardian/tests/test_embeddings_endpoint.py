import os

import pytest

import guardian.embedding_engine as embedding_engine
from guardian.vector import store as vector_store_module

VALID_KEY = os.environ["GUARDIAN_API_KEY"]


class _FakeEmbedding:
    def tolist(self) -> list[float]:
        return [0.125, 0.875]


class _FakeLocalModel:
    def encode(self, text: str, normalize_embeddings: bool = True):
        assert normalize_embeddings is True
        assert text
        return _FakeEmbedding()


class _RecordingVectorStore:
    created: list["_RecordingVectorStore"] = []

    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []
        self.__class__.created.append(self)

    def add_texts(self, items):
        self.items.extend(items)
        return len(items)


def test_embeddings_endpoint_contract(client):
    payload = {
        "texts": ["hello embeddings"],
        "embedder": "dummy",
        "model": "unit",
    }
    response = client.post(
        "/api/embeddings",
        headers={"X-API-Key": VALID_KEY},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dummy"
    assert data["model"] == "unit"
    assert isinstance(data["vectors"], list)
    assert len(data["vectors"]) == 1
    assert isinstance(data["vectors"][0], list)
    assert len(data["vectors"][0]) > 0
    assert isinstance(data["vectors"][0][0], float)


def test_embeddings_endpoint_minimal_payload(client, monkeypatch):
    monkeypatch.delenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", raising=False)
    monkeypatch.delenv("CODEXIFY_EMBEDDINGS_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDING_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDER", raising=False)
    payload = {"texts": ["hello embeddings"]}
    response = client.post(
        "/api/embeddings",
        headers={"X-API-Key": VALID_KEY},
        json=payload,
    )
    assert response.status_code == 503
    assert "Embeddings backend is not configured" in response.json()["detail"]


def test_embeddings_endpoint_allows_dummy_fallback(client, monkeypatch):
    monkeypatch.setenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", "1")
    monkeypatch.delenv("CODEXIFY_EMBEDDINGS_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDING_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDER", raising=False)
    payload = {"texts": ["hello embeddings"]}
    response = client.post(
        "/api/embeddings",
        headers={"X-API-Key": VALID_KEY},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dummy"
    assert data["model"] is None
    assert isinstance(data["vectors"], list)
    assert len(data["vectors"]) == 1


def test_embeddings_endpoint_allows_stub_alias(client, monkeypatch):
    monkeypatch.delenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", raising=False)
    monkeypatch.delenv("CODEXIFY_EMBEDDINGS_BACKEND", raising=False)
    monkeypatch.setenv("EMBEDDING_BACKEND", "stub")
    monkeypatch.delenv("EMBEDDER", raising=False)
    payload = {"texts": ["hello embeddings"]}
    response = client.post(
        "/api/embeddings",
        headers={"X-API-Key": VALID_KEY},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dummy"


@pytest.mark.parametrize("backend_value", ["local", "local_api"])
def test_embeddings_endpoint_accepts_local_backends(
    client,
    monkeypatch,
    backend_value,
):
    _RecordingVectorStore.created.clear()
    monkeypatch.delenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", raising=False)
    monkeypatch.delenv("CODEXIFY_EMBEDDINGS_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDER", raising=False)
    monkeypatch.setenv("EMBEDDING_BACKEND", backend_value)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", "/models/bge-large-en-v1.5")
    monkeypatch.setattr(
        embedding_engine,
        "_get_bge_model",
        lambda *args, **kwargs: _FakeLocalModel(),
    )
    monkeypatch.setattr(
        vector_store_module, "VectorStore", _RecordingVectorStore
    )

    payload = {"texts": ["hello embeddings"], "model": "unit"}
    response = client.post(
        "/api/embeddings",
        headers={"X-API-Key": VALID_KEY},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == backend_value
    assert data["model"] == "unit"
    assert data["vectors"] == [[0.125, 0.875]]
    assert len(_RecordingVectorStore.created) == 1
    assert _RecordingVectorStore.created[0].items == [
        {"text": "hello embeddings", "meta": {"source": "api/embeddings"}}
    ]
