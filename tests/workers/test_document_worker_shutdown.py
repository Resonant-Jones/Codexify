"""Process-level checks for document worker graceful shutdown."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
import sys

import pytest


@pytest.fixture(autouse=True)
def _spawn_import_path(monkeypatch):
    # guardian/tests conftest adds guardian/ to sys.path. A fresh interpreter
    # would then resolve stdlib queue as guardian.queue before Redis imports.
    from pathlib import Path
    guardian_root = str(Path.cwd() / "guardian")
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != guardian_root])


def _idle_worker(ready) -> None:
    from guardian.workers import document_embed_worker as worker

    # No model, database, Redis or candidate resource is opened by this probe.
    worker.VectorStore = lambda: object()

    def dequeue(**_kwargs):
        ready.set()
        time.sleep(0.05)
        return None

    worker.dequeue_document_embed = dequeue
    worker.run_forever()


def test_idle_sigterm_exits_cleanly_without_starting_a_job():
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    process = context.Process(target=_idle_worker, args=(ready,))
    process.start()
    try:
        assert ready.wait(30), "worker did not reach idle dequeue"
        started = time.monotonic()
        os.kill(process.pid, signal.SIGTERM)
        process.join(3)
        assert not process.is_alive(), "idle worker did not honor shutdown"
        assert process.exitcode == 0
        assert time.monotonic() - started < 3
    finally:
        if process.is_alive():
            process.kill()
            process.join(3)
        process.close()


def _prepare_documents(root):
    import sqlite3
    from pathlib import Path

    from sqlalchemy import Column, MetaData, Table, create_engine
    from guardian.db.models import UploadedDocument

    engine = create_engine(f"sqlite:///{root}/documents.sqlite")
    table = Table(
        "uploaded_documents", MetaData(),
        *(Column(c.name, c.type, primary_key=c.primary_key)
          for c in UploadedDocument.__table__.columns),
    )
    table.create(engine)
    with engine.begin() as connection:
        for identifier in ("active", "next"):
            connection.execute(table.insert().values(
                id=identifier, parsed_text="synthetic document", filename="probe.txt",
                user_id="probe", filesize=18, mime_type="text/plain", src_url="probe",
                embedding_status="pending",
            ))
    engine.dispose()
    with sqlite3.connect(f"{root}/documents.sqlite") as connection:
        connection.executescript("""
            CREATE TABLE transitions (status TEXT);
            CREATE TRIGGER record_transition AFTER UPDATE ON uploaded_documents
            BEGIN INSERT INTO transitions VALUES (NEW.embedding_status); END;
        """)
    Path(root, "queue.json").write_text('[{"doc_id":"active"},{"doc_id":"next"}]')


class _ProbeVectorStore:
    def __init__(self, root, mode):
        self.root = root
        self.mode = mode

    def add_texts(self, items):
        from pathlib import Path
        root = Path(self.root)
        root.joinpath("active.pid").write_text(str(os.getpid()))
        while not root.joinpath("release").exists():
            time.sleep(0.01)
        if self.mode == "failure":
            raise RuntimeError("probe_failure")
        root.joinpath("vectors.json").write_text(__import__("json").dumps(items))


def _active_worker(root, mode, bound, reject_commit=False, early_shutdown=False):
    import functools
    import json
    import logging
    from pathlib import Path
    from types import SimpleNamespace

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from guardian.workers import document_embed_worker as worker

    logging.basicConfig(filename=f"{root}/worker.log", level=logging.INFO, force=True)
    engine = create_engine(f"sqlite:///{root}/documents.sqlite")
    db = SimpleNamespace(get_session=sessionmaker(bind=engine))
    worker._get_db = lambda: db
    if reject_commit:
        persist = worker._update_status

        def reject_terminal(*args, **kwargs):
            if kwargs["status"] in {"ready", "failed"}:
                raise RuntimeError("probe_terminal_commit_unconfirmed")
            return persist(*args, **kwargs)

        worker._update_status = reject_terminal
    worker.get_settings = lambda: SimpleNamespace(
        DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS=bound,
    )
    executor_class = worker._BoundedEmbedding
    worker._BoundedEmbedding = lambda timeout: executor_class(
        timeout, functools.partial(_ProbeVectorStore, root, mode),
    )

    def dequeue(**_kwargs):
        path = Path(root, "queue.json")
        jobs = json.loads(path.read_text())
        if not jobs:
            return None
        job = jobs.pop(0)
        path.write_text(json.dumps(jobs))
        if early_shutdown:
            os.kill(os.getpid(), signal.SIGTERM)
        return job

    worker.dequeue_document_embed = dequeue
    worker.run_forever()


def _wait_for(path, timeout=30):
    end = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < end:
        time.sleep(0.01)
    assert path.exists(), f"probe did not reach {path.name}"


def _document_state(root):
    import sqlite3
    with sqlite3.connect(f"{root}/documents.sqlite") as connection:
        return connection.execute(
            "SELECT embedding_status, embedding_error FROM uploaded_documents WHERE id='active'",
        ).fetchone(), connection.execute("SELECT status FROM transitions").fetchall()


def _run_active_probe(tmp_path, mode, repeated=False):
    import json
    _prepare_documents(str(tmp_path))
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=_active_worker, args=(str(tmp_path), mode, 6.0))
    process.start()
    try:
        _wait_for(tmp_path / "active.pid")
        child_pid = int((tmp_path / "active.pid").read_text())
        assert _document_state(tmp_path)[0][0] == "processing" or mode == "failure"
        started = time.monotonic()
        os.kill(process.pid, signal.SIGTERM)
        if repeated:
            os.kill(process.pid, signal.SIGINT)
            os.kill(process.pid, signal.SIGTERM)
        if mode in {"success", "failure"}:
            (tmp_path / "release").touch()
        process.join(10)
        assert not process.is_alive()
        assert process.exitcode == 0
        assert time.monotonic() - started < 10
        expected = "ready" if mode == "success" else "failed"
        state, transitions = _document_state(tmp_path)
        assert state[0] == expected
        assert transitions == [("processing",), (expected,)]
        assert json.loads((tmp_path / "queue.json").read_text()) == [{"doc_id": "next"}]
        assert "document_embed_terminal_ack" in (tmp_path / "worker.log").read_text()
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        # Release the deliberately abandoned operation AFTER exit. A surviving
        # execution would now write vectors; observe beyond its polling interval.
        before = _document_state(tmp_path)
        (tmp_path / "release").touch()
        time.sleep(0.15)
        assert _document_state(tmp_path) == before
        assert (tmp_path / "vectors.json").exists() == (mode == "success")
        if mode == "hung":
            assert state[1] == "document_embed_execution_bound_exceeded"
    finally:
        if process.is_alive():
            process.kill()
            process.join(3)
        process.close()


def test_active_success_commits_before_shutdown(tmp_path):
    _run_active_probe(tmp_path, "success")


def test_active_failure_commits_before_shutdown(tmp_path):
    _run_active_probe(tmp_path, "failure")


def test_hung_writer_is_reaped_before_failed_commit_with_no_late_writes(tmp_path):
    _run_active_probe(tmp_path, "hung")


def test_repeated_signals_do_not_duplicate_finalization(tmp_path):
    _run_active_probe(tmp_path, "hung", repeated=True)


def test_compose_grace_exceeds_maximum_execution_and_finalization_margin():
    import re
    from pathlib import Path
    from guardian.core.config import Settings
    from guardian.workers.document_embed_worker import DOCUMENT_EMBED_FINALIZATION_MARGIN_SECONDS

    compose = Path("docker-compose.yml").read_text()
    service = compose.split("  worker-document-embed:", 1)[1].split("  worker-chat-embed:", 1)[0]
    duration = re.search(r"stop_grace_period: (\d+)m(\d+)s", service)
    assert duration
    grace = int(duration[1]) * 60 + int(duration[2])
    field = Settings.model_fields["DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS"]
    maximum = next(m.le for m in field.metadata if hasattr(m, "le"))
    assert grace > maximum + DOCUMENT_EMBED_FINALIZATION_MARGIN_SECONDS


@pytest.mark.parametrize("invalid", [0, -1, 601, float("inf"), float("nan")])
def test_execution_setting_rejects_invalid_bounds(invalid):
    from pydantic import ValidationError
    from guardian.core.config import Settings
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS=invalid)


def test_ready_document_replay_does_not_execute_or_rewrite(tmp_path):
    from types import SimpleNamespace
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from guardian.workers import document_embed_worker as worker

    _prepare_documents(str(tmp_path))
    engine = create_engine(f"sqlite:///{tmp_path}/documents.sqlite")
    with engine.begin() as connection:
        connection.execute(text("UPDATE uploaded_documents SET embedding_status='ready' WHERE id='active'"))
    before = _document_state(tmp_path)

    def forbidden(_doc):
        raise AssertionError("ready document was reprocessed")

    assert worker.process_document_embed_task(
        {"doc_id": "active"},
        db=SimpleNamespace(get_session=sessionmaker(bind=engine)), execution=forbidden,
    )
    assert _document_state(tmp_path) == before
    engine.dispose()


def test_unconfirmed_terminal_commit_never_claims_clean_drain(tmp_path):
    _prepare_documents(str(tmp_path))
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_active_worker, args=(str(tmp_path), "success", 6.0, True),
    )
    process.start()
    try:
        _wait_for(tmp_path / "active.pid")
        child_pid = int((tmp_path / "active.pid").read_text())
        os.kill(process.pid, signal.SIGTERM)
        (tmp_path / "release").touch()
        process.join(10)
        assert not process.is_alive() and process.exitcode != 0
        log = (tmp_path / "worker.log").read_text()
        assert "document_embed_terminal_ack" not in log
        assert "document_embed_worker_drained" not in log
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        assert _document_state(tmp_path)[1] == [("processing",)]
    finally:
        if process.is_alive():
            process.kill()
            process.join(3)
        process.close()


class _NativeFaissWriter:
    def __init__(self, root):
        from guardian.vector.store import VectorStore
        self.store = VectorStore()
        self.root = root

    def add_texts(self, items):
        from pathlib import Path
        import json
        self.store.add_texts(items)
        Path(self.root, "faiss.json").write_text(json.dumps({
            "pid": os.getpid(), "texts": self.store.embedder._texts,
        }))


def test_faiss_success_preserves_worker_index_between_jobs(monkeypatch, tmp_path):
    import functools
    import json
    from guardian.workers import document_embed_worker as worker

    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setattr(worker, "_shutdown_requested", False)
    execution = worker._BoundedEmbedding(
        6, functools.partial(_NativeFaissWriter, str(tmp_path)),
    )
    try:
        execution({"id": "first", "parsed_text": "first document", "user_id": "probe"})
        first = json.loads((tmp_path / "faiss.json").read_text())
        execution({"id": "second", "parsed_text": "second document", "user_id": "probe"})
        second = json.loads((tmp_path / "faiss.json").read_text())
        assert first["pid"] == second["pid"]
        assert second["texts"] == ["first document", "second document"]
    finally:
        execution.close()



def test_signal_during_dequeue_drains_the_already_owned_job(tmp_path):
    import json
    _prepare_documents(str(tmp_path))
    (tmp_path / "release").touch()
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_active_worker, args=(str(tmp_path), "success", 6.0, False, True),
    )
    process.start()
    try:
        process.join(20)
        assert not process.is_alive() and process.exitcode == 0
        assert _document_state(tmp_path)[1] == [("processing",), ("ready",)]
        assert json.loads((tmp_path / "queue.json").read_text()) == [{"doc_id": "next"}]
    finally:
        if process.is_alive():
            process.kill()
            process.join(3)
        process.close()


def test_partial_ipc_response_cannot_slide_execution_deadline():
    import socket
    import struct
    from guardian.workers.document_embed_worker import _DocumentChannel

    receiver, sender = socket.socketpair()
    channel = _DocumentChannel(receiver)
    try:
        sender.sendall(struct.pack('!I', 10))
        channel.deadline = time.monotonic() + 0.05
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            channel.recv()
        assert time.monotonic() - started < 0.2
    finally:
        channel.close()
        sender.close()


def test_failed_document_is_not_silently_treated_as_ready(tmp_path):
    from types import SimpleNamespace
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from guardian.workers import document_embed_worker as worker

    _prepare_documents(str(tmp_path))
    engine = create_engine(f"sqlite:///{tmp_path}/documents.sqlite")
    with engine.begin() as connection:
        connection.execute(text("UPDATE uploaded_documents SET embedding_status='failed' WHERE id='active'"))
    called = []

    def fail_again(doc):
        called.append(doc["id"])
        raise RuntimeError("explicitly_queued_retry_failed")

    assert not worker.process_document_embed_task(
        {"doc_id": "active"},
        db=SimpleNamespace(get_session=sessionmaker(bind=engine)), execution=fail_again,
    )
    assert called == ["active"]
    assert _document_state(tmp_path)[0] == ("failed", "explicitly_queued_retry_failed")
    engine.dispose()
