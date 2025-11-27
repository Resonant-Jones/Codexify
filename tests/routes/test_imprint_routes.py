from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import imprint as imprint_routes


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
        resp = client.post("/api/imprint/proposal", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["imprint_draft"]["id"] == 1
    assert "persona_draft" in data

    with patch.object(
        imprint_routes.imprint_store,
        "get_imprint_by_id",
        return_value=draft_imprint,
    ), patch.object(
        imprint_routes.imprint_store,
        "activate_imprint",
        return_value=active_imprint,
    ), patch.object(
        imprint_routes.persona_store, "set_persona", return_value=persona_obj
    ):
        resp = client.post("/api/imprint/accept", json={"imprint_id": 1})
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

    with patch.object(
        imprint_routes.imprint_store,
        "get_imprint_by_id",
        return_value=draft_imprint,
    ), patch.object(
        imprint_routes.imprint_store,
        "activate_imprint",
        return_value=active_imprint,
    ), patch.object(
        imprint_routes.persona_store, "set_persona", return_value=persona_obj
    ):
        resp = client.post(
            "/api/imprint/accept",
            json={"imprint_id": 1, "persona_text_override": "override persona"},
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["persona"]["source"] == "user"


def test_reject_marks_superseded():
    app = make_app()
    client = TestClient(app)
    imprint_obj = SimpleNamespace(id=2, status="draft")
    with patch.object(
        imprint_routes.imprint_store,
        "supersede_imprint",
        return_value=imprint_obj,
    ):
        resp = client.post("/api/imprint/reject", json={"imprint_id": 2})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_system_prompt_summary():
    app = make_app()
    client = TestClient(app)

    meta = {
        "estimated_tokens": 1200,
        "docs_count": 1,
        "segments": {"base": 10, "persona": 5},
    }
    with patch.object(
        imprint_routes,
        "build_guardian_system_prompt",
        return_value=("prompt", meta),
    ):
        resp = client.get("/api/system_prompt/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_tokens"] == 1200
    assert body["docs_count"] == 1


def test_system_docs_toggle():
    app = make_app()
    client = TestClient(app)
    doc = SimpleNamespace(id=5, title="Doc", scope="user", is_enabled=True, content="System doc content")
    with patch.object(
        imprint_routes.system_doc_store,
        "list_docs_with_links",
        return_value=[(doc, True)],
    ):
        resp = client.get("/api/system_docs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["docs"][0]["id"] == 5

    with patch.object(
        imprint_routes.system_doc_store, "set_doc_link", return_value=None
    ):
        resp = client.post(
            "/api/system_docs/toggle", json={"doc_id": 5, "enabled": False}
        )
    assert resp.status_code == 200
