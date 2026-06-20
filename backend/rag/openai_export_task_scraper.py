"""Prototype scraper for Codexify task artifacts inside OpenAI exports."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    OpenAIExportFileRecord,
    OpenAIExportInventory,
)

EXTRACTOR_NAME = "codexify_task_prompt_v1"
ARTIFACT_DIRS = {
    "codexify_task_prompt": "codexify_task_prompts",
    "task_summary": "task_summaries",
    "execution_contract": "execution_contracts",
    "unknown_or_partial": "unknown_or_partial_matches",
}
DIAGNOSTICS_DIR = "diagnostics"
_TEXTUAL_KINDS = {"text", "html"}
_JSON_KINDS = {"json_object", "json_array", "jsonl"}
_CONTAINER_KEYS = ("conversations", "threads", "chats", "items", "data")
_PARTIAL_HINT = re.compile(
    r"(?im)\b(Codexify\s+Task\s+Prompts?|Task\s+Summary|Execution\s+Contract)\b"
)


@dataclass
class SourceMessage:
    text: str
    source_file_path: str
    source_conversation_id: str | None = None
    source_thread_id: str | None = None
    source_message_id: str | None = None
    source_created_at: str | None = None
    source_updated_at: str | None = None


@dataclass
class ExtractedArtifact:
    artifact_type: str
    raw_text: str
    metadata: dict[str, Any]
    parsed_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def artifact_id(self) -> str:
        return str(self.metadata["artifact_id"])


@dataclass
class ScraperReport:
    output_dir: Path
    import_batch_id: str
    files_scanned: int
    messages_scanned: int
    artifacts: list[ExtractedArtifact]
    skipped_files: list[dict[str, str]]
    parse_failures: list[dict[str, str]]

    def counts(self) -> dict[str, int]:
        return {
            "codexify_task_prompt_hits": sum(
                1
                for artifact in self.artifacts
                if artifact.artifact_type == "codexify_task_prompt"
            ),
            "task_summary_hits": sum(
                1
                for artifact in self.artifacts
                if artifact.artifact_type == "task_summary"
            ),
            "execution_contract_hits": sum(
                1
                for artifact in self.artifacts
                if artifact.artifact_type == "execution_contract"
            ),
            "partial_or_ambiguous_hits": sum(
                1
                for artifact in self.artifacts
                if artifact.artifact_type == "unknown_or_partial"
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        counts = self.counts()
        return {
            "extractor": EXTRACTOR_NAME,
            "import_batch_id": self.import_batch_id,
            "output_dir": str(self.output_dir),
            "files_scanned": self.files_scanned,
            "messages_scanned": self.messages_scanned,
            **counts,
            "skipped_files": self.skipped_files,
            "parse_failures": self.parse_failures,
            "artifacts": [
                {
                    "artifact_id": artifact.artifact_id,
                    "artifact_type": artifact.artifact_type,
                    "raw_path": str(
                        self.output_dir
                        / ARTIFACT_DIRS[artifact.artifact_type]
                        / f"{artifact.artifact_id}.md"
                    ),
                    "json_path": str(
                        self.output_dir
                        / ARTIFACT_DIRS[artifact.artifact_type]
                        / f"{artifact.artifact_id}.json"
                    ),
                    "confidence": artifact.metadata.get("confidence"),
                    "source_file_path": artifact.metadata.get(
                        "source_file_path"
                    ),
                    "source_conversation_id": artifact.metadata.get(
                        "source_conversation_id"
                    ),
                    "source_message_id": artifact.metadata.get(
                        "source_message_id"
                    ),
                }
                for artifact in self.artifacts
            ],
        }

    def to_markdown(self) -> str:
        counts = self.counts()
        lines = [
            "# OpenAI Export Task Scraper Report",
            "",
            f"- Extractor: `{EXTRACTOR_NAME}`",
            f"- Import batch: `{self.import_batch_id}`",
            f"- Output directory: `{self.output_dir}`",
            f"- Files scanned: {self.files_scanned}",
            f"- Messages scanned: {self.messages_scanned}",
            f"- Codexify Task Prompt hits: {counts['codexify_task_prompt_hits']}",
            f"- Task Summary hits: {counts['task_summary_hits']}",
            f"- Execution Contract hits: {counts['execution_contract_hits']}",
            f"- Partial or ambiguous hits: {counts['partial_or_ambiguous_hits']}",
            f"- Skipped files: {len(self.skipped_files)}",
            f"- Parse failures: {len(self.parse_failures)}",
            "",
        ]
        if self.skipped_files:
            lines.append("## Skipped Files")
            for item in self.skipped_files:
                lines.append(f"- `{item['path']}`: {item['reason']}")
            lines.append("")
        if self.parse_failures:
            lines.append("## Parse Failures")
            for item in self.parse_failures:
                lines.append(f"- `{item['path']}`: {item['reason']}")
            lines.append("")
        return "\n".join(lines)


class CodexifyTaskPromptExtractor:
    artifact_type = "codexify_task_prompt"
    confidence = 1.0
    _label = re.compile(
        r"(?im)^(?:#{1,6}\s*)?Codexify\s+Task\s+Prompt"
        r"(?:\s*\([^)\n]*\))?\s*:?\s*$"
    )

    def extract(self, text: str) -> list[tuple[str, dict[str, Any]]]:
        stop = re.compile(
            r"(?im)^(?:#{1,6}\s*)?(?:Task\s+Summary|Summary|Execution\s+Contract)"
            r"\s*:?\s*$"
        )
        return [
            (section, {"label": "Codexify Task Prompt"})
            for section in _find_labeled_sections(
                text, self._label, stop_pattern=stop
            )
            if _has_substantive_body(section)
        ]


class TaskSummaryExtractor:
    artifact_type = "task_summary"
    confidence = 1.0
    _label = re.compile(
        r"(?im)^(?:#{1,6}\s*)?Task\s+Summary\s*:?\s*$"
    )

    def extract(self, text: str) -> list[tuple[str, dict[str, Any]]]:
        return [
            (section, {"label": "Task Summary"})
            for section in _find_labeled_sections(
                text,
                self._label,
                stop_pattern=_canonical_or_markdown_stop(
                    "Codexify Task Prompt", "Execution Contract"
                ),
            )
            if _has_substantive_body(section)
        ]


class ExecutionContractExtractor:
    artifact_type = "execution_contract"
    confidence = 1.0
    _label = re.compile(
        r"(?im)^(?:#{1,6}\s*)?\**Execution\s+Contract\**\s*:?\s*$"
    )

    def extract(self, text: str) -> list[tuple[str, dict[str, Any]]]:
        sections: list[tuple[str, dict[str, Any]]] = []
        for section in _find_labeled_sections(
            text, self._label, stop_pattern=_next_markdown_heading()
        ):
            if not _has_substantive_body(section):
                continue
            if _has_execution_contract_shape(section):
                sections.append((section, {"label": "Execution Contract"}))
        return sections


EXTRACTORS = (
    CodexifyTaskPromptExtractor(),
    TaskSummaryExtractor(),
    ExecutionContractExtractor(),
)


def scrape_openai_export_tasks(
    root_path: str | Path,
    *,
    output_dir: str | Path = "export_scraper",
) -> ScraperReport:
    """Scan an OpenAI export and write repo-local task prompt artifacts."""

    inventory = OpenAIExportDetector().scan(root_path)
    output_root = Path(output_dir).expanduser().resolve()
    _prepare_output_dirs(output_root)
    import_batch_id = _build_import_batch_id(inventory)
    extracted_at = _utc_now_iso()

    messages, skipped_files, parse_failures = collect_source_messages(inventory)
    artifacts: list[ExtractedArtifact] = []
    seen_ids: set[str] = set()
    for message in messages:
        message_artifacts = _extract_artifacts_from_message(
            message,
            import_batch_id=import_batch_id,
            extracted_at=extracted_at,
        )
        for artifact in message_artifacts:
            if artifact.artifact_id in seen_ids:
                continue
            seen_ids.add(artifact.artifact_id)
            _write_artifact(output_root, artifact)
            artifacts.append(artifact)

    report = ScraperReport(
        output_dir=output_root,
        import_batch_id=import_batch_id,
        files_scanned=len(inventory.files),
        messages_scanned=len(messages),
        artifacts=artifacts,
        skipped_files=skipped_files,
        parse_failures=parse_failures,
    )
    _write_report(output_root, report)
    return report


def collect_source_messages(
    inventory: OpenAIExportInventory,
) -> tuple[list[SourceMessage], list[dict[str, str]], list[dict[str, str]]]:
    messages: list[SourceMessage] = []
    skipped_files: list[dict[str, str]] = []
    parse_failures: list[dict[str, str]] = []

    for record in inventory.files:
        if record.detected_kind in _JSON_KINDS:
            try:
                before = len(messages)
                for payload in _iter_json_payloads(record):
                    messages.extend(_messages_from_payload(payload, record.path))
                if len(messages) == before:
                    skipped_files.append(
                        {
                            "path": record.path,
                            "reason": "json_without_extractable_message_text",
                        }
                    )
            except Exception as exc:
                parse_failures.append({"path": record.path, "reason": str(exc)})
            continue

        if record.detected_kind in _TEXTUAL_KINDS:
            try:
                text = _read_text(record)
            except Exception as exc:
                parse_failures.append({"path": record.path, "reason": str(exc)})
                continue
            if text.strip():
                messages.append(
                    SourceMessage(
                        text=text,
                        source_file_path=record.path,
                        source_message_id=_stable_source_id(record.path, text),
                    )
                )
            else:
                skipped_files.append({"path": record.path, "reason": "empty_text"})
            continue

        if record.detected_kind == "invalid_json":
            parse_failures.append(
                {
                    "path": record.path,
                    "reason": record.parse_error or "invalid_json",
                }
            )
            continue

        skipped_files.append(
            {"path": record.path, "reason": f"unsupported_kind:{record.detected_kind}"}
        )

    return messages, skipped_files, parse_failures


def _extract_artifacts_from_message(
    message: SourceMessage,
    *,
    import_batch_id: str,
    extracted_at: str,
) -> list[ExtractedArtifact]:
    artifacts: list[ExtractedArtifact] = []
    for extractor in EXTRACTORS:
        for raw_text, parsed_fields in extractor.extract(message.text):
            artifacts.append(
                _build_artifact(
                    artifact_type=extractor.artifact_type,
                    raw_text=raw_text,
                    source=message,
                    import_batch_id=import_batch_id,
                    extracted_at=extracted_at,
                    confidence=extractor.confidence,
                    parsed_fields=parsed_fields,
                )
            )

    if not artifacts and _PARTIAL_HINT.search(message.text or ""):
        raw_text = _safe_boundary_trim(message.text)
        if raw_text:
            artifacts.append(
                _build_artifact(
                    artifact_type="unknown_or_partial",
                    raw_text=raw_text,
                    source=message,
                    import_batch_id=import_batch_id,
                    extracted_at=extracted_at,
                    confidence=0.35,
                    parsed_fields={"reason": "canonical_label_without_v1_shape"},
                )
            )

    return artifacts


def _build_artifact(
    *,
    artifact_type: str,
    raw_text: str,
    source: SourceMessage,
    import_batch_id: str,
    extracted_at: str,
    confidence: float,
    parsed_fields: dict[str, Any],
) -> ExtractedArtifact:
    raw_text = _safe_boundary_trim(raw_text)
    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    artifact_id = _artifact_id(artifact_type, source, content_hash)
    metadata = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "source": "openai_export",
        "source_conversation_id": source.source_conversation_id,
        "source_thread_id": source.source_thread_id,
        "source_message_id": source.source_message_id,
        "source_file_path": source.source_file_path,
        "source_created_at": source.source_created_at,
        "source_updated_at": source.source_updated_at,
        "import_batch_id": import_batch_id,
        "extracted_at": extracted_at,
        "extractor": EXTRACTOR_NAME,
        "confidence": confidence,
        "content_sha256": content_hash,
    }
    return ExtractedArtifact(
        artifact_type=artifact_type,
        raw_text=raw_text,
        metadata=metadata,
        parsed_fields=parsed_fields,
    )


def _messages_from_payload(payload: Any, source_path: str) -> list[SourceMessage]:
    if isinstance(payload, list):
        messages: list[SourceMessage] = []
        for item in payload:
            messages.extend(_messages_from_payload(item, source_path))
        return messages

    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("mapping"), dict):
        return _messages_from_mapping_conversation(payload, source_path)

    nested_messages = payload.get("messages")
    if isinstance(nested_messages, list):
        return _messages_from_messages_container(payload, nested_messages, source_path)

    if _looks_like_single_message(payload):
        message = _source_message_from_message_record(
            payload,
            container=payload,
            source_path=source_path,
        )
        return [message] if message else []

    messages: list[SourceMessage] = []
    for key in _CONTAINER_KEYS:
        nested = payload.get(key)
        if isinstance(nested, list):
            messages.extend(_messages_from_payload(nested, source_path))
    return messages


def _messages_from_mapping_conversation(
    conversation: dict[str, Any], source_path: str
) -> list[SourceMessage]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        return []

    nodes = _linearize_mainline(mapping, conversation.get("current_node"))
    if not nodes:
        nodes = [
            (str(node_id), node)
            for node_id, node in sorted(mapping.items())
            if isinstance(node, dict)
        ]

    messages: list[SourceMessage] = []
    source_thread_id = _clean_str(
        conversation.get("id") or conversation.get("conversation_id")
    )
    source_updated_at = _timestamp_to_metadata(conversation.get("update_time"))
    for node_id, node in nodes:
        raw_message = node.get("message") if isinstance(node, dict) else None
        if not isinstance(raw_message, dict):
            continue
        text = _message_text(raw_message)
        if not text:
            continue
        source_message_id = _clean_str(raw_message.get("id")) or node_id
        messages.append(
            SourceMessage(
                text=text,
                source_file_path=source_path,
                source_conversation_id=source_thread_id,
                source_thread_id=source_thread_id,
                source_message_id=source_message_id,
                source_created_at=_timestamp_to_metadata(
                    raw_message.get("create_time")
                ),
                source_updated_at=source_updated_at,
            )
        )
    return messages


def _messages_from_messages_container(
    container: dict[str, Any],
    raw_messages: list[Any],
    source_path: str,
) -> list[SourceMessage]:
    messages: list[SourceMessage] = []
    for raw in raw_messages:
        if not isinstance(raw, dict):
            continue
        message = _source_message_from_message_record(
            raw, container=container, source_path=source_path
        )
        if message:
            messages.append(message)
    return messages


def _source_message_from_message_record(
    raw: dict[str, Any],
    *,
    container: dict[str, Any],
    source_path: str,
) -> SourceMessage | None:
    message = raw.get("message") if isinstance(raw.get("message"), dict) else raw
    text = _message_text(message)
    if not text:
        return None

    source_thread_id = _clean_str(
        container.get("id")
        or container.get("conversation_id")
        or container.get("thread_id")
        or raw.get("conversation_id")
        or raw.get("thread_id")
        or raw.get("chat_id")
    )
    source_message_id = _clean_str(
        message.get("id")
        or message.get("message_id")
        or raw.get("message_id")
        or raw.get("id")
    )
    if not source_message_id:
        source_message_id = _stable_source_id(source_path, source_thread_id, text)

    return SourceMessage(
        text=text,
        source_file_path=source_path,
        source_conversation_id=source_thread_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        source_created_at=_timestamp_to_metadata(
            message.get("create_time")
            or message.get("created_at")
            or raw.get("create_time")
            or raw.get("created_at")
        ),
        source_updated_at=_timestamp_to_metadata(
            container.get("update_time")
            or container.get("updated_at")
            or raw.get("updated_at")
        ),
    )


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


def _find_labeled_sections(
    text: str, label_pattern: re.Pattern[str], *, stop_pattern: re.Pattern[str]
) -> list[str]:
    matches = list(label_pattern.finditer(text))
    sections: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        next_same = matches[index + 1].start() if index + 1 < len(matches) else None
        stop = _find_stop(text, stop_pattern, match.end())
        candidates = [value for value in (next_same, stop) if value is not None]
        end = min(candidates) if candidates else len(text)
        section = _safe_boundary_trim(text[start:end])
        if section:
            sections.append(section)
    return sections


def _find_stop(
    text: str, stop_pattern: re.Pattern[str], start_at: int
) -> int | None:
    match = stop_pattern.search(text, start_at)
    return match.start() if match else None


def _next_markdown_heading() -> re.Pattern[str]:
    return re.compile(r"(?m)^#{1,3}\s+\S.*$")


def _canonical_or_markdown_stop(*labels: str) -> re.Pattern[str]:
    escaped = "|".join(re.escape(label).replace(r"\ ", r"\s+") for label in labels)
    return re.compile(rf"(?im)^(?:#{{1,3}}\s+\S.*|(?:{escaped})\s*:?\s*)$")


def _has_substantive_body(section: str) -> bool:
    lines = [line for line in section.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    body = "\n".join(lines[1:]).strip()
    return len(body) >= 24


def _has_execution_contract_shape(section: str) -> bool:
    lowered = section.lower()
    yaml_markers = all(
        marker in lowered
        for marker in ("id:", "title:", "status:", "priority:")
    )
    heading_markers = sum(
        1
        for marker in (
            "summary",
            "purpose",
            "scope",
            "acceptance",
            "blast radius",
            "rollback",
            "review",
        )
        if marker in lowered
    )
    return yaml_markers or heading_markers >= 3


def _safe_boundary_trim(text: str) -> str:
    return text.strip("\n\r\t ")


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
    children = dict.fromkeys(mapping.keys(), 0)
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        parent = node.get("parent")
        if isinstance(parent, str) and parent in children:
            children[parent] += 1
    leaves = sorted(
        [
            node_id
            for node_id, child_count in children.items()
            if child_count == 0 and isinstance(mapping.get(node_id), dict)
        ]
    )
    return leaves[-1] if leaves else None


def _iter_json_payloads(record: OpenAIExportFileRecord) -> Iterator[Any]:
    path = Path(record.absolute_path)
    if record.detected_kind in {"json_object", "json_array"}:
        yield json.loads(path.read_text(encoding="utf-8-sig"))
        return
    if record.detected_kind == "jsonl":
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def _read_text(record: OpenAIExportFileRecord) -> str:
    return Path(record.absolute_path).read_text(encoding="utf-8-sig")


def _looks_like_single_message(payload: dict[str, Any]) -> bool:
    if isinstance(payload.get("message"), dict):
        return True
    return any(key in payload for key in ("content", "parts", "text")) and any(
        key in payload for key in ("conversation_id", "thread_id", "message_id", "id")
    )


def _prepare_output_dirs(output_root: Path) -> None:
    for dirname in ARTIFACT_DIRS.values():
        (output_root / dirname).mkdir(parents=True, exist_ok=True)
    (output_root / DIAGNOSTICS_DIR).mkdir(parents=True, exist_ok=True)


def _write_artifact(output_root: Path, artifact: ExtractedArtifact) -> None:
    target_dir = output_root / ARTIFACT_DIRS[artifact.artifact_type]
    raw_path = target_dir / f"{artifact.artifact_id}.md"
    json_path = target_dir / f"{artifact.artifact_id}.json"
    raw_path.write_text(artifact.raw_text, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "metadata": artifact.metadata,
                "parsed_fields": artifact.parsed_fields,
                "raw_file": raw_path.name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_report(output_root: Path, report: ScraperReport) -> None:
    diagnostics = output_root / DIAGNOSTICS_DIR
    (diagnostics / "scraper_report.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (diagnostics / "scraper_report.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )


def _build_import_batch_id(inventory: OpenAIExportInventory) -> str:
    payload = [
        {
            "path": record.path,
            "size": record.size,
            "kind": record.detected_kind,
            "magic": record.magic_signature,
        }
        for record in inventory.files
    ]
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"openai-export-{digest[:16]}"


def _artifact_id(
    artifact_type: str, source: SourceMessage, content_hash: str
) -> str:
    basis = {
        "artifact_type": artifact_type,
        "source_conversation_id": source.source_conversation_id,
        "source_thread_id": source.source_thread_id,
        "source_message_id": source.source_message_id,
        "source_file_path": source.source_file_path,
        "content_hash": content_hash,
    }
    digest = hashlib.sha256(
        json.dumps(basis, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"{artifact_type}-{digest[:20]}"


def _stable_source_id(*parts: Any) -> str:
    digest = hashlib.sha256(
        json.dumps(parts, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return f"source-{digest[:20]}"


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _timestamp_to_metadata(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        if parsed > 1_000_000_000_000:
            parsed = parsed / 1000.0
        try:
            return datetime.fromtimestamp(parsed, timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
