"""Explicit disposable PostgreSQL proof, never the serving database."""

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from guardian.db.models import (
    Base,
    ChatMessage,
    ChatThread,
    MediaAlias,
    MediaAsset,
    OpenAIAccountImportJob,
    Project,
    ProjectDocumentLink,
    ThreadDocument,
    UploadedDocument,
)
from guardian.services import account_import_pdf_repair as repair
from guardian.services.document_parsers import pdf_text_extractor
from guardian.services.openai_account_import import AccountImportError, StagedImportFile
from tests.rag.test_openai_export_account_import import _build_account_import_service
from guardian.tests.test_pdf_text_extraction import _simple_pdf_bytes


@pytest.fixture
def ready(tmp_path, monkeypatch):
    raw = os.getenv("CODEXIFY_TEST_ACCOUNT_IMPORT_POSTGRES_URL")
    if not raw:
        pytest.skip("explicit disposable PostgreSQL URL required")
    url = make_url(raw).set(drivername="postgresql+psycopg")
    assert url.host in {"localhost", "127.0.0.1"} and url.database == "chunkproof"
    schema = "pdf_proof_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    tables = {
        model.__table__
        for model in (
            ChatMessage,
            ChatThread,
            MediaAlias,
            MediaAsset,
            OpenAIAccountImportJob,
            Project,
            ProjectDocumentLink,
            ThreadDocument,
            UploadedDocument,
        )
    }
    while True:
        closure = tables | {
            fk.column.table for table in tables for fk in table.foreign_keys
        }
        if closure == tables:
            break
        tables = closure
    try:
        Base.metadata.create_all(engine, tables=list(tables))
        service, sessions, trace, staging, media = _build_account_import_service(
            tmp_path, sessionmaker(bind=engine, expire_on_commit=False)
        )
        data = _simple_pdf_bytes("left\x00right")
        metadata = json.dumps(
            [
                {
                    "id": "source-thread",
                    "title": "Proof",
                    "mapping": {
                        "message": {
                            "id": "message",
                            "message": {
                                "id": "message",
                                "author": {"role": "user"},
                                "content": {"content_type": "text", "parts": ["proof"]},
                                "metadata": {
                                    "attachments": [{"file_name": "original.dat"}]
                                },
                            },
                        }
                    },
                }
            ]
        ).encode()
        job = service.create_job(
            user_id="account-a",
            total_file_count=2,
            total_byte_count=len(data) + len(metadata),
        )
        service.stage_files(
            job_id=job["job_id"],
            user_id="account-a",
            files=[
                StagedImportFile("export/conversations.json", metadata),
                StagedImportFile("export/original.dat", data),
            ],
        )
        service.finalize_job(job_id=job["job_id"], user_id="account-a")
        with sessions() as session:
            row = session.get(OpenAIAccountImportJob, job["job_id"])
            row.status = "completed_with_warnings"
            row.warning_count = row.skipped_count = 1
            row.warning_details = [{"code": "document_import_failed"}]
            row.checkpoint = {
                "media_paths": ["export/original.dat"],
                "imported_document_count": 0,
            }
            session.add(Project(name="Imports", user_id="account-a"))
            session.commit()
            fingerprint = row.source_export_fingerprint
        monkeypatch.setattr(pdf_text_extractor, "_load_pdf_reader", lambda: None)
        args = dict(
            job_id=job["job_id"],
            user_id="account-a",
            relative_path="export/original.dat",
            file_size=len(data),
            file_sha256=hashlib.sha256(data).hexdigest(),
            source_export_fingerprint=fingerprint,
        )
        yield service, sessions, staging, media, args, data, engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_real_pg_persists_normalized_text_original_and_exact_once_receipt(
    ready, monkeypatch
):
    service, sessions, staging, media, args, data, _ = ready
    original_files = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in staging.provider.base_path.rglob("*")
        if p.is_file()
    }
    audit = repair.repair_retained_pdf(service, **args)
    assert audit["busy"] is False
    assert audit["job"]["status"] == "completed_with_warnings"
    assert audit["job"]["warning_count"] == audit["job"]["skipped_count"] == 1
    assert (
        audit["job"]["imported_media_count"]
        == audit["job"]["imported_document_count"]
        == 1
    )
    with sessions() as session:
        document = session.query(UploadedDocument).one()
        asset = session.query(MediaAsset).one()
        assert document.parsed_text == "left\ufffdright"
        assert (
            asset.provenance == "imported"
            and asset.source_export_id == args["source_export_fingerprint"]
        )
        assert (
            media.provider.base_path / (asset.storage_prefix + asset.system_name)
        ).read_bytes() == data
        assert session.query(ProjectDocumentLink).count() == 1
        row = session.get(OpenAIAccountImportJob, args["job_id"])
        events = row.checkpoint["pdf_repair_events"]
        row.checkpoint = {
            **row.checkpoint,
            "pdf_repair_events": events + [dict(events[-1])] * repair.MAX_EVENTS,
        }
        session.commit()
    monkeypatch.setattr(
        repair,
        "_verified_evidence",
        lambda *a: pytest.fail("completed replay rehashed whole export"),
    )
    again = repair.repair_retained_pdf(service, **args)
    assert again["job"]["imported_media_count"] == 1 and not again["busy"]
    assert {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in staging.provider.base_path.rglob("*")
        if p.is_file()
    } == original_files
    assert "staged_manifest" not in audit["job"] and "user_id" not in audit["job"]
    with pytest.raises(AccountImportError):
        service.retry_failed_account_import(job_id=args["job_id"], user_id="account-a")


