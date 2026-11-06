"""Characterisation of the abandoned 'processing' document sweeper.

A killed document-embed worker leaves a row in ``embedding_status =
'processing'``. The sweeper that lives inside the existing worker process
must terminally fail those rows without stealing documents that a live worker
is actively embedding.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, select, update
from sqlalchemy.orm import sessionmaker

from guardian.core.config import Settings
from guardian.db.models import UploadedDocument
from guardian.workers import document_embed_worker as worker

_STALE_SECONDS = 900.0
_NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/documents.sqlite")
    table = Table(
        "uploaded_documents", MetaData(),
        *(Column(c.name, c.type, primary_key=c.primary_key)
          for c in UploadedDocument.__table__.columns),
    )
    table.create(engine)
    return SimpleNamespace(get_session=sessionmaker(bind=engine)), engine


def _insert(session, doc_id, *, status, started_at, parsed_text="document body"):
    session.add(
        UploadedDocument(
            id=doc_id,
            user_id="probe",
            filename=f"{doc_id}.txt",
            filesize=12,
            mime_type="text/plain",
            src_url=f"/tmp/{doc_id}.txt",
            parsed_text=parsed_text,
            embedding_status=status,
            embedding_started_at=started_at,
        )
    )


def _state(session, doc_id):
    row = session.execute(
        select(
            UploadedDocument.embedding_status,
            UploadedDocument.embedding_error,
            UploadedDocument.embedding_started_at,
            UploadedDocument.embedding_completed_at,
        ).where(UploadedDocument.id == doc_id)
    ).one()
    return {
        "status": row[0],
        "error": row[1],
        "started_at": row[2],
        "completed_at": row[3],
    }


def test_killed_worker_leftover_reaches_a_terminal_failure(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "abandoned",
            status="processing",
            started_at=_NOW - timedelta(hours=2),
        )
        session.commit()

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        now=_NOW,
    )

    assert failed == ["abandoned"]
    with db.get_session() as session:
        state = _state(session, "abandoned")
    assert state["status"] == "failed"
    assert state["error"] == worker.ABANDONED_PROCESSING_REASON
    assert state["completed_at"] is not None
    engine.dispose()


def test_abandoned_document_without_parsed_text_records_its_own_reason(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "no-text",
            status="processing",
            started_at=_NOW - timedelta(hours=2),
            parsed_text=None,
        )
        session.commit()

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        now=_NOW,
    )

    assert failed == ["no-text"]
    with db.get_session() as session:
        state = _state(session, "no-text")
    assert state["status"] == "failed"
    assert state["error"] == worker.ABANDONED_PROCESSING_NO_TEXT_REASON
    engine.dispose()


def test_live_worker_document_is_not_stolen(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "live",
            status="processing",
            started_at=_NOW - timedelta(seconds=5),
        )
        session.commit()

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        now=_NOW,
    )

    assert failed == []
    with db.get_session() as session:
        state = _state(session, "live")
    assert state["status"] == "processing"
    assert state["error"] is None
    assert state["completed_at"] is None
    engine.dispose()


def test_deliberately_failed_document_is_not_resurrected(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "explicit-failure",
            status="failed",
            started_at=_NOW - timedelta(hours=5),
        )
        session.commit()

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        now=_NOW,
    )

    assert failed == []
    with db.get_session() as session:
        state = _state(session, "explicit-failure")
    assert state["status"] == "failed"
    assert state["error"] is None
    engine.dispose()


def test_sweep_claims_a_bounded_number_of_documents_per_pass(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        for index in range(60):
            _insert(
                session,
                f"stuck-{index:03d}",
                status="processing",
                started_at=_NOW - timedelta(hours=2, seconds=index),
            )
        session.commit()

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        batch_limit=50,
        now=_NOW,
    )

    assert len(failed) == 50
    with db.get_session() as session:
        remaining = session.execute(
            select(UploadedDocument.id).where(
                UploadedDocument.embedding_status == "processing"
            )
        ).all()
    assert len(remaining) == 10
    engine.dispose()


def test_running_the_sweep_twice_is_safe(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "abandoned",
            status="processing",
            started_at=_NOW - timedelta(hours=2),
        )
        session.commit()

    first = worker.sweep_abandoned_processing_documents(
        db, stale_after_seconds=_STALE_SECONDS, now=_NOW
    )
    with db.get_session() as session:
        state_after_first = _state(session, "abandoned")

    second = worker.sweep_abandoned_processing_documents(
        db, stale_after_seconds=_STALE_SECONDS, now=_NOW
    )
    with db.get_session() as session:
        state_after_second = _state(session, "abandoned")

    assert first == ["abandoned"]
    assert second == []
    assert state_after_first == state_after_second
    engine.dispose()


class _ReclaimingSession:
    """Session proxy that re-claims a document just before the sweeper writes.

    This models a live worker that picked the same document up again between
    the sweeper's candidate read and its conditional UPDATE.
    """

    def __init__(self, session, doc_id):
        self._session = session
        self._doc_id = doc_id
        self._calls = 0

    def __enter__(self):
        self._session.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._session.__exit__(*exc_info)

    def __getattr__(self, name):
        return getattr(self._session, name)

    def execute(self, statement, *args, **kwargs):
        self._calls += 1
        if self._calls == 2:
            self._session.execute(
                update(UploadedDocument)
                .where(UploadedDocument.id == self._doc_id)
                .values(embedding_started_at=_NOW)
                .execution_options(synchronize_session=False)
            )
        return self._session.execute(statement, *args, **kwargs)


def test_document_reclaimed_after_the_candidate_read_is_not_clobbered(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "reclaimed",
            status="processing",
            started_at=_NOW - timedelta(hours=2),
        )
        session.commit()

    real_sessionmaker = db.get_session

    def get_session():
        return _ReclaimingSession(real_sessionmaker(), "reclaimed")

    db.get_session = get_session

    failed = worker.sweep_abandoned_processing_documents(
        db,
        stale_after_seconds=_STALE_SECONDS,
        now=_NOW,
    )

    assert failed == []
    with real_sessionmaker() as session:
        state = _state(session, "reclaimed")
    assert state["status"] == "processing"
    assert state["error"] is None
    assert state["completed_at"] is None
    engine.dispose()


def test_conditional_update_requires_the_observed_claim_timestamp(tmp_path):
    db, engine = _make_db(tmp_path)
    with db.get_session() as session:
        _insert(
            session,
            "claimed",
            status="processing",
            started_at=_NOW - timedelta(hours=2),
        )
        session.commit()

    statement = worker._abandoned_processing_statement(
        [("claimed", _NOW - timedelta(hours=3))],
        completed_at=_NOW,
    )
    with db.get_session() as session:
        result = session.execute(statement)
        updated = result.fetchall()
        session.commit()

    assert updated == []
    with db.get_session() as session:
        state = _state(session, "claimed")
    assert state["status"] == "processing"
    engine.dispose()


def test_worker_process_runs_the_sweeper_without_a_new_service(monkeypatch, tmp_path):
    db, engine = _make_db(tmp_path)
    sweeps = []

    monkeypatch.setattr(worker, "_get_db", lambda: db)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(
            DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS=5,
            DOCUMENT_EMBED_STALE_SECONDS=_STALE_SECONDS,
            DOCUMENT_EMBED_SWEEP_INTERVAL_SECONDS=60,
            DOCUMENT_EMBED_SWEEP_BATCH_LIMIT=50,
        ),
    )
    monkeypatch.setattr(
        worker,
        "_run_abandoned_processing_sweep",
        lambda db, **kwargs: sweeps.append(kwargs) or [],
    )

    def dequeue(**_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(worker, "dequeue_document_embed", dequeue)

    with pytest.raises(KeyboardInterrupt):
        worker.run_forever()

    assert len(sweeps) == 1
    assert sweeps[0]["stale_after_seconds"] == _STALE_SECONDS
    assert sweeps[0]["batch_limit"] == 50
    engine.dispose()


def test_sweeper_settings_are_declared_with_bounded_defaults():
    settings = Settings(_env_file=None)
    assert settings.DOCUMENT_EMBED_STALE_SECONDS == 900.0
    assert settings.DOCUMENT_EMBED_SWEEP_INTERVAL_SECONDS == 60.0
    assert settings.DOCUMENT_EMBED_SWEEP_BATCH_LIMIT == 50

    from pydantic import ValidationError

    for invalid in (0, -1, 86401, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, DOCUMENT_EMBED_STALE_SECONDS=invalid)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DOCUMENT_EMBED_SWEEP_BATCH_LIMIT=0)
