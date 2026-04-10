from __future__ import annotations

import importlib
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import chat
from guardian.services import builtin_help_ingest as help_ingest


def _accepted_task_created_event(task_id: str) -> dict[str, object]:
    return {
        "ok": True,
        "task_id": task_id,
        "event_type": "task.created",
        "visibility_scope": "progress",
        "terminal_visibility": False,
        "execution_continued": True,
        "event_id": f"{task_id}:created",
        "failure_class": None,
        "error": None,
    }


@contextmanager
def _supported_help_startup_client(
    monkeypatch, tmp_path
) -> Iterator[tuple[TestClient, object, dict[str, int]]]:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("CODEXIFY_BETA_CORE_ONLY", "0")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("ENABLE_OUTBOX", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "supported_retrieval_golden")
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    class _State:
        def __init__(self) -> None:
            self.uploaded_documents = {}
            self.project_links = {}

    class _Query:
        def __init__(self, state: _State, model) -> None:
            self._state = state
            self._model = model
            self._filters: dict[str, object] = {}
            self._limit: int | None = None

        def filter(self, *args, **kwargs):
            _ = args, kwargs
            return self

        def filter_by(self, **kwargs):
            self._filters.update(kwargs)
            return self

        def order_by(self, *args, **kwargs):
            _ = args, kwargs
            return self

        def limit(self, value):
            try:
                self._limit = int(value)
            except (TypeError, ValueError):
                self._limit = None
            return self

        def all(self):
            if self._model.__name__ != "UploadedDocument":
                return []
            rows = [
                doc
                for doc in self._state.uploaded_documents.values()
                if getattr(doc, "deleted_at", None) is None
            ]
            if "project_id" in self._filters:
                rows = [
                    doc
                    for doc in rows
                    if getattr(doc, "project_id", None)
                    == self._filters["project_id"]
                ]
            if "thread_id" in self._filters:
                rows = [
                    doc
                    for doc in rows
                    if getattr(doc, "thread_id", None)
                    == self._filters["thread_id"]
                ]
            if "source_tag" in self._filters:
                rows = [
                    doc
                    for doc in rows
                    if getattr(doc, "source_tag", None)
                    == self._filters["source_tag"]
                ]
            if self._limit is not None:
                rows = rows[: self._limit]
            return rows

        def first(self):
            if self._model.__name__ == "UploadedDocument":
                doc_id = str(self._filters.get("id") or "")
                return self._state.uploaded_documents.get(doc_id)
            if self._model.__name__ == "ProjectDocumentLink":
                key = (
                    int(self._filters.get("project_id") or 0),
                    str(self._filters.get("document_id") or ""),
                    str(self._filters.get("document_type") or ""),
                )
                return self._state.project_links.get(key)
            raise AssertionError(f"Unexpected query model: {self._model!r}")

    class _Session:
        def __init__(self, state: _State) -> None:
            self._state = state
            self.commits = 0

        def query(self, model):
            return _Query(self._state, model)

        def add(self, obj):
            if obj.__class__.__name__ == "UploadedDocument":
                self._state.uploaded_documents[obj.id] = obj
                return
            if obj.__class__.__name__ == "ProjectDocumentLink":
                key = (obj.project_id, obj.document_id, obj.document_type)
                self._state.project_links[key] = obj
                return
            raise AssertionError(f"Unexpected add object: {type(obj)!r}")

        def commit(self):
            self.commits += 1

    class _SessionContext:
        def __init__(self, session: _Session) -> None:
            self._session = session

        def __enter__(self):
            return self._session

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeGuardianDB:
        def __init__(self, project_id: int = 9) -> None:
            self.project_id = project_id
            self.state = _State()

        def ensure_default_project(self) -> int:
            return self.project_id

        def get_session(self):
            return _SessionContext(_Session(self.state))

    class _FakeChatlogDB:
        def list_connector_configs(self):
            return []

        def ensure_event_outbox(self):
            return None

        def ensure_sync_job_support(self):
            return None

        def sync_inference_provider_rows_from_catalog(self):
            return {}

    fake_guardian_db = _FakeGuardianDB(project_id=9)
    fake_chatlog_db = _FakeChatlogDB()

    real_ingest = help_ingest.ingest_builtin_help_document
    ingest_calls = {"count": 0}

    def _wrapped_ingest(*args, **kwargs):
        ingest_calls["count"] += 1
        return real_ingest(*args, **kwargs)

    monkeypatch.setattr(
        help_ingest,
        "ingest_builtin_help_document",
        _wrapped_ingest,
    )

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    monkeypatch.setattr(
        guardian_api,
        "assert_config_coherence",
        lambda _settings: None,
    )
    monkeypatch.setattr(
        guardian_api.dependencies,
        "init_database",
        lambda: fake_chatlog_db,
    )
    monkeypatch.setattr(
        guardian_api,
        "load_guardian_db_from_env",
        lambda: fake_guardian_db,
    )
    monkeypatch.setattr(guardian_api, "ensure_default_project", lambda: True)
    monkeypatch.setattr(
        guardian_api,
        "_schedule_chatgpt_import_startup_sweep",
        lambda _app: None,
    )
    monkeypatch.setattr(guardian_api, "ENABLE_OUTBOX", False)
    monkeypatch.setattr(guardian_api, "ENABLE_CONNECTOR_WORKER", False)

    import guardian.routes.media as media_routes

    monkeypatch.setattr(
        media_routes,
        "load_guardian_db_from_env",
        lambda: fake_guardian_db,
    )

    with TestClient(guardian_api.app) as client:
        try:
            yield client, fake_guardian_db, ingest_calls
        finally:
            from guardian.core import event_bus

            event_bus.reset()
            importlib.reload(guardian_api)


