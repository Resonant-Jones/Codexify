"""Task type definitions for async execution."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type


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
    model: str | None = None
    provider: str | None = None
    max_context: int | None = 50
    depth_mode: str | None = "normal"
    system_override: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChatCompletionTask:
        base = _base_kwargs(payload or {})
        base.setdefault("type", cls.type)
        return cls(
            thread_id=int(payload.get("thread_id") or 0),
            model=payload.get("model"),
            provider=payload.get("provider"),
            max_context=payload.get("max_context"),
            depth_mode=payload.get("depth_mode"),
            system_override=payload.get("system_override"),
            **base,
        )


TASK_TYPE_REGISTRY: dict[str, type[BaseTask]] = {
    "warmup": WarmupTask,
    "chat_completion": ChatCompletionTask,
}


def task_from_dict(payload: dict[str, Any]) -> BaseTask:
    task_type = str(payload.get("type") or "").strip()
    task_cls = TASK_TYPE_REGISTRY.get(task_type)
    if not task_cls:
        raise ValueError(f"Unknown task type: {task_type or '<missing>'}")
    return task_cls.from_dict(payload)
