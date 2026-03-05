"""Voice runtime configuration helpers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from guardian.voice.runtime import (
    STREAM_PROXY_ENABLED,
    voice_routes_enabled,
    voice_turns_enabled,
)

_TRUTHY = {"1", "true", "yes", "on"}
_LOGGER = logging.getLogger(__name__)
_WARNED_LEGACY_KEYS: set[str] = set()


def _warn_legacy_once(name: str, replacement: str) -> None:
    if name in _WARNED_LEGACY_KEYS:
        return
    _WARNED_LEGACY_KEYS.add(name)
    _LOGGER.warning(
        "[voice.config] legacy env %s is deprecated; use %s",
        name,
        replacement,
    )


def _get_int(
    name: str,
    default: int,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _get_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in _TRUTHY


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    mode: str
    routes_enabled: bool
    turns_enabled: bool
    stt_provider: str
    tts_provider: str
    local_voice_base_url: str | None
    stream_proxy_enabled: bool
    stt_timeout_seconds: int
    completion_timeout_seconds: int
    tts_timeout_seconds: int
    input_max_bytes: int
    output_max_bytes: int
    max_duration_seconds: int
    turn_dedupe_ttl_seconds: int
    internal_format: str
    delivery_formats: tuple[str, ...]
    bake_models: bool
    service_url: str | None


def _resolve_mode() -> str:
    mode = (os.getenv("CODEXIFY_VOICE_MODE") or "").strip().lower()
    return mode or "off"


def _resolve_local_voice_base_url() -> str | None:
    explicit = (os.getenv("CODEXIFY_LOCAL_VOICE_BASE_URL") or "").strip()
    if explicit:
        return explicit

    stt_base = (os.getenv("CODEXIFY_STT_BASE_URL") or "").strip()
    if stt_base:
        _warn_legacy_once(
            "CODEXIFY_STT_BASE_URL", "CODEXIFY_LOCAL_VOICE_BASE_URL"
        )
        return stt_base

    legacy_tts = (os.getenv("CODEXIFY_LOCAL_TTS_BASE_URL") or "").strip()
    if legacy_tts:
        _warn_legacy_once(
            "CODEXIFY_LOCAL_TTS_BASE_URL", "CODEXIFY_LOCAL_VOICE_BASE_URL"
        )
        return legacy_tts

    legacy_stt = (os.getenv("CODEXIFY_LOCAL_STT_BASE_URL") or "").strip()
    if legacy_stt:
        _warn_legacy_once(
            "CODEXIFY_LOCAL_STT_BASE_URL", "CODEXIFY_LOCAL_VOICE_BASE_URL"
        )
        return legacy_stt

    fallback = (os.getenv("LOCAL_BASE_URL") or "").strip()
    if fallback:
        _warn_legacy_once("LOCAL_BASE_URL", "CODEXIFY_LOCAL_VOICE_BASE_URL")
        return fallback
    return None


def _normalize_provider(provider: str, *, kind: str) -> str:
    value = (provider or "").strip().lower()
    if not value:
        return ""
    if value in {"whisper_local", "whispercpp"}:
        return "whispercpp"
    if value in {"local_openai_compatible", "openai_compatible_local"}:
        return "local_openai_compatible"
    if kind == "tts" and value in {"local"}:
        return "local_openai_compatible"
    return value


def get_voice_runtime_config() -> VoiceRuntimeConfig:
    mode = _resolve_mode()
    if os.getenv("CODEXIFY_VOICE_MODE") is not None:
        _warn_legacy_once("CODEXIFY_VOICE_MODE", "CODEXIFY_*_PROVIDER flags")
    local_voice_base_url = _resolve_local_voice_base_url()

    explicit_stt = (os.getenv("CODEXIFY_STT_PROVIDER") or "").strip().lower()
    if explicit_stt:
        stt_provider = _normalize_provider(explicit_stt, kind="stt")
    else:
        # Canonical local-first default.
        stt_provider = "local_openai_compatible"

    explicit_tts = (os.getenv("CODEXIFY_TTS_PROVIDER") or "").strip().lower()
    if explicit_tts:
        tts_provider = _normalize_provider(explicit_tts, kind="tts")
    else:
        # Canonical local-first default.
        tts_provider = "local_openai_compatible"

    if os.getenv("CODEXIFY_ENABLE_VOICE_TURNS") is not None:
        _warn_legacy_once(
            "CODEXIFY_ENABLE_VOICE_TURNS", "CODEXIFY_VOICE_TURNS_ENABLED"
        )

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
        routes_enabled=voice_routes_enabled(),
        turns_enabled=voice_turns_enabled(),
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        local_voice_base_url=local_voice_base_url,
        stream_proxy_enabled=STREAM_PROXY_ENABLED,
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
        turn_dedupe_ttl_seconds=_get_int(
            "CODEXIFY_VOICE_TURN_DEDUPE_TTL_SECONDS",
            600,
            minimum=300,
            maximum=900,
        ),
        internal_format=(os.getenv("CODEXIFY_VOICE_INTERNAL_FORMAT") or "wav")
        .strip()
        .lower(),
        delivery_formats=delivery_formats or ("wav",),
        bake_models=_get_bool("CODEXIFY_VOICE_BAKE_MODELS", False),
        service_url=service_url or None,
    )
