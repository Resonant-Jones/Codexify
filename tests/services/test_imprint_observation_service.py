from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, ImprintObservation
from guardian.services import imprint_observation_service


@pytest.fixture()
def observation_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[ImprintObservation.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    imprint_observation_service._set_session_factory(Session)
    return Session


def test_append_observation_is_append_only_and_idempotent(
    observation_session_factory,
):
    first = imprint_observation_service.append_observation(
        "u1",
        7,
        schema_version=2,
        provenance={"source": "chat", "thread_id": 9},
        idempotency_key="obs-1",
        signal_type="Speech Pattern",
        signal_payload={
            "communication": {"tone": "direct"},
            "name_hints": ["Ari"],
        },
    )
    duplicate = imprint_observation_service.append_observation(
        "u1",
        7,
        schema_version=2,
        provenance={"source": "chat", "thread_id": 9},
        idempotency_key="obs-1",
        signal_type="Speech Pattern",
        signal_payload={
            "communication": {"tone": "warm"},
            "name_hints": ["Mira"],
        },
    )

    assert first.id == duplicate.id
    assert first.schema_version == 2
    assert first.provenance["source"] == "chat"
    assert first.signal_payload["communication"]["tone"] == "direct"

    Session = observation_session_factory
    with Session() as session:
        rows = session.scalars(select(ImprintObservation)).all()
    assert len(rows) == 1
    assert rows[0].idempotency_key == "obs-1"
