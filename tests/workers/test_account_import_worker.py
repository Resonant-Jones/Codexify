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
        self.raise_complete: Exception | None = None

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

    def record_source_summary(self, **kwargs):
        self.calls.append(("source-summary", kwargs["summary"]))
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
        if self.raise_complete:
            raise self.raise_complete
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
        return SimpleNamespace(
            errors=[],
            conversations_discovered=1,
            conversations_accepted=1,
            conversations_skipped_title=0,
            conversations_skipped_limit=0,
            conversations_skipped_duplicate=0,
            conversations_skipped_checkpoint=0,
            conversations_failed=0,
            text_import_complete=True,
        )

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
    assert (
        "source-summary",
        {
            "conversations_discovered": 1,
            "conversations_accepted": 1,
            "conversations_skipped": 0,
            "conversations_failed": 0,
            "conversation_transactions_committed": True,
        },
    ) in service.calls
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


def test_worker_records_zero_write_completion_as_terminal_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    service = FakeWorkerService()
    service.raise_complete = AccountImportError(
        "The export finished processing, but no canonical entities were committed.",
        code="account_import_no_committed_entities",
        status_code=500,
    )
    inventory = OpenAIExportInventory(
        root_path="/worker-fixture",
        files=[],
        legacy_detected=True,
        sharded_detected=False,
        detected_format="legacy",
    )
    monkeypatch.setattr(
        account_import_worker,
        "diagnose_openai_export_path",
        lambda _root: SimpleNamespace(inventory=inventory),
    )
    monkeypatch.setattr(
        account_import_worker,
        "import_openai_export_conversations",
        lambda _root, **_kwargs: SimpleNamespace(
            errors=[],
            conversations_discovered=1,
            conversations_accepted=1,
            conversations_skipped_title=0,
            conversations_skipped_limit=0,
            conversations_skipped_duplicate=0,
            conversations_skipped_checkpoint=0,
            conversations_failed=1,
            text_import_complete=True,
        ),
    )
    monkeypatch.setattr(
        account_import_worker,
        "build_openai_export_image_evidence_index",
        lambda _inventory: {},
    )

    result = account_import_worker.process_account_import_task(
        {"type": TASK_TYPE, "job_id": "job-zero", "user_id": "account-a"},
        service=service,
    )

    assert result is False
    assert ("complete", {"job_id": "job-zero", "user_id": "account-a"}) in service.calls
    assert (
        "failed",
        {
            "job_id": "job-zero",
            "user_id": "account-a",
            "code": "account_import_no_committed_entities",
            "message": "The export finished processing, but no canonical entities were committed.",
        },
    ) in service.calls


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


# ---------------------------------------------------------------------------
# Anthropic dispatch (source-system branch)
# ---------------------------------------------------------------------------


class FakeAnthropicService(FakeWorkerService):
    """Worker service stub whose ``materialize_staged_export`` reports the
    ``source_system`` we want the dispatch to read."""

    def __init__(self, *, source_system: str) -> None:
        super().__init__()
        self._source_system = source_system

    def materialize_staged_export(self, **kwargs):  # type: ignore[override]
        self.calls.append(("materialize", kwargs))
        if self.raise_materialize:
            raise self.raise_materialize
        return {
            "checkpoint": {
                "conversation_ids": [],
                "media_paths": [],
            },
            "source_system": self._source_system,
        }


def test_worker_dispatches_anthropic_source_to_anthropic_adapter(
    monkeypatch: pytest.MonkeyPatch,
):
    service = FakeAnthropicService(source_system="anthropic")
    observed: dict[str, object] = {}

    def _import_anthropic(root, **kwargs):
        observed["root"] = root
        observed["user_id"] = kwargs["user_id"]
        return SimpleNamespace(
            errors=[],
            conversations_discovered=2,
            conversations_imported=2,
            conversations_failed=0,
        )

    # Guard against any OpenAI-specific imports leaking into the Anthropic
    # dispatch path.
    def _openai_guard(*_args, **_kwargs):
        raise AssertionError(
            "Anthropic dispatch must not invoke OpenAI-specific imports."
        )

    monkeypatch.setattr(
        account_import_worker,
        "import_anthropic_export_conversations",
        _import_anthropic,
    )
    monkeypatch.setattr(
        account_import_worker,
        "import_openai_export_conversations",
        _openai_guard,
    )
    monkeypatch.setattr(
        account_import_worker,
        "diagnose_openai_export_path",
        _openai_guard,
    )
    monkeypatch.setattr(
        account_import_worker,
        "build_openai_export_image_evidence_index",
        _openai_guard,
    )
    monkeypatch.setattr(
        account_import_worker,
        "resolve_openai_export_image_evidence",
        _openai_guard,
    )

    result = account_import_worker.process_account_import_task(
        {
            "type": TASK_TYPE,
            "job_id": "job-anthropic",
            "user_id": "account-a",
        },
        service=service,
    )

    assert result is True
    assert observed["user_id"] == "account-a"
    # The Anthropic branch records its source summary and completes the job
    # without going through the OpenAI image path.
    assert any(
        name == "source-summary" and payload["conversations_discovered"] == 2
        for name, payload in service.calls
    )
    assert any(name == "complete" for name, _ in service.calls)
    # Crucially: the OpenAI-only helpers were never called.
    assert not any(
        name in {"conversation-batch", "media-batch"} for name, _ in service.calls
    )


