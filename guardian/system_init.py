"""
System Initialization
------------------
Main entry point for the Threadspace system.
Handles component initialization, health checks, and system startup.
"""

import logging
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.codex_awareness import CodexAwareness
from guardian.config.system_config import system_config
from guardian.metacognition import MetacognitionEngine
from guardian.plugin_loader import plugin_loader
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SystemInitializer:
    """
    System initialization and management interface for testing.
    Wraps ThreadspaceSystem to provide the interface expected by tests.
    """

    def __init__(self):
        self._system = ThreadspaceSystem()
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the system."""
        try:
            success = self._system.initialize()
            self._initialized = success
            return success
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def cleanup(self) -> bool:
        """Clean up system resources."""
        try:
            self._system.shutdown()
            return True
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            status = self._system.get_system_status()
            return {
                "status": (
                    "healthy" if status["health_status"] == "nominal" else "unhealthy"
                ),
                "initialized": status["initialized"],
                "components": status["components"],
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {"status": "error", "error": str(e)}


class ThreadspaceSystem:
    """
    Main system class that coordinates all Threadspace components.
    Handles initialization, shutdown, and system-wide operations.
    """

    def __init__(self):
        """Initialize the system components in the correct order."""
        # Initialize core components
        self.thread_manager = ThreadManager()
        self.codex_awareness = CodexAwareness()
        self.metacognition = MetacognitionEngine(thread_manager=self.thread_manager)
        self.plugin_loader = plugin_loader  # Expose plugin loader

        # Update metacognition with codex reference
        self.metacognition.codex_awareness = self.codex_awareness

        # Initialize agents with dependencies
        self.thread_manager.initialize_agents(
            codex=self.codex_awareness, metacognition=self.metacognition
        )

        self.shutdown_event = threading.Event()
        self.initialized = False
        self.startup_timestamp = datetime.utcnow()
        self.health_status = "initializing"

    def initialize(self) -> bool:
        """
        Initialize all system components.

        Returns:
            bool: True if initialization was successful
        """
        try:
            logger.info("Starting Threadspace system initialization...")

            # 1. Validate system configuration
            if not system_config.validate():
                raise RuntimeError("System configuration validation failed")

            # 2. Initialize core components
            self._init_core_components()

            # 3. Load plugins
            self._init_plugins()

            # 4. Register signal handlers
            self._register_signal_handlers()

            # 5. Perform initial health check
            initial_health = self._check_system_health()
            if initial_health["status"] == "error":
                raise RuntimeError(
                    f"System health check failed: {initial_health['message']}"
                )

            # 6. Record initialization success
            self.initialized = True
            self.startup_timestamp = datetime.utcnow()
            self.health_status = initial_health["status"]

            logger.info("Threadspace system initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.shutdown()
            return False

    def _init_core_components(self) -> None:
        """Initialize core system components."""
        logger.info("Initializing core components...")

        # Initialize required directories
        for dir_name in ["logs", "data", "temp"]:
            path = system_config.get_path(f"{dir_name}_dir")
            path.mkdir(parents=True, exist_ok=True)

        # Start thread manager monitoring
        self.thread_manager.register_thread(
            "system_monitor", threading.current_thread(), "core"
        )

        # Initialize memory system
        memory_status = self.codex_awareness.query_memory(
            query="system_health", limit=1
        )
        if not memory_status:
            logger.info("Initializing system memory...")
            self.codex_awareness.store_memory(
                content={
                    "type": "system_health",
                    "status": "initialized",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="system",
                tags=["system", "health", "initialization"],
                confidence=1.0,
            )

    def _init_plugins(self) -> None:
        """Initialize plugin system and load plugins."""
        logger.info("Initializing plugin system...")

        # Load all plugins
        plugin_loader.load_all_plugins()

        # Check plugin health
        plugin_health = plugin_loader.check_all_plugin_health()
        for plugin_name, health in plugin_health.items():
            if health["status"] == "error":
                logger.warning(
                    f"Plugin {plugin_name} health check failed: " f"{health['message']}"
                )

    def _register_signal_handlers(self) -> None:
        """Register system signal handlers."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _check_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.

        Returns:
            Dict containing health status information
        """
        # Check thread health
        thread_health = self.thread_manager.health_check()

        # Check plugin health
        plugin_health = plugin_loader.check_all_plugin_health()

        # Check memory system
        try:
            self.codex_awareness.query_memory("health_check", limit=1)
            memory_status = "nominal"
        except Exception as e:
            logger.error(f"Memory system health check failed: {e}")
            memory_status = "error"

        # Determine overall status
        if (
            thread_health["status"] == "error"
            or memory_status == "error"
            or any(h["status"] == "error" for h in plugin_health.values())
        ):
            status = "error"
        elif (
            thread_health["status"] == "warning"
            or memory_status == "warning"
            or any(h["status"] == "warning" for h in plugin_health.values())
        ):
            status = "warning"
        else:
            status = "nominal"

        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "threads": thread_health,
                "plugins": plugin_health,
                "memory": memory_status,
            },
            "message": f"System health status: {status}",
        }

    def shutdown(self) -> None:
        """Perform graceful system shutdown."""
        if not self.initialized:
            return

        logger.info("Initiating system shutdown...")

        try:
            # Signal shutdown
            self.shutdown_event.set()

            # Stop all plugins
            for plugin_name in plugin_loader.plugins:
                plugin_loader.disable_plugin(plugin_name)

            # Stop thread manager
            self.thread_manager.shutdown()

            # Record shutdown in memory
            self.codex_awareness.store_memory(
                content={
                    "type": "system_event",
                    "event": "shutdown",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="system",
                tags=["system", "shutdown"],
                confidence=1.0,
            )

            logger.info("System shutdown completed successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        finally:
            self.initialized = False

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status.

        Returns:
            Dict containing system status information
        """
        return {
            "initialized": self.initialized,
            "startup_time": (
                self.startup_timestamp.isoformat() if self.startup_timestamp else None
            ),
            "health_status": self.health_status,
            "uptime": (
                str(datetime.utcnow() - self.startup_timestamp)
                if self.startup_timestamp
                else None
            ),
            "components": {
                "thread_manager": bool(self.thread_manager),
                "codex_awareness": bool(self.codex_awareness),
                "metacognition": bool(self.metacognition),
                "plugin_count": len(plugin_loader.plugins),
            },
        }


# Global system instance
threadspace = ThreadspaceSystem()


def main():
    """Main entry point for the system."""
    if threadspace.initialize():
        logger.info("Threadspace system is ready")

        # Keep the main thread alive
        try:
            while not threadspace.shutdown_event.is_set():
                threadspace.shutdown_event.wait(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            threadspace.shutdown()
    else:
        logger.error("System initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
