"""Forensic OpenAI export discovery, diagnostics, and import adapters."""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)

_SAMPLE_BYTES = 1024 * 1024
_JSON_PREVIEW_LINES = 25
_CONVERSATION_CONTAINER_KEYS = (
    "conversations",
    "threads",
    "chats",
    "items",
    "data",
)
_CONVERSATION_HINT_KEYS = {
    "title",
    "create_time",
    "update_time",
    "mapping",
    "messages",
    "conversation_id",
    "message",
    "author",
    "content",
    "parts",
}

# Keys that strongly indicate a file manifest record (not a conversation).
_MANIFEST_HINT_KEYS = {
    "file_name",
    "file_path",
    "file_size",
    "original_path",
    "export_path",
    "export_id",
    "manifest_version",
}

# Directories that contain export metadata rather than conversation data.
_MANIFEST_DIR_PATTERNS = (
    "__export_file_manifests__",
)


@dataclass
class OpenAIExportFileRecord:
    """Diagnostic record for one scanned export file."""

    path: str
    absolute_path: str
    size: int
    extension: str
    detected_kind: str
    first_bytes_hex: str
    magic_signature: str
    parse_success: bool = False
    parse_error: str | None = None
    top_level_json_keys: list[str] = field(default_factory=list)
    json_item_count: int | None = None
    conversation_candidate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "absolute_path": self.absolute_path,
            "size": self.size,
            "extension": self.extension,
            "detected_kind": self.detected_kind,
            "first_bytes_hex": self.first_bytes_hex,
            "magic_signature": self.magic_signature,
            "parse_success": self.parse_success,
            "parse_error": self.parse_error,
            "top_level_json_keys": self.top_level_json_keys,
            "json_item_count": self.json_item_count,
            "conversation_candidate": self.conversation_candidate,
        }


@dataclass
class OpenAIExportInventory:
    """Full diagnostic inventory for an OpenAI export root."""

    root_path: str
    files: list[OpenAIExportFileRecord]
    legacy_detected: bool
    sharded_detected: bool
    detected_format: str

    @property
    def json_files(self) -> list[OpenAIExportFileRecord]:
        return [
            item
            for item in self.files
            if item.detected_kind
            in {"json_object", "json_array", "jsonl", "invalid_json"}
        ]

    @property
    def attachment_files(self) -> list[OpenAIExportFileRecord]:
        return [
            item
            for item in self.files
            if item.detected_kind.startswith(("image_", "audio_", "video_"))
            or item.detected_kind
            in {"pdf", "zip", "unknown_binary", "binary_attachment"}
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "legacy_detected": self.legacy_detected,
            "sharded_detected": self.sharded_detected,
            "detected_format": self.detected_format,
            "files_scanned": len(self.files),
            "json_files": len(self.json_files),
            "attachment_files": len(self.attachment_files),
            "conversation_candidate_files": sum(
                1 for item in self.files if item.conversation_candidate
            ),
            "files": [item.to_dict() for item in self.files],
        }

    def to_summary_text(self) -> str:
        counts: dict[str, int] = {}
        for item in self.files:
            counts[item.detected_kind] = counts.get(item.detected_kind, 0) + 1

        lines = [
            "OpenAI Export Diagnostic Summary",
            f"Root: {self.root_path}",
            f"Detected format: {self.detected_format}",
            f"Files scanned: {len(self.files)}",
            f"JSON-like files: {len(self.json_files)}",
            f"Attachment/orphan asset files: {len(self.attachment_files)}",
            "Kinds:",
        ]
        for kind, count in sorted(counts.items()):
            lines.append(f"  - {kind}: {count}")

        candidates = [
            item.path for item in self.files if item.conversation_candidate
        ]
        if candidates:
            lines.append("Conversation candidates:")
            for path in candidates[:50]:
                lines.append(f"  - {path}")
            if len(candidates) > 50:
                lines.append(f"  - ... {len(candidates) - 50} more")

        return "\n".join(lines) + "\n"


