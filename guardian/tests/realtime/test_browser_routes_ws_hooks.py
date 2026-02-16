from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.browser import approval
from guardian.routes import browser as browser_routes


class _DB:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        approval.ensure_tables(engine)
        self._session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )

    @contextmanager
    def get_session(self) -> Iterator:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@dataclass
class _FakeSession:
    session_id: str
    profile_dir: Path
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


class _FakeSessionManager:
    def __init__(self) -> None:
        now = datetime(2026, 2, 7, tzinfo=timezone.utc)
        self._now = now
        self._sessions: dict[str, _FakeSession] = {}
        self._counter = 0

    def create_session(self) -> _FakeSession:
        self._counter += 1
        session_id = f"s-{self._counter}"
        session = _FakeSession(
            session_id=session_id,
            profile_dir=Path(f"/tmp/{session_id}"),
            created_at=self._now,
            last_used_at=self._now,
            expires_at=self._now + timedelta(minutes=5),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> _FakeSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise RuntimeError(f"session not found: {session_id}")
        return session

    def close_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None


@pytest.fixture
def browser_ws_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, list[tuple[str, dict]]]:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    db = _DB()
    approval.configure_db(db)
    browser_routes.configure_db(db)
    browser_routes.configure_session_manager(_FakeSessionManager())  # type: ignore[arg-type]

    emitted: list[tuple[str, dict]] = []

    def _capture(name: str, payload: dict) -> None:
        emitted.append((name, payload))

    monkeypatch.setattr(browser_routes, "_emit", _capture)

    app = FastAPI()
    app.include_router(browser_routes.router)
    return TestClient(app), emitted


def test_approval_request_emits_event(
    browser_ws_client: tuple[TestClient, list[tuple[str, dict]]]
) -> None:
    client, emitted = browser_ws_client
    resp = client.post(
        "/api/browser/approvals/request",
        headers={"X-API-Key": "test-api-key"},
        json={
            "operation": "evaluate",
            "target": "https://example.com",
            "reason": "needs review",
        },
    )
    assert resp.status_code == 200
    assert emitted
    assert emitted[-1][0] == "browser.approval.requested"
    assert emitted[-1][1]["approval_id"] == resp.json()["id"]


def test_approval_decision_emits_event(
    browser_ws_client: tuple[TestClient, list[tuple[str, dict]]]
) -> None:
    client, emitted = browser_ws_client
    create_resp = client.post(
        "/api/browser/approvals/request",
        headers={"X-API-Key": "test-api-key"},
        json={"operation": "evaluate", "target": "https://example.com"},
    )
    approval_id = create_resp.json()["id"]
    decide_resp = client.post(
        f"/api/browser/approvals/{approval_id}/approve",
        headers={"X-API-Key": "test-api-key"},
        json={"reason": "approved"},
    )
    assert decide_resp.status_code == 200
    assert emitted[-1][0] == "browser.approval.decided"
    assert emitted[-1][1]["approval_id"] == approval_id


def test_session_updates_emit_event(
    browser_ws_client: tuple[TestClient, list[tuple[str, dict]]]
) -> None:
    client, emitted = browser_ws_client

    create_resp = client.post(
        "/api/browser/sessions",
        headers={"X-API-Key": "test-api-key"},
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]
    assert emitted[-1][0] == "browser.session.updated"
    assert emitted[-1][1]["status"] == "created"

    get_resp = client.get(
        f"/api/browser/sessions/{session_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert get_resp.status_code == 200
    assert emitted[-1][0] == "browser.session.updated"
    assert emitted[-1][1]["status"] == "active"

    delete_resp = client.delete(
        f"/api/browser/sessions/{session_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert delete_resp.status_code == 200
    assert emitted[-1][0] == "browser.session.updated"
    assert emitted[-1][1]["status"] == "closed"
