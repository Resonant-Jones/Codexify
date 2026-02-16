from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.cron.scheduler import CRON_QUEUE_NAME, tick_once
from guardian.db import models as db_models
from guardian.workers.cron_worker import process_cron_message


class _TestDB:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def get_session(self):  # noqa: ANN201
        return self._session_factory()


def _make_test_db() -> _TestDB:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    db_models.CronJob.__table__.create(bind=engine)
    db_models.CronRun.__table__.create(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )
    return _TestDB(session_factory)


def test_cron_scheduler_execution_creates_run_and_enqueues_due_job() -> None:
    db = _make_test_db()
    now = datetime.now(timezone.utc)

    with db.get_session() as session:
        job = db_models.CronJob(
            name="test cron",
            schedule="*/5 * * * *",
            job_type="noop",
            payload={"x": 1},
            is_enabled=True,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        previous = db_models.CronRun(
            job_id=job.id,
            status="succeeded",
            created_at=now - timedelta(minutes=10),
            started_at=now - timedelta(minutes=10),
            finished_at=now - timedelta(minutes=9),
            result={"ok": True},
        )
        session.add(previous)
        session.commit()

    captured: list[tuple[dict[str, Any], str]] = []

    def _capture(payload: dict[str, Any], queue_name: str) -> None:
        captured.append((payload, queue_name))

    run_ids = tick_once(db=db, now=now, enqueue_fn=_capture, emit_events=False)

    assert len(run_ids) == 1
    assert captured
    queued_payload, queue_name = captured[0]
    assert queue_name == CRON_QUEUE_NAME
    assert int(queued_payload["cron_run_id"]) == run_ids[0]
    assert int(queued_payload["cron_job_id"]) > 0
    assert queued_payload["job_type"] == "noop"

    with db.get_session() as session:
        run = session.query(db_models.CronRun).filter_by(id=run_ids[0]).first()
        assert run is not None
        assert run.status == "queued"


def test_cron_worker_execution_marks_run_succeeded() -> None:
    db = _make_test_db()

    with db.get_session() as session:
        job = db_models.CronJob(
            name="worker job",
            schedule="@hourly",
            job_type="noop",
            payload={"key": "value"},
            is_enabled=True,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        run = db_models.CronRun(job_id=job.id, status="queued")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
        job_id = job.id

    called: list[tuple[str, dict[str, Any] | None]] = []

    def _executor(
        *, job_type: str, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        called.append((job_type, payload))
        return {"ok": True, "echo": payload}

    ok = process_cron_message(
        {
            "cron_run_id": run_id,
            "cron_job_id": job_id,
            "job_type": "noop",
            "payload": {"k": 1},
        },
        db=db,
        executor=_executor,
        emit_events=False,
    )

    assert ok is True
    assert called == [("noop", {"k": 1})]

    with db.get_session() as session:
        run = session.query(db_models.CronRun).filter_by(id=run_id).first()
        assert run is not None
        assert run.status == "succeeded"
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.error is None
        assert isinstance(run.result, dict)
        assert run.result.get("ok") is True