@dataclass
class OpenAIExportDiagnosticReport:
    inventory: OpenAIExportInventory
    json_path: Path | None = None
    summary_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory": self.inventory.to_dict(),
            "json_path": str(self.json_path) if self.json_path else None,
            "summary_path": str(self.summary_path)
            if self.summary_path
            else None,
        }


class OpenAIExportFileClassifier:
    """Classify export files from content, not filename extension."""

    def classify_path(
        self, path: Path, *, relative_to: Path | None = None
    ) -> OpenAIExportFileRecord:
        resolved = path.resolve()
        root = relative_to.resolve() if relative_to else resolved.parent
        try:
            rel_path = resolved.relative_to(root).as_posix()
        except ValueError:
            rel_path = resolved.name

        size = resolved.stat().st_size
        with resolved.open("rb") as fh:
            sample = fh.read(_SAMPLE_BYTES)
        record = OpenAIExportFileRecord(
            path=rel_path,
            absolute_path=str(resolved),
            size=size,
            extension=resolved.suffix.lower(),
            detected_kind="unknown_binary",
            first_bytes_hex=sample[:16].hex(),
            magic_signature=_magic_signature(sample),
        )
        self._classify_sample(record, sample)
        return record

    def _classify_sample(
        self, record: OpenAIExportFileRecord, sample: bytes
    ) -> None:
        if not sample:
            record.detected_kind = "empty"
            record.parse_success = True
            return

        magic_kind = _detect_magic_kind(sample)
        if magic_kind:
            record.detected_kind = magic_kind
            record.parse_success = True
            return

        stripped = sample.lstrip()
        lowered = stripped[:256].lower()
        if lowered.startswith((b"<!doctype html", b"<html", b"<!--")):
            record.detected_kind = "html"
            record.parse_success = True
            return

        if stripped[:1] in {b"{", b"["}:
            self._probe_json(record)
            return

        # JSONL often starts with `{`, but keep a secondary text probe for
        # exports that begin with a BOM or leading comments/noise.
        if _looks_textual(sample):
            if self._probe_jsonl(record):
                return
            if lowered.startswith(b"<"):
                record.detected_kind = "html"
                record.parse_success = True
                return
            record.detected_kind = "text"
            record.parse_success = True
            return

        record.detected_kind = "unknown_binary"

    def _probe_json(self, record: OpenAIExportFileRecord) -> None:
        try:
            payload = Path(record.absolute_path).read_text(
                encoding="utf-8-sig"
            )
            parsed = json.loads(payload)
        except Exception as exc:
            record.parse_error = str(exc)
            if self._probe_jsonl(record):
                return
            record.detected_kind = "invalid_json"
            record.parse_success = False
            return

        record.parse_success = True
        if isinstance(parsed, dict):
            record.detected_kind = "json_object"
            record.top_level_json_keys = sorted(str(key) for key in parsed.keys())
            record.conversation_candidate = _payload_has_conversation_shape(
                parsed
            )
            return
        if isinstance(parsed, list):
            record.detected_kind = "json_array"
            record.json_item_count = len(parsed)
            first_dict = next(
                (item for item in parsed if isinstance(item, dict)), None
            )
            if first_dict is not None:
                record.top_level_json_keys = sorted(
                    str(key) for key in first_dict.keys()
                )
            record.conversation_candidate = _payload_has_conversation_shape(
                parsed
            )
            return

        record.detected_kind = "json_scalar"

    def _probe_jsonl(self, record: OpenAIExportFileRecord) -> bool:
        try:
            lines = Path(record.absolute_path).read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except Exception as exc:
            record.parse_error = str(exc)
            return False

        parsed_count = 0
        keys: set[str] = set()
        candidate = False
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception as exc:
                if parsed_count:
                    record.parse_error = str(exc)
                return False
            parsed_count += 1
            if isinstance(parsed, dict):
                keys.update(str(key) for key in parsed.keys())
            candidate = candidate or _payload_has_conversation_shape(parsed)
            if parsed_count >= _JSON_PREVIEW_LINES:
                break

        if not parsed_count:
            return False

        record.detected_kind = "jsonl"
        record.parse_success = True
        record.parse_error = None
        record.json_item_count = parsed_count
        record.top_level_json_keys = sorted(keys)
        record.conversation_candidate = candidate
        return True


