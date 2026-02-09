"""MemoryOS semantic retriever for RAG context assembly."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryOSRetriever:
    """Semantic retriever that uses vector search for memory recall.

    This retriever integrates with the VectorStore to provide semantic
    search capabilities for the MemoryOS system, enabling RAG-based
    context assembly.
    """

    def __init__(
        self,
        vector_store: Any,
        chatlog_db: Any | None = None,
        *,
        neighbor_turn_window: int = 4,
        neighbor_time_window_minutes: int = 15,
    ) -> None:
        """Initialize the retriever with a vector store backend.

        Args:
            vector_store: A VectorStore instance with a search(query, k) method.
            chatlog_db: Optional chat database adapter used for neighbor stitching.
        """
        self.vector_store = vector_store
        self.chatlog_db = chatlog_db
        self.neighbor_turn_window = max(1, int(neighbor_turn_window))
        self.neighbor_time_window_minutes = max(
            1, int(neighbor_time_window_minutes)
        )
        logger.info(
            f"[MemoryOSRetriever] Initialized with vector_store: {type(vector_store).__name__}"
        )

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    @staticmethod
    def _extract_metadata(item: dict[str, Any]) -> dict[str, Any]:
        if isinstance(item.get("meta"), dict):
            return dict(item["meta"])
        if isinstance(item.get("metadata"), dict):
            return dict(item["metadata"])
        return {}

    @staticmethod
    def _resolve_source_thread_id(meta: dict[str, Any]) -> str | None:
        source_thread_id = meta.get("source_thread_id")
        if source_thread_id:
            return str(source_thread_id)
        thread_id = meta.get("thread_id")
        if thread_id is None:
            return None
        return str(thread_id)

    @classmethod
    def _resolve_source_created_at(cls, meta: dict[str, Any]) -> str | None:
        value = meta.get("source_created_at")
        if not value:
            value = meta.get("timestamp")
        if value is None:
            return None
        return str(value)

    @classmethod
    def _resolve_turn_index(cls, meta: dict[str, Any]) -> int | None:
        return cls._coerce_int(meta.get("turn_index"))

    @classmethod
    def _resolve_source_message_id(cls, meta: dict[str, Any]) -> str | None:
        value = meta.get("source_message_id")
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _resolve_message_id(cls, meta: dict[str, Any]) -> int | None:
        return cls._coerce_int(meta.get("message_id"))

    def _normalize_result(
        self, item: dict[str, Any], semantic_rank: int
    ) -> dict[str, Any]:
        metadata = self._extract_metadata(item)
        return {
            "text": str(item.get("text", "")),
            "metadata": metadata,
            "score": float(item.get("score", 0.0)),
            "_semantic_rank": semantic_rank,
        }

    @classmethod
    def _dedupe_key(cls, item: dict[str, Any]) -> str | None:
        meta = item.get("metadata", {})
        source_message_id = cls._resolve_source_message_id(meta)
        if source_message_id:
            return f"source:{source_message_id}"
        message_id = cls._resolve_message_id(meta)
        if message_id is not None:
            return f"id:{message_id}"
        # No stable identifier available: do not collapse via dedupe.
        return None

    @classmethod
    def _chronological_sort_key(
        cls, item: dict[str, Any]
    ) -> tuple[int, datetime, int, int, str, int]:
        meta = item.get("metadata", {})
        source_dt = cls._parse_timestamp(cls._resolve_source_created_at(meta))
        turn_index = cls._resolve_turn_index(meta)
        source_message_id = cls._resolve_source_message_id(meta)
        message_id = cls._resolve_message_id(meta)
        semantic_rank = cls._coerce_int(item.get("_semantic_rank")) or 0

        return (
            1 if source_dt is None else 0,
            source_dt or datetime.max.replace(tzinfo=timezone.utc),
            1 if turn_index is None else 0,
            turn_index if turn_index is not None else 2**31 - 1,
            source_message_id
            or (str(message_id) if message_id is not None else "~"),
            semantic_rank,
        )

    @staticmethod
    def _merge_metadata(
        primary: dict[str, Any], secondary: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(primary)
        for key, value in secondary.items():
            if key not in merged or merged.get(key) in (None, ""):
                merged[key] = value
        return merged

    def _current_chatlog(self) -> Any | None:
        if self.chatlog_db is not None:
            return self.chatlog_db
        try:
            from guardian.core import dependencies

            return dependencies.chatlog_db
        except Exception:
            return None

    def _query_neighbors(
        self,
        source_thread_id: str,
        turn_index: int | None,
        source_created_at: datetime | None,
    ) -> list[dict[str, Any]]:
        chatlog_db = self._current_chatlog()
        if not chatlog_db or not hasattr(chatlog_db, "_connect"):
            return []

        rows: list[dict[str, Any]] = []
        try:
            with chatlog_db._connect() as conn, conn.cursor() as cur:
                if turn_index is not None:
                    lower = max(0, turn_index - self.neighbor_turn_window)
                    upper = turn_index + self.neighbor_turn_window
                    cur.execute(
                        """
                        SELECT id, thread_id, role, content, created_at, event_at, extra_meta
                        FROM chat_messages
                        WHERE extra_meta->>'source_thread_id' = %s
                          AND extra_meta ? 'turn_index'
                          AND (extra_meta->>'turn_index') ~ '^[0-9]+$'
                          AND ((extra_meta->>'turn_index')::integer BETWEEN %s AND %s)
                        ORDER BY ((extra_meta->>'turn_index')::integer) ASC, id ASC
                        """,
                        (source_thread_id, lower, upper),
                    )
                    rows = [dict(row) for row in cur.fetchall()]
                elif source_created_at is not None:
                    lower = (
                        source_created_at
                        - timedelta(minutes=self.neighbor_time_window_minutes)
                    ).isoformat()
                    upper = (
                        source_created_at
                        + timedelta(minutes=self.neighbor_time_window_minutes)
                    ).isoformat()
                    cur.execute(
                        """
                        SELECT id, thread_id, role, content, created_at, event_at, extra_meta
                        FROM chat_messages
                        WHERE extra_meta->>'source_thread_id' = %s
                          AND extra_meta ? 'source_created_at'
                          AND (extra_meta->>'source_created_at') BETWEEN %s AND %s
                        ORDER BY (extra_meta->>'source_created_at') ASC, id ASC
                        """,
                        (source_thread_id, lower, upper),
                    )
                    rows = [dict(row) for row in cur.fetchall()]
        except Exception as exc:
            logger.debug(
                "[MemoryOSRetriever] Neighbor query unavailable: %s", exc
            )
            return []

        return rows

    def _row_to_result(self, row: dict[str, Any]) -> dict[str, Any]:
        meta = dict(row.get("extra_meta") or {})
        message_id = row.get("id")
        if message_id is not None:
            meta.setdefault("message_id", int(message_id))
        if row.get("thread_id") is not None:
            meta.setdefault("thread_id", int(row["thread_id"]))
        meta.setdefault("role", row.get("role"))

        if not meta.get("source_created_at"):
            event_at = row.get("event_at") or row.get("created_at")
            parsed = self._parse_timestamp(event_at)
            if parsed is not None:
                meta["source_created_at"] = parsed.isoformat()

        return {
            "text": str(row.get("content", "")),
            "metadata": meta,
            "score": 0.0,
        }

    def _fetch_neighbors_for_hit(
        self, hit: dict[str, Any]
    ) -> list[dict[str, Any]]:
        meta = hit.get("metadata", {})
        source_thread_id = self._resolve_source_thread_id(meta)
        if not source_thread_id:
            return []
        turn_index = self._resolve_turn_index(meta)
        source_created_at = self._parse_timestamp(
            self._resolve_source_created_at(meta)
        )
        rows = self._query_neighbors(
            source_thread_id=source_thread_id,
            turn_index=turn_index,
            source_created_at=source_created_at,
        )
        return [self._row_to_result(row) for row in rows]

    def _stitch_and_sort(
        self, semantic_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        stitched: list[dict[str, Any]] = []
        for hit in semantic_results:
            stitched.append(hit)
            hit_thread_id = self._resolve_source_thread_id(
                hit.get("metadata", {})
            )
            for neighbor in self._fetch_neighbors_for_hit(hit):
                neighbor_thread_id = self._resolve_source_thread_id(
                    neighbor.get("metadata", {})
                )
                # Strictly keep stitching within the same source thread.
                if (
                    hit_thread_id
                    and neighbor_thread_id
                    and neighbor_thread_id != hit_thread_id
                ):
                    continue
                stitched.append(neighbor)

        deduped: dict[str, dict[str, Any]] = {}
        for idx, item in enumerate(stitched):
            key = self._dedupe_key(item)
            if key is None:
                key = f"no-id:{idx}"
            if key not in deduped:
                deduped[key] = {
                    "text": str(item.get("text", "")),
                    "metadata": dict(item.get("metadata", {})),
                    "score": float(item.get("score", 0.0)),
                    "_semantic_rank": self._coerce_int(
                        item.get("_semantic_rank")
                    )
                    or 0,
                }
                continue

            existing = deduped[key]
            existing["metadata"] = self._merge_metadata(
                existing.get("metadata", {}),
                item.get("metadata", {}),
            )
            existing["score"] = max(
                float(existing.get("score", 0.0)),
                float(item.get("score", 0.0)),
            )
            existing["_semantic_rank"] = min(
                self._coerce_int(existing.get("_semantic_rank")) or 0,
                self._coerce_int(item.get("_semantic_rank")) or 0,
            )
            if not existing.get("text") and item.get("text"):
                existing["text"] = str(item["text"])

        ordered = sorted(deduped.values(), key=self._chronological_sort_key)
        for item in ordered:
            item.pop("_semantic_rank", None)
        return ordered

    async def retrieve(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
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
            logger.debug(
                "[MemoryOSRetriever] Empty query, returning empty results"
            )
            return []

        start_time = time.time()

        try:
            # Call vector store search (handles embedding generation internally)
            # VectorStore.search() returns [{text, meta, score}]
            results = self.vector_store.search(query, k=limit)

            # Handle both sync and async vector stores
            if hasattr(results, "__await__"):
                results = await results

            # Ensure results is a list
            if not isinstance(results, list):
                logger.warning(
                    f"[MemoryOSRetriever] Vector store returned non-list: {type(results)}"
                )
                return []

            # Normalize semantic hits first, then stitch neighbors and return
            # deterministic chronological ordering.
            standardized = [
                self._normalize_result(item, semantic_rank=idx)
                for idx, item in enumerate(results)
            ]
            ordered = self._stitch_and_sort(standardized)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"[MemoryOSRetriever] Retrieved {len(standardized)} results "
                f"for query '{query[:50]}...' in {elapsed_ms:.2f}ms"
            )

            return ordered

        except Exception as e:
            logger.warning(
                f"[MemoryOSRetriever] Search failed: {e}", exc_info=True
            )
            return []

    def retrieve_context(
        self, user_query: str, user_id: str
    ) -> dict[str, list[dict[str, Any]]]:
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
                logger.warning(
                    "[MemoryOSRetriever] retrieve_context called from async context"
                )
                return {
                    "retrieved_pages": [],
                    "retrieved_user_knowledge": [],
                    "retrieved_assistant_knowledge": [],
                }
            else:
                results = loop.run_until_complete(
                    self.retrieve(user_query, limit=5)
                )
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

    def retrieve_context(
        self, user_query: str, user_id: str
    ) -> dict[str, list]:
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
