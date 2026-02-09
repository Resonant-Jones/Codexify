from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

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


@pytest.fixture
def approval_db() -> _DB:
    db = _DB()
    approval.configure_db(db)
    browser_routes.configure_db(db)
    return db


@pytest.fixture
def browser_client(monkeypatch: pytest.MonkeyPatch, approval_db: _DB) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    app = FastAPI()
    app.include_router(browser_routes.router)
    return TestClient(app)


def test_blocked_operation_creates_approval_and_audit(approval_db: _DB) -> None:
    with pytest.raises(approval.ApprovalRequiredError) as exc:
        approval.require_approval_for_operation(
            operation="evaluate",
            target="https://example.com",
            actor="tester",
            reason="needs review",
        )

    approval_id = exc.value.approval_id
    approvals = approval.list_approvals()
    assert approvals
    assert approvals[0]["id"] == approval_id
    assert approvals[0]["status"] == "PENDING"

    with approval_db.get_session() as session:
        audit_rows = session.execute(
            select(approval.browser_audit_log).where(
                approval.browser_audit_log.c.approval_id == approval_id
            )
        ).all()
    assert len(audit_rows) == 1
    assert audit_rows[0].status == "blocked"


def test_pending_only_transition_enforced() -> None:
    created = approval.create_approval_request(
        operation="cookie.set",
        target="https://example.com",
        actor="tester",
        request_reason="cookie write",
    )
    approved = approval.decide_approval(
        approval_id=created["id"],
        decision="APPROVED",
        actor="approver",
        decision_reason="safe",
    )
    assert approved["status"] == "APPROVED"

    with pytest.raises(approval.ApprovalTransitionError):
        approval.decide_approval(
            approval_id=created["id"],
            decision="DENIED",
            actor="approver2",
            decision_reason="late deny",
        )


def test_audit_always_written_for_non_dangerous_op(approval_db: _DB) -> None:
    approval.require_approval_for_operation(
        operation="content",
        target="https://example.com",
        actor="tester",
        reason="read content",
    )
    with approval_db.get_session() as session:
        rows = session.execute(select(approval.browser_audit_log)).all()
    assert rows
    assert rows[0].status == "allowed"


def test_routes_list_and_decide(browser_client: TestClient) -> None:
    created = approval.create_approval_request(
        operation="evaluate",
        target="https://example.com",
        actor="tester",
        request_reason="eval",
    )
    headers = {"X-API-Key": "test-api-key"}

    list_response = browser_client.get("/api/browser/approvals", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["count"] >= 1

    approve_response = browser_client.post(
        f"/api/browser/approvals/{created['id']}/approve",
        headers=headers,
        json={"reason": "approved"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    conflict_response = browser_client.post(
        f"/api/browser/approvals/{created['id']}/approve",
        headers=headers,
        json={"reason": "second approve"},
    )
    assert conflict_response.status_code == 409
