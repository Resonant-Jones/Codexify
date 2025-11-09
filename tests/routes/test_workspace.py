from __future__ import annotations

import types
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Stub optional heavy deps to keep app import minimal
    import sys
    sys.modules.setdefault("notion_client", types.SimpleNamespace(Client=object))

    # Stub heavy server modules that drag in CLI stacks
    from fastapi import APIRouter
    tools_stub = types.ModuleType("guardian.server.tools_api")
    tools_stub.router = APIRouter()
    sys.modules["guardian.server.tools_api"] = tools_stub

    # Prepare workspace module with fakes before app import
    import guardian.routes.workspace as ws

    class FakeChatDB:
        def get_chat_thread(self, thread_id: int):
            return {
                "id": thread_id,
                "user_id": "u1",
                "title": "Test Thread",
                "summary": "",
                "project_id": 1,
                "parent_id": None,
                "archived_at": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }

    # Monkeypatch chat DB & documents collector & sensors
    monkeypatch.setattr(ws, "chatlog_db", FakeChatDB(), raising=True)

    def fake_collect_docs(thread_id: int):
        return [
            {"id": "d1", "title": "Session notes - Test Thread", "relation": "autosave", "created_at": "2025-01-01T00:00:00Z"}
        ]

    monkeypatch.setattr(ws, "_collect_thread_documents", fake_collect_docs, raising=True)

    class FakeSensors:
        def __init__(self, *_args, **_kwargs):
            pass

        def snapshot(self):
            return {"cpu": 10.0, "memory": 20.0}

    monkeypatch.setattr(ws, "Sensors", FakeSensors, raising=True)

    # Now import the app (workspace router is included)
    from guardian.server.app import app
    return TestClient(app)


def test_workspace_endpoint_combines_data(client: TestClient):
    resp = client.get("/api/workspace/123")
    assert resp.status_code == 200
    data = resp.json()
    assert "thread" in data
    assert "documents" in data
    assert "diagnostics" in data
    assert data["thread"]["id"] == 123
    assert isinstance(data["documents"], list)
    assert "cpu" in data["diagnostics"]
    assert "memory" in data["diagnostics"]
