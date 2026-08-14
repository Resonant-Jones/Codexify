"""Anthropic source adapter for the existing Codexify account-import pipeline.

This module is a *source adapter*, not a second import product. It detects an
extracted Anthropic account-export root, normalizes its conversation corpus
through the existing Claude ingestion path (``backend.rag.chatgpt_migration``),
and preserves Anthropic source provenance via the established
``_codexify_import_metadata`` convention.

Invariants (must remain true after any future edit):

1. The adapter is a thin source-detection + conversation-normalization layer.
   It never writes directly to chat tables, never creates Codexify Projects,
   never mutates personal-facts / memory / persona state, and never produces
   media-asset rows.
2. The adapter does not invent a second worker, queue, job table, route, or
   persistence path. It exists to be called from the existing
   ``OpenAIAccountImportService`` / ``account_import_worker`` seams when an
   account-export job declares ``source_system="anthropic"``.
3. Anthropic ``projects/*.json``, ``users.json``, and ``memories.json`` are
   ignored by this slice. Their presence must not cause import failure, and
   they must not create any Codexify entity.
4. Anthropic ``files[]`` references carry only ``{file_uuid, file_name}``
   metadata with no recoverable bytes in the inspected export. The adapter
   never fabricates or infers media binaries; it preserves the raw source
   metadata through ``raw_message`` so downstream consumers can reason about
   it, but it does not call any media/asset write seam.
5. Provenance is structural: the adapter stamps
   ``_codexify_import_metadata.anthropic_export_format`` and
   ``_codexify_import_metadata.anthropic_export_source_path`` on every
   conversation record, mirroring the OpenAI adapter's pattern.
6. Persistence is delegated entirely to ``ingest_claude_export`` from
   ``backend.rag.chatgpt_migration``. The Claude role normalization, content
   extraction, and canonical message writer remain authoritative.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structural vocabulary (names only, never values)
# ---------------------------------------------------------------------------

# File names that may carry an Anthropic conversation corpus. Filenames alone
# are NOT enough to classify; the detector must validate that the candidate
# payload contains Anthropic conversation records with `chat_messages`.
_CANDIDATE_CONVERSATION_FILENAMES = (
    "conversations.json",
)

# Container / wrapper keys that may hold a list of conversation records.
# These mirror the keys already recognized by ``chatgpt_migration`` so the
# downstream Claude validator picks up the records without modification.
_CONVERSATION_WRAPPER_KEYS = (
    "conversations",
    "threads",
    "chats",
    "data",
)

# Required structural evidence inside a single conversation record. A record
# qualifies as an Anthropic conversation only when it has ``chat_messages``.
# Other Anthropic top-level keys (uuid, name, summary, created_at, updated_at,
# account) are accepted as additional evidence but not required.
_REQUIRED_CONVERSATION_KEYS = ("chat_messages",)

# Source-system token used to dispatch into the existing account-import
# intake. Matches the value the worker/service must accept.
SOURCE_SYSTEM = "anthropic"

# Provenance tag written into ``_codexify_import_metadata`` and stamped on
# every conversation record the adapter returns.
ANTHROPIC_IMPORT_PROFILE = "anthropic_v1_canonical"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnthropicExportFileRecord:
    """Lightweight file classification for the Anthropic detector."""

    path: str
    absolute_path: str
    size: int
    detected_kind: str  # one of: "json_array", "json_object", "jsonl", "non_json", "missing"


@dataclass(frozen=True)
class AnthropicExportInventory:
    """Bounded structural inventory for an Anthropic export root."""

    root_path: str
    files: tuple[AnthropicExportFileRecord, ...]
    conversation_files: tuple[AnthropicExportFileRecord, ...]
    conversation_candidate: bool
    detected_format: str  # "anthropic_legacy" | "unknown"
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "files": [
                {
                    "path": record.path,
                    "absolute_path": record.absolute_path,
                    "size": record.size,
                    "detected_kind": record.detected_kind,
                }
                for record in self.files
            ],
            "conversation_files": [record.path for record in self.conversation_files],
            "conversation_candidate": self.conversation_candidate,
            "detected_format": self.detected_format,
            "reason": self.reason,
        }


def _classify_json_payload(path: Path) -> str:
    """Classify a file's JSON shape without trusting its extension."""

    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return "non_json"

    stripped = text.lstrip()
    if not stripped:
        return "non_json"
    if stripped.startswith("["):
        return "json_array"
    if stripped.startswith("{"):
        # Distinguish a JSONL stream (one object per line) from a single object.
        line_count = sum(1 for line in text.splitlines() if line.strip())
        if line_count > 1:
            first_nonempty = next(
                (line for line in text.splitlines() if line.strip()), ""
            ).lstrip()
            if first_nonempty.startswith("{"):
                # Try parsing the first line; if it parses as JSON, treat as
                # JSONL. Anthropic exports do not currently ship JSONL
                # conversation files, but we recognize the shape honestly.
                try:
                    json.loads(first_nonempty)
                    return "jsonl"
                except json.JSONDecodeError:
                    pass
        return "json_object"
    return "non_json"


