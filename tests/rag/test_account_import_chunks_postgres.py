"""Opt-in real two-session proof; never target the serving database."""
from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from guardian.db.models import Base, OpenAIAccountImportJob, OpenAIImportSource, User
from guardian.services import account_import_chunks as chunks
from tests.rag.test_openai_export_account_import import _build_account_import_service


@pytest.fixture
def pg_chunk_service(tmp_path):
    raw = os.getenv("CODEXIFY_TEST_ACCOUNT_IMPORT_POSTGRES_URL")
    if not raw: pytest.skip("requires an explicit disposable account import PostgreSQL URL")
    url = make_url(raw).set(drivername="postgresql+psycopg")
    assert url.host in {"127.0.0.1", "localhost"} and url.database == "chunkproof"
    schema = "chunk_proof_" + uuid4().hex
    app = "chunk-proof-" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn: conn.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}", "application_name": app})
    try:
        Base.metadata.create_all(engine, tables=[User.__table__, OpenAIImportSource.__table__, OpenAIAccountImportJob.__table__])
        values = _build_account_import_service(tmp_path, sessionmaker(bind=engine, expire_on_commit=False))
        yield values, engine, app
    finally:
        engine.dispose()
        with admin.begin() as conn: conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_two_sessions_serialize_same_job_parts_and_replay_without_overwrite(pg_chunk_service, monkeypatch):
    (service, _sessions, _trace, staging, _media), engine, app = pg_chunk_service
    monkeypatch.setattr(chunks, "CHUNK_BYTES", 4)
    body = b"abcdefghij"
    record = service.create_job(user_id="account-a", total_file_count=1, total_byte_count=10)
    entered, release, second = threading.Event(), threading.Event(), threading.Event()
    original = chunks._write_metadata
    paused = False
    def metadata(*args, **kwargs):
        nonlocal paused
        if not paused:
            paused = True; entered.set()
            assert release.wait(5), "test did not release held row lock"
        return original(*args, **kwargs)
    monkeypatch.setattr(chunks, "_write_metadata", metadata)
    def send(offset=0):
        data = body[offset:offset+4]
        return chunks.stage_account_import_chunk(service, job_id=record["job_id"], user_id="account-a",
            relative_path="export/movie.dat", file_size=10, file_sha256=hashlib.sha256(body).hexdigest(),
            chunk_sha256=hashlib.sha256(data).hexdigest(), offset=offset, data=data)
    def replay():
        second.set()
        return send()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send)
        try:
            assert entered.wait(3)
            other = pool.submit(replay)
            assert second.wait(3)
            observed_lock = False
            deadline = time.monotonic()+3
            while time.monotonic() < deadline:
                with engine.connect() as conn:
                    count = conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name=:app AND wait_event_type='Lock'"), {"app": app}).scalar_one()
                if count:
                    observed_lock = True; break
                time.sleep(.02)
            assert observed_lock, "second real PostgreSQL session never waited on the job row lock"
            assert not list(staging.provider.base_path.rglob("*.part"))
        finally:
            release.set()
        a, b = first.result(timeout=5), other.result(timeout=5)
    assert a["received_bytes"] == b["received_bytes"] == 4
    assert len(list(staging.provider.base_path.rglob("*.part"))) == 1
    assert send(4)["received_bytes"] == 8
    assert send(8)["job"]["uploaded_file_count"] == 1
    assert send(8)["job"]["uploaded_byte_count"] == 10
