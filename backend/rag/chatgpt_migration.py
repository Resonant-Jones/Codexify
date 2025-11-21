"""
ChatGPT Migration Module - Dual Ingestion
==========================================

Provides reusable functions for parsing ChatGPT conversation exports and
ingesting them into both Neo4j (graph) and Chroma (vector store).

This module is used by:
- The CLI import script (scripts/chatgpt_import/import_chatgpt.py)
- The HTTP endpoint for drag-and-drop ChatGPT import (guardian/routes/rag_upload.py)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def parse_chatgpt_export(raw_bytes: bytes) -> Iterable[Dict[str, Any]]:
    """
    Parse a ChatGPT-style export (OpenAI conversations JSON) into normalized conversations.

    Args:
        raw_bytes: Raw bytes of a ChatGPT export JSON file

    Returns:
        Iterable of normalized conversations with structure:
        [
          {
            "thread_id": str,
            "title": str | None,
            "messages": [
              {
                "id": str,
                "parent_id": str | None,
                "role": str,
                "content": str,
                "timestamp": float | None,
              }, ...
            ]
          }, ...
        ]

    Raises:
        ValueError: If the export cannot be parsed or is invalid
    """
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse ChatGPT export JSON: {e}")

    # Handle both array format and single conversation format
    if isinstance(data, dict):
        conversations = [data]
    elif isinstance(data, list):
        conversations = data
    else:
        raise ValueError("ChatGPT export must be a JSON object or array")

    normalized = []

    for convo in conversations:
        # Extract thread info
        thread_id = convo.get("id") or convo.get("conversation_id")
        if not thread_id:
            # Generate a fallback ID if none exists
            thread_id = f"thread_{hash(str(convo))}"

        title = convo.get("title", "Untitled Thread")
        create_time = convo.get("create_time")
        update_time = convo.get("update_time")

        # Parse messages from the mapping structure
        mapping = convo.get("mapping", {})
        messages = []

        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue

            # Extract message content
            message_id = msg.get("id", node_id)
            content_obj = msg.get("content", {})

            # Handle different content formats
            if isinstance(content_obj, dict):
                parts = content_obj.get("parts", [])
            elif isinstance(content_obj, list):
                parts = content_obj
            else:
                parts = [str(content_obj)] if content_obj else []

            # Join all parts into single content string
            content = "\n".join(str(part) for part in parts if part)

            # Skip empty messages
            if not content.strip():
                continue

            # Extract metadata
            author = msg.get("author", {})
            role = author.get("role", "unknown") if isinstance(author, dict) else str(author)
            author_name = author.get("name", role) if isinstance(author, dict) else role

            # Extract parent relationship
            parent_id = node.get("parent")
            # Resolve parent to actual message ID if it exists in mapping
            if parent_id and parent_id in mapping:
                parent_msg = mapping[parent_id].get("message")
                if parent_msg:
                    parent_id = parent_msg.get("id", parent_id)
                else:
                    parent_id = None
            else:
                parent_id = None

            # Normalize timestamp
            timestamp = msg.get("create_time")

            messages.append({
                "id": message_id,
                "parent_id": parent_id,
                "role": role,
                "author_name": author_name,
                "content": content,
                "timestamp": timestamp,
            })

        normalized.append({
            "thread_id": thread_id,
            "title": title,
            "create_time": create_time,
            "update_time": update_time,
            "messages": messages,
        })

    return normalized


def _normalize_timestamp(ts: Any) -> str:
    """
    Normalize various timestamp formats to ISO format.

    Args:
        ts: Timestamp (unix timestamp, ISO string, or None)

    Returns:
        ISO formatted timestamp string
    """
    if ts is None:
        return datetime.utcnow().isoformat()

    try:
        # Try parsing as unix timestamp
        if isinstance(ts, (int, float)):
            return datetime.utcfromtimestamp(ts).isoformat()
        # Try parsing as ISO string
        elif isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00')).isoformat()
        else:
            return datetime.utcnow().isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def ingest_chatgpt_export(
    raw_bytes: bytes,
    user_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    Ingest a ChatGPT export into both Neo4j (graph) and Chroma (vector store).

    This function:
    1. Parses the export via parse_chatgpt_export()
    2. Writes threads/messages into Neo4j with proper relationships
    3. Embeds messages into Chroma via the existing embedder abstraction

    Args:
        raw_bytes: Raw bytes of the ChatGPT export JSON file
        user_id: Optional user ID to associate with the imported data

    Returns:
        Statistics dictionary:
        {
            "threads_imported": int,
            "messages_imported": int,
        }

    Raises:
        ValueError: If the export cannot be parsed
        RuntimeError: If Neo4j or Chroma operations fail
    """
    # Parse the export
    logger.info("Parsing ChatGPT export...")
    conversations = list(parse_chatgpt_export(raw_bytes))
    logger.info(f"Parsed {len(conversations)} conversation(s)")

    stats = {
        "threads_imported": 0,
        "messages_imported": 0,
    }

    # Phase 1: Import to Neo4j
    logger.info("Starting Neo4j import...")
    try:
        from guardian.db.neo import get_session

        with get_session() as session:
            for convo in conversations:
                thread_id = convo["thread_id"]
                title = convo["title"]
                create_time = _normalize_timestamp(convo.get("create_time"))
                update_time = _normalize_timestamp(convo.get("update_time"))

                # Create thread node
                session.run(
                    """
                    MERGE (t:Thread {id: $id})
                    SET t.title = $title,
                        t.created_at = $created_at,
                        t.updated_at = $updated_at
                    """,
                    {
                        "id": thread_id,
                        "title": title,
                        "created_at": create_time,
                        "updated_at": update_time,
                    },
                )
                stats["threads_imported"] += 1

                # Create messages and relationships
                for msg in convo["messages"]:
                    message_id = msg["id"]
                    role = msg["role"]
                    content = msg["content"]
                    author_name = msg.get("author_name", role)
                    created = _normalize_timestamp(msg.get("timestamp"))

                    # Create message node
                    session.run(
                        """
                        MERGE (m:Message {id: $mid})
                        SET m.role = $role,
                            m.content = $content,
                            m.created_at = $created,
                            m.author_name = $author_name
                        """,
                        {
                            "mid": message_id,
                            "role": role,
                            "content": content,
                            "created": created,
                            "author_name": author_name,
                        },
                    )
                    stats["messages_imported"] += 1

                    # Link message to thread
                    session.run(
                        """
                        MATCH (t:Thread {id: $tid}), (m:Message {id: $mid})
                        MERGE (t)-[:CONTAINS]->(m)
                        """,
                        {"tid": thread_id, "mid": message_id},
                    )

                    # Create author node and relationship
                    if author_name:
                        session.run(
                            """
                            MERGE (a:Author {name: $name, role: $role})
                            WITH a
                            MATCH (m:Message {id: $mid})
                            MERGE (a)-[:AUTHORED]->(m)
                            """,
                            {"name": author_name, "role": role, "mid": message_id},
                        )

                    # Create parent-child relationships
                    parent_id = msg.get("parent_id")
                    if parent_id:
                        session.run(
                            """
                            MATCH (p:Message {id: $parent}), (c:Message {id: $child})
                            MERGE (p)-[:REPLIED_WITH]->(c)
                            """,
                            {"parent": parent_id, "child": message_id},
                        )

        logger.info(f"Neo4j import complete: {stats['threads_imported']} threads, {stats['messages_imported']} messages")

    except Exception as e:
        logger.error(f"Neo4j import failed: {e}")
        raise RuntimeError(f"Failed to import to Neo4j: {e}")

    # Phase 2: Import to Chroma
    logger.info("Starting Chroma import...")
    try:
        from guardian.runtime.embed.embedder import CodexifyEmbedder
        import os

        # Collect all messages for embedding
        all_messages = []
        for convo in conversations:
            thread_id = convo["thread_id"]
            for msg in convo["messages"]:
                message_id = msg["id"]
                content = msg["content"]
                role = msg["role"]
                timestamp = msg.get("timestamp")

                all_messages.append({
                    "id": f"chatgpt::{message_id}",
                    "content": content,
                    "metadata": {
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "role": role,
                        "timestamp": _normalize_timestamp(timestamp),
                        "source": "chatgpt_export",
                        "user_id": user_id or "unknown",
                    },
                })

        if all_messages:
            # Use OpenAI embeddings if available, otherwise fall back to local
            use_openai = bool(os.getenv("OPENAI_API_KEY"))
            chroma_path = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
            collection_name = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")

            embedder = CodexifyEmbedder(
                use_openai=use_openai,
                store="chroma",
                chroma_path=chroma_path,
                collection=collection_name,
            )

            # Embed and index
            docs = [msg["content"] for msg in all_messages]
            metadatas = [msg["metadata"] for msg in all_messages]
            ids_prefix = "chatgpt"

            # The CodexifyEmbedder.embed_and_index method uses auto-generated IDs,
            # but we want to use our custom IDs. So we'll use the lower-level API:
            vectors = embedder.embed_texts(docs)

            # Store directly in Chroma with our custom IDs
            import chromadb
            client = chromadb.PersistentClient(path=chroma_path)
            collection = client.get_or_create_collection(name=collection_name)

            # Use our custom IDs
            custom_ids = [msg["id"] for msg in all_messages]
            collection.upsert(
                ids=custom_ids,
                embeddings=vectors,
                documents=docs,
                metadatas=metadatas,
            )

            logger.info(f"Chroma import complete: {len(all_messages)} messages embedded")
        else:
            logger.warning("No messages to embed")

    except Exception as e:
        logger.warning(f"Chroma import failed (graph data was saved): {e}")
        # Don't raise - graph import already succeeded

    return stats
