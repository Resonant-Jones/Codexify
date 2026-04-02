from __future__ import annotations

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
from guardian.services.imprint_proposal_service import build_imprint_proposal
from guardian.services.imprint_signal_snapshot_service import (
    build_imprint_signal_snapshot,
)


@pytest.fixture()
def isolation_session_factory():
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


def _seed_user(user_id: str):
    iddb_settings_service.upsert_user_settings(
        user_id,
        {
            "memory_mode": "deep",
            "diary_requires_unlock": False,
            "allow_sensitive_modeling": True,
        },
    )


def test_folded_state_and_proposals_do_not_bleed_across_users_or_projects(
    isolation_session_factory,
):
    _seed_user("u1")
    _seed_user("u2")

    imprint_observation_service.append_observation(
        "u1",
        None,
        idempotency_key="u1-global",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "communication": {"tone": "warm", "verbosity": "balanced"},
            "persona_hints": ["u1-global"],
            "prompt_hints": ["u1-global"],
            "name_hints": ["Aurora"],
        },
    )
    imprint_observation_service.append_observation(
        "u1",
        1,
        idempotency_key="u1-p1",
        signal_type="speech_pattern",
        provenance={"source": "chat"},
        signal_payload={
            "communication": {"tone": "direct", "verbosity": "concise"},
            "persona_hints": ["u1-project1"],
            "prompt_hints": ["u1-project1"],
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
            "communication": {"tone": "curious", "verbosity": "detailed"},
            "persona_hints": ["u1-project2"],
            "prompt_hints": ["u1-project2"],
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
            "communication": {"tone": "formal", "verbosity": "concise"},
            "persona_hints": ["u2-project1"],
            "prompt_hints": ["u2-project1"],
            "name_hints": ["Atlas"],
        },
    )

    snapshot_u1_p1 = build_imprint_signal_snapshot(
        user_id="u1",
        project_id=1,
        requested_depth="light",
        project_identity_depth="light",
    )
    snapshot_u1_p2 = build_imprint_signal_snapshot(
        user_id="u1",
        project_id=2,
        requested_depth="light",
        project_identity_depth="light",
    )
    snapshot_u2_p1 = build_imprint_signal_snapshot(
        user_id="u2",
        project_id=1,
        requested_depth="light",
        project_identity_depth="light",
    )

    proposal_u1_p1 = build_imprint_proposal(snapshot_u1_p1)
    proposal_u1_p2 = build_imprint_proposal(snapshot_u1_p2)
    proposal_u2_p1 = build_imprint_proposal(snapshot_u2_p1)

    assert "u1-global" in snapshot_u1_p1.effective_state["combined_markers"]
    assert (
        "u1-project2" not in snapshot_u1_p1.effective_state["combined_markers"]
    )
    assert (
        "u2-project1" not in snapshot_u1_p1.effective_state["combined_markers"]
    )
    assert snapshot_u1_p1.snapshot_hash != snapshot_u1_p2.snapshot_hash
    assert snapshot_u1_p1.snapshot_hash != snapshot_u2_p1.snapshot_hash
    assert proposal_u1_p1.proposal_name != proposal_u1_p2.proposal_name
    assert proposal_u1_p1.proposal_name != proposal_u2_p1.proposal_name
