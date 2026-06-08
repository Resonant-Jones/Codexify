"""Configuration for Codexify's local TTS adapter layer."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from guardian.tts.contracts import TTS_BACKEND_QWEN3

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LocalTTSConfig:
    backend_id: str
    local_only: bool
    qwen3_model_path: Path | None
    qwen3_python: str
    qwen3_render_script: Path | None
    output_dir: Path
    default_voice: str
    chunk_max_chars: int
    short_pause_ms: int
    long_pause_ms: int


def _get_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in _TRUTHY


def _get_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(int(raw), minimum)
    except ValueError:
        return default


def _path_or_none(value: str | None) -> Path | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return Path(cleaned).expanduser()


def get_local_tts_config() -> LocalTTSConfig:
    """Resolve local TTS configuration without touching LLM provider routing."""

    backend_id = (
        os.getenv("CODEXIFY_TTS_BACKEND")
        or os.getenv("CODEXIFY_TTS_PROVIDER")
        or TTS_BACKEND_QWEN3
    ).strip().lower()
    output_dir = Path(
        os.getenv("CODEXIFY_TTS_OUTPUT_DIR") or "storage/tts"
    ).expanduser()
    return LocalTTSConfig(
        backend_id=backend_id,
        local_only=_get_bool("CODEXIFY_TTS_LOCAL_ONLY", True),
        qwen3_model_path=_path_or_none(
            os.getenv("CODEXIFY_TTS_QWEN3_MODEL_PATH")
        ),
        qwen3_python=(
            os.getenv("CODEXIFY_TTS_QWEN3_PYTHON") or sys.executable
        ).strip(),
        qwen3_render_script=_path_or_none(
            os.getenv("CODEXIFY_TTS_QWEN3_RENDER_SCRIPT")
        ),
        output_dir=output_dir,
        default_voice=(
            os.getenv("CODEXIFY_TTS_DEFAULT_VOICE") or "default"
        ).strip(),
        chunk_max_chars=_get_int("CODEXIFY_TTS_CHUNK_MAX_CHARS", 900),
        short_pause_ms=_get_int("CODEXIFY_TTS_SHORT_PAUSE_MS", 350),
        long_pause_ms=_get_int("CODEXIFY_TTS_LONG_PAUSE_MS", 900),
    )
