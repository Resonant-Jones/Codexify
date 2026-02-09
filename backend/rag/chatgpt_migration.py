"""ChatGPT export migration into Postgres and the vector store."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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


def _parse_export_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    # Some exports provide milliseconds, normalize to seconds.
    if ts > 1_000_000_000_000:
        ts = ts / 1000.0
    try:
        return datetime.fromtimestamp(ts, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _extract_text_content(content: Dict[str, Any]) -> str:
    content_parts = content.get("parts") or []
    text_content = ""
    for part in content_parts:
        if isinstance(part, str):
            text_content += part
        elif isinstance(part, dict):
            part_text = part.get("text")
            if isinstance(part_text, str):
                text_content += part_text
    if not text_content.strip():
        fallback_text = content.get("text")
        if isinstance(fallback_text, str):
            text_content = fallback_text
    return text_content


def _map_role(raw_role: Any) -> Tuple[str, Optional[str]]:
    role = str(raw_role or "").strip().lower()
    if role in {"assistant", "user", "system", "tool"}:
        return role, None
    if role:
        # Keep unknown roles visible while mapping to a safe canonical role.
        return "tool", role
    return "system", None


def _resolve_active_node(
    mapping: Dict[str, Any], current_node: Any
) -> Optional[str]:
    if isinstance(current_node, str) and current_node in mapping:
        return current_node

    # Deterministic fallback: select leaf with message payload, then lexical id.
    children: Dict[str, int] = dict.fromkeys(mapping.keys(), 0)
    for node in mapping.values():
        parent = node.get("parent") if isinstance(node, dict) else None
        if isinstance(parent, str) and parent in children:
            children[parent] += 1
    leaves = sorted(
        [
            node_id
            for node_id, child_count in children.items()
            if child_count == 0 and mapping.get(node_id, {}).get("message")
        ]
    )
    if leaves:
        return leaves[-1]
    all_ids = sorted(mapping.keys())
    return all_ids[-1] if all_ids else None


def _linearize_mainline(
    mapping: Dict[str, Any], current_node: Any
) -> List[Tuple[str, Dict[str, Any]]]:
    active_node = _resolve_active_node(mapping, current_node)
    if not active_node:
        return []

    chain: List[Tuple[str, Dict[str, Any]]] = []
    seen: set[str] = set()
    node_id = active_node
    while (
        isinstance(node_id, str) and node_id in mapping and node_id not in seen
    ):
        seen.add(node_id)
        node = mapping[node_id]
        if isinstance(node, dict):
            chain.append((node_id, node))
            parent = node.get("parent")
            node_id = parent if isinstance(parent, str) else ""
            continue
        break
    chain.reverse()
    return chain


def _find_existing_thread_for_source(
    chatlog_db, user_id: str, source_thread_id: str
) -> Optional[int]:
    if not source_thread_id or not hasattr(chatlog_db, "_connect"):
        return None
    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT cm.thread_id
                FROM chat_messages cm
                JOIN chat_threads ct ON ct.id = cm.thread_id
                WHERE ct.user_id = %s
                  AND cm.extra_meta->>'source_thread_id' = %s
                ORDER BY cm.id ASC
                LIMIT 1
                """,
                (user_id, source_thread_id),
            )
            row = cur.fetchone()
            return int(row["thread_id"]) if row else None
    except Exception:
        return None


