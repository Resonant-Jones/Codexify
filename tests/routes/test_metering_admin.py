"""Admin-only read guard for the account metering projection."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.routes import metering_admin
from guardian.routes.account_observability import _require_account_admin


def test_non_admin_cannot_read_cross_account_usage():
    app = FastAPI()
    app.include_router(metering_admin.router)
    def deny():
        raise HTTPException(status_code=403, detail="Admin role required")
    app.dependency_overrides[_require_account_admin] = deny
    with TestClient(app) as client:
        response = client.get("/api/admin/metering/inference")
    assert response.status_code == 403


def test_admin_projection_does_not_return_prompt_content(monkeypatch):
    app = FastAPI()
    app.include_router(metering_admin.router)
    app.dependency_overrides[_require_account_admin] = lambda: "operator"
    class FakeSession:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    class FakeDB:
        def get_session(self): return FakeSession()
    monkeypatch.setattr(metering_admin, "load_guardian_db_from_env", lambda: FakeDB())
    monkeypatch.setattr(
        metering_admin, "account_inference_totals",
        lambda session, *, account_id, limit: [{
            "account_id": "one", "attempts": 1,
            "estimated_cost_usd": "0.000120000",
            "cost_is_complete": True,
        }],
    )
    with TestClient(app) as client:
        response = client.get("/api/admin/metering/inference")
    assert response.status_code == 200
    assert response.json()["accounts"][0]["account_id"] == "one"
    assert "prompt" not in response.text.lower()
    assert response.json()["mode"] == "observe_only"
