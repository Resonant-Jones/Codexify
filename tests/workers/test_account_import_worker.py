from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.rag.openai_export_adapter import (
    OpenAIExportFileRecord,
    OpenAIExportImageEvidence,
    OpenAIExportInventory,
)
from guardian.queue.account_import_queue import TASK_TYPE
from guardian.services.openai_account_import import AccountImportError
from guardian.workers import account_import_worker


def _record(path: str, kind: str) -> OpenAIExportFileRecord:
    return OpenAIExportFileRecord(
        path=path,
        absolute_path=f"/worker-fixture/{path}",
        size=10,
        extension=Path(path).suffix,
        detected_kind=kind,
        first_bytes_hex="00",
        magic_signature=kind,
    )


class FakeWorkerService:
    def __init__(self) -> None:
        self.limits = SimpleNamespace(
            max_files=100,
            max_total_bytes=1024 * 1024,
            max_file_bytes=1024 * 1024,
            conversation_batch_size=2,
            media_batch_size=2,
        )
        self.calls: list[tuple[str, object]] = []
        self.enqueue_task = lambda job_id, *, user_id: self.calls.append(
            ("enqueue", (job_id, user_id))
        )
        self.raise_materialize: Exception | None = None

    def mark_running(self, **kwargs):
        self.calls.append(("running", kwargs))
        return {"status": "running"}

    def materialize_staged_export(self, **kwargs):
        self.calls.append(("materialize", kwargs))
        if self.raise_materialize:
            raise self.raise_materialize
        return {
            "checkpoint": {
                "conversation_ids": ["already-committed"],
                "media_paths": ["media/already.png"],
            }
        }

    def record_conversation_batch(self, **kwargs):
        self.calls.append(("conversation-batch", kwargs["batch"]))
        return {}

    def import_image_record(self, **kwargs):
        path = kwargs["record"].path
        self.calls.append(("image", path))
        return {
            "path": path,
            "media_id": f"media:{path}",
            "created": True,
            "duplicate": False,
        }

    def record_media_batch(self, **kwargs):
        self.calls.append(("media-batch", kwargs))
        return {}

    def complete_job(self, **kwargs):
        self.calls.append(("complete", kwargs))
        return {"status": "completed"}

    def fail_job(self, **kwargs):
        self.calls.append(("failed", kwargs))
        return {"status": "failed"}

    def recover_incomplete_jobs(self):
        return [
            {"job_id": "queued-job", "user_id": "account-a"},
            {"job_id": "running-job", "user_id": "account-a"},
        ]


def test_worker_resumes_partial_checkpoint_and_processes_remaining_batches(
    monkeypatch: pytest.MonkeyPatch,
):
    service = FakeWorkerService()
    inventory = OpenAIExportInventory(
        root_path="/worker-fixture",
        files=[
            _record("media/already.png", "image_png"),
            _record("media/new.png", "image_png"),
            _record("attachments/manual.pdf", "pdf"),
        ],
        legacy_detected=True,
        sharded_detected=False,
        detected_format="legacy",
    )
    monkeypatch.setattr(
        account_import_worker,
        "diagnose_openai_export_path",
        lambda _root: SimpleNamespace(inventory=inventory),
    )
    observed_completed_ids: list[set[str]] = []

    def import_conversations(_root, **kwargs):
        observed_completed_ids.append(set(kwargs["completed_conversation_ids"]))
        kwargs["on_batch_committed"](
            {
                "conversation_ids": ["new-conversation"],
                "conversation_counts": [
                    {"conversation_id": "new-conversation", "message_count": 2}
                ],
                "threads_imported": 1,
                "messages_imported": 2,
            }
        )
        return SimpleNamespace(errors=[])

    monkeypatch.setattr(
        account_import_worker,
        "import_openai_export_conversations",
        import_conversations,
    )
    monkeypatch.setattr(
        account_import_worker,
        "build_openai_export_image_evidence_index",
        lambda _inventory: {},
    )
    monkeypatch.setattr(
        account_import_worker,
        "resolve_openai_export_image_evidence",
        lambda _path, _index: OpenAIExportImageEvidence(
            source_tag="unclassified"
        ),
    )

    result = account_import_worker.process_account_import_task(
        {
            "type": TASK_TYPE,
            "job_id": "job-1",
            "user_id": "account-a",
        },
        service=service,
    )

    assert result is True
    assert observed_completed_ids == [{"already-committed"}]
    assert ("image", "media/already.png") not in service.calls
    assert ("image", "media/new.png") in service.calls
    media_batches = [payload for name, payload in service.calls if name == "media-batch"]
    assert any(
        batch["results"] and batch["results"][0]["path"] == "media/new.png"
        for batch in media_batches
    )
    assert any(
        batch["warnings"]
        and batch["warnings"][0]["code"] == "image_provenance_unclassified"
        for batch in media_batches
    )
    assert any(
        batch["skipped"]
        and batch["skipped"][0]["path"] == "attachments/manual.pdf"
        for batch in media_batches
    )
    assert service.calls[-1][0] == "complete"


def test_worker_failure_is_persisted_with_bounded_error_code():
    service = FakeWorkerService()
    service.raise_materialize = AccountImportError(
        "staged bytes were corrupted",
        code="staged_file_integrity_failed",
        status_code=500,
    )

    result = account_import_worker.process_account_import_task(
        {
            "type": TASK_TYPE,
            "job_id": "job-failed",
            "user_id": "account-a",
        },
        service=service,
    )

    assert result is False
    failed = [payload for name, payload in service.calls if name == "failed"]
    assert failed == [
        {
            "job_id": "job-failed",
            "user_id": "account-a",
            "code": "staged_file_integrity_failed",
            "message": "staged bytes were corrupted",
        }
    ]


def test_worker_startup_requeues_queued_and_running_jobs():
    service = FakeWorkerService()
    assert account_import_worker.requeue_incomplete_jobs(service) == 2
    assert ("enqueue", ("queued-job", "account-a")) in service.calls
    assert ("enqueue", ("running-job", "account-a")) in service.calls


def test_zip_traversal_is_rejected_before_extraction(tmp_path: Path):
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.json", "[]")
    service = FakeWorkerService()

    with pytest.raises(AccountImportError) as exc_info:
        account_import_worker._safe_extract_zip(
            archive,
            tmp_path / "expanded",
            service=service,
        )

    assert exc_info.value.code == "path_traversal_rejected"
    assert not (tmp_path / "escape.json").exists()
