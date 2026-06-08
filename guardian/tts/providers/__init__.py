"""
Guardian TTS Providers Package
--------------------------
Collection of TTS provider implementations.
"""

from __future__ import annotations

from .local_provider import LocalProvider
from .qwen3_provider import Qwen3Provider

try:
    from .elevenlabs_provider import ElevenLabsProvider
except Exception:  # pragma: no cover - depends on optional packages/secrets
    ElevenLabsProvider = None  # type: ignore[assignment]

try:
    from .google_provider import GoogleProvider, GoogleTTSProvider
except Exception:  # pragma: no cover - depends on optional package
    GoogleProvider = None  # type: ignore[assignment]
    GoogleTTSProvider = None  # type: ignore[assignment]

# Map of provider names to their classes
PROVIDERS = {
    "local": LocalProvider,
    "qwen3_tts": Qwen3Provider,
}

if ElevenLabsProvider is not None:
    PROVIDERS["elevenlabs"] = ElevenLabsProvider

if GoogleProvider is not None:
    PROVIDERS["google"] = GoogleProvider

__all__ = [
    "ElevenLabsProvider",
    "GoogleProvider",
    "GoogleTTSProvider",
    "LocalProvider",
    "PROVIDERS",
    "Qwen3Provider",
]