def test_committed_document_before_lost_audit_reconciles_without_duplicate_or_reupload(
    ready, monkeypatch
):
    service, sessions, _, media, args, _, _ = ready
    event = repair._event

    def lose_completed(*a, **k):
        if a[3].get("completed_at"):
            raise RuntimeError("lost audit")
        return event(*a, **k)

    monkeypatch.setattr(repair, "_event", lose_completed)
    with pytest.raises(AccountImportError):
        repair.repair_retained_pdf(service, **args)
    with sessions() as session:
        assert session.query(UploadedDocument).count() == 1
        assert (
            session.get(OpenAIAccountImportJob, args["job_id"]).imported_media_count
            == 0
        )
    monkeypatch.setattr(repair, "_event", event)
    monkeypatch.setattr(
        media, "upload_file", lambda *a, **k: pytest.fail("replay uploaded original")
    )
    audit = repair.repair_retained_pdf(service, **args)
    assert audit["job"]["imported_media_count"] == 1
    repair.repair_retained_pdf(service, **args)
    with sessions() as session:
        assert (
            session.query(UploadedDocument).count()
            == session.query(MediaAsset).count()
            == 1
        )
        assert (
            len(
                session.get(OpenAIAccountImportJob, args["job_id"]).checkpoint[
                    "pdf_repair_credits"
                ]
            )
            == 1
        )


def test_separate_pg_connections_serialize_repairs_and_release_lock(ready, monkeypatch):
    service, _, _, _, args, _, _ = ready
    entered, release = threading.Event(), threading.Event()
    verify = repair._verified_evidence

    def pause(*a):
        entered.set()
        assert release.wait(6)
        return verify(*a)

    monkeypatch.setattr(repair, "_verified_evidence", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(repair.repair_retained_pdf, service, **args)
        try:
            assert entered.wait(3)
            assert repair.get_pdf_repair_audit(
                service, job_id=args["job_id"], user_id="account-a"
            )["busy"]
            with pytest.raises(AccountImportError) as error:
                repair.repair_retained_pdf(service, **args)
            assert error.value.code == repair.Code.MEDIA_REPAIR_BUSY.value
        finally:
            release.set()
        assert not first.result(timeout=8)["busy"]


@pytest.mark.parametrize(
    "mutation",
    ["owner", "fingerprint", "size", "active", "tamper", "symlink", "budget"],
)
def test_guard_failures_never_admit_document(ready, monkeypatch, mutation):
    service, sessions, staging, _, args, _, _ = ready
    args = dict(args)
    if mutation == "owner":
        args["user_id"] = "account-b"
    if mutation == "fingerprint":
        args["source_export_fingerprint"] = "0" * 64
    if mutation == "size":
        args["file_size"] += 1
    if mutation == "active":
        service.create_job(user_id="account-a", total_file_count=1, total_byte_count=0)
        with sessions() as session:
            row = (
                session.query(OpenAIAccountImportJob)
                .filter(OpenAIAccountImportJob.id != args["job_id"])
                .one()
            )
            row.status = "running"
            session.commit()
    if mutation in {"tamper", "symlink"}:
        path = next(staging.provider.base_path.rglob("original.dat"))
        if mutation == "tamper":
            path.write_bytes(b"wrong")
        else:
            external = path.parent / "outside"
            external.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(external)
    if mutation == "budget":
        monkeypatch.setattr(repair, "PRE_PERSISTENCE_SECONDS", 0)
    with pytest.raises((AccountImportError, OSError)):
        repair.repair_retained_pdf(service, **args)
    with sessions() as session:
        assert session.query(UploadedDocument).count() == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "deleted_asset",
        "deleted_document",
        "duplicate",
        "owner",
        "metadata",
        "blob",
        "project_link",
    ],
)
def test_completed_receipt_never_restores_deleted_or_conflicting_canonical_state(
    ready, mutation
):
    service, sessions, _, media, args, _, _ = ready
    repair.repair_retained_pdf(service, **args)
    with sessions() as session:
        asset = session.query(MediaAsset).one()
        document = session.query(UploadedDocument).one()
        if mutation == "deleted_asset":
            asset.deleted_at = datetime.now(timezone.utc)
        if mutation == "deleted_document":
            document.deleted_at = datetime.now(timezone.utc)
        if mutation == "duplicate":
            values = {
                column.name: getattr(asset, column.name)
                for column in MediaAsset.__table__.columns
            }
            # Active identity is unique; a historical deleted match can coexist.
            values["id"] = str(uuid4())
            values["deleted_at"] = datetime.now(timezone.utc)
            session.add(MediaAsset(**values))
        if mutation == "owner":
            document.user_id = "account-b"
        if mutation == "metadata":
            document.filesize += 1
        if mutation == "blob":
            (
                media.provider.base_path / (asset.storage_prefix + asset.system_name)
            ).write_bytes(b"wrong")
        if mutation == "project_link":
            session.query(ProjectDocumentLink).delete()
        session.commit()
    with pytest.raises(AccountImportError):
        repair.repair_retained_pdf(service, **args)
    with sessions() as session:
        assert session.query(UploadedDocument).count() == 1
        assert (
            session.get(OpenAIAccountImportJob, args["job_id"]).imported_media_count
            == 1
        )


