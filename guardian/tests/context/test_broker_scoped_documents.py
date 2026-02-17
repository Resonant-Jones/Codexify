from __future__ import annotations

from typing import Any

import pytest

from guardian.context.broker import ContextBroker
from guardian.core.config import Settings


class DummyChatlog:
    def __init__(self, project_id: int | None = None) -> None:
        self.project_id = project_id

    def last_messages(
        self, *_args: Any, **_kwargs: Any
    ) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "hello"}]

    def get_chat_thread(self, thread_id: int) -> dict[str, Any]:
        return {"id": thread_id, "project_id": self.project_id}


class DummyVector:
    def search(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return []


class StubScopedDocsBroker(ContextBroker):
    def __init__(
        self,
        *args: Any,
        docs_payload: dict[str, list[dict[str, Any]]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.docs_payload = docs_payload
        self.doc_calls: list[dict[str, Any]] = []

    def _fetch_scoped_documents(
        self,
        *,
        thread_id: int,
        project_id: int | None,
        k_project_docs: int,
        k_thread_docs: int,
        doc_excerpt_chars: int,
    ) -> dict[str, list[dict[str, Any]]]:
        self.doc_calls.append(
            {
                "thread_id": thread_id,
                "project_id": project_id,
                "k_project_docs": k_project_docs,
                "k_thread_docs": k_thread_docs,
                "doc_excerpt_chars": doc_excerpt_chars,
            }
        )
        return self.docs_payload


@pytest.mark.asyncio
async def test_project_docs_returned_when_project_scope_is_provided() -> None:
    docs_payload = {
        "project": [
            {
                "id": "proj-1",
                "title": "Project Plan",
                "excerpt": "project excerpt",
                "scope": "project",
                "document_type": "uploaded",
                "provenance": {"relation": "project_library"},
            }
        ],
        "thread": [],
        "global": [],
    }
    broker = StubScopedDocsBroker(
        DummyChatlog(project_id=111),
        DummyVector(),
        settings=Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
        docs_payload=docs_payload,
    )

    bundle, _trace = await broker.assemble(
        thread_id=7,
        query="hello",
        depth_mode="normal",
        project_id=222,
    )

    assert bundle["docs"]["project"][0]["id"] == "proj-1"
    assert broker.doc_calls[0]["project_id"] == 222


@pytest.mark.asyncio
async def test_thread_docs_returned_when_thread_scope_is_provided() -> None:
    docs_payload = {
        "project": [],
        "thread": [
            {
                "id": "thr-1",
                "title": "Thread Notes",
                "excerpt": "thread excerpt",
                "scope": "thread",
                "document_type": "generated",
                "provenance": {"relation": "attached"},
            }
        ],
        "global": [],
    }
    broker = StubScopedDocsBroker(
        DummyChatlog(project_id=None),
        DummyVector(),
        settings=Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
        docs_payload=docs_payload,
    )

    bundle, _trace = await broker.assemble(
        thread_id=91,
        query="hello",
        depth_mode="normal",
    )

    assert bundle["docs"]["thread"][0]["id"] == "thr-1"
    assert broker.doc_calls[0]["thread_id"] == 91


@pytest.mark.asyncio
async def test_project_docs_are_included_even_when_thread_docs_exist() -> None:
    docs_payload = {
        "project": [
            {
                "id": "proj-priority",
                "title": "Project Contract",
                "excerpt": "project-first",
                "scope": "project",
                "document_type": "uploaded",
                "provenance": {"relation": "project_library"},
            }
        ],
        "thread": [
            {
                "id": "thread-secondary",
                "title": "Thread Scratch",
                "excerpt": "thread-second",
                "scope": "thread",
                "document_type": "generated",
                "provenance": {"relation": "reference"},
            }
        ],
        "global": [],
    }
    broker = StubScopedDocsBroker(
        DummyChatlog(project_id=77),
        DummyVector(),
        settings=Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
        docs_payload=docs_payload,
    )

    bundle, _trace = await broker.assemble(
        thread_id=15,
        query="hello",
        depth_mode="normal",
    )

    scopes_with_docs = [
        scope for scope in ("project", "thread") if bundle["docs"].get(scope)
    ]
    assert scopes_with_docs == ["project", "thread"]
    assert bundle["docs"]["project"][0]["id"] == "proj-priority"


@pytest.mark.asyncio
async def test_scoped_docs_preserve_provenance_fields() -> None:
    docs_payload = {
        "project": [
            {
                "id": "proj-with-prov",
                "title": "Architecture Notes",
                "excerpt": "bounded text",
                "scope": "project",
                "document_type": "uploaded",
                "source": "uploaded",
                "project_id": 99,
                "thread_id": None,
                "provenance": {
                    "relation": "project_library",
                    "attached_at": "2026-02-17T12:00:00+00:00",
                    "attached_by": "user-1",
                },
            }
        ],
        "thread": [],
        "global": [],
    }
    broker = StubScopedDocsBroker(
        DummyChatlog(project_id=99),
        DummyVector(),
        settings=Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
        docs_payload=docs_payload,
    )

    bundle, _trace = await broker.assemble(
        thread_id=33,
        query="hello",
        depth_mode="normal",
    )

    doc = bundle["docs"]["project"][0]
    assert doc["provenance"]["relation"] == "project_library"
    assert doc["provenance"]["attached_at"] == "2026-02-17T12:00:00+00:00"
    assert doc["provenance"]["attached_by"] == "user-1"
