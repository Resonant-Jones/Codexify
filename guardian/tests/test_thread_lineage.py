import importlib

from fastapi.testclient import TestClient

from guardian.core import event_bus


def test_thread_branch_and_archive(tmp_path, monkeypatch):
    db_path = tmp_path / "guardian.db"
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(db_path))
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("GUARDIAN_ENABLE_CONNECTOR_SYNC", "0")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)

    parent = ga.chatlog_db.create_chat_thread(
        user_id="tester",
        title="Root Thread",
        summary="base",
        project_id=2,
    )

    with TestClient(ga.app) as client:
        resp = client.post(
            f"/api/chat/{parent['id']}/branch",
            headers={"X-API-Key": "test-key"},
            json={"title": "Child Thread"},
        )
        assert resp.status_code == 200
        child = resp.json()
        assert child["parent_id"] == parent["id"]

        branch_events = ga.chatlog_db.list_events_after(0, limit=10)
        assert any(evt["topic"] == "thread.branch" for evt in branch_events)

        resp = client.patch(
            f"/api/chat/{child['id']}",
            headers={"X-API-Key": "test-key"},
            json={"archived": True},
        )
        assert resp.status_code == 200
        archived = resp.json()
        assert archived["archived_at"] is not None

        events = ga.chatlog_db.list_events_after(0, limit=20)
        assert any(evt["topic"] == "thread.archived" for evt in events)

    event_bus.reset()
    for key in (
        "DATABASE_URL",
        "GUARDIAN_DB_PATH",
        "ENABLE_OUTBOX",
        "GUARDIAN_ENABLE_CONNECTOR_SYNC",
        "ENABLE_BLIP_MODEL",
        "GUARDIAN_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    importlib.reload(ga)