def test_audit_job_row_lock_is_bounded_and_advisory_lock_released(ready):
    service, sessions, _, _, args, _, _ = ready
    with sessions() as blocker:
        blocker.query(OpenAIAccountImportJob).filter_by(
            id=args["job_id"]
        ).with_for_update().one()
        started = time.monotonic()
        with pytest.raises(Exception):
            repair.repair_retained_pdf(service, **args)
        assert time.monotonic() - started < 5
    assert not repair.get_pdf_repair_audit(
        service, job_id=args["job_id"], user_id="account-a"
    )["busy"]


@pytest.mark.parametrize("reference", ["a/original.dat", "original.dat"])
def test_utf8_json_edge_and_all_binary_aliases_match_normal_source_evidence(
    ready, tmp_path, reference
):
    service, sessions, staging, _, _, data, _ = ready
    from backend.rag.openai_export_adapter import (
        OpenAIExportDetector,
        build_openai_export_image_evidence_index,
        resolve_openai_export_image_evidence,
    )

    conversation = {
        "id": "source-thread",
        "mapping": {
            "message": {
                "message": {
                    "id": "message",
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["proof"]},
                    "metadata": {"attachments": [{"file_name": reference}]},
                }
            }
        },
    }
    prefix = b'[{"padding":"'
    metadata = (
        prefix
        + b"x" * (4095 - len(prefix))
        + "\u00e9".encode()
        + b'",'
        + json.dumps(conversation)[1:].encode()
        + b"]"
    )
    files = {
        "conversations.json": metadata,
        "a/original.dat": data,
        "b/original.dat": data + b"different",
    }
    job = service.create_job(
        user_id="account-a",
        total_file_count=3,
        total_byte_count=sum(map(len, files.values())),
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile(p, b) for p, b in files.items()],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.status = "completed_with_warnings"
        row.checkpoint = {"media_paths": ["a/original.dat"]}
        session.commit()
        snapshot = service.serialize_job(row, include_internal=True)
    full = OpenAIExportDetector().scan(
        staging.provider.base_path / snapshot["staging_locator"]
    )
    expected = resolve_openai_export_image_evidence(
        "a/original.dat", build_openai_export_image_evidence_index(full)
    )
    workspace = tmp_path / "verified"
    workspace.mkdir()
    _, actual = repair._verified_evidence(
        service, snapshot, "a/original.dat", workspace, time.monotonic() + 10
    )
    assert actual == expected
    assert actual.source_tag == (
        "uploaded" if reference.startswith("a/") else "unclassified"
    )


def test_late_native_pdf_parse_cannot_start_canonical_writer(ready, monkeypatch):
    service, sessions, _, _, args, _, _ = ready
    clock = [100.0]
    monkeypatch.setattr(repair.time, "monotonic", lambda: clock[0])

    def slow_parse(data):
        clock[0] += repair.PRE_PERSISTENCE_SECONDS + 1
        return "late derived text"

    monkeypatch.setattr(repair, "extract_pdf_text", slow_parse)
    with pytest.raises(AccountImportError) as error:
        repair.repair_retained_pdf(service, **args)
    assert error.value.code == repair.Code.MEDIA_REPAIR_LIMIT.value
    with sessions() as session:
        assert session.query(UploadedDocument).count() == 0
