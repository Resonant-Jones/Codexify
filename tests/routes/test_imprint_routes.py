import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    Base,
    ImprintFoldState,
    ImprintObservation,
    UserSettings,
)
from guardian.routes import imprint as imprint_routes
from guardian.services import (
    iddb_settings_service,
    imprint_fold_service,
    imprint_observation_service,
)

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


@pytest.fixture(autouse=True)
def _settings_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            UserSettings.__table__,
            ImprintObservation.__table__,
            ImprintFoldState.__table__,
        ],
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    iddb_settings_service._set_session_factory(Session)
    imprint_observation_service._set_session_factory(Session)
    imprint_fold_service._set_session_factory(Session)
    yield


def make_app():
    app = FastAPI()
    app.include_router(imprint_routes.router)
    app.include_router(imprint_routes.system_prompt_router)
    app.include_router(imprint_routes.system_docs_router)
    return app


def test_proposal_and_accept_flow():
    app = make_app()
    client = TestClient(app)

    draft_imprint = SimpleNamespace(
        id=1,
        user_id="u1",
        project_id=None,
        guardian_name="Name",
        preferred_name="friend",
        status="draft",
        heat_score=0.5,
        metrics={"persona_draft": "seed persona"},
    )
    active_imprint = SimpleNamespace(
        **{**draft_imprint.__dict__, "status": "active"}
    )
    persona_obj = SimpleNamespace(
        id=9, body="seed persona", source="imprint_zero_seed", is_active=True
    )

    with patch.object(
        imprint_routes.imprint_store, "save_imprint", return_value=draft_imprint
    ):
        resp = client.post(
            "/api/imprint/proposal", json={}, headers=AUTH_HEADERS
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imprint_draft"]["id"] == 1
    assert "persona_draft" in data

    with (
        patch.object(
            imprint_routes.imprint_store,
            "get_imprint_by_id",
            return_value=draft_imprint,
        ),
        patch.object(
            imprint_routes.imprint_store,
            "activate_imprint",
            return_value=active_imprint,
        ),
        patch.object(
            imprint_routes.persona_store,
            "set_persona",
            return_value=persona_obj,
        ),
    ):
        resp = client.post(
            "/api/imprint/accept",
            json={"imprint_id": 1},
            headers=AUTH_HEADERS,
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["imprint"]["status"] == "active"
    assert payload["persona"]["id"] == persona_obj.id


def test_accept_with_user_override_marks_source_user():
    app = make_app()
    client = TestClient(app)
    draft_imprint = SimpleNamespace(
        id=1,
        user_id="u1",
        project_id=None,
        guardian_name="Name",
        preferred_name="friend",
        status="draft",
        heat_score=0.5,
        metrics={"persona_draft": "seed persona"},
    )
    active_imprint = SimpleNamespace(
        **{**draft_imprint.__dict__, "status": "active"}
    )
    persona_obj = SimpleNamespace(
        id=9, body="override persona", source="user", is_active=True
    )

    with (
        patch.object(
            imprint_routes.imprint_store,
            "get_imprint_by_id",
            return_value=draft_imprint,
        ),
        patch.object(
            imprint_routes.imprint_store,
            "activate_imprint",
            return_value=active_imprint,
        ),
        patch.object(
            imprint_routes.persona_store,
            "set_persona",
            return_value=persona_obj,
        ),
    ):
        resp = client.post(
            "/api/imprint/accept",
            json={"imprint_id": 1, "persona_text_override": "override persona"},
            headers=AUTH_HEADERS,
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["persona"]["source"] == "user"


def test_reject_marks_superseded():
    app = make_app()
    client = TestClient(app)
    imprint_obj = SimpleNamespace(id=2, user_id="u1", status="draft")
    with patch.object(
        imprint_routes.imprint_store,
        "get_imprint_by_id",
        return_value=imprint_obj,
    ):
        with patch.object(
            imprint_routes.imprint_store,
            "supersede_imprint",
            return_value=imprint_obj,
        ):
            resp = client.post(
                "/api/imprint/reject",
                json={"imprint_id": 2},
                headers=AUTH_HEADERS,
            )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_system_prompt_summary():
    app = make_app()
    client = TestClient(app)

    meta = {
        "estimated_tokens": 1200,
        "docs_count": 1,
        "segments": [
            {
                "name": "base",
                "chars": 40,
                "estimated_tokens": 10,
                "truncated": False,
            }
        ],
    }
    with patch.object(
        imprint_routes,
        "build_guardian_system_prompt",
        return_value=("SECRET_PROMPT_CONTENT", meta),
    ):
        resp = client.get("/api/system_prompt/summary", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_tokens"] == 1200
    assert body["estimated_tokens_total"] == 1200
    assert body["docs_count"] == 1
    assert body["threshold"]["status"] == "ok"
    assert body["segments"][0]["name"] == "base"
    assert "SECRET_PROMPT_CONTENT" not in json.dumps(body)


def test_system_prompt_summary_threshold_boundaries():
    app = make_app()
    client = TestClient(app)

    with patch.object(
        imprint_routes,
        "build_guardian_system_prompt",
        return_value=("prompt", {"estimated_tokens": 6100, "segments": []}),
    ):
        warn_resp = client.get(
            "/api/system_prompt/summary", headers=AUTH_HEADERS
        )
    assert warn_resp.status_code == 200
    assert warn_resp.json()["threshold"]["status"] == "warn"

    with patch.object(
        imprint_routes,
        "build_guardian_system_prompt",
        return_value=("prompt", {"estimated_tokens": 8100, "segments": []}),
    ):
        hard_resp = client.get(
            "/api/system_prompt/summary", headers=AUTH_HEADERS
        )
    assert hard_resp.status_code == 200
    assert hard_resp.json()["threshold"]["status"] == "hard"


def test_system_prompt_summary_unknown_when_builder_unavailable():
    app = make_app()
    client = TestClient(app)

    with patch.object(
        imprint_routes,
        "build_guardian_system_prompt",
        side_effect=RuntimeError("boom"),
    ):
        resp = client.get("/api/system_prompt/summary", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["threshold"]["status"] == "unknown"
    assert body["estimated_tokens_total"] is None


def test_system_docs_toggle():
    app = make_app()
    client = TestClient(app)
    doc = SimpleNamespace(
        id=5,
        title="Doc",
        scope="user",
        is_enabled=True,
        content="System doc content",
    )
    with patch.object(
        imprint_routes.system_doc_store,
        "list_docs_with_links",
        return_value=[(doc, True)],
    ):
        resp = client.get("/api/system_docs", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["docs"][0]["id"] == 5

    with patch.object(
        imprint_routes.system_doc_store, "set_doc_link", return_value=None
    ):
        resp = client.post(
            "/api/system_docs/toggle",
            json={"doc_id": 5, "enabled": False},
            headers=AUTH_HEADERS,
        )
    assert resp.status_code == 200
