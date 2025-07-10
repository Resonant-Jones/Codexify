"""
Async Plugin Executor
------------------
Handles safe and rate-limited async plugin execution.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from guardian.utils.performance import rate_limited_plugin_runner
from guardian.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncPluginExecutor:
    """Safe async plugin execution manager."""

    def __init__(self):
        """Initialize plugin executor."""
        self.manifest_path = Path("guardian/plugins/plugin_manifest.json")
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load plugin manifest."""
        if not self.manifest_path.exists():
            self.manifest = {"plugins": {}}
            return

        try:
            with open(self.manifest_path) as f:
                self.manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load plugin manifest: {e}")
            self.manifest = {"plugins": {}}

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get plugin configuration from manifest.

        Args:
            plugin_name: Name of plugin

        Returns:
            Dict[str, Any]: Plugin configuration
        """
        return self.manifest.get("plugins", {}).get(plugin_name, {})

    def validate_plugin(self, plugin_name: str) -> bool:
        """
        Validate plugin can be executed.

        Args:
            plugin_name: Name of plugin

        Returns:
            bool: Whether plugin is valid
        """
        config = self.get_plugin_config(plugin_name)

        # Check if plugin declares side effects
        if config.get("declares_side_effects", False):
            if not Config.SAFE_MODE:
                logger.warning(
                    f"Plugin {plugin_name} has side effects "
                    "but SAFE_MODE is disabled"
                )

        # Check if plugin requires memory access
        if config.get("requires_memory_access", False):
            # Validate memory access permissions here
            pass

        return True

    async def execute_plugin(
        self, plugin_name: str, *args: Any, **kwargs: Any
    ) -> Optional[Any]:
        """
        Execute plugin with rate limiting.

        Args:
            plugin_name: Name of plugin
            *args: Plugin arguments
            **kwargs: Plugin keyword arguments

        Returns:
            Optional[Any]: Plugin result
        """
        if not self.validate_plugin(plugin_name):
            logger.error(f"Plugin {plugin_name} validation failed")
            return None

        # Get rate limit from manifest
        config = self.get_plugin_config(plugin_name)
        rate_limit = 2.0  # Default 2 calls/sec
        if "rate_limit" in config:
            try:
                rate_str = config["rate_limit"]
                rate_limit = float(rate_str.split("/")[0])
            except (ValueError, IndexError):
                logger.warning(
                    f"Invalid rate limit format for {plugin_name}: {config['rate_limit']}"
                )

        # Apply rate limiting decorator
        @rate_limited_plugin_runner(plugin_name, rate_limit)
        async def run_plugin(*a: Any, **kw: Any) -> Optional[Any]:
            try:
                # Import and execute plugin
                module_name = f"guardian.plugins.{plugin_name}"
                try:
                    module = __import__(module_name, fromlist=["execute"])
                    if hasattr(module, "execute"):
                        if asyncio.iscoroutinefunction(module.execute):
                            return await module.execute(*a, **kw)
                        else:
                            # Convert sync function to async
                            loop = asyncio.get_event_loop()
                            return await loop.run_in_executor(
                                None, module.execute, *a, **kw
                            )
                    else:
                        logger.error(f"Plugin {plugin_name} has no execute function")
                        return None
                except ImportError as e:
                    logger.error(f"Failed to import plugin {plugin_name}: {e}")
                    return None

            except Exception as e:
                logger.error(f"Failed to execute plugin {plugin_name}: {e}")
                return None

        return await run_plugin(*args, **kwargs)


# Global executor instance
plugin_executor = AsyncPluginExecutor()
