"""Minimal, dependency-light context assembly broker for enriching chat completions."""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from guardian.context.tool_intents import (
    ToolIntentParseError,
    ToolRisk,
    classify_tool_intent,
    parse_tool_intents,
    redact_tool_intent_dict,
)
from guardian.core.config import Settings, get_settings
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE

logger = logging.getLogger(__name__)
_OBSIDIAN_CONNECTOR_NAME = "obsidian_local"
_SOURCE_MODE_CONVERSATION = "conversation"
_SOURCE_MODE_PROJECT = "project"
_SOURCE_MODE_PERSONAL_KNOWLEDGE = "personal_knowledge"
_LOW_CONFIDENCE_SCORE_THRESHOLD = 0.1
_THREAD_CANDIDATE_LIMIT = 500
_PERSONAL_FACT_LIMIT = 100


def _thread_namespace(thread_id: int) -> str:
    return f"thread:{thread_id}"


def _coerce_int(value: Any) -> Optional[int]:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


def _normalize_source_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == _SOURCE_MODE_CONVERSATION:
        return _SOURCE_MODE_CONVERSATION
    if normalized == _SOURCE_MODE_PERSONAL_KNOWLEDGE:
        return _SOURCE_MODE_PERSONAL_KNOWLEDGE
    return _SOURCE_MODE_PROJECT


def _source_mode_boundary_label(value: Any) -> str:
    normalized = _normalize_source_mode(value)
    if normalized == _SOURCE_MODE_CONVERSATION:
        return "active_conversation_only"
    if normalized == _SOURCE_MODE_PERSONAL_KNOWLEDGE:
        return "same_user_only"
    return "same_user_same_project"


def _is_verified_active_personal_fact(fact: Any) -> bool:
    if not isinstance(fact, dict):
        return False
    if str(fact.get("status") or "").strip().lower() != "verified":
        return False
    if fact.get("is_active") is False:
        return False

    key = str(fact.get("key") or "").strip()
    value = str(fact.get("value") or "").strip()
    return bool(key and value)


def _coerce_graph_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _coerce_graph_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_coerce_graph_value(item) for item in value]

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass

    to_native = getattr(value, "to_native", None)
    if callable(to_native):
        try:
            return _coerce_graph_value(to_native())
        except Exception:
            pass

    return str(value)


def _looks_like_json(text: str) -> bool:
    s = (text or "").lstrip()
    if not s:
        return False
    if s[0] in "{[":
        return True
    # Accept fenced JSON (```json ...``` or ``` ... ```)
    if s.startswith("```"):
        return True
    return False


