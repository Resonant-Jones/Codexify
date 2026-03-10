"""ChatGPT export migration into Postgres and the vector store."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from guardian.core import dependencies

logger = logging.getLogger(__name__)

_CHATGPT_IMPORT_PROFILE = "chatgpt_v1_canonical"
_FILTERED_CONTENT_TYPES = {
    "model_editable_context",
    "thoughts",
    "reasoning_recap",
}


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
    text_segments: list[str] = []
    for part in content_parts:
        if isinstance(part, str):
            text_segments.append(part)
        elif isinstance(part, dict):
            part_text = part.get("text")
            if isinstance(part_text, str):
                text_segments.append(part_text)
    text_content = "\n".join([segment for segment in text_segments if segment])
    if not text_content.strip():
        fallback_text = content.get("text")
        if isinstance(fallback_text, str):
            text_content = fallback_text
    return text_content


def _extract_multimodal_content(content: Dict[str, Any]) -> str:
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    rendered: list[str] = []
    for part in parts:
        if isinstance(part, str):
            if part.strip():
                rendered.append(part)
            continue
        if not isinstance(part, dict):
            continue

        part_type = str(part.get("content_type") or "").strip().lower()
        if part_type == "image_asset_pointer":
            metadata = part.get("metadata")
            if isinstance(metadata, dict):
                dalle_prompt = metadata.get("dalle_prompt")
                dalle_block = metadata.get("dalle")
                if isinstance(dalle_block, dict):
                    dalle_prompt = dalle_prompt or dalle_block.get("prompt")
                if isinstance(dalle_prompt, str) and dalle_prompt.strip():
                    rendered.append(f"[DALL-E Image: {dalle_prompt.strip()}]")
                    continue
            rendered.append("[Image]")
            continue
        if part_type == "code_interpreter_output":
            output = part.get("output") or part.get("text")
            if isinstance(output, str) and output.strip():
                rendered.append(f"```output\n{output.strip()}\n```")
                continue
        if part_type == "audio_transcription":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                rendered.append(f"[Audio transcription]\n{text.strip()}")
                continue

        text = part.get("text")
        if isinstance(text, str) and text.strip():
            rendered.append(text)

    return "\n".join(rendered)


def _extract_user_editable_context(content: Dict[str, Any]) -> str:
    text = content.get("text")
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""

    wrappers = (
        "The user provided the following information about themselves:",
        "The user provided the additional info about how they would like you to respond:",
    )
    for wrapper in wrappers:
        cleaned = cleaned.replace(wrapper, "").strip()
    return cleaned


def _contains_dalle_image(content: Dict[str, Any]) -> bool:
    if str(content.get("content_type") or "") != "multimodal_text":
        return False
    parts = content.get("parts")
    if not isinstance(parts, list):
        return False
    for part in parts:
        if not isinstance(part, dict):
            continue
        if str(part.get("content_type") or "") != "image_asset_pointer":
            continue
        metadata = part.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("dalle_prompt"):
            return True
        dalle_block = metadata.get("dalle")
        if isinstance(dalle_block, dict) and dalle_block.get("prompt"):
            return True
    return False


def _is_user_system_message(message: Dict[str, Any]) -> bool:
    metadata = message.get("metadata")
    if isinstance(metadata, dict) and metadata.get("is_user_system_message"):
        return True
    content = message.get("content")
    if (
        isinstance(content, dict)
        and content.get("content_type") == "user_editable_context"
    ):
        return True
    return False


def _canonicalize_message_role(
    raw_role: Any, content: Dict[str, Any]
) -> Tuple[str, Optional[str]]:
    role, source_role_raw = _map_role(raw_role)
    # Tool messages that include DALL-E payloads should read as assistant output.
    if role == "tool" and _contains_dalle_image(content):
        return "assistant", source_role_raw
    return role, source_role_raw


def _should_filter_message(
    *,
    raw_role: str,
    content: Dict[str, Any],
    message: Dict[str, Any],
) -> Optional[str]:
    metadata = message.get("metadata")
    if isinstance(metadata, dict) and metadata.get(
        "is_visually_hidden_from_conversation"
    ):
        return "visually_hidden"

    content_type = str(content.get("content_type") or "").strip().lower()
    if content_type in _FILTERED_CONTENT_TYPES:
        return f"content_type: {content_type}"

    if raw_role == "system" and not _is_user_system_message(message):
        return "internal_system"

    if raw_role == "tool" and not _contains_dalle_image(content):
        return "tool_noise"

    if (
        raw_role == "assistant"
        and content_type == "text"
        and content.get("parts") == [""]
    ):
        return "assistant_placeholder"

    return None


def _extract_canonical_content(
    *,
    content: Dict[str, Any],
    raw_role: str,
) -> str:
    content_type = str(content.get("content_type") or "").strip().lower()

    if content_type in {"", "text"}:
        return _extract_text_content(content)

    if content_type == "code":
        code = content.get("text")
        if isinstance(code, str) and code.strip():
            language = str(content.get("language") or "").strip()
            return (
                f"```{language}\n{code.strip()}\n```"
                if language
                else f"```\n{code.strip()}\n```"
            )
        return ""

    if content_type == "execution_output":
        output = content.get("text")
        if isinstance(output, str) and output.strip():
            return f"```output\n{output.strip()}\n```"
        return ""

    if content_type == "multimodal_text":
        return _extract_multimodal_content(content)

    if content_type == "user_editable_context":
        return _extract_user_editable_context(content)

    if content_type == "tether_browsing_display":
        result = content.get("result")
        return result if isinstance(result, str) else ""

    if content_type == "tether_quote":
        lines: list[str] = []
        title = content.get("title")
        if isinstance(title, str) and title.strip():
            lines.append(f"**{title.strip()}**")
        quote = content.get("text")
        if isinstance(quote, str) and quote.strip():
            lines.append(f"> {quote.strip()}")
        url = content.get("url")
        if isinstance(url, str) and url.strip():
            lines.append(f"Source: {url.strip()}")
        return "\n".join(lines)

    if content_type == "sonic_webpage":
        text = content.get("text")
        url = content.get("url")
        if isinstance(text, str) and text.strip():
            if isinstance(url, str) and url.strip():
                return f"[Web Content from {url.strip()}]\n{text.strip()}"
            return text.strip()

    # Fallback for unknown content types: retain plain text when possible.
    fallback = _extract_text_content(content)
    if fallback.strip():
        return fallback

    text = content.get("text")
    if isinstance(text, str):
        return text

    # Tool role fallback may still have useful rendered parts.
    if raw_role == "tool":
        return _extract_multimodal_content(content)

    return ""


def _normalize_template_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate.startswith("g-p-"):
        return None
    return candidate


def _slugify_title_for_project(title: Any) -> str:
    text = str(title or "").strip()
    if not text:
        return "Project"
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return "Project"
    friendly = " ".join(words[:6]).strip()
    if len(friendly) > 42:
        friendly = friendly[:42].rstrip()
    return friendly or "Project"


def _build_template_project_name(template_id: str, title: Any) -> str:
    suffix = template_id[-8:]
    friendly = _slugify_title_for_project(title)
    return f"ChatGPT {friendly} [{suffix}]"


def _find_project_id_by_name(chatlog_db, project_name: str) -> Optional[int]:
    try:
        projects = chatlog_db.list_projects()
    except Exception:
        return None

    for project in projects:
        if str(project.get("name") or "") != project_name:
            continue
        project_id = project.get("id")
        if project_id is None:
            continue
        try:
            return int(project_id)
        except (TypeError, ValueError):
            continue
    return None


def _find_existing_project_for_template(
    chatlog_db,
    *,
    user_id: str,
    template_id: str,
) -> Optional[int]:
    if not template_id or not hasattr(chatlog_db, "_connect"):
        return None
    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT project_id
                FROM chat_threads
                WHERE user_id = %s
                  AND project_id IS NOT NULL
                  AND metadata->>'import_source' = 'chatgpt'
                  AND metadata->>'source_conversation_template_id' = %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (user_id, template_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            project_id = row.get("project_id")
            return int(project_id) if project_id is not None else None
    except Exception:
        return None


def _ensure_template_project_id(
    chatlog_db,
    *,
    template_id: str,
    title: Any,
) -> Tuple[int, bool]:
    project_name = _build_template_project_name(template_id, title)
    existing_by_name = _find_project_id_by_name(chatlog_db, project_name)
    if existing_by_name is not None:
        return existing_by_name, False

    project_id = chatlog_db.ensure_project(
        project_name,
        f"Imported ChatGPT conversations for template {template_id}",
    )
    return int(project_id), True


def _resolve_target_project(
    chatlog_db,
    *,
    user_id: str,
    conversation: Dict[str, Any],
) -> Tuple[int, Optional[str], str]:
    template_id = _normalize_template_id(
        conversation.get("conversation_template_id")
    )
    if not template_id:
        return _resolve_imports_project_id(chatlog_db), None, "imports"

    existing_project_id = _find_existing_project_for_template(
        chatlog_db,
        user_id=user_id,
        template_id=template_id,
    )
    if existing_project_id is not None:
        return existing_project_id, template_id, "reused"

    project_id, created = _ensure_template_project_id(
        chatlog_db,
        template_id=template_id,
        title=conversation.get("title"),
    )
    return project_id, template_id, "created" if created else "reused"


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


def _build_raw_envelope(
    *,
    raw_role: str,
    content: Dict[str, Any],
    message: Dict[str, Any],
) -> Dict[str, Any]:
    metadata = (
        message.get("metadata")
        if isinstance(message.get("metadata"), dict)
        else {}
    )
    content_type = (
        str(content.get("content_type") or "").strip().lower() or None
    )
    return {
        "author_role": raw_role or None,
        "content_type": content_type,
        "is_user_system_message": bool(_is_user_system_message(message)),
        "is_visually_hidden_from_conversation": bool(
            metadata.get("is_visually_hidden_from_conversation")
        ),
    }


def _normalize_mainline_messages(
    *,
    mainline_nodes: List[Tuple[str, Dict[str, Any]]],
    source_thread_id: str,
    conversation_created_at: Optional[datetime],
    imported_at: datetime,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, int]]:
    messages: list[dict[str, Any]] = []
    filtered_count = 0
    filtered_reasons: dict[str, int] = {}

    for turn_index, (node_id, node) in enumerate(mainline_nodes):
        message = node.get("message")
        if not isinstance(message, dict):
            continue

        author = message.get("author")
        if isinstance(author, dict):
            raw_role = (
                str(author.get("role") or message.get("role") or "")
                .strip()
                .lower()
            )
        else:
            raw_role = str(message.get("role") or "").strip().lower()

        content = message.get("content")
        if not isinstance(content, dict):
            content = {}

        filter_reason = _should_filter_message(
            raw_role=raw_role,
            content=content,
            message=message,
        )
        if filter_reason:
            filtered_count += 1
            filtered_reasons[filter_reason] = (
                filtered_reasons.get(filter_reason, 0) + 1
            )
            continue

        canonical_text = _extract_canonical_content(
            content=content,
            raw_role=raw_role,
        )
        if not canonical_text.strip():
            filtered_count += 1
            filtered_reasons["empty_content"] = (
                filtered_reasons.get("empty_content", 0) + 1
            )
            continue

        create_time = message.get("create_time")
        message_created_at = _parse_export_timestamp(create_time)
        source_created_at_inferred = False
        if not message_created_at:
            message_created_at = conversation_created_at
        if not message_created_at:
            message_created_at = imported_at
            source_created_at_inferred = True

        guardian_role, source_role_raw = _canonicalize_message_role(
            raw_role, content
        )

        messages.append(
            {
                "role": guardian_role,
                "content": canonical_text,
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

    return messages, filtered_count, filtered_reasons


def _merge_thread_metadata(
    existing: Dict[str, Any] | None,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    merged = dict(existing or {})
    for key, value in updates.items():
        if value is None:
            continue
        if key not in merged or merged.get(key) in (None, ""):
            merged[key] = value
            continue
        if key == "import_summary" and isinstance(value, dict):
            existing_summary = merged.get("import_summary")
            if isinstance(existing_summary, dict):
                summary = dict(existing_summary)
                for k, v in value.items():
                    if k not in summary:
                        summary[k] = v
                    elif isinstance(v, int) and isinstance(summary.get(k), int):
                        summary[k] = max(summary[k], v)
                    elif isinstance(v, dict) and isinstance(
                        summary.get(k), dict
                    ):
                        merged_counts = dict(summary[k])
                        for rk, rv in v.items():
                            if isinstance(rv, int):
                                merged_counts[rk] = max(
                                    int(merged_counts.get(rk) or 0), rv
                                )
                        summary[k] = merged_counts
                    else:
                        summary[k] = v
                merged[key] = summary
                continue
        merged[key] = value
    return merged


def _update_thread_metadata_best_effort(
    chatlog_db,
    *,
    thread_id: int,
    updates: Dict[str, Any],
) -> None:
    try:
        get_thread = getattr(chatlog_db, "get_chat_thread", None)
        update_thread_metadata = getattr(
            chatlog_db, "update_thread_metadata", None
        )
        if not callable(get_thread) or not callable(update_thread_metadata):
            return
        thread = get_thread(thread_id)
        if not isinstance(thread, dict):
            thread = {}
        existing_metadata = thread.get("metadata")
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}
        merged = _merge_thread_metadata(existing_metadata, updates)
        update_thread_metadata(thread_id, merged)
    except Exception:
        return


def ingest_chatgpt_export(
    content: bytes, user_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Ingest a ChatGPT export (JSON bytes) into the database and vector store.
    """
    # Defense-in-depth: enforce size limit at service entry
    MAX_IMPORT_SIZE = 50 * 1024 * 1024  # 50MB
    if len(content) > MAX_IMPORT_SIZE:
        raise ValueError("Export file exceeds 50MB limit")

    if not user_id:
        raise ValueError(
            "ingest_chatgpt_export requires a valid user_id (got None or empty)"
        )

    chatlog_db = dependencies.chatlog_db

    if not chatlog_db:
        # Try to init if not ready (e.g. in tests)
        chatlog_db = dependencies.init_database()

    if not chatlog_db:
        raise RuntimeError("Database not available")

    # Use existing vector store if already initialized; do NOT eagerly initialize
    # This allows import to succeed (with DB records) even if vector store is unavailable
    _vector_store = getattr(dependencies, "_vector_store", None) or None

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
    messages_filtered = 0
    imports_project_id = int(_resolve_imports_project_id(chatlog_db))

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
            (
                messages,
                conv_filtered_count,
                filtered_reasons,
            ) = _normalize_mainline_messages(
                mainline_nodes=mainline_nodes,
                source_thread_id=source_thread_id,
                conversation_created_at=conversation_created_at,
                imported_at=imported_at,
            )
            messages_filtered += conv_filtered_count

            # Avoid creating empty threads for malformed/empty conversations.
            if not messages:
                continue

            title = str(conv.get("title") or "Imported Chat")
            template_id = _normalize_template_id(
                conv.get("conversation_template_id")
            )

            thread_id = _find_existing_thread_for_source(
                chatlog_db, user_id=user_id, source_thread_id=source_thread_id
            )
            if thread_id is None:
                project_id = imports_project_id

                thread_metadata: Dict[str, Any] = {
                    "import_source": "chatgpt",
                    "import_profile": _CHATGPT_IMPORT_PROFILE,
                    "source_thread_id": source_thread_id,
                    "import_summary": {
                        "messages_kept": len(messages),
                        "messages_filtered": conv_filtered_count,
                        "filtered_reasons": filtered_reasons,
                    },
                }
                if template_id:
                    thread_metadata[
                        "source_conversation_template_id"
                    ] = template_id
                if (
                    isinstance(conv.get("gizmo_id"), str)
                    and str(conv.get("gizmo_id")).strip()
                ):
                    thread_metadata["source_gizmo_id"] = str(
                        conv.get("gizmo_id")
                    ).strip()
                if (
                    isinstance(conv.get("gizmo_type"), str)
                    and str(conv.get("gizmo_type")).strip()
                ):
                    thread_metadata["source_gizmo_type"] = str(
                        conv.get("gizmo_type")
                    ).strip()

                try:
                    thread_record = chatlog_db.create_chat_thread(
                        user_id=user_id,
                        title=title,
                        summary="Imported from ChatGPT",
                        project_id=project_id,
                        metadata=thread_metadata,
                    )
                except TypeError:
                    thread_record = chatlog_db.create_chat_thread(
                        user_id=user_id,
                        title=title,
                        summary="Imported from ChatGPT",
                        project_id=project_id,
                    )
                    try:
                        thread_id_for_update = int(thread_record.get("id") or 0)
                    except Exception:
                        thread_id_for_update = 0
                    if thread_id_for_update > 0:
                        _update_thread_metadata_best_effort(
                            chatlog_db,
                            thread_id=thread_id_for_update,
                            updates=thread_metadata,
                        )

                thread_id = int(thread_record["id"])
                threads_count += 1
            else:
                _update_thread_metadata_best_effort(
                    chatlog_db,
                    thread_id=thread_id,
                    updates={
                        "import_source": "chatgpt",
                        "import_profile": _CHATGPT_IMPORT_PROFILE,
                        "source_thread_id": source_thread_id,
                        "source_conversation_template_id": template_id,
                        "import_summary": {
                            "messages_kept": len(messages),
                            "messages_filtered": conv_filtered_count,
                            "filtered_reasons": filtered_reasons,
                        },
                    },
                )

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
                    "imported_at": msg["imported_at"].isoformat(),
                }

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
                            "canonical_filter_profile": _CHATGPT_IMPORT_PROFILE,
                        }
                        _vector_store.add_texts(
                            [{"text": msg["content"], "meta": meta}]
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to embed imported message %s: %s",
                            mid,
                            e,
                        )

        except Exception as e:
            logger.error("Failed to import conversation: %s", e)
            continue

    return {
        "threads_imported": threads_count,
        "messages_imported": messages_count,
        "projects_created": 0,
        "projects_reused": 0,
        "messages_filtered": messages_filtered,
    }
