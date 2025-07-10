"""
TTS Manager Module
---------------
Manages TTS providers and provides a unified interface for text-to-speech synthesis.
"""

import json
import os
from typing import Dict, List, Optional, Type
import logging

from .tts_service import TTSProvider, TTSError, ProviderNotFoundError
from .providers import PROVIDERS

# Configure logging
logger = logging.getLogger(__name__)


class TTSManager:
    """Manages multiple TTS providers and provides a unified interface."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize TTS manager.

        Args:
            config_path: Path to config file (optional)
        """
        self.providers: Dict[str, TTSProvider] = {}
        self.default_provider: Optional[str] = None

        # Load configuration
        self.config = self._load_config(
            config_path or os.path.join(os.path.dirname(__file__), "config.json")
        )

        # Register providers
        self._register_providers()

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from file or environment.

        Args:
            config_path: Path to config file

        Returns:
            dict: Configuration dictionary
        """
        config = {
            "default_provider": os.getenv("TTS_DEFAULT_PROVIDER", "local"),
            "providers": {
                "elevenlabs": {"api_key": os.getenv("ELEVENLABS_API_KEY")},
                "google": {
                    "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                },
                "local": {"enabled": True},
            },
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        return config

    def _register_providers(self) -> None:
        """Register configured TTS providers."""
        for name, provider_class in PROVIDERS.items():
            provider_config = self.config["providers"].get(name, {})

            # Skip if provider is explicitly disabled
            if not provider_config.get("enabled", True):
                continue

            try:
                # Initialize provider with its config
                if name == "elevenlabs":
                    provider = provider_class(api_key=provider_config.get("api_key"))
                elif name == "google":
                    provider = provider_class(
                        credentials_path=provider_config.get("credentials_path")
                    )
                else:
                    provider = provider_class()

                self.register_provider(name, provider)
                logger.info(f"Registered TTS provider: {name}")

            except Exception as e:
                logger.warning(f"Failed to register provider '{name}': {e}")

        # Set default provider
        if self.config["default_provider"] in self.providers:
            self.default_provider = self.config["default_provider"]
        elif self.providers:
            # Use first available provider as default
            self.default_provider = next(iter(self.providers.keys()))

    def register_provider(self, name: str, provider: TTSProvider) -> None:
        """
        Register a new TTS provider.

        Args:
            name: Provider name
            provider: Provider instance
        """
        if not isinstance(provider, TTSProvider):
            raise ValueError("Provider must implement TTSProvider interface")

        self.providers[name] = provider

        # Set as default if no default exists
        if not self.default_provider:
            self.default_provider = name

    def get_provider(self, name: Optional[str] = None) -> TTSProvider:
        """
        Get a TTS provider by name.

        Args:
            name: Provider name (uses default if not specified)

        Returns:
            TTSProvider: Provider instance

        Raises:
            ProviderNotFoundError: If provider is not found
        """
        provider_name = name or self.default_provider
        if not provider_name:
            raise ProviderNotFoundError("No default provider configured")

        provider = self.providers.get(provider_name)
        if not provider:
            raise ProviderNotFoundError(f"Provider '{provider_name}' not found")

        return provider

    def list_providers(self) -> List[str]:
        """Get list of registered provider names."""
        return list(self.providers.keys())

    def synthesize(
        self, text: str, voice: str, provider_name: Optional[str] = None
    ) -> bytes:
        """
        Synthesize text to speech using specified provider and voice.

        Args:
            text: Text to synthesize
            voice: Voice ID/name to use
            provider_name: Provider to use (uses default if not specified)

        Returns:
            bytes: Audio data in WAV format

        Raises:
            TTSError: If synthesis fails
        """
        provider = self.get_provider(provider_name)
        return provider.synthesize(text, voice)

    def list_voices(self, provider_name: Optional[str] = None) -> List[str]:
        """
        Get list of available voices for a provider.

        Args:
            provider_name: Provider to query (uses default if not specified)

        Returns:
            list: List of voice IDs/names

        Raises:
            TTSError: If request fails
        """
        provider = self.get_provider(provider_name)
        return provider.list_voices()

    def save_audio(self, audio_data: bytes, output_path: str) -> None:
        """
        Save audio data to file.

        Args:
            audio_data: Audio data in WAV format
            output_path: Path to save audio file
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            logger.info(f"Saved audio to: {output_path}")
        except Exception as e:
            raise TTSError(f"Failed to save audio file: {e}")