def test_golden_completion_acceptance_contract(monkeypatch):
    mock_db = MagicMock()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 1,
    }
    mock_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "Hello there"}
    ]
    mock_db.write_audit_log.return_value = None

    captured: dict[str, object] = {}
    monkeypatch.setattr(chat, "chatlog_db", mock_db)
    monkeypatch.setattr(
        "guardian.core.dependencies.chatlog_db",
        mock_db,
        raising=False,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.chat.task_events.publish_with_visibility",
        lambda task_id, event_type, data: _accepted_task_created_event(task_id),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    app.dependency_overrides[chat.require_api_key] = lambda: "test-api-key"

    with TestClient(app) as test_client:
        response = test_client.post("/api/chat/1/complete", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["acceptance_status"] == "accepted"
    assert payload["acceptance_warnings"] == []
    assert isinstance(payload["task_id"], str)
    assert payload["thread_id"] == 1
    assert payload["messages_url"] == "/api/chat/1/messages"
    assert payload["trace_url"] == "/api/chat/debug/rag-trace/1/latest"
    assert "execution" not in payload
    assert captured["queue_name"] == "codexify:queue:chat"
    assert getattr(captured["task"], "turn_lock_owner") == payload["task_id"]
    # Accepted work is queued for execution; it is not terminal completion.


def test_golden_rag_trace_latest_and_isolation(monkeypatch):
    original_latest_task = dict(chat._thread_latest_task)
    original_rag_traces = dict(chat._rag_traces)
    task_payloads = {
        "task-completed-11": {
            "trace": {
                "documents": [
                    {
                        "id": "doc-11",
                        "title": "thread-11.md",
                        "score": 0.94,
                        "snippet": "thread 11 trace",
                    }
                ],
                "graph": [],
                "retrieval_query": "thread 11 query",
                "retrieval_target": "latest_turn",
                "retrieval_query_matches_latest_turn": True,
                "payload_summary": {"message_count": 2},
            }
        },
        "task-completed-31": {
            "trace": {
                "documents": [
                    {
                        "id": "doc-31",
                        "title": "thread-31.md",
                        "score": 0.91,
                        "snippet": "thread 31 trace",
                    }
                ],
                "graph": [],
                "payload_summary": {"message_count": 3},
            }
        },
        "task-completed-32": {
            "trace": {
                "documents": [
                    {
                        "id": "doc-32",
                        "title": "thread-32.md",
                        "score": 0.88,
                        "snippet": "thread 32 trace",
                    }
                ],
                "graph": [
                    {"node_id": "node-32", "kind": "memory", "text": "x"}
                ],
                "payload_summary": {"message_count": 4},
            }
        },
    }

    def _fake_completed_payload(task_id, block_ms=0):
        _ = block_ms
        return task_payloads.get(task_id)

    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        _fake_completed_payload,
    )
    monkeypatch.setattr(
        "guardian.routes.chat._fetch_thread_metadata",
        lambda _thread_id: {},
    )
    monkeypatch.setattr(
        "guardian.routes.chat.resolve_thread_system_profile",
        lambda *args, **kwargs: None,
    )
    try:
        chat._thread_latest_task.clear()
        chat._rag_traces.clear()

        chat._thread_latest_task[11] = "task-completed-11"
        latest = chat.get_latest_rag_trace(11, api_key="test-key")
        assert latest["thread_id"] == 11
        assert latest["documents"][0]["id"] == "doc-11"
        assert latest["retrieval_target"] == "latest_turn"
        assert latest["retrieval_query_matches_latest_turn"] is True
        assert latest["payload_summary"] == {"message_count": 2}

        untouched = chat.get_latest_rag_trace(22, api_key="test-key")
        assert untouched["thread_id"] == 22
        assert untouched["documents"] == []
        assert untouched["graph"] == []
        assert untouched["project_id"] is None
        assert untouched["source_mode"] is None
        assert untouched["widen_reason"] == "none"

        chat._thread_latest_task[31] = "task-completed-31"
        chat._thread_latest_task[32] = "task-completed-32"
        thread_31 = chat.get_latest_rag_trace(31, api_key="test-key")
        thread_32 = chat.get_latest_rag_trace(32, api_key="test-key")

        assert thread_31["documents"][0]["id"] == "doc-31"
        assert thread_32["documents"][0]["id"] == "doc-32"
        assert thread_31["documents"] != thread_32["documents"]
        assert thread_31["payload_summary"] == {"message_count": 3}
        assert thread_32["payload_summary"] == {"message_count": 4}
    finally:
        chat._thread_latest_task.clear()
        chat._thread_latest_task.update(original_latest_task)
        chat._rag_traces.clear()
        chat._rag_traces.update(original_rag_traces)


def test_golden_supported_retrieval_path(monkeypatch, tmp_path):
    with _supported_help_startup_client(monkeypatch, tmp_path) as (
        client,
        fake_guardian_db,
        ingest_calls,
    ):
        response = client.get(
            "/api/media/documents",
            headers={"X-API-Key": "test-api-key"},
            params={"tag": "builtin_help"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        document = payload["documents"][0]
        assert document["id"] == help_ingest.BUILTIN_HELP_DOCUMENT_ID
        assert document["source_tag"] == help_ingest.BUILTIN_HELP_SOURCE_TAG
        assert document["project_id"] == fake_guardian_db.project_id
        assert document["src_url"].endswith(
            help_ingest.BUILTIN_HELP_REL_PATH.as_posix()
        )
        assert ingest_calls["count"] == 1

        retrieve_app = FastAPI()
        import guardian.retrieve.api as retrieve_api

        retrieve_api = importlib.reload(retrieve_api)
        monkeypatch.setattr(
            "guardian.core.config.assert_config_coherence",
            lambda _settings: None,
        )
        retrieve_app.include_router(retrieve_api.router)

        with TestClient(retrieve_app) as retrieve_client:
            retrieval_response = retrieve_client.post(
                "/api/retrieve",
                json={
                    "q": "codexify-builtin-help-sentinel amber lantern 4k2",
                    "k": 1,
                },
            )
        assert retrieval_response.status_code == 200
        matches = retrieval_response.json()["matches"]
        assert matches
        assert (
            "codexify-builtin-help-sentinel amber lantern 4k2"
            in matches[0]["text"]
        )
        assert matches[0]["meta"]["source_tag"] == "builtin_help"
        # This proves the supported startup seed is retrievable through the backend route seam.
