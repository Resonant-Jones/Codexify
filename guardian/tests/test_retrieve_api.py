from fastapi.testclient import TestClient

from guardian.core import dependencies
from guardian.retrieve.api import router as retrieve_router
from guardian.vector.store import VectorStore


def _make_app():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(retrieve_router)
    return app


def test_health_vector():
    with TestClient(_make_app()) as client:
        r = client.get("/health/vector")
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "error")


def test_retrieve_simple(tmp_path, monkeypatch):
    # Point index to temp dir for isolation
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("GUARDIAN_INDEX_DIR", str(tmp_path / "index"))
    vs = VectorStore()
    monkeypatch.setattr(dependencies, "_vector_store", vs, raising=False)
    vs.add_texts(
        [
            {
                "text": "Codexify is the experiential layer.",
                "meta": {"src": "demo"},
            },
            {"text": "PulseOS handles orchestration.", "meta": {"src": "demo"}},
            {
                "text": "Guardian provides ethics filter.",
                "meta": {"src": "demo"},
            },
        ]
    )
    with TestClient(_make_app()) as client:
        r = client.post("/api/retrieve", json={"q": "orchestration", "k": 2})
    assert r.status_code == 200
    matches = r.json().get("matches")
    assert isinstance(matches, list)
    assert matches, "should return at least one match"


def test_retrieve_uses_shared_runtime_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("GUARDIAN_INDEX_DIR", str(tmp_path / "index"))
    shared_store = VectorStore()
    monkeypatch.setattr(
        dependencies, "_vector_store", shared_store, raising=False
    )
    shared_store.add_texts(
        [
            {
                "text": "Built-in help explains /help and /docs.",
                "meta": {"src": "seed"},
            }
        ]
    )

    with TestClient(_make_app()) as client:
        r = client.post("/api/retrieve", json={"q": "docs", "k": 1})
    assert r.status_code == 200
    matches = r.json().get("matches")
    assert matches
    assert "Built-in help" in matches[0]["text"]
