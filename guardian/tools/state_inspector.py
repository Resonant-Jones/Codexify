"""
State Inspector Module
~~~~~~~~~~~~~~~~~~~~~~

Real-time state inspection for MVP-critical surfaces.
Validates thread health, context bundles, and agent readiness.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_codexify_state(thread_id: str) -> Dict[str, Any]:
    """
    Perform a full health check across MVP-critical surfaces for a given thread.

    Returns a structured state report covering:
    - Thread existence and message count
    - Persona attachment
    - Context bundle readiness (system docs, persona, memory, vector)
    - Linked documents and images
    - Agent target readiness (Codex, Claude)

    Args:
        thread_id: The thread identifier to inspect

    Returns:
        Structured state report dictionary
    """
    # Initialize default state
    state: Dict[str, Any] = {
        "thread_exists": False,
        "messages_loaded": 0,
        "persona_attached": None,
        "context_bundle": {
            "system_docs_attached": False,
            "persona_configured": False,
            "memory_fragments_present": False,
            "vector_context_ready": False,
        },
        "documents_linked": 0,
        "images_linked": 0,
        "agent_targets": {
            "codex_ready": False,
            "claude_ready": False,
        },
    }

    # --- Thread Existence Check ---
    # TODO: Hook up to chatlog_db.get_thread_by_id() or similar
    try:
        from guardian.core.dependencies import chatlog_db

        if chatlog_db:
            # Attempt to check thread existence via message count
            try:
                thread_id_int = int(thread_id)
                messages = chatlog_db.get_messages(thread_id_int)
                if messages is not None:
                    state["thread_exists"] = True
                    state["messages_loaded"] = len(messages) if messages else 0
            except (ValueError, TypeError):
                # thread_id might be a string UUID - try as string
                try:
                    messages = chatlog_db.get_messages(thread_id)
                    if messages is not None:
                        state["thread_exists"] = True
                        state["messages_loaded"] = (
                            len(messages) if messages else 0
                        )
                except Exception:
                    pass
            except AttributeError:
                logger.debug(
                    "[state_inspector] chatlog_db.get_messages not available"
                )
    except ImportError:
        logger.debug(
            "[state_inspector] guardian.core.dependencies not available"
        )
    except Exception as e:
        logger.warning("[state_inspector] thread check failed: %s", e)

    # --- Persona Check ---
    # TODO: Hook up to persona/imprint registry when available
    # Will check: chatlog_db.get_thread_persona(thread_id) or imprint_store.get_active()
    state[
        "persona_attached"
    ] = None  # TODO: persona_store.get_for_thread(thread_id)

    # --- Context Bundle Checks ---
    # TODO: system_docs_attached - check if system docs are loaded for thread context
    # Data source: imprint system / system_prompt_store

    # TODO: persona_configured - check if persona directives are set
    # Data source: persona_store or thread metadata

    # TODO: memory_fragments_present - check if memory fragments exist
    # Data source: memory silo (ephemeral/midterm/longterm)
    try:
        from guardian.routes.memory import EPHEMERAL_MEMORY

        # Check if any memory fragments exist (basic check)
        if EPHEMERAL_MEMORY:
            state["context_bundle"]["memory_fragments_present"] = True
    except ImportError:
        pass

    # TODO: vector_context_ready - check if vector store is initialized and has embeddings
    # Data source: vector_store / RAG system
    try:
        from guardian.core.dependencies import vector_store

        if vector_store is not None:
            state["context_bundle"]["vector_context_ready"] = True
    except (ImportError, AttributeError):
        pass

    # --- Document/Image Links ---
    # TODO: Hook up to document attachment system
    # Data source: chatlog_db.get_thread_documents(thread_id)
    state[
        "documents_linked"
    ] = 0  # TODO: len(doc_store.get_for_thread(thread_id))

    # TODO: Hook up to image attachment system
    # Data source: chatlog_db.get_thread_images(thread_id) or media API
    state[
        "images_linked"
    ] = 0  # TODO: len(media_store.get_images_for_thread(thread_id))

    # --- Agent Readiness ---
    # TODO: codex_ready - check if Codex API is configured and reachable
    # Data source: settings.OPENAI_API_KEY or codex client health check
    try:
        import os

        if os.getenv("OPENAI_API_KEY"):
            state["agent_targets"]["codex_ready"] = True
    except Exception:
        pass

    # TODO: claude_ready - check if Claude API is configured and reachable
    # Data source: settings.ANTHROPIC_API_KEY or claude client health check
    try:
        import os

        if os.getenv("ANTHROPIC_API_KEY"):
            state["agent_targets"]["claude_ready"] = True
    except Exception:
        pass

    logger.debug("[state_inspector] thread=%s state=%s", thread_id, state)
    return state
