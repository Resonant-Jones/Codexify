import os

VALID_KEY = os.environ["GUARDIAN_API_KEY"]


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
