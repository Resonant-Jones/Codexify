from __future__ import annotations

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


@pytest.fixture()
def proposal_session_factory():
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
    return Session


def make_app():
    app = FastAPI()
    app.include_router(imprint_routes.router)
    return app


def test_imprint_proposal_returns_backend_authoritative_outputs(
    proposal_session_factory,
):
    iddb_settings_service.upsert_user_settings(
        "u1",
        {
            "memory_mode": "deep",
            "diary_requires_unlock": False,
            "allow_sensitive_modeling": True,
        },
    )
    imprint_observation_service.append_observation(
        "u1",
        None,
        idempotency_key="u1-global-1",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "communication": {
                "tone": "direct",
                "verbosity": "concise",
                "formality": "casual",
            },
            "persona_hints": ["keep answers grounded"],
            "prompt_hints": ["ask clarifying questions"],
            "name_hints": ["Ari"],
        },
    )
    imprint_observation_service.append_observation(
        "u1",
        7,
        idempotency_key="u1-project-1",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "communication": {
                "tone": "direct",
                "verbosity": "concise",
                "formality": "casual",
            },
            "persona_hints": ["project grounded"],
            "prompt_hints": ["prefer short answers"],
            "name_hints": ["Nova"],
        },
    )

    app = make_app()
    client = TestClient(app)

    def _fake_save_imprint(**kwargs):
        return SimpleNamespace(
            id=42,
            user_id=kwargs["user_id"],
            project_id=kwargs["project_id"],
            guardian_name=kwargs["guardian_name"],
            preferred_name=kwargs["preferred_name"],
            status=kwargs["status"],
            heat_score=kwargs["heat_score"],
        )

    with patch.object(
        imprint_routes.imprint_store,
        "save_imprint",
        side_effect=_fake_save_imprint,
    ) as mock_save:
        response = client.post(
            "/api/imprint/proposal",
            json={"project_id": 7},
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    body = response.json()
    proposal = body["proposal"]
    assert body["name"] == proposal["proposal_name"]
    assert body["persona_draft"] == proposal["persona_draft"]
    assert body["prompt_metadata"] == proposal["prompt_metadata"]
    assert body["prompt_metadata"]["snapshot_hash"] == proposal["snapshot_hash"]
    assert body["imprint_draft"]["guardian_name"] == body["name"]
    assert body["imprint_draft"]["preferred_name"] == proposal["preferred_name"]
    assert proposal["scope_kind"] == "project_scoped"
    assert proposal["generator_version"] == "imprint-proposal-v1"
    assert proposal["proposal_hash"]
    assert proposal["proposal_version"] == 1
    assert body["prompt_metadata"]["proposal_name"] == body["name"]
    assert body["prompt_metadata"]["generator_version"] == "imprint-proposal-v1"
    assert body["prompt_metadata"]["prompt_hints"] == [
        "ask clarifying questions",
        "prefer short answers",
    ]
    assert body["prompt_metadata"]["persona_hints"] == [
        "keep answers grounded",
        "project grounded",
    ]

    called = mock_save.call_args.kwargs
    assert called["guardian_name"] == body["name"]
    assert called["metrics"]["proposal_name"] == body["name"]
    assert called["metrics"]["snapshot_hash"] == proposal["snapshot_hash"]
    assert called["metrics"]["prompt_metadata"]["generator_version"] == (
        "imprint-proposal-v1"
    )
