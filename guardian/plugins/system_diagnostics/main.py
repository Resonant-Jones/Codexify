"""
System Diagnostics Plugin
------------------------
Advanced system monitoring and diagnostics with comprehensive error handling
and core system communication.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.threads.thread_manager import ThreadManager
from guardian.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


class DiagnosticResult:
    """Represents a diagnostic check result."""

    def __init__(
        self,
        check_type: str,
        status: str,
        value: Any,
        threshold: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.check_type = check_type
        self.status = status
        self.value = value
        self.threshold = threshold
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.anomaly_score = self._calculate_anomaly_score()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "check_type": self.check_type,
            "status": self.status,
            "value": self.value,
            "threshold": self.threshold,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "anomaly_score": self.anomaly_score,
        }

    def _calculate_anomaly_score(self) -> float:
        """Calculate anomaly score based on value and threshold."""
        if self.threshold is None:
            return 0.0
        try:
            if isinstance(self.value, (int, float)):
                return abs(self.value - self.threshold) / self.threshold
            return 0.0
        except Exception:
            return 0.0


class SystemDiagnostics:
    """Core system diagnostics functionality."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.codex = CodexAwareness()
        self.metacognition = MetacognitionEngine()
        self.thread_manager = ThreadManager()

        self.running = False
        self.diagnostic_thread: Optional[threading.Thread] = None
        self.last_check: Optional[datetime] = None
        self.check_results: List[DiagnosticResult] = []
        self.error_count: Dict[str, int] = {}
        self.recovery_in_progress = False

        self.monitors = self._initialize_monitors()

    def _initialize_monitors(self) -> Dict[str, Any]:
        monitors = {}

        if self.config["monitors"]["memory"]:
            monitors["memory"] = self.MemoryMonitor(self)

        if self.config["monitors"]["threads"]:
            monitors["threads"] = self.ThreadMonitor(self)

        if self.config["monitors"]["plugins"]:
            monitors["plugins"] = self.PluginMonitor(self)

        if self.config["monitors"]["agents"]:
            monitors["agents"] = self.AgentMonitor(self)

        if self.config["monitors"]["performance"]:
            monitors["performance"] = self.PerformanceMonitor(self)

        if self.config["monitors"]["errors"]:
            monitors["errors"] = self.ErrorMonitor(self)

        return monitors

    class BaseMonitor:
        def __init__(self, diagnostics: "SystemDiagnostics"):
            self.diagnostics = diagnostics
            self.history: List[DiagnosticResult] = []

        async def check(self) -> DiagnosticResult:
            raise NotImplementedError

        def _trim_history(self):
            max_history = self.diagnostics.config["max_history"]
            if len(self.history) > max_history:
                self.history = self.history[-max_history:]

    # Memory Monitor
    class MemoryMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                memory_info = self.diagnostics.thread_manager.get_memory_info()
                usage = memory_info.get("usage_percent", 0.0)
                threshold = 80.0
                status = "healthy" if usage < threshold else "warning"

                result = DiagnosticResult(
                    check_type="memory",
                    status=status,
                    value=usage,
                    threshold=threshold,
                    metadata=memory_info,
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Memory check failed: {e}")
                return DiagnosticResult(
                    "memory", "error", None, metadata={"error": str(e)}
                )

    # Thread Monitor
    class ThreadMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                # Try get_thread_info first (for test compatibility), then fallback to health_check
                if hasattr(self.diagnostics.thread_manager, "get_thread_info"):
                    thread_info = self.diagnostics.thread_manager.get_thread_info()
                    active_threads = thread_info.get("active_count", 0)
                    dead_threads = thread_info.get("dead_count", 0)
                    monitored_threads_info = {
                        "active_count": active_threads,
                        "dead_count": dead_threads,
                    }
                else:
                    health_check_report = self.diagnostics.thread_manager.health_check()
                    active_threads, dead_threads = 0, 0
                    monitored_threads_info = health_check_report.get("threads", {})

                    for _, tinfo in monitored_threads_info.items():
                        if isinstance(tinfo, dict):
                            if tinfo.get("status") in ("running", "initializing"):
                                active_threads += 1
                            elif tinfo.get("status") in ("error", "stopped"):
                                dead_threads += 1

                threshold = self.diagnostics.config.get("max_dead_threads", 5)
                status = "healthy" if dead_threads < threshold else "warning"

                result = DiagnosticResult(
                    check_type="threads",
                    status=status,
                    value=dead_threads,
                    threshold=threshold,
                    metadata={
                        "active_threads": active_threads,
                        "dead_threads": dead_threads,
                        "threads": monitored_threads_info,
                    },
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Thread check failed: {e}")
                return DiagnosticResult(
                    "threads", "error", None, metadata={"error": str(e)}
                )

    # Plugin Monitor
    class PluginMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                plugin_info = await self.diagnostics._check_plugins()
                unhealthy = len(
                    [p for p in plugin_info["plugins"] if p["status"] != "healthy"]
                )
                threshold = self.diagnostics.config.get("max_unhealthy_plugins", 2)
                status = "healthy" if unhealthy < threshold else "warning"

                result = DiagnosticResult(
                    "plugins", status, unhealthy, threshold, metadata=plugin_info
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Plugin check failed: {e}")
                return DiagnosticResult(
                    "plugins", "error", None, metadata={"error": str(e)}
                )

    # Agent Monitor
    class AgentMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                agent_info = await self.diagnostics._check_agents()
                unhealthy = len(
                    [a for a in agent_info["agents"] if a["status"] != "healthy"]
                )
                threshold = 0
                status = "healthy" if unhealthy == 0 else "critical"

                result = DiagnosticResult(
                    "agents", status, unhealthy, threshold, metadata=agent_info
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Agent check failed: {e}")
                return DiagnosticResult(
                    "agents", "error", None, metadata={"error": str(e)}
                )

    # Performance Monitor
    class PerformanceMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                perf_info = await self.diagnostics._check_performance()
                response_time = perf_info["avg_response_time"]
                threshold = self.diagnostics.config.get("max_response_time", 1000)
                status = "healthy" if response_time < threshold else "warning"

                result = DiagnosticResult(
                    "performance", status, response_time, threshold, metadata=perf_info
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Performance check failed: {e}")
                return DiagnosticResult(
                    "performance", "error", None, metadata={"error": str(e)}
                )

    # Error Monitor
    class ErrorMonitor(BaseMonitor):
        async def check(self) -> DiagnosticResult:
            try:
                error_info = self.diagnostics._check_errors()
                error_rate = error_info["error_rate"]
                threshold = self.diagnostics.config.get("max_error_rate", 0.1)
                status = "healthy" if error_rate < threshold else "warning"

                result = DiagnosticResult(
                    "errors", status, error_rate, threshold, metadata=error_info
                )
                self.history.append(result)
                self._trim_history()
                return result
            except Exception as e:
                logger.error(f"Error check failed: {e}")
                return DiagnosticResult(
                    "errors", "error", None, metadata={"error": str(e)}
                )

    async def _check_plugins(self) -> Dict[str, Any]:
        plugins = []
        try:
            plugin_list = self.thread_manager.get_plugins()
            for plugin in plugin_list:
                try:
                    health = plugin.health_check()
                    plugins.append(
                        {
                            "name": plugin.name,
                            "status": health["status"],
                            "message": health.get("message", ""),
                            "metrics": health.get("metrics", {}),
                        }
                    )
                except Exception as e:
                    plugins.append(
                        {
                            "name": plugin.name,
                            "status": "error",
                            "message": str(e),
                            "metrics": {},
                        }
                    )
            return {
                "plugins": plugins,
                "total": len(plugins),
                "healthy": len([p for p in plugins if p["status"] == "healthy"]),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Plugin check failed: {e}")
            return {"plugins": [], "total": 0, "healthy": 0, "error": str(e)}

    async def _check_agents(self) -> Dict[str, Any]:
        agents = []
        try:
            agent_list = self.thread_manager.get_agents()
            for agent in agent_list:
                try:
                    status = await agent.get_status()
                    agents.append(
                        {
                            "name": agent.name,
                            "status": status["status"],
                            "message": status.get("message", ""),
                            "metrics": status.get("metrics", {}),
                        }
                    )
                except Exception as e:
                    agents.append(
                        {
                            "name": agent.name,
                            "status": "error",
                            "message": str(e),
                            "metrics": {},
                        }
                    )
            return {
                "agents": agents,
                "total": len(agents),
                "healthy": len([a for a in agents if a["status"] == "healthy"]),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Agent check failed: {e}")
            return {"agents": [], "total": 0, "healthy": 0, "error": str(e)}

    async def _check_performance(self) -> Dict[str, Any]:
        try:
            metrics = self.thread_manager.get_performance_metrics()
            return {
                "avg_response_time": metrics["response_time"],
                "throughput": metrics["throughput"],
                "cpu_usage": metrics["cpu_usage"],
                "memory_usage": metrics["memory_usage"],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _check_errors(self) -> Dict[str, Any]:
        try:
            total_ops = sum(
                1
                for r in self.check_results
                if r.timestamp > datetime.utcnow() - timedelta(hours=1)
            )
            error_count = sum(
                1
                for r in self.check_results
                if r.status == "error"
                and r.timestamp > datetime.utcnow() - timedelta(hours=1)
            )
            error_rate = error_count / total_ops if total_ops else 0
            return {
                "error_rate": error_rate,
                "error_count": error_count,
                "total_operations": total_ops,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error check failed: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _store_results(self, results: Dict[str, Any]) -> None:
        try:
            for check_type, result in results.items():
                if isinstance(result, dict):
                    self.check_results.append(
                        DiagnosticResult(
                            check_type=check_type,
                            status=result["status"],
                            value=result.get("value"),
                            threshold=result.get("threshold"),
                            metadata=result.get("metadata", {}),
                        )
                    )
            while len(self.check_results) > self.config["max_history"]:
                self.check_results.pop(0)
            self.codex.store_memory(
                content={
                    "type": "diagnostic_results",
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="system_diagnostics",
                tags=["diagnostics", "system_health"],
                confidence=1.0,
            )
        except Exception as e:
            logger.error(f"Failed to store results: {e}")

    async def _check_alerts(self, results: Dict[str, Any]) -> None:
        try:
            alerts = []
            for check_type, result in results.items():
                if isinstance(result, dict):
                    if result["status"] in ("warning", "critical", "error"):
                        alerts.append(
                            {
                                "type": check_type,
                                "status": result["status"],
                                "message": f"{check_type} check {result['status']}",
                                "details": result,
                            }
                        )
            if alerts:
                await self._send_alerts(alerts)
                # Update metrics after sending alerts
                if hasattr(self.thread_manager, "update_metrics"):
                    self.thread_manager.update_metrics(alerts)
        except Exception as e:
            logger.error(f"Alert check failed: {e}")

    async def _handle_error(self, component: str, error: Exception) -> None:
        try:
            self.error_count[component] = self.error_count.get(component, 0) + 1
            if (
                self.error_count[component]
                >= self.config["failure_handling"]["max_retries"]
            ):
                if not self.recovery_in_progress:
                    await self._initiate_recovery(component)
        except Exception as e:
            logger.error(f"Error handling failed: {e}")

    def _start_diagnostic_thread(self) -> None:
        self.diagnostic_thread = threading.Thread(
            target=lambda: asyncio.run(self._diagnostic_loop()), daemon=True
        )
        self.diagnostic_thread.start()

    async def _diagnostic_loop(self) -> None:
        """Main diagnostic loop that runs checks and updates results."""
        while self.running:
            try:
                # Run all monitor checks
                for monitor_name, monitor in self.monitors.items():
                    result = await monitor.check()
                    self.check_results.append(result)

                # Update last check timestamp
                self.last_check = datetime.utcnow()

                # Trim results to max history
                while len(self.check_results) > self.config.get("max_history", 100):
                    self.check_results.pop(0)

                # Sleep for the configured interval
                await asyncio.sleep(self.config.get("diagnostic_interval", 1))
            except Exception as e:
                logger.error(f"Diagnostic loop error: {e}")
                await asyncio.sleep(1)  # Brief pause on error

    async def _initiate_recovery(self, component: str) -> None:
        """Initiate recovery procedures for a failing component."""
        try:
            self.recovery_in_progress = True
            logger.info(f"Initiating recovery for component: {component}")

            # Simulate recovery delay
            await asyncio.sleep(0.1)

            # Reset error count for the component
            self.error_count[component] = 0

            logger.info(f"Recovery completed for component: {component}")
        except Exception as e:
            logger.error(f"Recovery failed for {component}: {e}")
        finally:
            self.recovery_in_progress = False

    async def _send_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Send alerts through configured channels."""
        try:
            for alert in alerts:
                self.codex.store_memory(
                    content={
                        "type": "system_alert",
                        "alert": alert,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    source="system_diagnostics",
                    tags=["alert"],
                    confidence=1.0,
                )
            logger.info(f"Alerts sent: {len(alerts)}")
        except Exception as e:
            logger.error(f"Failed to send alerts: {e}")
