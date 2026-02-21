"""Route tests for durable tool job persistence."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.db import models
from guardian.routes import tools


class _FakeSession:
    def __init__(self, store: dict[str, models.ToolJob]) -> None:
        self._store = store

    def add(self, obj: Any) -> None:
        if isinstance(obj, models.ToolJob):
            now = datetime.now(UTC)
            if obj.created_at is None:
                obj.created_at = now
            obj.updated_at = now
            self._store[obj.id] = obj

    def commit(self) -> None:
        return None

    def refresh(self, obj: Any) -> None:
        return None

    def get(self, model: Any, key: str) -> models.ToolJob | None:
        if model is models.ToolJob:
            return self._store.get(key)
        return None


class _FakeDB:
    def __init__(self) -> None:
        self.jobs: dict[str, models.ToolJob] = {}

    @contextmanager
    def get_session(self):
        yield _FakeSession(self.jobs)


@pytest.fixture
def tools_client():
    fake_db = _FakeDB()
    tools.configure_db(fake_db)

    app = FastAPI()
    app.include_router(tools.router)
    app.dependency_overrides[tools.require_api_key] = lambda: "test-api-key"

    with TestClient(app) as client:
        yield client, fake_db

    app.dependency_overrides.clear()
    tools.configure_db(None)
    tools.JOBS.clear()


def test_tools_execute_persists_success_job(tools_client):
    client, fake_db = tools_client

    response = client.post(
        "/api/tools/execute",
        json={"name": "echo", "args": {"value": 42}},
    )

    assert response.status_code == 200
    body = response.json()
    UUID(body["job_id"])
    assert body["status"] == "succeeded"
    assert body["result"] == {"ok": True, "tool": "echo", "args": {"value": 42}}

    persisted = fake_db.jobs[body["job_id"]]
    assert persisted.tool_name == "echo"
    assert persisted.status == "succeeded"
    assert persisted.request_json == {"name": "echo", "args": {"value": 42}}
    assert persisted.result_json == body["result"]
    assert persisted.error is None


def test_tools_job_get_reads_persisted_result(tools_client):
    client, fake_db = tools_client

    execute = client.post(
        "/api/tools/execute",
        json={"name": "echo", "args": {"kind": "persist"}},
    )
    assert execute.status_code == 200
    job_id = execute.json()["job_id"]

    get_job = client.get(f"/api/tools/jobs/{job_id}")
    assert get_job.status_code == 200

    body = get_job.json()
    assert body["job_id"] == job_id
    assert body["tool_name"] == "echo"
    assert body["status"] == "succeeded"
    assert body["result"] == {
        "ok": True,
        "tool": "echo",
        "args": {"kind": "persist"},
    }
    assert body["error"] is None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
    assert job_id in fake_db.jobs


def test_tools_execute_persists_failed_job(tools_client, monkeypatch):
    client, fake_db = tools_client

    def _boom(_body):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools, "_dispatch_tool", _boom)

    response = client.post(
        "/api/tools/execute",
        json={"name": "explode", "args": {}},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    job_id = detail["job_id"]

    assert detail["status"] == "failed"
    assert "RuntimeError: boom" in detail["error"]

    persisted = fake_db.jobs[job_id]
    assert persisted.tool_name == "explode"
    assert persisted.status == "failed"
    assert persisted.result_json is None
    assert "RuntimeError: boom" in (persisted.error or "")
    assert persisted.error_json is not None
    assert persisted.error_json["type"] == "RuntimeError"
