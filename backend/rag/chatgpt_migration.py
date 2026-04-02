"""ChatGPT export migration into Postgres and the vector store."""

import json
import logging
import multiprocessing as mp
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from guardian.core import dependencies

from .personal_fact_extraction import (
    extract_personal_fact_candidates,
    persist_personal_fact_candidates,
)

logger = logging.getLogger(__name__)

_CHATGPT_IMPORT_PROFILE = "chatgpt_v1_canonical"
_FILTERED_CONTENT_TYPES = {
    "model_editable_context",
    "thoughts",
    "reasoning_recap",
}
_TRUTHY = {"1", "true", "yes", "on"}
_IMPORT_EMBEDDINGS_ENABLED = (
    os.getenv("CODEXIFY_CHATGPT_IMPORT_EMBEDDINGS", "1").strip().lower()
    in _TRUTHY
)
_IMPORT_EMBED_ISOLATED = (
    os.getenv("CODEXIFY_CHATGPT_IMPORT_EMBED_ISOLATED", "1").strip().lower()
    in _TRUTHY
)
_MAX_EMBED_TEXT_CHARS = int(
    os.getenv("CODEXIFY_CHATGPT_IMPORT_MAX_EMBED_TEXT_CHARS", "24000")
)
_EMBED_SUBPROCESS_TIMEOUT_S = float(
    os.getenv("CODEXIFY_CHATGPT_IMPORT_EMBED_TIMEOUT_SECONDS", "180")
)


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


def _sanitize_embed_text(text: Any) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    if len(normalized) > _MAX_EMBED_TEXT_CHARS:
        return normalized[:_MAX_EMBED_TEXT_CHARS]
    return normalized


def _sanitize_embed_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
            continue
        safe[str(key)] = str(value)
    return safe


def _embed_items_subprocess(items: List[Dict[str, Any]]) -> None:
    # Child process entrypoint: isolate native embedding/indexing libs from API.
    from guardian.vector.store import VectorStore

    store = VectorStore()
    store.add_texts(items)


def _embed_items_best_effort(
    items: List[Dict[str, Any]],
    vector_store: Any,
) -> Dict[str, Any]:
    candidates = len(items)
    diagnostics: Dict[str, Any] = {
        "embedding_candidates": candidates,
        "embeddings_persisted": 0,
        "embeddings_failed": candidates,
        "embedding_coverage_degraded": candidates > 0,
    }
    if not items:
        diagnostics["embedding_coverage_degraded"] = False
        return diagnostics

    if vector_store is None:
        logger.warning(
            "ChatGPT import embedding unavailable; skipped candidate batch size=%d",
            candidates,
        )
        return diagnostics

    def _embed_in_process() -> Dict[str, Any]:
        try:
            persisted = vector_store.add_texts(items)
            if persisted is None:
                persisted_count = candidates
            else:
                persisted_count = max(
                    0,
                    min(candidates, int(persisted)),
                )
            diagnostics["embeddings_persisted"] = persisted_count
            diagnostics["embeddings_failed"] = candidates - persisted_count
            diagnostics["embedding_coverage_degraded"] = (
                diagnostics["embeddings_failed"] > 0
            )
        except Exception as exc:
            logger.warning(
                "ChatGPT import embedding write failed in-process: %s",
                exc,
            )
        return diagnostics

    if not _IMPORT_EMBED_ISOLATED:
        return _embed_in_process()

    try:
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_embed_items_subprocess, args=(items,))
        proc.start()
        proc.join(_EMBED_SUBPROCESS_TIMEOUT_S)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5.0)
            logger.warning(
                "ChatGPT import embedding timed out after %.1fs; skipped batch size=%d",
                _EMBED_SUBPROCESS_TIMEOUT_S,
                candidates,
            )
            return _embed_in_process()
        if proc.exitcode != 0:
            logger.warning(
                "ChatGPT import embedding subprocess failed with exit code=%s for batch size=%d",
                proc.exitcode,
                candidates,
            )
            return _embed_in_process()
        diagnostics["embeddings_persisted"] = candidates
        diagnostics["embeddings_failed"] = 0
        diagnostics["embedding_coverage_degraded"] = False
        return diagnostics
    except Exception as exc:
        logger.warning(
            "ChatGPT import embedding subprocess launch failed: %s",
            exc,
        )
        return _embed_in_process()


