"""ChatGPT export migration into Postgres and the vector store."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guardian.core import dependencies

logger = logging.getLogger(__name__)


def _detect_non_json_hint(content: bytes) -> Optional[str]:
    raw = content.lstrip()
    if not raw:
        return "Uploaded file is empty."
    if raw.startswith(b"PK\x03\x04"):
        return (
            "Uploaded file appears to be a ZIP archive. "
            "Extract and upload the JSON export file content."
        )
    if raw.startswith(b"<"):
        return (
            "Uploaded file appears to be HTML. "
            "This importer only supports ChatGPT JSON exports."
        )
    return None


def _validate_chatgpt_export_payload(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError(
            "Invalid export format: expected a JSON array of conversations."
        )

    if not data:
        return []

    dict_items = [item for item in data if isinstance(item, dict)]
    if not dict_items:
        raise ValueError(
            "Invalid export format: expected conversation objects in the JSON array."
        )

    with_mapping = [
        item for item in dict_items if isinstance(item.get("mapping"), dict)
    ]
    if with_mapping:
        return dict_items

    first = dict_items[0]
    shared_keys = {"id", "conversation_id", "title", "is_anonymous"}
    if shared_keys.issubset(set(first.keys())):
        raise ValueError(
            "Unsupported ChatGPT export file: this looks like shared_conversations metadata. "
            "Use the full conversations JSON export (contains a 'mapping' field)."
        )

    raise ValueError(
        "Invalid export format: no conversation objects with a 'mapping' field were found."
    )


def _resolve_imports_project_id(chatlog_db) -> int:
    try:
        return chatlog_db.ensure_project(
            "Imports", "Default bucket for imported threads"
        )
    except Exception as e:
        logger.warning(
            "Failed to ensure Imports project during migration: %s",
            e,
        )
    try:
        projects = chatlog_db.list_projects()
        imports = [p for p in projects if p.get("name") == "Imports"]
        imports_ids = [int(p["id"]) for p in imports if p.get("id") is not None]
        if imports_ids:
            return min(imports_ids)

        legacy = [p for p in projects if p.get("name") == "Loose Threads"]
        legacy_ids = [int(p["id"]) for p in legacy if p.get("id") is not None]
        if legacy_ids:
            return min(legacy_ids)
    except Exception as e:
        logger.warning(
            "Failed to resolve Imports/Loose Threads project ID via list_projects: %s",
            e,
        )
    raise RuntimeError("Unable to resolve Loose Threads project ID")


def ingest_chatgpt_export(
    content: bytes, user_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Ingest a ChatGPT export (JSON bytes) into the database and vector store.
    Returns stats: {"threads": count, "messages": count}.
    """
    if not user_id:
        raise ValueError(
            "ingest_chatgpt_export requires a valid user_id (got None or empty)"
        )

    chatlog_db = dependencies.chatlog_db
    _vector_store = dependencies._vector_store

    if not chatlog_db:
        # Try to init if not ready (e.g. in tests)
        chatlog_db = dependencies.init_database()

    if not chatlog_db:
        raise RuntimeError("Database not available")

    # Initialize vector store if not already done
    if not _vector_store:
        from guardian.vector.store import VectorStore

        _vector_store = VectorStore()
        dependencies._vector_store = _vector_store
        logger.info("Initialized VectorStore for migration")

    hint = _detect_non_json_hint(content)
    if hint:
        raise ValueError(hint)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON file: unable to parse uploaded content.")

    data = _validate_chatgpt_export_payload(parsed)

    threads_count = 0
    messages_count = 0

    for conv in data:
        try:
            if not user_id:
                raise RuntimeError(
                    "User identity lost during ChatGPT import loop"
                )

            # Process messages
            mapping = conv.get("mapping", {})
            if not isinstance(mapping, dict):
                logger.warning("Skipping conversation with non-dict mapping")
                continue

            # Linearize messages
            messages = []
            for _node_id, node in mapping.items():
                message = node.get("message")
                if not message:
                    continue

                author = message.get("author", {})
                role = author.get("role") or message.get("role")
                content = message.get("content") or {}
                content_parts = content.get("parts") or []
                create_time = message.get("create_time")

                if not role:
                    continue

                text_content = ""
                for part in content_parts:
                    if isinstance(part, str):
                        text_content += part
                    elif isinstance(part, dict):
                        part_text = part.get("text")
                        if isinstance(part_text, str):
                            text_content += part_text

                if not text_content.strip():
                    # Some exports store code/tool output under content.text.
                    fallback_text = content.get("text")
                    if isinstance(fallback_text, str):
                        text_content = fallback_text

                if not text_content.strip():
                    continue

                # Map roles
                if role == "assistant":
                    guardian_role = "assistant"
                elif role == "user":
                    guardian_role = "user"
                elif role == "system":
                    guardian_role = "system"
                else:
                    guardian_role = "user"

                messages.append(
                    {
                        "role": guardian_role,
                        "content": text_content,
                        "timestamp": create_time or 0,
                    }
                )

            # Sort by timestamp
            messages.sort(key=lambda x: x["timestamp"])

            # Avoid creating empty threads for malformed/empty conversations.
            if not messages:
                continue

            # Extract thread metadata
            title = conv.get("title") or "Imported Chat"

            # Resolve Imports project ID (create if missing to avoid FK error)
            imports_project_id = _resolve_imports_project_id(chatlog_db)

            # Create thread
            thread_record = chatlog_db.create_chat_thread(
                user_id=user_id,
                title=title,
                summary="Imported from ChatGPT",
                project_id=imports_project_id,
            )
            thread_id = thread_record["id"]
            threads_count += 1

            # Insert messages
            for msg in messages:
                mid = chatlog_db.create_message(
                    thread_id, msg["role"], msg["content"]
                )
                messages_count += 1

                # Embed message
                if _vector_store:
                    try:
                        meta = {
                            "thread_id": thread_id,
                            "role": msg["role"],
                            "message_id": mid,
                            "timestamp": (
                                datetime.fromtimestamp(
                                    msg["timestamp"], timezone.utc
                                ).isoformat()
                                if msg["timestamp"]
                                else datetime.now(timezone.utc).isoformat()
                            ),
                            "source": "chatgpt_import",
                        }
                        _vector_store.add_texts(
                            [{"text": msg["content"], "meta": meta}]
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to embed imported message {mid}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to import conversation: {e}")
            continue

    return {
        "threads_imported": threads_count,
        "messages_imported": messages_count,
    }