def _find_existing_message_for_source(
    chatlog_db, thread_id: int, source_message_id: str
) -> Optional[Dict[str, Any]]:
    if not source_message_id or not hasattr(chatlog_db, "_connect"):
        return None
    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, extra_meta
                FROM chat_messages
                WHERE thread_id = %s
                  AND extra_meta->>'source_message_id' = %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (thread_id, source_message_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def _create_message_with_fallback(
    chatlog_db,
    thread_id: int,
    role: str,
    content: str,
    created_at: datetime,
) -> int:
    try:
        return chatlog_db.create_message(
            thread_id,
            role,
            content,
            created_at=created_at.isoformat(),
        )
    except TypeError:
        return chatlog_db.create_message(thread_id, role, content)


def _merge_temporal_meta(
    existing_meta: Dict[str, Any], new_meta: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(existing_meta or {})
    for key, value in new_meta.items():
        if key == "imported_at" and merged.get(key):
            continue
        if key == "turn_index" and merged.get(key) is not None:
            continue
        if merged.get(key) is None:
            merged[key] = value
            continue
        if key not in merged:
            merged[key] = value
    for key, value in new_meta.items():
        if key not in merged:
            merged[key] = value
    return merged


def _persist_temporal_metadata(
    chatlog_db,
    message_id: int,
    merged_meta: Dict[str, Any],
    source_created_at: datetime,
) -> None:
    if not hasattr(chatlog_db, "_connect"):
        return
    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chat_messages
                SET event_at = COALESCE(event_at, %s),
                    extra_meta = %s::jsonb
                WHERE id = %s
                """,
                (
                    source_created_at.isoformat(),
                    json.dumps(merged_meta),
                    message_id,
                ),
            )
    except Exception as exc:
        logger.warning(
            "Unable to persist temporal metadata for message %s: %s",
            message_id,
            exc,
        )


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

            source_thread_id = str(
                conv.get("id") or conv.get("conversation_id") or ""
            )
            conversation_created_at = _parse_export_timestamp(
                conv.get("create_time")
            ) or _parse_export_timestamp(conv.get("update_time"))
            imported_at = datetime.now(timezone.utc)

            # Linearize canonical mainline (root -> active leaf).
            mainline_nodes = _linearize_mainline(
                mapping, conv.get("current_node")
            )
            messages = []
            for turn_index, (node_id, node) in enumerate(mainline_nodes):
                message = node.get("message")
                if not message:
                    continue

                author = message.get("author", {})
                raw_role = author.get("role") or message.get("role")
                content = message.get("content") or {}
                create_time = message.get("create_time")

                text_content = _extract_text_content(content)

                if not text_content.strip():
                    continue

                guardian_role, source_role_raw = _map_role(raw_role)
                message_created_at = _parse_export_timestamp(create_time)
                source_created_at_inferred = False
                if not message_created_at:
                    message_created_at = conversation_created_at
                if not message_created_at:
                    message_created_at = imported_at
                    source_created_at_inferred = True

                messages.append(
                    {
                        "role": guardian_role,
                        "content": text_content,
                        "source_created_at": message_created_at,
                        "source_created_at_inferred": source_created_at_inferred,
                        "imported_at": imported_at,
                        "source_thread_id": source_thread_id,
                        "source_message_id": str(node_id),
                        "turn_index": turn_index,
                        "source_role_raw": source_role_raw,
                        "origin": "chatgpt_import",
                        "era": "pre_codexify",
                    }
                )

            # Avoid creating empty threads for malformed/empty conversations.
            if not messages:
                continue

            # Extract thread metadata
            title = conv.get("title") or "Imported Chat"
            thread_id = _find_existing_thread_for_source(
                chatlog_db, user_id=user_id, source_thread_id=source_thread_id
            )
            if thread_id is None:
                # Resolve Imports project ID (create if missing to avoid FK error)
                imports_project_id = _resolve_imports_project_id(chatlog_db)
                thread_record = chatlog_db.create_chat_thread(
                    user_id=user_id,
                    title=title,
                    summary="Imported from ChatGPT",
                    project_id=imports_project_id,
                )
                thread_id = int(thread_record["id"])
                threads_count += 1

            # Insert messages
            for msg in messages:
                source_message_id = msg["source_message_id"]
                existing = _find_existing_message_for_source(
                    chatlog_db,
                    thread_id=thread_id,
                    source_message_id=source_message_id,
                )
                temporal_meta = {
                    "source_thread_id": msg["source_thread_id"],
                    "source_message_id": source_message_id,
                    "turn_index": msg["turn_index"],
                    "source_created_at": msg["source_created_at"].isoformat(),
                    "source_created_at_inferred": msg[
                        "source_created_at_inferred"
                    ],
                    "imported_at": msg["imported_at"].isoformat(),
                    "role": msg["role"],
                    "origin": msg["origin"],
                    "era": msg["era"],
                }
                if msg["source_role_raw"]:
                    temporal_meta["source_role_raw"] = msg["source_role_raw"]

                if existing:
                    mid = int(existing["id"])
                    existing_meta = existing.get("extra_meta") or {}
                    merged_meta = _merge_temporal_meta(
                        existing_meta, temporal_meta
                    )
                else:
                    mid = _create_message_with_fallback(
                        chatlog_db,
                        thread_id=thread_id,
                        role=msg["role"],
                        content=msg["content"],
                        created_at=msg["source_created_at"],
                    )
                    messages_count += 1
                    merged_meta = temporal_meta

                _persist_temporal_metadata(
                    chatlog_db,
                    message_id=mid,
                    merged_meta=merged_meta,
                    source_created_at=msg["source_created_at"],
                )

                # Embed message
                if _vector_store and not existing:
                    try:
                        meta = {
                            "thread_id": thread_id,
                            "role": msg["role"],
                            "message_id": mid,
                            "timestamp": msg["source_created_at"].isoformat(),
                            "source_thread_id": msg["source_thread_id"],
                            "source_message_id": source_message_id,
                            "turn_index": msg["turn_index"],
                            "source_created_at_inferred": msg[
                                "source_created_at_inferred"
                            ],
                            "origin": msg["origin"],
                            "era": msg["era"],
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
