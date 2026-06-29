"""
TTS Manager Module
---------------
Manages TTS providers and provides a unified interface for text-to-speech synthesis.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .providers import PROVIDERS
from .contracts import TTS_BACKEND_QWEN3
from .providers.coqui_provider import CoquiProvider
from .providers.local_openai_compatible_provider import (
    LocalOpenAICompatibleProvider,
)
from .providers.minimax_provider import MiniMaxProvider
from .tts_service import (
    AuthenticationError,
    ProviderNotFoundError,
    TTSError,
    TTSProvider,
)

# Configure logging
logger = logging.getLogger(__name__)


PROVIDER_CLASSIFICATION_LOCAL = "local"
PROVIDER_CLASSIFICATION_CLOUD = "cloud"

PROVIDER_STATE_AVAILABLE = "available"
PROVIDER_STATE_DEGRADED = "degraded"
PROVIDER_STATE_UNAVAILABLE = "unavailable"

VOICE_KIND_PRESET = "preset"

_PROVIDER_SPECS: dict[str, dict[str, Any]] = {
    "local": {
        "label": "Local Mock",
        "classification": PROVIDER_CLASSIFICATION_LOCAL,
        "capabilities": {
            "presetVoices": True,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
    "qwen3_tts": {
        "label": "Qwen3-TTS",
        "classification": PROVIDER_CLASSIFICATION_LOCAL,
        "capabilities": {
            "presetVoices": True,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
    "local_openai_compatible": {
        "label": "Local OpenAI-Compatible",
        "classification": PROVIDER_CLASSIFICATION_LOCAL,
        "capabilities": {
            "presetVoices": True,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
    "elevenlabs": {
        "label": "ElevenLabs",
        "classification": PROVIDER_CLASSIFICATION_CLOUD,
        "capabilities": {
            "presetVoices": True,
            "cloning": True,
            "promptDefinedVoice": True,
            "preview": False,
        },
    },
    "google": {
        "label": "Google Cloud TTS",
        "classification": PROVIDER_CLASSIFICATION_CLOUD,
        "capabilities": {
            "presetVoices": True,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
    "minimax": {
        "label": "MiniMax",
        "classification": PROVIDER_CLASSIFICATION_CLOUD,
        "capabilities": {
            "presetVoices": False,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
    "coqui": {
        "label": "Coqui",
        "classification": PROVIDER_CLASSIFICATION_LOCAL,
        "capabilities": {
            "presetVoices": False,
            "cloning": False,
            "promptDefinedVoice": False,
            "preview": False,
        },
    },
}


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
            config_path
            or os.path.join(os.path.dirname(__file__), "config.json")
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
            "default_provider": os.getenv(
                "TTS_DEFAULT_PROVIDER",
                os.getenv(
                    "CODEXIFY_TTS_PROVIDER",
                    os.getenv("CODEXIFY_TTS_BACKEND", TTS_BACKEND_QWEN3),
                ),
            ),
            "providers": {
                "elevenlabs": {"api_key": os.getenv("ELEVENLABS_API_KEY")},
                "google": {
                    "credentials_path": os.getenv(
                        "GOOGLE_APPLICATION_CREDENTIALS"
                    )
                },
                "local": {"enabled": True},
                "qwen3_tts": {"enabled": True},
                "local_openai_compatible": {
                    "base_url": os.getenv("CODEXIFY_LOCAL_VOICE_BASE_URL")
                    or os.getenv("CODEXIFY_LOCAL_TTS_BASE_URL")
                    or os.getenv("LOCAL_BASE_URL"),
                    "api_key": os.getenv("LOCAL_API_KEY", "local"),
                    "model": os.getenv("CODEXIFY_LOCAL_TTS_MODEL")
                    or os.getenv("LOCAL_TTS_MODEL"),
                },
                "minimax": {
                    "api_key": os.getenv("MINIMAX_API_KEY"),
                    "base_url": os.getenv("MINIMAX_TTS_URL"),
                    "enabled": bool(os.getenv("MINIMAX_API_KEY")),
                },
                "coqui": {
                    "model": os.getenv("COQUI_TTS_MODEL"),
                    "enabled": os.getenv("CODEXIFY_ENABLE_COQUI", "0")
                    .strip()
                    .lower()
                    in {"1", "true", "yes"},
                },
            },
        }

        env_default_provider = (
            os.getenv("TTS_DEFAULT_PROVIDER")
            or os.getenv("CODEXIFY_TTS_PROVIDER")
            or os.getenv("CODEXIFY_TTS_BACKEND")
            or TTS_BACKEND_QWEN3
        )

        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        # Environment/code defaults are authoritative for local runtime posture;
        # legacy config.json must not silently force the mock local provider.
        config["default_provider"] = env_default_provider

        return config

    def _register_providers(self) -> None:
        """Register configured TTS providers."""
        for name, provider_class in self._provider_classes().items():
            provider_config = self.config["providers"].get(name, {})

            # Skip if provider is explicitly disabled
            if not provider_config.get("enabled", True):
                continue

            try:
                # Initialize provider with its config
                if name == "elevenlabs":
                    provider = provider_class(
                        api_key=provider_config.get("api_key")
                    )
                elif name == "google":
                    provider = provider_class(
                        credentials_path=provider_config.get("credentials_path")
                    )
                elif name == "local_openai_compatible":
                    provider = provider_class(
                        base_url=provider_config.get("base_url"),
                        api_key=provider_config.get("api_key"),
                        model=provider_config.get("model"),
                    )
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

    def _provider_classes(self) -> dict[str, type[TTSProvider]]:
        classes: dict[str, type[TTSProvider]] = dict(PROVIDERS)
        classes["local_openai_compatible"] = LocalOpenAICompatibleProvider
        classes["minimax"] = MiniMaxProvider
        classes["coqui"] = CoquiProvider
        return classes

    def _provider_names(self) -> list[str]:
        names = set(_PROVIDER_SPECS)
        names.update(self.config.get("providers", {}).keys())
        names.update(self._provider_classes().keys())
        return sorted(names)

    def _cloud_providers_allowed(self) -> bool:
        return _env_flag("ALLOW_CLOUD_PROVIDERS", False)

    def _normalize_voices(self, voices: list[str] | None) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for voice in voices or []:
            value = str(voice or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _provider_label(self, provider_name: str) -> str:
        spec = _PROVIDER_SPECS.get(provider_name, {})
        return str(spec.get("label") or provider_name.replace("_", " ").title())

    def _provider_classification(self, provider_name: str) -> str:
        spec = _PROVIDER_SPECS.get(provider_name, {})
        return str(
            spec.get("classification") or PROVIDER_CLASSIFICATION_LOCAL
        )

    def _provider_capability_flags(
        self, provider_name: str
    ) -> dict[str, bool]:
        spec = _PROVIDER_SPECS.get(provider_name, {})
        base = dict(spec.get("capabilities") or {})
        return {
            "presetVoices": bool(base.get("presetVoices")),
            "cloning": bool(base.get("cloning")),
            "promptDefinedVoice": bool(base.get("promptDefinedVoice")),
            "preview": bool(base.get("preview")),
        }

    def _provider_status(
        self, provider_name: str
    ) -> tuple[str, str, list[str]]:
        provider_config = dict(
            self.config.get("providers", {}).get(provider_name, {})
        )
        classification = self._provider_classification(provider_name)
        provider = self.providers.get(provider_name)
        capability_flags = self._provider_capability_flags(provider_name)

        if (
            classification == PROVIDER_CLASSIFICATION_CLOUD
            and not self._cloud_providers_allowed()
        ):
            return (
                PROVIDER_STATE_DEGRADED,
                "Provider registered, but disabled under the current local-only beta posture.",
                [],
            )

        if not provider_config.get("enabled", True):
            return (
                PROVIDER_STATE_UNAVAILABLE,
                "Provider adapter is disabled in this environment.",
                [],
            )

        if provider is None:
            if provider_name == "local_openai_compatible" and not (
                provider_config.get("base_url")
            ):
                return (
                    PROVIDER_STATE_DEGRADED,
                    "Local provider is missing a base URL configuration.",
                    [],
                )
            if provider_name == "elevenlabs" and not (
                provider_config.get("api_key")
            ):
                return (
                    PROVIDER_STATE_DEGRADED,
                    "Provider credentials are missing.",
                    [],
                )
            if provider_name == "google" and not (
                provider_config.get("credentials_path")
            ):
                return (
                    PROVIDER_STATE_DEGRADED,
                    "Provider credentials are missing.",
                    [],
                )
            if provider_name == "minimax" and (
                not provider_config.get("api_key")
                or not provider_config.get("base_url")
            ):
                return (
                    PROVIDER_STATE_DEGRADED,
                    "Provider credentials or endpoint settings are missing.",
                    [],
                )
            return (
                PROVIDER_STATE_UNAVAILABLE,
                "Provider adapter is not configured in this environment.",
                [],
            )

        try:
            voices = self._normalize_voices(provider.list_voices())
        except AuthenticationError as exc:
            return (PROVIDER_STATE_DEGRADED, str(exc), [])
        except TTSError as exc:
            return (PROVIDER_STATE_DEGRADED, str(exc), [])
        except Exception as exc:
            return (PROVIDER_STATE_DEGRADED, str(exc), [])

        if capability_flags["presetVoices"] and not voices:
            return (
                PROVIDER_STATE_DEGRADED,
                "Provider is registered but exposes no selectable preset voices.",
                [],
            )

        return (
            PROVIDER_STATE_AVAILABLE,
            "Provider is available for Persona Studio voice selection.",
            voices,
        )

    def describe_provider(self, provider_name: str) -> dict[str, Any]:
        if provider_name not in self._provider_names():
            raise ProviderNotFoundError(f"Provider '{provider_name}' not found")

        state, status_detail, _voices = self._provider_status(provider_name)
        return {
            "providerId": provider_name,
            "label": self._provider_label(provider_name),
            "classification": self._provider_classification(provider_name),
            "state": state,
            "statusDetail": status_detail,
            "capabilities": self._provider_capability_flags(provider_name),
        }

    def describe_provider_registry(self) -> list[dict[str, Any]]:
        return [
            self.describe_provider(provider_name)
            for provider_name in self._provider_names()
        ]

    def list_selectable_voice_records(
        self, provider_name: str
    ) -> dict[str, Any]:
        provider_info = self.describe_provider(provider_name)
        state, status_detail, voices = self._provider_status(provider_name)
        voice_rows = [
            {
                "voiceId": voice_id,
                "label": voice_id,
                "kind": VOICE_KIND_PRESET,
                "previewSupported": bool(
                    provider_info["capabilities"]["preview"]
                ),
                "bindingSupported": True,
                "summary": None,
            }
            for voice_id in voices
        ]
        return {
            "providerId": provider_name,
            "state": state,
            "statusDetail": status_detail,
            "voices": voice_rows,
        }

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
        audio = provider.synthesize(text, voice)

        max_output = int(
            os.getenv("CODEXIFY_VOICE_OUTPUT_MAX_BYTES", str(15 * 1024 * 1024))
        )
        if len(audio) > max_output:
            raise TTSError(
                f"Audio output too large ({len(audio)} bytes > {max_output})"
            )
        return audio

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
        return self._normalize_voices(provider.list_voices())

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
