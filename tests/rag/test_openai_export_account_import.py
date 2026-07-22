from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.rag.openai_export_adapter import (
    OpenAIExportFileRecord,
    OpenAIExportImageEvidence,
    OpenAIExportImageRelationship,
    build_openai_export_image_evidence_index,
    diagnose_openai_export_path,
    resolve_openai_export_image_evidence,
)
from guardian.core.storage import StorageManager
from guardian.db.models import (
    Base,
    GeneratedImage,
    MediaAlias,
    MediaAsset,
    OpenAIAccountImportJob,
    Project,
    UploadedImage,
    User,
)
from guardian.services.openai_account_import import (
    AccountImportError,
    OpenAIAccountImportService,
    StagedImportFile,
    normalize_import_relative_path,
)

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _message_node(
    node_id: str,
    role: str,
    *,
    reference: str,
    generated: bool = False,
) -> dict:
    metadata = {"file_path": reference}
    if generated:
        metadata.update(
            {
                "dalle": {"generated": True},
                "prompt": "A generated constellation",
                "model_slug": "dall-e-3",
            }
        )
    return {
        "id": node_id,
        "parent": None,
        "children": [],
        "message": {
            "id": node_id,
            "author": {"role": role},
            "content": {
                "content_type": "multimodal_text",
                "parts": [{"asset_pointer": reference}],
            },
            "metadata": metadata,
        },
    }


def test_nested_export_detects_legacy_dat_and_explicit_image_provenance(
    tmp_path: Path,
):
    legacy_root = tmp_path / "legacy"
    media = legacy_root / "nested" / "media"
    media.mkdir(parents=True)
    uploaded_path = "nested/media/uploaded.png"
    generated_path = "nested/media/generated.png"
    unlinked_path = "nested/media/orphan.png"
    conflicting_path = "nested/media/conflicting.png"
    (legacy_root / uploaded_path).write_bytes(PNG_BYTES)
    (legacy_root / generated_path).write_bytes(PNG_BYTES + b"generated")
    (legacy_root / unlinked_path).write_bytes(PNG_BYTES + b"orphan")
    (legacy_root / conflicting_path).write_bytes(PNG_BYTES + b"conflicting")
    conversation = {
        "id": "thread-provenance",
        "conversation_id": "thread-provenance",
        "title": "Image provenance",
        "current_node": "assistant-image",
        "mapping": {
            "user-image": _message_node(
                "user-image", "user", reference=uploaded_path
            ),
            "assistant-image": _message_node(
                "assistant-image",
                "assistant",
                reference=generated_path,
                generated=True,
            ),
            "user-conflict": _message_node(
                "user-conflict", "user", reference=conflicting_path
            ),
            "assistant-conflict": _message_node(
                "assistant-conflict",
                "assistant",
                reference=conflicting_path,
                generated=True,
            ),
        },
    }
    (legacy_root / "conversations.json").write_text(
        json.dumps([conversation]), encoding="utf-8"
    )

    report = diagnose_openai_export_path(legacy_root)
    assert report.inventory.legacy_detected is True
    assert {record.path for record in report.inventory.files} >= {
        "conversations.json",
        uploaded_path,
        generated_path,
        unlinked_path,
        conflicting_path,
    }
    evidence = build_openai_export_image_evidence_index(report.inventory)

    uploaded = resolve_openai_export_image_evidence(uploaded_path, evidence)
    generated = resolve_openai_export_image_evidence(generated_path, evidence)
    unlinked = resolve_openai_export_image_evidence(unlinked_path, evidence)
    conflicting = resolve_openai_export_image_evidence(
        conflicting_path, evidence
    )

    assert uploaded.source_tag == "uploaded"
    assert uploaded.source_message_id == "user-image"
    assert generated.source_tag == "generated"
    assert generated.source_message_id == "assistant-image"
    assert generated.prompt == "A generated constellation"
    assert generated.model == "dall-e-3"
    assert unlinked.source_tag == "unclassified"
    assert unlinked.evidence_kind == "unlinked"
    assert conflicting.source_tag == "unclassified"
    assert conflicting.evidence_kind == "conflicting_references"
    assert conflicting.source_thread_id == "thread-provenance"
    assert {item.source_message_id for item in conflicting.relationships} == {
        "user-conflict",
        "assistant-conflict",
    }

    sharded_root = tmp_path / "sharded"
    sharded_root.mkdir()
    (sharded_root / "file_0000000000000001.dat").write_text(
        json.dumps([conversation]), encoding="utf-8"
    )
    sharded = diagnose_openai_export_path(sharded_root)
    assert sharded.inventory.sharded_detected is True
    assert sharded.inventory.files[0].conversation_candidate is True