def _anthropic_payload_has_conversation(payload: Any) -> bool:
    """Validate that a parsed payload actually carries Anthropic conversation
    records (one or more entries with a ``chat_messages`` field)."""

    candidates: list[Any]
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        candidates = [payload]
        for wrapper_key in _CONVERSATION_WRAPPER_KEYS:
            nested = payload.get(wrapper_key)
            if isinstance(nested, list):
                candidates = nested
                break
    else:
        return False

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        if not all(key in entry for key in _REQUIRED_CONVERSATION_KEYS):
            continue
        chat_messages = entry.get("chat_messages")
        if not isinstance(chat_messages, list):
            continue
        # At least one message must be present. Empty conversations are valid
        # records but they don't constitute positive evidence of an Anthropic
        # corpus on their own; however, for the structural test we accept
        # records whose chat_messages is a list (even empty) when the top-level
        # shape is otherwise Anthropic-typed.
        return True
    return False


def _coerce_path(root: str | Path) -> Path:
    return Path(root).expanduser().resolve()


def scan_anthropic_export_root(root_path: str | Path) -> AnthropicExportInventory:
    """Walk an extracted Anthropic export root and produce a bounded inventory.

    The detector never scans outside ``root_path``. It classifies candidate
    JSON files by structural content, not by filename, and only reports a
    positive Anthropic detection when at least one candidate payload actually
    carries ``chat_messages``-bearing conversation records.
    """

    root = _coerce_path(root_path)
    if not root.exists():
        return AnthropicExportInventory(
            root_path=str(root),
            files=(),
            conversation_files=(),
            conversation_candidate=False,
            detected_format="unknown",
            reason="root_does_not_exist",
        )

    if root.is_file():
        files_iter: Iterable[Path] = [root]
        relative_root = root.parent
    else:
        files_iter = sorted(p for p in root.rglob("*") if p.is_file())
        relative_root = root

    records: list[AnthropicExportFileRecord] = []
    conversation_files: list[AnthropicExportFileRecord] = []

    for path in files_iter:
        try:
            rel = path.resolve().relative_to(relative_root).as_posix()
        except ValueError:
            rel = path.name
        try:
            size = path.stat().st_size
        except OSError:
            continue

        kind = _classify_json_payload(path)
        record = AnthropicExportFileRecord(
            path=rel,
            absolute_path=str(path),
            size=size,
            detected_kind=kind,
        )
        records.append(record)

        if record.detected_kind in {"json_array", "json_object", "jsonl"}:
            # Validate structurally: a real Anthropic payload must carry
            # ``chat_messages`` records somewhere in the structure.
            try:
                text = path.read_text(encoding="utf-8-sig")
                if record.detected_kind == "jsonl":
                    parsed_first = next(
                        (
                            json.loads(line)
                            for line in text.splitlines()
                            if line.strip()
                        ),
                        None,
                    )
                    parsed: Any = parsed_first
                else:
                    parsed = json.loads(text)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
            if _anthropic_payload_has_conversation(parsed):
                conversation_files.append(record)

    candidate = bool(conversation_files)
    return AnthropicExportInventory(
        root_path=str(root),
        files=tuple(records),
        conversation_files=tuple(conversation_files),
        conversation_candidate=candidate,
        detected_format="anthropic_legacy" if candidate else "unknown",
        reason=(
            "anthropic_chat_messages_payload_found"
            if candidate
            else "no_anthropic_chat_messages_payload"
        ),
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnthropicExtractedConversation:
    """One normalized Anthropic conversation record.

    Carries the parsed conversation dict plus its source-path provenance so
    downstream code can attach ``_codexify_import_metadata`` and route to the
    existing Claude ingestion entrypoint without any DB write at this layer.
    """

    conversation: dict[str, Any]
    source_path: str


@dataclass
class AnthropicImportResult:
    """Bounded result returned by ``import_anthropic_export_path``."""

    conversations_discovered: int = 0
    conversations_imported: int = 0
    conversations_failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversations_discovered": self.conversations_discovered,
            "conversations_imported": self.conversations_imported,
            "conversations_failed": self.conversations_failed,
            "errors": list(self.errors),
        }


