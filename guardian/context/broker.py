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


def _thread_namespace(thread_id: int) -> str:
    return f"thread:{thread_id}"


def _coerce_int(value: Any) -> Optional[int]:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


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
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Assemble a context bundle for the given thread and query.

        Args:
            thread_id: ID of the chat thread
            query: Query string for semantic search
            depth_mode: Retrieval depth ("shallow", "normal", "deep", "diagnostic")
            project_id: Optional project scope override for project-library docs
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
        if normalized_depth != "shallow":
            try:
                semantic_thread = await self._search_semantic(
                    query,
                    k_semantic,
                    namespace=_thread_namespace(thread_id),
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
        if normalized_depth in ("normal", "deep", "diagnostic"):
            try:
                scoped_docs = await self.get_scoped_documents(
                    thread_id=thread_id,
                    project_id=project_id,
                    k_project_docs=k_project_docs,
                    k_thread_docs=k_thread_docs,
                    doc_excerpt_chars=doc_excerpt_chars,
                )
                context["docs"] = scoped_docs
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Failed to fetch scoped documents: %s", e
                )

        # Optional graph-derived context (explicit flag; deferred for CORE LOOP by default)
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
        if normalized_depth in ("deep", "diagnostic"):
            try:
                if self.memory:
                    memory = await self._search_memory(
                        query,
                        k_memory,
                        namespace=_thread_namespace(thread_id),
                    )
                    context["memory"] = memory
                else:
                    context["memory"] = []
            except Exception as e:
                logger.warning(f"Failed to fetch memory results: {e}")
                context["memory"] = []

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
                federated_results = await self._search_federated(
                    query, k_semantic
                )
                context["federated"] = federated_results
            except Exception as e:
                logger.warning(f"Failed to fetch federated context: {e}")
                context["federated"] = []

        # Build RAG Trace
        rag_trace = {
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
        }

        try:
            logger.info(
                "[ContextBroker] thread=%s depth=%s messages=%s semantic=%s obsidian=%s docs(project/thread)=%s/%s memory=%s graph=%s",
                thread_id,
                normalized_depth,
                len(context.get("messages", [])),
                len(context.get("semantic", [])),
                len(context.get("obsidian", [])),
                len(context.get("docs", {}).get("project", [])),
                len(context.get("docs", {}).get("thread", [])),
                len(context.get("memory", [])) if "memory" in context else 0,
                len(context.get("graph", [])),
            )
        except Exception:
            pass

        return context, rag_trace

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
    ) -> List[Dict[str, Any]]:
        """Search for related memory entries using MemoryOS semantic retriever.

        Primary: Uses MemoryOSRetriever for vector-based semantic memory search.
        Fallback: Falls back to legacy memory_store.search_related() if available.
        """
        try:
            # Primary: Use MemoryOS semantic retriever for RAG-based memory recall
            if self.memory_retriever:
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
                logger.debug(
                    f"[ContextBroker] Retrieved {len(memory_results)} memory chunks "
                    f"via MemoryOSRetriever"
                )
                return memory_results
        except Exception as e:
            logger.warning(f"[ContextBroker] MemoryOS retriever failed: {e}")

            # Fallback: Use legacy memory_store if available
            if self.memory and hasattr(self.memory, "search_related"):
                try:
                    result = self.memory.search_related(query, limit=k)
                    # Handle both sync and async returns
                    if hasattr(result, "__await__"):
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

        session_factory = getattr(self.chatlog, "get_session", None)
        if not callable(session_factory):
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
            session = session_factory()
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
    ) -> List[Dict[str, Any]]:
        """Fetch lightweight graph context for a thread/user pair."""
        try:
            from guardian.graph.connection import connect_neo4j
            from guardian.graph.models import MessageNode, ThreadNode, UserNode
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.debug("[ContextBroker] Graph modules unavailable: %s", exc)
            return []

        try:
            connect_neo4j()
            snippets: List[Dict[str, Any]] = []

            thread = (
                ThreadNode.nodes.get_or_none(thread_id=str(thread_id))
                if thread_id
                else None
            )
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
                            snippet["user_id"] = getattr(
                                sender, "user_id", None
                            )
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
