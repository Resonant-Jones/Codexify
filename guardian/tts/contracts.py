"""Canonical local TTS adapter contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal


class TTSBackendStatus(StrEnum):
    """Bounded backend health states for operator-visible TTS truth."""

    INSTALLED = "installed"
    MODEL_FILES_AVAILABLE = "model_files_available"
    IMPORTABLE = "importable"
    HEALTHY = "healthy"
    UNAVAILABLE = "backend_unavailable"
    RENDER_SUCCEEDED = "render_succeeded"
    RENDER_FAILED = "render_failed"


TTS_OUTPUT_FORMATS = ("wav", "mp3")
TTS_BACKEND_QWEN3 = "qwen3_tts"
TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE = "local_openai_compatible"
TTS_BACKEND_LOCAL_MOCK = "local"


@dataclass(frozen=True)
class TTSBackendInfo:
    backend_id: str
    display_name: str
    local_only: bool = True
    output_formats: tuple[str, ...] = ("wav",)
    supports_voice_sample_path: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TTSHealthProbe:
    backend_id: str
    status: TTSBackendStatus
    installed: bool
    model_files_available: bool
    importable: bool
    healthy: bool
    failure_reason: str | None = None
    setup_hint: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass(frozen=True)
class TTSRenderRequest:
    text: str
    output_path: Path
    backend_id: str = TTS_BACKEND_QWEN3
    output_format: Literal["wav", "mp3"] = "wav"
    voice_id: str = "default"
    voice_sample_path: Path | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class TTSRenderResult:
    backend_id: str
    status: TTSBackendStatus
    output_path: Path | None
    output_format: str
    voice_id: str
    render_succeeded: bool
    failure_reason: str | None = None
    setup_hint: str | None = None
    duration_seconds: float | None = None
    bytes_written: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["output_path"] = str(self.output_path) if self.output_path else None
        return payload