def test_ambiguous_image_basename_does_not_invent_provenance(tmp_path: Path):
    export_root = tmp_path / "ambiguous-export"
    first_path = "media/first/shared.png"
    second_path = "media/second/shared.png"
    (export_root / first_path).parent.mkdir(parents=True)
    (export_root / second_path).parent.mkdir(parents=True)
    (export_root / first_path).write_bytes(PNG_BYTES)
    (export_root / second_path).write_bytes(PNG_BYTES + b"second")
    conversation = {
        "id": "ambiguous-thread",
        "conversation_id": "ambiguous-thread",
        "title": "Ambiguous image basename",
        "current_node": "user-image",
        "mapping": {
            "user-image": _message_node(
                "user-image", "user", reference="shared.png"
            )
        },
    }
    (export_root / "conversations.json").write_text(
        json.dumps([conversation]), encoding="utf-8"
    )

    inventory = diagnose_openai_export_path(export_root).inventory
    evidence = build_openai_export_image_evidence_index(inventory)

    assert resolve_openai_export_image_evidence(
        first_path, evidence
    ).source_tag == "unclassified"
    assert resolve_openai_export_image_evidence(
        second_path, evidence
    ).source_tag == "unclassified"


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("../secret.json", "path_traversal_rejected"),
        ("/tmp/secret.json", "absolute_path_rejected"),
        ("C:\\secret.json", "absolute_path_rejected"),
        ("./", "empty_relative_path"),
    ],
)
def test_import_relative_paths_fail_closed(value: str, code: str):
    with pytest.raises(AccountImportError) as exc_info:
        normalize_import_relative_path(value)
    assert exc_info.value.code == code


def test_import_relative_paths_use_one_unicode_normal_form():
    assert normalize_import_relative_path("media/cafe\u0301.png") == (
        "media/café.png"
    )


class _TestDB:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def get_session(self):
        return self._session_factory()