def _normalize_conversation_record(
    conv: dict[str, Any], *, source_path: str
) -> dict[str, Any]:
    """Return a defensive copy of the conversation with provenance attached.

    The adapter does not invent fields. It only stamps
    ``_codexify_import_metadata`` on the conversation record (mirroring the
    OpenAI adapter's pattern at ``openai_export_adapter.py`` line ~1126) and
    forwards the original conversation to the Claude ingestion path.
    """

    # Shallow copy is sufficient: the Claude ingestion path is read-only on
    # this dict; it normalizes from here without mutating it.
    normalized = dict(conv)
    existing = normalized.get("_codexify_import_metadata")
    metadata = dict(existing) if isinstance(existing, dict) else {}
    metadata.update(
        {
            "anthropic_export_format": "anthropic_legacy",
            "anthropic_export_source_path": source_path,
            "anthropic_import_profile": ANTHROPIC_IMPORT_PROFILE,
        }
    )
    normalized["_codexify_import_metadata"] = metadata
    return normalized


def extract_anthropic_conversations(
    inventory: AnthropicExportInventory,
) -> list[AnthropicExtractedConversation]:
    """Read every positively-detected conversation corpus file and return the
    conversation records inside it, each tagged with its source path.

    The function is read-only: it does not write anywhere. ``projects/``,
    ``users.json``, and ``memories.json`` are not part of the inventory's
    ``conversation_files`` and are therefore ignored here.

    Records are returned in the natural file-order of the inventory so the
    caller can preserve deterministic ordering.
    """

    results: list[AnthropicExtractedConversation] = []
    for record in inventory.conversation_files:
        try:
            text = Path(record.absolute_path).read_text(encoding="utf-8-sig")
            payload: Any = json.loads(text)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(
                "anthropic_export_adapter: skipping unreadable corpus file=%s",
                record.path,
            )
            continue

        candidates: list[Any]
        if isinstance(payload, list):
            candidates = payload
        elif isinstance(payload, dict):
            candidates = [payload]
            for wrapper_key in _CONVERSATION_WRAPPER_KEYS:
                nested = payload.get(wrapper_key)
                if isinstance(nested, list):
                    candidates = nested
                    break
        else:
            continue

        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            if not all(key in entry for key in _REQUIRED_CONVERSATION_KEYS):
                continue
            results.append(
                AnthropicExtractedConversation(
                    conversation=entry,
                    source_path=record.path,
                )
            )
    return results


def import_anthropic_export_path(
    root_path: str | Path,
    *,
    user_id: str,
) -> AnthropicImportResult:
    """Detect, extract, and persist an Anthropic account-export conversation
    corpus through the existing Claude ingestion entrypoint.

    The function never writes to the chat / thread / message tables directly.
    It delegates persistence to ``backend.rag.chatgpt_migration.ingest_claude_export``,
    which is the authoritative Claude normalization + canonical writer. The
    adapter's only responsibility is to feed that writer with the conversation
    records it expects, with provenance attached.

    Returns an ``AnthropicImportResult`` describing bounded per-job outcomes
    suitable for the worker to translate into ``source_summary`` evidence.
    """

    inventory = scan_anthropic_export_root(root_path)
    if not inventory.conversation_candidate:
        return AnthropicImportResult(
            conversations_discovered=0,
            conversations_imported=0,
            conversations_failed=0,
            errors=[
                (
                    "Anthropic export root did not contain a chat_messages-bearing "
                    "conversation corpus: "
                    f"{inventory.reason}"
                )
            ],
        )

    extracted = extract_anthropic_conversations(inventory)
    if not extracted:
        return AnthropicImportResult(
            conversations_discovered=0,
            conversations_imported=0,
            conversations_failed=0,
            errors=[
                "Anthropic detector found candidate files but no parseable "
                "conversation records could be extracted."
            ],
        )

    # Defer the import to avoid an import cycle at module load (the
    # chatgpt_migration module imports backend.rag.* helpers). The import is
    # cheap and only happens on actual invocation.
    from backend.rag.chatgpt_migration import ingest_claude_export

    result = AnthropicImportResult(conversations_discovered=len(extracted))

    # The Claude ingestion entrypoint expects the full ``[conversations]``
    # payload shape in raw bytes (it re-parses internally). Round-tripping
    # through JSON keeps a single normalization contract without forcing a
    # deep refactor of the canonical writer.
    payload_bytes = json.dumps(
        [
            _normalize_conversation_record(
                item.conversation, source_path=item.source_path
            )
            for item in extracted
        ],
        ensure_ascii=False,
    ).encode("utf-8")

    try:
        stats = ingest_claude_export(payload_bytes, user_id=user_id)
    except Exception as exc:  # pragma: no cover - adapter contract surface
        logger.exception(
            "anthropic_export_adapter: ingest_claude_export failed user_id=%s", user_id
        )
        result.conversations_failed = len(extracted)
        result.errors.append(f"ingest_claude_export_failed: {exc}")
        return result

    result.conversations_imported = int(stats.get("threads_imported", 0))
    return result
