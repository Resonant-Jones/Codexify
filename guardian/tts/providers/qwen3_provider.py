"""TTSProvider wrapper for Codexify's Qwen3-TTS backend adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.contracts import TTS_BACKEND_QWEN3, TTSRenderRequest
from guardian.tts.tts_service import SynthesisError, TTSProvider


class Qwen3Provider(TTSProvider):
    """Expose Qwen3-TTS through the existing TTSManager interface."""

    def __init__(self):
        self.backend = Qwen3TTSBackend()

    def list_voices(self) -> List[str]:
        return ["default"]

    def synthesize(self, text: str, voice: str) -> bytes:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        with tempfile.TemporaryDirectory(prefix="codexify-qwen3-") as tmp_dir:
            output_path = Path(tmp_dir) / "speech.wav"
            result = self.backend.render(
                TTSRenderRequest(
                    text=text,
                    output_path=output_path,
                    backend_id=TTS_BACKEND_QWEN3,
                    output_format="wav",
                    voice_id=voice or "default",
                )
            )
            if not result.render_succeeded or not result.output_path:
                raise SynthesisError(
                    result.failure_reason
                    or "qwen3_tts_unavailable: configure local Qwen3-TTS"
                )
            return result.output_path.read_bytes()
