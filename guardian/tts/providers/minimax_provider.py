"""MiniMax TTS provider scaffold.

This adapter is intentionally conservative for MVP and returns deterministic
configuration errors until credentials/endpoint are provided.
"""

from __future__ import annotations

import os
from typing import List

from ..tts_service import AuthenticationError, SynthesisError, TTSProvider


class MiniMaxProvider(TTSProvider):
    """Scaffold provider for MiniMax cloud TTS."""

    def __init__(self):
        self.api_key = (os.getenv("MINIMAX_API_KEY") or "").strip()
        self.base_url = (os.getenv("MINIMAX_TTS_URL") or "").strip()

    def list_voices(self) -> list[str]:
        return []

    def synthesize(self, text: str, voice: str) -> bytes:
        if not self.api_key or not self.base_url:
            raise AuthenticationError(
                "MiniMax provider is not configured (set MINIMAX_API_KEY and MINIMAX_TTS_URL)"
            )
        raise SynthesisError(
            "MiniMax provider scaffold is enabled but runtime synthesis is not implemented yet"
        )
