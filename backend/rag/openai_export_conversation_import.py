"""OpenAI export conversation import into Codexify-native chat storage.

Reads recovered OpenAI conversations from the local export corpus,
filters by limit/title, and writes Codexify-native thread/message records
with source provenance preserved. Idempotent on re-import.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    OpenAILegacyExportAdapter,
    OpenAIShardedExportAdapter,
    import_openai_export_path,
)

logger = logging.getLogger(__name__)

_DIAGNOSTIC_DIR = Path("logs/openai_import")


@dataclass
class ImportDiagnostics:
    export_path: str
    dry_run: bool
    limit: int | None
    title_filter: str | None
    started_at: str
    order: str = "file"
    completed_at: str = ""
    export_format: str = "unknown"
    conversations_discovered: int = 0
    conversations_imported: int = 0
    conversations_skipped_title: int = 0
    conversations_skipped_limit: int = 0
    conversations_skipped_duplicate: int = 0
    messages_discovered: int = 0
    messages_imported: int = 0
    messages_skipped_duplicate: int = 0
    parse_failures: int = 0
    skipped_records: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    latest_source_timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_path": self.export_path,
            "dry_run": self.dry_run,
            "limit": self.limit,
            "title_filter": self.title_filter,
            "order": self.order,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "export_format": self.export_format,
            "conversations_discovered": self.conversations_discovered,
            "conversations_imported": self.conversations_imported,
            "conversations_skipped_title": self.conversations_skipped_title,
            "conversations_skipped_limit": self.conversations_skipped_limit,
            "conversations_skipped_duplicate": self.conversations_skipped_duplicate,
            "messages_discovered": self.messages_discovered,
            "messages_imported": self.messages_imported,
            "messages_skipped_duplicate": self.messages_skipped_duplicate,
            "parse_failures": self.parse_failures,
            "skipped_records": self.skipped_records[:50],
            "errors": self.errors,
            "latest_source_timestamp": self.latest_source_timestamp,
        }


def _count_messages_in_conversation(conv: dict[str, Any]) -> int:
    """Count recoverable messages in a conversation record."""
    mapping = conv.get("mapping")
    if isinstance(mapping, dict):
        count = 0
        for node in mapping.values():
            if isinstance(node, dict) and isinstance(
                node.get("message"), dict
            ):
                count += 1
        return count

    messages = conv.get("messages")
    if isinstance(messages, list):
        return len(messages)

    return 0


def _extract_messages_from_conversation(
    conv: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract message dicts with timestamps from a conversation record."""
    mapping = conv.get("mapping")
    messages: list[dict[str, Any]] = []
    if isinstance(mapping, dict):
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                continue
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", {})
            parts = (
                content.get("parts", [])
                if isinstance(content, dict)
                else []
            )
            text = "\n".join(
                str(p) for p in (parts if isinstance(parts, list) else [])
            )
            if not text:
                continue
            create_time = msg.get("create_time")
            messages.append(
                {
                    "message_id": msg.get("id") or node_id,
                    "text": text,
                    "create_time": create_time,
                }
            )
        return messages

    raw_messages = conv.get("messages")
    if isinstance(raw_messages, list):
        for raw in raw_messages:
            if not isinstance(raw, dict):
                continue
            msg = (
                raw.get("message")
                if isinstance(raw.get("message"), dict)
                else raw
            )
            content = msg.get("content", "")
            if isinstance(content, dict):
                parts = content.get("parts", [])
                text = "\n".join(
                    str(p) for p in (parts if isinstance(parts, list) else [])
                )
            elif isinstance(content, list):
                text = "\n".join(str(p) for p in content)
            elif isinstance(content, str):
                text = content
            else:
                continue
            if not text:
                continue
            messages.append(
                {
                    "message_id": msg.get("id")
                    or msg.get("message_id")
                    or raw.get("id"),
                    "text": text,
                    "create_time": msg.get("create_time")
                    or msg.get("created_at")
                    or raw.get("create_time")
                    or raw.get("created_at"),
                }
            )
        return messages

    return []


def _matches_title_filter(conv: dict[str, Any], filter_text: str) -> bool:
    if not filter_text:
        return True
    title = str(conv.get("title") or "").lower()
    return filter_text.lower() in title


def _source_timestamp(conv: dict[str, Any], key: str = "update_time") -> float:
    """Extract a sortable timestamp from a conversation record."""
    for ts_key in (key, "create_time", "update_time"):
        val = conv.get(ts_key)
        if isinstance(val, (int, float)):
            ts = float(val)
            return ts / 1000.0 if ts > 1_000_000_000_000 else ts
    return 0.0


def _sort_conversations(
    conversations: list[dict[str, Any]],
    order: str,
) -> list[dict[str, Any]]:
    if order == "newest":
        return sorted(
            conversations,
            key=lambda c: _source_timestamp(c, "update_time"),
            reverse=True,
        )
    elif order == "oldest":
        return sorted(
            conversations,
            key=lambda c: _source_timestamp(c, "create_time"),
        )
    elif order == "updated":
        return sorted(
            conversations,
            key=lambda c: _source_timestamp(c, "update_time"),
            reverse=True,
        )
    return conversations  # "file" — adapter natural order


