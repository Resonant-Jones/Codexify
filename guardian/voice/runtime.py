"""Shared voice runtime constants and feature-flag helpers."""

from __future__ import annotations

import os

VOICE_QUEUE_NAME = os.getenv("VOICE_QUEUE_NAME", "codexify:queue:voice")
VOICE_HEARTBEAT_KEY = os.getenv(
    "VOICE_HEARTBEAT_KEY", "codexify:worker:voice:heartbeat"
)
VOICE_HEARTBEAT_TTL_SECONDS = int(
    os.getenv("VOICE_HEARTBEAT_TTL_SECONDS", "30")
)
VOICE_HEARTBEAT_INTERVAL_SECONDS = int(
    os.getenv("VOICE_HEARTBEAT_INTERVAL_SECONDS", "10")
)

STREAM_PROXY_ENABLED = os.getenv(
    "CODEXIFY_VOICE_STREAM_PROXY_ENABLED", "0"
).strip().lower() in {"1", "true", "yes", "on"}

SUPPORTED_TTS_PROVIDERS = (
    "local_openai_compatible",
    "elevenlabs",
    "minimax",
)
SUPPORTED_STT_PROVIDERS = (
    "local_openai_compatible",
    "whispercpp",
)
SUPPORTED_INPUT_MIME = (
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
)

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    return default


def voice_routes_enabled() -> bool:
    return _env_bool("CODEXIFY_VOICE_ROUTES_ENABLED", True)


def voice_turns_enabled() -> bool:
    explicit = os.getenv("CODEXIFY_VOICE_TURNS_ENABLED")
    if explicit is not None:
        return str(explicit).strip().lower() in _TRUTHY

    legacy = os.getenv("CODEXIFY_ENABLE_VOICE_TURNS")
    if legacy is not None:
        return str(legacy).strip().lower() in _TRUTHY

    # Legacy fallback: only explicit turn-like modes imply enabled.
    mode = (os.getenv("CODEXIFY_VOICE_MODE") or "").strip().lower()
    return mode in {"turns", "turn", "turn_based", "turn-based"}
