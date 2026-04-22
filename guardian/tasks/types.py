"""Task type definitions for async execution."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypedDict

from guardian.protocol_tokens import (
    DELEGATION_SUMMARY_OUTCOME_TYPE,
    DelegationJobStatus,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "task_id": str(payload.get("task_id") or uuid.uuid4()),
        "request_id": str(
            payload.get("request_id") or payload.get("requestId") or ""
        ),
        "created_at": str(payload.get("created_at") or _utc_now_iso()),
        "origin": str(payload.get("origin") or "unknown"),
    }
    task_type = payload.get("type")
    if isinstance(task_type, str) and task_type.strip():
        base["type"] = task_type.strip()
    return base


def _coerce_optional_positive_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


class TaskLifecycleState(str, Enum):
    QUEUED = "QUEUED"
    DISPATCHING = "DISPATCHING"
    AWAITING_ACK = "AWAITING_ACK"
    AWAITING_MODEL = "AWAITING_MODEL"
    AWAITING_FIRST_TOKEN = "AWAITING_FIRST_TOKEN"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TASK_LIFECYCLE_STATES = frozenset(state.value for state in TaskLifecycleState)


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _coerce_optional_raw_text(raw: Any) -> str | None:
    if raw is None:
        return None
    return str(raw)


def _coerce_optional_identifier(raw: Any) -> int | str | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    value = str(raw).strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return value


def _coerce_text_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        result = []
        for item in raw:
            value = str(item).strip()
            if value:
                result.append(value)
        return result
    value = str(raw).strip()
    return [value] if value else []


def _coerce_deduped_text_list(raw: Any) -> list[str]:
    result: list[str] = []
    for item in _coerce_text_list(raw):
        if item not in result:
            result.append(item)
    return result


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _status_text(raw: Any, default: str) -> str:
    value = str(raw or "").strip().lower()
    return value or default


def _normalize_executor_id(raw: Any) -> str:
    value = _coerce_optional_text(raw)
    return (
        value.lower().replace("-", "_").replace(" ", "_")
        if value is not None
        else ""
    )


class CandidateTraceIngestTask(TypedDict):
    request_id: str
    thread_id: int
    candidate_trace_id: str
    created_at: str
    payload: dict[str, Any]


class GraphWriteTask(TypedDict):
    request_id: str
    thread_id: str | int
    candidate_trace_id: str
    created_at: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    warnings: list[str]


@dataclass
class DelegationDraftRequest:
    thread_id: int | None = None
    conversation_id: str | None = None
    project_id: int | None = None
    repo_path: str = ""
    executor: str = ""
    user_intent: str = ""
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    origin: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DelegationDraftRequest:
        payload = payload or {}
        return cls(
            thread_id=_coerce_optional_positive_int(payload.get("thread_id")),
            conversation_id=_coerce_optional_text(
                payload.get("conversation_id")
            ),
            project_id=_coerce_optional_positive_int(payload.get("project_id")),
            repo_path=str(payload.get("repo_path") or "").strip(),
            executor=str(payload.get("executor") or "").strip(),
            user_intent=str(
                payload.get("user_intent") or payload.get("task_prompt") or ""
            ).strip(),
            tags=_coerce_deduped_text_list(payload.get("tags")),
            context=_coerce_mapping(
                payload.get("context")
                or payload.get("thread_context")
                or payload.get("conversation_context")
            ),
            created_at=str(payload.get("created_at") or _utc_now_iso()),
            origin=str(payload.get("origin") or "unknown"),
        )


@dataclass
class DelegationPacket:
    packet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: int | None = None
    conversation_id: str | None = None
    project_id: int | None = None
    repo_path: str = ""
    executor: str = ""
    status: str = DelegationJobStatus.DRAFT.value
    task_prompt: str = ""
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    approved_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DelegationPacket:
        payload = payload or {}
        return cls(
            packet_id=str(payload.get("packet_id") or uuid.uuid4()),
            thread_id=_coerce_optional_positive_int(payload.get("thread_id")),
            conversation_id=_coerce_optional_text(
                payload.get("conversation_id")
            ),
            project_id=_coerce_optional_positive_int(payload.get("project_id")),
            repo_path=str(payload.get("repo_path") or "").strip(),
            executor=str(payload.get("executor") or "").strip(),
            status=_status_text(
                payload.get("status"), DelegationJobStatus.DRAFT.value
            ),
            task_prompt=str(
                payload.get("task_prompt") or payload.get("user_intent") or ""
            ).strip(),
            tags=_coerce_deduped_text_list(payload.get("tags")),
            context=_coerce_mapping(
                payload.get("context")
                or payload.get("thread_context")
                or payload.get("conversation_context")
            ),
            created_at=str(payload.get("created_at") or _utc_now_iso()),
            approved_at=_coerce_optional_text(payload.get("approved_at")),
            completed_at=_coerce_optional_text(payload.get("completed_at")),
            error_message=_coerce_optional_text(payload.get("error_message")),
        )


@dataclass
class DelegationSummary:
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
    failure: dict[str, Any] | None = None
    error_message: str | None = None
    lineage: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.request_id = _coerce_optional_text(self.request_id) or ""
        self.delegation_id = (
            _coerce_optional_text(self.delegation_id) or self.request_id
        )
        self.task_id = _coerce_optional_text(self.task_id)
        self.thread_id = _coerce_optional_identifier(self.thread_id)
        self.source_message_id = _coerce_optional_identifier(
            self.source_message_id
        )
        self.project_id = _coerce_optional_identifier(self.project_id)
        self.executor_id = _normalize_executor_id(self.executor_id)
        self.title = _coerce_optional_text(self.title) or ""
        self.status = _status_text(
            self.status, DelegationJobStatus.COMPLETED.value
        )
        self.outcome_type = _status_text(
            self.outcome_type,
            DELEGATION_SUMMARY_OUTCOME_TYPE,
        )
        self.summary = _coerce_optional_text(self.summary)
        self.files_changed = _coerce_deduped_text_list(self.files_changed)
        self.commands_run = _coerce_deduped_text_list(self.commands_run)
        self.key_changes = _coerce_deduped_text_list(self.key_changes)
        self.unresolved_questions = _coerce_deduped_text_list(
            self.unresolved_questions
        )
        self.tags = _coerce_deduped_text_list(self.tags)
        self.result = _coerce_mapping(self.result)
        self.metadata = _coerce_mapping(self.metadata)
        self.raw_transcript = _coerce_optional_raw_text(self.raw_transcript)
        self.transcript = _coerce_optional_text(self.transcript)
        self.failure = _coerce_mapping(self.failure) if self.failure else None
        self.error_message = _coerce_optional_text(self.error_message)
        self.lineage = _coerce_mapping(self.lineage)
        self.created_at = str(self.created_at or _utc_now_iso())
        self.completed_at = str(self.completed_at or _utc_now_iso())
        if self.summary is None:
            self.summary = (
                _coerce_optional_text(self.result.get("summary"))
                or _coerce_optional_text(self.result.get("final_text"))
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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request_id"] = self.request_id
        payload["files_changed"] = _coerce_deduped_text_list(
            payload.get("files_changed")
        )
        payload["commands_run"] = _coerce_deduped_text_list(
            payload.get("commands_run")
        )
        payload["key_changes"] = _coerce_deduped_text_list(
            payload.get("key_changes")
        )
        payload["unresolved_questions"] = _coerce_deduped_text_list(
            payload.get("unresolved_questions")
        )
        payload["tags"] = _coerce_deduped_text_list(payload.get("tags"))
        payload["requestId"] = self.request_id
        payload["delegationId"] = self.delegation_id
        payload["taskId"] = self.task_id
        payload["threadId"] = self.thread_id
        payload["sourceMessageId"] = self.source_message_id
        payload["projectId"] = self.project_id
        payload["executorId"] = self.executor_id
        payload["title"] = self.title
        payload["outcomeType"] = self.outcome_type
        payload["filesChanged"] = list(self.files_changed)
        payload["commandsRun"] = list(self.commands_run)
        payload["keyChanges"] = list(self.key_changes)
        payload["unresolvedQuestions"] = list(self.unresolved_questions)
        payload["rawTranscript"] = self.raw_transcript
        payload["errorMessage"] = self.error_message
        payload["lineage"] = dict(self.lineage)
        payload["createdAt"] = self.created_at
        payload["completedAt"] = self.completed_at
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DelegationSummary:
        payload = payload or {}
        files_changed = _coerce_deduped_text_list(
            payload.get("files_changed") or payload.get("filesChanged")
        )
        commands_run = _coerce_deduped_text_list(
            payload.get("commands_run") or payload.get("commandsRun")
        )
        key_changes = _coerce_deduped_text_list(
            payload.get("key_changes") or payload.get("keyChanges")
        )
        unresolved_questions = _coerce_deduped_text_list(
            payload.get("unresolved_questions")
            or payload.get("unresolvedQuestions")
        )
        tags = _coerce_deduped_text_list(payload.get("tags"))
        return cls(
            request_id=str(
                payload.get("request_id") or payload.get("requestId") or ""
            ).strip(),
            delegation_id=str(
                payload.get("delegation_id")
                or payload.get("delegationId")
                or ""
            ).strip(),
            task_id=str(
                payload.get("task_id") or payload.get("taskId") or ""
            ).strip(),
            thread_id=_coerce_optional_identifier(
                payload.get("thread_id") or payload.get("threadId")
            ),
            source_message_id=_coerce_optional_identifier(
                payload.get("source_message_id")
                or payload.get("sourceMessageId")
            ),
            project_id=_coerce_optional_identifier(
                payload.get("project_id") or payload.get("projectId")
            ),
            executor_id=str(
                payload.get("executor_id") or payload.get("executorId") or ""
            ).strip(),
            title=str(payload.get("title") or "").strip(),
            status=_status_text(
                payload.get("status"),
                DelegationJobStatus.COMPLETED.value,
            ),
            outcome_type=_status_text(
                payload.get("outcome_type") or payload.get("outcomeType"),
                DELEGATION_SUMMARY_OUTCOME_TYPE,
            ),
            summary=_coerce_optional_text(payload.get("summary")),
            files_changed=files_changed,
            commands_run=commands_run,
            key_changes=key_changes,
            unresolved_questions=unresolved_questions,
            tags=tags,
            result=_coerce_mapping(payload.get("result")),
            metadata=_coerce_mapping(payload.get("metadata")),
            raw_transcript=_coerce_optional_raw_text(
                payload.get("raw_transcript") or payload.get("rawTranscript")
            ),
            transcript=_coerce_optional_text(payload.get("transcript")),
            failure=_coerce_mapping(payload.get("failure"))
            if payload.get("failure") is not None
            else None,
            error_message=_coerce_optional_text(payload.get("error_message")),
            lineage=_coerce_mapping(payload.get("lineage")),
            created_at=str(
                payload.get("created_at")
                or payload.get("createdAt")
                or _utc_now_iso()
            ),
            completed_at=str(
                payload.get("completed_at")
                or payload.get("completedAt")
                or _utc_now_iso()
            ),
        )


@dataclass
class BaseTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    type: str = "base"
    created_at: str = field(default_factory=_utc_now_iso)
    origin: str = "unknown"

    def __post_init__(self) -> None:
        self.request_id = _coerce_optional_text(self.request_id) or ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BaseTask:
        base = _base_kwargs(payload or {})
        if "type" not in base:
            base["type"] = cls.type
        return cls(**base)


@dataclass
class WarmupTask(BaseTask):
    type: str = "warmup"
    models: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WarmupTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        models = payload.get("models") or []
        return cls(models=list(models), **base)


@dataclass(kw_only=True)
class ChatCompletionTask(BaseTask):
    type: str = "chat_completion"
    user_id: str
    thread_id: int = 0
    latest_turn_message_id: int | None = None
    model: str | None = None
    provider: str | None = None
    temperature: float | None = None
    requested_model: str | None = None
    requested_provider: str | None = None
    selection_source: str | None = None
    provider_pinned: bool = False
    reasoning_mode: str | None = None
    max_context: int | None = 50
    depth_mode: str | None = "normal"
    requested_source_mode: str | None = None
    system_override: str | None = None
    retrieval_override: dict[str, Any] | None = None
    preferred_name: str | None = None
    profession: str | None = None
    guardian_name: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChatCompletionTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        user_id = _coerce_optional_text(
            payload.get("user_id") or payload.get("userId")
        )
        if not user_id:
            raise ValueError("ChatCompletionTask missing user_id")
        raw_temperature = payload.get("temperature")
        temperature: float | None
        if raw_temperature is None:
            temperature = None
        else:
            try:
                temperature = float(raw_temperature)
            except (TypeError, ValueError):
                temperature = None
        return cls(
            user_id=user_id,
            thread_id=int(payload.get("thread_id") or 0),
            latest_turn_message_id=_coerce_optional_positive_int(
                payload.get("latest_turn_message_id")
            ),
            model=payload.get("model"),
            provider=payload.get("provider"),
            temperature=temperature,
            requested_model=payload.get("requested_model"),
            requested_provider=payload.get("requested_provider"),
            selection_source=payload.get("selection_source"),
            provider_pinned=bool(payload.get("provider_pinned", False)),
            reasoning_mode=payload.get("reasoning_mode"),
            max_context=payload.get("max_context"),
            depth_mode=payload.get("depth_mode"),
            requested_source_mode=(
                None
                if payload.get("requested_source_mode") is None
                else str(payload.get("requested_source_mode"))
            ),
            system_override=payload.get("system_override"),
            retrieval_override=_coerce_mapping(
                payload.get("retrieval_override")
            )
            or None,
            preferred_name=_coerce_optional_text(payload.get("preferred_name")),
            profession=_coerce_optional_text(payload.get("profession")),
            guardian_name=_coerce_optional_text(payload.get("guardian_name")),
            **base,
        )


@dataclass
class EvalTask(BaseTask):
    type: str = "eval.trace"
    thread_id: int = 0
    trace_snapshot_id: str = ""
    evaluator_kind: str = "code"
    evaluator_name: str = "groundedness_basic"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvalTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            thread_id=int(payload.get("thread_id") or 0),
            trace_snapshot_id=str(
                payload.get("trace_snapshot_id")
                or payload.get("traceSnapshotId")
                or ""
            ).strip(),
            evaluator_kind=_normalize_executor_id(
                payload.get("evaluator_kind") or payload.get("evaluatorKind")
            )
            or "code",
            evaluator_name=str(
                payload.get("evaluator_name")
                or payload.get("evaluatorName")
                or "groundedness_basic"
            ).strip(),
            **base,
        )


@dataclass
class VoiceTurnTask(BaseTask):
    type: str = "voice_turn"
    thread_id: int = 0
    audio_b64: str = ""
    audio_mime: str | None = None
    stt_provider: str | None = None
    tts_enabled: bool = True
    tts_provider: str | None = None
    voice: str | None = None
    output_format: str | None = None
    completion_provider: str | None = None
    completion_model: str | None = None
    max_context: int | None = 50
    depth_mode: str | None = "normal"
    system_override: str | None = None
    turn_id: str | None = None
    turn_lock_owner: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VoiceTurnTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            thread_id=int(payload.get("thread_id") or 0),
            audio_b64=str(payload.get("audio_b64") or ""),
            audio_mime=payload.get("audio_mime"),
            stt_provider=payload.get("stt_provider"),
            tts_enabled=bool(payload.get("tts_enabled", True)),
            tts_provider=payload.get("tts_provider"),
            voice=payload.get("voice"),
            output_format=payload.get("output_format"),
            completion_provider=payload.get("completion_provider"),
            completion_model=payload.get("completion_model"),
            max_context=payload.get("max_context"),
            depth_mode=payload.get("depth_mode"),
            system_override=payload.get("system_override"),
            turn_id=payload.get("turn_id"),
            turn_lock_owner=payload.get("turn_lock_owner"),
            **base,
        )


@dataclass
class CronExecutionTask(BaseTask):
    """Queue payload for executing a cron run."""

    type: str = "cron.execute"
    cron_run_id: int = 0
    cron_job_id: int = 0
    job_type: str = "noop"
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CronExecutionTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            cron_run_id=int(payload.get("cron_run_id") or 0),
            cron_job_id=int(payload.get("cron_job_id") or 0),
            job_type=str(payload.get("job_type") or "noop").strip().lower(),
            payload=dict(payload.get("payload") or {}),
            **base,
        )


@dataclass
class DelegationTask(BaseTask):
    type: str = "delegation.task"
    packet_id: str = ""
    delegation_id: str = ""
    thread_id: int | None = None
    source_message_id: int | None = None
    conversation_id: str | None = None
    project_id: int | None = None
    repo_path: str = ""
    executor: str = ""
    task_prompt: str = ""
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    status: str = DelegationJobStatus.QUEUED.value

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DelegationTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            packet_id=str(payload.get("packet_id") or "").strip(),
            delegation_id=str(payload.get("delegation_id") or "").strip(),
            thread_id=_coerce_optional_positive_int(payload.get("thread_id")),
            source_message_id=_coerce_optional_positive_int(
                payload.get("source_message_id")
                or payload.get("sourceMessageId")
            ),
            conversation_id=_coerce_optional_text(
                payload.get("conversation_id")
            ),
            project_id=_coerce_optional_positive_int(payload.get("project_id")),
            repo_path=str(payload.get("repo_path") or "").strip(),
            executor=str(payload.get("executor") or "").strip(),
            task_prompt=str(
                payload.get("task_prompt") or payload.get("user_intent") or ""
            ).strip(),
            tags=_coerce_deduped_text_list(payload.get("tags")),
            context=_coerce_mapping(
                payload.get("context")
                or payload.get("thread_context")
                or payload.get("conversation_context")
            ),
            status=_status_text(
                payload.get("status"), DelegationJobStatus.QUEUED.value
            ),
            **base,
        )


TASK_TYPE_REGISTRY: dict[str, type[BaseTask]] = {
    "warmup": WarmupTask,
    "chat_completion": ChatCompletionTask,
    "eval.trace": EvalTask,
    "voice_turn": VoiceTurnTask,
    "cron.execute": CronExecutionTask,
    "delegation.task": DelegationTask,
}


def task_from_dict(payload: dict[str, Any]) -> BaseTask:
    task_type = str(payload.get("type") or "").strip()
    task_cls = TASK_TYPE_REGISTRY.get(task_type)
    if not task_cls:
        raise ValueError(f"Unknown task type: {task_type or '<missing>'}")
    return task_cls.from_dict(payload)
