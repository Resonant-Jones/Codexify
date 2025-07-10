"""
Guardian TTS Plugin
----------------
Text-to-Speech plugin for Guardian.
"""

import logging
from typing import Any, Dict

from ...plugins.plugin_base import PluginBase, PluginActivationError
from ...tts.tts_manager import TTSManager

# Configure logging
logger = logging.getLogger(__name__)


class TTSPlugin(PluginBase):
    """TTS Plugin implementation."""

    @property
    def name(self) -> str:
        """Get plugin name."""
        return "tts"

    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Get plugin description."""
        return "Text-to-Speech synthesis with multiple provider support"

    def __init__(self):
        """Initialize TTS plugin."""
        self.tts_manager = None

    def activate(self, core_services: Dict[str, Any]) -> None:
        """
        Activate TTS plugin.

        Args:
            core_services: Core Guardian services

        Raises:
            PluginActivationError: If activation fails
        """
        try:
            config = core_services.get("config", {})

            # Initialize TTS manager with config
            self.tts_manager = TTSManager(config_path=config.get("tts_config_path"))

            logger.info(
                f"TTS Plugin activated with providers: {self.tts_manager.list_providers()}"
            )

        except Exception as e:
            raise PluginActivationError(f"Failed to activate TTS plugin: {e}")

    def register_cli(self, cli: Any) -> None:
        """
        Register TTS CLI commands.

        Args:
            cli: CLI registry
        """

        @cli.command("tts:speak")
        def tts_speak(
            text: str = None,
            provider: str = None,
            voice: str = None,
            output: str = None,
            list_voices: bool = False,
            list_providers: bool = False,
        ):
            """Synthesize text to speech."""
            if not self.tts_manager:
                print("TTS plugin not properly initialized")
                return

            try:
                # Handle informational commands
                if list_providers:
                    print("\nAvailable TTS providers:")
                    providers = self.tts_manager.list_providers()
                    for provider in providers:
                        if provider == self.tts_manager.default_provider:
                            print(f"  - {provider} (default)")
                        else:
                            print(f"  - {provider}")
                    return

                if list_voices:
                    provider_name = provider or self.tts_manager.default_provider
                    print(f"\nAvailable voices for provider '{provider_name}':")
                    voices = self.tts_manager.list_voices(provider_name)
                    for voice in voices:
                        print(f"  - {voice}")
                    return

                # Handle synthesis
                if not text:
                    print("Error: --text is required for speech synthesis")
                    return

                if not voice:
                    print("Error: --voice is required for speech synthesis")
                    return

                print(
                    f"\nSynthesizing speech using provider '{provider or 'default'}'..."
                )
                audio_data = self.tts_manager.synthesize(
                    text=text, voice=voice, provider_name=provider
                )

                # Save audio file
                self.tts_manager.save_audio(audio_data, output)
                print(f"Audio saved to: {output}")

            except Exception as e:
                print(f"Error: {str(e)}")

    def shutdown(self) -> None:
        """Clean up TTS plugin resources."""
        logger.info("Shutting down TTS plugin")
