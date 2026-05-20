"""Pure contracts for the Codex Knowledge Compiler dry-run harness.

This module is intentionally dependency-light. It models bounded, deterministic
contracts only and does not import runtime routes, workers, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


def _clean_required_text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty.")
    return text


def _clean_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_enum(
    value: object,
    enum_type: type[Enum],
    field_name: str,
) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).strip())
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be one of {[member.value for member in enum_type]}."
        ) from exc


def _normalize_string_mapping(
    value: Mapping[str, object] | None,
) -> dict[str, str]:
    if not value:
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized[_clean_required_text(key, "mapping key")] = str(item)
    return normalized


def _normalize_hash_mapping(
    value: Mapping[str, object] | None,
) -> dict[str, str]:
    if not value:
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        source_id = _clean_required_text(key, "previous_hashes key")
        normalized[source_id] = _clean_required_text(
            item, f"previous_hashes[{source_id}]"
        )
    return normalized


def _normalize_string_tuple(
    values: Sequence[object] | None,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(
        _clean_required_text(value, field_name)
        for value in values
    )


class KnowledgeScopeKind(str, Enum):
    PROJECT = "project"
    WORKSPACE = "workspace"
    SYSTEM = "system"
    DOMAIN = "domain"


class KnowledgeSourceType(str, Enum):
    THREAD = "thread"
    MESSAGE = "message"
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    OBSIDIAN_NOTE = "obsidian_note"
    REPO_FILE = "repo_file"
    AUDIT = "audit"
    EXTERNAL = "external"


class KnowledgeArtifactKind(str, Enum):
    CODEX_ENTRY_DRAFT = "codex_entry_draft"
    SOURCE_SUMMARY = "source_summary"
    CONCEPT_CARD = "concept_card"
    DECISION_RECORD = "decision_record"
    RETRIEVAL_CARD = "retrieval_card"
    RELATIONSHIP_EDGE = "relationship_edge"
    MAINTENANCE_FINDING = "maintenance_finding"
    CONTRADICTION_FINDING = "contradiction_finding"


class KnowledgeReviewState(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class KnowledgeChangeState(str, Enum):
    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    EXCLUDED = "excluded"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class KnowledgeSourceProvenance:
    thread_id: str | None = None
    message_id: str | None = None
    project_id: str | None = None
    artifact_id: str | None = None
    document_id: str | None = None
    file_path: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "thread_id", _clean_optional_text(self.thread_id))
        object.__setattr__(self, "message_id", _clean_optional_text(self.message_id))
        object.__setattr__(self, "project_id", _clean_optional_text(self.project_id))
        object.__setattr__(self, "artifact_id", _clean_optional_text(self.artifact_id))
        object.__setattr__(self, "document_id", _clean_optional_text(self.document_id))
        object.__setattr__(self, "file_path", _clean_optional_text(self.file_path))
        object.__setattr__(self, "url", _clean_optional_text(self.url))


@dataclass(frozen=True, slots=True)
class KnowledgeSourceItem:
    source_id: str
    scope_kind: KnowledgeScopeKind
    scope_id: str
    source_type: KnowledgeSourceType
    title: str | None
    content: str
    content_hash: str
    created_at: str | None
    updated_at: str | None
    provenance: KnowledgeSourceProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _clean_required_text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "scope_kind",
            _normalize_enum(self.scope_kind, KnowledgeScopeKind, "scope_kind"),
        )
        object.__setattr__(self, "scope_id", _clean_required_text(self.scope_id, "scope_id"))
        object.__setattr__(
            self,
            "source_type",
            _normalize_enum(self.source_type, KnowledgeSourceType, "source_type"),
        )
        object.__setattr__(self, "title", _clean_optional_text(self.title))
        object.__setattr__(self, "content", str(self.content))
        object.__setattr__(
            self, "content_hash", _clean_required_text(self.content_hash, "content_hash")
        )
        object.__setattr__(self, "created_at", _clean_optional_text(self.created_at))
        object.__setattr__(self, "updated_at", _clean_optional_text(self.updated_at))
        if not isinstance(self.provenance, KnowledgeSourceProvenance):
            raise ValueError("provenance must be a KnowledgeSourceProvenance.")


@dataclass(frozen=True, slots=True)
class CompiledKnowledgeArtifact:
    artifact_id: str
    artifact_kind: KnowledgeArtifactKind
    scope_kind: KnowledgeScopeKind
    scope_id: str
    title: str
    body: str
    source_ids: tuple[str, ...]
    review_state: KnowledgeReviewState
    retrieval_visible: bool
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _clean_required_text(self.artifact_id, "artifact_id"))
        object.__setattr__(
            self,
            "artifact_kind",
            _normalize_enum(
                self.artifact_kind, KnowledgeArtifactKind, "artifact_kind"
            ),
        )
        object.__setattr__(
            self,
            "scope_kind",
            _normalize_enum(self.scope_kind, KnowledgeScopeKind, "scope_kind"),
        )
        object.__setattr__(self, "scope_id", _clean_required_text(self.scope_id, "scope_id"))
        object.__setattr__(self, "title", _clean_required_text(self.title, "title"))
        object.__setattr__(self, "body", str(self.body))
        normalized_source_ids = _normalize_string_tuple(
            self.source_ids,
            field_name="source_ids",
        )
        if not normalized_source_ids:
            raise ValueError("Every artifact must have at least one source_id.")
        object.__setattr__(self, "source_ids", normalized_source_ids)
        object.__setattr__(
            self,
            "review_state",
            _normalize_enum(self.review_state, KnowledgeReviewState, "review_state"),
        )
        object.__setattr__(self, "retrieval_visible", bool(self.retrieval_visible))
        object.__setattr__(self, "metadata", _normalize_string_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class KnowledgeSourceChange:
    source_id: str
    change_state: KnowledgeChangeState
    previous_hash: str | None
    current_hash: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _clean_required_text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "change_state",
            _normalize_enum(self.change_state, KnowledgeChangeState, "change_state"),
        )
        object.__setattr__(self, "previous_hash", _clean_optional_text(self.previous_hash))
        object.__setattr__(
            self, "current_hash", _clean_required_text(self.current_hash, "current_hash")
        )
        object.__setattr__(self, "reason", _clean_required_text(self.reason, "reason"))


@dataclass(frozen=True, slots=True)
class KnowledgeCompilerBudget:
    max_sources: int
    max_artifacts: int
    max_model_calls: int
    max_wall_time_seconds: int
    max_graph_edges: int
    max_write_operations: int

    def __post_init__(self) -> None:
        for field_name in (
            "max_sources",
            "max_artifacts",
            "max_model_calls",
            "max_wall_time_seconds",
            "max_graph_edges",
            "max_write_operations",
        ):
            value = int(getattr(self, field_name))
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative.")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True)
class KnowledgeCompilerDryRunRequest:
    scope_kind: KnowledgeScopeKind
    scope_id: str
    trigger_kind: str
    sources: tuple[KnowledgeSourceItem, ...]
    previous_hashes: dict[str, str]
    budget: KnowledgeCompilerBudget

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scope_kind",
            _normalize_enum(self.scope_kind, KnowledgeScopeKind, "scope_kind"),
        )
        object.__setattr__(self, "scope_id", _clean_required_text(self.scope_id, "scope_id"))
        object.__setattr__(
            self, "trigger_kind", _clean_required_text(self.trigger_kind, "trigger_kind")
        )
        if not isinstance(self.budget, KnowledgeCompilerBudget):
            raise ValueError("budget must be a KnowledgeCompilerBudget.")
        normalized_sources = tuple(self.sources or ())
        for source in normalized_sources:
            if not isinstance(source, KnowledgeSourceItem):
                raise ValueError("sources must contain KnowledgeSourceItem values.")
        object.__setattr__(self, "sources", normalized_sources)
        object.__setattr__(
            self, "previous_hashes", _normalize_hash_mapping(self.previous_hashes)
        )
        if self.budget.max_model_calls > 0:
            raise ValueError("Dry-run requests cannot request model calls.")
        if self.budget.max_write_operations > 0:
            raise ValueError("Dry-run requests cannot request write operations.")


@dataclass(frozen=True, slots=True)
class KnowledgeCompilerProofReport:
    run_id: str
    scope_kind: KnowledgeScopeKind
    scope_id: str
    trigger_kind: str
    source_candidates_discovered: int
    changed_sources_detected: int
    sources_skipped: tuple[str, ...]
    source_changes: tuple[KnowledgeSourceChange, ...]
    draft_artifacts_generated: int
    artifacts_approved: int
    artifacts_published: int
    retrieval_cards_generated: int
    graph_edges_proposed: int
    budget_used: dict[str, int]
    errors: tuple[str, ...]
    policy_exclusions: tuple[str, ...]
    review_status: str
    artifacts: tuple[CompiledKnowledgeArtifact, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _clean_required_text(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "scope_kind",
            _normalize_enum(self.scope_kind, KnowledgeScopeKind, "scope_kind"),
        )
        object.__setattr__(self, "scope_id", _clean_required_text(self.scope_id, "scope_id"))
        object.__setattr__(
            self, "trigger_kind", _clean_required_text(self.trigger_kind, "trigger_kind")
        )
        for field_name in (
            "source_candidates_discovered",
            "changed_sources_detected",
            "draft_artifacts_generated",
            "artifacts_approved",
            "artifacts_published",
            "retrieval_cards_generated",
            "graph_edges_proposed",
        ):
            value = int(getattr(self, field_name))
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative.")
            object.__setattr__(self, field_name, value)
        object.__setattr__(
            self,
            "sources_skipped",
            _normalize_string_tuple(self.sources_skipped, field_name="sources_skipped"),
        )
        source_changes = tuple(self.source_changes or ())
        for item in source_changes:
            if not isinstance(item, KnowledgeSourceChange):
                raise ValueError("source_changes must contain KnowledgeSourceChange values.")
        object.__setattr__(self, "source_changes", source_changes)
        normalized_budget_used = {
            _clean_required_text(key, "budget_used key"): int(value)
            for key, value in (self.budget_used or {}).items()
        }
        object.__setattr__(self, "budget_used", normalized_budget_used)
        object.__setattr__(
            self, "errors", _normalize_string_tuple(self.errors, field_name="errors")
        )
        object.__setattr__(
            self,
            "policy_exclusions",
            _normalize_string_tuple(
                self.policy_exclusions, field_name="policy_exclusions"
            ),
        )
        object.__setattr__(
            self, "review_status", _clean_required_text(self.review_status, "review_status")
        )
        artifacts = tuple(self.artifacts or ())
        for artifact in artifacts:
            if not isinstance(artifact, CompiledKnowledgeArtifact):
                raise ValueError(
                    "artifacts must contain CompiledKnowledgeArtifact values."
                )
        object.__setattr__(self, "artifacts", artifacts)


__all__ = [
    "CompiledKnowledgeArtifact",
    "KnowledgeArtifactKind",
    "KnowledgeChangeState",
    "KnowledgeCompilerBudget",
    "KnowledgeCompilerDryRunRequest",
    "KnowledgeCompilerProofReport",
    "KnowledgeReviewState",
    "KnowledgeScopeKind",
    "KnowledgeSourceChange",
    "KnowledgeSourceItem",
    "KnowledgeSourceProvenance",
    "KnowledgeSourceType",
]
