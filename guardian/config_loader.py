"""
Guardian Config Loader
-------------------
Loads and manages Guardian configuration from environment and files.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import logging
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages Guardian configuration."""

    def __init__(
        self, config_path: Optional[str] = None, env_file: Optional[str] = None
    ):
        """
        Initialize config loader.

        Args:
            config_path: Path to guardian.yaml config file
            env_file: Path to .env file
        """
        # Load environment variables
        load_dotenv(env_file)

        # Load config file
        self.config = self._load_config(config_path)

        # Merge with environment variables
        self._merge_environment()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            dict: Configuration dictionary
        """
        config = {
            "core": {"plugins_dir": "plugins", "conversation_token_limit": 90000},
            "plugins": {"enabled": ["tts", "codexify"]},
            "tts": {
                "default_provider": "local",
                "output_dir": "tts_output",
                "providers": {
                    "elevenlabs": {"api_key": None},
                    "google": {"credentials_path": None},
                    "local": {"enabled": True},
                },
            },
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self._deep_update(config, file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        return config

    def _merge_environment(self) -> None:
        """Merge environment variables into config."""
        # Core settings
        if token_limit := os.getenv("GUARDIAN_TOKEN_LIMIT"):
            self.config["core"]["conversation_token_limit"] = int(token_limit)

        # TTS Provider settings
        if api_key := os.getenv("ELEVENLABS_API_KEY"):
            self.config["tts"]["providers"]["elevenlabs"]["api_key"] = api_key

        if creds_path := os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            self.config["tts"]["providers"]["google"]["credentials_path"] = creds_path

    def _deep_update(self, base: Dict, update: Dict) -> None:
        """
        Recursively update a dictionary.

        Args:
            base: Base dictionary to update
            update: Dictionary with updates
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in base:
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            value = self.config
            for part in key.split("."):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (dot notation supported)
            value: Value to set
        """
        parts = key.split(".")
        config = self.config

        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        config[parts[-1]] = value

    @property
    def plugins_dir(self) -> str:
        """Get plugins directory path."""
        return self.get("core.plugins_dir", "plugins")

    @property
    def enabled_plugins(self) -> list:
        """Get list of enabled plugins."""
        return self.get("plugins.enabled", [])
