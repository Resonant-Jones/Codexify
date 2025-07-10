"""
Local Mock TTS Provider
-------------------
A simple mock TTS provider for testing and development.
"""

import os
import wave
import struct
from typing import List
import logging

from ..tts_service import TTSProvider, TTSError, VoiceNotFoundError

# Configure logging
logger = logging.getLogger(__name__)


class LocalProvider(TTSProvider):
    """
    Local mock implementation of TTSProvider.
    Generates simple sine wave tones for testing.
    """

    # Available mock voices
    MOCK_VOICES = ["local-male-1", "local-female-1", "local-neutral-1"]

    def __init__(self):
        """Initialize local provider."""
        logger.info("Initialized local mock TTS provider")

    def list_voices(self) -> List[str]:
        """
        Get list of available mock voices.

        Returns:
            list: List of voice names
        """
        return self.MOCK_VOICES.copy()

    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Generate a simple audio tone as mock TTS output.

        Args:
            text: Text to "synthesize"
            voice: Voice to use

        Returns:
            bytes: WAV audio data

        Raises:
            VoiceNotFoundError: If voice is not found
        """
        if not text:
            raise ValueError("Text cannot be empty")

        if voice not in self.MOCK_VOICES:
            raise VoiceNotFoundError(f"Voice '{voice}' not found")

        try:
            # Generate a simple sine wave based on text length
            duration = min(len(text) * 0.1, 5.0)  # 0.1s per character, max 5s
            sample_rate = 44100
            frequency = 440.0  # A4 note

            # Adjust frequency based on voice
            if voice == "local-male-1":
                frequency *= 0.5  # Lower pitch
            elif voice == "local-female-1":
                frequency *= 1.5  # Higher pitch

            # Generate samples
            samples = []
            for i in range(int(duration * sample_rate)):
                t = float(i) / sample_rate
                value = int(32767.0 * 0.3 * self._sine_wave(t, frequency))
                samples.append(struct.pack("h", value))

            # Create WAV file in memory
            wav_data = self._create_wav(b"".join(samples), sample_rate)

            logger.info(
                f"Generated mock audio for text of length {len(text)} "
                f"using voice {voice}"
            )

            return wav_data

        except Exception as e:
            raise TTSError(f"Failed to generate mock audio: {str(e)}")

    def _sine_wave(self, t: float, frequency: float) -> float:
        """Generate sine wave value at time t."""
        import math

        return math.sin(2.0 * math.pi * frequency * t)

    def _create_wav(self, audio_data: bytes, sample_rate: int) -> bytes:
        """
        Create a WAV file in memory.

        Args:
            audio_data: Raw audio samples
            sample_rate: Sample rate in Hz

        Returns:
            bytes: WAV file data
        """
        try:
            import io

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)

            return wav_buffer.getvalue()

        except Exception as e:
            raise TTSError(f"Failed to create WAV file: {str(e)}")

    def get_voice_info(self, voice: str) -> dict:
        """
        Get mock voice information.

        Args:
            voice: Voice name

        Returns:
            dict: Voice information

        Raises:
            VoiceNotFoundError: If voice is not found
        """
        if voice not in self.MOCK_VOICES:
            raise VoiceNotFoundError(f"Voice '{voice}' not found")

        gender = (
            "male" if "male" in voice else "female" if "female" in voice else "neutral"
        )

        return {
            "name": voice,
            "type": "mock",
            "gender": gender,
            "description": f"Local mock {gender} voice for testing",
        }
