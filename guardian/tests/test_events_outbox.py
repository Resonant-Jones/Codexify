import asyncio
import json
import importlib

import pytest
from fastapi.testclient import TestClient

from guardian.core import event_bus
from guardian.connectors import github as github_module


def test_events_outbox_replay_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "guardian.db"))
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("GUARDIAN_ENABLE_CONNECTOR_SYNC", "0")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)

    with TestClient(ga.app) as client:
        event_bus.emit_event("message.created", {"thread_id": 1, "content": "hi"})

        received = None
        with client.stream(
            "GET",
            "/api/events",
            headers={"Last-Event-ID": "0", "X-API-Key": "test-key"},
        ) as stream:
            buffer = ""
            for chunk in stream.iter_raw():
                if not chunk:
                    continue
                buffer += chunk.decode()
                while "\n\n" in buffer:
                    frame, buffer = buffer.split("\n\n", 1)
                    if not frame.strip() or frame.startswith("retry:"):
                        continue
                    lines = frame.splitlines()
                    data_line = next(
                        (line for line in lines if line.startswith("data:")), None
                    )
                    if data_line is None:
                        continue
                    payload_str = data_line.split(":", 1)[1].strip() or "{}"
                    received = json.loads(payload_str)
                    break
                if received is not None:
                    break

        assert received == {"thread_id": 1, "content": "hi"}
        remaining = ga.chatlog_db.list_events_after(0, limit=10)
        assert remaining == []

    event_bus.reset()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DB_PATH", raising=False)
    monkeypatch.delenv("ENABLE_OUTBOX", raising=False)
    monkeypatch.delenv("GUARDIAN_ENABLE_CONNECTOR_SYNC", raising=False)
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    importlib.reload(ga)


def test_github_connector_worker_stores_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "guardian.db"))
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)

    created = ga.chatlog_db.create_connector_config(
        "github-test", "github", {"owner": "octocat", "repo": "hello-world"}
    )

    sample_docs = [
        {
            "external_id": "issue:1",
            "payload": {"kind": "issue", "data": {"number": 1}},
            "fetched_at": "2023-01-01T00:00:00+00:00",
        }
    ]

    monkeypatch.setattr(github_module, "sync_repo", lambda owner, repo, token: sample_docs)

    asyncio.run(ga._run_github_sync(created))

    last_run = ga.chatlog_db.get_last_connector_run(created["id"])
    assert last_run is not None
    assert last_run["status"] == "succeeded"

    docs = ga.chatlog_db.list_raw_documents_for_config(created["id"])
    assert len(docs) == 1
    assert docs[0]["payload"]["kind"] == "issue"

    events = ga.chatlog_db.list_events_after(0, limit=10)
    statuses = [event.get("payload", {}).get("status") for event in events]
    assert "succeeded" in statuses

    event_bus.reset()
    importlib.reload(ga)
