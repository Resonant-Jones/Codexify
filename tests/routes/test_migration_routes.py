"""Route tests for ChatGPT migration endpoint."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from backend.rag import chatgpt_migration
from guardian.core import dependencies

SERVER_USER_ID = "local_user"


@pytest.fixture(autouse=True)
def _single_user_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")


class StubVectorStore:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add_texts(self, items: list[dict]) -> int:
        self.items.extend(items)
        return len(items)


def _build_mainline_export() -> bytes:
    payload = [
        {
            "id": "route-conv-1",
            "title": "Route Recall Fixture",
            "current_node": "m2",
            "mapping": {
                "m1": {
                    "id": "m1",
                    "parent": None,
                    "children": ["m2"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {
                            "parts": ["Route-imported fact: ORBIT-ROUTE-314."]
                        },
                        "create_time": 1,
                    },
                },
                "m2": {
                    "id": "m2",
                    "parent": "m1",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Stored for recall."]},
                        "create_time": 2,
                    },
                },
            },
        }
    ]
    return json.dumps(payload).encode("utf-8")


def _post_export(test_client, path: str):
    files = {"file": ("export.json", b"[]", "application/json")}
    return test_client.post(
        path,
        files=files,
        headers={"X-User-Id": "spoofed_user"},
    )


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


def test_migration_route_executes_real_ingest_and_embeds(
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

    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_ISOLATED", False)
    monkeypatch.setattr(dependencies, "_vector_store", vector_store)
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

    # Should swallow subprocess failure and return explicit degradation diagnostics.
    diagnostics = chatgpt_migration._embed_items_best_effort(
        items=[{"text": "hello", "meta": {"thread_id": 1}}],
        vector_store=object(),
    )
    assert diagnostics["embedding_candidates"] == 1
    assert diagnostics["embeddings_persisted"] == 0
    assert diagnostics["embeddings_failed"] == 1
    assert diagnostics["embedding_coverage_degraded"] is True


def test_migration_route_reports_embedding_degradation_on_exit_139(
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

    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_ISOLATED", True)
    monkeypatch.setattr(
        chatgpt_migration.mp, "get_context", lambda *_: _FakeContext()
    )
    monkeypatch.setattr(dependencies, "_vector_store", object())
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


def test_migration_rejects_oversized_file(test_client):
    """Oversized file should return 413 instead of loading into memory."""
    # Create payload larger than 50MB limit
    oversized_content = b"x" * (51 * 1024 * 1024)
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

    assert response.status_code == 413
    assert "50MB" in response.json()["detail"]


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
    assert data["embeddings_persisted"] == 0
    assert data["embeddings_failed"] == 2
    assert data["embedding_coverage_degraded"] is True
    # DB records were created
    assert mock_db.create_chat_thread.call_count == 1
    assert mock_db.create_message.call_count == 2
