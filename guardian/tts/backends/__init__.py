"""Canonical executable TTS backend registry. Presence grants no authority."""

from collections.abc import Callable

from guardian.tts.backends.base import TTSBackend
from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.config import LocalTTSConfig, get_local_tts_config
from guardian.tts.contracts import TTS_BACKEND_QWEN3

# Only Qwen is executable here. Legacy profile ids are not registrations.
_BACKEND_FACTORIES: dict[str, Callable[[LocalTTSConfig], TTSBackend]] = {
    TTS_BACKEND_QWEN3: Qwen3TTSBackend,
}


class UnsupportedTTSBackendError(ValueError):
    """Explicit backend rejection; callers must never substitute a backend."""


def registered_tts_backend_ids() -> tuple[str, ...]:
    return tuple(_BACKEND_FACTORIES)


def resolve_tts_backend(
    backend_id: str, config: LocalTTSConfig | None = None
) -> TTSBackend:
    """Resolve a canonical id without probing health or invoking synthesis."""

    factory = _BACKEND_FACTORIES.get(backend_id)
    if factory is None:
        raise UnsupportedTTSBackendError(f"unsupported_tts_backend:{backend_id}")
    return factory(config or get_local_tts_config())


__all__ = [
    "Qwen3TTSBackend",
    "TTSBackend",
    "UnsupportedTTSBackendError",
    "registered_tts_backend_ids",
    "resolve_tts_backend",
]
