from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.contracts.imprint_snapshot import ImprintSignalSnapshot
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
    imprint_signal_snapshot_service,
)


@pytest.fixture()
def snapshot_session_factory():
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


def test_snapshot_is_stable_for_identical_folded_state(
    snapshot_session_factory,
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
        7,
        idempotency_key="snapshot-obs",
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

    snapshot1 = imprint_signal_snapshot_service.build_imprint_signal_snapshot(
        user_id="u1",
        project_id=7,
        requested_depth="deep",
        project_identity_depth="deep",
    )
    snapshot2 = imprint_signal_snapshot_service.build_imprint_signal_snapshot(
        user_id="u1",
        project_id=7,
        requested_depth="deep",
        project_identity_depth="deep",
    )

    assert isinstance(snapshot1, ImprintSignalSnapshot)
    assert snapshot1.snapshot_version == 1
    assert snapshot1.builder_version == "imprint-snapshot-v1"
    assert snapshot1.snapshot_hash == snapshot2.snapshot_hash
    assert snapshot1.canonical_json() == snapshot2.canonical_json()
    assert (
        snapshot1.effective_state["communication_profile"]["tone"] == "direct"
    )
