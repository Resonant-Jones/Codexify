"""Unit tests for MemoryOSRetriever."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest

from guardian.memoryos.retriever import MemoryOSRetriever


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, results: list[dict[str, Any]] | None = None):
        """Initialize mock with predefined results."""
        self.results = results or []
        self.search_calls: list[tuple] = []

    def search(self, query: str, k: int) -> list[dict[str, Any]]:
        """Mock search that returns predefined results."""
        self.search_calls.append((query, k))
        return self.results[:k]


class AsyncMockVectorStore:
    """Async mock vector store for testing async compatibility."""

    def __init__(self, results: list[dict[str, Any]] | None = None):
        """Initialize mock with predefined results."""
        self.results = results or []
        self.search_calls: list[tuple] = []

    async def search(self, query: str, k: int) -> list[dict[str, Any]]:
        """Mock async search that returns predefined results."""
        self.search_calls.append((query, k))
        return self.results[:k]


def _candidate_k(limit: int) -> int:
    return max(limit * 3, limit + 5)


@pytest.fixture
def sample_results():
    """Sample vector search results."""
    return [
        {
            "text": "Python is a high-level programming language",
            "meta": {"source": "wiki", "page": 1},
            "score": 0.95,
        },
        {
            "text": "JavaScript is used for web development",
            "meta": {"source": "docs", "page": 2},
            "score": 0.87,
        },
        {
            "text": "Rust is a systems programming language",
            "meta": {"source": "wiki", "page": 3},
            "score": 0.76,
        },
    ]


@pytest.mark.asyncio
async def test_retrieve_basic(sample_results):
    """Test basic retrieval functionality."""
    vector_store = MockVectorStore(sample_results)
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("programming languages", limit=3)

    # Verify search was called
    assert len(vector_store.search_calls) == 1
    assert vector_store.search_calls[0] == (
        "programming languages",
        _candidate_k(3),
    )

    # Verify results
    assert len(results) == 3
    assert results[0]["text"] == "Python is a high-level programming language"
    assert results[0]["metadata"] == {"source": "wiki", "page": 1}
    assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_retrieve_limit(sample_results):
    """Test that limit parameter is respected."""
    vector_store = MockVectorStore(sample_results)
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("test query", limit=2)

    assert len(results) == 2
    assert vector_store.search_calls[0][1] == _candidate_k(
        2
    )  # candidate_k passed to search


@pytest.mark.asyncio
async def test_retrieve_empty_query():
    """Test that empty queries return empty results."""
    vector_store = MockVectorStore([])
    retriever = MemoryOSRetriever(vector_store)

    # Test empty string
    results = await retriever.retrieve("", limit=5)
    assert results == []

    # Test whitespace only
    results = await retriever.retrieve("   ", limit=5)
    assert results == []

    # Verify vector store was not called
    assert len(vector_store.search_calls) == 0


@pytest.mark.asyncio
async def test_retrieve_empty_vector_store():
    """Test graceful handling of empty vector store."""
    vector_store = MockVectorStore([])
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("test query", limit=5)

    assert results == []
    assert len(vector_store.search_calls) == 1


@pytest.mark.asyncio
async def test_retrieve_schema_normalization(sample_results):
    """Test that results are normalized to expected schema."""
    vector_store = MockVectorStore(sample_results)
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("test", limit=1)

    # Verify schema transformation: meta -> metadata
    result = results[0]
    assert "text" in result
    assert "metadata" in result  # Normalized from "meta"
    assert "score" in result
    assert "meta" not in result  # Old key should be gone


@pytest.mark.asyncio
async def test_retrieve_async_vector_store(sample_results):
    """Test compatibility with async vector stores."""
    async_store = AsyncMockVectorStore(sample_results)
    retriever = MemoryOSRetriever(async_store)

    results = await retriever.retrieve("async test", limit=2)

    assert len(results) == 2
    assert len(async_store.search_calls) == 1


@pytest.mark.asyncio
async def test_retrieve_handles_exceptions():
    """Test that exceptions are caught and empty list is returned."""
    error_store = Mock()
    error_store.search = Mock(side_effect=Exception("Vector store error"))

    retriever = MemoryOSRetriever(error_store)
    results = await retriever.retrieve("test query", limit=5)

    # Should return empty list on error
    assert results == []


@pytest.mark.asyncio
async def test_retrieve_handles_malformed_results():
    """Test handling of malformed vector store results."""
    # Vector store returns non-list
    bad_store = Mock()
    bad_store.search = Mock(return_value="not a list")

    retriever = MemoryOSRetriever(bad_store)
    results = await retriever.retrieve("test", limit=5)

    assert results == []


@pytest.mark.asyncio
async def test_retrieve_handles_missing_fields(sample_results):
    """Test handling of results with missing fields."""
    incomplete_results = [
        {"text": "Only text field"},  # Missing meta and score
        {"score": 0.5},  # Missing text and meta
        {},  # All fields missing
    ]

    vector_store = MockVectorStore(incomplete_results)
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("test", limit=3)

    # Should handle gracefully with defaults
    assert len(results) == 3
    assert results[0]["text"] == "Only text field"
    assert results[0]["metadata"] == {}
    assert results[0]["score"] == 0.0

    assert results[1]["text"] == ""
    assert results[1]["score"] == 0.5


def test_retrieve_context_legacy_method(sample_results):
    """Test legacy retrieve_context method for backward compatibility."""
    vector_store = MockVectorStore(sample_results)
    retriever = MemoryOSRetriever(vector_store)

    result = retriever.retrieve_context("test query", user_id="user123")

    # Verify structure
    assert "retrieved_pages" in result
    assert "retrieved_user_knowledge" in result
    assert "retrieved_assistant_knowledge" in result

    # Verify knowledge was populated
    assert len(result["retrieved_user_knowledge"]) > 0
    assert result["retrieved_pages"] == []
    assert result["retrieved_assistant_knowledge"] == []


@pytest.mark.asyncio
async def test_retrieve_default_limit(sample_results):
    """Test that default limit of 5 is used."""
    vector_store = MockVectorStore(sample_results * 3)  # 9 results
    retriever = MemoryOSRetriever(vector_store)

    # Call without limit parameter
    results = await retriever.retrieve("test query")

    # Should use default limit=5
    assert vector_store.search_calls[0][1] == _candidate_k(5)


@pytest.mark.asyncio
async def test_retrieve_preserves_score_order(sample_results):
    """Test that results maintain descending score order."""
    # Reverse the sample results to ensure they're not already sorted
    shuffled = [sample_results[2], sample_results[0], sample_results[1]]
    vector_store = MockVectorStore(shuffled)
    retriever = MemoryOSRetriever(vector_store)

    results = await retriever.retrieve("test", limit=3)

    # VectorStore should already sort, so order should be preserved
    # (This tests that we don't accidentally re-sort or mess up ordering)
    assert results[0]["score"] == 0.76  # First in shuffled list
    assert results[1]["score"] == 0.95
    assert results[2]["score"] == 0.87


@pytest.mark.asyncio
async def test_retrieve_stitches_neighbors_deduplicates_and_sorts():
    """Semantic hits should stitch neighbor windows into ordered context."""
    semantic_hits = [
        {
            "text": "turn 2",
            "meta": {
                "source_thread_id": "thread-a",
                "source_message_id": "m2",
                "source_created_at": "2026-02-08T12:02:00+00:00",
                "turn_index": 2,
                "message_id": 102,
            },
            "score": 0.92,
        },
        {
            "text": "turn 3",
            "meta": {
                "source_thread_id": "thread-a",
                "source_message_id": "m3",
                "source_created_at": "2026-02-08T12:03:00+00:00",
                "turn_index": 3,
                "message_id": 103,
            },
            "score": 0.88,
        },
    ]

    vector_store = MockVectorStore(semantic_hits)
    retriever = MemoryOSRetriever(vector_store)

    def fake_neighbors(hit: dict[str, Any]) -> list[dict[str, Any]]:
        hit_id = hit["metadata"]["source_message_id"]
        if hit_id == "m2":
            return [
                {
                    "text": "turn 1",
                    "metadata": {
                        "source_thread_id": "thread-a",
                        "source_message_id": "m1",
                        "source_created_at": "2026-02-08T12:01:00+00:00",
                        "turn_index": 1,
                        "message_id": 101,
                    },
                    "score": 0.0,
                },
                {
                    "text": "turn 2 duplicate",
                    "metadata": {
                        "source_thread_id": "thread-a",
                        "source_message_id": "m2",
                        "source_created_at": "2026-02-08T12:02:00+00:00",
                        "turn_index": 2,
                        "message_id": 102,
                    },
                    "score": 0.0,
                },
                {
                    "text": "turn 3 duplicate",
                    "metadata": {
                        "source_thread_id": "thread-a",
                        "source_message_id": "m3",
                        "source_created_at": "2026-02-08T12:03:00+00:00",
                        "turn_index": 3,
                        "message_id": 103,
                    },
                    "score": 0.0,
                },
            ]
        if hit_id == "m3":
            return [
                {
                    "text": "turn 4",
                    "metadata": {
                        "source_thread_id": "thread-a",
                        "source_message_id": "m4",
                        "source_created_at": "2026-02-08T12:04:00+00:00",
                        "turn_index": 4,
                        "message_id": 104,
                    },
                    "score": 0.0,
                },
                {
                    "text": "wrong thread",
                    "metadata": {
                        "source_thread_id": "thread-b",
                        "source_message_id": "z1",
                        "source_created_at": "2026-02-08T11:59:00+00:00",
                        "turn_index": 1,
                        "message_id": 201,
                    },
                    "score": 0.0,
                },
            ]
        return []

    retriever._fetch_neighbors_for_hit = fake_neighbors  # type: ignore[method-assign]

    results = await retriever.retrieve("chronological context", limit=2)

    ids = [r["metadata"]["source_message_id"] for r in results]
    assert ids == ["m1", "m2", "m3", "m4"]

    # Duplicate hits keep the highest semantic score.
    by_id = {r["metadata"]["source_message_id"]: r for r in results}
    assert by_id["m2"]["score"] == pytest.approx(0.92)
    assert by_id["m3"]["score"] == pytest.approx(0.88)

    # Monotonic by (timestamp, turn_index, id)
    ordering = [
        (
            r["metadata"]["source_created_at"],
            r["metadata"]["turn_index"],
            r["metadata"]["source_message_id"],
        )
        for r in results
    ]
    assert ordering == sorted(ordering)


@pytest.mark.asyncio
async def test_retrieve_sorts_with_missing_turn_index_by_timestamp():
    """When turn_index is missing, ordering falls back to timestamp."""
    semantic_hits = [
        {
            "text": "late",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "m2",
                "source_created_at": "2026-02-08T12:05:00+00:00",
            },
            "score": 0.91,
        },
        {
            "text": "early",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "m1",
                "source_created_at": "2026-02-08T12:01:00+00:00",
            },
            "score": 0.87,
        },
    ]
    vector_store = MockVectorStore(semantic_hits)
    retriever = MemoryOSRetriever(vector_store)
    retriever._fetch_neighbors_for_hit = lambda hit: []  # type: ignore[method-assign]

    results = await retriever.retrieve("sort fallback", limit=2)
    ids = [r["metadata"]["source_message_id"] for r in results]
    assert ids == ["m1", "m2"]


@pytest.mark.asyncio
async def test_retrieve_prefers_live_over_archival_by_default():
    """Default retrieval should deprioritize archival import memories."""
    semantic_hits = [
        {
            "text": "archival memory",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "a1",
                "source_created_at": "2026-01-01T10:00:00+00:00",
                "origin": "chatgpt_import",
                "era": "pre_codexify",
            },
            "score": 0.99,
        },
        {
            "text": "live memory one",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "l1",
                "source_created_at": "2026-02-08T12:00:00+00:00",
                "origin": "live",
            },
            "score": 0.92,
        },
        {
            "text": "live memory two",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "l2",
                "source_created_at": "2026-02-08T12:01:00+00:00",
                "origin": "live",
            },
            "score": 0.90,
        },
    ]
    vector_store = MockVectorStore(semantic_hits)
    retriever = MemoryOSRetriever(vector_store)
    retriever._fetch_neighbors_for_hit = lambda hit: []  # type: ignore[method-assign]

    results = await retriever.retrieve("what is the current status", limit=2)

    ids = {r["metadata"]["source_message_id"] for r in results}
    assert ids == {"l1", "l2"}
    for result in results:
        assert "is_archival" not in result["metadata"]


@pytest.mark.asyncio
async def test_retrieve_allows_archival_for_history_queries():
    """History-style queries should allow archival memories back into results."""
    semantic_hits = [
        {
            "text": "archival memory",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "a1",
                "source_created_at": "2026-01-01T10:00:00+00:00",
                "origin": "chatgpt_import",
                "era": "pre_codexify",
            },
            "score": 0.99,
        },
        {
            "text": "live memory",
            "meta": {
                "source_thread_id": "thread-x",
                "source_message_id": "l1",
                "source_created_at": "2026-02-08T12:00:00+00:00",
                "origin": "live",
            },
            "score": 0.92,
        },
    ]
    vector_store = MockVectorStore(semantic_hits)
    retriever = MemoryOSRetriever(vector_store)
    retriever._fetch_neighbors_for_hit = lambda hit: []  # type: ignore[method-assign]

    results = await retriever.retrieve(
        "from import history what happened before codexify", limit=2
    )

    by_id = {r["metadata"]["source_message_id"]: r for r in results}
    assert "a1" in by_id
    assert by_id["a1"]["metadata"]["is_archival"] is True
    assert by_id["a1"]["metadata"]["origin"] == "chatgpt_import"
