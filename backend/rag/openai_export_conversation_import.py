"""OpenAI export conversation import into Codexify-native chat storage.

Reads recovered OpenAI conversations from the local export corpus,
filters by limit/title, and writes Codexify-native thread/message records
with source provenance preserved. Idempotent on re-import.

Supports resumable checkpointing, staged import (messages-only), and
personal facts / embedding deferral for archive-scale reliability.
"""

from __future__ import annotations

import json
import logging
import time
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
from backend.rag.import_checkpoint import (
    ImportCheckpointManager,
    resolve_checkpoint_path,
)

logger = logging.getLogger(__name__)

_DIAGNOSTIC_DIR = Path("logs/openai_import")
_DEFAULT_BATCH_CONVERSATIONS = 10
_DEFAULT_BATCH_MESSAGES = 500
_DB_HEALTH_BACKOFF_SECONDS = 2.0


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
    conversations_skipped_checkpoint: int = 0
    conversations_failed: int = 0
    messages_discovered: int = 0
    messages_imported: int = 0
    messages_skipped_duplicate: int = 0
    parse_failures: int = 0
    skipped_records: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    latest_source_timestamp: str | None = None
    # Import orchestration
    resume: bool = False
    checkpoint_path: str = ""
    import_run_id: str = ""
    batch_conversations: int = _DEFAULT_BATCH_CONVERSATIONS
    elapsed_seconds: float = 0.0
    # Staging flags
    messages_only: bool = False
    disable_personal_facts: bool = False
    # Embedding phase (separate from text import)
    embedding_mode: str = "defer"
    embedding_candidates: int = 0
    embedding_enqueued: int = 0
    embedding_deferred: int = 0
    embedding_failed: int = 0
    text_import_complete: bool = False

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
            "conversations_skipped_checkpoint": self.conversations_skipped_checkpoint,
            "conversations_failed": self.conversations_failed,
            "messages_discovered": self.messages_discovered,
            "messages_imported": self.messages_imported,
            "messages_skipped_duplicate": self.messages_skipped_duplicate,
            "parse_failures": self.parse_failures,
            "skipped_records": self.skipped_records[:50],
            "errors": self.errors,
            "latest_source_timestamp": self.latest_source_timestamp,
            "resume": self.resume,
            "checkpoint_path": self.checkpoint_path,
            "import_run_id": self.import_run_id,
            "batch_conversations": self.batch_conversations,
            "elapsed_seconds": self.elapsed_seconds,
            "messages_only": self.messages_only,
            "disable_personal_facts": self.disable_personal_facts,
            "embedding_mode": self.embedding_mode,
            "embedding_candidates": self.embedding_candidates,
            "embedding_enqueued": self.embedding_enqueued,
            "embedding_deferred": self.embedding_deferred,
            "embedding_failed": self.embedding_failed,
            "text_import_complete": self.text_import_complete,
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
    embedding_mode: str = "defer",
    resume: bool = False,
    checkpoint_path: str | None = None,
    batch_conversations: int = _DEFAULT_BATCH_CONVERSATIONS,
    disable_personal_facts: bool = False,
    messages_only: bool = False,
) -> ImportDiagnostics:
    """Import OpenAI export conversations into Codexify chat tables.

    Preserves source IDs as provenance metadata. Idempotent on re-import.

    Args:
        resume: If True, skip conversations already in the checkpoint.
        checkpoint_path: Explicit directory for checkpoint file.
        batch_conversations: Conversations to process per DB batch commit.
        disable_personal_facts: Skip personal facts extraction (Stage A).
        messages_only: Only import thread/messages, no derived processing.
    """
    start_ts = time.monotonic()
    root = Path(root_path).expanduser().resolve()
    diag_dir = Path(diagnostic_dir).expanduser().resolve()
    diag_dir.mkdir(parents=True, exist_ok=True)

    # Resolve checkpoint manager
    ckpt_dir = resolve_checkpoint_path(
        cli_path=checkpoint_path, diagnostic_dir=diag_dir
    )
    ckpt = ImportCheckpointManager(ckpt_dir)

    diagnostics = ImportDiagnostics(
        export_path=str(root),
        dry_run=dry_run,
        limit=limit,
        title_filter=title_contains,
        order=order,
        embedding_mode=embedding_mode,
        started_at=datetime.now(timezone.utc).isoformat(),
        resume=resume,
        checkpoint_path=str(ckpt_dir),
        batch_conversations=batch_conversations,
        disable_personal_facts=disable_personal_facts,
        messages_only=messages_only,
    )

    # --- Start / resume checkpoint run ---
    diagnostics.import_run_id = ckpt.start_run(str(root))
    completed_ids = ckpt.load_completed()
    if resume and completed_ids:
        logger.info(
            "Resuming import: %d conversations already completed",
            len(completed_ids),
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

    # --- Import into DB with checkpointing ---
    if not all_conversations:
        diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
        _write_diagnostics(diagnostics, diag_dir)
        return diagnostics

    try:
        _import_with_checkpoints(
            all_conversations=all_conversations,
            user_id=user_id,
            embedding_mode=embedding_mode,
            diagnostics=diagnostics,
            ckpt=ckpt,
            batch_size=max(1, batch_conversations),
            disable_personal_facts=disable_personal_facts,
            messages_only=messages_only,
        )
    except Exception as exc:
        diagnostics.errors.append(f"Import failed: {exc}")
        logger.exception("Import process failed")

    diagnostics.elapsed_seconds = round(time.monotonic() - start_ts, 3)
    diagnostics.completed_at = datetime.now(timezone.utc).isoformat()
    _write_diagnostics(diagnostics, diag_dir)

    ckpt_summary = ckpt.summary()
    logger.info(
        "Import run %s complete: imported=%d failed=%d skipped=%d elapsed=%.1fs",
        diagnostics.import_run_id,
        ckpt_summary.get("imported", 0),
        ckpt_summary.get("failed", 0),
        ckpt_summary.get("skipped", 0),
        diagnostics.elapsed_seconds,
    )

    return diagnostics


def _import_with_checkpoints(
    *,
    all_conversations: list[dict[str, Any]],
    user_id: str,
    embedding_mode: str,
    diagnostics: ImportDiagnostics,
    ckpt: ImportCheckpointManager,
    batch_size: int,
    disable_personal_facts: bool,
    messages_only: bool,
) -> None:
    """Import conversations in bounded batches with checkpointing."""
    total = len(all_conversations)
    batch_count = (total + batch_size - 1) // batch_size

    for batch_idx in range(0, total, batch_size):
        batch = all_conversations[batch_idx : batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1

        # Filter out already-completed conversations when resuming
        pending: list[dict[str, Any]] = []
        for conv in batch:
            conv_id = str(
                conv.get("conversation_id") or conv.get("id") or ""
            )
            if ckpt.is_completed(conv_id):
                diagnostics.conversations_skipped_checkpoint += 1
                continue
            pending.append(conv)

        if not pending:
            logger.info(
                "Batch %d/%d: all already completed, skipping",
                batch_num,
                batch_count,
            )
            continue

        logger.info(
            "Batch %d/%d: processing %d conversations...",
            batch_num,
            batch_count,
            len(pending),
        )

        # Import the batch
        batch_stats = _import_conversation_batch(
            conversations=pending,
            user_id=user_id,
            embedding_mode=embedding_mode,
            disable_personal_facts=disable_personal_facts,
            messages_only=messages_only,
        )

        # Update diagnostics from batch stats
        diagnostics.conversations_imported += batch_stats.get("threads_imported", 0)
        diagnostics.messages_imported += batch_stats.get("messages_imported", 0)

        # Mark each conversation in the batch
        for conv in pending:
            conv_id = str(
                conv.get("conversation_id") or conv.get("id") or ""
            )
            msg_count = _count_messages_in_conversation(conv)
            try:
                ckpt.mark_imported(
                    conversation_id=conv_id,
                    source_file=conv.get("_codexify_import_metadata", {}).get(
                        "openai_export_source_path", ""
                    ),
                    messages_imported=msg_count,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to write checkpoint for %s: %s", conv_id, exc
                )

        progress = min(batch_idx + batch_size, total)
        logger.info(
            "Progress: %d/%d conversations (%.1f%%) | "
            "threads=%d messages=%d",
            progress,
            total,
            100.0 * progress / total,
            diagnostics.conversations_imported,
            diagnostics.messages_imported,
        )

    diagnostics.text_import_complete = True


def _import_conversation_batch(
    *,
    conversations: list[dict[str, Any]],
    user_id: str,
    embedding_mode: str,
    disable_personal_facts: bool,
    messages_only: bool,
) -> dict[str, Any]:
    """Import a single batch of conversations with short transactions.

    Uses the existing ingest_chatgpt_conversation_records function but
    wraps it with optional personal facts / embedding staging.
    """
    from backend.rag.chatgpt_migration import (
        ingest_chatgpt_conversation_records,
    )

    # Resolve effective embedding mode
    effective_embedding = embedding_mode
    if messages_only:
        effective_embedding = "off"

    # Build import kwargs
    kwargs: dict[str, Any] = {
        "user_id": user_id,
        "embedding_mode": effective_embedding,
    }

    if disable_personal_facts:
        kwargs["disable_personal_facts"] = True

    # Run the batch through the existing import pipeline
    # Each conversation is already handled with idempotent upsert
    return ingest_chatgpt_conversation_records(
        conversations,
        user_id=user_id,
        embedding_mode=effective_embedding,
        disable_personal_facts=disable_personal_facts,
    )


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
