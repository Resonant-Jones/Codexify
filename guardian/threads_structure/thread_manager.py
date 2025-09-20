"""
Thread Manager Module
------------------
Manages the lifecycle and health monitoring of all system threads and agents.
Provides centralized control over thread initialization, monitoring, and graceful shutdown.

This module ensures reliable operation of concurrent system components and
maintains health metrics for system-wide monitoring.
"""

import json
import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from guardian.utils.datetime import to_iso_z

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThreadHealth:
    """Tracks health metrics for a single thread or agent."""

    def __init__(self, thread_id: str, thread_type: str):
        self.thread_id = thread_id
        self.thread_type = thread_type
        self.start_time = datetime.now(UTC)
        self.last_heartbeat = self.start_time
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.status = "initializing"  # initializing, running, warning, error, stopped
        self.metrics: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert health metrics to a dictionary."""
        return {
            "thread_id": self.thread_id,
            "thread_type": self.thread_type,
            "start_time": to_iso_z(self.start_time),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "uptime": str(datetime.now(UTC) - self.start_time),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "status": self.status,
            "metrics": self.metrics,
        }


class ThreadManager:
    """
    Manages system threads and monitors their health.
    Provides interfaces for thread lifecycle management and health reporting.
    """

    def __init__(self):
        """Initialize the thread manager."""
        self.threads: Dict[str, threading.Thread] = {}
        self.health_metrics: Dict[str, ThreadHealth] = {}
        self.agents: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.shutdown_flag = threading.Event()
        self.shutdown_complete = False
        self.health_check_interval = 10  # seconds
        self.performance_metrics: Dict[str, Any] = {
            "response_time": 0,
            "error_rate": 0,
            "active_count": 0,
        }
        self.monitor_thread: Optional[threading.Thread] = None
        self._start_health_monitor()

    def initialize_agents(self, codex: Any, metacognition: Any) -> None:
        """Initialize agents with required dependencies."""
        from guardian.agents.axis import AxisAgent
        from guardian.agents.echoform import EchoformAgent
        from guardian.agents.vestige import VestigeAgent

        # Create and register agents
        vestige = VestigeAgent(codex, metacognition)
        axis = AxisAgent(codex, metacognition)
        echoform = EchoformAgent(codex, metacognition)

        self.register_agent("vestige", vestige)
        self.register_agent("axis", axis)
        self.register_agent("echoform", echoform)

    def _start_health_monitor(self) -> None:
        """Start the background health monitoring thread."""
        self.monitor_thread = threading.Thread(
            target=self._health_monitor_loop, daemon=True
        )
        self.monitor_thread.start()

    def _health_monitor_loop(self) -> None:
        """Continuous health monitoring loop."""
        while not self.shutdown_flag.is_set():
            try:
                self._check_thread_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    def _check_thread_health(self) -> None:
        """Check health of all registered threads."""
        with self.lock:
            current_time = datetime.now(UTC)
            for thread_id, health in self.health_metrics.items():
                # Check if thread is still alive
                thread = self.threads.get(thread_id)
                if thread and not thread.is_alive():
                    health.status = "error"
                    health.last_error = "Thread died unexpectedly"
                    continue

                # Check heartbeat age
                heartbeat_age = current_time - health.last_heartbeat
                if heartbeat_age > timedelta(seconds=30):
                    health.status = "warning"
                    logger.warning(
                        f"Thread {thread_id} heartbeat is old: {heartbeat_age}"
                    )

    def create_thread(self, name: str, target: Any, *args: Any, **kwargs: Any) -> str:
        """
        Create and register a new thread.

        Args:
            name: Name/ID for the thread
            target: Function to run in the thread
            *args: Positional arguments for the target function
            **kwargs: Keyword arguments for the target function

        Returns:
            str: Thread ID
        """
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        self.register_thread(name, thread, "worker")
        return name

    def register_thread(
        self, thread_id: str, thread: threading.Thread, thread_type: str
    ) -> None:
        """
        Register a new thread for management.

        Args:
            thread_id: Unique identifier for the thread
            thread: The thread object to manage
            thread_type: Type/category of the thread
        """
        with self.lock:
            if thread_id in self.threads:
                raise ValueError(f"Thread {thread_id} already registered")

            self.threads[thread_id] = thread
            self.health_metrics[thread_id] = ThreadHealth(thread_id, thread_type)
            logger.info(f"Registered thread {thread_id} of type {thread_type}")

    def start_thread(self, thread_id: str) -> None:
        """
        Start a registered thread.

        Args:
            thread_id: ID of the thread to start
        """
        with self.lock:
            if thread_id not in self.threads:
                raise ValueError(f"Thread {thread_id} not registered")

            thread = self.threads[thread_id]
            if not thread.is_alive():
                thread.start()
                self.health_metrics[thread_id].status = "running"
                logger.info(f"Started thread {thread_id}")

    def stop_thread(self, thread_id: str, timeout: float = 5.0) -> bool:
        """
        Stop a thread gracefully.

        Args:
            thread_id: ID of the thread to stop
            timeout: Maximum time to wait for thread to stop

        Returns:
            bool: True if thread stopped successfully
        """
        with self.lock:
            if thread_id not in self.threads:
                raise ValueError(f"Thread {thread_id} not registered")

            thread = self.threads[thread_id]
            health = self.health_metrics[thread_id]
            current = threading.current_thread()

            # Signal thread to stop
            health.status = "stopping"  # Signal the thread to stop

        # Don't try to join the current thread
        if thread is current:
            logger.warning(f"Skipping join of current thread {thread_id}")
            return True

        # Wait for thread to stop (lock is released before this)
        try:
            thread.join(timeout)
            success = not thread.is_alive()

            with self.lock:  # Re-acquire lock to update final status
                health = self.health_metrics[thread_id]  # Re-fetch health obj
                if success:
                    health.status = "stopped"
                    logger.info(f"Stopped thread {thread_id}")
                else:
                    health.status = "error"
                    health.last_error = "Failed to stop thread"
                    logger.warning(f"Thread {thread_id} did not stop within timeout")

            return success

        except Exception as e:
            with self.lock:  # Re-acquire lock to update error status
                health = self.health_metrics[thread_id]  # Re-fetch health obj
                health.status = "error"
                health.last_error = f"Error stopping thread: {e}"
            logger.error(f"Failed to stop thread {thread_id}: {e}")
            return False

    def heartbeat(
        self, thread_id: str, metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update thread heartbeat and optional metrics.

        Args:
            thread_id: ID of the thread
            metrics: Optional metrics to update
        """
        with self.lock:
            if thread_id in self.health_metrics:
                health = self.health_metrics[thread_id]
                health.last_heartbeat = datetime.now(UTC)
                if metrics:
                    health.metrics.update(metrics)

    def report_error(self, thread_id: str, error: str) -> None:
        """
        Report an error for a thread.

        Args:
            thread_id: ID of the thread
            error: Error message
        """
        with self.lock:
            if thread_id in self.health_metrics:
                health = self.health_metrics[thread_id]
                health.error_count += 1
                health.last_error = error
                health.status = "error"
                logger.error(f"Thread {thread_id} error: {error}")

    def get_agent(self, agent_name: str) -> Any:
        """
        Get an agent by name.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            Agent instance
        """
        return self.agents.get(agent_name)

    def register_agent(self, agent_name: str, agent: Any) -> None:
        """
        Register an agent with the thread manager.

        Args:
            agent_name: Name of the agent
            agent: Agent instance
        """
        self.agents[agent_name] = agent

    def get_thread_info(self) -> Dict[str, Any]:
        """
        Get information about all threads.

        Returns:
            Dict containing thread information
        """
        with self.lock:
            return {
                "active_count": len([t for t in self.threads.values() if t.is_alive()]),
                "total_count": len(self.threads),
                "threads": {
                    tid: {"alive": t.is_alive(), "daemon": t.daemon}
                    for tid, t in self.threads.items()
                },
            }

    def join_thread(self, thread_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a thread to complete.

        Args:
            thread_id: ID of the thread to join
            timeout: Maximum time to wait (in seconds)

        Returns:
            bool: True if thread completed, False if timeout occurred
        """
        try:
            with self.lock:
                if thread_id not in self.threads:
                    logger.error(f"Thread {thread_id} not found")
                    return False

                thread = self.threads[thread_id]

            thread.join(timeout=timeout)
            return not thread.is_alive()

        except Exception as e:
            logger.error(f"Failed to join thread {thread_id}: {e}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics.

        Returns:
            Dict containing performance metrics
        """
        with self.lock:
            self.performance_metrics["active_count"] = len(
                [t for t in self.threads.values() if t.is_alive()]
            )
            return self.performance_metrics.copy()

    # --- Placeholder methods for system_diagnostics plugin ---
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Retrieves memory usage information.

        Currently a placeholder, returns a dictionary with zero values.
        Planned implementation will use psutil to gather actual memory data.
        """
        logger.warning(
            "ThreadManager.get_memory_info is a placeholder and not fully implemented."
        )
        return {"total": 0, "available": 0, "percent": 0, "used": 0}

    def get_plugins(
        self,
    ) -> List[Any]:  # Actual type might be List[Plugin] or List[Dict]
        """
        Retrieves a list of plugins.

        Currently a placeholder, returns an empty list.
        Planned implementation will integrate with the plugin manager.
        """
        logger.warning(
            "ThreadManager.get_plugins is a placeholder and not fully implemented."
        )
        return []

    def get_agents(self) -> List[Any]:  # Actual type might be List[Agent] or List[Dict]
        """
        Retrieves a list of agents.

        Currently a placeholder, returns an empty list.
        Planned implementation will return a list of registered agents.
        """
        logger.warning(
            "ThreadManager.get_agents is a placeholder and not fully implemented."
        )
        return []

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Updates performance metrics.

        Currently a placeholder, does nothing.
        Planned implementation will update internal performance metrics.
        """
        logger.warning(
            f"ThreadManager.update_metrics called with {metrics}, but is a placeholder."
        )
        pass

    # --- End placeholder methods ---

    def health_check(self) -> Dict[str, Any]:
        """
        Get health status for all threads.

        Returns:
            Dict containing:
            - status: Overall system status
            - thread_count: Number of registered threads
            - threads: Dict of thread health metrics
            - timestamp: Time of health check
        """
        with self.lock:
            thread_health = {
                thread_id: health.to_dict()
                for thread_id, health in self.health_metrics.items()
            }

            # Determine overall status
            status = "nominal"
            if any(h.status == "error" for h in self.health_metrics.values()):
                status = "error"
            elif any(h.status == "warning" for h in self.health_metrics.values()):
                status = "warning"

            return {
                "status": status,
                "thread_count": len(self.threads),
                "threads": thread_health,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def shutdown(self, timeout: float = 5.0) -> bool:
        """
        Shutdown all threads gracefully.

        Args:
            timeout: Maximum time to wait for each thread

        Returns:
            bool: True if all threads stopped successfully
        """
        logger.info("Initiating system shutdown...")
        self.shutdown_flag.set()

        success = True
        current = threading.current_thread()
        thread_ids = list(self.threads.keys())

        # First stop non-essential threads
        for thread_id in thread_ids:
            thread = self.threads[thread_id]
            if thread is not current and thread != self.monitor_thread:
                if not self.stop_thread(thread_id, timeout):
                    success = False

        # Stop monitor thread last
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout)
                if self.monitor_thread.is_alive():
                    logger.warning("Monitor thread did not stop cleanly")
                    success = False
            except Exception as e:
                logger.error(f"Error stopping monitor thread: {e}")
                success = False

        # Set final shutdown status
        self.shutdown_complete = True

        if success:
            logger.info("System shutdown completed successfully")
        else:
            logger.error("Some threads failed to stop during shutdown")

        return success


# Example usage:
if __name__ == "__main__":
    # Initialize thread manager
    manager = ThreadManager()

    # Example worker thread
    def worker():
        while True:
            time.sleep(1)
            manager.heartbeat("worker1", {"iterations": 1})

    # Create and register thread
    worker_thread = threading.Thread(target=worker, daemon=True)
    manager.register_thread("worker1", worker_thread, "worker")

    # Start thread
    manager.start_thread("worker1")

    # Wait a bit and check health
    time.sleep(2)
    health_report = manager.health_check()
    print("\nHealth Report:")
    print(json.dumps(health_report, indent=2))

    # Shutdown
    manager.shutdown()