def _fetch_retryable_chatgpt_embedding_items(
    chatlog_db,
    *,
    user_id: str,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    if not hasattr(chatlog_db, "_connect"):
        return []

    rows: List[Dict[str, Any]] = []
    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id AS message_id,
                    m.thread_id,
                    m.role,
                    m.content,
                    m.event_at,
                    COALESCE(m.extra_meta, '{}'::jsonb) AS extra_meta
                FROM chat_messages AS m
                JOIN chat_threads AS t
                  ON t.id = m.thread_id
                WHERE t.user_id = %s
                  AND COALESCE(t.metadata->>'import_source', '') = 'chatgpt'
                  AND (
                    COALESCE(m.extra_meta, '{}'::jsonb) ? 'source_message_id'
                    OR COALESCE(m.extra_meta, '{}'::jsonb) ? 'source_thread_id'
                  )
                  AND (
                    COALESCE(m.extra_meta->>'embedding_status', '') = ''
                    OR COALESCE(m.extra_meta->>'embedding_status', '') IN ('pending', 'failed')
                  )
                ORDER BY m.id ASC
                LIMIT %s
                """,
                (user_id, int(limit)),
            )
            rows = list(cur.fetchall() or [])
    except Exception as exc:
        logger.warning(
            "Unable to fetch retryable ChatGPT embedding items for user=%s: %s",
            user_id,
            exc,
        )
        return []

    retry_items: List[Dict[str, Any]] = []
    for row in rows:
        try:
            message_id = int(row.get("message_id"))
        except Exception:
            continue

        raw_meta = row.get("extra_meta")
        existing_meta = raw_meta if isinstance(raw_meta, dict) else {}

        text = _sanitize_embed_text(row.get("content"))
        if not text:
            continue

        event_at = row.get("event_at")
        timestamp = (
            event_at.isoformat()
            if hasattr(event_at, "isoformat")
            else str(existing_meta.get("source_created_at") or "")
        )
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        retry_items.append(
            {
                "message_id": message_id,
                "text": text,
                "meta": _sanitize_embed_meta(
                    {
                        "thread_id": row.get("thread_id"),
                        "role": row.get("role"),
                        "message_id": message_id,
                        "timestamp": timestamp,
                        "source_thread_id": existing_meta.get(
                            "source_thread_id"
                        ),
                        "source_conversation_template_id": existing_meta.get(
                            "source_conversation_template_id"
                        ),
                        "source_gizmo_id": existing_meta.get("source_gizmo_id"),
                        "source_gizmo_type": existing_meta.get(
                            "source_gizmo_type"
                        ),
                        "source_message_id": existing_meta.get(
                            "source_message_id"
                        ),
                        "turn_index": existing_meta.get("turn_index"),
                        "source_created_at_inferred": existing_meta.get(
                            "source_created_at_inferred"
                        ),
                        "origin": "chatgpt_import",
                        "era": "pre_codexify",
                        "source": "chatgpt_import",
                        "canonical_filter_profile": _CHATGPT_IMPORT_PROFILE,
                    }
                ),
            }
        )
    return retry_items


def _persist_chatgpt_embedding_attempt_outcome(
    chatlog_db,
    *,
    message_ids: List[int],
    persisted_count: int,
    failure_reason: Optional[str] = None,
) -> None:
    if not message_ids or not hasattr(chatlog_db, "_connect"):
        return

    persisted_count = max(0, min(int(persisted_count), len(message_ids)))
    persisted_ids = set(message_ids[:persisted_count])
    attempted_at = datetime.now(timezone.utc).isoformat()

    try:
        with chatlog_db._connect() as conn, conn.cursor() as cur:
            for message_id in message_ids:
                cur.execute(
                    """
                    SELECT COALESCE(extra_meta, '{}'::jsonb) AS extra_meta
                    FROM chat_messages
                    WHERE id = %s
                    """,
                    (message_id,),
                )
                row = cur.fetchone()
                row_meta = (
                    row.get("extra_meta") if isinstance(row, dict) else {}
                )
                extra_meta = dict(row_meta or {})

                attempts = extra_meta.get("embedding_attempts")
                try:
                    attempts_value = int(attempts)
                except (TypeError, ValueError):
                    attempts_value = 0

                if message_id in persisted_ids:
                    extra_meta["embedding_status"] = "persisted"
                    extra_meta["embedding_last_error"] = None
                else:
                    extra_meta["embedding_status"] = "failed"
                    extra_meta["embedding_last_error"] = str(
                        failure_reason or "embedding_write_failed"
                    )

                extra_meta["embedding_attempts"] = attempts_value + 1
                extra_meta["embedding_last_attempt_at"] = attempted_at

                cur.execute(
                    """
                    UPDATE chat_messages
                    SET extra_meta = %s::jsonb
                    WHERE id = %s
                    """,
                    (json.dumps(extra_meta), message_id),
                )
    except Exception as exc:
        logger.warning(
            "Unable to persist ChatGPT embedding retry outcome for %d messages: %s",
            len(message_ids),
            exc,
        )


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
    except Exception as e:
        logger.warning(
            "Failed to resolve Imports project ID via list_projects: %s",
            e,
        )
    raise RuntimeError("Unable to resolve Imports project ID")


def _build_import_grouping_metadata(
    conversation: Dict[str, Any],
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}

    template_id = _normalize_template_id(
        conversation.get("conversation_template_id")
    )
    if template_id:
        metadata["source_conversation_template_id"] = template_id

    gizmo_id = conversation.get("gizmo_id")
    if isinstance(gizmo_id, str) and gizmo_id.strip():
        metadata["source_gizmo_id"] = gizmo_id.strip()

    gizmo_type = conversation.get("gizmo_type")
    if isinstance(gizmo_type, str) and gizmo_type.strip():
        metadata["source_gizmo_type"] = gizmo_type.strip()

    return metadata


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
                "content_type": str(content.get("content_type") or "")
                .strip()
                .lower(),
                "source_created_at": message_created_at,
                "source_created_at_inferred": source_created_at_inferred,
                "imported_at": imported_at,
                "source_thread_id": source_thread_id,
                "source_message_id": str(node_id),
                "turn_index": turn_index,
                "source_role_raw": source_role_raw,
                "raw_role": raw_role,
                "raw_message": dict(message),
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

    # Use existing vector store if already initialized; do NOT eagerly initialize.
    # This allows import to succeed (with DB records) even if vector store is unavailable.
    _vector_store = None
    if _IMPORT_EMBEDDINGS_ENABLED:
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
    projects_created = 0
    projects_reused = 0
    imports_project_id = int(_resolve_imports_project_id(chatlog_db))
    pending_embed_items: List[Dict[str, Any]] = []
    pending_embed_message_ids: List[int] = []

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
            import_grouping_metadata = _build_import_grouping_metadata(conv)

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

            thread_id = _find_existing_thread_for_source(
                chatlog_db, user_id=user_id, source_thread_id=source_thread_id
            )
            if thread_id is None:
                # Keep the surface flat: imported threads land in Imports, and
                # any inferred grouping survives only in metadata.
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
                    **import_grouping_metadata,
                }

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
                        "import_summary": {
                            "messages_kept": len(messages),
                            "messages_filtered": conv_filtered_count,
                            "filtered_reasons": filtered_reasons,
                        },
                        **import_grouping_metadata,
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
                    "content_type": msg.get("content_type"),
                    "raw_role": msg.get("raw_role"),
                    "raw_message": msg.get("raw_message"),
                    "origin": msg.get("origin"),
                    "era": msg.get("era"),
                    "canonical_filter_profile": _CHATGPT_IMPORT_PROFILE,
                    **import_grouping_metadata,
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

                personal_fact_candidates = extract_personal_fact_candidates(msg)
                if personal_fact_candidates:
                    try:
                        persist_personal_fact_candidates(
                            chatlog_db,
                            user_id=user_id,
                            message={
                                **msg,
                                "chatlog_message_id": mid,
                            },
                            candidates=personal_fact_candidates,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to persist ChatGPT personal fact candidates for message %s: %s",
                            mid,
                            exc,
                        )

                # Queue embedding payload for post-import processing.
                if not existing:
                    try:
                        embed_text = _sanitize_embed_text(msg["content"])
                        if not embed_text:
                            continue
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
                            **import_grouping_metadata,
                        }
                        pending_embed_items.append(
                            {
                                "text": embed_text,
                                "meta": _sanitize_embed_meta(meta),
                            }
                        )
                        pending_embed_message_ids.append(mid)
                    except Exception as e:
                        logger.warning(
                            "Failed to queue embedded payload for imported message %s: %s",
                            mid,
                            e,
                        )

        except Exception as e:
            logger.error("Failed to import conversation: %s", e)
            continue

    if _vector_store and pending_embed_items:
        embedding_diagnostics = _embed_items_best_effort(
            pending_embed_items, _vector_store
        )
    else:
        embedding_diagnostics = _embed_items_best_effort(
            pending_embed_items, None
        )

    _persist_chatgpt_embedding_attempt_outcome(
        chatlog_db,
        message_ids=pending_embed_message_ids,
        persisted_count=int(
            embedding_diagnostics.get("embeddings_persisted", 0)
        ),
        failure_reason=(
            "embedding_coverage_degraded"
            if embedding_diagnostics.get("embedding_coverage_degraded")
            else None
        ),
    )

    return {
        "threads_imported": threads_count,
        "messages_imported": messages_count,
        "projects_created": projects_created,
        "projects_reused": projects_reused,
        "messages_filtered": messages_filtered,
        "embedding_candidates": embedding_diagnostics["embedding_candidates"],
        "embeddings_persisted": embedding_diagnostics["embeddings_persisted"],
        "embeddings_failed": embedding_diagnostics["embeddings_failed"],
        "embedding_coverage_degraded": embedding_diagnostics[
            "embedding_coverage_degraded"
        ],
    }


def retry_chatgpt_import_embeddings(
    *, user_id: Optional[str] = None
) -> Dict[str, Any]:
    if not user_id:
        raise ValueError(
            "retry_chatgpt_import_embeddings requires a valid user_id (got None or empty)"
        )

    chatlog_db = dependencies.chatlog_db
    if not chatlog_db:
        chatlog_db = dependencies.init_database()
    if not chatlog_db:
        raise RuntimeError("Database not available")

    retryable_items = _fetch_retryable_chatgpt_embedding_items(
        chatlog_db, user_id=user_id
    )
    if not retryable_items:
        return {
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        }

    payload_items = [
        {"text": item["text"], "meta": item["meta"]} for item in retryable_items
    ]
    message_ids = [
        int(item["message_id"])
        for item in retryable_items
        if item.get("message_id") is not None
    ]

    vector_store = None
    if _IMPORT_EMBEDDINGS_ENABLED:
        vector_store = getattr(dependencies, "_vector_store", None) or None

    diagnostics = _embed_items_best_effort(payload_items, vector_store)
    _persist_chatgpt_embedding_attempt_outcome(
        chatlog_db,
        message_ids=message_ids,
        persisted_count=int(diagnostics.get("embeddings_persisted", 0)),
        failure_reason=(
            "embedding_retry_degraded"
            if diagnostics.get("embedding_coverage_degraded")
            else None
        ),
    )
    return {
        "embedding_candidates": int(diagnostics.get("embedding_candidates", 0)),
        "embeddings_persisted": int(diagnostics.get("embeddings_persisted", 0)),
        "embeddings_failed": int(diagnostics.get("embeddings_failed", 0)),
        "embedding_coverage_degraded": bool(
            diagnostics.get("embedding_coverage_degraded", False)
        ),
    }
