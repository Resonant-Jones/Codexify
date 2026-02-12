"""
Guardian TTS Providers Package
--------------------------
Collection of TTS provider implementations.
"""

from __future__ import annotations

from .elevenlabs_provider import ElevenLabsProvider
from .local_provider import LocalProvider

try:
    from .google_provider import GoogleProvider, GoogleTTSProvider
except Exception:  # pragma: no cover - depends on optional package
    GoogleProvider = None  # type: ignore[assignment]
    GoogleTTSProvider = None  # type: ignore[assignment]

# Map of provider names to their classes
PROVIDERS = {
    "elevenlabs": ElevenLabsProvider,
    "local": LocalProvider,
}

if GoogleProvider is not None:
    PROVIDERS["google"] = GoogleProvider

__all__ = [
    "ElevenLabsProvider",
    "GoogleProvider",
    "GoogleTTSProvider",
    "LocalProvider",
    "PROVIDERS",
]
