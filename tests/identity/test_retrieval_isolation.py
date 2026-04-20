from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.context.broker import ContextBroker


class _FakeQuery:
    def __init__(self, rows) -> None:
        self._rows = list(rows)
        self._criteria: dict[str, object] = {}

    def filter(self, *_args, **_kwargs):
        for criterion in _args:
            column = getattr(getattr(criterion, "left", None), "name", None)
            value = getattr(getattr(criterion, "right", None), "value", None)
            if column and value is not None:
                self._criteria[column] = value
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        target_id = self._criteria.get("id")
        if target_id is not None:
            for row in self._rows:
                row_id = getattr(row, "id", None)
                if str(row_id) == str(target_id):
                    return row
            return None
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows_by_model: dict[str, list[object]]) -> None:
        self._rows_by_model = rows_by_model

    def query(self, model):
        return _FakeQuery(self._rows_by_model.get(model.__name__, []))

    def close(self):
        return None


def _hit(*, user_id: str, text: str, thread_id: int, project_id: int):
    return {
        "text": text,
        "metadata": {
            "user_id": user_id,
            "thread_id": thread_id,
            "project_id": project_id,
        },
        "score": 0.99,
    }


def _doc_row(**kwargs):
    return SimpleNamespace(**kwargs)


def _make_broker(
    *,
    thread_user_id: str,
    document_user_id: str,
):
    rows_by_model = {
        "GeneratedDocument": [
            _doc_row(
                id="gen-project-doc",
                project_id=1,
                thread_id=1,
                user_id=document_user_id,
                title="Project evidence",
                content="project-scoped evidence",
                format="md",
                model="test-model",
                deleted_at=None,
            )
        ],
        "UploadedDocument": [
            _doc_row(
                id="up-thread-doc",
                project_id=1,
                thread_id=1,
                user_id=document_user_id,
                filename="thread-evidence.txt",
                filesize=1,
                mime_type="text/plain",
                src_url="/tmp/thread-evidence.txt",
                source_tag="uploaded",
                parsed_text="thread-scoped evidence",
                deleted_at=None,
            )
        ],
        "ProjectDocumentLink": [
            _doc_row(
                project_id=1,
                document_id="gen-project-doc",
                document_type="generated",
                is_enabled=True,
                attached_at=None,
                attached_by=document_user_id,
            )
        ],
        "ThreadDocument": [
            _doc_row(
                thread_id=1,
                document_id="up-thread-doc",
                relation="attached",
                created_at=None,
            )
        ],
    }

    chatlog_db = SimpleNamespace()
    chatlog_db.get_chat_thread = MagicMock(
        return_value={
            "id": 1,
            "user_id": thread_user_id,
            "project_id": 1,
        }
    )
    chatlog_db.last_messages = MagicMock(
        return_value=[
            {
                "id": 101,
                "role": "user",
                "content": "Where is the evidence?",
                "user_id": thread_user_id,
            }
        ]
    )
    chatlog_db.list_messages = MagicMock(
        return_value=[
            {
                "id": 101,
                "role": "user",
                "content": "Where is the evidence?",
                "user_id": thread_user_id,
            }
        ]
    )
    chatlog_db.list_chat_threads = MagicMock(return_value=[])
    chatlog_db.get_connector_config = MagicMock(return_value=None)
    chatlog_db.get_session = MagicMock(
        side_effect=lambda: _FakeSession(rows_by_model)
    )

    vector_store = MagicMock()
    vector_store.search = MagicMock(
        return_value=[
            _hit(
                user_id="user-a",
                text="foreign semantic hit",
                thread_id=1,
                project_id=1,
            ),
            _hit(
                user_id="user-b",
                text="local semantic hit",
                thread_id=1,
                project_id=1,
            ),
        ]
    )

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )

    return broker, chatlog_db, vector_store


@pytest.mark.asyncio
async def test_retrieval_isolation_blocks_cross_user_data():
    broker, chatlog_db, vector_store = _make_broker(
        thread_user_id="user-b",
        document_user_id="user-a",
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="deep",
        user_id="user-b",
        project_id=1,
        source_mode="project",
        k_semantic=1,
        k_memory=1,
        k_project_docs=4,
        k_thread_docs=4,
    )

    assert context["docs"]["project"] == []
    assert context["docs"]["thread"] == []
    assert all(
        item["metadata"]["user_id"] == "user-b"
        for item in context.get("semantic", [])
    )
    assert all(
        item["metadata"]["user_id"] == "user-b"
        for item in context.get("memory", [])
    )
    assert chatlog_db.last_messages.call_args.kwargs["user_id"] == "user-b"
    assert all(
        call.kwargs.get("user_id") == "user-b"
        for call in vector_store.search.call_args_list
    )
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_retrieval_isolation_same_user_retrieval_works():
    broker, chatlog_db, vector_store = _make_broker(
        thread_user_id="user-a",
        document_user_id="user-a",
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="deep",
        user_id="user-a",
        project_id=1,
        source_mode="project",
        k_semantic=1,
        k_memory=1,
        k_project_docs=4,
        k_thread_docs=4,
    )

    assert any(
        doc["title"] == "Project evidence" for doc in context["docs"]["project"]
    )
    assert any(
        doc["title"] == "thread-evidence.txt"
        for doc in context["docs"]["thread"]
    )
    assert all(
        item["metadata"]["user_id"] == "user-a"
        for item in context.get("semantic", [])
    )
    assert all(
        item["metadata"]["user_id"] == "user-a"
        for item in context.get("memory", [])
    )
    assert chatlog_db.last_messages.call_args.kwargs["user_id"] == "user-a"
    assert all(
        call.kwargs.get("user_id") == "user-a"
        for call in vector_store.search.call_args_list
    )
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_retrieval_isolation_missing_user_id_fails():
    broker, _chatlog_db, _vector_store = _make_broker(
        thread_user_id="user-a",
        document_user_id="user-a",
    )

    with pytest.raises(ValueError, match="ContextBroker requires user_id"):
        await broker.assemble(
            thread_id=1,
            query="identity boundary",
            depth_mode="normal",
            user_id="",
            project_id=1,
            source_mode="project",
        )
