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


def test_embeddings_endpoint_minimal_payload(client):
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