@pytest.fixture
def account_import_service(tmp_path: Path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [
        User.__table__,
        Project.__table__,
        OpenAIAccountImportJob.__table__,
        MediaAsset.__table__,
        MediaAlias.__table__,
        GeneratedImage.__table__,
        UploadedImage.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        session.add(User(id="account-a", username="account-a", password_hash="x"))
        session.add(User(id="account-b", username="account-b", password_hash="x"))
        session.commit()

    trace: list[tuple] = []

    def enqueue(job_id: str, *, user_id: str) -> None:
        trace.append(("enqueue", job_id, user_id))

    def emit(topic: str, payload: dict, *, tenant_id: str) -> None:
        with sessions() as session:
            row = session.get(OpenAIAccountImportJob, payload["job_id"])
            trace.append(
                (
                    "event",
                    topic,
                    tenant_id,
                    row.status,
                    int(row.imported_media_count or 0),
                )
            )

    staging = StorageManager(
        "local",
        base_path=tmp_path / "private-imports",
        url_prefix="/internal",
    )
    media = StorageManager(
        "local",
        base_path=tmp_path / "media",
        url_prefix="/media",
    )
    service = OpenAIAccountImportService(
        db=_TestDB(sessions),
        staging_storage=staging,
        media_storage=media,
        enqueue_task=enqueue,
        emit_event=emit,
    )
    return service, sessions, trace, staging, media


def test_staged_job_conflicts_events_and_media_replay_are_durable(
    account_import_service,
    tmp_path: Path,
):
    service, sessions, trace, staging, media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=1
    )

    with pytest.raises(AccountImportError) as conflict:
        service.stage_files(
            job_id=job["job_id"],
            user_id="account-a",
            files=[
                StagedImportFile("nested/conversations.json", b"a"),
                StagedImportFile("nested/conversations.json", b"b"),
            ],
        )
    assert conflict.value.code == "conflicting_duplicate_path"
    assert trace == []

    staged = service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("nested/conversations.json", b"a")],
    )
    assert staged["uploaded_file_count"] == 1
    assert "staged_manifest" not in staged
    assert staging.list_files("account-imports")

    accepted = service.finalize_job(job_id=job["job_id"], user_id="account-a")
    assert accepted["status"] == "queued"
    assert [entry[0] for entry in trace[:2]] == ["enqueue", "event"]
    assert trace[1][1:4] == (
        "account_import.accepted",
        "account-a",
        "queued",
    )
    internal = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert internal["staged_manifest"][0]["path"] == "nested/conversations.json"
    with pytest.raises(AccountImportError) as wrong_account:
        service.get_job(job_id=job["job_id"], user_id="account-b")
    assert wrong_account.value.status_code == 404

    service.mark_running(job_id=job["job_id"], user_id="account-a")
    image_path = tmp_path / "orphan.png"
    image_path.write_bytes(PNG_BYTES)
    record = OpenAIExportFileRecord(
        path="nested/media/orphan.png",
        absolute_path=str(image_path),
        size=len(PNG_BYTES),
        extension=".png",
        detected_kind="image_png",
        first_bytes_hex=PNG_BYTES[:16].hex(),
        magic_signature="png",
    )
    evidence = resolve_openai_export_image_evidence(record.path, {})
    first = service.import_image_record(
        job_id=job["job_id"],
        user_id="account-a",
        record=record,
        evidence=evidence,
    )
    service.record_media_batch(
        job_id=job["job_id"], user_id="account-a", results=[first]
    )
    replay = service.import_image_record(
        job_id=job["job_id"],
        user_id="account-a",
        record=record,
        evidence=evidence,
    )
    service.record_media_batch(
        job_id=job["job_id"], user_id="account-a", results=[replay]
    )

    with sessions() as session:
        assert session.query(MediaAsset).count() == 1
        assert session.query(UploadedImage).count() == 1
        asset = session.query(MediaAsset).one()
        assert asset.user_id == "account-a"
        assert asset.source_tag == "unclassified"
        assert asset.source_relative_path == "nested/media/orphan.png"
        assert asset.import_job_id == job["job_id"]
        assert "localhost:5173" not in asset.src_url
    assert len(media.list_files("images")) == 1
    status = service.get_job(job_id=job["job_id"], user_id="account-a")
    assert status["imported_media_count"] == 1
    media_events = [
        entry
        for entry in trace
        if entry[:2] == ("event", "account_import.batch_committed")
    ]
    assert len(media_events) == 1
    assert media_events[0][4] == 1


def test_unclassified_media_keeps_conflicting_source_relationships(
    account_import_service,
    tmp_path: Path,
):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=1
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"a")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    image_path = tmp_path / "conflicting.png"
    image_path.write_bytes(PNG_BYTES + b"conflicting")
    record = OpenAIExportFileRecord(
        path="media/conflicting.png",
        absolute_path=str(image_path),
        size=image_path.stat().st_size,
        extension=".png",
        detected_kind="image_png",
        first_bytes_hex=PNG_BYTES[:16].hex(),
        magic_signature="png",
    )
    evidence = OpenAIExportImageEvidence(
        source_tag="unclassified",
        evidence_kind="conflicting_references",
        relationships=(
            OpenAIExportImageRelationship(
                source_message_id="user-image",
                evidence_kind="user_message_attachment",
            ),
            OpenAIExportImageRelationship(
                source_message_id="assistant-image",
                evidence_kind="generation_metadata",
            ),
        ),
    )

    service.import_image_record(
        job_id=job["job_id"],
        user_id="account-a",
        record=record,
        evidence=evidence,
    )

    with sessions() as session:
        asset = session.query(MediaAsset).one()
        assert asset.source_tag == "unclassified"
        assert {item["source_message_id"] for item in asset.import_lineage} == {
            "user-image",
            "assistant-image",
        }
        assert {item["evidence_kind"] for item in asset.import_lineage} == {
            "user_message_attachment",
            "generation_metadata",
        }


def test_terminal_failure_replay_does_not_inflate_counters_or_events(
    account_import_service,
):
    service, _sessions, trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=1
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"a")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")

    first = service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="worker_failed",
        message="first terminal failure",
    )
    replay = service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="worker_failed_again",
        message="duplicate delivery",
    )

    assert first["failure_count"] == 1
    assert replay["failure_count"] == 1
    assert replay["error_details"] == first["error_details"]
    failed_events = [
        item
        for item in trace
        if item[:2] == ("event", "account_import.failed")
    ]
    assert len(failed_events) == 1
