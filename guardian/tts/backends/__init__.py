"""Local TTS backend adapters."""

from guardian.tts.backends.base import TTSBackend
from guardian.tts.backends.qwen3 import Qwen3TTSBackend

__all__ = ["Qwen3TTSBackend", "TTSBackend"]
