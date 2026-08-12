#!/usr/bin/env python3
"""Validate and generate deterministic Document Lifecycle Graph projections.

This local control-plane tool reads only Git-backed DLG node records and the
DLG JSON Schema.  It intentionally has no Guardian, runtime, network, or
provider dependencies.  Generated projections are disposable, derived, and
never change canonical node records.

Usage:
  python3 scripts/knowledge_graph/validate_and_generate_dlg.py validate
  python3 scripts/knowledge_graph/validate_and_generate_dlg.py generate \
    --repository-revision <40-char-sha> --generated-at <RFC3339 timestamp>
  python3 scripts/knowledge_graph/validate_and_generate_dlg.py check-generated \
    --repository-revision <40-char-sha> --generated-at <RFC3339 timestamp>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence
from urllib.parse import unquote

import jsonschema


SCRIPT_ID = "scripts/knowledge_graph/validate_and_generate_dlg.py"
SCHEMA_VERSION = "1.0.0"
GRAPH_ID = "codexify:graph:document-lifecycle"
NODES_RELATIVE_DIR = Path("docs/knowledge-graph/nodes")
SCHEMA_RELATIVE_PATH = Path(
    "schemas/knowledge/document-lifecycle-graph.schema.json"
)
DEFAULT_OUTPUT_RELATIVE_DIR = Path("docs/knowledge-graph/generated")

OUTPUT_FILENAMES = (
    "document-graph.json",
    "stale-documents.json",
    "supersession-map.json",
    "authority-conflicts.json",
    "collisions.json",
    "orphans.json",
)

REPORT_RECORD_TYPES = {
    "stale-documents.json": "stale_documents_report",
    "supersession-map.json": "supersession_map",
    "authority-conflicts.json": "authority_conflicts_report",
    "collisions.json": "collision_report",
    "orphans.json": "orphan_report",
}

NOTICE = (
    "Generated derived projection. Reconstructable from canonical Git-backed "
    "DLG inputs; non-authoritative; do not hand edit."
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
PRIVATE_UNIX_PATH_RE = re.compile(
    r"(?:^|[\s\"'(<])/(?:Users|home|Volumes|private|var/folders)/[^\s\"')>]*"
)
WINDOWS_PATH_RE = re.compile(r"(?:^|[\s\"'(<])[A-Za-z]:[\\/]")
FILE_URI_RE = re.compile(r"\bfile://", re.IGNORECASE)
OPENAI_SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
GITHUB_SECRET_RE = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
AWS_SECRET_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
ENV_ASSIGNMENT_RE = re.compile(
    r"\b[A-Z][A-Z0-9_]{2,}=(?!true\b|false\b|null\b|none\b|0\b|1\b)[^\s\"']{8,}",
    re.IGNORECASE,
)
SECRET_FIELD_RE = re.compile(
    r"(?:api[_-]?key|secret|password|private[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token)$",
    re.IGNORECASE,
)
TEMPORAL_PROSE_RE = re.compile(
    r"\b(?:\d+\s*(?:day|week|month|year)s?|daily|weekly|monthly|annually|"
    r"every\s+\d+|expires?\s+(?:after|in)|freshness\s+window)\b",
    re.IGNORECASE,
)
INLINE_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
ADR_FILENAME_RE = re.compile(r"^(?P<number>[0-9]{3})-.*\.md$")


class ToolConfigurationError(RuntimeError):
    """Raised when required local Git/schema inputs cannot be used."""


@dataclass(frozen=True)
class Issue:
    """One deterministic validator observation."""

    severity: str
    code: str
    message: str
    document_id: str = ""
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        value = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.document_id:
            value["document_id"] = self.document_id
        if self.path:
            value["path"] = self.path
        return value


@dataclass
class ValidationResult:
    """All semantic inputs, findings, and report payload fragments."""

    repository_root: Path
    repository_revision: str
    generated_at: str
    schema: dict[str, Any]
    schema_bytes: bytes
    nodes: list[dict[str, Any]]
    node_files: list[Path]
    graph_revision: str
    issues: list[Issue] = field(default_factory=list)
    schema_valid_node_count: int = 0
    source_hash_match_count: int = 0
    target_resolution_count: int = 0
    self_relation_count: int = 0
    duplicate_relation_count: int = 0
    cycle_findings: dict[str, list[list[str]]] = field(default_factory=dict)
    accepted_contract_governance_findings: int = 0
    local_link_findings: list[dict[str, str]] = field(default_factory=list)
    prohibited_metadata_findings: int = 0
    plaintext_lfs_findings: int = 0
    retrieval_policy_findings: int = 0
    stale_documents: list[dict[str, Any]] = field(default_factory=list)
    changed_anchors: list[dict[str, Any]] = field(default_factory=list)
    coverage_gaps: list[dict[str, str]] = field(default_factory=list)
    supersession_set: list[dict[str, str]] = field(default_factory=list)
    authority_conflicts: list[dict[str, Any]] = field(default_factory=list)
    document_id_collisions: list[dict[str, Any]] = field(default_factory=list)
    active_path_collisions: list[dict[str, Any]] = field(default_factory=list)
    adr_number_collisions: list[dict[str, Any]] = field(default_factory=list)
    orphans: list[dict[str, str]] = field(default_factory=list)

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        *,
        document_id: str = "",
        path: str = "",
    ) -> None:
        self.issues.append(
            Issue(
                severity=severity,
                code=code,
                message=message,
                document_id=document_id,
                path=path,
            )
        )

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def edge_count(self) -> int:
        return sum(len(node.get("relations", [])) for node in self.nodes)

    def predicate_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            for relation in node.get("relations", []):
                relation_type = relation.get("relation_type", "<invalid>")
                counts[relation_type] = counts.get(relation_type, 0) + 1
        return dict(sorted(counts.items()))

    def summary(self) -> dict[str, Any]:
        """Return a deterministic, concise Phase 3A proof summary."""
        errors = sorted(
            (issue.as_dict() for issue in self.issues if issue.severity == "error"),
            key=_issue_sort_key,
        )
        warnings = sorted(
            (issue.as_dict() for issue in self.issues if issue.severity == "warning"),
            key=_issue_sort_key,
        )
        return {
            "tool": SCRIPT_ID,
            "result": "fail" if errors else "pass",
            "repository_revision": self.repository_revision,
            "generated_at": self.generated_at,
            "graph_revision": self.graph_revision,
            "corpus": {
                "node_count": len(self.nodes),
                "edge_count": self.edge_count,
                "predicate_counts": self.predicate_counts(),
            },
            "validation": {
                "schema_valid_node_count": self.schema_valid_node_count,
                "source_hash_match_count": self.source_hash_match_count,
                "target_resolution_count": self.target_resolution_count,
                "self_relation_count": self.self_relation_count,
                "duplicate_relation_count": self.duplicate_relation_count,
                "cycle_findings": {
                    predicate: len(cycles)
                    for predicate, cycles in sorted(self.cycle_findings.items())
                },
                "accepted_contract_governance_findings": self.accepted_contract_governance_findings,
                "plaintext_lfs_findings": self.plaintext_lfs_findings,
                "local_link_findings": len(self.local_link_findings),
                "prohibited_metadata_findings": self.prohibited_metadata_findings,
                "retrieval_policy_contradictions": self.retrieval_policy_findings,
            },
            "generated_findings": {
                "stale_document_count": len(self.stale_documents),
                "changed_anchor_count": len(self.changed_anchors),
                "freshness_coverage_gap_count": len(self.coverage_gaps),
                "supersession_count": len(self.supersession_set),
                "authority_conflict_count": len(self.authority_conflicts),
                "adr_number_collision_count": len(self.adr_number_collisions),
                "orphan_count": len(self.orphans),
            },
            "errors": errors,
            "warnings": warnings,
        }


def _issue_sort_key(issue: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        issue.get("severity", ""),
        issue.get("code", ""),
        issue.get("document_id", ""),
        issue.get("path", ""),
    )


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _pretty_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_lfs_pointer(data: bytes) -> bool:
    return data.startswith(LFS_POINTER_PREFIX)


def _read_utf8_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    data.decode("utf-8")
    return data


def _run_git(repository_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *args],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git_stdout(repository_root: Path, *args: str) -> str | None:
    completed = _run_git(repository_root, *args)
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_commit_exists(repository_root: Path, revision: str) -> bool:
    completed = _run_git(repository_root, "cat-file", "-e", f"{revision}^{{commit}}")
    return completed.returncode == 0


def _git_is_ancestor(repository_root: Path, older: str, newer: str) -> bool:
    completed = _run_git(repository_root, "merge-base", "--is-ancestor", older, newer)
    return completed.returncode == 0


def _git_revision_timestamp(repository_root: Path, revision: str) -> str:
    stdout = _git_stdout(repository_root, "show", "-s", "--format=%cI", revision)
    if stdout is None or not stdout.strip():
        raise ToolConfigurationError(
            f"Cannot derive deterministic generation timestamp for revision {revision}."
        )
    return stdout.strip()


def _parse_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty RFC3339 date-time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an explicit UTC offset")
    return parsed


def _validate_generation_parameters(repository_revision: str, generated_at: str) -> None:
    if not SHA_RE.fullmatch(repository_revision):
        raise ToolConfigurationError(
            "repository revision must be a full lowercase 40-character Git SHA."
        )
    try:
        _parse_datetime(generated_at)
    except ValueError as exc:
        raise ToolConfigurationError(
            f"generated-at must be an RFC3339 date-time with an offset: {exc}"
        ) from exc


def _root_relative_path(repository_root: Path, candidate: Path) -> str:
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(repository_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_repository_path(repository_root: Path, raw_path: Any) -> Path | None:
    """Resolve one ordinary repository-relative path without escaping root."""
    if not isinstance(raw_path, str) or not raw_path:
        return None
    if raw_path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw_path):
        return None
    pure = PurePosixPath(raw_path)
    if any(part in {"", ".", ".."} for part in pure.parts):
        return None
    candidate = (repository_root / raw_path).resolve()
    try:
        candidate.relative_to(repository_root.resolve())
    except ValueError:
        return None
    return candidate


def _resolve_source_anchor_paths(repository_root: Path, raw_path: Any) -> list[Path]:
    """Resolve a source-anchor locator or glob deterministically."""
    if not isinstance(raw_path, str) or not raw_path:
        return []
    if raw_path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw_path):
        return []
    pure = PurePosixPath(raw_path)
    if any(part in {"", ".", ".."} for part in pure.parts):
        return []
    has_glob = any(character in raw_path for character in "*?[")
    if not has_glob:
        candidate = _resolve_repository_path(repository_root, raw_path)
        return [candidate] if candidate is not None and candidate.exists() else []
    matches: list[Path] = []
    for match in sorted(repository_root.glob(raw_path), key=lambda item: item.as_posix()):
        try:
            match.resolve().relative_to(repository_root.resolve())
        except ValueError:
            continue
        matches.append(match)
    return matches


def _add_plaintext_issue(
    result: ValidationResult,
    code: str,
    message: str,
    *,
    path: str,
    document_id: str = "",
) -> None:
    result.plaintext_lfs_findings += 1
    result.add("error", code, message, path=path, document_id=document_id)


def _check_utf8_and_lfs(
    result: ValidationResult,
    path: Path,
    *,
    label: str,
    document_id: str = "",
) -> bytes | None:
    relative = _root_relative_path(result.repository_root, path)
    try:
        data = _read_utf8_bytes(path)
    except (OSError, UnicodeDecodeError) as exc:
        _add_plaintext_issue(
            result,
            f"{label}_not_utf8",
            f"{label} must be readable UTF-8 JSON: {exc}",
            path=relative,
            document_id=document_id,
        )
        return None
    if _is_lfs_pointer(data):
        _add_plaintext_issue(
            result,
            f"{label}_lfs_pointer",
            f"{label} contains a Git LFS pointer rather than JSON text.",
            path=relative,
            document_id=document_id,
        )
        return None
    return data


def _parse_git_attributes(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split(": ", 2)
        if len(parts) != 3:
            continue
        _, attribute, value = parts
        values[attribute] = value
    return values


def _check_attributes(
    result: ValidationResult,
    relative_path: str,
    *,
    graph_record: bool,
    check_git: bool,
) -> None:
    if not check_git:
        return
    completed = _run_git(
        result.repository_root,
        "check-attr",
        "filter",
        "diff",
        "merge",
        "text",
        "--",
        relative_path,
    )
    if completed.returncode != 0:
        _add_plaintext_issue(
            result,
            "git_attribute_check_failed",
            f"Cannot inspect Git attributes: {completed.stderr.strip() or 'git check-attr failed'}",
            path=relative_path,
        )
        return
    attributes = _parse_git_attributes(completed.stdout)
    if graph_record:
        expected = {
            "filter": "unspecified",
            "diff": "set",
            "merge": "unspecified",
            "text": "set",
        }
        for attribute, expected_value in expected.items():
            actual = attributes.get(attribute)
            if actual != expected_value:
                _add_plaintext_issue(
                    result,
                    "graph_json_attribute_invalid",
                    f"{relative_path} has {attribute}={actual!r}; expected {expected_value!r}.",
                    path=relative_path,
                )
    elif attributes.get("filter") == "set" or attributes.get("text") != "set":
        _add_plaintext_issue(
            result,
            "schema_json_attribute_invalid",
            f"{relative_path} must remain normal readable text, not a filtered binary artifact.",
            path=relative_path,
        )


def _find_prohibited_metadata(value: Any, location: str = "$") -> list[tuple[str, str]]:
    """Find bounded secret/path violations without treating ordinary words as secrets."""
    findings: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key in sorted(value):
            item = value[key]
            child_location = f"{location}.{key}"
            if SECRET_FIELD_RE.search(key) and isinstance(item, str) and item.strip():
                findings.append((child_location, "secret-bearing metadata field"))
            findings.extend(_find_prohibited_metadata(item, child_location))
        return findings
    if isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_find_prohibited_metadata(item, f"{location}[{index}]"))
        return findings
    if not isinstance(value, str):
        return findings
    patterns = (
        (PRIVATE_UNIX_PATH_RE, "private absolute host path"),
        (WINDOWS_PATH_RE, "Windows drive path"),
        (FILE_URI_RE, "file URI"),
        (OPENAI_SECRET_RE, "OpenAI-style secret"),
        (GITHUB_SECRET_RE, "GitHub-style secret"),
        (AWS_SECRET_RE, "AWS access key"),
        (PRIVATE_KEY_RE, "private key material"),
        (ENV_ASSIGNMENT_RE, "raw environment-variable value"),
    )
    for pattern, reason in patterns:
        if pattern.search(value):
            findings.append((location, reason))
    return findings


def _record_prohibited_metadata(
    result: ValidationResult,
    value: Any,
    *,
    document_id: str = "",
    path: str = "",
) -> None:
    for location, reason in _find_prohibited_metadata(value):
        result.prohibited_metadata_findings += 1
        result.add(
            "error",
            "prohibited_metadata",
            f"Prohibited {reason} at {location}.",
            document_id=document_id,
            path=path,
        )


def _parse_json_object(
    result: ValidationResult,
    raw: bytes,
    *,
    label: str,
    path: str,
    document_id: str = "",
) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        result.add(
            "error",
            f"{label}_json_invalid",
            f"Invalid JSON: {exc}",
            document_id=document_id,
            path=path,
        )
        return None
    if not isinstance(parsed, dict):
        result.add(
            "error",
            f"{label}_root_invalid",
            "JSON root must be an object.",
            document_id=document_id,
            path=path,
        )
        return None
    return parsed


def _load_schema(repository_root: Path, check_git: bool) -> tuple[dict[str, Any], bytes]:
    schema_path = repository_root / SCHEMA_RELATIVE_PATH
    if not schema_path.is_file():
        raise ToolConfigurationError(f"Missing DLG schema: {SCHEMA_RELATIVE_PATH}")
    raw = _read_utf8_bytes(schema_path)
    if _is_lfs_pointer(raw):
        raise ToolConfigurationError(f"DLG schema is a Git LFS pointer: {SCHEMA_RELATIVE_PATH}")
    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolConfigurationError(f"Invalid DLG schema JSON: {exc}") from exc
    if not isinstance(schema, dict):
        raise ToolConfigurationError("DLG schema root must be a JSON object.")
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        raise ToolConfigurationError(f"Invalid Draft 2020-12 DLG schema: {exc}") from exc
    return schema, raw


def _load_canonical_nodes(
    result: ValidationResult,
    validator: jsonschema.Draft202012Validator,
    *,
    check_git: bool,
) -> None:
    node_dir = result.repository_root / NODES_RELATIVE_DIR
    if not node_dir.is_dir():
        result.add(
            "error",
            "node_directory_missing",
            "Canonical DLG node directory is missing.",
            path=NODES_RELATIVE_DIR.as_posix(),
        )
        return
    entries = sorted(node_dir.iterdir(), key=lambda item: item.name)
    for entry in entries:
        if not entry.is_file() or entry.suffix != ".json":
            result.add(
                "error",
                "node_directory_ambiguous",
                "Canonical DLG node directory contains an unexpected non-JSON entry.",
                path=_root_relative_path(result.repository_root, entry),
            )
    for node_file in (entry for entry in entries if entry.is_file() and entry.suffix == ".json"):
        relative = _root_relative_path(result.repository_root, node_file)
        raw = _check_utf8_and_lfs(result, node_file, label="node")
        if raw is None:
            continue
        node = _parse_json_object(result, raw, label="node", path=relative)
        if node is None:
            continue
        document_id = node.get("document_id", "")
        if isinstance(document_id, str) and node_file.name != f"{document_id}.json":
            result.add(
                "error",
                "canonical_filename_identity_mismatch",
                "Canonical node filename must equal <document_id>.json.",
                document_id=document_id,
                path=relative,
            )
        errors = sorted(
            validator.iter_errors(node),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        if errors:
            for error in errors:
                result.add(
                    "error",
                    "node_schema_invalid",
                    error.message,
                    document_id=document_id if isinstance(document_id, str) else "",
                    path=relative,
                )
        else:
            result.schema_valid_node_count += 1
        _record_prohibited_metadata(
            result,
            node,
            document_id=document_id if isinstance(document_id, str) else "",
            path=relative,
        )
        result.node_files.append(node_file)
        result.nodes.append(node)
        _check_attributes(result, relative, graph_record=True, check_git=check_git)
    result.nodes.sort(key=lambda node: (str(node.get("document_id", "")), _canonical_json_bytes(node)))
    result.node_files.sort(key=lambda path: path.name)


def _detect_document_id_collisions(result: ValidationResult) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in result.nodes:
        document_id = node.get("document_id")
        if isinstance(document_id, str):
            grouped.setdefault(document_id, []).append(node)
    for document_id, nodes in sorted(grouped.items()):
        if len(nodes) < 2:
            continue
        paths = sorted(str(node.get("path", "")) for node in nodes)
        result.document_id_collisions.append(
            {"document_id": document_id, "paths": paths}
        )
        result.add(
            "error",
            "duplicate_document_id",
            "Duplicate canonical document_id.",
            document_id=document_id,
        )


def _is_active_path_node(node: dict[str, Any]) -> bool:
    return node.get("lifecycle_state") not in {"retired", "tombstoned"}


def _detect_active_path_collisions(result: ValidationResult) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in result.nodes:
        path = node.get("path")
        if isinstance(path, str) and _is_active_path_node(node):
            grouped.setdefault(path, []).append(node)
    for path, nodes in sorted(grouped.items()):
        if len(nodes) < 2:
            continue
        document_ids = sorted(str(node.get("document_id", "")) for node in nodes)
        result.active_path_collisions.append(
            {"path": path, "document_ids": document_ids}
        )
        result.add(
            "error",
            "duplicate_active_path",
            "Multiple active DLG records claim the same canonical path.",
            path=path,
        )


def _validate_source_integrity(result: ValidationResult) -> dict[tuple[str, str], list[Path]]:
    """Validate governed source files, hashes, source anchors, and local links."""
    anchor_matches: dict[tuple[str, str], list[Path]] = {}
    for node in result.nodes:
        document_id = str(node.get("document_id", ""))
        source_path_value = node.get("path")
        source_path = _resolve_repository_path(result.repository_root, source_path_value)
        if source_path is None or not source_path.is_file():
            result.add(
                "error",
                "canonical_source_missing",
                "Canonical source path is missing, non-file, or resolves outside the repository.",
                document_id=document_id,
                path=str(source_path_value or ""),
            )
        else:
            try:
                source_bytes = source_path.read_bytes()
            except OSError as exc:
                result.add(
                    "error",
                    "canonical_source_unreadable",
                    f"Cannot read canonical source: {exc}",
                    document_id=document_id,
                    path=str(source_path_value),
                )
            else:
                expected_hash = node.get("content_hash")
                if expected_hash == _sha256(source_bytes):
                    result.source_hash_match_count += 1
                else:
                    result.add(
                        "error",
                        "content_hash_mismatch",
                        "Canonical source bytes do not match node content_hash.",
                        document_id=document_id,
                        path=str(source_path_value),
                    )
                if source_path.suffix.lower() in {".md", ".markdown"}:
                    _validate_markdown_links(result, document_id, source_path)

        for anchor in node.get("source_anchors", []):
            if not isinstance(anchor, dict):
                continue
            anchor_path = anchor.get("path")
            matches = _resolve_source_anchor_paths(result.repository_root, anchor_path)
            if not matches:
                result.add(
                    "error",
                    "source_anchor_missing",
                    "Repository-relative source anchor does not resolve.",
                    document_id=document_id,
                    path=str(anchor_path or ""),
                )
                continue
            anchor_matches[(document_id, str(anchor_path))] = matches
    return anchor_matches


def _normalise_markdown_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1].strip()
    if " " in target:
        target = target.split(" ", 1)[0]
    return target


def _validate_markdown_links(
    result: ValidationResult,
    document_id: str,
    source_path: Path,
) -> None:
    try:
        text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result.add(
            "error",
            "markdown_source_unreadable",
            f"Cannot inspect Markdown links: {exc}",
            document_id=document_id,
            path=_root_relative_path(result.repository_root, source_path),
        )
        return
    for match in INLINE_LINK_RE.finditer(text):
        target = _normalise_markdown_target(match.group(1))
        if not target or target.startswith("#"):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        target_without_fragment = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not target_without_fragment:
            continue
        if target_without_fragment.startswith("/"):
            resolved = None
        else:
            resolved = (source_path.parent / target_without_fragment).resolve()
            try:
                resolved.relative_to(result.repository_root.resolve())
            except ValueError:
                resolved = None
        if resolved is not None and resolved.exists():
            continue
        source_relative = _root_relative_path(result.repository_root, source_path)
        result.local_link_findings.append(
            {
                "document_id": document_id,
                "source_path": source_relative,
                "target": target_without_fragment,
            }
        )
        result.add(
            "warning",
            "broken_local_markdown_link",
            "Repository-local Markdown link target does not exist.",
            document_id=document_id,
            path=source_relative,
        )


def _all_relations(result: ValidationResult) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for node in result.nodes:
        relations = node.get("relations", [])
        if isinstance(relations, list):
            for relation in relations:
                if isinstance(relation, dict):
                    rows.append((node, relation))
    return rows


def _validate_relation_targets_and_self_edges(result: ValidationResult) -> None:
    document_ids = {
        node.get("document_id") for node in result.nodes if isinstance(node.get("document_id"), str)
    }
    for source, relation in _all_relations(result):
        source_id = str(source.get("document_id", ""))
        target_id = relation.get("target_document_id")
        if target_id in document_ids:
            result.target_resolution_count += 1
        else:
            result.add(
                "error",
                "relationship_target_unresolved",
                "Relationship target does not resolve to a canonical DLG node.",
                document_id=source_id,
                path=str(target_id or ""),
            )
        if target_id == source_id:
            result.self_relation_count += 1
            result.add(
                "error",
                "self_relation",
                "DLG relations may not target their source node.",
                document_id=source_id,
            )


def _validate_duplicate_relations(result: ValidationResult) -> None:
    for node in result.nodes:
        document_id = str(node.get("document_id", ""))
        seen: set[tuple[Any, Any, Any, Any, Any]] = set()
        for relation in node.get("relations", []):
            if not isinstance(relation, dict):
                continue
            key = (
                relation.get("relation_type"),
                relation.get("target_document_id"),
                relation.get("authority_scope"),
                relation.get("canonicality"),
                relation.get("review_status"),
            )
            if key in seen:
                result.duplicate_relation_count += 1
                result.add(
                    "error",
                    "duplicate_relationship",
                    "Duplicate DLG relationship identity on one source node.",
                    document_id=document_id,
                )
            seen.add(key)


def _find_directed_cycles(
    edges: dict[str, list[str]],
) -> list[list[str]]:
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for neighbor in sorted(edges.get(node, [])):
            if state.get(neighbor, 0) == 0:
                visit(neighbor)
            elif state.get(neighbor) == 1:
                start = stack.index(neighbor)
                cycle = stack[start:] + [neighbor]
                rotations = [tuple(cycle[index:-1] + cycle[:index] + [cycle[index]]) for index in range(len(cycle) - 1)]
                cycles.add(min(rotations))
        stack.pop()
        state[node] = 2

    for node in sorted(edges):
        if state.get(node, 0) == 0:
            visit(node)
    return [list(cycle) for cycle in sorted(cycles)]


def _validate_acyclic_predicates(result: ValidationResult) -> None:
    for predicate in ("pointer_to", "supersedes", "derived_from"):
        graph: dict[str, list[str]] = {}
        for source, relation in _all_relations(result):
            if relation.get("relation_type") != predicate:
                continue
            source_id = str(source.get("document_id", ""))
            target_id = relation.get("target_document_id")
            if isinstance(target_id, str):
                graph.setdefault(source_id, []).append(target_id)
        cycles = _find_directed_cycles(graph)
        result.cycle_findings[predicate] = cycles
        for cycle in cycles:
            result.add(
                "error",
                "forbidden_relation_cycle",
                f"{predicate} cycle: {' -> '.join(cycle)}",
                document_id=cycle[0] if cycle else "",
            )


def _validate_compatibility_pointers(result: ValidationResult) -> None:
    for node in result.nodes:
        if node.get("kind") != "compatibility_pointer":
            continue
        pointers = [
            relation
            for relation in node.get("relations", [])
            if isinstance(relation, dict) and relation.get("relation_type") == "pointer_to"
        ]
        if len(pointers) != 1:
            result.add(
                "error",
                "compatibility_pointer_cardinality",
                "Compatibility pointer must have exactly one pointer_to relation.",
                document_id=str(node.get("document_id", "")),
            )


def _node_map(result: ValidationResult) -> dict[str, dict[str, Any]]:
    return {
        node["document_id"]: node
        for node in result.nodes
        if isinstance(node.get("document_id"), str)
    }


def _validate_accepted_contract_governance(result: ValidationResult) -> None:
    nodes = _node_map(result)
    for node in result.nodes:
        if not (
            node.get("kind") == "architecture_contract"
            and node.get("disposition") == "accepted"
        ):
            continue
        document_id = str(node.get("document_id", ""))
        if node.get("governing_adr_posture") != "accepted":
            result.accepted_contract_governance_findings += 1
            result.add(
                "error",
                "accepted_contract_governing_posture_invalid",
                "Accepted architecture contract requires governing_adr_posture=accepted.",
                document_id=document_id,
            )
        governing_relations = [
            relation
            for relation in node.get("relations", [])
            if isinstance(relation, dict) and relation.get("relation_type") == "governed_by"
        ]
        accepted_canonical = [
            relation
            for relation in governing_relations
            if relation.get("canonicality") == "canonical"
            and relation.get("review_status") == "accepted"
        ]
        if not accepted_canonical:
            result.accepted_contract_governance_findings += 1
            result.add(
                "error",
                "accepted_contract_governing_relation_missing",
                "Accepted architecture contract requires an accepted canonical governed_by relation.",
                document_id=document_id,
            )
        for relation in governing_relations:
            target = nodes.get(str(relation.get("target_document_id", "")))
            if not (
                target
                and target.get("kind") == "adr"
                and target.get("authority_class") == "accepted_adr"
                and target.get("disposition") == "accepted"
            ):
                result.accepted_contract_governance_findings += 1
                result.add(
                    "error",
                    "accepted_contract_governing_target_invalid",
                    "governed_by target for an accepted architecture contract must be an accepted ADR node.",
                    document_id=document_id,
                )


def _validate_proof_invariants(result: ValidationResult) -> None:
    for node in result.nodes:
        if node.get("kind") != "proof":
            continue
        document_id = str(node.get("document_id", ""))
        if node.get("authority_class") != "evidence_only":
            result.add(
                "error",
                "proof_authority_invariant",
                "Proof nodes must retain authority_class=evidence_only.",
                document_id=document_id,
            )
        if node.get("lifecycle_state") != "frozen":
            result.add(
                "error",
                "proof_lifecycle_invariant",
                "Proof nodes must retain lifecycle_state=frozen.",
                document_id=document_id,
            )


def _validate_retrieval_policy(result: ValidationResult) -> None:
    for node in result.nodes:
        policy = node.get("retrieval_policy")
        if not isinstance(policy, dict):
            continue
        overlap = sorted(
            set(policy.get("applicable_intents", []))
            & set(policy.get("excluded_intents", []))
        )
        if overlap:
            result.retrieval_policy_findings += 1
            result.add(
                "error",
                "retrieval_policy_contradiction",
                f"Intent(s) appear in both applicable and excluded sets: {', '.join(overlap)}.",
                document_id=str(node.get("document_id", "")),
            )


def _collect_supersession(result: ValidationResult) -> None:
    entries: list[dict[str, str]] = []
    for source, relation in _all_relations(result):
        if not (
            relation.get("relation_type") == "supersedes"
            and relation.get("canonicality") == "canonical"
            and relation.get("review_status") == "accepted"
        ):
            continue
        entries.append(
            {
                "newer_document_id": str(source.get("document_id", "")),
                "older_document_id": str(relation.get("target_document_id", "")),
            }
        )
    result.supersession_set = sorted(
        entries,
        key=lambda item: (item["newer_document_id"], item["older_document_id"]),
    )


def _active_authority_nodes(result: ValidationResult) -> Iterable[dict[str, Any]]:
    authoritative = {
        "release_authority",
        "accepted_adr",
        "normative_contract",
        "structural_authority",
        "operator_authority",
        "design_canon",
    }
    for node in result.nodes:
        if node.get("lifecycle_state") in {"retired", "tombstoned"}:
            continue
        if node.get("authority_class") in authoritative:
            yield node


def _collect_authority_conflicts(result: ValidationResult) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in _active_authority_nodes(result):
        for scope in node.get("authority_scopes", []):
            if isinstance(scope, str):
                grouped.setdefault(scope, []).append(node)
    conflicts: list[dict[str, Any]] = []
    for scope, nodes in sorted(grouped.items()):
        document_ids = sorted(str(node.get("document_id", "")) for node in nodes)
        if len(document_ids) < 2:
            continue
        classes = {
            str(node.get("document_id", "")): str(node.get("authority_class", ""))
            for node in sorted(nodes, key=lambda item: str(item.get("document_id", "")))
        }
        release_nodes = [
            node
            for node in nodes
            if node.get("authority_class") == "release_authority"
            and node.get("lifecycle_state") == "active"
            and node.get("disposition") == "accepted"
        ]
        if len(release_nodes) > 1:
            reason = "multiple active accepted release-authority records claim the exact scope"
        else:
            reason = "multiple active canonical/normative records claim the exact scope"
        conflicts.append(
            {
                "scope": scope,
                "document_ids": document_ids,
                "authority_classes": classes,
                "reason": reason,
            }
        )
    result.authority_conflicts = conflicts


def _collect_orphans(result: ValidationResult) -> None:
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for node in result.nodes:
        document_id = str(node.get("document_id", ""))
        incoming.setdefault(document_id, 0)
        outgoing.setdefault(document_id, 0)
    for source, relation in _all_relations(result):
        if not (
            relation.get("canonicality") == "canonical"
            and relation.get("review_status") == "accepted"
        ):
            continue
        source_id = str(source.get("document_id", ""))
        target_id = str(relation.get("target_document_id", ""))
        outgoing[source_id] = outgoing.get(source_id, 0) + 1
        if target_id in incoming:
            incoming[target_id] += 1
    result.orphans = [
        {
            "document_id": str(node.get("document_id", "")),
            "path": str(node.get("path", "")),
            "reason": "no incoming or outgoing reviewed DLG relations",
        }
        for node in result.nodes
        if incoming.get(str(node.get("document_id", "")), 0) == 0
        and outgoing.get(str(node.get("document_id", "")), 0) == 0
    ]
    result.orphans.sort(key=lambda item: item["document_id"])


def _collect_adr_number_collisions(result: ValidationResult, *, check_git: bool) -> None:
    paths: list[str]
    if check_git:
        stdout = _git_stdout(result.repository_root, "ls-files", "--", "docs/architecture/adr")
        if stdout is None:
            result.add(
                "error",
                "adr_inventory_git_failed",
                "Cannot list tracked ADR paths for collision detection.",
                path="docs/architecture/adr",
            )
            return
        paths = sorted(
            line
            for line in stdout.splitlines()
            if Path(line).parent.as_posix() == "docs/architecture/adr"
            and ADR_FILENAME_RE.match(Path(line).name)
        )
    else:
        paths = sorted(
            _root_relative_path(result.repository_root, path)
            for path in (result.repository_root / "docs/architecture/adr").glob("[0-9][0-9][0-9]-*.md")
        )
    grouped: dict[str, list[str]] = {}
    for path in paths:
        match = ADR_FILENAME_RE.match(Path(path).name)
        if match:
            grouped.setdefault(match.group("number"), []).append(path)
    result.adr_number_collisions = [
        {
            "adr_number": number,
            "paths": sorted(collision_paths),
            "reason": "multiple tracked ADR paths share the numeric prefix",
        }
        for number, collision_paths in sorted(grouped.items())
        if len(collision_paths) > 1
    ]


def _validate_git_revision_integrity(
    result: ValidationResult,
    *,
    check_git: bool,
) -> None:
    if not check_git:
        return
    if not _git_commit_exists(result.repository_root, result.repository_revision):
        result.add(
            "error",
            "repository_revision_unknown",
            "Requested repository revision does not resolve to a Git commit.",
            path=result.repository_revision,
        )
        return
    for node in result.nodes:
        document_id = str(node.get("document_id", ""))
        freshness = node.get("freshness")
        verified_commit = freshness.get("verified_commit") if isinstance(freshness, dict) else None
        if not isinstance(verified_commit, str) or not SHA_RE.fullmatch(verified_commit):
            result.add(
                "error",
                "verified_commit_invalid",
                "freshness.verified_commit must be a full lowercase 40-character SHA.",
                document_id=document_id,
            )
            continue
        if not _git_commit_exists(result.repository_root, verified_commit):
            result.add(
                "error",
                "verified_commit_unknown",
                "freshness.verified_commit does not resolve to a Git commit.",
                document_id=document_id,
            )
            continue
        if not _git_is_ancestor(
            result.repository_root, verified_commit, result.repository_revision
        ):
            result.add(
                "error",
                "verified_commit_not_ancestor",
                "freshness.verified_commit must be an ancestor of repository_revision.",
                document_id=document_id,
            )


def _changed_commits_for_anchor(
    repository_root: Path,
    verified_commit: str,
    repository_revision: str,
    anchor_path: str,
) -> list[str] | None:
    pathspec = f":(glob){anchor_path}" if any(char in anchor_path for char in "*?[") else anchor_path
    completed = _run_git(
        repository_root,
        "log",
        "--format=%H",
        f"{verified_commit}..{repository_revision}",
        "--",
        pathspec,
    )
    if completed.returncode != 0:
        return None
    return sorted({line.strip() for line in completed.stdout.splitlines() if line.strip()})


def _add_stale_document(
    stale_by_id: dict[str, dict[str, Any]],
    node: dict[str, Any],
    reason: str,
) -> None:
    document_id = str(node.get("document_id", ""))
    entry = stale_by_id.setdefault(
        document_id,
        {
            "document_id": document_id,
            "path": str(node.get("path", "")),
            "freshness_state": str(node.get("freshness", {}).get("state", "unknown")),
            "reasons": [],
        },
    )
    entry["reasons"].append(reason)


def _collect_freshness_findings(
    result: ValidationResult,
    anchor_matches: dict[tuple[str, str], list[Path]],
    *,
    check_git: bool,
) -> None:
    stale_by_id: dict[str, dict[str, Any]] = {}
    generated_time = _parse_datetime(result.generated_at)
    for node in result.nodes:
        document_id = str(node.get("document_id", ""))
        freshness = node.get("freshness")
        if not isinstance(freshness, dict):
            continue
        state = freshness.get("state")
        if state == "stale":
            _add_stale_document(stale_by_id, node, "canonical node declares freshness.state=stale")
        verified_commit = freshness.get("verified_commit")
        window_days = freshness.get("window_days")
        if isinstance(window_days, int):
            try:
                verified_at = _parse_datetime(str(freshness.get("verified_at", "")))
            except ValueError:
                result.add(
                    "error",
                    "freshness_verified_at_invalid",
                    "Cannot evaluate structured freshness window without RFC3339 verified_at.",
                    document_id=document_id,
                )
            else:
                if generated_time > verified_at + timedelta(days=window_days):
                    _add_stale_document(
                        stale_by_id,
                        node,
                        "structured freshness.window_days has expired at generated_at",
                    )
        elif state != "not_applicable":
            prose = " ".join(
                [str(freshness.get("reason", ""))]
                + [str(trigger) for trigger in freshness.get("triggers", [])]
            )
            if TEMPORAL_PROSE_RE.search(prose):
                result.coverage_gaps.append(
                    {
                        "document_id": document_id,
                        "path": str(node.get("path", "")),
                        "field": "freshness.triggers/reason",
                        "reason": "freshness duration appears only in free-form prose and is not machine-enforceable",
                    }
                )

        if not check_git or not isinstance(verified_commit, str) or not SHA_RE.fullmatch(verified_commit):
            continue
        for anchor in node.get("source_anchors", []):
            if not isinstance(anchor, dict) or anchor.get("invalidates_freshness") is not True:
                continue
            anchor_path = str(anchor.get("path", ""))
            if not anchor_matches.get((document_id, anchor_path)):
                continue
            changed_commits = _changed_commits_for_anchor(
                result.repository_root,
                verified_commit,
                result.repository_revision,
                anchor_path,
            )
            if changed_commits is None:
                result.add(
                    "error",
                    "freshness_anchor_history_unavailable",
                    "Cannot inspect Git history for freshness-invalidating source anchor.",
                    document_id=document_id,
                    path=anchor_path,
                )
                continue
            if not changed_commits:
                continue
            result.changed_anchors.append(
                {
                    "document_id": document_id,
                    "path": str(node.get("path", "")),
                    "anchor_path": anchor_path,
                    "changed_commits": changed_commits,
                }
            )
            _add_stale_document(
                stale_by_id,
                node,
                f"freshness-invalidating source anchor changed: {anchor_path}",
            )
    for entry in stale_by_id.values():
        entry["reasons"] = sorted(set(entry["reasons"]))
    result.stale_documents = sorted(
        stale_by_id.values(), key=lambda item: item["document_id"]
    )
    result.changed_anchors.sort(
        key=lambda item: (item["document_id"], item["anchor_path"])
    )
    result.coverage_gaps.sort(key=lambda item: (item["document_id"], item["field"]))


def compute_graph_revision(
    schema: dict[str, Any], schema_bytes: bytes, nodes: Sequence[dict[str, Any]]
) -> str:
    """Compute the semantic graph revision independent of generation metadata."""
    schema_version = schema.get("$defs", {}).get("schemaVersion", {}).get("const")
    if not isinstance(schema_version, str):
        schema_version = SCHEMA_VERSION
    payload = {
        "schema_version": schema_version,
        "schema_sha256": _sha256(schema_bytes),
        "nodes": sorted(nodes, key=lambda node: str(node.get("document_id", ""))),
    }
    return _sha256(_canonical_json_bytes(payload))


def validate_repository(
    repository_root: Path | str,
    repository_revision: str,
    generated_at: str,
    *,
    check_git: bool = True,
) -> ValidationResult:
    """Perform deterministic DLG semantic validation without writing files."""
    _validate_generation_parameters(repository_revision, generated_at)
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise ToolConfigurationError(f"Repository root does not exist: {root}")
    schema, schema_bytes = _load_schema(root, check_git)
    graph_revision = compute_graph_revision(schema, schema_bytes, [])
    result = ValidationResult(
        repository_root=root,
        repository_revision=repository_revision,
        generated_at=generated_at,
        schema=schema,
        schema_bytes=schema_bytes,
        nodes=[],
        node_files=[],
        graph_revision=graph_revision,
    )
    schema_path = root / SCHEMA_RELATIVE_PATH
    _check_utf8_and_lfs(result, schema_path, label="schema")
    _check_attributes(result, SCHEMA_RELATIVE_PATH.as_posix(), graph_record=False, check_git=check_git)
    validator = jsonschema.Draft202012Validator(schema)
    _load_canonical_nodes(result, validator, check_git=check_git)
    result.graph_revision = compute_graph_revision(schema, schema_bytes, result.nodes)
    _detect_document_id_collisions(result)
    _detect_active_path_collisions(result)
    anchor_matches = _validate_source_integrity(result)
    _validate_relation_targets_and_self_edges(result)
    _validate_duplicate_relations(result)
    _validate_acyclic_predicates(result)
    _validate_compatibility_pointers(result)
    _validate_accepted_contract_governance(result)
    _validate_proof_invariants(result)
    _validate_retrieval_policy(result)
    _validate_git_revision_integrity(result, check_git=check_git)
    _collect_freshness_findings(result, anchor_matches, check_git=check_git)
    _collect_supersession(result)
    _collect_authority_conflicts(result)
    _collect_adr_number_collisions(result, check_git=check_git)
    _collect_orphans(result)
    for filename in OUTPUT_FILENAMES:
        relative = (DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix()
        _check_attributes(result, relative, graph_record=True, check_git=check_git)
    return result


def build_generated_artifacts(result: ValidationResult) -> dict[str, dict[str, Any]]:
    """Build six deterministic non-authoritative projection payloads in memory."""
    common = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": result.generated_at,
        "repository_revision": result.repository_revision,
        "graph_revision": result.graph_revision,
        "notice": NOTICE,
    }
    return {
        "document-graph.json": {
            **common,
            "record_type": "document_graph",
            "graph_id": GRAPH_ID,
            "illustrative": False,
            "nodes": sorted(result.nodes, key=lambda node: str(node.get("document_id", ""))),
            "supersession_set": result.supersession_set,
        },
        "stale-documents.json": {
            **common,
            "record_type": "stale_documents_report",
            "stale_documents": result.stale_documents,
            "changed_anchors": result.changed_anchors,
            "coverage_gaps": result.coverage_gaps,
        },
        "supersession-map.json": {
            **common,
            "record_type": "supersession_map",
            "supersession_set": result.supersession_set,
        },
        "authority-conflicts.json": {
            **common,
            "record_type": "authority_conflicts_report",
            "conflicts": result.authority_conflicts,
        },
        "collisions.json": {
            **common,
            "record_type": "collision_report",
            "document_id_collisions": result.document_id_collisions,
            "active_path_collisions": result.active_path_collisions,
            "adr_number_collisions": result.adr_number_collisions,
        },
        "orphans.json": {
            **common,
            "record_type": "orphan_report",
            "orphans": result.orphans,
        },
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a readable JSON projection through same-directory atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(temporary_fd, "wb") as handle:
            handle.write(_pretty_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            temporary_path.unlink(missing_ok=True)
        finally:
            raise


def write_generated_artifacts(
    result: ValidationResult, output_root: Path | str
) -> dict[str, Path]:
    """Atomically write all derived projections without touching canonical records."""
    root = Path(output_root)
    artifacts = build_generated_artifacts(result)
    written: dict[str, Path] = {}
    for filename in OUTPUT_FILENAMES:
        payload = artifacts[filename]
        path = root / filename
        atomic_write_json(path, payload)
        written[filename] = path
    return written


def _validate_common_generated_envelope(
    result: ValidationResult,
    payload: dict[str, Any],
    filename: str,
) -> None:
    relative = (DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix()
    required = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": result.generated_at,
        "repository_revision": result.repository_revision,
        "graph_revision": result.graph_revision,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            result.add(
                "error",
                "generated_envelope_mismatch",
                f"Generated {key} does not match the requested deterministic value.",
                path=relative,
            )
    notice = payload.get("notice")
    if not isinstance(notice, str) or not all(
        phrase in notice.lower()
        for phrase in ("generated", "derived", "reconstructable", "non-authoritative", "hand edit")
    ):
        result.add(
            "error",
            "generated_notice_invalid",
            "Generated projection notice must declare generated, derived, reconstructable, non-authoritative, and do-not-hand-edit posture.",
            path=relative,
        )


def validate_generated_artifacts(
    result: ValidationResult,
    output_root: Path | str,
    *,
    check_git: bool = True,
) -> bool:
    """Validate committed/generated output integrity and report-specific shapes."""
    root = Path(output_root)
    before_errors = sum(issue.severity == "error" for issue in result.issues)
    payloads: dict[str, dict[str, Any]] = {}
    for filename in OUTPUT_FILENAMES:
        path = root / filename
        relative = (DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix()
        if not path.is_file():
            result.add(
                "error",
                "generated_output_missing",
                "Required generated projection is missing.",
                path=relative,
            )
            continue
        raw = _check_utf8_and_lfs(result, path, label="generated_output")
        if raw is None:
            continue
        payload = _parse_json_object(
            result, raw, label="generated_output", path=relative
        )
        if payload is None:
            continue
        _record_prohibited_metadata(result, payload, path=relative)
        _validate_common_generated_envelope(result, payload, filename)
        payloads[filename] = payload
        _check_attributes(result, relative, graph_record=True, check_git=check_git)

    graph = payloads.get("document-graph.json")
    if graph is not None:
        graph_errors = sorted(
            jsonschema.Draft202012Validator(result.schema).iter_errors(graph),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        for error in graph_errors:
            result.add(
                "error",
                "document_graph_schema_invalid",
                error.message,
                path=(DEFAULT_OUTPUT_RELATIVE_DIR / "document-graph.json").as_posix(),
            )
    expected_arrays = {
        "stale-documents.json": ("stale_documents", "changed_anchors", "coverage_gaps"),
        "supersession-map.json": ("supersession_set",),
        "authority-conflicts.json": ("conflicts",),
        "collisions.json": (
            "document_id_collisions",
            "active_path_collisions",
            "adr_number_collisions",
        ),
        "orphans.json": ("orphans",),
    }
    for filename, fields in expected_arrays.items():
        payload = payloads.get(filename)
        if payload is None:
            continue
        if payload.get("record_type") != REPORT_RECORD_TYPES[filename]:
            result.add(
                "error",
                "generated_record_type_invalid",
                "Generated report has an unexpected record_type.",
                path=(DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix(),
            )
        for field_name in fields:
            if not isinstance(payload.get(field_name), list):
                result.add(
                    "error",
                    "generated_report_shape_invalid",
                    f"Generated report field {field_name!r} must be an array.",
                    path=(DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix(),
                )
    after_errors = sum(issue.severity == "error" for issue in result.issues)
    return after_errors == before_errors


def generate(
    repository_root: Path | str,
    repository_revision: str,
    generated_at: str,
    *,
    output_root: Path | str | None = None,
    check_git: bool = True,
) -> ValidationResult:
    """Validate then atomically generate the six Phase 3A projections."""
    result = validate_repository(
        repository_root,
        repository_revision,
        generated_at,
        check_git=check_git,
    )
    if result.has_errors:
        return result
    target_root = (
        Path(output_root)
        if output_root is not None
        else result.repository_root / DEFAULT_OUTPUT_RELATIVE_DIR
    )
    write_generated_artifacts(result, target_root)
    validate_generated_artifacts(result, target_root, check_git=check_git)
    return result


def check_generated(
    repository_root: Path | str,
    repository_revision: str,
    generated_at: str,
    *,
    output_root: Path | str | None = None,
    check_git: bool = True,
) -> ValidationResult:
    """Regenerate outputs into a temporary directory and byte-compare each file."""
    result = validate_repository(
        repository_root,
        repository_revision,
        generated_at,
        check_git=check_git,
    )
    if result.has_errors:
        return result
    target_root = (
        Path(output_root)
        if output_root is not None
        else result.repository_root / DEFAULT_OUTPUT_RELATIVE_DIR
    )
    if not validate_generated_artifacts(result, target_root, check_git=check_git):
        return result
    with tempfile.TemporaryDirectory(prefix="codexify-dlg-phase3a-repro-") as temporary_dir:
        temporary_root = Path(temporary_dir)
        write_generated_artifacts(result, temporary_root)
        for filename in OUTPUT_FILENAMES:
            expected_path = temporary_root / filename
            actual_path = target_root / filename
            if expected_path.read_bytes() != actual_path.read_bytes():
                result.add(
                    "error",
                    "generated_output_drift",
                    f"Generated output differs from deterministic regeneration: {filename}",
                    path=(DEFAULT_OUTPUT_RELATIVE_DIR / filename).as_posix(),
                )
    return result


def _current_repository_revision(repository_root: Path) -> str:
    stdout = _git_stdout(repository_root, "rev-parse", "HEAD")
    if stdout is None or not SHA_RE.fullmatch(stdout.strip()):
        raise ToolConfigurationError("Cannot resolve current repository HEAD as a full Git SHA.")
    return stdout.strip()


def _print_summary(result: ValidationResult) -> None:
    print(json.dumps(result.summary(), ensure_ascii=False, sort_keys=True, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and generate deterministic DLG Phase 3A projections."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "generate", "check-generated"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repository-root",
            default=str(Path(__file__).resolve().parents[2]),
            help="Repository root containing canonical DLG inputs.",
        )
        if command == "validate":
            subparser.add_argument(
                "--repository-revision",
                help="Optional full SHA; defaults explicitly to repository HEAD.",
            )
            subparser.add_argument(
                "--generated-at",
                help="Optional RFC3339 value; defaults deterministically to the chosen commit timestamp.",
            )
        else:
            subparser.add_argument("--repository-revision", required=True)
            subparser.add_argument("--generated-at", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    repository_root = Path(args.repository_root).resolve()
    try:
        repository_revision = (
            args.repository_revision
            if args.repository_revision
            else _current_repository_revision(repository_root)
        )
        generated_at = (
            args.generated_at
            if args.generated_at
            else _git_revision_timestamp(repository_root, repository_revision)
        )
        if args.command == "validate":
            result = validate_repository(
                repository_root,
                repository_revision,
                generated_at,
            )
        elif args.command == "generate":
            result = generate(repository_root, repository_revision, generated_at)
        else:
            result = check_generated(repository_root, repository_revision, generated_at)
    except ToolConfigurationError as exc:
        print(f"DLG Phase 3A tooling error: {exc}", file=sys.stderr)
        return 1
    _print_summary(result)
    return 1 if result.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
