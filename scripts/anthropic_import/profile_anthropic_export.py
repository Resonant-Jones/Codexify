#!/usr/bin/env python3
"""Read-only Anthropic account-export profiler.

This is fixture archaeology, not an importer. It inspects a real Anthropic
account export (ZIP archive, extracted directory, or individual JSON file) and
emits a deterministic structural evidence report. It never imports data, never
writes to any Codexify runtime store, never invokes the existing Claude or
OpenAI importers, and never mutates the source package.

The report describes schema *shape* only. It never carries message text,
conversation titles, project or account names, email addresses, UUIDs, IDs,
URLs, prompts, or attachment contents. Only a small explicit allowlist of
structural scalar values (role/sender labels, content-block type labels, coarse
timestamp format categories, safe booleans, and detected file types) may be
aggregated. Everything else is key names and counts.

Profiler output is *observed evidence*, not an Anthropic schema contract, and it
does not widen Codexify's supported release promise. Durable Anthropic account
import remains deferred.

Standard-library only by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Sequence

# --------------------------------------------------------------------------
# Report identity
# --------------------------------------------------------------------------

REPORT_SCHEMA = "anthropic_export_profile_report_v1"
PROFILER_VERSION = "1"

# --------------------------------------------------------------------------
# Exit codes
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNSAFE = 3

# --------------------------------------------------------------------------
# Safety limits (conservative defaults). All enforced; overflow is reported,
# never silently dropped.
# --------------------------------------------------------------------------

MAX_PACKAGE_FILE_COUNT = 50_000
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_UNIQUE_KEYS_PER_SCOPE = 2_000
MAX_WARNINGS = 200
MAX_ROLE_VALUE_DISTINCT = 32
MAX_CONTENT_BLOCK_TYPE_DISTINCT = 200
MAX_CANDIDATE_EVIDENCE_KEYS = 50
MAX_CAPABILITY_EVIDENCE = 25
MAX_TOP_LEVEL_KEYS_DISPLAY = 500
MAX_UNKNOWN_RELATIVE_PATHS = 100
MAX_UNKNOWN_KEY_NAMES = 200

SAMPLE_BYTES = 1024 * 1024
READ_CHUNK = 65536

# --------------------------------------------------------------------------
# Structural vocabulary. These are key *names* and type *labels* only.
# Recognizing them never emits the values that hang off the keys.
# --------------------------------------------------------------------------

# Message-container keys already understood by Codexify's Claude path plus a
# generic fallback used to detect unknown alternatives.
MESSAGE_CONTAINER_KEYS = ("chat_messages", "messages", "conversation", "entries")

# Identifier value scrubbing for paths. Anthropic shards some record families
# as one file per record using a UUID filename. Relative package paths are
# allowed for structural inventory, but an embedded UUID is an identity value,
# so UUID-shaped path stems are redacted while preserving directory shape,
# extension, and deterministic uniqueness.
UUID_SEGMENT_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


# Wrapper keys that may hold a collection of conversation/record objects.
COLLECTION_WRAPPER_KEYS = (
    "conversations",
    "threads",
    "chats",
    "items",
    "data",
    "projects",
    "memories",
    "users",
    "user",
    "account",
    "artifacts",
)

ROLE_VALUE_FIELDS = ("sender", "role")
ROLE_FIELD_NAMES = ("sender", "role", "author", "type")

CONTENT_BLOCK_TYPE_KEYS = ("type", "content_type")
KNOWN_CONTENT_BLOCK_TYPES = {
    "text",
    "markdown",
    "tool_use",
    "tool_result",
    "tool",
    "server_tool_use",
    "server_tool_result",
    "web_search_tool_result",
    "image",
    "attachment",
    "file",
    "thinking",
    "code",
    "plan",
}

# Branch / parent relationship fields. Explicit candidates plus unknown
# alternatives beginning with "parent".
PARENT_FIELD_EXPLICIT = (
    "parent_message_uuid",
    "parent_uuid",
    "parent_message_id",
    "parent_id",
)

TS_FIELD_EXPLICIT = {
    "created_at",
    "updated_at",
    "timestamp",
    "createdat",
    "updatedat",
    "create_time",
    "update_time",
    "time",
    "date",
    "published_at",
    "expires_at",
    "deleted_at",
    "sent_at",
    "modified_at",
}

# Regex classifiers for structural field families. These match *names*, never
# values.
IDENTIFIER_NAME_RE = re.compile(
    r"^(id|uuid|uid|key|guid)$|(_id|_uuid|_uid|_key|_guid)$", re.IGNORECASE
)
PARENT_NAME_RE = re.compile(r"^parent", re.IGNORECASE)
PROJECT_NAME_RE = re.compile(r"^project", re.IGNORECASE)
MODEL_NAME_RE = re.compile(r"^(model|provider)", re.IGNORECASE)
ATTACHMENT_NAME_RE = re.compile(
    r"(file|attachment|upload|asset|image|document)", re.IGNORECASE
)
GENERATION_NAME_RE = re.compile(r"^(generat|dalle)", re.IGNORECASE)
ARTIFACT_NAME_RE = re.compile(r"^artifact", re.IGNORECASE)
MEMORY_NAME_RE = re.compile(r"^memor", re.IGNORECASE)
ACCOUNT_NAME_RE = re.compile(
    r"^(user|account|profile|organization|organisation|email|member|person)", re.IGNORECASE
)
TS_NAME_RE = re.compile(
    r"((_at|at|time|date|timestamp)$)|^(time|date|timestamp)", re.IGNORECASE
)

# Safe scalar-value sanitizers. These permit only short structural labels.
ROLE_VALUE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
BLOCK_TYPE_RE = re.compile(r"^[A-Za-z0-9_.\-/ ]{1,48}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class UsageError(ValueError):
    """Invalid arguments, missing input, unsupported input, unwritable output."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class UnsafePackageError(ValueError):
    """Structural integrity rejection: traversal, symlink, duplicate, corruption."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# Path normalization (mirrors Codexify's import-path rules, stdlib only)
# --------------------------------------------------------------------------


def normalize_member_path(value: str) -> str:
    """Return a canonical POSIX relative path or reject unsafe input."""

    raw = unicodedata.normalize("NFC", str(value or "").replace("\\", "/").strip())
    if not raw or "\x00" in raw:
        raise UnsafePackageError(
            "Member path is empty or contains a null byte.",
            code="invalid_member_path",
        )
    if raw.startswith("/") or _WINDOWS_DRIVE_RE.match(raw):
        raise UnsafePackageError(
            "Absolute member paths are not allowed.",
            code="absolute_path_rejected",
        )
    if any(part == ".." for part in raw.split("/")):
        raise UnsafePackageError(
            "Member path traversal is not allowed.",
            code="path_traversal_rejected",
        )
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if not parts:
        raise UnsafePackageError(
            "Member path is empty after normalization.",
            code="empty_member_path",
        )
    return PurePosixPath(*parts).as_posix()


def _redact_path_segment(segment: str) -> str:
    """Redact UUID-shaped stems inside a single path segment."""

    if "." in segment:
        stem, dot, ext = segment.rpartition(".")
        ext = dot + ext
    else:
        stem, ext = segment, ""
    if not stem:
        return segment
    return UUID_SEGMENT_RE.sub("<uuid>", stem) + ext


def build_path_redaction(relpaths: list[str]) -> dict[str, str]:
    """Map original relative paths to identity-scrubbed, collision-free paths.

    Non-identifier paths pass through unchanged. UUID-shaped stems are replaced
    with ``<uuid>``; if that collides, a deterministic numeric suffix is added
    before the extension so structural inventory stays unique and stable.
    """

    groups: dict[str, list[str]] = {}
    for original in sorted(set(relpaths)):
        redacted = "/".join(
            _redact_path_segment(seg) for seg in original.split("/")
        )
        groups.setdefault(redacted, []).append(original)

    mapping: dict[str, str] = {}
    for redacted, originals in groups.items():
        originals = sorted(originals)
        if len(originals) == 1:
            mapping[originals[0]] = redacted
            continue
        for index, original in enumerate(originals, start=1):
            dot_index = redacted.rfind(".")
            if "/" not in redacted[dot_index:] and dot_index > redacted.rfind("/"):
                mapped = redacted[:dot_index] + f".{index}" + redacted[dot_index:]
            else:
                mapped = f"{redacted}.{index}"
            mapping[original] = mapped
    return mapping


# --------------------------------------------------------------------------
# Magic / broad-type detection (content-based, never extension-only)
# --------------------------------------------------------------------------


def _detect_magic_kind(sample: bytes) -> str | None:
    if sample.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "archive"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if sample.startswith(b"\xff\xd8\xff"):
        return "image"
    if sample.startswith((b"GIF87a", b"GIF89a")):
        return "image"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WEBP":
        return "image"
    if sample.startswith(b"%PDF-"):
        return "pdf"
    if sample[4:8] == b"ftyp":
        return "video"
    if sample.startswith(b"\x1a\x45\xdf\xa3"):
        return "video"
    if sample.startswith(b"RIFF") and sample[8:12] == b"WAVE":
        return "audio"
    if sample.startswith(b"OggS"):
        return "audio"
    if sample.startswith(b"fLaC"):
        return "audio"
    if sample.startswith(b"ID3") or (
        len(sample) > 2 and sample[0] == 0xFF and sample[1] & 0xE0 == 0xE0
    ):
        return "audio"
    return None


def _looks_textual(sample: bytes) -> bool:
    try:
        text = sample[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "\x00" in text:
        return False
    return True


def _broad_type(sample: bytes) -> str:
    """Return a coarse, content-derived broad file type."""

    if not sample:
        return "empty"
    magic = _detect_magic_kind(sample)
    if magic is not None:
        return magic
    stripped = sample.lstrip()
    lowered = stripped[:256].lower()
    if lowered.startswith((b"<!doctype html", b"<html", b"<!--")):
        return "text"
    if stripped[:1] in {b"{", b"["}:
        return "json"
    if _looks_textual(sample):
        if lowered.startswith(b"<"):
            return "text"
        return "text"
    return "unknown_binary"


def _extension_of(name: str) -> str:
    return PurePosixPath(name).suffix.lower()


# --------------------------------------------------------------------------
# Streaming reader for a single member
# --------------------------------------------------------------------------


@dataclass
class MemberBytes:
    size: int
    sha256: str
    sample: bytes
    buffered: bytes
    full_buffer_available: bool


def _stream_member(open_callable: Callable[[], Any]) -> MemberBytes:
    """Stream a member computing sha/size with bounded memory.

    ``sample`` holds the first ``SAMPLE_BYTES`` for type detection. ``buffered``
    holds up to ``MAX_MEMBER_BYTES`` for JSON parsing; ``full_buffer_available``
    is False when the member exceeded that cap (JSON analysis is then skipped).
    """

    digest = hashlib.sha256()
    size = 0
    sample = bytearray()
    buffered = bytearray()
    with open_callable() as handle:
        while True:
            chunk = handle.read(READ_CHUNK)
            if not chunk:
                break
            if isinstance(chunk, str):  # defensive; binary streams expected
                chunk = chunk.encode("utf-8")
            size += len(chunk)
            digest.update(chunk)
            if len(sample) < SAMPLE_BYTES:
                sample.extend(chunk[: SAMPLE_BYTES - len(sample)])
            room = MAX_MEMBER_BYTES - len(buffered)
            if room > 0:
                buffered.extend(chunk[:room])
    return MemberBytes(
        size=size,
        sha256=digest.hexdigest(),
        sample=bytes(sample),
        buffered=bytes(buffered),
        full_buffer_available=size <= MAX_MEMBER_BYTES,
    )


# --------------------------------------------------------------------------
# Scanned file record
# --------------------------------------------------------------------------


@dataclass
class ScannedFile:
    relative_path: str
    size_bytes: int
    sha256: str
    extension: str
    broad_type: str
    json_parse_status: str  # ok | failed | not_json | skipped
    json_top_level_type: str  # object | array | scalar | none
    json_top_level_keys: list[str]
    compressed_size_bytes: int | None = None
    parsed: Any = None


# --------------------------------------------------------------------------
# Structural collector
# --------------------------------------------------------------------------


def _sorted_counter(counter: dict[str, int]) -> list[dict[str, Any]]:
    return [{"key": key, "count": int(counter[key])} for key in sorted(counter)]


class ShapeCollector:
    """Accumulates structural evidence only. Never stores raw user values."""

    def __init__(self) -> None:
        self.conversations_observed = False
        self.candidate_conversation_count = 0
        self._conversation_keys: dict[str, int] = {}
        self._message_container_keys: dict[str, int] = {}
        self._message_keys: dict[str, int] = {}
        self._role_fields: dict[str, int] = {}
        self._role_values: dict[str, int] = {}
        self._timestamp_fields: dict[str, int] = {}
        self._timestamp_formats: dict[str, int] = {}
        self._identifier_fields: dict[str, int] = {}
        self._model_fields: dict[str, int] = {}
        self._project_ref_fields: dict[str, int] = {}
        self._parent_fields: dict[str, int] = {}
        self._attachment_fields: dict[str, int] = {}
        self._content_block_types: dict[str, int] = {}
        self._unknown_content_block_types: dict[str, int] = {}
        self._unknown_message_keys: dict[str, int] = {}

        # capability evidence: name -> list of {relative_path, structural_keys}
        self._capability_evidence: dict[str, list[dict[str, Any]]] = {}
        self._capability_observed: dict[str, bool] = {}

        # candidate surfaces: list of {relative_path, classification, evidence_keys}
        self.candidate_surfaces: list[dict[str, Any]] = []

        # unknown top-level shapes (parsed JSON that matched nothing)
        self._unknown_json_shapes: list[str] = []

    # -- bounded helpers --------------------------------------------------

    def _bump(self, store: dict[str, int], key: str) -> None:
        if len(store) >= MAX_UNIQUE_KEYS_PER_SCOPE and key not in store:
            return
        store[key] = store.get(key, 0) + 1

    def _bump_value(
        self, store: dict[str, int], key: str, *, distinct_cap: int
    ) -> None:
        if len(store) >= distinct_cap and key not in store:
            return
        store[key] = store.get(key, 0) + 1

    # -- conversation / message recording --------------------------------

    def mark_conversation(self) -> None:
        self.conversations_observed = True
        self.candidate_conversation_count += 1

    def add_conversation_key(self, key: str) -> None:
        self._bump(self._conversation_keys, str(key))

    def add_message_container_key(self, key: str) -> None:
        self._bump(self._message_container_keys, str(key))

    def add_message_key(self, key: str) -> None:
        self._bump(self._message_keys, str(key))

    def add_role_field(self, key: str) -> None:
        self._bump(self._role_fields, str(key))

    def add_role_value(self, value: str) -> None:
        self._bump_value(
            self._role_values, str(value), distinct_cap=MAX_ROLE_VALUE_DISTINCT
        )

    def add_timestamp_field(self, key: str, category: str) -> None:
        self._bump(self._timestamp_fields, str(key))
        self._bump(self._timestamp_formats, str(category))

    def add_identifier_field(self, key: str) -> None:
        self._bump(self._identifier_fields, str(key))

    def add_model_field(self, key: str) -> None:
        self._bump(self._model_fields, str(key))

    def add_project_ref_field(self, key: str) -> None:
        self._bump(self._project_ref_fields, str(key))

    def add_parent_field(self, key: str) -> None:
        self._bump(self._parent_fields, str(key))

    def add_attachment_field(self, key: str) -> None:
        self._bump(self._attachment_fields, str(key))

    def add_content_block_type(self, value: str) -> None:
        label = str(value)
        if label in KNOWN_CONTENT_BLOCK_TYPES:
            self._bump_value(
                self._content_block_types,
                label,
                distinct_cap=MAX_CONTENT_BLOCK_TYPE_DISTINCT,
            )
        else:
            self._bump_value(
                self._unknown_content_block_types,
                label,
                distinct_cap=MAX_CONTENT_BLOCK_TYPE_DISTINCT,
            )

    def add_unknown_message_key(self, key: str) -> None:
        self._bump_value(
            self._unknown_message_keys,
            str(key),
            distinct_cap=MAX_UNKNOWN_KEY_NAMES,
        )

    def add_unknown_json_shape(self, relative_path: str) -> None:
        if len(self._unknown_json_shapes) < MAX_UNKNOWN_RELATIVE_PATHS:
            self._unknown_json_shapes.append(relative_path)

    # -- capabilities -----------------------------------------------------

    def note_capability(
        self, name: str, *, relative_path: str, structural_keys: list[str]
    ) -> None:
        self._capability_observed[name] = True
        bucket = self._capability_evidence.setdefault(name, [])
        if len(bucket) >= MAX_CAPABILITY_EVIDENCE:
            return
        entry = {
            "relative_path": relative_path,
            "structural_keys": sorted(dict.fromkeys(structural_keys))[
                :MAX_CANDIDATE_EVIDENCE_KEYS
            ],
        }
        if entry not in bucket:
            bucket.append(entry)

    def add_candidate_surface(
        self,
        *,
        relative_path: str,
        classification: str,
        evidence_keys: list[str],
    ) -> None:
        self.candidate_surfaces.append(
            {
                "relative_path": relative_path,
                "classification": classification,
                "evidence_keys": sorted(dict.fromkeys(evidence_keys))[
                    :MAX_CANDIDATE_EVIDENCE_KEYS
                ],
            }
        )

    # -- finalize ---------------------------------------------------------

    def capability_payload(self) -> dict[str, Any]:
        names = [
            "flat_conversation_array",
            "nested_conversation_container",
            "message_parent_links",
            "project_records",
            "conversation_project_links",
            "account_metadata",
            "memory_records",
            "attachment_references",
            "binary_payloads",
            "generated_file_evidence",
            "artifact_evidence",
        ]
        payload: dict[str, Any] = {}
        for name in names:
            observed = self._capability_observed.get(name, False)
            payload[name] = {
                "observed": bool(observed),
                "evidence": self._capability_evidence.get(name, []),
            }
        return payload

    def conversation_shape_payload(self) -> dict[str, Any]:
        return {
            "conversations_observed": bool(self.conversations_observed),
            "candidate_conversation_count": int(self.candidate_conversation_count),
            "conversation_object_keys": _sorted_counter(self._conversation_keys),
            "message_container_keys": _sorted_counter(self._message_container_keys),
            "message_object_keys": _sorted_counter(self._message_keys),
            "role_field_names": _sorted_counter(self._role_fields),
            "role_values": _sorted_counter(self._role_values),
            "timestamp_field_names": _sorted_counter(self._timestamp_fields),
            "timestamp_format_categories": _sorted_counter(self._timestamp_formats),
            "identifier_field_names": _sorted_counter(self._identifier_fields),
            "model_field_names": _sorted_counter(self._model_fields),
            "project_reference_field_names": _sorted_counter(
                self._project_ref_fields
            ),
            "parent_relationship_field_names": _sorted_counter(self._parent_fields),
            "attachment_reference_field_names": _sorted_counter(
                self._attachment_fields
            ),
            "content_block_types": _sorted_counter(self._content_block_types),
        }

    def unknown_structures_payload(self) -> dict[str, Any]:
        return {
            "unknown_json_shapes": {
                "count": len(self._unknown_json_shapes),
                "relative_paths": list(self._unknown_json_shapes),
            },
            "unknown_content_block_types": _sorted_counter(
                self._unknown_content_block_types
            ),
            "unknown_message_keys": _sorted_counter(self._unknown_message_keys),
        }


# --------------------------------------------------------------------------
# Field classification (names only)
# --------------------------------------------------------------------------


def _is_timestamp_field(name: str) -> bool:
    return name in TS_FIELD_EXPLICIT or bool(TS_NAME_RE.search(name))


def _is_identifier_field(name: str) -> bool:
    return bool(IDENTIFIER_NAME_RE.search(name))


def _is_parent_field(name: str) -> bool:
    return name in PARENT_FIELD_EXPLICIT or bool(PARENT_NAME_RE.match(name))


def _is_project_field(name: str) -> bool:
    return bool(PROJECT_NAME_RE.match(name))


def _is_model_field(name: str) -> bool:
    return bool(MODEL_NAME_RE.match(name))


def _is_attachment_field(name: str) -> bool:
    return bool(ATTACHMENT_NAME_RE.search(name))


def _is_generation_field(name: str) -> bool:
    return bool(GENERATION_NAME_RE.match(name))


def _is_artifact_field(name: str) -> bool:
    return bool(ARTIFACT_NAME_RE.match(name))


def _is_memory_field(name: str) -> bool:
    return bool(MEMORY_NAME_RE.match(name))


def _is_account_field(name: str) -> bool:
    return bool(ACCOUNT_NAME_RE.match(name))


def _timestamp_category(value: Any) -> str:
    if isinstance(value, bool):
        return "unknown"
    if isinstance(value, (int, float)):
        return "epoch_millis" if float(value) > 1_000_000_000_000 else "epoch_seconds"
    if isinstance(value, str):
        stripped = value.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", stripped):
            return "iso8601"
        if re.fullmatch(r"\d+(\.\d+)?", stripped):
            return (
                "epoch_millis"
                if float(stripped) > 1_000_000_000_000
                else "epoch_seconds"
            )
        return "unknown"
    return "unknown"


def _sanitize_role_value(value: Any) -> str | None:
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        return None
    if isinstance(value, (int, float)):
        return None
    text = str(value).strip().lower()
    if ROLE_VALUE_RE.match(text):
        return text
    return None


def _content_block_type(part: Any) -> str | None:
    if not isinstance(part, dict):
        return None
    for key in CONTENT_BLOCK_TYPE_KEYS:
        if key in part:
            label = str(part[key]).strip().lower()
            if BLOCK_TYPE_RE.match(label):
                return label
    return None


# --------------------------------------------------------------------------
# Structural analysis
# --------------------------------------------------------------------------


def _is_message_like(obj: dict[str, Any]) -> bool:
    keys = {str(k) for k in obj.keys()}
    if keys & {"sender", "role", "author"}:
        return True
    if (keys & {"content", "text"}) and (keys & {"sender", "role", "author", "type"}):
        return True
    return False


def _find_message_container(obj: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
    """Return (container_key, messages) for the first message-bearing list."""

    for key in MESSAGE_CONTAINER_KEYS:
        value = obj.get(key)
        if isinstance(value, list):
            msgs = [m for m in value if isinstance(m, dict)]
            if msgs:
                return key, msgs
    # Unknown container alternatives: any list of message-like dicts.
    for key, value in obj.items():
        if not isinstance(value, list) or not value:
            continue
        if key in MESSAGE_CONTAINER_KEYS:
            continue
        sample = [m for m in value if isinstance(m, dict)]
        if sample and any(_is_message_like(m) for m in sample[:3]):
            return key, sample
    return None, []


def _analyze_message(
    message: dict[str, Any],
    *,
    collector: ShapeCollector,
    relative_path: str,
    depth_budget: list[int],
) -> None:
    keys = [str(k) for k in message.keys()]
    key_set = set(keys)
    for key in keys:
        collector.add_message_key(key)

    # Role field + bounded role value (sender/role only).
    role_field = None
    for field_name in ROLE_VALUE_FIELDS:
        if field_name in key_set:
            role_field = field_name
            collector.add_role_field(field_name)
            sanitized = _sanitize_role_value(message.get(field_name))
            if sanitized:
                collector.add_role_value(sanitized)
            break
    if role_field is None:
        for field_name in ("author", "type"):
            if field_name in key_set:
                collector.add_role_field(field_name)
                break

    structural_key_seen: list[str] = []

    for key in keys:
        value = message.get(key)
        if _is_timestamp_field(key):
            collector.add_timestamp_field(key, _timestamp_category(value))
            structural_key_seen.append(key)
        if _is_identifier_field(key):
            collector.add_identifier_field(key)
        if _is_model_field(key):
            collector.add_model_field(key)
            structural_key_seen.append(key)
        if _is_parent_field(key):
            collector.add_parent_field(key)
            collector.note_capability(
                "message_parent_links",
                relative_path=relative_path,
                structural_keys=[key],
            )
            structural_key_seen.append(key)
        if _is_project_field(key):
            collector.add_project_ref_field(key)
            structural_key_seen.append(key)
        if _is_attachment_field(key):
            collector.add_attachment_field(key)
            collector.note_capability(
                "attachment_references",
                relative_path=relative_path,
                structural_keys=[key],
            )
            structural_key_seen.append(key)
        if _is_generation_field(key):
            collector.note_capability(
                "generated_file_evidence",
                relative_path=relative_path,
                structural_keys=[key],
            )
            structural_key_seen.append(key)
        if _is_artifact_field(key):
            collector.note_capability(
                "artifact_evidence",
                relative_path=relative_path,
                structural_keys=[key],
            )
            structural_key_seen.append(key)

    # Content blocks (structured content). Type labels only.
    content = message.get("content")
    if isinstance(content, list) and depth_budget[0] > 0:
        depth_budget[0] -= 1
        for part in content:
            label = _content_block_type(part)
            if label:
                collector.add_content_block_type(label)
            if isinstance(part, dict):
                for part_key in part.keys():
                    if _is_attachment_field(str(part_key)):
                        collector.note_capability(
                            "attachment_references",
                            relative_path=relative_path,
                            structural_keys=[str(part_key)],
                        )
                    if _is_generation_field(str(part_key)):
                        collector.note_capability(
                            "generated_file_evidence",
                            relative_path=relative_path,
                            structural_keys=[str(part_key)],
                        )
                    if _is_artifact_field(str(part_key)):
                        collector.note_capability(
                            "artifact_evidence",
                            relative_path=relative_path,
                            structural_keys=[str(part_key)],
                        )


def _analyze_conversation(
    conversation: dict[str, Any],
    *,
    collector: ShapeCollector,
    relative_path: str,
    root_container: str | None,
) -> None:
    collector.mark_conversation()
    if root_container is not None:
        collector.add_message_container_key(root_container)

    conv_keys = [str(k) for k in conversation.keys()]
    for key in conv_keys:
        collector.add_conversation_key(key)
        if _is_project_field(key):
            collector.add_project_ref_field(key)
            collector.note_capability(
                "conversation_project_links",
                relative_path=relative_path,
                structural_keys=[key],
            )

    container_key, messages = _find_message_container(conversation)
    if container_key is not None:
        collector.add_message_container_key(container_key)
    for message in messages:
        depth_budget = [MAX_JSON_DEPTH]
        _analyze_message(
            message,
            collector=collector,
            relative_path=relative_path,
            depth_budget=depth_budget,
        )


def _classify_record_dict(obj: dict[str, Any]) -> set[str]:
    """Return candidate surface classifications for a record dict."""

    keys = {str(k) for k in obj.keys()}
    classes: set[str] = set()
    container_key, _messages = _find_message_container(obj)
    if container_key is not None or _is_message_like(obj):
        classes.add("conversations")
    project_hits = sum(1 for k in keys if _is_project_field(k))
    if project_hits >= 1 and any(k in keys for k in ("name", "description")):
        classes.add("projects")
    if any(_is_memory_field(k) for k in keys):
        classes.add("memories")
    if any(_is_account_field(k) for k in keys):
        classes.add("users_or_account")
    if any(_is_artifact_field(k) for k in keys):
        classes.add("artifacts")
    return classes


# Directory names that constitute observed structural evidence for a record
# family when an export shards records as one object file per record (for
# example Anthropic's ``projects/<uuid>.json`` layout).
RECORD_FAMILY_DIRS = {
    "projects": ("projects", "project_records"),
    "memories": ("memories", "memory_records"),
    "users": ("users_or_account", "account_metadata"),
    "user": ("users_or_account", "account_metadata"),
    "account": ("users_or_account", "account_metadata"),
    "artifacts": ("artifacts", "artifact_evidence"),
}


def _directory_family(relative_path: str) -> tuple[str | None, str | None, str | None]:
    for part in relative_path.split("/")[:-1]:
        key = part.lower()
        if key in RECORD_FAMILY_DIRS:
            classification, capability = RECORD_FAMILY_DIRS[key]
            return classification, capability, part
    return None, None, None



def _analyze_parsed_json(
    parsed: Any,
    *,
    collector: ShapeCollector,
    relative_path: str,
) -> tuple[set[str], bool]:
    """Analyze one parsed JSON payload.

    Returns (classifications_seen, matched_any_known_surface).
    """

    classifications: set[str] = set()
    matched = False

    if isinstance(parsed, list):
        dicts = [item for item in parsed if isinstance(item, dict)]
        if dicts and any(_find_message_container(d)[0] for d in dicts[:5]):
            matched = True
            collector.note_capability(
                "nested_conversation_container",
                relative_path=relative_path,
                structural_keys=["<array_of_conversation_objects>"],
            )
            for conversation in dicts:
                _analyze_conversation(
                    conversation,
                    collector=collector,
                    relative_path=relative_path,
                    root_container=None,
                )
            classifications.add("conversations")
        elif dicts and any(_is_message_like(d) for d in dicts[:5]):
            matched = True
            collector.note_capability(
                "flat_conversation_array",
                relative_path=relative_path,
                structural_keys=["<flat_message_array>"],
            )
            collector.mark_conversation()
            collector.add_message_container_key("<top_level_array>")
            for message in dicts:
                depth_budget = [MAX_JSON_DEPTH]
                _analyze_message(
                    message,
                    collector=collector,
                    relative_path=relative_path,
                    depth_budget=depth_budget,
                )
            classifications.add("conversations")
        elif dicts:
            for record in dicts[:100]:
                classifications |= _classify_record_dict(record)
            if classifications:
                matched = True
                if "projects" in classifications:
                    collector.note_capability(
                        "project_records",
                        relative_path=relative_path,
                        structural_keys=["<array_of_project_records>"],
                    )
                if "memories" in classifications:
                    collector.note_capability(
                        "memory_records",
                        relative_path=relative_path,
                        structural_keys=["<array_of_memory_records>"],
                    )
                if "users_or_account" in classifications:
                    collector.note_capability(
                        "account_metadata",
                        relative_path=relative_path,
                        structural_keys=["<array_of_account_records>"],
                    )
        return classifications, matched

    if isinstance(parsed, dict):
        container_key, messages = _find_message_container(parsed)
        if container_key is not None:
            matched = True
            classifications.add("conversations")
            collector.note_capability(
                "flat_conversation_array",
                relative_path=relative_path,
                structural_keys=[container_key],
            )
            _analyze_conversation(
                parsed,
                collector=collector,
                relative_path=relative_path,
                root_container=container_key,
            )
            return classifications, matched

        # Wrapper objects: { "conversations": [...], "projects": [...] }
        saw_wrapper = False
        for wrapper in COLLECTION_WRAPPER_KEYS:
            value = parsed.get(wrapper)
            if not isinstance(value, list) or not value:
                continue
            saw_wrapper = True
            sub_classes: set[str] = set()
            for record in [v for v in value if isinstance(v, dict)][:100]:
                sub_classes |= _classify_record_dict(record)
            if wrapper in {"conversations", "threads", "chats", "items", "data"} and (
                (sub_classes & {"conversations"})
                or any(
                    _find_message_container(v)[0] is not None
                    for v in value
                    if isinstance(v, dict)
                )
            ):
                matched = True
                classifications.add("conversations")
                collector.note_capability(
                    "nested_conversation_container",
                    relative_path=relative_path,
                    structural_keys=[wrapper],
                )
                for record in [v for v in value if isinstance(v, dict)]:
                    _analyze_conversation(
                        record,
                        collector=collector,
                        relative_path=relative_path,
                        root_container=None,
                    )
            elif wrapper == "projects":
                matched = True
                classifications.add("projects")
                collector.note_capability(
                    "project_records",
                    relative_path=relative_path,
                    structural_keys=[wrapper],
                )
            elif wrapper == "memories":
                matched = True
                classifications.add("memories")
                collector.note_capability(
                    "memory_records",
                    relative_path=relative_path,
                    structural_keys=[wrapper],
                )
            elif wrapper in {"users", "user", "account"}:
                matched = True
                classifications.add("users_or_account")
                collector.note_capability(
                    "account_metadata",
                    relative_path=relative_path,
                    structural_keys=[wrapper],
                )
            elif wrapper == "artifacts":
                matched = True
                classifications.add("artifacts")
                collector.note_capability(
                    "artifact_evidence",
                    relative_path=relative_path,
                    structural_keys=[wrapper],
                )
        if saw_wrapper:
            return classifications, matched

        # Single record dict.
        record_classes = _classify_record_dict(parsed)
        dir_class, dir_capability, dir_name = _directory_family(relative_path)
        if dir_class is not None:
            record_classes.add(dir_class)
            collector.note_capability(
                dir_capability,
                relative_path=relative_path,
                structural_keys=[f"directory:{dir_name}"],
            )
        if record_classes:
            matched = True
            classifications |= record_classes
            if "projects" in record_classes:
                collector.note_capability(
                    "project_records",
                    relative_path=relative_path,
                    structural_keys=sorted(record_classes),
                )
            if "memories" in record_classes:
                collector.note_capability(
                    "memory_records",
                    relative_path=relative_path,
                    structural_keys=sorted(record_classes),
                )
            if "users_or_account" in record_classes:
                collector.note_capability(
                    "account_metadata",
                    relative_path=relative_path,
                    structural_keys=sorted(record_classes),
                )
            if "artifacts" in record_classes:
                collector.note_capability(
                    "artifact_evidence",
                    relative_path=relative_path,
                    structural_keys=sorted(record_classes),
                )
        return classifications, matched

    return classifications, matched


# --------------------------------------------------------------------------
# Input sources
# --------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _package_fingerprint(entries: list[tuple[str, int, str]]) -> str:
    """Deterministic fingerprint from ordered (relpath, size, sha256)."""

    payload = json.dumps(
        [[path, size, sha] for path, size, sha in entries],
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _looks_json_file(path: Path) -> bool:
    if path.suffix.lower() == ".json":
        return True
    try:
        with path.open("rb") as handle:
            head = handle.read(8).lstrip()
    except OSError:
        return False
    return head[:1] in (b"{", b"[")


def _build_scanned_file(
    *,
    relative_path: str,
    member: MemberBytes,
    compressed_size_bytes: int | None,
    warnings: list[dict[str, Any]],
) -> ScannedFile:
    extension = _extension_of(relative_path)
    broad_type = _broad_type(member.sample)
    json_parse_status = "not_json"
    json_top_level_type = "none"
    json_top_level_keys: list[str] = []
    parsed: Any = None

    looks_json = broad_type == "json" or extension == ".json"
    if looks_json:
        if not member.full_buffer_available:
            json_parse_status = "skipped"
            warnings.append(
                {
                    "code": "analysis_limit_reached",
                    "relative_path": relative_path,
                    "message": (
                        "JSON member exceeded the per-member analysis cap and "
                        "was not parsed."
                    ),
                }
            )
        else:
            try:
                parsed = json.loads(member.buffered.decode("utf-8-sig"))
                json_parse_status = "ok"
            except (ValueError, UnicodeDecodeError) as exc:
                json_parse_status = "failed"
                warnings.append(
                    {
                        "code": "json_parse_failed",
                        "relative_path": relative_path,
                        "message": (
                            f"JSON parse failed: {exc.__class__.__name__}"
                        ),
                    }
                )
            if json_parse_status == "ok":
                if isinstance(parsed, dict):
                    json_top_level_type = "object"
                    json_top_level_keys = sorted(str(k) for k in parsed.keys())[
                        :MAX_TOP_LEVEL_KEYS_DISPLAY
                    ]
                elif isinstance(parsed, list):
                    json_top_level_type = "array"
                    first_dict = next(
                        (item for item in parsed if isinstance(item, dict)), None
                    )
                    if first_dict is not None:
                        json_top_level_keys = sorted(
                            str(k) for k in first_dict.keys()
                        )[:MAX_TOP_LEVEL_KEYS_DISPLAY]
                else:
                    json_top_level_type = "scalar"

    return ScannedFile(
        relative_path=relative_path,
        size_bytes=member.size,
        sha256=member.sha256,
        extension=extension,
        broad_type=broad_type,
        json_parse_status=json_parse_status,
        json_top_level_type=json_top_level_type,
        json_top_level_keys=json_top_level_keys,
        compressed_size_bytes=compressed_size_bytes,
        parsed=parsed,
    )


def _profile_zip(path: Path) -> tuple[str, list[ScannedFile], bool, list[dict[str, Any]]]:
    package_sha = _sha256_file(path)
    warnings: list[dict[str, Any]] = []
    scanned: list[ScannedFile] = []
    truncated = False
    total_bytes = 0
    seen_paths: set[str] = set()

    try:
        zip_handle = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise UnsafePackageError(
            f"ZIP container is corrupt: {exc}",
            code="corrupt_zip",
        ) from exc

    with zip_handle as bundle:
        infos = list(bundle.infolist())
        # Deterministic normalized-path order; reject unsafe members first.
        normalized: list[tuple[str, zipfile.ZipInfo]] = []
        for info in infos:
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise UnsafePackageError(
                    "ZIP member is a symbolic link.",
                    code="symlink_rejected",
                )
            rel = normalize_member_path(info.filename)
            if rel in seen_paths:
                raise UnsafePackageError(
                    f"ZIP contains a duplicate normalized path: {rel}",
                    code="duplicate_path_rejected",
                )
            seen_paths.add(rel)
            normalized.append((rel, info))
        normalized.sort(key=lambda item: item[0])

        for rel, info in normalized:
            if len(scanned) >= MAX_PACKAGE_FILE_COUNT:
                truncated = True
                warnings.append(
                    {
                        "code": "analysis_limit_reached",
                        "relative_path": rel,
                        "message": "Package file count limit reached; remaining members skipped.",
                    }
                )
                break
            declared = int(info.file_size)
            if total_bytes + declared > MAX_TOTAL_BYTES:
                truncated = True
                warnings.append(
                    {
                        "code": "analysis_limit_reached",
                        "relative_path": rel,
                        "message": "Total byte inspection limit reached; remaining members skipped.",
                    }
                )
                break
            total_bytes += declared

            member = _stream_member(lambda i=info: bundle.open(i, "r"))
            scanned.append(
                _build_scanned_file(
                    relative_path=rel,
                    member=member,
                    compressed_size_bytes=int(info.compress_size),
                    warnings=warnings,
                )
            )

    return package_sha, scanned, truncated, warnings


def _iter_directory_files(root: Path) -> Iterator[Path]:
    """Yield regular files beneath root, rejecting symlinks and escape."""

    resolved_root = root.resolve()
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in sorted(entries, key=lambda p: p.name):
            if entry.is_symlink():
                raise UnsafePackageError(
                    f"Directory contains a symbolic link: {entry.name}",
                    code="symlink_rejected",
                )
            resolved = entry.resolve()
            try:
                resolved.relative_to(resolved_root)
            except ValueError as exc:
                raise UnsafePackageError(
                    "Directory entry escaped the inspection root.",
                    code="path_traversal_rejected",
                ) from exc
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                yield entry


def _profile_directory(
    path: Path,
) -> tuple[str, list[ScannedFile], bool, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    scanned: list[ScannedFile] = []
    truncated = False
    total_bytes = 0
    resolved_root = path.resolve()

    collected: list[tuple[str, Path]] = []
    for absolute in _iter_directory_files(path):
        rel = absolute.resolve().relative_to(resolved_root).as_posix()
        collected.append((rel, absolute))
    collected.sort(key=lambda item: item[0])

    for rel, absolute in collected:
        if len(scanned) >= MAX_PACKAGE_FILE_COUNT:
            truncated = True
            warnings.append(
                {
                    "code": "analysis_limit_reached",
                    "relative_path": rel,
                    "message": "Package file count limit reached; remaining files skipped.",
                }
            )
            break
        size = absolute.stat().st_size
        if total_bytes + size > MAX_TOTAL_BYTES:
            truncated = True
            warnings.append(
                {
                    "code": "analysis_limit_reached",
                    "relative_path": rel,
                    "message": "Total byte inspection limit reached; remaining files skipped.",
                }
            )
            break
        total_bytes += size
        member = _stream_member(lambda p=absolute: p.open("rb"))
        scanned.append(
            _build_scanned_file(
                relative_path=rel,
                member=member,
                compressed_size_bytes=None,
                warnings=warnings,
            )
        )

    fingerprint_entries = [
        (f.relative_path, f.size_bytes, f.sha256) for f in scanned
    ]
    package_sha = _package_fingerprint(fingerprint_entries)
    return package_sha, scanned, truncated, warnings


def _profile_json_file(
    path: Path,
) -> tuple[str, list[ScannedFile], bool, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    member = _stream_member(lambda p=path: p.open("rb"))
    rel = path.name
    scanned = _build_scanned_file(
        relative_path=rel,
        member=member,
        compressed_size_bytes=None,
        warnings=warnings,
    )
    return scanned.sha256, [scanned], False, warnings


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------


def _build_report(
    *,
    kind: str,
    display_name: str,
    package_sha: str,
    files: list[ScannedFile],
    truncated: bool,
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    collector = ShapeCollector()

    # Scrub identity values (UUID-shaped stems) from every relative path before
    # any analysis emits a path. All downstream path fields derive from this.
    redaction = build_path_redaction([f.relative_path for f in files])
    for scanned_file in files:
        scanned_file.relative_path = redaction.get(
            scanned_file.relative_path, scanned_file.relative_path
        )
    for warning in warnings:
        rel = warning.get("relative_path")
        if rel:
            warning["relative_path"] = redaction.get(rel, rel)

    binary_count = 0
    json_count = 0
    for scanned_file in files:
        if scanned_file.broad_type in {
            "image",
            "pdf",
            "audio",
            "video",
            "archive",
            "unknown_binary",
        }:
            binary_count += 1
        if scanned_file.json_parse_status == "ok":
            json_count += 1

        # Structural analysis of parsed JSON.
        if scanned_file.parsed is not None:
            classifications, matched = _analyze_parsed_json(
                scanned_file.parsed,
                collector=collector,
                relative_path=scanned_file.relative_path,
            )
            if classifications:
                for classification in sorted(classifications):
                    collector.add_candidate_surface(
                        relative_path=scanned_file.relative_path,
                        classification=classification,
                        evidence_keys=[
                            k for k in scanned_file.json_top_level_keys
                        ][:MAX_CANDIDATE_EVIDENCE_KEYS],
                    )
            elif scanned_file.json_top_level_type in {"object", "array"}:
                if not matched:
                    collector.add_unknown_json_shape(scanned_file.relative_path)
                    if len(warnings) < MAX_WARNINGS:
                        warnings.append(
                            {
                                "code": "unknown_json_shape",
                                "relative_path": scanned_file.relative_path,
                                "message": "Parsed JSON matched no known structural surface.",
                            }
                        )

        # Binary / attachment evidence.
        if scanned_file.broad_type in {
            "image",
            "pdf",
            "audio",
            "video",
            "unknown_binary",
        }:
            collector.note_capability(
                "binary_payloads",
                relative_path=scanned_file.relative_path,
                structural_keys=[f"broad_type:{scanned_file.broad_type}"],
            )
            collector.add_candidate_surface(
                relative_path=scanned_file.relative_path,
                classification="attachments_or_files",
                evidence_keys=[f"broad_type:{scanned_file.broad_type}"],
            )

    # Branch-structure warning when parent links were observed.
    if collector._parent_fields and len(warnings) < MAX_WARNINGS:
        warnings.append(
            {
                "code": "possible_branch_structure",
                "relative_path": None,
                "message": "Parent/branch relationship field names were observed on messages.",
            }
        )

    # Cross-file binary/reference reconciliation warnings (bounded, heuristic).
    has_binary = any(
        f.broad_type in {"image", "pdf", "audio", "video", "unknown_binary"}
        for f in files
    )
    has_attachment_refs = bool(collector._attachment_fields)
    if has_binary and not has_attachment_refs and len(warnings) < MAX_WARNINGS:
        warnings.append(
            {
                "code": "binary_without_reference",
                "relative_path": None,
                "message": "Binary payloads present but no attachment-reference field names observed.",
            }
        )
    if has_attachment_refs and not has_binary and len(warnings) < MAX_WARNINGS:
        warnings.append(
            {
                "code": "reference_without_binary",
                "relative_path": None,
                "message": "Attachment-reference field names observed but no binary payloads present.",
            }
        )

    bounded_warnings = warnings[:MAX_WARNINGS]
    if len(warnings) > MAX_WARNINGS:
        bounded_warnings.append(
            {
                "code": "analysis_limit_reached",
                "relative_path": None,
                "message": "Warning count limit reached; additional warnings dropped.",
            }
        )

    file_inventory: list[dict[str, Any]] = []
    for scanned_file in sorted(files, key=lambda f: f.relative_path):
        record: dict[str, Any] = {
            "relative_path": scanned_file.relative_path,
            "size_bytes": scanned_file.size_bytes,
            "sha256": scanned_file.sha256,
            "extension": scanned_file.extension,
            "broad_type": scanned_file.broad_type,
            "json_parse_status": scanned_file.json_parse_status,
            "json_top_level_type": scanned_file.json_top_level_type,
            "json_top_level_keys": scanned_file.json_top_level_keys,
        }
        if scanned_file.compressed_size_bytes is not None:
            record["compressed_size_bytes"] = scanned_file.compressed_size_bytes
        file_inventory.append(record)

    total_bytes = sum(f.size_bytes for f in files)

    candidate_surfaces = sorted(
        collector.candidate_surfaces,
        key=lambda c: (c["relative_path"], c["classification"]),
    )

    report = {
        "report_schema": REPORT_SCHEMA,
        "profiler_version": PROFILER_VERSION,
        "package": {
            "kind": kind,
            "display_name": display_name,
            "sha256": package_sha,
            "file_count": len(files),
            "json_file_count": json_count,
            "binary_file_count": binary_count,
            "total_bytes": total_bytes,
            "analysis_truncated": bool(truncated),
        },
        "files": file_inventory,
        "candidate_surfaces": candidate_surfaces,
        "conversation_shape": collector.conversation_shape_payload(),
        "capabilities_observed": collector.capability_payload(),
        "unknown_structures": collector.unknown_structures_payload(),
        "warnings": bounded_warnings,
        "errors": [],
    }
    return report


# --------------------------------------------------------------------------
# Public profiling entrypoint
# --------------------------------------------------------------------------


def profile_export(input_path: str) -> dict[str, Any]:
    """Profile an Anthropic export and return the deterministic report dict."""

    source = Path(input_path)
    if not source.exists() and not source.is_symlink():
        raise UsageError(
            f"Input path does not exist: {input_path}",
            code="input_not_found",
        )
    if source.is_symlink():
        raise UnsafePackageError(
            "Input path is a symbolic link.",
            code="symlink_rejected",
        )
    display_name = source.name or input_path

    if source.is_dir():
        kind = "directory"
        package_sha, files, truncated, warnings = _profile_directory(source)
    elif zipfile.is_zipfile(source):
        kind = "zip"
        package_sha, files, truncated, warnings = _profile_zip(source)
    elif source.is_file():
        if _looks_json_file(source):
            kind = "json"
            package_sha, files, truncated, warnings = _profile_json_file(source)
        else:
            raise UsageError(
                "Unsupported input type: expected a ZIP archive, extracted "
                "directory, or JSON file.",
                code="unsupported_input_type",
            )
    else:
        raise UsageError(
            "Unsupported input type: expected a ZIP archive, extracted "
            "directory, or JSON file.",
            code="unsupported_input_type",
        )

    return _build_report(
        kind=kind,
        display_name=display_name,
        package_sha=package_sha,
        files=files,
        truncated=truncated,
        warnings=warnings,
    )


# --------------------------------------------------------------------------
# Output / CLI
# --------------------------------------------------------------------------


def serialize_report(report: dict[str, Any]) -> str:
    return (
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n"
    )


def write_report(report: dict[str, Any], output_path: str) -> None:
    target = Path(output_path)
    if target.is_dir():
        raise UsageError(
            f"Output path is a directory: {output_path}",
            code="output_not_writable",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_report(report), encoding="utf-8")


def _short(text: str, limit: int = 16) -> str:
    return text[:limit] if len(text) > limit else text


def print_summary(report: dict[str, Any], output_path: str) -> None:
    package = report["package"]
    print("Anthropic export profile complete")
    print(f"package_kind: {package['kind']}")
    print(f"package_fingerprint: sha256:{_short(package['sha256'])}...")
    print(f"file_count: {package['file_count']}")
    print(f"json_file_count: {package['json_file_count']}")
    print(f"warning_count: {len(report['warnings'])}")
    print(f"report_path: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="profile_anthropic_export.py",
        description=(
            "Read-only Anthropic account-export profiler. Inspects a ZIP "
            "archive, extracted directory, or JSON file and emits a "
            "deterministic structural evidence report. Does not import data."
        ),
    )
    parser.add_argument(
        "input",
        help="Path to a ZIP archive, extracted directory, or JSON file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the JSON report to write.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = profile_export(args.input)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except UnsafePackageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNSAFE

    try:
        write_report(report, args.output)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print_summary(report, args.output)
    return EXIT_OK


# ``Sequence`` is imported with the other typing names above.


if __name__ == "__main__":
    sys.exit(main())
