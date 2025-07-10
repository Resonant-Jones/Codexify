"""
Google Cloud TTS Provider
---------------------
Implementation of TTSProvider for Google Cloud Text-to-Speech API.
"""

import os
from typing import List, Optional
import logging

try:
    from google.cloud import texttospeech
    from google.api_core import exceptions as google_exceptions
except ImportError:
    raise ImportError(
        "Google Cloud TTS dependencies not installed. "
        "Install with: pip install google-cloud-texttospeech"
    )

from ..tts_service import (
    TTSProvider,
    AuthenticationError,
    SynthesisError,
    VoiceNotFoundError,
)

# Configure logging
logger = logging.getLogger(__name__)


class GoogleProvider(TTSProvider):
    """Google Cloud implementation of TTSProvider."""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Cloud TTS provider.

        Args:
            credentials_path: Path to Google Cloud credentials JSON file.
                           If not provided, looks for GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise AuthenticationError(
                "Google Cloud credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or provide credentials_path."
            )

        try:
            self.client = texttospeech.TextToSpeechClient()
            self._voices = None  # Cache for voices
        except Exception as e:
            raise AuthenticationError(
                f"Failed to initialize Google Cloud TTS client: {str(e)}"
            )

    def list_voices(self) -> List[str]:
        """
        Get list of available voices.

        Returns:
            list: List of voice names

        Raises:
            AuthenticationError: If credentials are invalid
            TTSError: If request fails
        """
        if self._voices is not None:
            return self._voices

        try:
            response = self.client.list_voices()
            # Filter for English voices as an example
            self._voices = [
                voice.name
                for voice in response.voices
                if any(lang.startswith("en-") for lang in voice.language_codes)
            ]
            return self._voices

        except google_exceptions.PermissionDenied:
            raise AuthenticationError("Invalid Google Cloud credentials")
        except Exception as e:
            raise SynthesisError(f"Failed to list voices: {str(e)}")

    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize text to speech using specified voice.

        Args:
            text: Text to synthesize
            voice: Voice name to use

        Returns:
            bytes: Audio data in WAV format

        Raises:
            VoiceNotFoundError: If voice is not found
            AuthenticationError: If credentials are invalid
            SynthesisError: If synthesis fails
        """
        if not text:
            raise ValueError("Text cannot be empty")

        # Verify voice exists
        available_voices = self.list_voices()
        if voice not in available_voices:
            raise VoiceNotFoundError(f"Voice '{voice}' not found")

        try:
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Configure voice parameters
            voice_params = texttospeech.VoiceSelectionParams(
                name=voice, language_code="en-US"  # Default to US English
            )

            # Configure audio parameters (WAV format)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            )

            # Perform synthesis
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )

            return response.audio_content

        except google_exceptions.PermissionDenied:
            raise AuthenticationError("Invalid Google Cloud credentials")
        except google_exceptions.InvalidArgument as e:
            if "Voice" in str(e):
                raise VoiceNotFoundError(f"Voice '{voice}' not found")
            raise SynthesisError(f"Invalid synthesis parameters: {str(e)}")
        except Exception as e:
            raise SynthesisError(f"Synthesis failed: {str(e)}")

    def get_voice_info(self, voice_name: str) -> dict:
        """
        Get detailed information about a voice.

        Args:
            voice_name: Name of the voice

        Returns:
            dict: Voice information

        Raises:
            VoiceNotFoundError: If voice is not found
            TTSError: If request fails
        """
        try:
            response = self.client.list_voices()
            for voice in response.voices:
                if voice.name == voice_name:
                    return {
                        "name": voice.name,
                        "language_codes": voice.language_codes,
                        "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                        "natural_sample_rate_hertz": voice.natural_sample_rate_hertz,
                    }
            raise VoiceNotFoundError(f"Voice '{voice_name}' not found")

        except google_exceptions.PermissionDenied:
            raise AuthenticationError("Invalid Google Cloud credentials")
        except Exception as e:
            raise SynthesisError(f"Failed to get voice info: {str(e)}")
