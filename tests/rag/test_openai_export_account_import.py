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
from guardian.protocol_tokens import AccountImportErrorCode
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


def test_zero_committed_entities_cannot_be_classified_as_success(
    account_import_service,
):
    service, _sessions, trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    staged_replay = service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    assert staged_replay["duplicate_count"] == 1
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.record_source_summary(
        job_id=job["job_id"],
        user_id="account-a",
        summary={
            "conversations_discovered": 1,
            "conversations_accepted": 1,
            "conversations_skipped": 0,
            "conversations_failed": 1,
            "conversation_transactions_committed": False,
        },
    )

    with pytest.raises(AccountImportError) as exc_info:
        service.complete_job(job_id=job["job_id"], user_id="account-a")

    assert exc_info.value.code == AccountImportErrorCode.NO_COMMITTED_ENTITIES.value
    failed = service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code=exc_info.value.code,
        message=str(exc_info.value),
    )
    assert failed["status"] == "failed"
    assert failed["imported_thread_count"] == 0
    assert failed["imported_message_count"] == 0
    assert failed["imported_media_count"] == 0
    assert failed["source_summary"] == {
        "conversations_discovered": 1,
        "conversations_accepted": 1,
        "conversations_skipped": 0,
        "conversations_failed": 1,
        "conversation_transactions_committed": False,
    }
    assert any(
        item[:2] == ("event", "account_import.failed") for item in trace
    )


# ---------------------------------------------------------------------------
# Provider-neutral committed-conversation-total accounting
# ---------------------------------------------------------------------------


def test_committed_conversation_totals_first_application_credits_durable_job(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a",
        total_file_count=1,
        total_byte_count=2,
        source_system="anthropic",
    )

    credited = service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )

    assert credited["imported_thread_count"] == 63
    assert credited["imported_message_count"] == 784
    assert credited["source_system"] == "anthropic"

    # Durable readback through a separate serialization confirms persistence,
    # including the durable accounting checkpoint entry.
    reread = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert reread["imported_thread_count"] == 63
    assert reread["imported_message_count"] == 784
    assert reread["checkpoint"]["committed_conversation_totals"] == [
        {
            "key": "anthropic_conversations",
            "threads_imported": 63,
            "messages_imported": 784,
        }
    ]


def test_committed_conversation_totals_exact_replay_is_idempotent(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )

    replay = service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )

    assert replay["imported_thread_count"] == 63
    assert replay["imported_message_count"] == 784
    internal = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert len(
        internal["checkpoint"]["committed_conversation_totals"]
    ) == 1


def test_committed_conversation_totals_conflicting_replay_fails_closed(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )

    with pytest.raises(AccountImportError) as conflict:
        service.record_committed_conversation_totals(
            job_id=job["job_id"],
            user_id="account-a",
            threads_imported=63,
            messages_imported=785,
            phase_key="anthropic_conversations",
        )
    assert conflict.value.code == "committed_totals_conflict"
    assert conflict.value.status_code == 409

    unchanged = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert unchanged["imported_thread_count"] == 63
    assert unchanged["imported_message_count"] == 784


def test_committed_conversation_totals_positive_counts_satisfy_complete_job(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.record_source_summary(
        job_id=job["job_id"],
        user_id="account-a",
        summary={
            "conversations_discovered": 65,
            "conversations_accepted": 65,
            "conversations_skipped": 0,
            "conversations_failed": 0,
            "conversation_transactions_committed": True,
        },
    )
    service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )

    completed = service.complete_job(job_id=job["job_id"], user_id="account-a")

    assert completed["status"] == "completed"
    assert completed["imported_thread_count"] == 63
    assert completed["imported_message_count"] == 784
    assert completed["source_summary"]["conversation_transactions_committed"] is True


def test_committed_conversation_totals_zero_counts_do_not_bypass_guard(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    zero = service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=0,
        messages_imported=0,
        phase_key="anthropic_conversations",
    )
    assert zero["imported_thread_count"] == 0
    assert zero["imported_message_count"] == 0
    internal = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert internal["checkpoint"].get("committed_conversation_totals") in (
        None,
        [],
    )

    with pytest.raises(AccountImportError) as exc_info:
        service.complete_job(job_id=job["job_id"], user_id="account-a")
    assert exc_info.value.code == AccountImportErrorCode.NO_COMMITTED_ENTITIES.value


def test_committed_conversation_totals_phase_keys_accumulate_independently(
    account_import_service,
):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )
    second = service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=1,
        messages_imported=1,
        phase_key="another_source_conversations",
    )
    assert second["imported_thread_count"] == 64
    assert second["imported_message_count"] == 785
    internal = service.get_worker_job(job_id=job["job_id"], user_id="account-a")
    assert len(internal["checkpoint"]["committed_conversation_totals"]) == 2

    replay = service.record_committed_conversation_totals(
        job_id=job["job_id"],
        user_id="account-a",
        threads_imported=63,
        messages_imported=784,
        phase_key="anthropic_conversations",
    )
    assert replay["imported_thread_count"] == 64
    assert replay["imported_message_count"] == 785


# ---------------------------------------------------------------------------
# Retry seam service tests
# ---------------------------------------------------------------------------


