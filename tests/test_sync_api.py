import json
from fastapi.testclient import TestClient

from guardian.server.app import app


client = TestClient(app)


def test_health_sync():
    r = client.get("/health/sync")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_post_event_idempotent_persona_set(tmp_path, monkeypatch):
    # Ensure DB path is deterministic for test isolation if needed
    # monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "guardian.db"))

    body = {"event_id": "e1", "type": "persona.set", "payload": {"user_id": "u1", "persona": "Default"}}
    r1 = client.post("/api/sync/event", json=body)
    r2 = client.post("/api/sync/event", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json().get("idempotent") in (True, False)  # first may be not idempotent
    assert r2.json().get("idempotent") is True

