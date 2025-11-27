"""Event-driven graph synchronization for the federated awareness graph.

Subscribes to document autosave, collaboration, and federation events,
automatically updating the awareness graph to track relationships and
entity evolution across the federated network.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from guardian.core import event_bus
from guardian.federation.graph_model import GraphEdge, GraphNode
from guardian.federation.graph_store import get_graph_store

logger = logging.getLogger(__name__)


async def subscribe_to_graph_events() -> None:
    """Subscribe to relevant events and update the awareness graph.

    This should be called at application startup to begin listening for
    events that should be reflected in the graph.
    """
    queue = event_bus.subscribe_in_memory()

    try:
        while True:
            message = await queue.get()

            topic = message.get("type")
            payload = message.get("data", {})

            try:
                if topic == "document.autosaved":
                    await _handle_autosave_event(payload)
                elif topic == "collab.update":
                    await _handle_collab_event(payload)
                elif topic == "federation.diff.applied":
                    await _handle_diff_applied_event(payload)
                elif topic == "federation.session.accepted":
                    await _handle_session_accepted_event(payload)
            except Exception as e:
                logger.error(f"Error processing event {topic}: {e}")

    except Exception as e:
        logger.error(f"Graph event subscription error: {e}")
    finally:
        event_bus.unsubscribe_in_memory(queue)


async def _handle_autosave_event(payload: Dict[str, Any]) -> None:
    """Handle document autosave events.

    Creates or updates document nodes and references from thread nodes.

    Payload expected:
    {
        "thread_id": str,
        "document_id": str,
        "user_id": str,
        "content_length": int,
    }
    """
    try:
        thread_id = payload.get("thread_id")
        document_id = payload.get("document_id")
        user_id = payload.get("user_id")

        if not (thread_id and document_id and user_id):
            logger.warning(f"Incomplete autosave payload: {payload}")
            return

        store = get_graph_store()

        # Upsert document node
        doc_node = GraphNode(
            id=document_id,
            type="document",
            label=f"Document {document_id[:8]}",
            metadata={
                "autosaved_by": user_id,
                "content_length": payload.get("content_length", 0),
                "last_autosave": datetime.now(timezone.utc).isoformat(),
            },
        )
        store.upsert_node(doc_node)

        # Ensure thread node exists
        thread_node = store.get_node(f"thread:{thread_id}")
        if not thread_node:
            thread_node = GraphNode(
                id=thread_id,
                type="thread",
                label=f"Thread {thread_id[:8]}",
                metadata={},
            )
            store.upsert_node(thread_node)

        # Create edge from thread to document
        edge = GraphEdge(
            source=f"thread:{thread_id}",
            target=f"document:{document_id}",
            relation="contains",
            metadata={
                "created_by": user_id,
            },
        )
        store.add_edge(edge)

        # Create edge from user to document
        user_node = store.get_node(f"user:{user_id}")
        if not user_node:
            user_node = GraphNode(
                id=user_id,
                type="user",
                label=f"User {user_id[:8]}",
                metadata={},
            )
            store.upsert_node(user_node)

        author_edge = GraphEdge(
            source=f"user:{user_id}",
            target=f"document:{document_id}",
            relation="authored",
            metadata={
                "last_edit": datetime.now(timezone.utc).isoformat(),
            },
        )
        store.add_edge(author_edge)

        logger.info(
            f"Updated graph for autosave: thread={thread_id}, doc={document_id}"
        )

    except Exception as e:
        logger.error(f"Error handling autosave event: {e}", exc_info=True)


async def _handle_collab_event(payload: Dict[str, Any]) -> None:
    """Handle collaboration events.

    Tracks user presence and collaboration relationships.

    Payload expected:
    {
        "document_id": str,
        "user_id": str,
        "action": "join" | "leave" | "edit",
        "thread_id": optional str,
    }
    """
    try:
        document_id = payload.get("document_id")
        user_id = payload.get("user_id")
        action = payload.get("action")

        if not (document_id and user_id):
            logger.warning(f"Incomplete collab payload: {payload}")
            return

        store = get_graph_store()

        # Ensure document and user nodes exist
        doc_node = store.get_node(f"document:{document_id}")
        if not doc_node:
            doc_node = GraphNode(
                id=document_id,
                type="document",
                label=f"Document {document_id[:8]}",
                metadata={},
            )
            store.upsert_node(doc_node)

        user_node = store.get_node(f"user:{user_id}")
        if not user_node:
            user_node = GraphNode(
                id=user_id,
                type="user",
                label=f"User {user_id[:8]}",
                metadata={},
            )
            store.upsert_node(user_node)

        # Create or update collaboration edge
        if action == "join":
            collab_edge = GraphEdge(
                source=f"user:{user_id}",
                target=f"document:{document_id}",
                relation="collaborates_with",
                metadata={
                    "joined_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            store.add_edge(collab_edge)

        logger.info(
            f"Updated graph for collab: user={user_id}, doc={document_id}, action={action}"
        )

    except Exception as e:
        logger.error(f"Error handling collab event: {e}", exc_info=True)


async def _handle_diff_applied_event(payload: Dict[str, Any]) -> None:
    """Handle federation diff applied events.

    Updates document nodes with diff metadata and tracks authorship.

    Payload expected:
    {
        "doc_id": str,
        "version": int,
        "author": str,
        "forwarded_to": int,
    }
    """
    try:
        doc_id = payload.get("doc_id")
        version = payload.get("version")
        author = payload.get("author")

        if not doc_id:
            logger.warning(f"Incomplete diff payload: {payload}")
            return

        store = get_graph_store()

        # Ensure document node exists
        doc_node = store.get_node(f"document:{doc_id}")
        if doc_node:
            # Update with diff info
            if not doc_node.metadata:
                doc_node.metadata = {}
            doc_node.metadata["latest_version"] = version
            doc_node.metadata["latest_diff_author"] = author
            doc_node.metadata["last_diff_applied"] = datetime.now(
                timezone.utc
            ).isoformat()
            store.upsert_node(doc_node)

            # If author is a node ID, create edge
            if author and author.startswith("node-"):
                # This is a remote node
                author_node = store.get_node(f"connector:{author}")
                if not author_node:
                    author_node = GraphNode(
                        id=author,
                        type="connector",
                        label=f"Node {author[:8]}",
                        metadata={
                            "node_id": author,
                        },
                    )
                    store.upsert_node(author_node)

                diff_edge = GraphEdge(
                    source=f"connector:{author}",
                    target=f"document:{doc_id}",
                    relation="mirrors",
                    metadata={
                        "version": version,
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                store.add_edge(diff_edge)

        logger.info(
            f"Updated graph for diff: doc={doc_id}, version={version}, author={author}"
        )

    except Exception as e:
        logger.error(f"Error handling diff applied event: {e}", exc_info=True)


async def _handle_session_accepted_event(payload: Dict[str, Any]) -> None:
    """Handle federation session accepted events.

    Creates edges between nodes to track federation relationships.

    Payload expected:
    {
        "relay_id": str,
        "source_node_id": str,
        "target_node_id": str,
        "document_id": str,
    }
    """
    try:
        source_node_id = payload.get("source_node_id")
        target_node_id = payload.get("target_node_id")
        document_id = payload.get("document_id")

        if not (source_node_id and target_node_id):
            logger.warning(f"Incomplete session payload: {payload}")
            return

        store = get_graph_store()

        # Ensure connector nodes exist
        for node_id in [source_node_id, target_node_id]:
            connector_node = store.get_node(f"connector:{node_id}")
            if not connector_node:
                connector_node = GraphNode(
                    id=node_id,
                    type="connector",
                    label=f"Node {node_id[:8]}",
                    metadata={
                        "node_id": node_id,
                    },
                )
                store.upsert_node(connector_node)

        # Create federation edge
        fed_edge = GraphEdge(
            source=f"connector:{source_node_id}",
            target=f"connector:{target_node_id}",
            relation="collaborates_with",
            metadata={
                "document_id": document_id,
                "session_started": datetime.now(timezone.utc).isoformat(),
            },
        )
        store.add_edge(fed_edge)

        logger.info(
            f"Updated graph for federation: {source_node_id} -> {target_node_id}"
        )

    except Exception as e:
        logger.error(
            f"Error handling session accepted event: {e}", exc_info=True
        )
