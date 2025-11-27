from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from backend.vector_store.chroma_store import ChromaVectorStore
from backend.vector_store.factory import get_vector_store


def test_factory_returns_chroma_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_STORE", "chroma")
    store = get_vector_store()
    assert isinstance(store, ChromaVectorStore)


def test_factory_returns_pgvector_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("pgvector.sqlalchemy")
    from backend.vector_store.pgvector_store import PGVectorStore

    monkeypatch.setenv("VECTOR_STORE", "pgvector")
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    store = get_vector_store(engine=engine, eager_init=False)
    assert isinstance(store, PGVectorStore)


def test_factory_rejects_unknown_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VECTOR_STORE", "unknown")
    with pytest.raises(ValueError):
        get_vector_store()