class OpenAIExportDetector:
    """Recursively scan an export root and identify legacy vs sharded format."""

    def __init__(self, classifier: OpenAIExportFileClassifier | None = None):
        self.classifier = classifier or OpenAIExportFileClassifier()

    def scan(self, root_path: str | Path) -> OpenAIExportInventory:
        root = Path(root_path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"OpenAI export path does not exist: {root}")

        if root.is_file():
            files = [root]
            relative_root = root.parent
        else:
            files = sorted(path for path in root.rglob("*") if path.is_file())
            relative_root = root

        records = [
            self.classifier.classify_path(path, relative_to=relative_root)
            for path in files
        ]

        legacy_detected = any(
            Path(record.path).name == "conversations.json"
            and record.detected_kind in {"json_array", "json_object"}
            and not _is_manifest_path(record.path)
            and _has_conversation_payload(record)
            for record in records
        )
        sharded_detected = any(_is_modern_marker(record) for record in records)
        sharded_detected = sharded_detected or any(
            record.conversation_candidate
            and Path(record.path).name != "conversations.json"
            for record in records
        )
        if legacy_detected and sharded_detected:
            detected_format = "mixed"
        elif legacy_detected:
            detected_format = "legacy"
        elif sharded_detected:
            detected_format = "sharded"
        else:
            detected_format = "unknown"

        return OpenAIExportInventory(
            root_path=str(root),
            files=records,
            legacy_detected=legacy_detected,
            sharded_detected=sharded_detected,
            detected_format=detected_format,
        )


class OpenAILegacyExportAdapter:
    """Adapter for legacy exports containing conversations.json."""

    def extract_conversations(
        self, inventory: OpenAIExportInventory
    ) -> list[dict[str, Any]]:
        candidates = [
            record
            for record in inventory.files
            if Path(record.path).name == "conversations.json"
            and record.detected_kind in {"json_array", "json_object"}
        ]
        if not candidates:
            raise ValueError(
                "Legacy OpenAI export detected, but conversations.json was not readable JSON."
            )

        record = sorted(candidates, key=lambda item: item.path)[0]
        payload = _load_json_record(record)
        return _extract_conversation_records(
            payload,
            source_path=record.path,
            export_format="legacy",
        )


class OpenAIShardedExportAdapter:
    """Adapter for newer exports with opaque sharded payload files."""

    def extract_conversations(
        self, inventory: OpenAIExportInventory
    ) -> list[dict[str, Any]]:
        conversations: list[dict[str, Any]] = []
        per_message_records: list[tuple[dict[str, Any], str]] = []

        for record in inventory.files:
            if record.detected_kind not in {"json_object", "json_array", "jsonl"}:
                continue
            try:
                for payload in _iter_json_payloads(record):
                    extracted, message_records = _extract_conversation_payload(
                        payload,
                        source_path=record.path,
                        export_format="sharded",
                    )
                    conversations.extend(extracted)
                    per_message_records.extend(message_records)
            except Exception as exc:
                logger.warning(
                    "Skipping OpenAI export JSON payload path=%s error=%s",
                    record.path,
                    exc,
                )

        conversations.extend(
            _synthesize_conversations_from_message_records(
                per_message_records,
                export_format="sharded",
            )
        )
        return _dedupe_conversations(conversations)


