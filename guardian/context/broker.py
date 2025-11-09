"""Minimal, dependency-light context assembly broker for enriching chat completions."""

from typing import Any, Dict, List, Optional
import logging

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

    async def assemble(
        self,
        thread_id: int,
        query: str,
        *,
        depth: str = "normal",
        n_messages: int = 6,
        k_semantic: int = 4,
        k_memory: int = 5,
    ) -> Dict[str, Any]:
        """Assemble a context bundle for the given thread and query.

        Args:
            thread_id: ID of the chat thread
            query: Query string for semantic search
            depth: Retrieval depth ("shallow", "normal", "deep", "diagnostic")
            n_messages: Number of recent messages to fetch
            k_semantic: Number of semantic results to fetch
            k_memory: Number of memory results to fetch

        Returns:
            Dict with keys depending on depth:
            - "messages": Recent thread messages (all depths)
            - "semantic": Semantic search results (all depths)
            - "memory": Memory search results (deep, diagnostic)
            - "sensors": System sensor snapshot (diagnostic only)
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

        return context

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
        """Search for related memory entries."""
        if self.memory and hasattr(self.memory, 'search_related'):
            result = self.memory.search_related(query, limit=k)
            # Handle both sync and async returns
            if hasattr(result, '__await__'):
                return await result
            return result if isinstance(result, list) else []
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
