from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db import models as db_models
from guardian.routes import cron

_API_KEY = "test-api-key"


class _TestDB:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db_models.Base.metadata.create_all(
            self.engine,
            tables=[db_models.CronJob.__table__, db_models.CronRun.__table__],
        )
        self._SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

    @contextmanager
    def get_session(self):
        session = self._SessionLocal()
        try:
            yield session
        finally:
            session.close()


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    db = _TestDB()
    cron.configure_db(db)

    app = FastAPI()
    app.include_router(cron.router)
    return TestClient(app)


def test_cron_create_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/api/cron/jobs",
        headers={"X-API-Key": ""},
        json={
            "name": "NoAuth",
            "schedule": "@hourly",
            "job_type": "noop",
            "payload": {},
            "is_enabled": True,
        },
    )
    assert response.status_code == 401


def test_cron_crud_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY}

    create_response = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Daily Sync",
            "schedule": "@daily",
            "job_type": "noop",
            "payload": {"scope": "docs"},
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    job_id = created["id"]
    assert created["name"] == "Daily Sync"
    assert created["schedule"] == "@daily"

    list_response = client.get("/api/cron/jobs", headers=headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == job_id

    get_response = client.get(f"/api/cron/jobs/{job_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == job_id

    patch_response = client.patch(
        f"/api/cron/jobs/{job_id}",
        headers=headers,
        json={"name": "Daily Sync Updated", "is_enabled": False},
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["name"] == "Daily Sync Updated"
    assert updated["is_enabled"] is False

    delete_response = client.delete(f"/api/cron/jobs/{job_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    missing_response = client.get(f"/api/cron/jobs/{job_id}", headers=headers)
    assert missing_response.status_code == 404


def test_cron_invalid_schedule_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY}

    response = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Bad Schedule",
            "schedule": "every minute forever",
            "job_type": "noop",
            "payload": {},
            "is_enabled": True,
        },
    )
    assert response.status_code == 422
    assert "Invalid schedule" in response.json()["detail"]


def test_cron_webhook_forbidden_target(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY}

    response = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Webhook Job",
            "schedule": "@hourly",
            "job_type": "webhook",
            "payload": {"url": "http://localhost:8080/hook"},
            "is_enabled": True,
        },
    )
    assert response.status_code == 422
    assert "forbidden" in response.json()["detail"]


def test_cron_webhook_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRON_WEBHOOK_ALLOWLIST", "api.example.com")
    client = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY}

    blocked = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Webhook Blocked",
            "schedule": "@hourly",
            "job_type": "webhook",
            "payload": {"url": "https://evil.example.com/hook"},
            "is_enabled": True,
        },
    )
    assert blocked.status_code == 422
    assert "ALLOWLIST" in blocked.json()["detail"]

    allowed = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Webhook Allowed",
            "schedule": "@hourly",
            "job_type": "webhook",
            "payload": {"url": "https://api.example.com/hook"},
            "is_enabled": True,
        },
    )
    assert allowed.status_code == 201


def test_cron_trigger_and_runs_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY}

    create_response = client.post(
        "/api/cron/jobs",
        headers=headers,
        json={
            "name": "Runner",
            "schedule": "@weekly",
            "job_type": "noop",
            "payload": {},
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    trigger_response = client.post(
        f"/api/cron/jobs/{job_id}/trigger",
        headers=headers,
    )
    assert trigger_response.status_code == 200
    run = trigger_response.json()
    assert run["job_id"] == job_id
    assert run["status"] == "queued"

    runs_response = client.get(f"/api/cron/jobs/{job_id}/runs", headers=headers)
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert len(runs) == 1
    assert runs[0]["id"] == run["id"]
