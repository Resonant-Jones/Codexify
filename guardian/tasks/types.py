"""Task type definitions for async execution."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from guardian.protocol_tokens import DelegationJobStatus


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "task_id": str(payload.get("task_id") or uuid.uuid4()),
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


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


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


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _status_text(raw: Any, default: str) -> str:
    value = str(raw or "").strip().lower()
    return value or default


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
            tags=_coerce_text_list(payload.get("tags")),
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
            tags=_coerce_text_list(payload.get("tags")),
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
    delegation_id: str = ""
    task_id: str = ""
    status: str = DelegationJobStatus.COMPLETED.value
    summary: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DelegationSummary:
        payload = payload or {}
        return cls(
            delegation_id=str(payload.get("delegation_id") or "").strip(),
            task_id=str(payload.get("task_id") or "").strip(),
            status=_status_text(
                payload.get("status"),
                DelegationJobStatus.COMPLETED.value,
            ),
            summary=_coerce_optional_text(payload.get("summary")),
            result=_coerce_mapping(payload.get("result")),
            metadata=_coerce_mapping(payload.get("metadata")),
            error_message=_coerce_optional_text(payload.get("error_message")),
            created_at=str(payload.get("created_at") or _utc_now_iso()),
            completed_at=str(payload.get("completed_at") or _utc_now_iso()),
        )


@dataclass
class BaseTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "base"
    created_at: str = field(default_factory=_utc_now_iso)
    origin: str = "unknown"

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


@dataclass
class ChatCompletionTask(BaseTask):
    type: str = "chat_completion"
    thread_id: int = 0
    latest_turn_message_id: int | None = None
    model: str | None = None
    provider: str | None = None
    requested_model: str | None = None
    requested_provider: str | None = None
    selection_source: str | None = None
    provider_pinned: bool = False
    reasoning_mode: str | None = None
    max_context: int | None = 50
    depth_mode: str | None = "normal"
    system_override: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChatCompletionTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            thread_id=int(payload.get("thread_id") or 0),
            latest_turn_message_id=_coerce_optional_positive_int(
                payload.get("latest_turn_message_id")
            ),
            model=payload.get("model"),
            provider=payload.get("provider"),
            requested_model=payload.get("requested_model"),
            requested_provider=payload.get("requested_provider"),
            selection_source=payload.get("selection_source"),
            provider_pinned=bool(payload.get("provider_pinned", False)),
            reasoning_mode=payload.get("reasoning_mode"),
            max_context=payload.get("max_context"),
            depth_mode=payload.get("depth_mode"),
            system_override=payload.get("system_override"),
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
            conversation_id=_coerce_optional_text(
                payload.get("conversation_id")
            ),
            project_id=_coerce_optional_positive_int(payload.get("project_id")),
            repo_path=str(payload.get("repo_path") or "").strip(),
            executor=str(payload.get("executor") or "").strip(),
            task_prompt=str(
                payload.get("task_prompt") or payload.get("user_intent") or ""
            ).strip(),
            tags=_coerce_text_list(payload.get("tags")),
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
