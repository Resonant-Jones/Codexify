"""
Guardian Plugin Host
-----------------
Discovers, validates, and manages Guardian plugins.
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .plugins.plugin_base import (
    PluginBase,
    PluginError,
    PluginActivationError,
    PluginNotFoundError,
    PluginValidationError,
)

# Configure logging
logger = logging.getLogger(__name__)


class PluginHost:
    """
    Manages Guardian plugin lifecycle and registration.

    The Plugin Host is responsible for:
    - Discovering plugins in the plugins directory
    - Validating plugin implementations
    - Managing plugin lifecycle (activation, shutdown)
    - Providing plugin status and information
    """

    def __init__(
        self,
        plugins_dir: str = "plugins",
        manifest_path: Optional[str] = None,
        core_services: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Plugin Host.

        Args:
            plugins_dir: Directory containing plugin folders
            manifest_path: Path to plugins.json manifest
            core_services: Dictionary of core services to pass to plugins
        """
        self.plugins_dir = Path(plugins_dir)
        self.manifest_path = manifest_path or self.plugins_dir / "plugins.json"
        self.core_services = core_services or {}

        # Plugin registry
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_states: Dict[str, bool] = {}  # Tracks active state

        # Load plugin manifest
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Load plugin manifest file."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load plugin manifest: {e}")
        return {"enabled_plugins": []}

    def _save_manifest(self) -> None:
        """Save current plugin manifest."""
        try:
            os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
            with open(self.manifest_path, "w") as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin manifest: {e}")

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in plugins directory.

        Returns:
            list: List of discovered plugin names
        """
        discovered = []

        if not os.path.exists(self.plugins_dir):
            return discovered

        for item in os.listdir(self.plugins_dir):
            plugin_dir = os.path.join(self.plugins_dir, item)
            if os.path.isdir(plugin_dir):
                plugin_file = os.path.join(plugin_dir, "plugin.py")
                if os.path.exists(plugin_file):
                    discovered.append(item)

        return discovered

    def load_plugin(self, plugin_name: str) -> Optional[Type[PluginBase]]:
        """
        Load a plugin module and return its Plugin class.

        Args:
            plugin_name: Name of plugin to load

        Returns:
            Plugin class if successful, None otherwise

        Raises:
            PluginNotFoundError: If plugin directory or file not found
            PluginValidationError: If plugin fails validation
        """
        plugin_dir = os.path.join(self.plugins_dir, plugin_name)
        plugin_file = os.path.join(plugin_dir, "plugin.py")

        if not os.path.exists(plugin_file):
            raise PluginNotFoundError(f"Plugin file not found: {plugin_file}")

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                f"guardian.plugins.{plugin_name}", plugin_file
            )
            if not spec or not spec.loader:
                raise PluginValidationError(
                    f"Failed to load plugin spec: {plugin_name}"
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Plugin class
            plugin_class = None
            for item in dir(module):
                if item != "PluginBase":  # Skip the base class
                    obj = getattr(module, item)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, PluginBase)
                        and obj != PluginBase
                    ):
                        plugin_class = obj
                        break

            if not plugin_class:
                raise PluginValidationError(f"No Plugin class found in {plugin_file}")

            return plugin_class

        except Exception as e:
            raise PluginValidationError(f"Failed to load plugin {plugin_name}: {e}")

    def activate_plugin(self, plugin_name: str) -> None:
        """
        Activate a plugin.

        Args:
            plugin_name: Name of plugin to activate

        Raises:
            PluginError: If activation fails
        """
        try:
            # Load plugin class
            plugin_class = self.load_plugin(plugin_name)
            if not plugin_class:
                raise PluginActivationError(f"Failed to load plugin: {plugin_name}")

            # Instantiate plugin
            plugin = plugin_class()

            # Activate plugin
            plugin.activate(self.core_services)

            # Register plugin
            self.plugins[plugin_name] = plugin
            self.plugin_states[plugin_name] = True

            logger.info(f"Activated plugin: {plugin_name} v{plugin.version}")

        except Exception as e:
            raise PluginActivationError(f"Failed to activate {plugin_name}: {e}")

    def deactivate_plugin(self, plugin_name: str) -> None:
        """
        Deactivate a plugin.

        Args:
            plugin_name: Name of plugin to deactivate
        """
        if plugin_name in self.plugins:
            try:
                self.plugins[plugin_name].shutdown()
                self.plugin_states[plugin_name] = False
                logger.info(f"Deactivated plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error deactivating {plugin_name}: {e}")

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get information about a plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            dict: Plugin information
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return {
                "name": plugin_name,
                "status": "not_loaded",
                "error": "Plugin not loaded",
            }

        return {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "status": "active" if self.plugin_states.get(plugin_name) else "inactive",
        }

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        Get information about all plugins.

        Returns:
            list: List of plugin information dictionaries
        """
        return [self.get_plugin_info(name) for name in self.discover_plugins()]

    def register_plugin_cli_commands(self, cli: Any) -> None:
        """
        Register CLI commands for all active plugins.

        Args:
            cli: CLI registry to add commands to
        """
        for plugin in self.plugins.values():
            try:
                plugin.register_cli(cli)
            except Exception as e:
                logger.error(f"Failed to register CLI for {plugin.name}: {e}")

    def shutdown(self) -> None:
        """Shutdown all active plugins."""
        for plugin_name in list(self.plugins.keys()):
            self.deactivate_plugin(plugin_name)
