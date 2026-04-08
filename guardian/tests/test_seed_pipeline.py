from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Literal

from guardian.runtime.ingest.seed_pipeline import seed_global_system_docs


class _FakeVectorStore:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add_texts(self, items: list[dict[str, Any]]) -> int:
        self.items.extend(items)
        return len(items)


class _FakeScalarResult:
    def __init__(self, docs: list[Any]) -> None:
        self._docs = docs

    def all(self) -> list[Any]:
        return list(self._docs)


class _FakeSession:
    def __init__(self, docs: list[Any]) -> None:
        self._docs = docs

    def scalars(self, _stmt: Any) -> _FakeScalarResult:
        return _FakeScalarResult(self._docs)

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


class _FakeSessionFactory:
    def __init__(self, docs: list[Any]) -> None:
        self._docs = docs

    def __call__(self) -> _FakeSession:
        return _FakeSession(self._docs)


def test_seed_global_system_docs_indexes_global_docs() -> None:
    docs = [
        SimpleNamespace(
            id=1,
            scope="global",
            is_enabled=True,
            slug="builtin-help",
            title="Built-in Help",
            content="Use /help to inspect supported commands.",
            owner_user_id=None,
            project_id=None,
        )
    ]
    fake_store = _FakeVectorStore()

    summary = seed_global_system_docs(
        fake_store, session_factory=_FakeSessionFactory(docs)
    )

    assert summary["seeded"] == 1
    assert summary["candidate_count"] == 1
    assert fake_store.items == [
        {
            "id": "system-doc:1",
            "text": "Use /help to inspect supported commands.",
            "meta": {
                "namespace": "system_docs:global",
                "source": "system_doc",
                "scope": "global",
                "doc_id": 1,
                "slug": "builtin-help",
                "title": "Built-in Help",
                "owner_user_id": None,
                "project_id": None,
                "is_enabled": True,
            },
        }
    ]
