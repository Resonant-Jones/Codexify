"""Forensic corpus reconnaissance for OpenAI exports.

Read-only, deterministic statistical analysis. No database writes,
no embeddings, no model calls, no mutations.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    OpenAIExportFileRecord,
    OpenAIExportInventory,
)

TRUNCATION_LIMIT = 200

# --- Heading patterns (deterministic string/pattern matching) ---

_MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

_CANONICAL_HEADINGS = {
    "Codexify Task Prompt",
    "Task Summary",
    "Execution Contract",
    "Definition of Done",
    "Files Changed",
    "Test Results",
    "Commit",
    "Objective",
    "Requirements",
    "Implementation Notes",
}

_PLAINTEXT_HEADING = re.compile(
    r"^(?:(?:Codexify\s+)?Task\s+Summary|Codexify\s+Task\s+Prompt|"
    r"Definition\s+of\s+Done|Files\s+Changed|Test\s+Results|"
    r"Execution\s+Contract|Implementation\s+Notes|"
    r"Acceptance\s+Criteria|"
    r"Task|Objective|Requirements|Summary|Implementation|"
    r"Commit|Notes|Architecture|Design|Specification|"
    r"Overview|Background|Purpose|Scope)"
    r"\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_KEYWORDS = [
    "Codexify",
    "PulseOS",
    "ThreadSpace",
    "WhisperMesh",
    "Guardian",
    "Scout",
    "GraphWrag",
    "IDDB",
    "Persona",
    "ThreadPrint",
    "OpenAI Export",
    "Task Prompt",
    "Task Summary",
    "Execution Contract",
]

_KEYWORD_PATTERNS = {
    kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    for kw in _KEYWORDS
}

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```|`[^`]+`")
_IMAGE_PATTERN = re.compile(r"!\[.*?\]\(.*?\)|<img\s|<svg\s")
_ATTACHMENT_PATTERN = re.compile(r"\[.*?\]\(\./.*?\)|attachment", re.IGNORECASE)
_SUMMARY_PATTERN = re.compile(
    r"(?im)^(?:#{1,6}\s*)?(?:Task\s+)?Summary", re.IGNORECASE
)
_TASK_PROMPT_PATTERN = re.compile(
    r"(?im)^(?:#{1,6}\s*)?Codexify\s+Task\s+Prompt", re.IGNORECASE
)

_PATH_FAMILIES = {
    "conversations",
    "workspace",
    "files",
    "Unassigned",
    "__export_file_manifests__",
    "unknown",
}

_SIZE_BUCKETS = [
    (0, "empty"),
    (1, 1023, "0-1KB"),
    (1024, 1024 * 1024 - 1, "1KB-1MB"),
    (1024 * 1024, 10 * 1024 * 1024 - 1, "1-10MB"),
    (10 * 1024 * 1024, 100 * 1024 * 1024 - 1, "10-100MB"),
    (100 * 1024 * 1024, None, "100MB+"),
]


# --- Data classes ---


@dataclass
class ReconMessage:
    text: str
    timestamp: float | None
    message_id: str | None = None
    role: str | None = None


@dataclass
class ReconConversation:
    conversation_id: str
    title: str
    messages: list[ReconMessage] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def first_message(self) -> str:
        if not self.messages:
            return ""
        text = self.messages[0].text
        return _safe_truncate(text)

    @property
    def last_message(self) -> str:
        if not self.messages:
            return ""
        text = self.messages[-1].text
        return _safe_truncate(text)

    @property
    def contains_task_prompt(self) -> bool:
        return any(
            _TASK_PROMPT_PATTERN.search(msg.text) for msg in self.messages
        )

    @property
    def contains_summary(self) -> bool:
        return any(
            _SUMMARY_PATTERN.search(msg.text) for msg in self.messages
        )

    @property
    def contains_code(self) -> bool:
        return any(
            _CODE_BLOCK_PATTERN.search(msg.text) for msg in self.messages
        )

    @property
    def contains_attachments(self) -> bool:
        return any(
            _ATTACHMENT_PATTERN.search(msg.text) for msg in self.messages
        )

    @property
    def contains_images(self) -> bool:
        return any(
            _IMAGE_PATTERN.search(msg.text) for msg in self.messages
        )

    def all_text(self) -> str:
        return "\n".join(msg.text for msg in self.messages)

    @property
    def first_timestamp(self) -> float | None:
        for msg in self.messages:
            if msg.timestamp is not None:
                return msg.timestamp
        return None

    @property
    def last_timestamp(self) -> float | None:
        for msg in reversed(self.messages):
            if msg.timestamp is not None:
                return msg.timestamp
        return None

    def to_index_row(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "message_count": self.message_count,
            "first_message": self.first_message,
            "last_message": self.last_message,
            "contains_task_prompt": str(self.contains_task_prompt).lower(),
            "contains_summary": str(self.contains_summary).lower(),
            "contains_attachments": str(self.contains_attachments).lower(),
            "contains_code": str(self.contains_code).lower(),
            "contains_images": str(self.contains_images).lower(),
        }


@dataclass
class CorpusReconStats:
    files_scanned: int = 0
    json_like_files: int = 0
    conversations_found: int = 0
    messages_scanned: int = 0
    assets_found: int = 0
    orphan_assets_found: int = 0
    parse_failures: int = 0
    skipped_files: int = 0

    messages_by_year: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    messages_by_year_month: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )

    conversations: list[ReconConversation] = field(default_factory=list)

    heading_counts: Counter[str] = field(default_factory=Counter)
    heading_excerpts: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    content_kind_counts: Counter[str] = field(default_factory=Counter)
    keyword_counts: Counter[str] = field(default_factory=Counter)

    asset_kind_counts: Counter[str] = field(default_factory=Counter)
    asset_path_family_counts: Counter[str] = field(default_factory=Counter)
    asset_size_bucket_counts: Counter[str] = field(default_factory=Counter)
    sharded_count: int = 0
    non_sharded_count: int = 0

    failed_paths: list[dict[str, str]] = field(default_factory=list)

    @property
    def largest_conversations(self) -> list[dict[str, Any]]:
        sorted_convs = sorted(
            self.conversations, key=lambda c: c.message_count, reverse=True
        )
        return [
            {
                "conversation_id": c.conversation_id,
                "title": c.title,
                "message_count": c.message_count,
            }
            for c in sorted_convs[:20]
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_totals": {
                "files_scanned": self.files_scanned,
                "json_like_files": self.json_like_files,
                "conversations_found": self.conversations_found,
                "messages_scanned": self.messages_scanned,
                "assets_found": self.assets_found,
                "orphan_assets_found": self.orphan_assets_found,
                "parse_failures": self.parse_failures,
                "skipped_files": self.skipped_files,
            },
            "messages_by_year": dict(
                sorted(self.messages_by_year.items())
            ),
            "messages_by_year_month": dict(
                sorted(self.messages_by_year_month.items())
            ),
            "largest_conversations": self.largest_conversations,
            "top_recurring_headings": {
                heading: {
                    "count": count,
                    "excerpts": self.heading_excerpts[heading][:3],
                }
                for heading, count in self.heading_counts.most_common(50)
            },
            "content_file_kinds": dict(
                self.content_kind_counts.most_common()
            ),
            "task_prompt_summary_variants": {
                heading: self.heading_counts.get(heading, 0)
                for heading in _CANONICAL_HEADINGS
            },
            "keyword_counts": dict(self.keyword_counts),
            "asset_orphan_breakdown": {
                "by_detected_kind": dict(self.asset_kind_counts.most_common()),
                "by_path_family": dict(
                    self.asset_path_family_counts.most_common()
                ),
                "by_size_bucket": dict(
                    self.asset_size_bucket_counts.most_common()
                ),
                "sharded": self.sharded_count,
                "non_sharded": self.non_sharded_count,
            },
            "failed_paths": self.failed_paths,
        }


# --- Recon engine ---


class OpenAIExportCorpusRecon:
    """Read-only forensic recon for an OpenAI export corpus."""

    def __init__(self) -> None:
        self.detector = OpenAIExportDetector()

    def scan(self, root_path: str | Path) -> CorpusReconStats:
        root = Path(root_path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Export path does not exist: {root}")

        inventory = self.detector.scan(root)
        stats = CorpusReconStats()
        stats.files_scanned = len(inventory.files)

        # Classify all files
        json_files: list[OpenAIExportFileRecord] = []
        asset_files: list[OpenAIExportFileRecord] = []

        for record in inventory.files:
            kind = record.detected_kind
            stats.content_kind_counts[kind] += 1

            if kind in {"json_object", "json_array", "jsonl"}:
                json_files.append(record)
            elif kind == "invalid_json":
                stats.parse_failures += 1
                stats.failed_paths.append(
                    {
                        "path": record.path,
                        "error": record.parse_error or "invalid_json",
                    }
                )
            elif kind in {
                "image_png",
                "image_jpeg",
                "image_gif",
                "image_webp",
                "pdf",
                "zip",
                "video_mp4",
                "video_webm",
                "audio_wav",
                "audio_ogg",
                "audio_flac",
                "audio_mpeg",
                "html",
                "text",
                "unknown_binary",
            }:
                asset_files.append(record)
            elif record.path.endswith(".DS_Store"):
                stats.skipped_files += 1
            else:
                stats.skipped_files += 1

        stats.json_like_files = len(json_files)

        # Extract conversations from sniffed JSON/JSONL files. Do not assume
        # legacy conversations.json or modern conversations-*.json names.
        all_conversations: list[ReconConversation] = []

        for record in json_files:
            try:
                payloads = list(_iter_json_payloads(record))
            except Exception as exc:
                stats.parse_failures += 1
                stats.failed_paths.append(
                    {"path": record.path, "error": str(exc) or "json_parse_failed"}
                )
                continue

            before = len(all_conversations)
            for payload in payloads:
                for conv in self._iter_conversations_from_payload(payload):
                    recon_conv = self._build_recon_conversation(conv)
                    if recon_conv:
                        all_conversations.append(recon_conv)
            if len(all_conversations) == before:
                stats.skipped_files += 1

        stats.conversations = all_conversations
        stats.conversations_found = len(all_conversations)

        # Count messages and build time series
        for conv in all_conversations:
            stats.messages_scanned += conv.message_count
            for msg in conv.messages:
                if msg.timestamp is not None:
                    dt = datetime.fromtimestamp(msg.timestamp, timezone.utc)
                    stats.messages_by_year[dt.year] += 1
                    stats.messages_by_year_month[f"{dt.year}-{dt.month:02d}"] += 1

            # Count keywords across all text (per-occurrence)
            all_text = conv.all_text()
            for kw, pattern in _KEYWORD_PATTERNS.items():
                count = len(pattern.findall(all_text))
                if count:
                    stats.keyword_counts[kw] += count

            # Count headings
            for line in all_text.splitlines():
                line_stripped = line.strip()
                # Markdown headings
                md_match = _MARKDOWN_HEADING.match(line_stripped)
                if md_match:
                    heading_text = md_match.group(2).strip()
                    stats.heading_counts[heading_text] += 1
                    if (
                        len(stats.heading_excerpts[heading_text]) < 3
                        and len(heading_text) < 200
                    ):
                        stats.heading_excerpts[heading_text].append(
                            heading_text[:200]
                        )
                    continue
                # Plaintext canonical headings
                text_match = _PLAINTEXT_HEADING.match(line_stripped)
                if text_match:
                    heading_text = text_match.group(0).strip()
                    stats.heading_counts[heading_text] += 1
                    if len(stats.heading_excerpts[heading_text]) < 3:
                        stats.heading_excerpts[heading_text].append(
                            heading_text[:200]
                        )

        # Asset breakdown
        stats.assets_found = len(asset_files)
        for record in asset_files:
            stats.asset_kind_counts[record.detected_kind] += 1

            # Path family
            family = _classify_path_family(record.path)
            stats.asset_path_family_counts[family] += 1

            # Size bucket
            bucket = _classify_size_bucket(record.size)
            stats.asset_size_bucket_counts[bucket] += 1

            # Sharded vs non-sharded
            if _is_sharded_path(record.path):
                stats.sharded_count += 1
            else:
                stats.non_sharded_count += 1

            # V1 recon does not perform manifest correlation, so assets are
            # inventory-preserved as orphaned until a later pass links them.
            stats.orphan_assets_found += 1

        return stats

    def _iter_conversations_from_payload(
        self, payload: Any
    ) -> Iterator[dict[str, Any]]:
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and (
                    "mapping" in item or "messages" in item
                ):
                    yield item
        elif isinstance(payload, dict):
            if "mapping" in payload or "messages" in payload:
                yield payload
            for key in ("conversations", "threads", "chats", "items", "data"):
                nested = payload.get(key)
                if isinstance(nested, list):
                    yield from self._iter_conversations_from_payload(nested)

    def _build_recon_conversation(
        self, conv: dict[str, Any]
    ) -> ReconConversation | None:
        conv_id = _coerce_str(
            conv.get("conversation_id") or conv.get("id") or ""
        )
        title = _coerce_str(conv.get("title") or "Untitled")
        mapping = conv.get("mapping")

        if isinstance(mapping, dict) and mapping:
            messages = self._extract_messages_from_mapping(mapping, conv)
            if messages:
                return ReconConversation(
                    conversation_id=conv_id,
                    title=title,
                    messages=messages,
                )

        raw_messages = conv.get("messages")
        if isinstance(raw_messages, list):
            messages = self._extract_messages_from_list(raw_messages)
            if messages:
                return ReconConversation(
                    conversation_id=conv_id,
                    title=title,
                    messages=messages,
                )

        return None

    def _extract_messages_from_mapping(
        self, mapping: dict[str, Any], conv: dict[str, Any]
    ) -> list[ReconMessage]:
        current_node = conv.get("current_node")
        mainline = _linearize_mainline(mapping, current_node)

        if not mainline:
            mainline = sorted(mapping.items())

        messages: list[ReconMessage] = []
        for node_id, node in mainline:
            if not isinstance(node, dict):
                continue
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue
            text = _message_text(msg)
            if not text:
                continue
            timestamp = _coerce_epoch_seconds(msg.get("create_time"))
            role = _extract_role(msg)
            messages.append(
                ReconMessage(
                    text=text,
                    timestamp=timestamp,
                    message_id=msg.get("id") or node_id,
                    role=role,
                )
            )
        return messages

    def _extract_messages_from_list(
        self, raw_messages: list[Any]
    ) -> list[ReconMessage]:
        messages: list[ReconMessage] = []
        for raw in raw_messages:
            if not isinstance(raw, dict):
                continue
            msg = raw.get("message") if isinstance(raw.get("message"), dict) else raw
            text = _message_text(msg)
            if not text:
                continue
            timestamp = _coerce_epoch_seconds(
                msg.get("create_time")
                or msg.get("created_at")
                or raw.get("create_time")
                or raw.get("created_at")
            )
            role = _extract_role(msg)
            messages.append(
                ReconMessage(
                    text=text,
                    timestamp=timestamp,
                    message_id=msg.get("id") or msg.get("message_id"),
                    role=role,
                )
            )
        return messages


# --- Output writers ---


def write_conversation_index(
    conversations: list[ReconConversation], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "conversation_id",
        "title",
        "message_count",
        "first_message",
        "last_message",
        "contains_task_prompt",
        "contains_summary",
        "contains_attachments",
        "contains_code",
        "contains_images",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for conv in sorted(
            conversations, key=lambda c: c.message_count, reverse=True
        ):
            writer.writerow(conv.to_index_row())


def write_corpus_stats(stats: CorpusReconStats, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_corpus_summary_markdown(
    stats: CorpusReconStats, output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    d = stats.to_dict()
    totals = d["corpus_totals"]

    lines = [
        "# OpenAI Export Corpus Reconnaissance Report",
        "",
        "## Corpus Totals",
        "",
        f"- Files scanned: {totals['files_scanned']}",
        f"- JSON-like files: {totals['json_like_files']}",
        f"- Conversations found: {totals['conversations_found']}",
        f"- Messages scanned: {totals['messages_scanned']}",
        f"- Assets found: {totals['assets_found']}",
        f"- Orphan assets found: {totals['orphan_assets_found']}",
        f"- Parse failures: {totals['parse_failures']}",
        f"- Skipped files: {totals['skipped_files']}",
        "",
        "## Largest Conversations",
        "",
    ]

    if d["largest_conversations"]:
        lines.append(
            "| conversation_id | title | message_count |"
        )
        lines.append(
            "| --- | --- | --- |"
        )
        for conv in d["largest_conversations"][:20]:
            lines.append(
                f"| {conv['conversation_id']} "
                f"| {_safe_truncate(conv['title'], limit=60)} "
                f"| {conv['message_count']} |"
            )
    else:
        lines.append("No conversations found.")
    lines.append("")

    lines.append("## Messages by Year")
    lines.append("")
    if d["messages_by_year"]:
        for year, count in sorted(d["messages_by_year"].items()):
            lines.append(f"- {year}: {count}")
    else:
        lines.append("No timestamped messages.")
    lines.append("")

    lines.append("## Messages by Year/Month")
    lines.append("")
    if d["messages_by_year_month"]:
        lines.append("| Year-Month | Count |")
        lines.append("| --- | --- |")
        for ym, count in sorted(d["messages_by_year_month"].items()):
            lines.append(f"| {ym} | {count} |")
    else:
        lines.append("No timestamped messages.")
    lines.append("")

    lines.append("## Top Recurring Headings (top 30)")
    lines.append("")
    top_headings = list(d["top_recurring_headings"].items())[:30]
    if top_headings:
        lines.append("| Heading | Count |")
        lines.append("| --- | --- |")
        for heading, info in top_headings:
            lines.append(f"| {_safe_truncate(heading, limit=80)} | {info['count']} |")
    else:
        lines.append("No headings detected.")
    lines.append("")

    lines.append("## Task Prompt / Summary Heading Variants")
    lines.append("")
    variants = d["task_prompt_summary_variants"]
    if any(variants.values()):
        for heading, count in sorted(variants.items()):
            if count > 0:
                lines.append(f"- `{heading}`: {count}")
    else:
        lines.append("No matching task prompt/summary headings found.")
    lines.append("")

    lines.append("## Keyword Counts")
    lines.append("")
    kc = d["keyword_counts"]
    if kc:
        lines.append("| Keyword | Conversation Count |")
        lines.append("| --- | --- |")
        for kw, count in sorted(kc.items(), key=lambda x: -x[1]):
            lines.append(f"| {kw} | {count} |")
    else:
        lines.append("No keywords matched.")
    lines.append("")

    lines.append("## Content / File Kinds")
    lines.append("")
    ck = d["content_file_kinds"]
    if ck:
        for kind, count in sorted(ck.items(), key=lambda x: -x[1]):
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("No classifications.")
    lines.append("")

    lines.append("## Asset / Orphan Breakdown")
    lines.append("")
    ab = d["asset_orphan_breakdown"]
    lines.append("### By Detected Kind")
    for kind, count in sorted(ab["by_detected_kind"].items(), key=lambda x: -x[1]):
        lines.append(f"- {kind}: {count}")
    lines.append("")
    lines.append("### By Path Family")
    for family, count in sorted(ab["by_path_family"].items(), key=lambda x: -x[1]):
        lines.append(f"- {family}: {count}")
    lines.append("")
    lines.append("### By Size Bucket")
    bucket_order = {
        label: idx
        for idx, spec in enumerate(_SIZE_BUCKETS)
        for label in (
            [spec[1]]
            if len(spec) == 2
            else [spec[2]]
        )
    }
    for bucket, count in sorted(
        ab["by_size_bucket"].items(),
        key=lambda item: bucket_order.get(item[0], 999),
    ):
        lines.append(f"- {bucket}: {count}")
    lines.append("")
    lines.append(f"- Sharded assets: {ab['sharded']}")
    lines.append(f"- Non-sharded assets: {ab['non_sharded']}")
    lines.append("")

    if d["failed_paths"]:
        lines.append("## Notable Parse Failures")
        lines.append("")
        for item in d["failed_paths"][:20]:
            lines.append(f"- `{item['path']}`: {item['error']}")
        if len(d["failed_paths"]) > 20:
            lines.append(f"- ... and {len(d['failed_paths']) - 20} more")
        lines.append("")

    lines.append("## Recommended Next Forensic Steps")
    lines.append("")
    lines.append(
        "1. Correlate largest conversations with keyword hits to identify "
        "high-value import candidates."
    )
    lines.append(
        "2. Map orphan assets to source conversations using manifest data "
        "if available."
    )
    lines.append(
        "3. Identify conversations containing `Codexify Task Prompt` "
        "headings for potential structured task extraction."
    )
    lines.append(
        "4. Review parse failures for malformed JSON or unexpected file "
        "encodings."
    )
    lines.append(
        "5. Cross-reference time series with known project milestones."
    )
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_recon_report(
    stats: CorpusReconStats,
    output_dir: Path,
    *,
    diagnostics_subdir: str = "diagnostics",
) -> None:
    diag_dir = output_dir / diagnostics_subdir
    diag_dir.mkdir(parents=True, exist_ok=True)
    write_corpus_stats(stats, diag_dir / "recon_report.json")
    write_corpus_summary_markdown(stats, diag_dir / "recon_report.md")


def run_corpus_recon(
    root_path: str | Path,
    *,
    output_dir: str | Path = "export_archaeology",
) -> CorpusReconStats:
    root = Path(root_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(root)

    write_conversation_index(stats.conversations, out / "conversation_index.csv")
    write_corpus_stats(stats, out / "corpus_stats.json")
    write_corpus_summary_markdown(stats, out / "corpus_summary.md")
    write_recon_report(stats, out)

    return stats


# --- Helpers ---


def _safe_truncate(text: str, limit: int = TRUNCATION_LIMIT) -> str:
    if not text:
        return ""
    stripped = text.strip().replace("\n", " ").replace("\r", " ")
    normalized = " ".join(stripped.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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
    return None


def _iter_json_payloads(record: OpenAIExportFileRecord) -> Iterator[Any]:
    path = Path(record.absolute_path)
    if record.detected_kind in {"json_object", "json_array"}:
        yield json.loads(path.read_text(encoding="utf-8-sig"))
        return
    if record.detected_kind == "jsonl":
        with path.open("r", encoding="utf-8-sig") as fh:
            for line in fh:
                raw = line.strip()
                if raw:
                    yield json.loads(raw)


def _linearize_mainline(
    mapping: dict[str, Any], current_node: Any
) -> list[tuple[str, dict[str, Any]]]:
    active = _resolve_active_node(mapping, current_node)
    if not active:
        return []
    chain: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    node_id = active
    while isinstance(node_id, str) and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        node = mapping.get(node_id)
        if not isinstance(node, dict):
            break
        chain.append((node_id, node))
        parent = node.get("parent")
        node_id = parent if isinstance(parent, str) else ""
    chain.reverse()
    return chain


def _resolve_active_node(
    mapping: dict[str, Any], current_node: Any
) -> str | None:
    if isinstance(current_node, str) and current_node in mapping:
        return current_node
    children: dict[str, int] = {}
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        parent = node.get("parent")
        if isinstance(parent, str):
            children[parent] = children.get(parent, 0) + 1
    for node_id in mapping:
        if node_id not in children:
            children[node_id] = 0
    leaves = sorted(
        [
            node_id
            for node_id, child_count in children.items()
            if child_count == 0 and isinstance(mapping.get(node_id), dict)
        ]
    )
    return leaves[-1] if leaves else None


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_part_text(part) for part in content if _part_text(part))
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            return "\n".join(_part_text(part) for part in parts if _part_text(part))
        text = content.get("text")
        if isinstance(text, str):
            return text
    parts = message.get("parts")
    if isinstance(parts, list):
        return "\n".join(_part_text(part) for part in parts if _part_text(part))
    text = message.get("text")
    return text if isinstance(text, str) else ""


def _part_text(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        text = part.get("text")
        if isinstance(text, str):
            return text
    return ""


def _extract_role(message: dict[str, Any]) -> str:
    author = message.get("author")
    if isinstance(author, dict):
        role = _coerce_str(author.get("role"))
        if role:
            return role.lower()
    for key in ("role", "sender"):
        value = message.get(key)
        if isinstance(value, dict):
            value = value.get("role") or value.get("name")
        role = _coerce_str(value)
        if role:
            lowered = role.lower()
            if lowered == "human":
                return "user"
            if lowered == "model":
                return "assistant"
            return lowered
    return "unknown"


def _classify_path_family(path: str) -> str:
    parts = Path(path).parts
    for part in parts:
        lowered = part.lower()
        if lowered.startswith("conversations"):
            return "conversations"
        if lowered.startswith("workspace"):
            return "workspace"
        if lowered.startswith("files"):
            return "files"
        if lowered == "unassigned":
            return "Unassigned"
        if lowered == "__export_file_manifests__":
            return "__export_file_manifests__"
    return "unknown"


def _classify_size_bucket(size: int) -> str:
    for spec in _SIZE_BUCKETS:
        if len(spec) == 2:
            low, label = spec  # type: ignore[misc]
            if size == low:
                return label
        else:
            low, high, label = spec  # type: ignore[misc]
            if high is None and size >= low:
                return label
            if high is not None and low <= size <= high:
                return label
    return "unknown"


_SHARDED_PATTERNS = [
    re.compile(r"conversations__"),
    re.compile(r"files__"),
    re.compile(r"__export_file_manifests__"),
    re.compile(r"workspace\s*\d+", re.IGNORECASE),
]


def _is_sharded_path(path: str) -> bool:
    parts = Path(path).parts
    for part in parts:
        for pattern in _SHARDED_PATTERNS:
            if pattern.search(part):
                return True
    return False


def _is_workspace_or_files_asset(path: str) -> bool:
    parts = Path(path).parts
    for part in parts:
        lowered = part.lower()
        if lowered.startswith("workspace") or lowered.startswith("files"):
            return True
    return False