def test_is_zero_write_job_accepts_all_zero_counters(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="test",
        message="test",
    )

    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        is_zero, reason = service._is_zero_write_job(row)
        assert is_zero is True
        assert reason is None


def test_is_zero_write_job_rejects_positive_thread_count(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.imported_thread_count = 5
        session.commit()
        is_zero, reason = service._is_zero_write_job(row)
        assert is_zero is False
        assert "imported_thread_count" in reason


def test_is_zero_write_job_rejects_positive_message_count(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.imported_message_count = 3
        session.commit()
        is_zero, reason = service._is_zero_write_job(row)
        assert is_zero is False
        assert "imported_message_count" in reason


def test_is_zero_write_job_rejects_positive_media_count(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.imported_media_count = 1
        session.commit()
        is_zero, reason = service._is_zero_write_job(row)
        assert is_zero is False
        assert "imported_media_count" in reason


def test_retry_failed_preserves_original_failure_receipt(account_import_service):
    service, sessions, trace, staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="account_import_worker_failed",
        message="disk full",
    )

    result = service.retry_failed_account_import(
        job_id=job["job_id"], user_id="account-a"
    )

    assert result["status"] == "queued"
    assert result["failure_count"] == 1
    assert result["imported_thread_count"] == 0
    assert result["imported_message_count"] == 0
    # At least one retry event was emitted
    retry_events = [item for item in trace if item[1] == "account_import.retry_attempt"]
    assert len(retry_events) == 1
    assert retry_events[0][2] == "account-a"


def test_retry_failed_preserves_ownership(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="test",
        message="test",
    )

    with pytest.raises(AccountImportError) as exc_info:
        service.retry_failed_account_import(
            job_id=job["job_id"], user_id="account-b"
        )
    assert exc_info.value.code == "account_import_not_found"


def test_retry_missing_staging_returns_restaging_required(account_import_service):
    service, sessions, _trace, staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="test",
        message="test",
    )

    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.staging_locator = "account-imports/missing/scope"
        row.staged_manifest = [
            {"path": "nonexistent.json", "sha256": "ab", "size": 2}
        ]
        session.commit()

    with pytest.raises(AccountImportError) as exc_info:
        service.retry_failed_account_import(
            job_id=job["job_id"], user_id="account-a"
        )
    assert exc_info.value.code == "account_import_restaging_required"


def test_retry_rejects_nonzero_write_job(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        row.status = "failed"
        row.imported_thread_count = 5
        session.commit()

    with pytest.raises(AccountImportError) as exc_info:
        service.retry_failed_account_import(
            job_id=job["job_id"], user_id="account-a"
        )
    assert exc_info.value.code == "account_import_retry_not_zero_write"


def test_retry_lifecycle_creates_retry_attempt_boundary(account_import_service):
    service, sessions, trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    service.finalize_job(job_id=job["job_id"], user_id="account-a")
    service.mark_running(job_id=job["job_id"], user_id="account-a")
    service.fail_job(
        job_id=job["job_id"],
        user_id="account-a",
        code="account_import_worker_failed",
        message="disconnected",
    )

    result = service.retry_failed_account_import(
        job_id=job["job_id"], user_id="account-a"
    )

    assert result["status"] == "queued"
    # Verify retry attempt recorded in checkpoint
    with sessions() as session:
        row = session.get(OpenAIAccountImportJob, job["job_id"])
        attempts = (row.checkpoint or {}).get("retry_attempts", [])
        assert len(attempts) == 1
        assert attempts[0]["attempt"] == 1
        assert attempts[0]["accepted"] is True


def test_retry_non_failed_status_rejected(account_import_service):
    service, sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=2
    )
    service.stage_files(
        job_id=job["job_id"],
        user_id="account-a",
        files=[StagedImportFile("conversations.json", b"[]")],
    )
    # job is still receiving
    with pytest.raises(AccountImportError) as exc_info:
        service.retry_failed_account_import(
            job_id=job["job_id"], user_id="account-a"
        )
    assert exc_info.value.code == "account_import_not_failed"


# ---------------------------------------------------------------------------
# Source-system allow-list (Anthropic adapter support)
# ---------------------------------------------------------------------------


def test_create_job_accepts_anthropic_source_system(account_import_service):
    """The intake must accept ``anthropic`` as a supported source system
    while preserving the existing OpenAI default and rejection semantics for
    other systems."""

    service, _sessions, _trace, _staging, _media = account_import_service

    job = service.create_job(
        user_id="account-a",
        total_file_count=1,
        total_byte_count=1,
        source_system="anthropic",
    )
    assert job["source_system"] == "anthropic"
    assert job["status"] == "receiving"


def test_create_job_rejects_unknown_source_system(account_import_service):
    service, _sessions, _trace, _staging, _media = account_import_service
    with pytest.raises(AccountImportError) as exc_info:
        service.create_job(
            user_id="account-a",
            total_file_count=1,
            total_byte_count=1,
            source_system="not-a-real-source",
        )
    assert exc_info.value.code == "unsupported_source_system"


def test_create_job_preserves_openai_default(account_import_service):
    """Existing OpenAI callers must remain on the ``openai`` source-system
    token. This is a regression guard for the Anthropic allow-list addition."""

    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(
        user_id="account-a", total_file_count=1, total_byte_count=1
    )
    assert job["source_system"] == "openai"
