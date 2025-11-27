from fastapi.testclient import TestClient

from guardian.server.app import app
from guardian.vector.store import VectorStore

client = TestClient(app)


def test_health_vector():
    r = client.get("/health/vector")
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "error")


def test_retrieve_simple(tmp_path, monkeypatch):
    # Point index to temp dir for isolation
    monkeypatch.setenv("GUARDIAN_INDEX_DIR", str(tmp_path / "index"))
    vs = VectorStore()
    vs.add_texts(
        [
            {
                "text": "ThreadSpace is the experiential layer.",
                "meta": {"src": "demo"},
            },
            {"text": "PulseOS handles orchestration.", "meta": {"src": "demo"}},
            {
                "text": "Guardian provides ethics filter.",
                "meta": {"src": "demo"},
            },
        ]
    )
    r = client.post("/api/retrieve", json={"q": "orchestration", "k": 2})
    assert r.status_code == 200
    matches = r.json().get("matches")
    assert isinstance(matches, list)
    assert matches, "should return at least one match"
