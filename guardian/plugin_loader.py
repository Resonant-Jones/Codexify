"""
Plugin Loader Module
-----------------
Handles dynamic loading, validation, and management of Threadspace plugins.
Maintains the plugin manifest and ensures proper plugin lifecycle management.
"""

import importlib.util
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from guardian.config import system_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginInterface:
    """Required interface that all plugins must implement."""

    REQUIRED_METADATA = {
        "name",
        "version",
        "description",
        "author",
        "dependencies",
        "capabilities",
    }

    REQUIRED_METHODS = {"init_plugin", "get_metadata"}

    OPTIONAL_METHODS = {"cleanup", "health_check"}


class Plugin:
    """Represents a loaded plugin instance."""

    def __init__(self, name: str, module: Any, metadata: Dict[str, Any], path: Path):
        self.name = name
        self.module = module
        self.metadata = metadata
        self.path = path
        self.enabled = True
        self.last_health_check: Optional[Dict[str, Any]] = None
        self.error_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert plugin to dictionary representation."""
        return {
            "name": self.name,
            "version": self.metadata["version"],
            "description": self.metadata["description"],
            "author": self.metadata["author"],
            "capabilities": self.metadata["capabilities"],
            "enabled": self.enabled,
            "health": self.last_health_check,
            "error_count": self.error_count,
            "path": str(self.path),
        }


class PluginLoader:
    """
    Manages plugin discovery, loading, and lifecycle management.
    Maintains the plugin manifest and handles plugin health monitoring.
    """

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        # Ensure this path is correct relative to where PluginLoader is instantiated
        self.plugin_dir = Path("plugins")
        self.manifest_path = self.plugin_dir / "plugin_manifest.json"
        # Create plugin_manifest.json if it doesn't exist
        if not self.manifest_path.exists():
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.manifest_path, "w") as f:
                json.dump({}, f)
        self.max_retries = system_config.get("plugins", "max_retries")

    def discover_plugins(self) -> List[Path]:
        """
        Scan plugin directory for available plugins.

        Returns:
            List[Path]: Paths to discovered plugin directories
        """
        plugin_paths = []
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "plugin.json").exists():
                plugin_paths.append(item)
        return plugin_paths

    def load_plugin(self, plugin_path: Path) -> Optional[Plugin]:
        """
        Load a plugin from the specified path.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            Optional[Plugin]: Loaded plugin instance or None if loading failed
        """
        try:
            # Load plugin metadata
            with open(plugin_path / "plugin.json", "r") as f:
                metadata = json.load(f)

            # Validate metadata
            if not self._validate_metadata(metadata):
                raise PluginError("Invalid plugin metadata")

            # Load plugin module
            module_path = plugin_path / "__init__.py"
            if not module_path.exists():
                module_path = plugin_path / "main.py"

            if not module_path.exists():
                raise PluginError("No plugin entry point found")

            spec = importlib.util.spec_from_file_location(metadata["name"], module_path)
            if not spec or not spec.loader:
                raise PluginError("Failed to create module spec")

            module = importlib.util.module_from_spec(spec)
            sys.modules[metadata["name"]] = module
            spec.loader.exec_module(module)

            # Validate interface
            if not self._validate_interface(module):
                raise PluginError("Plugin does not implement required interface")

            # Initialize plugin
            if not module.init_plugin():
                raise PluginError("Plugin initialization failed")

            plugin = Plugin(
                name=metadata["name"],
                module=module,
                metadata=metadata,
                path=plugin_path,
            )

            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return None

    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Validate plugin metadata.

        Args:
            metadata: Plugin metadata dictionary

        Returns:
            bool: True if metadata is valid
        """
        return all(key in metadata for key in PluginInterface.REQUIRED_METADATA)

    def _validate_interface(self, module: Any) -> bool:
        """
        Validate that module implements required interface.

        Args:
            module: Plugin module to validate

        Returns:
            bool: True if interface is valid
        """
        return all(
            hasattr(module, method) for method in PluginInterface.REQUIRED_METHODS
        )

    def load_all_plugins(self) -> None:
        """Discover and load all available plugins."""
        plugin_paths = self.discover_plugins()

        for path in plugin_paths:
            plugin = self.load_plugin(path)
            if plugin:
                self.plugins[plugin.name] = plugin
                logger.info(f"Loaded plugin: {plugin.name}")

        self.update_manifest()

    def update_manifest(self) -> None:
        """Update the plugin manifest in README.md."""
        try:
            # Read existing README content
            with open(self.manifest_path, "r") as f:
                content = f.read()

            # Prepare manifest data
            manifest = {
                "last_updated": datetime.utcnow().isoformat(),
                "active_plugins": {
                    name: plugin.to_dict()
                    for name, plugin in self.plugins.items()
                    if plugin.enabled
                },
                "disabled_plugins": {
                    name: plugin.to_dict()
                    for name, plugin in self.plugins.items()
                    if not plugin.enabled
                },
            }

            # Find the manifest section and replace it
            start_marker = "```json"
            end_marker = "```"
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker, start_idx + len(start_marker))

            if start_idx != -1 and end_idx != -1:
                new_content = (
                    content[: start_idx + len(start_marker)]
                    + "\n"
                    + json.dumps(manifest, indent=2)
                    + "\n"
                    + content[end_idx:]
                )

                with open(self.manifest_path, "w") as f:
                    f.write(new_content)

                logger.info("Updated plugin manifest")

        except Exception as e:
            logger.error(f"Failed to update plugin manifest: {e}")

    def check_plugin_health(self, plugin_name: str) -> Dict[str, Any]:
        """
        Check health status of a specific plugin.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            Dict containing health status information
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return {"status": "error", "message": f"Plugin {plugin_name} not found"}

        if not plugin.enabled:
            return {
                "status": "disabled",
                "message": f"Plugin {plugin_name} is disabled.",
            }

        try:
            if hasattr(plugin.module, "health_check"):
                health = plugin.module.health_check()
                plugin.last_health_check = health
                return health

            return {"status": "unknown", "message": "Health check not implemented"}

        except Exception as e:
            plugin.error_count += 1
            health = {
                "status": "error",
                "message": str(e),
                "error_count": plugin.error_count,
            }
            plugin.last_health_check = health
            return health

    def check_all_plugin_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health status of all plugins.

        Returns:
            Dict mapping plugin names to their health status
        """
        return {name: self.check_plugin_health(name) for name in self.plugins}

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a disabled plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            bool: True if plugin was enabled successfully
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return False

        if plugin.enabled:
            return True

        try:
            if plugin.module.init_plugin():
                plugin.enabled = True
                plugin.error_count = 0
                self.update_manifest()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to enable plugin {plugin_name}: {e}")
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable an active plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            bool: True if plugin was disabled successfully
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return False

        if not plugin.enabled:
            return True

        try:
            if hasattr(plugin.module, "cleanup"):
                plugin.module.cleanup()

            plugin.enabled = False
            self.update_manifest()
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to retrieve

        Returns:
            Optional[Plugin]: Plugin instance if found, None otherwise
        """
        return self.plugins.get(plugin_name)

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            bool: True if plugin was reloaded successfully
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return False

        try:
            # Disable plugin
            if plugin.enabled:
                self.disable_plugin(plugin_name)

            # Reload module
            new_plugin = self.load_plugin(plugin.path)
            if new_plugin:
                self.plugins[plugin_name] = new_plugin
                self.update_manifest()
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False


# Global plugin loader instance
plugin_loader = PluginLoader()

# Example usage:
if __name__ == "__main__":
    # Load all plugins
    plugin_loader.load_all_plugins()

    # Check plugin health
    health_status = plugin_loader.check_all_plugin_health()
    print("\nPlugin Health Status:")
    print(json.dumps(health_status, indent=2))
