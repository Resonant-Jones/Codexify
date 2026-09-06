from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.cognition import system_prompt_builder
from guardian.cognition.system_prompt_builder import (
    build_guardian_system_prompt,
)
from guardian.db.models import Base, Imprint, Persona, UserSettings
from guardian.routes import imprint as imprint_routes
from guardian.services import iddb_settings_service

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


@pytest.fixture(autouse=True)
def _settings_db(monkeypatch: pytest.MonkeyPatch):
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
            Imprint.__table__,
            Persona.__table__,
        ],
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    iddb_settings_service._set_session_factory(Session)
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)
    monkeypatch.setattr(
        imprint_routes,
        "chatlog_db",
        SimpleNamespace(get_project_identity_depth=lambda _project_id: "deep"),
        raising=False,
    )
    monkeypatch.setattr(
        system_prompt_builder, "get_docs_for", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        system_prompt_builder, "estimate_token_cost_for_docs", lambda _docs: 0
    )
    yield Session


def make_app() -> FastAPI:
    app = FastAPI()

    def _test_current_user(request: Request) -> str:
        return request.headers.get("X-User-Id") or "default"

    app.dependency_overrides[imprint_routes.get_current_user] = _test_current_user
    app.include_router(imprint_routes.router)
    app.include_router(imprint_routes.system_prompt_router)
    app.include_router(imprint_routes.system_docs_router)
    return app


def _persona_rows(Session):
    """Snapshot every persisted field, including inactive and foreign rows."""
    with Session() as session:
        return list(session.execute(select(Persona.__table__).order_by(Persona.id)))


@pytest.mark.parametrize("metrics", [{}, {"persona_draft": "Do not apply me."}])
def test_accept_imprint_does_not_create_persona(_settings_db, metrics):
    client = TestClient(make_app())
    draft = imprint_store.save_imprint("u1", 7, metrics=metrics)
    assert _persona_rows(_settings_db) == []
    response = client.post(
        "/api/imprint/accept",
        json={"imprint_id": draft.id},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert set(response.json()) == {"imprint"}
    assert imprint_store.get_imprint_by_id(draft.id).status == "active"
    assert _persona_rows(_settings_db) == []


@pytest.mark.parametrize("override", ["Override text", "", None, False, {}])
def test_accept_override_leaves_imprint_and_persona_unchanged(_settings_db, override):
    client = TestClient(make_app())
    persona_store.set_persona("u1", 7, "Keep exactly.\n", source="user")
    before = _persona_rows(_settings_db)
    draft = imprint_store.save_imprint("u1", 7)
    response = client.post(
        "/api/imprint/accept",
        json={"imprint_id": draft.id, "persona_text_override": override},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "persona_text_override is not supported for Imprint acceptance"
    )
    assert imprint_store.get_imprint_by_id(draft.id).status == "draft"
    assert _persona_rows(_settings_db) == before


def test_accept_imprint_preserves_personas_and_prompt_layers(_settings_db):
    app = make_app()
    client = TestClient(app)

    persona_store.create_persona("u1", 7, "old", "Inactive legacy text.")
    existing = persona_store.set_persona(
        "u1", 7, "Existing authored text.", source="user"
    )
    persona_store.set_persona("u2", 7, "Other user text.", source="user")
    persona_store.set_persona("u1", None, "Default text.", source="user")
    before = _persona_rows(_settings_db)

    draft = imprint_store.save_imprint(
        "u1",
        7,
        status="draft",
        guardian_name="Auri",
        preferred_name="Friend",
        style="playful-dry",
        metrics={"persona_draft": "Write with short sentences."},
    )

    response = client.post(
        "/api/imprint/accept",
        json={"imprint_id": draft.id},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["imprint"]["status"] == "active"
    assert set(payload) == {"imprint"}
    assert _persona_rows(_settings_db) == before

    active_imprint = imprint_store.get_active_imprint("u1", 7)
    active_persona = persona_store.get_active_persona("u1", 7)

    assert active_imprint is not None
    assert active_imprint.id == draft.id
    assert active_imprint.status == "active"
    assert active_persona is not None
    assert active_persona.id == existing.id
    assert active_persona.body == "Existing authored text."
    assert active_persona.is_active is True
    assert active_persona.source == "user"

    prompt, meta = build_guardian_system_prompt(
        user_id="u1",
        project_id=7,
        depth="normal",
        bundle={},
    )
    assert "=== IMPRINT_ZERO ===" in prompt
    assert "=== PERSONA ===" in prompt
    assert prompt.index("=== IMPRINT_ZERO ===") < prompt.index("=== PERSONA ===")
    assert "Auri" in prompt
    assert "Existing authored text." in prompt
    assert "Write with short sentences." not in prompt
    assert meta["resolved_imprint_source"] == "active_scope"
    assert meta["resolved_persona_source"] == "active_scope"
    assert meta["persona_has_body"] is True

    status = client.get(
        "/api/imprint/status",
        headers=AUTH_HEADERS,
        params={"project_id": 7},
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["imprint"]["status"] == "active"
    assert status_body["persona"]["source"] == "user"
    assert status_body["system_prompt_meta"]["segments_present"]["imprint"] is True
    assert status_body["system_prompt_meta"]["segments_present"]["persona"] is True
    assert set(status_body["system_prompt_meta"]) == {
        "estimated_tokens",
        "docs_count",
        "segments_present",
        "segments",
    }


def test_retired_persona_route_preserves_legacy_rows_and_status(_settings_db):
    client = TestClient(make_app())
    persona_store.create_persona("u1", 11, "old", "Inactive legacy text.")
    existing = persona_store.set_persona(
        "u1", 11, "Speak plainly and directly.", source="user"
    )
    persona_store.set_persona("u2", 11, "Other user text.", source="user")
    persona_store.set_persona("u1", None, "Default text.", source="user")
    before = _persona_rows(_settings_db)
    response = client.post(
        "/api/imprint/persona",
        json={"body": "Overwrite me", "project_id": 11},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert _persona_rows(_settings_db) == before
    assert persona_store.get_active_persona("u1", 11).id == existing.id

    prompt, meta = build_guardian_system_prompt(
        user_id="u1",
        project_id=11,
        depth="normal",
        bundle={},
    )
    assert "=== PERSONA ===" in prompt
    assert "Speak plainly and directly." in prompt
    assert "=== IMPRINT_ZERO ===" not in prompt
    assert meta["resolved_persona_source"] == "active_scope"
    assert meta["resolved_imprint_source"] == "system_default"
    assert meta["persona_has_body"] is True

    status = client.get(
        "/api/imprint/status",
        headers=AUTH_HEADERS,
        params={"project_id": 11},
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["imprint"] is None
    assert status_body["persona"]["source"] == "user"
    assert status_body["system_prompt_meta"]["segments_present"]["persona"] is True
    assert status_body["system_prompt_meta"]["segments_present"]["imprint"] is False
    assert set(status_body["system_prompt_meta"]) == {
        "estimated_tokens",
        "docs_count",
        "segments_present",
        "segments",
    }

    assert status_body["persona"]["id"] == existing.id
    assert status_body["persona"]["snippet"] == existing.body
    assert _persona_rows(_settings_db) == before


@pytest.mark.parametrize("field", ["body", "persona_prompt", "system_prompt"])
def test_retired_persona_route_cannot_create_rows(_settings_db, field):
    client = TestClient(make_app())
    assert _persona_rows(_settings_db) == []
    response = client.post(
        "/api/imprint/persona",
        json={field: "Do not create", "project_id": 11},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert _persona_rows(_settings_db) == []
