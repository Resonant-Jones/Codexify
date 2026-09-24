from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from guardian.services.openai_account_import import (
    AccountImportError,
    OpenAIAccountImportService,
)


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def join(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def limit(self, _limit):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def query(self, *_models):
        return _Query(self.rows)


class _DB:
    def __init__(self, rows):
        self.rows = rows

    def get_session(self):
        return _Session(self.rows)


def _row(
    message_id: int,
    *,
    owner: str = "account-a",
    project_owner: str = "account-a",
    source_id: str = "source-1",
    status: str = "pending",
    origin: str = "openai",
):
    message = SimpleNamespace(
        id=message_id,
        user_id=owner,
        thread_id=10,
        role="assistant",
        content="imported assistant marker",
        event_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        extra_meta={
            "user_id": "presentation-only-value",
            "source_thread_id": source_id,
            "source_message_id": f"source-message-{message_id}",
            "embedding_status": status,
            "turn_index": 1,
            "canonical_filter_profile": "chatgpt_v1_canonical",
        },
    )
    thread = SimpleNamespace(id=10, user_id=owner, project_id=20, origin_system=origin)
    project = SimpleNamespace(id=20, user_id=project_owner)
    return message, thread, project


def _service(rows, *, source_system="openai"):
    payloads = []
    service = object.__new__(OpenAIAccountImportService)
    service.db = _DB(rows)
    service.enqueue_import_embedding_task = payloads.append
    service._require_job = lambda _session, _job_id, _user_id: SimpleNamespace(
        source_system=source_system,
        checkpoint={"conversation_ids": ["source-1"]},
    )
    return service, payloads


def test_handoff_uses_only_committed_canonical_owner_and_provenance(monkeypatch):
    from guardian.services import openai_account_import

    monkeypatch.setattr(openai_account_import, "_IMPORT_EMBED_TEXT_LIMIT", 8)
    service, payloads = _service(
        [
            _row(1),
            _row(2, owner="account-b"),
            _row(3, project_owner="account-b"),
            _row(4, source_id="other-source"),
            _row(5, status="ready"),
            _row(6, origin="anthropic"),
        ]
    )

    count = service.enqueue_pending_import_embeddings(
        job_id="job-1", user_id="account-a", conversation_ids=["source-1"]
    )

    assert count == 1
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["message_id"] == 1
    assert payload["content"] == "imported"
    assert payload["meta"]["user_id"] == "account-a"
    assert payload["meta"]["source_thread_id"] == "source-1"
    assert payload["meta"]["source_message_id"] == "source-message-1"
    assert payload["meta"]["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert "raw_message" not in payload["meta"]

    # A crash after an uncertain Redis enqueue may replay the same durable
    # pending row; its canonical identity and provenance remain unchanged.
    assert (
        service.enqueue_pending_import_embeddings(
            job_id="job-1", user_id="account-a", conversation_ids=["source-1"]
        )
        == 1
    )
    assert payloads == [payload, payload]


def test_handoff_rejects_uncommitted_source_and_other_source_family():
    service, payloads = _service([_row(1)])
    with pytest.raises(AccountImportError) as exc_info:
        service.enqueue_pending_import_embeddings(
            job_id="job-1", user_id="account-a", conversation_ids=["not-committed"]
        )
    assert exc_info.value.code == "embedding_handoff_uncommitted_conversation"
    assert payloads == []

    other_service, other_payloads = _service([_row(1)], source_system="anthropic")
    assert (
        other_service.enqueue_pending_import_embeddings(
            job_id="job-2", user_id="account-a"
        )
        == 0
    )
    assert other_payloads == []


def test_partial_queue_failure_replays_canonical_pending_rows():
    service, _payloads = _service([_row(1), _row(2)])
    first_attempt = []

    def fail_after_first(payload):
        first_attempt.append(payload)
        if len(first_attempt) == 2:
            raise RuntimeError("Redis write result unavailable")

    service.enqueue_import_embedding_task = fail_after_first
    with pytest.raises(RuntimeError, match="Redis write result unavailable"):
        service.enqueue_pending_import_embeddings(job_id="job-1", user_id="account-a")

    replay = []
    service.enqueue_import_embedding_task = replay.append
    assert (
        service.enqueue_pending_import_embeddings(job_id="job-1", user_id="account-a")
        == 2
    )
    assert replay == first_attempt
    assert [payload["message_id"] for payload in replay] == [1, 2]
