"""Unit tests for MemoryOSRetriever."""

from __future__ import annotations

import pytest
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock

from guardian.memoryos.retriever import MemoryOSRetriever


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, results: List[Dict[str, Any]] | None = None):
        """Initialize mock with predefined results."""
        self.results = results or []
        self.search_calls: List[tuple] = []

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Mock search that returns predefined results."""
        self.search_calls.append((query, k))
        return self.results[:k]


class AsyncMockVectorStore:
    """Async mock vector store for testing async compatibility."""

    def __init__(self, results: List[Dict[str, Any]] | None = None):
        """Initialize mock with predefined results."""
        self.results = results or []
        self.search_calls: List[tuple] = []

    async def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Mock async search that returns predefined results."""
        self.search_calls.append((query, k))
        return self.results[:k]


@pytest.fixture
def sample_results():
    """Sample vector search results."""
    return [
        {
            "text": "Python is a high-level programming language",
            "meta": {"source": "wiki", "page": 1},
            "score": 0.95
        },
        {
            "text": "JavaScript is used for web development",
            "meta": {"source": "docs", "page": 2},
            "score": 0.87
        },
        {
            "text": "Rust is a systems programming language",
            "meta": {"source": "wiki", "page": 3},
            "score": 0.76
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
    assert vector_store.search_calls[0] == ("programming languages", 3)

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
    assert vector_store.search_calls[0][1] == 2  # k=2 passed to search


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
    assert vector_store.search_calls[0][1] == 5


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