def maybe_extract_tool_intents(
    model_text: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract tool intents from model output if it appears to be JSON."""
    if not _looks_like_json(model_text):
        return None, None

    try:
        intents = parse_tool_intents(model_text)
    except ToolIntentParseError as exc:
        return None, str(exc)

    normalized: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    for intent in intents:
        policy = classify_tool_intent(intent)
        record = {
            "id": intent.intent_id,
            "tool": intent.tool,
            "args": intent.args,
            "reason": intent.reason,
            "risk": policy.risk.value,
            "description": policy.description,
            "requires_consent": policy.requires_consent,
            "approved": policy.risk == ToolRisk.SAFE_READONLY,
        }
        normalized.append(record)
        if policy.requires_consent:
            pending.append(record)

    return {
        "tool_intents": normalized,
        "pending_tool_intents": pending,
    }, None


def build_assistant_response_payload(assistant_text: str) -> Dict[str, Any]:
    """Build a normalized assistant payload with optional tool intent metadata."""
    response: Dict[str, Any] = {"assistant_text": assistant_text}
    tool_block, tool_err = maybe_extract_tool_intents(assistant_text)

    if tool_block is not None:
        response.update(tool_block)
        tool_intents = tool_block.get("tool_intents", [])
        pending_tool_intents = tool_block.get("pending_tool_intents", [])
        tool_intents_redacted = [
            redact_tool_intent_dict(intent) for intent in tool_intents
        ]
        pending_tool_intents_redacted = [
            redact_tool_intent_dict(intent) for intent in pending_tool_intents
        ]
        # Secure-by-default exposure surface for UI/client consumers.
        response["tool_intents"] = tool_intents_redacted
        response["pending_tool_intents"] = pending_tool_intents_redacted
        # Explicit aliases retained for clarity and compatibility.
        response["tool_intents_redacted"] = tool_intents_redacted
        response[
            "pending_tool_intents_redacted"
        ] = pending_tool_intents_redacted
        debug_unredacted = (
            os.getenv("CODEXIFY_DEBUG_UNREDACTED_TOOL_INTENTS") == "1"
        )
        if debug_unredacted:
            response["tool_intents_unredacted"] = tool_intents
            response["pending_tool_intents_unredacted"] = pending_tool_intents
        response["consent_required"] = bool(
            tool_block.get("pending_tool_intents")
        )
    if tool_err:
        response["tool_intent_error"] = tool_err

    return response


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
                self.memory_retriever = MemoryOSRetriever(
                    vector_store,
                    chatlog_db=chatlog_db,
                )
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Memory retriever init failed: %s", exc
            )
        logger.info(
            "[ContextBroker] Initialized with MemoryOS semantic retriever"
        )

    async def assemble(
        self,
        thread_id: int,
        query: str,
        *,
        depth_mode: Optional[str] = None,
        depth: Optional[str] = None,
        project_id: Optional[int] = None,
        n_messages: int = 6,
        k_semantic: int = 4,
        k_memory: int = 5,
        k_project_docs: int = 4,
        k_thread_docs: int = 4,
        doc_excerpt_chars: int = 420,
        federated: bool = False,
        user_id: Optional[str] = None,
        source_mode: str = _SOURCE_MODE_PROJECT,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Assemble a context bundle for the given thread and query.

        Args:
            thread_id: ID of the chat thread
            query: Query string for semantic search
            depth_mode: Retrieval depth ("shallow", "normal", "deep", "diagnostic")
            project_id: Optional project scope override for project-library docs
            source_mode: Retrieval boundary beyond the active thread
            n_messages: Number of recent messages to fetch
            k_semantic: Number of semantic results to fetch
            k_memory: Number of memory results to fetch
            k_project_docs: Max explicit project library documents to include
            k_thread_docs: Max thread-linked documents to include
            doc_excerpt_chars: Max characters per document excerpt
            federated: If True, include federated context from peer nodes

        Returns:
            A tuple of (context, rag_trace):

            context: Dict with keys depending on depth:
                - "messages": Recent thread messages (all depths)
                - "semantic": Semantic search results (all depths except "shallow")
                - "docs": Project/thread document library excerpts (normal+)
                - "graph": Graph-derived context (if enabled)
                - "memory": Memory search results (deep, diagnostic)
                - "sensors": System sensor snapshot (diagnostic only)
                - "federated": Federated search results (if federated=True)

            rag_trace: Dict summarizing contributing items:
                - "documents": List of {id, title, score, snippet}
                - "graph": List of {node_id, kind, text}
        """
        # Normalize depth. `depth` is a legacy alias kept for compatibility.
        normalized_depth = str(depth_mode or depth or "normal").strip().lower()
        normalized_source_mode = _normalize_source_mode(source_mode)
        conversation_only = normalized_source_mode == _SOURCE_MODE_CONVERSATION
        source_mode_boundary = _source_mode_boundary_label(
            normalized_source_mode
        )
        resolved_project_id = await self._resolve_project_id(
            thread_id=thread_id, project_id=project_id
        )
        resolved_user_id = await self._resolve_user_id(
            thread_id=thread_id, user_id=user_id
        )

        context: Dict[str, Any] = {}

        # Always include recent messages
        try:
            messages = await self._fetch_messages(thread_id, n_messages)
            context["messages"] = messages
        except Exception as e:
            logger.warning(
                "[ContextBroker] Failed to fetch messages for thread %s: %s",
                thread_id,
                e,
            )
            context["messages"] = []

        # Always include semantic search (for all depths except "shallow")
        context["obsidian"] = []
        semantic_widen_reason = "none"
        if normalized_depth != "shallow" and not conversation_only:
            try:
                (
                    semantic_thread,
                    semantic_widen_reason,
                    _semantic_trace,
                ) = await self._search_with_widening(
                    query=query,
                    k=k_semantic,
                    thread_id=thread_id,
                    user_id=resolved_user_id,
                    project_id=resolved_project_id,
                    source_mode=normalized_source_mode,
                    search_fn=self._search_semantic,
                )
                semantic_obsidian: list[dict[str, Any]] = []
                if self._obsidian_retrieval_enabled():
                    try:
                        semantic_obsidian = await self._search_semantic(
                            query,
                            k_semantic,
                            namespace=OBSIDIAN_NAMESPACE,
                        )
                    except Exception as exc:
                        logger.warning(
                            "[ContextBroker] Obsidian retrieval failed; continuing without it: %s",
                            exc,
                        )
                context["obsidian"] = semantic_obsidian
                context["semantic"] = semantic_thread + semantic_obsidian
            except Exception as e:
                logger.warning(f"Failed to perform semantic search: {e}")
                context["semantic"] = []
                context["obsidian"] = []
        else:
            context["semantic"] = []
            context["obsidian"] = []

        context["docs"] = {"project": [], "thread": [], "global": []}
        if not conversation_only and normalized_depth in (
            "normal",
            "deep",
            "diagnostic",
        ):
            try:
                scoped_docs = await self.get_scoped_documents(
                    thread_id=thread_id,
                    project_id=resolved_project_id,
                    k_project_docs=k_project_docs,
                    k_thread_docs=k_thread_docs,
                    doc_excerpt_chars=doc_excerpt_chars,
                )
                context["docs"] = scoped_docs
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Failed to fetch scoped documents: %s", e
                )

        personal_facts_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                "source_mode_conversation"
                if conversation_only
                else "depth_not_allowed"
            ),
            "count": 0,
            "retrieved_count": 0,
            "user_id": resolved_user_id or "default",
            "source_mode": normalized_source_mode,
            "boundary": source_mode_boundary,
        }
        if not conversation_only and normalized_depth in ("deep", "diagnostic"):
            try:
                (
                    personal_facts,
                    personal_facts_trace,
                ) = await self._fetch_verified_personal_facts(
                    user_id=resolved_user_id,
                    limit=_PERSONAL_FACT_LIMIT,
                )
                if personal_facts:
                    context["personal_facts"] = personal_facts
                personal_facts_trace = {
                    **personal_facts_trace,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Personal facts unavailable; continuing without them: %s",
                    e,
                )
                personal_facts_trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "count": 0,
                    "retrieved_count": 0,
                    "user_id": resolved_user_id or "default",
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }

        # Optional graph-derived context (explicit flag; deferred for CORE LOOP by default)
        context["graph"] = []
        graph_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                "source_mode_conversation" if conversation_only else "disabled"
            ),
            "count": 0,
            "source_mode": normalized_source_mode,
            "boundary": source_mode_boundary,
        }
        if not conversation_only and getattr(
            self.settings, "GUARDIAN_ENABLE_GRAPH_CONTEXT", False
        ):
            try:
                graph_chunks, graph_trace = await self._get_graph_context(
                    user_id=resolved_user_id or "default",
                    thread_id=str(thread_id),
                )
                context["graph"] = graph_chunks
                graph_trace = {
                    **graph_trace,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Graph context unavailable; continuing without it: %s",
                    e,
                )
                graph_trace = {
                    **graph_trace,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }

        # Include memory search for deep and diagnostic modes
        memory_widen_reason = "none"
        memory_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                "source_mode_conversation"
                if conversation_only
                else "depth_not_allowed"
            ),
            "count": 0,
            "boundary": source_mode_boundary,
            "source_mode": normalized_source_mode,
        }
        if normalized_depth in ("deep", "diagnostic"):
            try:
                if conversation_only:
                    context["memory"] = []
                elif self.memory:
                    (
                        memory,
                        memory_widen_reason,
                        memory_trace,
                    ) = await self._search_with_widening(
                        query=query,
                        k=k_memory,
                        thread_id=thread_id,
                        user_id=resolved_user_id,
                        project_id=resolved_project_id,
                        source_mode=normalized_source_mode,
                        search_fn=self._search_memory,
                    )
                    context["memory"] = memory
                else:
                    context["memory"] = []
                    memory_trace = {
                        "attempted": False,
                        "status": "skipped",
                        "reason": "no_memory_store",
                        "count": 0,
                        "boundary": source_mode_boundary,
                        "source_mode": normalized_source_mode,
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch memory results: {e}")
                context["memory"] = []
                memory_trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "count": 0,
                    "boundary": source_mode_boundary,
                    "source_mode": normalized_source_mode,
                }

        # Include sensor snapshot for diagnostic mode only
        if normalized_depth == "diagnostic":
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
                if conversation_only:
                    context["federated"] = []
                else:
                    federated_results = await self._search_federated(
                        query, k_semantic
                    )
                    context["federated"] = federated_results
            except Exception as e:
                logger.warning(f"Failed to fetch federated context: {e}")
                context["federated"] = []

        # Keep source-boundary diagnostics stable while source_mode still
        # crosses the worker boundary through the temporary origin bridge.
        rag_trace = {
            "thread_id": thread_id,
            "project_id": resolved_project_id,
            "depth_mode": normalized_depth,
            "documents": [
                {
                    "id": str(item.get("id", "")),
                    "title": str(
                        item.get("metadata", {}).get("filename", "unknown")
                    ),
                    "score": float(item.get("score", 0.0)),
                    "snippet": str(item.get("text", ""))[:100] + "...",
                }
                for item in context.get("semantic", [])
            ],
            "graph": [
                {
                    "node_id": str(item.get("message_id", "")),
                    "kind": str(item.get("kind", "unknown")),
                    "text": str(item.get("text", ""))[:100] + "...",
                }
                for item in context.get("graph", [])
            ],
            "source_mode": normalized_source_mode,
            "widen_reason": self._merge_widen_reason(
                semantic_widen_reason, memory_widen_reason
            ),
            "graph_context": graph_trace,
            "memory_context": memory_trace,
            "personal_facts_context": personal_facts_trace,
        }

        try:
            logger.info(
                "[ContextBroker] thread=%s depth=%s messages=%s semantic=%s obsidian=%s docs(project/thread)=%s/%s memory=%s(%s) graph=%s(%s)",
                thread_id,
                normalized_depth,
                len(context.get("messages", [])),
                len(context.get("semantic", [])),
                len(context.get("obsidian", [])),
                len(context.get("docs", {}).get("project", [])),
                len(context.get("docs", {}).get("thread", [])),
                len(context.get("memory", [])) if "memory" in context else 0,
                memory_trace.get("status"),
                len(context.get("graph", [])),
                graph_trace.get("status"),
            )
        except Exception:
            pass

        return context, rag_trace

    async def _fetch_verified_personal_facts(
        self,
        *,
        user_id: Optional[str],
        limit: int,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch verified, active personal facts from the chatlog adapter."""
        effective_user_id = str(user_id or "default").strip() or "default"
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "no_fact_adapter",
            "count": 0,
            "retrieved_count": 0,
            "user_id": effective_user_id,
        }

        getter = getattr(self.chatlog, "list_facts", None)
        if not callable(getter):
            return [], trace

        try:
            try:
                result = getter(
                    effective_user_id,
                    status="verified",
                    active_only=True,
                    limit=limit,
                )
            except TypeError:
                result = getter(
                    effective_user_id,
                    status="verified",
                    active_only=True,
                )
            if hasattr(result, "__await__"):
                result = await result
            raw_facts = result if isinstance(result, list) else []
            eligible_facts = [
                fact
                for fact in raw_facts
                if _is_verified_active_personal_fact(fact)
            ]
            trace.update(
                attempted=True,
                retrieved_count=len(raw_facts),
                count=len(eligible_facts),
                status=(
                    "contributed" if eligible_facts else "attempted_no_hits"
                ),
                reason=(
                    "verified_active_facts"
                    if eligible_facts
                    else "no_verified_facts"
                ),
            )
            return eligible_facts, trace
        except Exception as exc:
            trace.update(
                attempted=True,
                status="failed",
                reason="retrieval_error",
                error=str(exc),
                count=0,
                retrieved_count=0,
            )
            return [], trace

    def _obsidian_retrieval_enabled(self) -> bool:
        getter = getattr(self.chatlog, "get_connector_config", None)
        if not callable(getter):
            return False
        try:
            config = getter(_OBSIDIAN_CONNECTOR_NAME)
            if hasattr(config, "__await__"):
                return False
            if not isinstance(config, dict):
                return False
            settings = config.get("settings")
            if not isinstance(settings, dict):
                return False
            if not str(settings.get("vault_root") or "").strip():
                return False
            if settings.get("enabled") is False:
                return False
            return True
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Obsidian connector check failed: %s", exc
            )
            return False

    async def _fetch_messages(
        self, thread_id: int, n: int
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages from a thread.

        Uses chatlog.last_messages when available, otherwise falls back to
        chatlog.list_messages(thread_id, limit=n, offset=0).
        """
        # Preferred: use last_messages if adapter provides it (ordered newest→oldest)
        if hasattr(self.chatlog, "last_messages"):
            result = self.chatlog.last_messages(thread_id, n=n)
        # Fallback for adapters that only expose list_messages (e.g., ChatDB/PgDB)
        elif hasattr(self.chatlog, "list_messages"):
            result = self.chatlog.list_messages(
                thread_id,
                limit=n,
                offset=0,
            )
        else:
            return []

        # Handle both sync and async returns
        if hasattr(result, "__await__"):
            result = await result

        return result if isinstance(result, list) else []

    async def _search_semantic(
        self,
        query: str,
        k: int,
        *,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for semantic matches via vector store."""
        if hasattr(self.vector, "search"):
            try:
                result = self.vector.search(query, k=k, namespace=namespace)
            except TypeError:
                result = self.vector.search(query, k=k)
            # Handle both sync and async returns
            if hasattr(result, "__await__"):
                return await result
            return result if isinstance(result, list) else []
        return []

    async def _search_memory(
        self,
        query: str,
        k: int,
        *,
        namespace: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Search for related memory entries using MemoryOS semantic retriever.

        Primary: Uses MemoryOSRetriever for vector-based semantic memory search.
        Fallback: Falls back to legacy memory_store.search_related() if available.
        """
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "no_retriever",
            "count": 0,
        }
        if self.memory_retriever:
            try:
                retrieve_with_trace = getattr(
                    self.memory_retriever, "retrieve_with_trace", None
                )
                if callable(retrieve_with_trace):
                    memory_results, retriever_trace = await retrieve_with_trace(
                        query,
                        limit=k,
                        namespace=namespace,
                    )
                else:
                    try:
                        memory_results = await self.memory_retriever.retrieve(
                            query,
                            limit=k,
                            namespace=namespace,
                        )
                    except TypeError:
                        memory_results = await self.memory_retriever.retrieve(
                            query, limit=k
                        )
                    retriever_trace = {
                        "attempted": True,
                        "status": (
                            "contributed"
                            if memory_results
                            else "attempted_no_hits"
                        ),
                        "reason": ("results" if memory_results else "no_hits"),
                        "count": len(memory_results),
                    }
                trace = {"attempted": True, **retriever_trace}
                logger.debug(
                    f"[ContextBroker] Retrieved {len(memory_results)} memory chunks "
                    f"via MemoryOSRetriever"
                )
                return memory_results, trace
            except Exception as e:
                logger.warning(
                    f"[ContextBroker] MemoryOS retriever failed: {e}"
                )
                trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retriever_error",
                    "error": str(e),
                    "count": 0,
                }

        # Fallback: Use legacy memory_store if available.
        if (
            namespace is None
            and self.memory
            and hasattr(self.memory, "search_related")
        ):
            try:
                result = self.memory.search_related(query, limit=k)
                if hasattr(result, "__await__"):
                    result = await result
                if isinstance(result, list):
                    trace = {
                        "attempted": True,
                        "status": (
                            "contributed" if result else "attempted_no_hits"
                        ),
                        "reason": (
                            "legacy_results" if result else "legacy_no_hits"
                        ),
                        "count": len(result),
                    }
                    logger.debug(
                        f"[ContextBroker] Fallback: Retrieved {len(result)} "
                        f"results from legacy memory_store"
                    )
                    return result, trace
            except Exception as fallback_error:
                logger.warning(
                    f"[ContextBroker] Legacy memory_store also failed: {fallback_error}"
                )
                trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "legacy_retriever_error",
                    "error": str(fallback_error),
                    "count": 0,
                }

        return [], trace

    async def _resolve_user_id(
        self, *, thread_id: int, user_id: Optional[str]
    ) -> Optional[str]:
        explicit_user = str(user_id or "").strip()
        if explicit_user:
            return explicit_user

        getter = getattr(self.chatlog, "get_chat_thread", None)
        if not callable(getter):
            return None

        try:
            thread = getter(thread_id)
            if hasattr(thread, "__await__"):
                thread = await thread
            if isinstance(thread, dict):
                resolved_user = str(thread.get("user_id") or "").strip()
                return resolved_user or None
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Failed to resolve user_id for thread %s: %s",
                thread_id,
                exc,
            )
        return None

    @staticmethod
    def _unpack_search_output(
        result: Any,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if (
            isinstance(result, tuple)
            and len(result) == 2
            and isinstance(result[1], dict)
        ):
            hits = result[0] if isinstance(result[0], list) else []
            return hits, dict(result[1])
        if isinstance(result, list):
            return result, {}
        return [], {}

    async def _search_with_widening(
        self,
        *,
        query: str,
        k: int,
        thread_id: int,
        user_id: Optional[str],
        project_id: Optional[int],
        source_mode: str,
        search_fn: Any,
    ) -> tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        normalized_source_mode = _normalize_source_mode(source_mode)
        diagnostics: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "not_attempted",
            "source_mode": normalized_source_mode,
            "boundary": _source_mode_boundary_label(normalized_source_mode),
            "primary_hit_count": 0,
            "candidate_thread_count": 0,
            "candidate_hit_count": 0,
            "result_count": 0,
            "widened": False,
        }
        if k <= 0:
            diagnostics["reason"] = "invalid_limit"
            return [], "none", diagnostics
        if normalized_source_mode == _SOURCE_MODE_CONVERSATION:
            diagnostics.update(reason="source_mode_conversation")
            return [], "none", diagnostics

        try:
            primary_output = await search_fn(
                query,
                k,
                namespace=_thread_namespace(thread_id),
            )
        except Exception as exc:
            diagnostics.update(
                attempted=True,
                status="failed",
                reason="primary_search_error",
                error=str(exc),
            )
            return [], "none", diagnostics

        primary_hits, search_trace = self._unpack_search_output(primary_output)
        diagnostics.update(
            attempted=True,
            retriever=search_trace,
            primary_hit_count=len(primary_hits),
        )
        if search_trace.get("status") == "failed" and not primary_hits:
            diagnostics.update(
                status="failed",
                reason=search_trace.get("reason", "primary_search_error"),
                error=search_trace.get("error"),
                result_count=0,
            )
            return [], "none", diagnostics

        widen_reason = self._determine_widen_reason(primary_hits, k)
        if widen_reason == "none":
            diagnostics.update(
                status="contributed" if primary_hits else "attempted_no_hits",
                reason=(
                    "local_hits"
                    if primary_hits
                    else search_trace.get("reason", "no_hits")
                ),
                result_count=len(primary_hits[:k]),
                candidate_thread_count=0,
                widened=False,
            )
            return primary_hits[:k], "none", diagnostics

        candidate_threads = await self._list_widening_threads(
            thread_id=thread_id,
            user_id=user_id,
            project_id=project_id,
            source_mode=normalized_source_mode,
        )
        diagnostics["candidate_thread_count"] = len(candidate_threads)
        if not candidate_threads:
            if primary_hits:
                diagnostics.update(
                    status="contributed",
                    reason="local_hits",
                    result_count=len(primary_hits[:k]),
                    widened=False,
                )
            else:
                diagnostics.update(
                    status=(
                        "skipped"
                        if not user_id
                        or (
                            normalized_source_mode == _SOURCE_MODE_PROJECT
                            and project_id is None
                        )
                        else "no_eligible_candidates"
                    ),
                    reason=(
                        "boundary_blocked"
                        if not user_id
                        or (
                            normalized_source_mode == _SOURCE_MODE_PROJECT
                            and project_id is None
                        )
                        else "no_eligible_candidates"
                    ),
                )
            return primary_hits[:k], "none", diagnostics

        merged_hits = self._seed_thread_hits_for_widening(
            primary_hits,
            target_count=k,
            widen_reason=widen_reason,
        )
        widened_executed = False
        candidate_hit_count = 0

        for thread in candidate_threads:
            candidate_id = _coerce_int(thread.get("id"))
            if candidate_id is None:
                continue
            remaining_slots = max(k - len(merged_hits), 0)
            if (
                remaining_slots <= 0
                and widen_reason != "low_confidence_thread_hits"
            ):
                break
            request_k = remaining_slots if remaining_slots > 0 else 1
            try:
                outcome = await search_fn(
                    query,
                    request_k,
                    namespace=_thread_namespace(candidate_id),
                )
            except Exception as exc:
                diagnostics.update(
                    status="failed",
                    reason="candidate_search_error",
                    error=str(exc),
                )
                break
            hits, _candidate_trace = self._unpack_search_output(outcome)
            if not hits:
                continue
            widened_executed = True
            candidate_hit_count += len(hits)
            merged_hits = self._dedupe_retrieval_items([*merged_hits, *hits])[
                :k
            ]
            if len(merged_hits) >= k:
                break

        final_hits = merged_hits[:k] if widened_executed else primary_hits[:k]
        effective_widen_reason = (
            "explicit_personal_knowledge"
            if widened_executed
            and normalized_source_mode == _SOURCE_MODE_PERSONAL_KNOWLEDGE
            else (widen_reason if widened_executed else "none")
        )
        if diagnostics.get("status") == "failed":
            diagnostics.update(
                widened=widened_executed,
                candidate_hit_count=candidate_hit_count,
                result_count=len(final_hits),
            )
            return final_hits, effective_widen_reason, diagnostics
        diagnostics.update(
            widened=widened_executed,
            candidate_hit_count=candidate_hit_count,
            result_count=len(final_hits),
            status="contributed" if final_hits else "attempted_no_hits",
            reason=(
                "widened"
                if widened_executed
                else (search_trace.get("reason") or "candidate_search_no_hits")
            ),
        )
        return final_hits, effective_widen_reason, diagnostics

    async def _list_widening_threads(
        self,
        *,
        thread_id: int,
        user_id: Optional[str],
        project_id: Optional[int],
        source_mode: str,
    ) -> List[Dict[str, Any]]:
        normalized_source_mode = _normalize_source_mode(source_mode)
        if not user_id:
            return []
        if normalized_source_mode == _SOURCE_MODE_CONVERSATION:
            return []
        if (
            normalized_source_mode == _SOURCE_MODE_PROJECT
            and project_id is None
        ):
            return []

        list_threads = getattr(self.chatlog, "list_chat_threads", None)
        if not callable(list_threads):
            return []

        scoped_project_id = (
            project_id
            if normalized_source_mode == _SOURCE_MODE_PROJECT
            else None
        )
        try:
            threads = list_threads(
                limit=_THREAD_CANDIDATE_LIMIT,
                offset=0,
                user_id=user_id,
                project_id=scoped_project_id,
            )
        except TypeError:
            try:
                threads = list_threads(limit=_THREAD_CANDIDATE_LIMIT, offset=0)
            except TypeError:
                threads = list_threads()
        if hasattr(threads, "__await__"):
            threads = await threads
        if not isinstance(threads, list):
            return []

        same_project_threads: List[Dict[str, Any]] = []
        cross_project_threads: List[Dict[str, Any]] = []
        for thread in threads:
            if not self._is_eligible_widening_thread(
                thread,
                thread_id=thread_id,
                user_id=user_id,
                project_id=project_id,
                source_mode=normalized_source_mode,
            ):
                continue
            thread_project_id = _coerce_int(thread.get("project_id"))
            if project_id is not None and thread_project_id == project_id:
                same_project_threads.append(thread)
            else:
                cross_project_threads.append(thread)

        if normalized_source_mode == _SOURCE_MODE_PROJECT:
            return same_project_threads
        return same_project_threads + cross_project_threads

    def _is_eligible_widening_thread(
        self,
        thread: Any,
        *,
        thread_id: int,
        user_id: str,
        project_id: Optional[int],
        source_mode: str,
    ) -> bool:
        if not isinstance(thread, dict):
            return False
        if _normalize_source_mode(source_mode) == _SOURCE_MODE_CONVERSATION:
            return False
        candidate_id = _coerce_int(thread.get("id"))
        if candidate_id is None or candidate_id == thread_id:
            return False
        candidate_user_id = str(thread.get("user_id") or "").strip()
        if not candidate_user_id or candidate_user_id != user_id:
            return False
        if thread.get("archived_at"):
            return False
        if bool(thread.get("exclude_from_identity")):
            return False
        if bool(thread.get("modeling_excluded")):
            return False
        if _normalize_source_mode(source_mode) == _SOURCE_MODE_PROJECT:
            return _coerce_int(thread.get("project_id")) == project_id
        return True

    def _determine_widen_reason(
        self, hits: List[Dict[str, Any]], target_count: int
    ) -> str:
        if target_count <= 0:
            return "none"
        limited_hits = list(hits[:target_count])
        if len(limited_hits) < target_count:
            return "insufficient_thread_hits"
        best_score = self._best_numeric_score(limited_hits)
        if (
            best_score is not None
            and best_score < _LOW_CONFIDENCE_SCORE_THRESHOLD
        ):
            return "low_confidence_thread_hits"
        return "none"

    def _seed_thread_hits_for_widening(
        self,
        hits: List[Dict[str, Any]],
        *,
        target_count: int,
        widen_reason: str,
    ) -> List[Dict[str, Any]]:
        limited_hits = self._dedupe_retrieval_items(hits[:target_count])
        if (
            widen_reason == "low_confidence_thread_hits"
            and target_count > 0
            and len(limited_hits) >= target_count
        ):
            preserve_count = max(target_count - 1, 0)
            return limited_hits[:preserve_count]
        return limited_hits[:target_count]

    def _best_numeric_score(
        self, hits: List[Dict[str, Any]]
    ) -> Optional[float]:
        scores: List[float] = []
        for item in hits:
            raw_score = item.get("score")
            try:
                if isinstance(raw_score, bool):
                    continue
                scores.append(float(raw_score))
            except (TypeError, ValueError):
                continue
        if not scores:
            return None
        return max(scores)

    def _dedupe_retrieval_items(
        self, hits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for item in hits:
            key = self._retrieval_item_key(item, len(deduped))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _retrieval_item_key(
        self, item: Dict[str, Any], fallback_index: int
    ) -> str:
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = item.get("meta")
        if isinstance(metadata, dict):
            for key in ("source_message_id", "message_id", "id", "chunk_id"):
                value = metadata.get(key)
                if value not in (None, ""):
                    return f"meta:{key}:{value}"
        item_id = item.get("id")
        if item_id not in (None, ""):
            return f"id:{item_id}"
        text = str(item.get("text") or "").strip()
        if text:
            return f"text:{text[:240]}"
        return f"fallback:{fallback_index}"

    def _merge_widen_reason(self, *reasons: str) -> str:
        priority = {
            "none": 0,
            "insufficient_thread_hits": 1,
            "low_confidence_thread_hits": 2,
            "explicit_personal_knowledge": 3,
        }
        selected = "none"
        for reason in reasons:
            normalized_reason = str(reason or "none")
            if priority.get(normalized_reason, -1) > priority[selected]:
                selected = normalized_reason
        return selected

    async def get_scoped_documents(
        self,
        *,
        thread_id: int,
        project_id: Optional[int] = None,
        k_project_docs: int = 4,
        k_thread_docs: int = 4,
        doc_excerpt_chars: int = 420,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch scoped document excerpts for RAG with project-first priority."""
        resolved_project_id = await self._resolve_project_id(
            thread_id=thread_id, project_id=project_id
        )
        return self._fetch_scoped_documents(
            thread_id=thread_id,
            project_id=resolved_project_id,
            k_project_docs=k_project_docs,
            k_thread_docs=k_thread_docs,
            doc_excerpt_chars=doc_excerpt_chars,
        )

    async def _resolve_project_id(
        self, *, thread_id: int, project_id: Optional[int]
    ) -> Optional[int]:
        explicit_project = _coerce_int(project_id)
        if explicit_project is not None:
            return explicit_project

        getter = getattr(self.chatlog, "get_chat_thread", None)
        if not callable(getter):
            return None

        try:
            thread = getter(thread_id)
            if hasattr(thread, "__await__"):
                thread = await thread
            if isinstance(thread, dict):
                return _coerce_int(thread.get("project_id"))
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Failed to resolve project_id for thread %s: %s",
                thread_id,
                exc,
            )
        return None

    def _fetch_scoped_documents(
        self,
        *,
        thread_id: int,
        project_id: Optional[int],
        k_project_docs: int,
        k_thread_docs: int,
        doc_excerpt_chars: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        docs: Dict[str, List[Dict[str, Any]]] = {
            "project": [],
            "thread": [],
            "global": [],
        }

        session_provider = self._resolve_session_provider()
        if session_provider is None:
            return docs

        try:
            from guardian.db.models import (
                GeneratedDocument,
                ProjectDocumentLink,
                ThreadDocument,
                UploadedDocument,
            )
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Document models unavailable; skipping doc retrieval: %s",
                exc,
            )
            return docs

        session = None
        try:
            session = session_provider()
            if hasattr(session, "__enter__") and hasattr(session, "__exit__"):
                with session as managed_session:
                    docs["project"] = self._query_project_docs(
                        managed_session,
                        project_id=project_id,
                        k_docs=k_project_docs,
                        doc_excerpt_chars=doc_excerpt_chars,
                        generated_model=GeneratedDocument,
                        uploaded_model=UploadedDocument,
                        project_link_model=ProjectDocumentLink,
                    )
                    docs["thread"] = self._query_thread_docs(
                        managed_session,
                        thread_id=thread_id,
                        k_docs=k_thread_docs,
                        doc_excerpt_chars=doc_excerpt_chars,
                        generated_model=GeneratedDocument,
                        uploaded_model=UploadedDocument,
                        thread_link_model=ThreadDocument,
                    )
                return docs

            docs["project"] = self._query_project_docs(
                session,
                project_id=project_id,
                k_docs=k_project_docs,
                doc_excerpt_chars=doc_excerpt_chars,
                generated_model=GeneratedDocument,
                uploaded_model=UploadedDocument,
                project_link_model=ProjectDocumentLink,
            )
            docs["thread"] = self._query_thread_docs(
                session,
                thread_id=thread_id,
                k_docs=k_thread_docs,
                doc_excerpt_chars=doc_excerpt_chars,
                generated_model=GeneratedDocument,
                uploaded_model=UploadedDocument,
                thread_link_model=ThreadDocument,
            )
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Scoped document retrieval failed thread=%s project=%s err=%s",
                thread_id,
                project_id,
                exc,
            )
        finally:
            if session is not None and hasattr(session, "close"):
                try:
                    session.close()
                except Exception:
                    pass

        return docs

    def _query_project_docs(
        self,
        session: Any,
        *,
        project_id: Optional[int],
        k_docs: int,
        doc_excerpt_chars: int,
        generated_model: Any,
        uploaded_model: Any,
        project_link_model: Any,
    ) -> List[Dict[str, Any]]:
        if project_id is None or k_docs <= 0:
            return []

        links = (
            session.query(project_link_model)
            .filter(project_link_model.project_id == project_id)
            .filter(project_link_model.is_enabled.is_(True))
            .order_by(project_link_model.attached_at.desc())
            .limit(max(k_docs * 4, k_docs))
            .all()
        )

        docs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for link in links:
            doc_type = self._normalize_doc_type(
                getattr(link, "document_type", "")
            )
            doc_id = str(getattr(link, "document_id", "") or "")
            if not doc_type or not doc_id:
                continue
            dedupe_key = (doc_type, doc_id)
            if dedupe_key in seen:
                continue

            loaded = self._load_doc_by_type(
                session=session,
                doc_id=doc_id,
                doc_type=doc_type,
                generated_model=generated_model,
                uploaded_model=uploaded_model,
            )
            if not loaded:
                continue
            seen.add(dedupe_key)
            docs.append(
                self._serialize_doc_record(
                    row=loaded,
                    doc_type=doc_type,
                    scope="project",
                    excerpt_chars=doc_excerpt_chars,
                    relation="project_library",
                    attached_at=getattr(link, "attached_at", None),
                    attached_by=getattr(link, "attached_by", None),
                )
            )
            if len(docs) >= k_docs:
                break
        return docs

    def _query_thread_docs(
        self,
        session: Any,
        *,
        thread_id: int,
        k_docs: int,
        doc_excerpt_chars: int,
        generated_model: Any,
        uploaded_model: Any,
        thread_link_model: Any,
    ) -> List[Dict[str, Any]]:
        if k_docs <= 0:
            return []

        links = (
            session.query(thread_link_model)
            .filter(thread_link_model.thread_id == thread_id)
            .order_by(thread_link_model.created_at.desc())
            .limit(max(k_docs * 4, k_docs))
            .all()
        )

        docs: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for link in links:
            doc_id = str(getattr(link, "document_id", "") or "")
            if not doc_id or doc_id in seen:
                continue

            loaded = self._load_doc_from_thread_link(
                session=session,
                doc_id=doc_id,
                generated_model=generated_model,
                uploaded_model=uploaded_model,
            )
            if not loaded:
                continue

            row, doc_type = loaded
            seen.add(doc_id)
            docs.append(
                self._serialize_doc_record(
                    row=row,
                    doc_type=doc_type,
                    scope="thread",
                    excerpt_chars=doc_excerpt_chars,
                    relation=str(
                        getattr(link, "relation", "attached") or "attached"
                    ),
                    attached_at=getattr(link, "created_at", None),
                    attached_by=None,
                )
            )
            if len(docs) >= k_docs:
                break
        return docs

    def _load_doc_by_type(
        self,
        *,
        session: Any,
        doc_id: str,
        doc_type: str,
        generated_model: Any,
        uploaded_model: Any,
    ) -> Any | None:
        if doc_type == "generated":
            row = (
                session.query(generated_model)
                .filter(generated_model.id == doc_id)
                .first()
            )
            if row and getattr(row, "deleted_at", None) is None:
                return row
            return None

        row = (
            session.query(uploaded_model)
            .filter(uploaded_model.id == doc_id)
            .first()
        )
        if row and getattr(row, "deleted_at", None) is None:
            return row
        return None

    def _load_doc_from_thread_link(
        self,
        *,
        session: Any,
        doc_id: str,
        generated_model: Any,
        uploaded_model: Any,
    ) -> tuple[Any, str] | None:
        generated = self._load_doc_by_type(
            session=session,
            doc_id=doc_id,
            doc_type="generated",
            generated_model=generated_model,
            uploaded_model=uploaded_model,
        )
        if generated is not None:
            return generated, "generated"

        uploaded = self._load_doc_by_type(
            session=session,
            doc_id=doc_id,
            doc_type="uploaded",
            generated_model=generated_model,
            uploaded_model=uploaded_model,
        )
        if uploaded is not None:
            return uploaded, "uploaded"

        return None

    def _serialize_doc_record(
        self,
        *,
        row: Any,
        doc_type: str,
        scope: str,
        excerpt_chars: int,
        relation: str,
        attached_at: Any,
        attached_by: Any,
    ) -> Dict[str, Any]:
        if doc_type == "generated":
            title = str(
                getattr(row, "title", "") or getattr(row, "id", "document")
            )
            raw_content = str(getattr(row, "content", "") or "")
            source = str(getattr(row, "model", "") or "generated")
            source_table = "generated_documents"
        else:
            title = str(
                getattr(row, "filename", "") or getattr(row, "id", "document")
            )
            raw_content = str(getattr(row, "parsed_text", "") or "")
            source = str(
                getattr(row, "source_tag", "")
                or getattr(row, "mime_type", "")
                or "uploaded"
            )
            source_table = "uploaded_documents"

        return {
            "id": str(getattr(row, "id", "")),
            "title": title,
            "excerpt": self._build_excerpt(raw_content, excerpt_chars),
            "scope": scope,
            "document_type": doc_type,
            "source_table": source_table,
            "source": source,
            "project_id": _coerce_int(getattr(row, "project_id", None)),
            "thread_id": _coerce_int(getattr(row, "thread_id", None)),
            "user_id": getattr(row, "user_id", None),
            "created_at": self._to_iso(getattr(row, "created_at", None)),
            "provenance": {
                "relation": relation,
                "attached_at": self._to_iso(attached_at),
                "attached_by": attached_by,
                "source_tag": getattr(row, "source_tag", None),
                "model": getattr(row, "model", None),
            },
        }

    def _build_excerpt(self, raw_content: str, max_chars: int) -> str:
        content = str(raw_content or "").strip()
        if not content:
            return ""
        if max_chars <= 0:
            return ""
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rstrip() + "..."

    def _to_iso(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        return str(value)

    def _normalize_doc_type(self, value: Any) -> Optional[str]:
        normalized = str(value or "").strip().lower()
        if normalized.startswith("gen"):
            return "generated"
        if normalized.startswith("up"):
            return "uploaded"
        return None

    def _resolve_session_provider(self) -> Optional[Any]:
        """Find a callable that yields a SQLAlchemy session."""
        if self.chatlog is None:
            return None

        explicit = getattr(self.chatlog, "get_session", None)
        if callable(explicit):
            return explicit

        sa_session = getattr(self.chatlog, "_sa_session", None)
        if callable(sa_session):
            return sa_session

        session_local = getattr(self.chatlog, "_SessionLocal", None)
        if session_local is not None:
            return lambda: session_local()

        return None

    async def _snapshot_sensors(self) -> Dict[str, Any]:
        """Snapshot current system sensors state."""
        if self.sensors and hasattr(self.sensors, "snapshot"):
            result = self.sensors.snapshot()
            # Handle both sync and async returns
            if hasattr(result, "__await__"):
                return await result
            return result if isinstance(result, dict) else {}
        return {}

    async def _search_federated(
        self, query: str, k: int
    ) -> List[Dict[str, Any]]:
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
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch lightweight graph context for a thread/user pair."""
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "disabled",
            "count": 0,
            "scope": None,
        }
        try:
            from neomodel import db as neo_db

            from guardian.graph.connection import connect_neo4j
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.debug("[ContextBroker] Graph modules unavailable: %s", exc)
            trace.update(reason="modules_unavailable", error=str(exc))
            return [], trace

        try:
            connect_neo4j()
            trace["attempted"] = True

            def _rows_to_snippets(
                rows: Any, meta: Any, scope: str
            ) -> List[Dict[str, Any]]:
                columns = (
                    [str(column) for column in meta]
                    if isinstance(meta, (list, tuple))
                    else []
                )
                snippets: List[Dict[str, Any]] = []
                if not isinstance(rows, list):
                    return snippets
                for row in rows:
                    if isinstance(row, dict):
                        record = row
                    elif isinstance(row, (list, tuple)):
                        if columns:
                            record = {
                                columns[idx]: row[idx]
                                for idx in range(min(len(columns), len(row)))
                            }
                        else:
                            record = {
                                str(idx): value for idx, value in enumerate(row)
                            }
                    else:
                        continue

                    snippet: Dict[str, Any] = {
                        "kind": "graph-fact",
                        "text": str(record.get("content") or ""),
                        "source": "neo4j",
                        "message_id": str(record.get("message_id") or ""),
                        "scope": scope,
                    }
                    created_at = record.get("created_at")
                    if created_at not in (None, ""):
                        snippet["created_at"] = _coerce_graph_value(created_at)
                    thread_value = record.get("thread_id")
                    if thread_value not in (None, ""):
                        snippet["thread_id"] = str(thread_value)
                    user_value = record.get("user_id")
                    if user_value not in (None, ""):
                        snippet["user_id"] = str(user_value)
                    snippets.append(snippet)
                return snippets

            if thread_id:
                rows, meta = neo_db.cypher_query(
                    """
                    MATCH (t:ThreadNode {thread_id: $thread_id})
                    <-[:PART_OF]-(m:MessageNode)
                    OPTIONAL MATCH (m)-[:SENT_BY]->(u:UserNode)
                    RETURN m.message_id AS message_id,
                           m.content AS content,
                           m.created_at AS created_at,
                           t.thread_id AS thread_id,
                           u.user_id AS user_id
                    ORDER BY m.created_at ASC
                    """,
                    {"thread_id": str(thread_id)},
                )
                snippets = _rows_to_snippets(rows, meta, "thread")
                if snippets:
                    trace.update(
                        status="contributed",
                        reason="thread_match",
                        scope="thread",
                        count=len(snippets),
                    )
                    return snippets, trace

            if user_id:
                rows, meta = neo_db.cypher_query(
                    """
                    MATCH (u:UserNode {user_id: $user_id})
                    <-[:SENT_BY]-(m:MessageNode)
                    OPTIONAL MATCH (m)-[:PART_OF]->(t:ThreadNode)
                    RETURN m.message_id AS message_id,
                           m.content AS content,
                           m.created_at AS created_at,
                           t.thread_id AS thread_id,
                           u.user_id AS user_id
                    ORDER BY m.created_at ASC
                    """,
                    {"user_id": str(user_id)},
                )
                snippets = _rows_to_snippets(rows, meta, "user")
                if snippets:
                    trace.update(
                        status="contributed",
                        reason="user_match",
                        scope="user",
                        count=len(snippets),
                    )
                    return snippets, trace

            trace.update(status="empty", reason="no_rows")
            return [], trace
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Graph context unavailable; proceeding without it: %s",
                exc,
            )
            trace.update(
                attempted=True,
                status="failed",
                reason="query_error",
                error=str(exc),
            )
            return [], trace
