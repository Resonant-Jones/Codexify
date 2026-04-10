from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
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
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
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
        "guardian.cognition.system_prompt_builder.get_docs_for",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.estimate_token_cost_for_docs",
        lambda _docs: 0,
    )
    yield


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(imprint_routes.router)
    app.include_router(imprint_routes.system_prompt_router)
    app.include_router(imprint_routes.system_docs_router)
    return app


def test_accept_imprint_promotes_active_records_and_prompt_layers():
    app = make_app()
    client = TestClient(app)

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
    assert payload["persona"]["source"] == "imprint_zero_seed"

    active_imprint = imprint_store.get_active_imprint("u1", 7)
    active_persona = persona_store.get_active_persona("u1", 7)

    assert active_imprint is not None
    assert active_imprint.id == draft.id
    assert active_imprint.status == "active"
    assert active_persona is not None
    assert active_persona.body == "Write with short sentences."
    assert active_persona.is_active is True
    assert active_persona.source == "imprint_zero_seed"

    prompt, meta = build_guardian_system_prompt(
        user_id="u1",
        project_id=7,
        depth="normal",
        bundle={},
    )
    assert "=== IMPRINT_ZERO ===" in prompt
    assert "=== PERSONA ===" in prompt
    assert prompt.index("=== IMPRINT_ZERO ===") < prompt.index(
        "=== PERSONA ==="
    )
    assert "Auri" in prompt
    assert "Write with short sentences." in prompt
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
    assert status_body["persona"]["source"] == "imprint_zero_seed"
    assert (
        status_body["system_prompt_meta"]["segments_present"]["imprint"] is True
    )
    assert (
        status_body["system_prompt_meta"]["segments_present"]["persona"] is True
    )
    assert set(status_body["system_prompt_meta"]) == {
        "estimated_tokens",
        "docs_count",
        "segments_present",
        "segments",
    }


def test_update_persona_persists_project_scoped_active_persona_and_prompt_layers():
    app = make_app()
    client = TestClient(app)

    response = client.post(
        "/api/imprint/persona",
        json={"body": "Speak plainly and directly.", "project_id": 11},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "user"
    assert payload["is_active"] is True

    active_persona = persona_store.get_active_persona("u1", 11)
    assert active_persona is not None
    assert active_persona.body == "Speak plainly and directly."
    assert active_persona.is_active is True
    assert persona_store.get_active_persona("u1", None) is None

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
    assert (
        status_body["system_prompt_meta"]["segments_present"]["persona"] is True
    )
    assert (
        status_body["system_prompt_meta"]["segments_present"]["imprint"]
        is False
    )
    assert set(status_body["system_prompt_meta"]) == {
        "estimated_tokens",
        "docs_count",
        "segments_present",
        "segments",
    }
