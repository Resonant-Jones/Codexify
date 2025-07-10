"""
System Health Monitor
------------------
Monitors and enforces system resource limits.
"""

import asyncio
import logging
import os
import psutil
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from guardian.config import Config
from guardian.utils.safe_logger import system_logger
from guardian.utils.safeguard import throttle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """System resource usage snapshot."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    open_files: int
    thread_count: int
    active_plugins: int
    event_queue_size: int


class SystemMonitor:
    """Monitors and manages system health."""

    def __init__(self):
        """Initialize system monitor."""
        self.process = psutil.Process()
        self.start_time = time.time()
        self.warning_count = 0
        self.last_warning = 0.0
        self.history: List[ResourceUsage] = []
        self._monitor_task: Optional[asyncio.Task] = None

        # Resource limits
        self.limits = {
            "cpu_percent": 80.0,  # Max CPU usage
            "memory_percent": 75.0,  # Max memory usage
            "disk_percent": 90.0,  # Max disk usage
            "max_files": 1000,  # Max open files
            "max_threads": 100,  # Max threads
            "warning_threshold": 3,  # Warnings before action
            "warning_interval": 300.0,  # 5 minutes between warnings
        }

    @throttle(rate=1.0)  # Limit checks to once per second
    async def check_health(self) -> ResourceUsage:
        """
        Check current system health.

        Returns:
            ResourceUsage: Current resource usage
        """
        try:
            cpu_percent = self.process.cpu_percent()
            memory_percent = self.process.memory_percent()

            # Get disk usage for current directory
            disk = psutil.disk_usage(os.getcwd())
            disk_percent = disk.percent

            # Count open files and threads
            open_files = len(self.process.open_files())
            thread_count = self.process.num_threads()

            # Get plugin and event info
            from guardian.plugin_manager import plugin_manager

            active_plugins = len(
                [p for p in plugin_manager.plugins.values() if p.enabled]
            )

            # Approximate event queue size
            event_queue_size = len(asyncio.all_tasks())

            usage = ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_percent,
                open_files=open_files,
                thread_count=thread_count,
                active_plugins=active_plugins,
                event_queue_size=event_queue_size,
            )

            # Keep history
            self.history.append(usage)
            if len(self.history) > 1000:  # Limit history
                self.history = self.history[-1000:]

            return usage

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise

    async def enforce_limits(self, usage: ResourceUsage) -> None:
        """
        Enforce resource limits.

        Args:
            usage: Current resource usage
        """
        warnings = []

        # Check CPU usage
        if usage.cpu_percent > self.limits["cpu_percent"]:
            warnings.append(f"High CPU usage: {usage.cpu_percent:.1f}%")

        # Check memory usage
        if usage.memory_percent > self.limits["memory_percent"]:
            warnings.append(f"High memory usage: {usage.memory_percent:.1f}%")

        # Check disk usage
        if usage.disk_usage_percent > self.limits["disk_percent"]:
            warnings.append(f"High disk usage: {usage.disk_usage_percent:.1f}%")

        # Check open files
        if usage.open_files > self.limits["max_files"]:
            warnings.append(f"Too many open files: {usage.open_files}")

        # Check thread count
        if usage.thread_count > self.limits["max_threads"]:
            warnings.append(f"Too many threads: {usage.thread_count}")

        if warnings:
            self.warning_count += 1
            current_time = time.time()

            # Log warnings if enough time has passed
            if current_time - self.last_warning >= self.limits["warning_interval"]:
                await system_logger.warning(
                    "Resource warning", warnings=warnings, usage=vars(usage)
                )
                self.last_warning = current_time

            # Take action if too many warnings
            if self.warning_count >= self.limits["warning_threshold"]:
                await self._handle_resource_pressure(usage)
        else:
            self.warning_count = 0

    async def _handle_resource_pressure(self, usage: ResourceUsage) -> None:
        """
        Handle excessive resource usage.

        Args:
            usage: Current resource usage
        """
        await system_logger.error(
            "Resource limits exceeded - taking action", usage=vars(usage)
        )

        from guardian.plugin_manager import plugin_manager

        # Disable non-essential plugins
        for plugin in plugin_manager.plugins.values():
            if plugin.enabled and "essential" not in plugin.metadata.get("tags", []):
                await plugin_manager.disable_plugin(plugin.name)

        # Force garbage collection
        import gc

        gc.collect()

        # Clear caches
        from guardian.cache import CacheConfig

        if CacheConfig.CACHE_DIR.exists():
            for cache_file in CacheConfig.CACHE_DIR.glob("*.jsonl"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to clear cache file {cache_file}: {e}")

        # Reset warning count
        self.warning_count = 0

    async def start_monitoring(self) -> None:
        """Start background monitoring."""

        async def monitor():
            while True:
                try:
                    usage = await self.check_health()
                    await self.enforce_limits(usage)
                    await asyncio.sleep(1.0)  # Check every second
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    await asyncio.sleep(5.0)  # Back off on error

        self._monitor_task = asyncio.create_task(monitor())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def get_health_report(self) -> Dict[str, any]:
        """
        Generate health report.

        Returns:
            Dict containing health statistics
        """
        if not self.history:
            return {"status": "No data available"}

        recent = self.history[-10:]  # Last 10 readings

        return {
            "status": "healthy" if self.warning_count == 0 else "warning",
            "uptime": time.time() - self.start_time,
            "warning_count": self.warning_count,
            "current_usage": vars(self.history[-1]),
            "averages": {
                "cpu": sum(u.cpu_percent for u in recent) / len(recent),
                "memory": sum(u.memory_percent for u in recent) / len(recent),
                "disk": sum(u.disk_usage_percent for u in recent) / len(recent),
            },
            "limits": self.limits,
        }


# Global monitor instance
system_monitor = SystemMonitor()

# Start monitoring on import
asyncio.create_task(system_monitor.start_monitoring())