def diagnose_openai_export_path(
    root_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> OpenAIExportDiagnosticReport:
    inventory = OpenAIExportDetector().scan(root_path)
    report = OpenAIExportDiagnosticReport(inventory=inventory)
    if output_dir is not None:
        write_diagnostic_report(report, output_dir)
    return report


def import_openai_export_path(
    root_path: str | Path,
    *,
    user_id: str,
    diagnose_only: bool = False,
    diagnostic_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Diagnose and optionally import an OpenAI export root."""

    report = diagnose_openai_export_path(
        root_path, output_dir=diagnostic_output_dir
    )
    inventory = report.inventory

    stats: dict[str, Any] = {
        "threads_imported": 0,
        "messages_imported": 0,
        "messages_filtered": 0,
        "embedding_candidates": 0,
        "embeddings_persisted": 0,
        "embeddings_failed": 0,
        "embedding_coverage_degraded": False,
        "export_format": inventory.detected_format,
        "files_scanned": len(inventory.files),
        "json_files": len(inventory.json_files),
        "orphaned_export_assets": len(inventory.attachment_files),
        "diagnostic_report": str(report.json_path) if report.json_path else None,
        "diagnostic_summary": str(report.summary_path)
        if report.summary_path
        else None,
    }
    if diagnose_only:
        return stats

    adapter: OpenAILegacyExportAdapter | OpenAIShardedExportAdapter
    # In "mixed" exports, prefer the sharded adapter. This avoids the
    # __export_file_manifests__/conversations.json false-positive problem.
    if inventory.sharded_detected:
        adapter = OpenAIShardedExportAdapter()
    elif inventory.legacy_detected:
        adapter = OpenAILegacyExportAdapter()
    else:
        raise ValueError(
            "Unrecognized OpenAI export structure: no conversations.json, "
            "sharded markers, or JSON/JSONL conversation candidates found."
        )

    conversations = adapter.extract_conversations(inventory)
    if not conversations:
        logger.info(
            "OpenAI export import found no conversation records; orphaned_assets=%d",
            len(inventory.attachment_files),
        )
        return stats

    from backend.rag.chatgpt_migration import (
        ingest_chatgpt_conversation_records,
    )

    import_stats = ingest_chatgpt_conversation_records(
        conversations,
        user_id=user_id,
    )
    stats.update(import_stats)
    stats["conversation_records"] = len(conversations)
    return stats


def write_diagnostic_report(
    report: OpenAIExportDiagnosticReport, output_dir: str | Path
) -> OpenAIExportDiagnosticReport:
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "openai_export_diagnostic.json"
    summary_path = output_root / "openai_export_diagnostic.md"
    json_path.write_text(
        json.dumps(report.inventory.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_path.write_text(
        report.inventory.to_summary_text(),
        encoding="utf-8",
    )
    report.json_path = json_path
    report.summary_path = summary_path
    return report


def _magic_signature(sample: bytes) -> str:
    if not sample:
        return ""
    if sample.startswith(b"PK"):
        return "PK"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if sample.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if sample.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if sample.startswith(b"%PDF-"):
        return "PDF"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WEBP":
        return "WEBP"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WAVE":
        return "WAV"
    if sample[4:8] == b"ftyp":
        return "ISO-BMFF"
    if sample.startswith(b"\x1a\x45\xdf\xa3"):
        return "EBML"
    if sample.startswith(b"OggS"):
        return "OGG"
    if sample.startswith(b"fLaC"):
        return "FLAC"
    if sample.startswith(b"ID3"):
        return "ID3"
    return sample[:8].hex()


def _detect_magic_kind(sample: bytes) -> str | None:
    if sample.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image_png"
    if sample.startswith(b"\xff\xd8\xff"):
        return "image_jpeg"
    if sample.startswith((b"GIF87a", b"GIF89a")):
        return "image_gif"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WEBP":
        return "image_webp"
    if sample.startswith(b"%PDF-"):
        return "pdf"
    if sample[4:8] == b"ftyp":
        return "video_mp4"
    if sample.startswith(b"\x1a\x45\xdf\xa3"):
        return "video_webm"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WAVE":
        return "audio_wav"
    if sample.startswith(b"OggS"):
        return "audio_ogg"
    if sample.startswith(b"fLaC"):
        return "audio_flac"
    if sample.startswith(b"ID3") or (
        len(sample) > 2 and sample[0] == 0xFF and sample[1] & 0xE0 == 0xE0
    ):
        return "audio_mpeg"
    return None


def _looks_textual(sample: bytes) -> bool:
    try:
        text = sample[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "\x00" in text:
        return False
    return True


def _is_manifest_path(path: str) -> bool:
    """Check if a file path is inside a manifest metadata directory."""
    parts = Path(path).parts
    for pattern in _MANIFEST_DIR_PATTERNS:
        if pattern in parts:
            return True
    return False


def _has_conversation_payload(record: OpenAIExportFileRecord) -> bool:
    """Check that a conversations.json candidate contains actual conversation
    records, not file manifest entries."""
    if not record.conversation_candidate:
        return True  # Let schema detection handle non-candidates
    try:
        payload = _load_json_record(record)
    except Exception:
        return False
    return _payload_has_conversation_shape(payload) and not _payload_is_manifest(
        payload
    )


def _payload_is_manifest(payload: Any) -> bool:
    """Returns True if payload looks like a file manifest, not conversations."""
    if not isinstance(payload, (dict, list)):
        return False
    items = [payload] if isinstance(payload, dict) else payload[:5]
    for item in items:
        if not isinstance(item, dict):
            continue
        keys = set(str(key) for key in item.keys())
        # Strong manifest signals: multiple file-metadata keys with no conversation keys
        if len(keys & _MANIFEST_HINT_KEYS) >= 2 and not (
            keys & _CONVERSATION_HINT_KEYS
        ):
            return True
    return False


def _is_modern_marker(record: OpenAIExportFileRecord) -> bool:
    parts = Path(record.path).parts
    if record.extension == ".dat":
        return True
    for part in parts:
        lowered = part.lower()
        if lowered == "unassigned":
            return True
        if lowered.startswith("conversations__"):
            return True
        if lowered.startswith("workspace"):
            return True
    return Path(record.path).name.lower() == "report.html"


def _load_json_record(record: OpenAIExportFileRecord) -> Any:
    return json.loads(Path(record.absolute_path).read_text(encoding="utf-8-sig"))


def _iter_json_payloads(record: OpenAIExportFileRecord) -> Iterator[Any]:
    if record.detected_kind in {"json_object", "json_array"}:
        yield _load_json_record(record)
        return
    if record.detected_kind == "jsonl":
        with Path(record.absolute_path).open("r", encoding="utf-8-sig") as fh:
            for line in fh:
                raw = line.strip()
                if raw:
                    yield json.loads(raw)


def _payload_has_conversation_shape(payload: Any) -> bool:
    if isinstance(payload, dict):
        keys = set(str(key) for key in payload.keys())
        if "mapping" in keys or "messages" in keys:
            return True
        if len(keys & _CONVERSATION_HINT_KEYS) >= 3:
            return True
        for key in _CONVERSATION_CONTAINER_KEYS:
            nested = payload.get(key)
            if isinstance(nested, list) and any(
                _payload_has_conversation_shape(item) for item in nested[:5]
            ):
                return True
        return False
    if isinstance(payload, list):
        return any(_payload_has_conversation_shape(item) for item in payload[:5])
    return False


def _extract_conversation_records(
    payload: Any,
    *,
    source_path: str,
    export_format: str,
) -> list[dict[str, Any]]:
    conversations, message_records = _extract_conversation_payload(
        payload,
        source_path=source_path,
        export_format=export_format,
    )
    conversations.extend(
        _synthesize_conversations_from_message_records(
            message_records,
            export_format=export_format,
        )
    )
    return _dedupe_conversations(conversations)


def _extract_conversation_payload(
    payload: Any,
    *,
    source_path: str,
    export_format: str,
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]]]:
    conversations: list[dict[str, Any]] = []
    message_records: list[tuple[dict[str, Any], str]] = []

    if isinstance(payload, list):
        for item in payload:
            nested_conversations, nested_messages = _extract_conversation_payload(
                item,
                source_path=source_path,
                export_format=export_format,
            )
            conversations.extend(nested_conversations)
            message_records.extend(nested_messages)
        return conversations, message_records

    if not isinstance(payload, dict):
        return conversations, message_records

    if isinstance(payload.get("mapping"), dict):
        conv = dict(payload)
        _tag_conversation(conv, source_path=source_path, export_format=export_format)
        conversations.append(conv)
        return conversations, message_records

    messages = payload.get("messages")
    if isinstance(messages, list):
        conv = _synthesize_conversation_from_messages(
            payload,
            messages,
            source_path=source_path,
            export_format=export_format,
        )
        if conv:
            conversations.append(conv)
            return conversations, message_records

    if _looks_like_per_message_record(payload):
        message_records.append((payload, source_path))
        return conversations, message_records

    for key in _CONVERSATION_CONTAINER_KEYS:
        nested = payload.get(key)
        if not isinstance(nested, list):
            continue
        nested_conversations, nested_messages = _extract_conversation_payload(
            nested,
            source_path=source_path,
            export_format=export_format,
        )
        conversations.extend(nested_conversations)
        message_records.extend(nested_messages)

    return conversations, message_records


def _tag_conversation(
    conversation: dict[str, Any], *, source_path: str, export_format: str
) -> None:
    existing = conversation.get("_codexify_import_metadata")
    metadata = dict(existing) if isinstance(existing, dict) else {}
    metadata.update(
        {
            "openai_export_format": export_format,
            "openai_export_source_path": source_path,
        }
    )
    conversation["_codexify_import_metadata"] = metadata


def _looks_like_per_message_record(payload: dict[str, Any]) -> bool:
    if not (
        payload.get("conversation_id")
        or payload.get("thread_id")
        or payload.get("chat_id")
    ):
        return False
    if isinstance(payload.get("message"), dict):
        return True
    if payload.get("author") or payload.get("role") or payload.get("sender"):
        return bool(
            payload.get("content") is not None or payload.get("parts") is not None
        )
    return False


def _synthesize_conversations_from_message_records(
    records: list[tuple[dict[str, Any], str]],
    *,
    export_format: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[int, dict[str, Any], str]]] = {}
    for index, (record, source_path) in enumerate(records):
        conv_id = _coerce_nonempty(
            record.get("conversation_id")
            or record.get("thread_id")
            or record.get("chat_id")
        )
        if not conv_id:
            continue
        grouped.setdefault(conv_id, []).append((index, record, source_path))

    conversations: list[dict[str, Any]] = []
    for conv_id, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: (_timestamp_sort_key(row[1]), row[0]))
        container = {
            "id": conv_id,
            "conversation_id": conv_id,
            "title": _coerce_nonempty(rows[0][1].get("title"))
            or "Imported Chat",
        }
        messages = [row[1] for row in rows]
        source_path = rows[0][2]
        conv = _synthesize_conversation_from_messages(
            container,
            messages,
            source_path=source_path,
            export_format=export_format,
        )
        if conv:
            conversations.append(conv)
    return conversations


def _synthesize_conversation_from_messages(
    container: dict[str, Any],
    messages: list[Any],
    *,
    source_path: str,
    export_format: str,
) -> dict[str, Any] | None:
    source_thread_id = _coerce_nonempty(
        container.get("id")
        or container.get("conversation_id")
        or container.get("thread_id")
        or container.get("chat_id")
    )
    title = _coerce_nonempty(container.get("title") or container.get("name"))
    if not source_thread_id:
        source_thread_id = _build_stable_id(
            "openai-thread", source_path, title or "", messages
        )

    mapping: dict[str, dict[str, Any]] = {}
    parent: str | None = None
    for idx, raw_message in enumerate(messages, start=1):
        if not isinstance(raw_message, dict):
            continue
        message = _unwrap_message(raw_message)
        node_id = _coerce_nonempty(
            message.get("id")
            or message.get("message_id")
            or raw_message.get("id")
            or raw_message.get("message_id")
        )
        if not node_id:
            node_id = _build_stable_id(
                "openai-message", source_thread_id, idx, raw_message
            )

        role = _extract_role(raw_message, message)
        content = _extract_content(raw_message, message)
        create_time = _extract_create_time(raw_message, message)
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "id": node_id,
                "author": {"role": role},
                "content": content,
                "create_time": create_time,
            },
        }
        if parent and parent in mapping:
            mapping[parent]["children"].append(node_id)
        parent = node_id

    if not mapping:
        return None

    conversation = {
        "id": source_thread_id,
        "conversation_id": source_thread_id,
        "title": title or "Imported Chat",
        "current_node": parent,
        "create_time": _extract_create_time(container, container),
        "update_time": _extract_update_time(container),
        "mapping": mapping,
    }
    _tag_conversation(
        conversation, source_path=source_path, export_format=export_format
    )
    return conversation


def _unwrap_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    nested = raw_message.get("message")
    if isinstance(nested, dict):
        return nested
    return raw_message


def _extract_role(raw: dict[str, Any], message: dict[str, Any]) -> str:
    author = message.get("author")
    if isinstance(author, dict):
        role = _coerce_nonempty(author.get("role"))
        if role:
            return role
    for key in ("role", "sender", "author"):
        value = message.get(key, raw.get(key))
        if isinstance(value, dict):
            value = value.get("role") or value.get("name")
        role = _coerce_nonempty(value)
        if role:
            lowered = role.lower()
            if lowered in {"human"}:
                return "user"
            if lowered in {"model"}:
                return "assistant"
            return lowered
    return "user"


def _extract_content(raw: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content", raw.get("content"))
    if isinstance(content, dict):
        normalized = dict(content)
        if "parts" not in normalized and isinstance(normalized.get("text"), str):
            normalized["parts"] = [normalized["text"]]
        return normalized
    if isinstance(content, list):
        return {"content_type": "text", "parts": content}
    if isinstance(content, str):
        return {"content_type": "text", "parts": [content]}
    parts = message.get("parts", raw.get("parts"))
    if isinstance(parts, list):
        return {"content_type": "text", "parts": parts}
    text = message.get("text", raw.get("text"))
    if isinstance(text, str):
        return {"content_type": "text", "parts": [text]}
    return {"content_type": "text", "parts": []}


def _extract_create_time(raw: dict[str, Any], message: dict[str, Any]) -> float | None:
    for key in ("create_time", "created_at", "timestamp", "time", "createdAt"):
        value = message.get(key, raw.get(key))
        parsed = _coerce_epoch_seconds(value)
        if parsed is not None:
            return parsed
    return None


def _extract_update_time(container: dict[str, Any]) -> float | None:
    for key in ("update_time", "updated_at", "updatedAt"):
        parsed = _coerce_epoch_seconds(container.get(key))
        if parsed is not None:
            return parsed
    return _extract_create_time(container, container)


def _timestamp_sort_key(record: dict[str, Any]) -> float:
    message = _unwrap_message(record)
    value = _extract_create_time(record, message)
    return value if value is not None else float("inf")


def _coerce_epoch_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed / 1000.0 if parsed > 1_000_000_000_000 else parsed
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
            return parsed / 1000.0 if parsed > 1_000_000_000_000 else parsed
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    return None


def _coerce_nonempty(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _build_stable_id(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    prefix = str(parts[0] or "openai-id")
    return f"{prefix}-{digest}"


def _dedupe_conversations(
    conversations: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for conversation in conversations:
        source_id = _coerce_nonempty(
            conversation.get("id") or conversation.get("conversation_id")
        )
        if not source_id:
            source_id = _build_stable_id("openai-thread", conversation)
            conversation["id"] = source_id
            conversation["conversation_id"] = source_id
        if source_id not in deduped:
            deduped[source_id] = conversation
    return list(deduped.values())


def guess_mime_type(record: OpenAIExportFileRecord) -> str | None:
    kind_mimes = {
        "image_png": "image/png",
        "image_jpeg": "image/jpeg",
        "image_gif": "image/gif",
        "image_webp": "image/webp",
        "pdf": "application/pdf",
        "zip": "application/zip",
        "video_mp4": "video/mp4",
        "video_webm": "video/webm",
        "audio_wav": "audio/wav",
        "audio_ogg": "audio/ogg",
        "audio_flac": "audio/flac",
        "audio_mpeg": "audio/mpeg",
        "html": "text/html",
        "json_object": "application/json",
        "json_array": "application/json",
        "jsonl": "application/x-ndjson",
    }
    if record.detected_kind in kind_mimes:
        return kind_mimes[record.detected_kind]
    guessed, _encoding = mimetypes.guess_type(record.path)
    return guessed
