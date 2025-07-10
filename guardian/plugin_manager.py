"""
Plugin Manager Module
------------------
Enhanced plugin management with safeguards and rate limiting.
"""

import asyncio
import importlib.util
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from guardian.config import Config
from guardian.utils.safeguard import safe_plugin_execution, throttle, rate_limited

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class SafePlugin:
    """Plugin wrapper with execution safeguards."""

    def __init__(self, name: str, module: Any, metadata: Dict[str, Any], path: Path):
        self.name = name
        self.module = module
        self.metadata = metadata
        self.path = path
        self.enabled = True
        self.last_health_check: Optional[Dict[str, Any]] = None
        self.error_count = 0
        self.active_calls = 0
        self.last_call = 0.0
        self.lock = asyncio.Lock()

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

    @safe_plugin_execution()
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute plugin method with safeguards."""
        async with self.lock:
            try:
                self.active_calls += 1
                self.last_call = datetime.now().timestamp()

                if hasattr(self.module, "execute"):
                    return await self.module.execute(*args, **kwargs)
                return None

            except Exception as e:
                self.error_count += 1
                logger.error(f"Plugin {self.name} execution failed: {e}")
                raise
            finally:
                self.active_calls -= 1


class SafePluginManager:
    """Plugin manager with safety controls."""

    def __init__(self):
        self.plugins: Dict[str, SafePlugin] = {}
        self.plugin_dir = Path(Config().PLUGIN_DIR)
        self.manifest_path = self.plugin_dir / "plugin_manifest.json"
        self.active_plugins: Set[str] = set()
        self.lock = asyncio.Lock()

    @throttle(rate=1.0)  # Limit plugin discovery
    async def discover_plugins(self) -> List[Path]:
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

    @rate_limited("plugin_load", rate=2.0)
    async def load_plugin(self, plugin_path: Path) -> Optional[SafePlugin]:
        """
        Load a plugin with rate limiting.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Optional[SafePlugin]: Loaded plugin or None
        """
        try:
            # Load metadata
            with open(plugin_path / "plugin.json") as f:
                metadata = json.load(f)

            # Validate rate limits
            if "rate_limit" in metadata:
                try:
                    rate = float(metadata["rate_limit"].split("/")[0])
                    if rate > Config().DEFAULT_RATE_LIMIT:
                        logger.warning(
                            f"Plugin {metadata['name']} requested rate {rate} "
                            f"exceeding limit {Config().DEFAULT_RATE_LIMIT}"
                        )
                        rate = Config().DEFAULT_RATE_LIMIT
                except (ValueError, IndexError):
                    rate = Config().DEFAULT_RATE_LIMIT
            else:
                rate = Config().DEFAULT_RATE_LIMIT

            # Load module
            module_path = plugin_path / "main.py"
            if not module_path.exists():
                raise PluginError(f"No main.py found in {plugin_path}")

            spec = importlib.util.spec_from_file_location(metadata["name"], module_path)
            if not spec or not spec.loader:
                raise PluginError("Failed to create module spec")

            module = importlib.util.module_from_spec(spec)
            sys.modules[metadata["name"]] = module
            spec.loader.exec_module(module)

            # Create safe plugin
            plugin = SafePlugin(
                name=metadata["name"],
                module=module,
                metadata=metadata,
                path=plugin_path,
            )

            # Initialize with timeout
            try:
                async with asyncio.timeout(Config().PLUGIN_TIMEOUT):
                    if hasattr(module, "init_plugin"):
                        await module.init_plugin()
            except asyncio.TimeoutError:
                raise PluginError("Plugin initialization timed out")

            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return None

    @throttle(rate=0.2)  # Limit full reloads
    async def load_all_plugins(self) -> None:
        """Load all plugins with rate limiting."""
        async with self.lock:
            paths = await self.discover_plugins()

            for path in paths:
                if (
                    Config().SAFE_MODE
                    and len(self.plugins) >= Config().MAX_CONCURRENT_PLUGINS
                ):
                    logger.warning("Maximum plugin limit reached in safe mode")
                    break

                plugin = await self.load_plugin(path)
                if plugin:
                    self.plugins[plugin.name] = plugin
                    logger.info(f"Loaded plugin: {plugin.name}")

            await self.update_manifest()

    @throttle(rate=1.0)
    async def update_manifest(self) -> None:
        """Update plugin manifest with rate limiting."""
        try:
            manifest = {
                "last_updated": datetime.utcnow().isoformat(),
                "safe_mode": Config().SAFE_MODE,
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

            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")

    @rate_limited("health_check", rate=0.1)
    async def check_plugin_health(self, plugin_name: str) -> Dict[str, Any]:
        """
        Check plugin health with rate limiting.

        Args:
            plugin_name: Name of plugin to check

        Returns:
            Dict with health status
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return {"status": "error", "message": f"Plugin {plugin_name} not found"}

        try:
            if hasattr(plugin.module, "health_check"):
                health = await plugin.module.health_check()
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


# Global manager instance
plugin_manager = SafePluginManager()
