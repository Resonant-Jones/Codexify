"""Route tests for ChatGPT migration endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.rag import chatgpt_migration
from guardian.core import dependencies
from guardian.queue.redis_queue import dequeue_chat_import_embed
from guardian.routes import migration as migration_routes
from guardian.workers import chat_embedding_worker

SERVER_USER_ID = "local_user"


@pytest.fixture(autouse=True)
def _single_user_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")


class StubVectorStore:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.batch_sizes: list[int] = []

    def add_texts(self, items: list[dict]) -> int:
        self.batch_sizes.append(len(items))
        self.items.extend(items)
        return len(items)


def _drain_chat_import_queue() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    while True:
        payload = dequeue_chat_import_embed(block=False)
        if not payload:
            break
        payloads.append(payload)
    return payloads


def _build_mainline_export(
    turns: list[tuple[str, str, float]] | None = None,
) -> bytes:
    if turns is None:
        turns = [
            ("user", "Route-imported fact: ORBIT-ROUTE-314.", 1),
            ("assistant", "Stored for recall.", 2),
        ]
    payload = [
        {
            "id": "route-conv-1",
            "title": "Route Recall Fixture",
            "current_node": f"m{len(turns)}",
            "mapping": {},
        }
    ]
    parent = None
    for idx, (role, text, create_time) in enumerate(turns, start=1):
        node_id = f"m{idx}"
        payload[0]["mapping"][node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "author": {"role": role},
                "content": {"parts": [text]},
                "create_time": create_time,
            },
        }
        if parent is not None:
            payload[0]["mapping"][parent]["children"].append(node_id)
        parent = node_id
    return json.dumps(payload).encode("utf-8")


def _build_large_export(min_size: int) -> bytes:
    payload = _build_mainline_export()
    if len(payload) >= min_size:
        return payload
    padding = b" " * (min_size - len(payload))
    return payload + padding


def _post_export(test_client, path: str):
    files = {"file": ("export.json", b"[]", "application/json")}
    return test_client.post(
        path,
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )


def _post_retry(test_client, path: str):
    return test_client.post(path, headers={"X-User-Id": "spoofed_user"})


def test_migration_endpoint_registered(test_client):
    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as mock_ingest:
        mock_ingest.return_value = {
            "threads_imported": 1,
            "messages_imported": 2,
        }
        canonical = _post_export(test_client, "/api/upload-chatgpt-export")
        legacy = _post_export(test_client, "/upload-chatgpt-export")

    assert canonical.status_code == 200
    assert legacy.status_code == 200

    for res in (canonical, legacy):
        data = res.json()
        assert data["threads_imported"] == 1
        assert data["messages_imported"] == 2
        assert data["embedding_candidates"] == 0
        assert data["embeddings_persisted"] == 0
        assert data["embeddings_failed"] == 0
        assert data["embedding_coverage_degraded"] is False
    assert len(mock_ingest.call_args_list) == 2
    for call in mock_ingest.call_args_list:
        assert call.kwargs["user_id"] == SERVER_USER_ID


def test_retry_route_recovers_previous_missing_embeddings(
    test_client,
    monkeypatch,
):
    retry_items = [
        {
            "message_id": 301,
            "text": "Recovered import chunk A",
            "meta": {"message_id": 301, "thread_id": 21},
        },
        {
            "message_id": 302,
            "text": "Recovered import chunk B",
            "meta": {"message_id": 302, "thread_id": 21},
        },
    ]

    dummy_db = object()

    _drain_chat_import_queue()
    monkeypatch.setattr(dependencies, "chatlog_db", dummy_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: dummy_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_fetch_retryable_chatgpt_embedding_items",
        lambda _db, *, user_id, limit=5000: retry_items
        if user_id == SERVER_USER_ID
        else [],
    )

    response = _post_retry(test_client, "/api/retry-chatgpt-import-embeddings")
    assert response.status_code == 200
    data = response.json()
    assert data["embedding_candidates"] == 2
    assert data["embeddings_persisted"] == 2
    assert data["embeddings_failed"] == 0
    assert data["embedding_coverage_degraded"] is False
    queued_payloads = _drain_chat_import_queue()
    assert len(queued_payloads) == 2
    assert [payload["message_id"] for payload in queued_payloads] == [
        301,
        302,
    ]
    assert all(
        payload["type"] == "chat_import_embed" for payload in queued_payloads
    )


def test_retry_route_reports_degraded_success_on_queue_failure(
    test_client,
    monkeypatch,
):
    retry_items = [
        {
            "message_id": 401,
            "text": "Retry candidate 1",
            "meta": {"message_id": 401, "thread_id": 31},
        },
        {
            "message_id": 402,
            "text": "Retry candidate 2",
            "meta": {"message_id": 402, "thread_id": 31},
        },
    ]
    dummy_db = object()

    _drain_chat_import_queue()
    monkeypatch.setattr(dependencies, "chatlog_db", dummy_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: dummy_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_fetch_retryable_chatgpt_embedding_items",
        lambda *_args, **_kwargs: retry_items,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "enqueue_chat_import_embed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("queue unavailable")
        ),
    )

    response = _post_retry(test_client, "/api/retry-chatgpt-import-embeddings")
    assert response.status_code == 200
    data = response.json()
    assert data["embedding_candidates"] == 2
    assert data["embeddings_persisted"] == 0
    assert data["embeddings_failed"] == 2
    assert data["embedding_coverage_degraded"] is True
    assert _drain_chat_import_queue() == []


def test_retry_route_returns_noop_when_nothing_retryable(
    test_client,
    monkeypatch,
):
    dummy_db = object()
    monkeypatch.setattr(dependencies, "chatlog_db", dummy_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: dummy_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_fetch_retryable_chatgpt_embedding_items",
        lambda *_args, **_kwargs: [],
    )

    def _unexpected_embed(*_args, **_kwargs):
        raise AssertionError("queue handoff should not run for no-op retry")

    monkeypatch.setattr(
        chatgpt_migration,
        "_queue_chatgpt_embedding_batch",
        _unexpected_embed,
    )

    response = _post_retry(test_client, "/api/retry-chatgpt-import-embeddings")
    assert response.status_code == 200
    data = response.json()
    assert data["embedding_candidates"] == 0
    assert data["embeddings_persisted"] == 0
    assert data["embeddings_failed"] == 0
    assert data["embedding_coverage_degraded"] is False


def test_migration_accepts_valid_content_even_with_non_json_filename(
    test_client,
):
    valid_payload = b"[]"
    files = {
        "file": (
            "totally_weird_name.txt",
            valid_payload,
            "application/octet-stream",
        )
    }

    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as mock_ingest:
        mock_ingest.return_value = {
            "threads_imported": 0,
            "messages_imported": 0,
        }
        response = test_client.post(
            "/api/upload-chatgpt-export",
            files=files,
            headers={"X-User-Id": "spoofed_user"},
        )

    assert response.status_code == 200
    mock_ingest.assert_called_once()
    assert mock_ingest.call_args.kwargs["user_id"] == SERVER_USER_ID


def test_migration_route_executes_real_ingest_and_catches_up_embeddings(
    test_client,
    mock_db,
    monkeypatch,
):
    vector_store = StubVectorStore()
    message_ids = iter([91, 92])

    def fake_create_message(
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        _ = thread_id, role, content, created_at
        return next(message_ids)

    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.side_effect = fake_create_message
    mock_db.ensure_project.return_value = 1

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    _drain_chat_import_queue()

    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    files = {
        "file": (
            "conversations-weird-name.txt",
            _build_mainline_export(),
            "application/octet-stream",
        )
    }

    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threads_imported"] == 1
    assert data["messages_imported"] == 2
    assert data["embedding_candidates"] == 2
    assert data["embeddings_persisted"] == 2
    assert data["embeddings_failed"] == 0
    assert data["embedding_coverage_degraded"] is False
    queued_payloads = _drain_chat_import_queue()
    assert len(queued_payloads) == 2
    for payload in queued_payloads:
        payload = dict(payload)
        payload.pop("message_id", None)
        assert (
            chat_embedding_worker.process_chat_embed_task(
                payload,
                vector_store=vector_store,
            )
            is True
        )
    assert len(vector_store.items) == 2
    assert "ORBIT-ROUTE-314" in str(vector_store.items[0].get("text", ""))
    assert mock_db.ensure_project.call_count == 1
    assert mock_db.create_chat_thread.call_count == 1
    assert mock_db.create_message.call_count == 2
    created_messages = [
        {
            "thread_id": call.args[0],
            "role": call.args[1],
            "content": call.args[2],
        }
        for call in mock_db.create_message.call_args_list
    ]
    assert [entry["thread_id"] for entry in created_messages] == [42, 42]
    assert [entry["role"] for entry in created_messages] == [
        "user",
        "assistant",
    ]
    assert "ORBIT-ROUTE-314" in created_messages[0]["content"]
    assert (
        mock_db.create_chat_thread.call_args.kwargs["user_id"] == SERVER_USER_ID
    )


def test_migration_route_batches_embedding_follow_up(
    test_client,
    mock_db,
    monkeypatch,
):
    vector_store = StubVectorStore()
    message_ids = iter([91, 92, 93, 94, 95])

    def fake_create_message(
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        _ = thread_id, role, content, created_at
        return next(message_ids)

    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.side_effect = fake_create_message
    mock_db.ensure_project.return_value = 1

    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_BATCH_SIZE", 2)
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    _drain_chat_import_queue()

    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    files = {
        "file": (
            "conversations-batched.json",
            _build_mainline_export(
                [
                    ("user", "Route chunk 1", 1),
                    ("assistant", "Route chunk 2", 2),
                    ("user", "Route chunk 3", 3),
                    ("assistant", "Route chunk 4", 4),
                    ("user", "Route chunk 5", 5),
                ]
            ),
            "application/json",
        )
    }

    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threads_imported"] == 1
    assert data["messages_imported"] == 5
    assert data["embedding_candidates"] == 5
    assert data["embeddings_persisted"] == 5
    assert data["embeddings_failed"] == 0
    assert data["embedding_coverage_degraded"] is False
    queued_payloads = _drain_chat_import_queue()
    assert len(queued_payloads) == 5
    for payload in queued_payloads:
        payload = dict(payload)
        payload.pop("message_id", None)
        assert (
            chat_embedding_worker.process_chat_embed_task(
                payload,
                vector_store=vector_store,
            )
            is True
        )
    assert len(vector_store.items) == 5
    assert mock_db.create_message.call_count == 5


def test_embed_items_best_effort_handles_subprocess_segfault(monkeypatch):
    class _FakeProcess:
        def __init__(self, *_args, **_kwargs) -> None:
            self.exitcode = 139
            self._alive = False

        def start(self) -> None:
            return None

        def join(self, timeout: float | None = None) -> None:
            _ = timeout

        def is_alive(self) -> bool:
            return self._alive

        def terminate(self) -> None:
            self._alive = False

    class _FakeContext:
        def Process(self, *args, **kwargs):  # noqa: N802
            _ = args, kwargs
            return _FakeProcess()

    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_ISOLATED", True)
    monkeypatch.setattr(
        chatgpt_migration.mp, "get_context", lambda *_: _FakeContext()
    )
    vector_store = MagicMock()

    # Should swallow subprocess failure and return explicit degradation diagnostics.
    diagnostics = chatgpt_migration._embed_items_best_effort(
        items=[{"text": "hello", "meta": {"thread_id": 1}}],
        vector_store=vector_store,
    )
    assert diagnostics["embedding_candidates"] == 1
    assert diagnostics["embeddings_persisted"] == 0
    assert diagnostics["embeddings_failed"] == 1
    assert diagnostics["embedding_coverage_degraded"] is True
    assert diagnostics["failure_class"] == "subprocess_exit_139"
    vector_store.add_texts.assert_not_called()


def test_migration_route_reports_embedding_degradation_on_queue_failure(
    test_client,
    mock_db,
    monkeypatch,
):
    message_ids = iter([121, 122])

    def fake_create_message(
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        _ = thread_id, role, content, created_at
        return next(message_ids)

    class _FakeProcess:
        def __init__(self, *_args, **_kwargs) -> None:
            self.exitcode = 139
            self._alive = False

        def start(self) -> None:
            return None

        def join(self, timeout: float | None = None) -> None:
            _ = timeout

        def is_alive(self) -> bool:
            return self._alive

        def terminate(self) -> None:
            self._alive = False

    class _FakeContext:
        def Process(self, *args, **kwargs):  # noqa: N802
            _ = args, kwargs
            return _FakeProcess()

    mock_db.create_chat_thread.return_value = {"id": 44}
    mock_db.create_message.side_effect = fake_create_message
    mock_db.ensure_project.return_value = 1

    _drain_chat_import_queue()
    monkeypatch.setattr(
        chatgpt_migration,
        "enqueue_chat_import_embed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("queue unavailable")
        ),
    )
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    files = {
        "file": (
            "conversations.json",
            _build_mainline_export(),
            "application/json",
        )
    }
    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["threads_imported"] == 1
    assert data["messages_imported"] == 2
    assert data["embedding_candidates"] == 2
    assert data["embeddings_persisted"] == 0
    assert data["embeddings_failed"] == 2
    assert data["embedding_coverage_degraded"] is True


def test_migration_accepts_large_export(test_client, monkeypatch):
    """Large but valid exports should be accepted and processed."""
    oversized_content = _build_large_export(51 * 1024 * 1024)
    captured: dict[str, object] = {}

    def fake_ingest(content: bytes, user_id: str | None = None):
        captured["size"] = len(content)
        captured["user_id"] = user_id
        parsed = json.loads(content)
        chatgpt_migration._validate_chatgpt_export_payload(parsed)
        return {
            "threads_imported": 0,
            "messages_imported": 0,
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        }

    monkeypatch.setattr(migration_routes, "ingest_chatgpt_export", fake_ingest)

    files = {
        "file": (
            "huge_export.json",
            oversized_content,
            "application/json",
        )
    }

    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )

    assert response.status_code == 200
    assert captured["size"] >= 51 * 1024 * 1024
    assert captured["user_id"] == SERVER_USER_ID
    assert response.json()["threads_imported"] == 0


def test_migration_rejects_malformed_json(test_client):
    """Malformed JSON should return 400, not crash the backend."""
    files = {
        "file": (
            "invalid.json",
            b"this is not valid json {{{",
            "application/json",
        )
    }

    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )

    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_migration_succeeds_without_vector_store(
    test_client,
    mock_db,
    monkeypatch,
):
    """Import should succeed (DB records created) even when vector store is unavailable."""
    message_ids = iter([101, 102])

    def fake_create_message(
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        _ = thread_id, role, content, created_at
        return next(message_ids)

    mock_db.create_chat_thread.return_value = {"id": 99}
    mock_db.create_message.side_effect = fake_create_message
    mock_db.ensure_project.return_value = 1

    # Explicitly set vector store to None - do NOT initialize
    monkeypatch.setattr(dependencies, "_vector_store", None)
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    files = {
        "file": (
            "conversations.json",
            _build_mainline_export(),
            "application/json",
        )
    }

    response = test_client.post(
        "/api/upload-chatgpt-export",
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )

    # Import should succeed - we got DB records
    assert response.status_code == 200
    data = response.json()
    assert data["threads_imported"] == 1
    assert data["messages_imported"] == 2
    assert data["embedding_candidates"] == 2
    assert data["embeddings_persisted"] == 2
    assert data["embeddings_failed"] == 0
    assert data["embedding_coverage_degraded"] is False
    queued_payloads = _drain_chat_import_queue()
    assert len(queued_payloads) == 2
    # DB records were created
    assert mock_db.create_chat_thread.call_count == 1
    assert mock_db.create_message.call_count == 2
