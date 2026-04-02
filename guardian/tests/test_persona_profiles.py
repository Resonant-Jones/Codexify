from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.system_profiles import store as persona_profile_store
from guardian.db import models as db_models
from guardian.routes import persona_profiles


@contextmanager
def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_models.Base.metadata.create_all(
        engine,
        tables=[db_models.PersonaProfile.__table__],
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    persona_profile_store._set_session_factory(session_factory)

    app = FastAPI()
    app.include_router(persona_profiles.router)
    app.dependency_overrides[
        persona_profiles.require_api_key
    ] = lambda: "test-api-key"

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        persona_profile_store._set_session_factory(None)


def test_persona_profile_routes_create_list_read_and_update():
    with _build_client() as client:
        create_response = client.post(
            "/api/persona-profiles",
            json={
                "id": "profile-runtime",
                "name": "Runtime Persona",
                "system_prompt": "You are a runtime persona.",
                "model_provider": "OpenAI",
                "model_id": "gpt-4o",
                "temperature": 0.4,
            },
        )
        assert create_response.status_code == 200, create_response.text
        created = create_response.json()["profile"]
        assert created["id"] == "profile-runtime"
        assert created["name"] == "Runtime Persona"
        assert created["system_prompt"] == "You are a runtime persona."
        assert created["model_provider"] == "openai"
        assert created["model_id"] == "gpt-4o"
        assert created["temperature"] == 0.4
        assert created["created_at"]
        assert created["updated_at"]

        list_response = client.get("/api/persona-profiles")
        assert list_response.status_code == 200, list_response.text
        profiles = list_response.json()["profiles"]
        assert [profile["id"] for profile in profiles] == ["profile-runtime"]

        read_response = client.get("/api/persona-profiles/profile-runtime")
        assert read_response.status_code == 200, read_response.text
        assert read_response.json()["profile"]["name"] == "Runtime Persona"

        update_response = client.patch(
            "/api/persona-profiles/profile-runtime",
            json={
                "name": "Runtime Persona Updated",
                "system_prompt": "Updated system prompt.",
                "model_provider": "Anthropic",
                "model_id": "claude-sonnet-4-20250514",
                "temperature": 0.2,
            },
        )
        assert update_response.status_code == 200, update_response.text
        updated = update_response.json()["profile"]
        assert updated["name"] == "Runtime Persona Updated"
        assert updated["system_prompt"] == "Updated system prompt."
        assert updated["model_provider"] == "anthropic"
        assert updated["model_id"] == "claude-sonnet-4-20250514"
        assert updated["temperature"] == 0.2
        assert updated["updated_at"] >= updated["created_at"]