def test_worker_keeps_openai_dispatch_unchanged(
    monkeypatch: pytest.MonkeyPatch,
):
    """The Anthropic allow-list must NOT regress OpenAI dispatch behavior."""

    service = FakeAnthropicService(source_system="openai")
    inventory = OpenAIExportInventory(
        root_path="/worker-fixture",
        files=[],
        legacy_detected=True,
        sharded_detected=False,
        detected_format="legacy",
    )
    monkeypatch.setattr(
        account_import_worker,
        "diagnose_openai_export_path",
        lambda _root: SimpleNamespace(inventory=inventory),
    )

    def _import_openai(_root, **kwargs):
        kwargs["on_batch_committed"](
            {
                "conversation_ids": ["c-1"],
                "conversation_counts": [
                    {"conversation_id": "c-1", "message_count": 1}
                ],
                "threads_imported": 1,
                "messages_imported": 1,
            }
        )
        return SimpleNamespace(
            errors=[],
            conversations_discovered=1,
            conversations_accepted=1,
            conversations_skipped_title=0,
            conversations_skipped_limit=0,
            conversations_skipped_duplicate=0,
            conversations_skipped_checkpoint=0,
            conversations_failed=0,
            text_import_complete=True,
        )

    def _openai_guard(*_args, **_kwargs):
        raise AssertionError(
            "OpenAI dispatch must not invoke the Anthropic adapter."
        )

    monkeypatch.setattr(
        account_import_worker,
        "import_openai_export_conversations",
        _import_openai,
    )
    monkeypatch.setattr(
        account_import_worker,
        "import_anthropic_export_conversations",
        _openai_guard,
    )
    monkeypatch.setattr(
        account_import_worker,
        "build_openai_export_image_evidence_index",
        lambda _inventory: {},
    )
    monkeypatch.setattr(
        account_import_worker,
        "resolve_openai_export_image_evidence",
        lambda _path, _index: OpenAIExportImageEvidence(source_tag="unclassified"),
    )

    result = account_import_worker.process_account_import_task(
        {
            "type": TASK_TYPE,
            "job_id": "job-openai",
            "user_id": "account-a",
        },
        service=service,
    )

    assert result is True
    # OpenAI dispatch continues to record conversation batch commits and
    # source summary as it did before the Anthropic allow-list was added.
    assert any(name == "conversation-batch" for name, _ in service.calls)
    assert any(name == "source-summary" for name, _ in service.calls)
    assert any(name == "complete" for name, _ in service.calls)


def test_worker_anthropic_dispatch_fails_closed_on_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
):
    service = FakeAnthropicService(source_system="anthropic")

    def _import_anthropic(_root, **kwargs):
        return SimpleNamespace(
            errors=["chat_messages payload was missing"],
            conversations_discovered=0,
            conversations_imported=0,
            conversations_failed=0,
        )

    monkeypatch.setattr(
        account_import_worker,
        "import_anthropic_export_conversations",
        _import_anthropic,
    )

    result = account_import_worker.process_account_import_task(
        {
            "type": TASK_TYPE,
            "job_id": "job-anthropic-fail",
            "user_id": "account-a",
        },
        service=service,
    )

    assert result is False
    failed = [payload for name, payload in service.calls if name == "failed"]
    assert failed == [
        {
            "job_id": "job-anthropic-fail",
            "user_id": "account-a",
            "code": "account_import_worker_failed",
            "message": "chat_messages payload was missing",
        }
    ]
