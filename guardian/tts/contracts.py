"""Canonical provider-neutral TTS adapter contracts."""

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
    UNKNOWN = "unknown"


class TTSBackendCapability(StrEnum):
    """Declared adapter features; declarations are not synthesis proof."""

    VOICE_SAMPLE_PATH = "voice_sample_path"


TTS_OUTPUT_FORMATS = ("wav", "mp3")
TTS_BACKEND_QWEN3 = "qwen3_tts"
TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE = "local_openai_compatible"
TTS_BACKEND_LOCAL_MOCK = "local"
TTS_LOCAL_BACKEND_IDS = (
    TTS_BACKEND_QWEN3,
    TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE,
    TTS_BACKEND_LOCAL_MOCK,
)

TTS_VOICE_MODE_PRESET = "preset"
TTS_VOICE_MODE_PROMPT = "prompt"
TTS_VOICE_MODE_REFERENCE = "reference_audio"
TTS_VOICE_MODE_CUSTOM = "custom"
TTS_VOICE_MODES = (
    TTS_VOICE_MODE_PRESET,
    TTS_VOICE_MODE_PROMPT,
    TTS_VOICE_MODE_REFERENCE,
    TTS_VOICE_MODE_CUSTOM,
)


@dataclass(frozen=True)
class TTSBackendInfo:
    backend_id: str
    display_name: str
    local_only: bool = True
    output_formats: tuple[str, ...] = ("wav",)
    supports_voice_sample_path: bool = False
    capabilities: tuple[TTSBackendCapability, ...] = ()

    def __post_init__(self) -> None:
        # Preserve the existing Qwen declaration without changing its adapter.
        if self.supports_voice_sample_path:
            object.__setattr__(
                self,
                "capabilities",
                tuple(
                    dict.fromkeys(
                        (*self.capabilities, TTSBackendCapability.VOICE_SAMPLE_PATH)
                    )
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TTSHealthProbe:
    """Independent evidence, with None meaning unestablished/not applicable.

    Local installation fields remain compatible with Qwen. Remote adapters
    leave them unset. No evidence field implies another or release support.
    """

    backend_id: str
    status: TTSBackendStatus
    installed: bool | None = None
    model_files_available: bool | None = None
    importable: bool | None = None
    healthy: bool | None = None
    failure_reason: str | None = None
    setup_hint: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    configured: bool | None = None
    credential_available: bool | None = None
    egress_allowed: bool | None = None
    reachable: bool | None = None
    synthesis_proven: bool | None = None

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
    profile_id: str | None = None
    voice_prompt: str | None = None
    style_instructions: str | None = None
    language: str | None = None
    speed: float | None = None
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    max_new_tokens: int | None = None
    do_sample: bool | None = None
    backend_params: dict[str, Any] = field(default_factory=dict)
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