def _compute_latest_timestamp(
    conversations: list[dict[str, Any]],
) -> str | None:
    latest: float | None = None
    for conv in conversations:
        for ts_key in ("create_time", "update_time"):
            val = conv.get(ts_key)
            if isinstance(val, (int, float)):
                ts = float(val)
                if ts > 1_000_000_000_000:
                    ts = ts / 1000.0
                if latest is None or ts > latest:
                    latest = ts
    if latest is not None:
        return datetime.fromtimestamp(latest, timezone.utc).isoformat()
    return None


def import_openai_export_conversations(
    root_path: str | Path,
    *,
    user_id: str,
    dry_run: bool = False,
    limit: int | None = None,
    title_contains: str | None = None,
    diagnostic_dir: str | Path = "logs/openai_import",
    order: str = "file",
) -> ImportDiagnostics:
    """Import OpenAI export conversations into Codexify chat tables.

    Preserves source IDs as provenance metadata. Idempotent on re-import.
    Does not create embeddings, graph data, or personal facts.
    """
    root = Path(root_path).expanduser().resolve()
    diag_dir = Path(diagnostic_dir).expanduser().resolve()
    diag_dir.mkdir(parents=True, exist_ok=True)

    diagnostics = ImportDiagnostics(
        export_path=str(root),
        dry_run=dry_run,
        limit=limit,
        title_filter=title_contains,
        order=order,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # --- Diagnosis pass ---
    detector = OpenAIExportDetector()
    try:
        inventory = detector.scan(root)
    except Exception as exc:
        diagnostics.errors.append(f"Scan failed: {exc}")
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    diagnostics.export_format = inventory.detected_format
    diagnostics.parse_failures = sum(
        1 for f in inventory.files if not f.parse_success
    )

    # --- Extract conversations ---
    adapter: OpenAILegacyExportAdapter | OpenAIShardedExportAdapter
    # In "mixed" exports, prefer sharded adapter since conversations-*.json
    # shards are the modern format; legacy conversations.json may be absent.
    if inventory.sharded_detected:
        adapter = OpenAIShardedExportAdapter()
    elif inventory.legacy_detected:
        adapter = OpenAILegacyExportAdapter()
    else:
        diagnostics.errors.append(
            f"Unrecognized export format: {inventory.detected_format}"
        )
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    try:
        all_conversations = adapter.extract_conversations(inventory)
    except Exception as exc:
        diagnostics.errors.append(f"Conversation extraction failed: {exc}")
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    diagnostics.conversations_discovered = len(all_conversations)

    # --- Sort by order ---
    all_conversations = _sort_conversations(all_conversations, order)

    # --- Apply title filter ---
    if title_contains:
        filtered: list[dict[str, Any]] = []
        for conv in all_conversations:
            if _matches_title_filter(conv, title_contains):
                filtered.append(conv)
            else:
                diagnostics.conversations_skipped_title += 1
                diagnostics.skipped_records.append(
                    {
                        "conversation_id": str(
                            conv.get("conversation_id")
                            or conv.get("id")
                            or ""
                        ),
                        "title": str(conv.get("title", ""))[:100],
                        "reason": f"title_does_not_contain:{title_contains}",
                    }
                )
        all_conversations = filtered

    # --- Apply limit ---
    if limit is not None and limit > 0:
        if len(all_conversations) > limit:
            skipped = all_conversations[limit:]
            all_conversations = all_conversations[:limit]
            diagnostics.conversations_skipped_limit = len(skipped)
            for conv in skipped:
                diagnostics.skipped_records.append(
                    {
                        "conversation_id": str(
                            conv.get("conversation_id")
                            or conv.get("id")
                            or ""
                        ),
                        "title": str(conv.get("title", ""))[:100],
                        "reason": "limit_exceeded",
                    }
                )

    # --- Count messages discovered ---
    for conv in all_conversations:
        msg_count = _count_messages_in_conversation(conv)
        diagnostics.messages_discovered += msg_count

    diagnostics.latest_source_timestamp = _compute_latest_timestamp(
        all_conversations
    )

    # --- Dry run: skip DB writes ---
    if dry_run:
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        logger.info(
            "Dry run complete: %d conversations, %d messages would be imported",
            len(all_conversations),
            diagnostics.messages_discovered,
        )
        return diagnostics

    # --- Import into DB ---
    if not all_conversations:
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    try:
        from backend.rag.chatgpt_migration import (
            ingest_chatgpt_conversation_records,
        )

        import_stats = ingest_chatgpt_conversation_records(
            all_conversations,
            user_id=user_id,
        )
    except Exception as exc:
        diagnostics.errors.append(f"Import failed: {exc}")
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    diagnostics.conversations_imported = import_stats.get(
        "threads_imported", 0
    )
    diagnostics.messages_imported = import_stats.get("messages_imported", 0)
    diagnostics.conversations_skipped_duplicate = (
        len(all_conversations) - diagnostics.conversations_imported
    )
    diagnostics.messages_skipped_duplicate = (
        diagnostics.messages_discovered - diagnostics.messages_imported
    )

    diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
    _write_diagnostics(diagnostics, diag_dir)

    return diagnostics


def _write_diagnostics(
    diagnostics: ImportDiagnostics, diag_dir: Path
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = diag_dir / f"import_diagnostics_{ts}.json"
    json_path.write_text(
        json.dumps(diagnostics.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Import diagnostics written to %s", json_path)
