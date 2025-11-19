"""MemoryOS semantic retriever for RAG context assembly."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MemoryOSRetriever:
    """Semantic retriever that uses vector search for memory recall.

    This retriever integrates with the VectorStore to provide semantic
    search capabilities for the MemoryOS system, enabling RAG-based
    context assembly.
    """

    def __init__(self, vector_store: Any) -> None:
        """Initialize the retriever with a vector store backend.

        Args:
            vector_store: A VectorStore instance with a search(query, k) method.
        """
        self.vector_store = vector_store
        logger.info(f"[MemoryOSRetriever] Initialized with vector_store: {type(vector_store).__name__}")

    async def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve semantically similar documents for a given query.

        This method:
        1. Generates query embedding (handled internally by VectorStore)
        2. Performs vector similarity search
        3. Returns results sorted by similarity score (descending)

        Args:
            query: The search query string
            limit: Maximum number of results to return (default: 5)

        Returns:
            List of result dictionaries with schema:
            [
                {
                    "text": str,        # Document text content
                    "metadata": dict,   # Associated metadata
                    "score": float      # Similarity score
                },
                ...
            ]

            Returns empty list if vector store is empty or on error.
        """
        if not query or not query.strip():
            logger.debug("[MemoryOSRetriever] Empty query, returning empty results")
            return []

        start_time = time.time()

        try:
            # Call vector store search (handles embedding generation internally)
            # VectorStore.search() returns [{text, meta, score}]
            results = self.vector_store.search(query, k=limit)

            # Handle both sync and async vector stores
            if hasattr(results, '__await__'):
                results = await results

            # Ensure results is a list
            if not isinstance(results, list):
                logger.warning(f"[MemoryOSRetriever] Vector store returned non-list: {type(results)}")
                return []

            # Normalize schema: VectorStore returns {text, meta, score}
            # We want {text, metadata, score}
            standardized = []
            for item in results:
                standardized.append({
                    "text": item.get("text", ""),
                    "metadata": item.get("meta", {}),
                    "score": item.get("score", 0.0)
                })

            # Results are already sorted by score (descending) from VectorStore
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"[MemoryOSRetriever] Retrieved {len(standardized)} results "
                f"for query '{query[:50]}...' in {elapsed_ms:.2f}ms"
            )

            return standardized

        except Exception as e:
            logger.warning(f"[MemoryOSRetriever] Search failed: {e}", exc_info=True)
            return []

    def retrieve_context(self, user_query: str, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Legacy method for backward compatibility.

        This method maintains compatibility with the old Retriever interface
        while delegating to the new async retrieve() method.

        Args:
            user_query: The user's query string
            user_id: The user identifier (currently unused)

        Returns:
            Dict with keys:
            - "retrieved_pages": Empty list (not implemented)
            - "retrieved_user_knowledge": Results from semantic search
            - "retrieved_assistant_knowledge": Empty list (not implemented)
        """
        import asyncio

        try:
            # Run async retrieve in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                logger.warning("[MemoryOSRetriever] retrieve_context called from async context")
                return {
                    "retrieved_pages": [],
                    "retrieved_user_knowledge": [],
                    "retrieved_assistant_knowledge": [],
                }
            else:
                results = loop.run_until_complete(self.retrieve(user_query, limit=5))
        except RuntimeError:
            # No event loop, create new one
            results = asyncio.run(self.retrieve(user_query, limit=5))

        return {
            "retrieved_pages": [],
            "retrieved_user_knowledge": results,
            "retrieved_assistant_knowledge": [],
        }


# Legacy class for backward compatibility
class Retriever:
    """Deprecated stub class. Use MemoryOSRetriever instead."""

    def retrieve_context(self, user_query: str, user_id: str) -> Dict[str, List]:
        """Legacy stub that returns empty results."""
        logger.warning(
            "[Retriever] Using deprecated Retriever class. "
            "Please migrate to MemoryOSRetriever."
        )
        return {
            "retrieved_pages": [],
            "retrieved_user_knowledge": [],
            "retrieved_assistant_knowledge": [],
        }
