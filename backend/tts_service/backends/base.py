"""Base interface for TTS backend providers."""

from abc import ABC, abstractmethod
from typing import Optional


class TTSBackend(ABC):
    """Abstract base class for TTS backend implementations."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> tuple[bytes, int]:
        """
        Synthesize speech from text.

        Args:
            text: The text to synthesize
            voice: Optional voice identifier (backend-specific)
            speed: Optional speed modifier (1.0 = normal)

        Returns:
            tuple of (wav_bytes, sampling_rate)
            Audio must be WAV-encoded PCM.
        """
        pass
