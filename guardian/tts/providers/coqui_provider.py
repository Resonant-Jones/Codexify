"""Coqui local TTS provider scaffold."""

from __future__ import annotations

import os
from typing import List

from ..tts_service import SynthesisError, TTSProvider


class CoquiProvider(TTSProvider):
    """Scaffold provider for local Coqui TTS integration."""

    def __init__(self):
        self.model_name = (
            os.getenv("COQUI_TTS_MODEL")
            or "tts_models/en/ljspeech/tacotron2-DDC"
        )

    def list_voices(self) -> list[str]:
        return []

    def synthesize(self, text: str, voice: str) -> bytes:
        raise SynthesisError(
            "Coqui provider scaffold is not implemented in this build"
        )
