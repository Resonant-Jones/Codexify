"""Voice runtime configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


def _get_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        value = default
    return max(minimum, value)


def _get_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in _TRUTHY


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    mode: str
    stt_provider: str
    tts_provider: str
    stt_timeout_seconds: int
    completion_timeout_seconds: int
    tts_timeout_seconds: int
    input_max_bytes: int
    output_max_bytes: int
    max_duration_seconds: int
    internal_format: str
    delivery_formats: tuple[str, ...]
    bake_models: bool
    service_url: str | None


def get_voice_runtime_config() -> VoiceRuntimeConfig:
    mode = (os.getenv("CODEXIFY_VOICE_MODE") or "off").strip().lower()
    stt_provider = (
        (os.getenv("CODEXIFY_STT_PROVIDER") or "whisper_local").strip().lower()
    )

    explicit_tts = (os.getenv("CODEXIFY_TTS_PROVIDER") or "").strip().lower()
    if explicit_tts:
        tts_provider = explicit_tts
    elif mode == "local":
        tts_provider = "local_openai_compatible"
    else:
        tts_provider = "elevenlabs"

    delivery_formats_raw = (
        os.getenv("CODEXIFY_VOICE_DELIVERY_FORMATS") or "wav,mp3"
    )
    delivery_formats = tuple(
        fmt.strip().lower()
        for fmt in delivery_formats_raw.split(",")
        if fmt.strip()
    )

    service_url = (os.getenv("CODEXIFY_VOICE_SERVICE_URL") or "").strip()

    return VoiceRuntimeConfig(
        mode=mode,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        stt_timeout_seconds=_get_int("CODEXIFY_STT_TIMEOUT_SECONDS", 20),
        completion_timeout_seconds=_get_int(
            "CODEXIFY_VOICE_COMPLETION_TIMEOUT_SECONDS", 60
        ),
        tts_timeout_seconds=_get_int("CODEXIFY_TTS_TIMEOUT_SECONDS", 30),
        input_max_bytes=_get_int(
            "CODEXIFY_VOICE_INPUT_MAX_BYTES", 15 * 1024 * 1024
        ),
        output_max_bytes=_get_int(
            "CODEXIFY_VOICE_OUTPUT_MAX_BYTES", 15 * 1024 * 1024
        ),
        max_duration_seconds=_get_int(
            "CODEXIFY_VOICE_MAX_DURATION_SECONDS", 120
        ),
        internal_format=(os.getenv("CODEXIFY_VOICE_INTERNAL_FORMAT") or "wav")
        .strip()
        .lower(),
        delivery_formats=delivery_formats or ("wav",),
        bake_models=_get_bool("CODEXIFY_VOICE_BAKE_MODELS", False),
        service_url=service_url or None,
    )
