"""
ElevenLabs TTS Provider
--------------------
Implementation of TTSProvider for ElevenLabs API.
"""

import os
import requests
from typing import List, Optional
import logging

from ..tts_service import (
    TTSProvider,
    AuthenticationError,
    SynthesisError,
    VoiceNotFoundError,
)

# Configure logging
logger = logging.getLogger(__name__)


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs implementation of TTSProvider."""

    API_BASE = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ElevenLabs provider.

        Args:
            api_key: ElevenLabs API key. If not provided, looks for ELEVENLABS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise AuthenticationError("ElevenLabs API key not found")

        self._voices = None  # Cache for voices

    def _get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        return {"Accept": "application/json", "xi-api-key": self.api_key}

    def list_voices(self) -> List[str]:
        """
        Get list of available voices.

        Returns:
            list: List of voice IDs

        Raises:
            AuthenticationError: If API key is invalid
            TTSError: If API request fails
        """
        if self._voices is not None:
            return self._voices

        try:
            response = requests.get(
                f"{self.API_BASE}/voices", headers=self._get_headers()
            )
            response.raise_for_status()

            voices_data = response.json()
            self._voices = [voice["voice_id"] for voice in voices_data["voices"]]
            return self._voices

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid ElevenLabs API key")
            raise SynthesisError(f"Failed to fetch voices: {str(e)}")

        except Exception as e:
            raise SynthesisError(f"Error listing voices: {str(e)}")

    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize text to speech using specified voice.

        Args:
            text: Text to synthesize
            voice: Voice ID to use

        Returns:
            bytes: Audio data in WAV format

        Raises:
            VoiceNotFoundError: If voice ID is not found
            AuthenticationError: If API key is invalid
            SynthesisError: If synthesis fails
        """
        if not text:
            raise ValueError("Text cannot be empty")

        # Verify voice exists
        available_voices = self.list_voices()
        if voice not in available_voices:
            raise VoiceNotFoundError(f"Voice '{voice}' not found")

        try:
            response = requests.post(
                f"{self.API_BASE}/text-to-speech/{voice}/stream",
                headers={**self._get_headers(), "Accept": "audio/mpeg"},
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                },
            )
            response.raise_for_status()

            return response.content

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid ElevenLabs API key")
            elif e.response.status_code == 404:
                raise VoiceNotFoundError(f"Voice '{voice}' not found")
            raise SynthesisError(f"Synthesis failed: {str(e)}")

        except Exception as e:
            raise SynthesisError(f"Error during synthesis: {str(e)}")

    def get_voice_info(self, voice_id: str) -> dict:
        """
        Get detailed information about a voice.

        Args:
            voice_id: ID of the voice

        Returns:
            dict: Voice information

        Raises:
            VoiceNotFoundError: If voice ID is not found
            TTSError: If request fails
        """
        try:
            response = requests.get(
                f"{self.API_BASE}/voices/{voice_id}", headers=self._get_headers()
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise VoiceNotFoundError(f"Voice '{voice_id}' not found")
            raise SynthesisError(f"Failed to get voice info: {str(e)}")
