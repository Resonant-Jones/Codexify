from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    Base,
    ImprintFoldState,
    ImprintObservation,
    UserSettings,
)
from guardian.services import (
    iddb_settings_service,
    imprint_fold_service,
    imprint_observation_service,
)


@pytest.fixture()
def fold_session_factory():
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


def _seed_settings(user_id: str, **payload):
    return iddb_settings_service.upsert_user_settings(user_id, payload)


def test_fold_state_is_deterministic_for_the_same_observation_set(
    fold_session_factory,
):
    _seed_settings(
        "u1",
        memory_mode="deep",
        diary_requires_unlock=False,
        allow_sensitive_modeling=True,
    )
    imprint_observation_service.append_observation(
        "u1",
        7,
        idempotency_key="obs-u1-project",
        signal_type="speech_pattern",
        provenance={"source": "chat", "requested_depth": "light"},
        signal_payload={
            "communication": {
                "tone": "direct",
                "verbosity": "concise",
                "formality": "casual",
            },
            "persona_hints": ["keep answers grounded"],
            "prompt_hints": ["ask clarifying questions"],
            "name_hints": ["Ari"],
            "question_topics": ["preferences"],
        },
    )

    first = imprint_fold_service.refresh_project_state(
        "u1",
        7,
        project_identity_depth="deep",
    )
    second = imprint_fold_service.refresh_project_state(
        "u1",
        7,
        project_identity_depth="deep",
    )

    assert first["state_hash"] == second["state_hash"]
    assert first["state_payload"] == second["state_payload"]
    assert first["state_payload"]["communication_profile"]["tone"] == "direct"
    assert first["state_payload"]["prompt_hints"] == [
        "ask clarifying questions"
    ]


def test_fold_state_is_scope_isolated(fold_session_factory):
    _seed_settings(
        "u1",
        memory_mode="deep",
        diary_requires_unlock=False,
        allow_sensitive_modeling=True,
    )
    _seed_settings(
        "u2",
        memory_mode="deep",
        diary_requires_unlock=False,
        allow_sensitive_modeling=True,
    )

    imprint_observation_service.append_observation(
        "u1",
        1,
        idempotency_key="u1-p1",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "persona_hints": ["u1 project1"],
            "name_hints": ["Nova"],
        },
    )
    imprint_observation_service.append_observation(
        "u1",
        2,
        idempotency_key="u1-p2",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "persona_hints": ["u1 project2"],
            "name_hints": ["Echo"],
        },
    )
    imprint_observation_service.append_observation(
        "u2",
        1,
        idempotency_key="u2-p1",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "persona_hints": ["u2 project1"],
            "name_hints": ["Mira"],
        },
    )

    state_u1_p1 = imprint_fold_service.refresh_project_state(
        "u1", 1, project_identity_depth="deep"
    )
    state_u1_p2 = imprint_fold_service.refresh_project_state(
        "u1", 2, project_identity_depth="deep"
    )
    state_u2_p1 = imprint_fold_service.refresh_project_state(
        "u2", 1, project_identity_depth="deep"
    )

    assert "u1 project1" in state_u1_p1["state_payload"]["persona_hints"]
    assert "u1 project2" not in state_u1_p1["state_payload"]["persona_hints"]
    assert "u1 project2" in state_u1_p2["state_payload"]["persona_hints"]
    assert "u2 project1" in state_u2_p1["state_payload"]["persona_hints"]
    assert state_u1_p1["state_hash"] != state_u1_p2["state_hash"]
    assert state_u1_p1["state_hash"] != state_u2_p1["state_hash"]


@pytest.mark.parametrize(
    "settings_payload, provenance, project_identity_depth",
    [
        (
            {
                "memory_mode": "deep",
                "diary_requires_unlock": False,
                "allow_sensitive_modeling": False,
            },
            {"source": "chat"},
            "deep",
        ),
        (
            {
                "memory_mode": "none",
                "diary_requires_unlock": False,
                "allow_sensitive_modeling": True,
            },
            {"source": "chat"},
            "deep",
        ),
        (
            {
                "memory_mode": "deep",
                "diary_requires_unlock": True,
                "allow_sensitive_modeling": True,
            },
            {"source": "chat", "is_diary": True},
            "deep",
        ),
        (
            {
                "memory_mode": "deep",
                "diary_requires_unlock": False,
                "allow_sensitive_modeling": True,
            },
            {"source": "chat", "requested_depth": "deep"},
            "light",
        ),
    ],
)
def test_fold_state_respects_consent_and_modeling_gates(
    fold_session_factory,
    settings_payload,
    provenance,
    project_identity_depth,
):
    _seed_settings("u1", **settings_payload)
    imprint_observation_service.append_observation(
        "u1",
        9,
        idempotency_key=f"blocked-{project_identity_depth}-{settings_payload['memory_mode']}",
        signal_type="speech_pattern",
        provenance=provenance,
        signal_payload={
            "persona_hints": ["blocked hint"],
            "prompt_hints": ["blocked prompt"],
            "name_hints": ["Blocked"],
        },
    )

    state = imprint_fold_service.refresh_project_state(
        "u1",
        9,
        project_identity_depth=project_identity_depth,
    )

    assert state["source_observation_count"] == 0
    assert state["state_payload"]["persona_hints"] == []
    assert state["state_payload"]["prompt_hints"] == []
    assert state["state_payload"]["name_hints"] == []
