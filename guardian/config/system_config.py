"""
System Configuration Module
------------------------
Central configuration management for the Threadspace system.
Handles system-wide settings, paths, and operational parameters.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SystemConfig:
    """Manages system-wide configuration settings."""

    # Default configuration values
    DEFAULT_CONFIG = {
        "system": {
            "name": "Threadspace",
            "version": "0.1.0",
            "debug_mode": False,
            "log_level": "INFO",
        },
        "paths": {
            "base_dir": "",  # Will be set during initialization
            "plugins_dir": "plugins",
            "memory_dir": "memory",
            "logs_dir": "logs",
            "temp_dir": "temp",
        },
        "threads": {
            "health_check_interval": 10,  # seconds
            "heartbeat_timeout": 30,  # seconds
            "shutdown_timeout": 5.0,  # seconds
        },
        "memory": {
            "max_artifacts": 10000,
            "cleanup_threshold": 0.9,  # 90% full
            "min_confidence": 0.1,
        },
        "agents": {
            "required": ["Axis", "Vestige"],
            "optional": ["Echoform"],
            "startup_timeout": 30,  # seconds
        },
        "plugins": {"auto_discover": True, "allow_remote": False, "max_retries": 3},
        "security": {
            "require_authentication": True,
            "token_expiry": 3600,  # seconds
            "max_failed_attempts": 3,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize system configuration.

        Args:
            config_path: Optional path to configuration file
        """
        self.base_dir = Path(__file__).parent.parent
        self.config_path = config_path or self.base_dir / "config.json"
        self.config = self.DEFAULT_CONFIG.copy()
        self.config["paths"]["base_dir"] = str(self.base_dir)

        # Load custom configuration if it exists
        self._load_config()

        # Ensure required directories exist
        self._init_directories()

    def _load_config(self) -> None:
        """Load configuration from file if it exists."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    custom_config = json.load(f)
                    self._update_recursive(self.config, custom_config)
                logger.info(f"Loaded custom configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load custom configuration: {e}")

    def _update_recursive(
        self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]
    ) -> None:
        """
        Recursively update dictionary while preserving nested structure.

        Args:
            base_dict: Base dictionary to update
            update_dict: Dictionary with updates
        """
        for key, value in update_dict.items():
            if (
                key in base_dict
                and isinstance(base_dict[key], dict)
                and isinstance(value, dict)
            ):
                self._update_recursive(base_dict[key], value)
            else:
                base_dict[key] = value

    def _init_directories(self) -> None:
        """Create required system directories if they don't exist."""
        for dir_name, dir_path in self.config["paths"].items():
            if dir_name != "base_dir":
                full_path = Path(self.config["paths"]["base_dir"]) / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Initialized directory: {full_path}")

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get(self, *keys: str) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            *keys: Sequence of keys to traverse

        Returns:
            Configuration value

        Example:
            config.get('threads', 'health_check_interval')
        """
        value = self.config
        for key in keys:
            try:
                value = value[key]
            except (KeyError, TypeError):
                logger.error(f"Configuration key not found: {'.'.join(keys)}")
                return None
        return value

    def set(self, value: Any, *keys: str) -> None:
        """
        Set configuration value using dot notation.

        Args:
            value: Value to set
            *keys: Sequence of keys to traverse

        Example:
            config.set(20, 'threads', 'health_check_interval')
        """
        if not keys:
            return

        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        logger.info(f"Updated configuration: {'.'.join(keys)} = {value}")

    def get_path(self, *path_keys: str) -> Path:
        """
        Get full path for a configured directory.

        Args:
            *path_keys: Sequence of keys under 'paths' config

        Returns:
            Path object for the requested directory
        """
        base = Path(self.config["paths"]["base_dir"])
        for key in path_keys:
            if key in self.config["paths"]:
                base = base / self.config["paths"][key]
        return base

    def validate(self) -> bool:
        """
        Validate current configuration.

        Returns:
            bool: True if configuration is valid
        """
        try:
            # Check required paths
            for dir_name, dir_path in self.config["paths"].items():
                if dir_name != "base_dir":
                    full_path = Path(self.config["paths"]["base_dir"]) / dir_path
                    if not full_path.exists():
                        logger.error(f"Required directory missing: {full_path}")
                        return False

            # Check required agents
            if not self.config["agents"]["required"]:
                logger.error("No required agents specified")
                return False

            # Validate intervals
            if self.config["threads"]["health_check_interval"] <= 0:
                logger.error("Invalid health check interval")
                return False

            if self.config["threads"]["heartbeat_timeout"] <= 0:
                logger.error("Invalid heartbeat timeout")
                return False

            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
system_config = SystemConfig()

# Example usage:
if __name__ == "__main__":
    # Get configuration value
    health_interval = system_config.get("threads", "health_check_interval")
    print(f"Health check interval: {health_interval}")

    # Set configuration value
    system_config.set(15, "threads", "health_check_interval")

    # Get path
    plugins_path = system_config.get_path("plugins_dir")
    print(f"Plugins directory: {plugins_path}")

    # Validate configuration
    is_valid = system_config.validate()
    print(f"Configuration valid: {is_valid}")
