"""
Text-to-Speech Service Module
--------------------------
Defines the abstract interface for TTS providers.
"""

from abc import ABC, abstractmethod
from typing import List

#: Native audio containers a provider may emit.
NATIVE_OUTPUT_FORMAT_WAV = "wav"
NATIVE_OUTPUT_FORMAT_MP3 = "mp3"


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    #: Container this provider emits from :meth:`synthesize`.
    #:
    #: Providers declare it here so a caller never has to encode a provider
    #: name to learn the container. ``wav`` is the default because it is the
    #: historical assumption of the local providers.
    native_output_format: str = NATIVE_OUTPUT_FORMAT_WAV

    @abstractmethod
    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: The text to synthesize
            voice: Voice ID or name to use

        Returns:
            bytes: Audio data in the provider's native container
                (see :attr:`native_output_format`)

        Raises:
            TTSError: If synthesis fails
        """
        pass

    @abstractmethod
    def list_voices(self) -> List[str]:
        """
        Get list of available voices.

        Returns:
            list: List of voice IDs/names
        """
        pass


class TTSError(Exception):
    """Base exception for TTS-related errors."""

    pass


class VoiceNotFoundError(TTSError):
    """Raised when specified voice is not found."""

    pass


class SynthesisError(TTSError):
    """Raised when text-to-speech synthesis fails."""

    pass


class ProviderNotFoundError(TTSError):
    """Raised when specified TTS provider is not found."""

    pass


class AuthenticationError(TTSError):
    """Raised when provider authentication fails."""

    pass
