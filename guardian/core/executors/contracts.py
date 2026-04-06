"""Canonical executor contract types for Codexify-facing executor surfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from guardian.protocol_tokens import (
    DELEGATION_SUMMARY_OUTCOME_TYPE,
    DelegationJobStatus,
    ExecutorEscalationKind,
    ExecutorEventType,
    ExecutorId,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(raw: Any) -> str:
    return str(raw or "").strip()


def _normalize_optional_text(raw: Any) -> str | None:
    text = _normalize_text(raw)
    return text or None


def _normalize_identifier(raw: Any) -> int | str | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    text = _normalize_text(raw)
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return text


def _normalize_executor_id(raw: Any) -> str:
    if isinstance(raw, ExecutorId):
        return raw.value
    if isinstance(raw, Enum):
        return (
            _normalize_text(raw.value)
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
    return _normalize_text(raw).lower().replace("-", "_").replace(" ", "_")


def _normalize_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        items = raw
    elif isinstance(raw, str):
        items = raw.split(",") if "," in raw else [raw]
    else:
        items = [raw]
    result: list[str] = []
    for item in items:
        text = _normalize_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _normalize_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _coerce_context_bundle(
    raw: CodexifyExecutorContextBundle | dict[str, Any] | None,
) -> CodexifyExecutorContextBundle:
    if isinstance(raw, CodexifyExecutorContextBundle):
        return raw
    if isinstance(raw, dict):
        return CodexifyExecutorContextBundle.from_dict(raw)
    return CodexifyExecutorContextBundle()


def _coerce_task_summary(
    raw: CanonicalTaskSummary | dict[str, Any] | None,
) -> CanonicalTaskSummary | None:
    if raw is None:
        return None
    if isinstance(raw, CanonicalTaskSummary):
        return raw
    if isinstance(raw, dict):
        return CanonicalTaskSummary.from_dict(raw)
    return None


def _coerce_failure(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return dict(raw)
    return raw


@dataclass(slots=True)
class CodexifyExecutorContextBundle:
    workspace_path: str | None = None
    thread_context: dict[str, Any] = field(default_factory=dict)
    message_context: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.workspace_path = _normalize_optional_text(self.workspace_path)
        self.thread_context = _normalize_mapping(self.thread_context)
        self.message_context = _normalize_mapping(self.message_context)
        self.routing = _normalize_mapping(self.routing)
        self.metadata = _normalize_mapping(self.metadata)
        self.raw = _normalize_mapping(self.raw)
        if not self.raw and self.thread_context:
            self.raw = dict(self.thread_context)

    @classmethod
    def from_dict(
        cls, payload: dict[str, Any]
    ) -> CodexifyExecutorContextBundle:
        payload = payload or {}
        return cls(
            workspace_path=payload.get("workspace_path")
            or payload.get("workspacePath"),
            thread_context=_normalize_mapping(
                payload.get("thread_context") or payload.get("threadContext")
            ),
            message_context=_normalize_mapping(
                payload.get("message_context") or payload.get("messageContext")
            ),
            routing=_normalize_mapping(payload.get("routing")),
            artifacts=list(payload.get("artifacts") or []),
            metadata=_normalize_mapping(payload.get("metadata")),
            raw=_normalize_mapping(payload.get("raw") or payload),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["workspacePath"] = self.workspace_path
        payload["threadContext"] = dict(self.thread_context)
        payload["messageContext"] = dict(self.message_context)
        return payload


@dataclass(slots=True)
class CodexifyExecutorRequest:
    request_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    title: str = ""
    canonical_task_prompt: str = ""
    context_bundle: CodexifyExecutorContextBundle | dict[str, Any] = field(
        default_factory=CodexifyExecutorContextBundle
    )
    permissions: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    delegation_id: str = ""
    task_id: str = ""
    repo_path: str = ""
    executor: str = ""
    task_prompt: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.request_id = (
            _normalize_optional_text(self.request_id)
            or _normalize_optional_text(self.delegation_id)
            or ""
        )
        self.delegation_id = (
            _normalize_optional_text(self.delegation_id) or self.request_id
        )
        self.task_id = _normalize_optional_text(self.task_id)
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(
            self.executor_id or self.executor
        )
        self.executor = self.executor_id
        self.title = (
            _normalize_optional_text(self.title)
            or _normalize_optional_text(self.canonical_task_prompt)
            or _normalize_optional_text(self.task_prompt)
            or self.title
        )
        self.canonical_task_prompt = (
            _normalize_optional_text(self.canonical_task_prompt)
            or _normalize_optional_text(self.task_prompt)
            or self.title
        )
        self.task_prompt = self.canonical_task_prompt
        self.context_bundle = _coerce_context_bundle(self.context_bundle)
        self.permissions = _normalize_mapping(self.permissions)
        self.tags = _normalize_text_list(self.tags)
        self.context = _normalize_mapping(self.context)
        if not self.context and self.context_bundle.raw:
            self.context = dict(self.context_bundle.raw)
        elif self.context and not self.context_bundle.raw:
            self.context_bundle.raw = dict(self.context)
        self.metadata = _normalize_mapping(self.metadata)
        if self.task_id:
            self.metadata.setdefault("task_id", self.task_id)
        if self.delegation_id:
            self.metadata.setdefault("delegation_id", self.delegation_id)
        if self.request_id:
            self.metadata.setdefault("request_id", self.request_id)
        if self.thread_id is not None:
            self.metadata.setdefault("thread_id", self.thread_id)
        if self.source_message_id is not None:
            self.metadata.setdefault(
                "source_message_id", self.source_message_id
            )
        if self.project_id is not None:
            self.metadata.setdefault("project_id", self.project_id)
        if self.executor_id:
            self.metadata.setdefault("executor_id", self.executor_id)
        if self.title:
            self.metadata.setdefault("title", self.title)
        if self.tags:
            self.metadata.setdefault("tags", list(self.tags))
        if self.repo_path:
            self.metadata.setdefault("repo_path", self.repo_path)
        self.metadata.setdefault(
            "canonical_task_prompt", self.canonical_task_prompt
        )

    @property
    def canonical_prompt(self) -> str:
        return self.canonical_task_prompt

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requestId"] = self.request_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["canonicalTaskPrompt"] = self.canonical_task_prompt
        payload["contextBundle"] = self.context_bundle.to_dict()
        payload["taskPrompt"] = self.task_prompt
        payload["repoPath"] = self.repo_path
        payload["delegationId"] = self.delegation_id
        payload["taskId"] = self.task_id
        return payload


@dataclass(slots=True)
class ExecutorProgressEvent:
    stream: str = "stdout"
    text: str = ""
    sequence: int | None = None
    event_type: str = ExecutorEventType.PROGRESS.value
    request_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.stream = _normalize_text(self.stream) or "stdout"
        self.text = _normalize_text(self.text)
        self.sequence = (
            self.sequence if self.sequence is None else int(self.sequence)
        )
        self.event_type = (
            _normalize_text(self.event_type) or ExecutorEventType.PROGRESS.value
        )
        self.request_id = _normalize_optional_text(self.request_id) or ""
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.title = _normalize_optional_text(self.title) or ""
        self.tags = _normalize_text_list(self.tags)
        self.metadata = _normalize_mapping(self.metadata)
        self.created_at = (
            _normalize_optional_text(self.created_at) or _utc_now_iso()
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExecutorProgressEvent:
        payload = payload or {}
        return cls(
            stream=payload.get("stream"),
            text=payload.get("text"),
            sequence=payload.get("sequence"),
            event_type=payload.get("event_type") or payload.get("eventType"),
            request_id=payload.get("request_id") or payload.get("requestId"),
            thread_id=payload.get("thread_id") or payload.get("threadId"),
            source_message_id=payload.get("source_message_id")
            or payload.get("sourceMessageId"),
            project_id=payload.get("project_id") or payload.get("projectId"),
            executor_id=payload.get("executor_id") or payload.get("executorId"),
            title=payload.get("title"),
            tags=payload.get("tags") or [],
            metadata=_normalize_mapping(payload.get("metadata")),
            created_at=payload.get("created_at") or payload.get("createdAt"),
        )

    @property
    def message(self) -> str:
        return self.text

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requestId"] = self.request_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["createdAt"] = self.created_at
        return payload


@dataclass(slots=True)
class CanonicalEscalation:
    kind: str = ExecutorEscalationKind.BLOCKED.value
    severity: str = "soft"
    reason_code: str = ""
    reason: str = ""
    status: str = "open"
    preserved_worktree: bool = False
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if isinstance(self.kind, Enum):
            self.kind = _normalize_text(self.kind.value)
        self.kind = (
            _normalize_text(self.kind)
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        self.severity = _normalize_text(self.severity) or "soft"
        self.reason_code = _normalize_text(self.reason_code)
        self.reason = _normalize_text(self.reason)
        self.status = _normalize_text(self.status) or "open"
        self.preserved_worktree = bool(self.preserved_worktree)
        self.payload = _normalize_mapping(self.payload)
        self.provenance = _normalize_mapping(self.provenance)
        self.created_at = (
            _normalize_optional_text(self.created_at) or _utc_now_iso()
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CanonicalEscalation:
        payload = payload or {}
        return cls(
            kind=payload.get("kind") or payload.get("escalation_kind"),
            severity=payload.get("severity"),
            reason_code=payload.get("reason_code") or payload.get("reasonCode"),
            reason=payload.get("reason"),
            status=payload.get("status"),
            preserved_worktree=payload.get("preserved_worktree")
            if "preserved_worktree" in payload
            else payload.get("preservedWorktree", False),
            payload=_normalize_mapping(payload.get("payload")),
            provenance=_normalize_mapping(payload.get("provenance")),
            created_at=payload.get("created_at") or payload.get("createdAt"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["createdAt"] = self.created_at
        return payload


@dataclass(slots=True)
class ExecutorEscalationEvent:
    event_type: str = ExecutorEventType.ESCALATION.value
    request_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    escalation: CanonicalEscalation | dict[str, Any] = field(
        default_factory=CanonicalEscalation
    )
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.event_type = (
            _normalize_text(self.event_type)
            or ExecutorEventType.ESCALATION.value
        )
        self.request_id = _normalize_optional_text(self.request_id) or ""
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.title = _normalize_optional_text(self.title) or ""
        self.tags = _normalize_text_list(self.tags)
        self.escalation = (
            self.escalation
            if isinstance(self.escalation, CanonicalEscalation)
            else CanonicalEscalation.from_dict(self.escalation)
            if isinstance(self.escalation, dict)
            else CanonicalEscalation()
        )
        if not self.escalation.provenance:
            self.escalation.provenance = {
                "request_id": self.request_id,
                "thread_id": self.thread_id,
                "source_message_id": self.source_message_id,
                "project_id": self.project_id,
                "executor_id": self.executor_id,
                "title": self.title,
                "tags": list(self.tags),
            }
        else:
            self.escalation.provenance.setdefault("request_id", self.request_id)
            self.escalation.provenance.setdefault("thread_id", self.thread_id)
            self.escalation.provenance.setdefault(
                "source_message_id", self.source_message_id
            )
            self.escalation.provenance.setdefault("project_id", self.project_id)
            self.escalation.provenance.setdefault(
                "executor_id", self.executor_id
            )
            self.escalation.provenance.setdefault("title", self.title)
            self.escalation.provenance.setdefault("tags", list(self.tags))
        self.created_at = (
            _normalize_optional_text(self.created_at) or _utc_now_iso()
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requestId"] = self.request_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["createdAt"] = self.created_at
        return payload

    @property
    def canonical_escalation(self) -> CanonicalEscalation:
        return self.escalation


@dataclass(slots=True)
class CanonicalTaskSummary:
    request_id: str = ""
    delegation_id: str = ""
    task_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    title: str = ""
    status: str = DelegationJobStatus.COMPLETED.value
    outcome_type: str = DELEGATION_SUMMARY_OUTCOME_TYPE
    summary: str | None = None
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    key_changes: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_transcript: str | None = None
    transcript: str | None = None
    failure: dict[str, Any] | Any | None = None
    error_message: str | None = None
    lineage: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.request_id = (
            _normalize_optional_text(self.request_id)
            or _normalize_optional_text(self.delegation_id)
            or ""
        )
        self.delegation_id = (
            _normalize_optional_text(self.delegation_id) or self.request_id
        )
        self.task_id = _normalize_optional_text(self.task_id)
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.title = _normalize_optional_text(self.title) or ""
        self.status = (
            _normalize_optional_text(self.status)
            or DelegationJobStatus.COMPLETED.value
        )
        self.outcome_type = (
            _normalize_optional_text(self.outcome_type)
            or DELEGATION_SUMMARY_OUTCOME_TYPE
        )
        self.summary = _normalize_optional_text(self.summary)
        self.files_changed = _normalize_text_list(self.files_changed)
        self.commands_run = _normalize_text_list(self.commands_run)
        self.key_changes = _normalize_text_list(self.key_changes)
        self.unresolved_questions = _normalize_text_list(
            self.unresolved_questions
        )
        self.tags = _normalize_text_list(self.tags)
        self.result = _normalize_mapping(self.result)
        self.metadata = _normalize_mapping(self.metadata)
        self.raw_transcript = _normalize_optional_text(self.raw_transcript)
        self.transcript = _normalize_optional_text(self.transcript)
        self.failure = _coerce_failure(self.failure)
        self.error_message = _normalize_optional_text(self.error_message)
        self.lineage = _normalize_mapping(self.lineage)
        self.created_at = (
            _normalize_optional_text(self.created_at) or _utc_now_iso()
        )
        self.completed_at = (
            _normalize_optional_text(self.completed_at) or _utc_now_iso()
        )
        if self.summary is None:
            self.summary = (
                _normalize_optional_text(self.result.get("summary"))
                or _normalize_optional_text(self.result.get("final_text"))
                or self.transcript
                or self.raw_transcript
                or self.error_message
            )
        self.lineage.setdefault("request_id", self.request_id)
        self.lineage.setdefault("delegation_id", self.delegation_id)
        self.lineage.setdefault("task_id", self.task_id)
        self.lineage.setdefault("thread_id", self.thread_id)
        self.lineage.setdefault("source_message_id", self.source_message_id)
        self.lineage.setdefault("project_id", self.project_id)
        self.lineage.setdefault("executor_id", self.executor_id)
        self.lineage.setdefault("title", self.title)
        self.lineage.setdefault("status", self.status)
        self.lineage.setdefault("outcome_type", self.outcome_type)
        self.lineage.setdefault("tags", list(self.tags))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CanonicalTaskSummary:
        payload = payload or {}
        return cls(
            request_id=payload.get("request_id") or payload.get("requestId"),
            delegation_id=payload.get("delegation_id")
            or payload.get("delegationId"),
            task_id=payload.get("task_id") or payload.get("taskId"),
            thread_id=payload.get("thread_id") or payload.get("threadId"),
            source_message_id=payload.get("source_message_id")
            or payload.get("sourceMessageId"),
            project_id=payload.get("project_id") or payload.get("projectId"),
            executor_id=payload.get("executor_id") or payload.get("executorId"),
            title=payload.get("title"),
            status=payload.get("status"),
            outcome_type=payload.get("outcome_type")
            or payload.get("outcomeType"),
            summary=payload.get("summary"),
            files_changed=payload.get("files_changed")
            or payload.get("filesChanged")
            or [],
            commands_run=payload.get("commands_run")
            or payload.get("commandsRun")
            or [],
            key_changes=payload.get("key_changes")
            or payload.get("keyChanges")
            or [],
            unresolved_questions=payload.get("unresolved_questions")
            or payload.get("unresolvedQuestions")
            or [],
            tags=payload.get("tags") or [],
            result=_normalize_mapping(payload.get("result")),
            metadata=_normalize_mapping(payload.get("metadata")),
            raw_transcript=payload.get("raw_transcript")
            or payload.get("rawTranscript"),
            transcript=payload.get("transcript"),
            failure=payload.get("failure"),
            error_message=payload.get("error_message")
            or payload.get("errorMessage"),
            lineage=_normalize_mapping(payload.get("lineage")),
            created_at=payload.get("created_at") or payload.get("createdAt"),
            completed_at=payload.get("completed_at")
            or payload.get("completedAt"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requestId"] = self.request_id
        payload["delegationId"] = self.delegation_id
        payload["taskId"] = self.task_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["outcomeType"] = self.outcome_type
        payload["filesChanged"] = list(self.files_changed)
        payload["commandsRun"] = list(self.commands_run)
        payload["keyChanges"] = list(self.key_changes)
        payload["unresolvedQuestions"] = list(self.unresolved_questions)
        payload["rawTranscript"] = self.raw_transcript
        payload["errorMessage"] = self.error_message
        payload["createdAt"] = self.created_at
        payload["completedAt"] = self.completed_at
        return payload


@dataclass(slots=True)
class ExecutorFailure:
    error_code: str
    failure_class: str
    message: str
    request_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    kind: str = ""
    binary: str | None = None
    command: list[str] = field(default_factory=list)
    returncode: int | None = None
    signal: int | None = None
    timeout_seconds: float | None = None
    timed_out: bool = False
    spawn_failed: bool = False
    retryable: bool = False
    stdout: str = ""
    stderr: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.error_code = _normalize_text(self.error_code)
        self.failure_class = _normalize_text(self.failure_class)
        self.message = _normalize_text(self.message)
        self.request_id = _normalize_optional_text(self.request_id) or ""
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.kind = _normalize_text(self.kind)
        self.binary = _normalize_optional_text(self.binary)
        self.command = _normalize_text_list(self.command)
        self.returncode = (
            None if self.returncode is None else int(self.returncode)
        )
        self.signal = None if self.signal is None else int(self.signal)
        self.timeout_seconds = (
            None
            if self.timeout_seconds is None
            else float(self.timeout_seconds)
        )
        self.timed_out = bool(self.timed_out)
        self.spawn_failed = bool(self.spawn_failed)
        self.retryable = bool(self.retryable)
        self.stdout = str(self.stdout or "")
        self.stderr = str(self.stderr or "")
        self.details = _normalize_mapping(self.details)
        self.provenance = _normalize_mapping(self.provenance)
        if not self.provenance:
            self.provenance = {
                "request_id": self.request_id,
                "thread_id": self.thread_id,
                "source_message_id": self.source_message_id,
                "project_id": self.project_id,
                "executor_id": self.executor_id,
                "kind": self.kind,
            }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorTerminalResult:
    request_id: str = ""
    delegation_id: str = ""
    task_id: str = ""
    thread_id: int | str | None = None
    source_message_id: int | str | None = None
    project_id: int | str | None = None
    executor_id: str = ""
    title: str = ""
    status: str = DelegationJobStatus.COMPLETED.value
    summary: str | None = None
    task_summary: CanonicalTaskSummary | dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    key_changes: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    failure: ExecutorFailure | dict[str, Any] | None = None
    error_message: str | None = None
    final_text: str | None = None
    stdout: str = ""
    stderr: str = ""
    raw_transcript: str = ""
    output_chunks: list[ExecutorProgressEvent] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.request_id = (
            _normalize_optional_text(self.request_id)
            or _normalize_optional_text(self.delegation_id)
            or ""
        )
        self.delegation_id = (
            _normalize_optional_text(self.delegation_id) or self.request_id
        )
        self.task_id = _normalize_optional_text(self.task_id)
        self.thread_id = _normalize_identifier(self.thread_id)
        self.source_message_id = _normalize_identifier(self.source_message_id)
        self.project_id = _normalize_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.title = _normalize_optional_text(self.title) or ""
        self.status = (
            _normalize_optional_text(self.status)
            or DelegationJobStatus.COMPLETED.value
        )
        self.summary = _normalize_optional_text(self.summary)
        self.tags = _normalize_text_list(self.tags)
        self.files_changed = _normalize_text_list(self.files_changed)
        self.commands_run = _normalize_text_list(self.commands_run)
        self.key_changes = _normalize_text_list(self.key_changes)
        self.unresolved_questions = _normalize_text_list(
            self.unresolved_questions
        )
        self.result = _normalize_mapping(self.result)
        self.metadata = _normalize_mapping(self.metadata)
        self.failure = _coerce_failure(self.failure)
        self.error_message = _normalize_optional_text(self.error_message)
        self.final_text = _normalize_optional_text(self.final_text)
        self.stdout = str(self.stdout or "")
        self.stderr = str(self.stderr or "")
        self.raw_transcript = str(self.raw_transcript or "")
        self.output_chunks = [
            chunk
            if isinstance(chunk, ExecutorProgressEvent)
            else ExecutorProgressEvent.from_dict(chunk)
            for chunk in self.output_chunks
            if chunk is not None
        ]
        self.created_at = (
            _normalize_optional_text(self.created_at) or _utc_now_iso()
        )
        self.completed_at = (
            _normalize_optional_text(self.completed_at) or _utc_now_iso()
        )

        if self.summary is None:
            self.summary = (
                _normalize_optional_text(self.final_text)
                or _normalize_optional_text(self.result.get("summary"))
                or _normalize_optional_text(self.result.get("final_text"))
                or self.error_message
            )
        if self.final_text is None:
            self.final_text = self.summary

        if self.request_id:
            self.metadata.setdefault("request_id", self.request_id)
        if self.delegation_id:
            self.metadata.setdefault("delegation_id", self.delegation_id)
        if self.task_id:
            self.metadata.setdefault("task_id", self.task_id)
        if self.thread_id is not None:
            self.metadata.setdefault("thread_id", self.thread_id)
        if self.source_message_id is not None:
            self.metadata.setdefault(
                "source_message_id", self.source_message_id
            )
        if self.project_id is not None:
            self.metadata.setdefault("project_id", self.project_id)
        if self.executor_id:
            self.metadata.setdefault("executor_id", self.executor_id)
        if self.title:
            self.metadata.setdefault("title", self.title)
        if self.tags:
            self.metadata.setdefault("tags", list(self.tags))

        if self.task_summary is None:
            self.task_summary = CanonicalTaskSummary(
                request_id=self.request_id,
                delegation_id=self.delegation_id,
                task_id=self.task_id,
                thread_id=self.thread_id,
                source_message_id=self.source_message_id,
                project_id=self.project_id,
                executor_id=self.executor_id,
                title=self.title or (self.summary or ""),
                status=self.status,
                summary=self.summary or self.final_text,
                files_changed=list(self.files_changed),
                commands_run=list(self.commands_run),
                key_changes=list(self.key_changes),
                unresolved_questions=list(self.unresolved_questions),
                tags=list(self.tags),
                result=dict(self.result),
                metadata=dict(self.metadata),
                raw_transcript=self.raw_transcript or None,
                transcript=self.stdout or self.summary,
                failure=self.failure,
                error_message=self.error_message,
                created_at=self.created_at,
                completed_at=self.completed_at,
            )
        else:
            self.task_summary = _coerce_task_summary(self.task_summary)
            if self.task_summary is not None:
                self.task_summary.request_id = (
                    self.task_summary.request_id or self.request_id
                )
                self.task_summary.delegation_id = (
                    self.task_summary.delegation_id or self.delegation_id
                )
                self.task_summary.task_id = (
                    self.task_summary.task_id or self.task_id
                )
                self.task_summary.thread_id = (
                    self.task_summary.thread_id or self.thread_id
                )
                self.task_summary.source_message_id = (
                    self.task_summary.source_message_id
                    or self.source_message_id
                )
                self.task_summary.project_id = (
                    self.task_summary.project_id or self.project_id
                )
                self.task_summary.executor_id = (
                    self.task_summary.executor_id or self.executor_id
                )
                self.task_summary.title = self.task_summary.title or self.title
                self.task_summary.status = (
                    self.task_summary.status or self.status
                )
                self.task_summary.summary = (
                    self.task_summary.summary or self.summary
                )
                if not self.task_summary.tags:
                    self.task_summary.tags = list(self.tags)
                if not self.task_summary.files_changed:
                    self.task_summary.files_changed = list(self.files_changed)
                if not self.task_summary.commands_run:
                    self.task_summary.commands_run = list(self.commands_run)
                if not self.task_summary.key_changes:
                    self.task_summary.key_changes = list(self.key_changes)
                if not self.task_summary.unresolved_questions:
                    self.task_summary.unresolved_questions = list(
                        self.unresolved_questions
                    )
                if not self.task_summary.result:
                    self.task_summary.result = dict(self.result)
                if not self.task_summary.metadata:
                    self.task_summary.metadata = dict(self.metadata)
                if not self.task_summary.raw_transcript and self.raw_transcript:
                    self.task_summary.raw_transcript = self.raw_transcript
                if not self.task_summary.transcript:
                    self.task_summary.transcript = self.stdout or self.summary
                if not self.task_summary.failure and self.failure:
                    self.task_summary.failure = self.failure
                if not self.task_summary.error_message and self.error_message:
                    self.task_summary.error_message = self.error_message
                self.task_summary.created_at = (
                    self.task_summary.created_at or self.created_at
                )
                self.task_summary.completed_at = (
                    self.task_summary.completed_at or self.completed_at
                )

        self.tags = list(self.task_summary.tags)
        self.files_changed = list(self.task_summary.files_changed)
        self.commands_run = list(self.task_summary.commands_run)
        self.key_changes = list(self.task_summary.key_changes)
        self.unresolved_questions = list(self.task_summary.unresolved_questions)
        if not self.result and self.task_summary.result:
            self.result = dict(self.task_summary.result)
        if not self.metadata and self.task_summary.metadata:
            self.metadata = dict(self.task_summary.metadata)

    @property
    def canonical_summary(self) -> CanonicalTaskSummary:
        assert self.task_summary is not None
        return self.task_summary

    @property
    def canonical_task_summary(self) -> CanonicalTaskSummary:
        return self.canonical_summary

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requestId"] = self.request_id
        payload["delegationId"] = self.delegation_id
        payload["taskId"] = self.task_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["createdAt"] = self.created_at
        payload["completedAt"] = self.completed_at
        payload["filesChanged"] = list(self.files_changed)
        payload["commandsRun"] = list(self.commands_run)
        payload["keyChanges"] = list(self.key_changes)
        payload["unresolvedQuestions"] = list(self.unresolved_questions)
        payload["rawTranscript"] = self.raw_transcript
        payload["errorMessage"] = self.error_message
        payload["taskSummary"] = (
            self.task_summary.to_dict()
            if isinstance(self.task_summary, CanonicalTaskSummary)
            else self.task_summary
        )
        return payload


__all__ = [
    "CodexifyExecutorContextBundle",
    "CodexifyExecutorRequest",
    "ExecutorProgressEvent",
    "CanonicalEscalation",
    "ExecutorEscalationEvent",
    "CanonicalTaskSummary",
    "ExecutorFailure",
    "ExecutorTerminalResult",
]
