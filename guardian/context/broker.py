"""Minimal, dependency-light context assembly broker for enriching chat completions."""

import logging
from typing import Any, Dict, List, Optional

from guardian.core.config import Settings, get_settings
from guardian.memoryos.retriever import MemoryOSRetriever

logger = logging.getLogger(__name__)


class ContextBroker:
    """Assembles context bundles for chat completions at different depth levels.

    Supports four depth modes:
    - "shallow": Only recent messages from the thread
    - "normal": Messages + semantic search results
    - "deep": Messages + semantic + memory search results
    - "diagnostic": Messages + semantic + memory + sensor snapshots
    """

    def __init__(
        self,
        chatlog_db: Any,
        vector_store: Any,
        memory_store: Optional[Any] = None,
        sensors: Optional[Any] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize ContextBroker with required and optional stores.

        Args:
            chatlog_db: Database providing chatlog access (required)
            vector_store: Vector store for semantic search (required)
            memory_store: Optional memory search backend
            sensors: Optional system sensors provider
        """
        self.chatlog = chatlog_db
        self.vector = vector_store
        self.memory = memory_store
        self.sensors = sensors
        self.settings = settings or get_settings()
        # Initialize MemoryOS semantic retriever for RAG-based memory search when available
        self.memory_retriever = None
        try:
            if vector_store is not None:
                self.memory_retriever = MemoryOSRetriever(vector_store)
        except Exception as exc:
            logger.debug("[ContextBroker] Memory retriever init failed: %s", exc)
        logger.info("[ContextBroker] Initialized with MemoryOS semantic retriever")

    async def assemble(
        self,
        thread_id: int,
        query: str,
        *,
        depth: str = "normal",
        n_messages: int = 6,
        k_semantic: int = 4,
        k_memory: int = 5,
        federated: bool = False,
        user_id: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Assemble a context bundle for the given thread and query.

        Args:
            thread_id: ID of the chat thread
            query: Query string for semantic search
            depth: Retrieval depth ("shallow", "normal", "deep", "diagnostic")
            n_messages: Number of recent messages to fetch
            k_semantic: Number of semantic results to fetch
            k_memory: Number of memory results to fetch
            federated: If True, include federated context from peer nodes

        Returns:
            Dict with keys depending on depth:
            - "messages": Recent thread messages (all depths)
            - "semantic": Semantic search results (all depths)
            - "memory": Memory search results (deep, diagnostic)
            - "sensors": System sensor snapshot (diagnostic only)
            - "federated": Federated search results (if federated=True)
        """
        # Normalize depth
        depth = str(depth or "normal").strip().lower()

        context: Dict[str, Any] = {}

        # Always include recent messages
        try:
            if hasattr(self.chatlog, 'last_messages'):
                messages = await self._fetch_messages(thread_id, n_messages)
            else:
                messages = []
            context["messages"] = messages
        except Exception as e:
            logger.warning(f"Failed to fetch messages for thread {thread_id}: {e}")
            context["messages"] = []

        # Always include semantic search (for all depths except "shallow")
        if depth != "shallow":
            try:
                semantic = await self._search_semantic(query, k_semantic)
                context["semantic"] = semantic
            except Exception as e:
                logger.warning(f"Failed to perform semantic search: {e}")
                context["semantic"] = []
        else:
            context["semantic"] = []

        # Optional graph-derived context (gated by explicit flag)
        context["graph"] = []
        if getattr(self.settings, "GUARDIAN_ENABLE_GRAPH_CONTEXT", False):
            try:
                graph_chunks = await self._get_graph_context(
                    user_id=user_id or "default", thread_id=str(thread_id)
                )
                context["graph"] = graph_chunks
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Graph context unavailable; continuing without it: %s",
                    e,
                )

        # Include memory search for deep and diagnostic modes
        if depth in ("deep", "diagnostic"):
            try:
                if self.memory:
                    memory = await self._search_memory(query, k_memory)
                    context["memory"] = memory
                else:
                    context["memory"] = []
            except Exception as e:
                logger.warning(f"Failed to fetch memory results: {e}")
                context["memory"] = []

        # Include sensor snapshot for diagnostic mode only
        if depth == "diagnostic":
            try:
                if self.sensors:
                    snapshot = await self._snapshot_sensors()
                    context["sensors"] = snapshot
                else:
                    context["sensors"] = {}
            except Exception as e:
                logger.warning(f"Failed to snapshot sensors: {e}")
                context["sensors"] = {}

        # Include federated context if requested
        if federated:
            try:
                federated_results = await self._search_federated(query, k_semantic)
                context["federated"] = federated_results
            except Exception as e:
                logger.warning(f"Failed to fetch federated context: {e}")
                context["federated"] = []

        # Build RAG Trace
        rag_trace = {
            "documents": [
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("metadata", {}).get("filename", "unknown")),
                    "score": float(item.get("score", 0.0)),
                    "snippet": str(item.get("text", ""))[:100] + "..."
                }
                for item in context.get("semantic", [])
            ],
            "graph": [
                {
                    "node_id": str(item.get("message_id", "")),
                    "kind": str(item.get("kind", "unknown")),
                    "text": str(item.get("text", ""))[:100] + "..."
                }
                for item in context.get("graph", [])
            ]
        }

        return context, rag_trace

    async def _fetch_messages(self, thread_id: int, n: int) -> List[Dict[str, Any]]:
        """Fetch recent messages from a thread."""
        if hasattr(self.chatlog, 'last_messages'):
            result = self.chatlog.last_messages(thread_id, n=n)
            # Handle both sync and async returns
            if hasattr(result, '__await__'):
                return await result
            return result if isinstance(result, list) else []
        return []

    async def _search_semantic(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Search for semantic matches via vector store."""
        if hasattr(self.vector, 'search'):
            result = self.vector.search(query, k=k)
            # Handle both sync and async returns
            if hasattr(result, '__await__'):
                return await result
            return result if isinstance(result, list) else []
        return []

    async def _search_memory(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Search for related memory entries using MemoryOS semantic retriever.

        Primary: Uses MemoryOSRetriever for vector-based semantic memory search.
        Fallback: Falls back to legacy memory_store.search_related() if available.
        """
        try:
            # Primary: Use MemoryOS semantic retriever for RAG-based memory recall
            if self.memory_retriever:
                memory_results = await self.memory_retriever.retrieve(query, limit=k)
                logger.debug(
                    f"[ContextBroker] Retrieved {len(memory_results)} memory chunks "
                    f"via MemoryOSRetriever"
                )
                return memory_results
        except Exception as e:
            logger.warning(f"[ContextBroker] MemoryOS retriever failed: {e}")

            # Fallback: Use legacy memory_store if available
            if self.memory and hasattr(self.memory, 'search_related'):
                try:
                    result = self.memory.search_related(query, limit=k)
                    # Handle both sync and async returns
                    if hasattr(result, '__await__'):
                        result = await result
                    if isinstance(result, list):
                        logger.debug(
                            f"[ContextBroker] Fallback: Retrieved {len(result)} "
                            f"results from legacy memory_store"
                        )
                        return result
                except Exception as fallback_error:
                    logger.warning(
                        f"[ContextBroker] Legacy memory_store also failed: {fallback_error}"
                    )

            return []

    async def _snapshot_sensors(self) -> Dict[str, Any]:
        """Snapshot current system sensors state."""
        if self.sensors and hasattr(self.sensors, 'snapshot'):
            result = self.sensors.snapshot()
            # Handle both sync and async returns
            if hasattr(result, '__await__'):
                return await result
            return result if isinstance(result, dict) else {}
        return {}

    async def _search_federated(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Search for context from federated peer nodes.

        This method calls the federated context search API if available.

        Args:
            query: Query string
            k: Number of results to fetch

        Returns:
            List of federated search results
        """
        try:
            # Try to import and call the federation context API
            from guardian.routes.federation_context import _search_peers

            results = await _search_peers(query, k)
            return results if isinstance(results, list) else []
        except ImportError:
            logger.debug("Federation context module not available")
            return []
        except Exception as e:
            logger.warning(f"Error searching federated peers: {e}")
            return []

    async def _get_graph_context(
        self, *, user_id: str, thread_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Fetch lightweight graph context for a thread/user pair."""
        try:
            from guardian.graph.connection import connect_neo4j
            from guardian.graph.models import ThreadNode, MessageNode, UserNode
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.debug("[ContextBroker] Graph modules unavailable: %s", exc)
            return []

        try:
            connect_neo4j()
            snippets: List[Dict[str, Any]] = []

            thread = ThreadNode.nodes.get_or_none(thread_id=str(thread_id)) if thread_id else None
            if thread and hasattr(thread.messages, "all"):
                msgs = thread.messages.all()
                for msg in msgs:
                    snippet = {
                        "kind": "graph-fact",
                        "text": getattr(msg, "content", ""),
                        "source": "neo4j",
                        "message_id": getattr(msg, "message_id", ""),
                    }
                    try:
                        sender = msg.user.single()
                        if sender:
                            snippet["user_id"] = getattr(sender, "user_id", None)
                    except Exception:
                        pass
                    snippets.append(snippet)

            if not snippets and user_id:
                user = UserNode.nodes.get_or_none(user_id=str(user_id))
                if user and hasattr(user.messages, "all"):
                    for msg in user.messages.all():
                        snippets.append(
                            {
                                "kind": "graph-fact",
                                "text": getattr(msg, "content", ""),
                                "source": "neo4j",
                                "message_id": getattr(msg, "message_id", ""),
                                "user_id": getattr(user, "user_id", None),
                            }
                        )

            return snippets
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Graph context unavailable; proceeding without it: %s",
                exc,
            )
            return []
