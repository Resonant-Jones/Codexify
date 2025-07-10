"""
Guardian TTS Providers Package
--------------------------
Collection of TTS provider implementations.
"""

from .elevenlabs_provider import ElevenLabsProvider
from .google_provider import GoogleProvider
from .local_provider import LocalProvider

# Map of provider names to their classes
PROVIDERS = {
    "elevenlabs": ElevenLabsProvider,
    "google": GoogleProvider,
    "local": LocalProvider,
}

__all__ = ["ElevenLabsProvider", "GoogleProvider", "LocalProvider", "PROVIDERS"]
