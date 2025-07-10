"""
Plugin Base Contract
------------------
Defines the base contract that all Guardian plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PluginBase(ABC):
    """Base class for all Guardian plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the plugin's unique name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Get the plugin's version."""
        pass

    @property
    def description(self) -> str:
        """Get the plugin's description."""
        return "No description provided"

    @abstractmethod
    def activate(self, core_services: Dict[str, Any]) -> None:
        """
        Activate the plugin with core services.

        Args:
            core_services: Dictionary containing core Guardian services:
                - memory_os: MemoryOS instance for conversation management
                - codemap: CodemapService for project navigation
                - config: ConfigLoader for environment and settings

        Raises:
            PluginActivationError: If activation fails
        """
        pass

    @abstractmethod
    def register_cli(self, cli: Any) -> None:
        """
        Register plugin's CLI commands.

        Args:
            cli: CLI registry to add commands to
        """
        pass

    def shutdown(self) -> None:
        """
        Clean up plugin resources before shutdown.
        Override if cleanup is needed.
        """
        pass


class PluginError(Exception):
    """Base class for plugin-related errors."""

    pass


class PluginActivationError(PluginError):
    """Raised when plugin activation fails."""

    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found."""

    pass


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""

    pass
