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
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiagnosticResult:
    """Represents a diagnostic check result."""
    
    def __init__(
        self,
        check_type: str,
        status: str,
        value: Any,
        threshold: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
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
            'check_type': self.check_type,
            'status': self.status,
            'value': self.value,
            'threshold': self.threshold,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'anomaly_score': self.anomaly_score
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
        
        # Initialize monitors
        self.monitors = self._initialize_monitors()
    
    def _initialize_monitors(self) -> Dict[str, Any]:
        """Initialize monitoring components."""
        monitors = {}
        
        if self.config['monitors']['memory']:
            monitors['memory'] = self.MemoryMonitor(self)
        
        if self.config['monitors']['threads']:
            monitors['threads'] = self.ThreadMonitor(self)
        
        if self.config['monitors']['plugins']:
            monitors['plugins'] = self.PluginMonitor(self)
        
        if self.config['monitors']['agents']:
            monitors['agents'] = self.AgentMonitor(self)
        
        if self.config['monitors']['performance']:
            monitors['performance'] = self.PerformanceMonitor(self)
        
        if self.config['monitors']['errors']:
            monitors['errors'] = self.ErrorMonitor(self)
        
        return monitors
    
    class BaseMonitor:
        """Base class for monitors."""
        
        def __init__(self, diagnostics: 'SystemDiagnostics'):
            self.diagnostics = diagnostics
            self.history: List[DiagnosticResult] = []
        
        async def check(self) -> DiagnosticResult:
            """Perform monitoring check."""
            raise NotImplementedError
        
        def _trim_history(self) -> None:
            """Trim history to configured size."""
            max_history = self.diagnostics.config['max_history']
            if len(self.history) > max_history:
                self.history = self.history[-max_history:]
    
    class MemoryMonitor(BaseMonitor):
        """Monitors system memory usage."""
        
        async def check(self) -> DiagnosticResult:
            try:
                # Get memory usage from core system
                memory_info = self.diagnostics.thread_manager.get_memory_info()
                
                usage = memory_info['usage_percent']
                threshold = 80.0  # 80% memory usage threshold
                
                status = 'healthy' if usage < threshold else 'warning'
                
                result = DiagnosticResult(
                    check_type='memory',
                    status=status,
                    value=usage,
                    threshold=threshold,
                    metadata=memory_info
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Memory check failed: {e}")
                return DiagnosticResult(
                    check_type='memory',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    class ThreadMonitor(BaseMonitor):
        """Monitors thread health and performance."""
        
        async def check(self) -> DiagnosticResult:
            try:
                thread_info = self.diagnostics.thread_manager.get_thread_info()
                
                active_threads = thread_info['active_count']
                dead_threads = thread_info['dead_count']
                threshold = self.diagnostics.config.get('max_dead_threads', 5)
                
                status = 'healthy' if dead_threads < threshold else 'warning'
                
                result = DiagnosticResult(
                    check_type='threads',
                    status=status,
                    value=dead_threads,
                    threshold=threshold,
                    metadata={
                        'active_threads': active_threads,
                        'dead_threads': dead_threads,
                        'thread_info': thread_info
                    }
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Thread check failed: {e}")
                return DiagnosticResult(
                    check_type='threads',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    class PluginMonitor(BaseMonitor):
        """Monitors plugin health and status."""
        
        async def check(self) -> DiagnosticResult:
            try:
                plugin_info = await self.diagnostics._check_plugins()
                
                unhealthy_plugins = len([
                    p for p in plugin_info['plugins']
                    if p['status'] != 'healthy'
                ])
                threshold = self.diagnostics.config.get(
                    'max_unhealthy_plugins',
                    2
                )
                
                status = 'healthy' if unhealthy_plugins < threshold else 'warning'
                
                result = DiagnosticResult(
                    check_type='plugins',
                    status=status,
                    value=unhealthy_plugins,
                    threshold=threshold,
                    metadata=plugin_info
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Plugin check failed: {e}")
                return DiagnosticResult(
                    check_type='plugins',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    class AgentMonitor(BaseMonitor):
        """Monitors agent health and performance."""
        
        async def check(self) -> DiagnosticResult:
            try:
                agent_info = await self.diagnostics._check_agents()
                
                unhealthy_agents = len([
                    a for a in agent_info['agents']
                    if a['status'] != 'healthy'
                ])
                threshold = 0  # No unhealthy agents allowed
                
                status = 'healthy' if unhealthy_agents == 0 else 'critical'
                
                result = DiagnosticResult(
                    check_type='agents',
                    status=status,
                    value=unhealthy_agents,
                    threshold=threshold,
                    metadata=agent_info
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Agent check failed: {e}")
                return DiagnosticResult(
                    check_type='agents',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    class PerformanceMonitor(BaseMonitor):
        """Monitors system performance metrics."""
        
        async def check(self) -> DiagnosticResult:
            try:
                perf_info = await self.diagnostics._check_performance()
                
                response_time = perf_info['avg_response_time']
                threshold = self.diagnostics.config.get(
                    'max_response_time',
                    1000
                )
                
                status = 'healthy' if response_time < threshold else 'warning'
                
                result = DiagnosticResult(
                    check_type='performance',
                    status=status,
                    value=response_time,
                    threshold=threshold,
                    metadata=perf_info
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Performance check failed: {e}")
                return DiagnosticResult(
                    check_type='performance',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    class ErrorMonitor(BaseMonitor):
        """Monitors system errors and exceptions."""
        
        async def check(self) -> DiagnosticResult:
            try:
                error_info = self.diagnostics._check_errors()
                
                error_rate = error_info['error_rate']
                threshold = self.diagnostics.config.get('max_error_rate', 0.1)
                
                status = 'healthy' if error_rate < threshold else 'warning'
                
                result = DiagnosticResult(
                    check_type='errors',
                    status=status,
                    value=error_rate,
                    threshold=threshold,
                    metadata=error_info
                )
                
                self.history.append(result)
                self._trim_history()
                
                return result
                
            except Exception as e:
                logger.error(f"Error check failed: {e}")
                return DiagnosticResult(
                    check_type='errors',
                    status='error',
                    value=None,
                    metadata={'error': str(e)}
                )
    
    async def _check_plugins(self) -> Dict[str, Any]:
        """Check plugin health status."""
        plugins = []
        
        try:
            # Get plugin information from core system
            plugin_list = self.thread_manager.get_plugins()
            
            for plugin in plugin_list:
                try:
                    health = plugin.health_check()
                    plugins.append({
                        'name': plugin.name,
                        'status': health['status'],
                        'message': health.get('message', ''),
                        'metrics': health.get('metrics', {})
                    })
                except Exception as e:
                    plugins.append({
                        'name': plugin.name,
                        'status': 'error',
                        'message': str(e),
                        'metrics': {}
                    })
            
            return {
                'plugins': plugins,
                'total': len(plugins),
                'healthy': len([p for p in plugins if p['status'] == 'healthy']),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Plugin check failed: {e}")
            return {
                'plugins': [],
                'total': 0,
                'healthy': 0,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_agents(self) -> Dict[str, Any]:
        """Check agent health status."""
        agents = []
        
        try:
            # Get agent information from core system
            agent_list = self.thread_manager.get_agents()
            
            for agent in agent_list:
                try:
                    status = await agent.get_status()
                    agents.append({
                        'name': agent.name,
                        'status': status['status'],
                        'message': status.get('message', ''),
                        'metrics': status.get('metrics', {})
                    })
                except Exception as e:
                    agents.append({
                        'name': agent.name,
                        'status': 'error',
                        'message': str(e),
                        'metrics': {}
                    })
            
            return {
                'agents': agents,
                'total': len(agents),
                'healthy': len([a for a in agents if a['status'] == 'healthy']),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent check failed: {e}")
            return {
                'agents': [],
                'total': 0,
                'healthy': 0,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_performance(self) -> Dict[str, Any]:
        """Check system performance metrics."""
        try:
            # Get performance metrics from core system
            metrics = self.thread_manager.get_performance_metrics()
            
            return {
                'avg_response_time': metrics['response_time'],
                'throughput': metrics['throughput'],
                'cpu_usage': metrics['cpu_usage'],
                'memory_usage': metrics['memory_usage'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_errors(self) -> Dict[str, Any]:
        """Check system error rates and patterns."""
        try:
            total_operations = sum(
                1 for r in self.check_results
                if r.timestamp > datetime.utcnow() - timedelta(hours=1)
            )
            
            error_count = sum(
                1 for r in self.check_results
                if r.status == 'error' and
                r.timestamp > datetime.utcnow() - timedelta(hours=1)
            )
            
            error_rate = error_count / total_operations if total_operations else 0
            
            return {
                'error_rate': error_rate,
                'error_count': error_count,
                'total_operations': total_operations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error check failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run all diagnostic checks."""
        try:
            results = {}
            
            # Run all monitor checks
            for name, monitor in self.monitors.items():
                try:
                    result = await monitor.check()
                    results[name] = result.to_dict()
                except Exception as e:
                    logger.error(f"{name} check failed: {e}")
                    results[name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Store results
            self._store_results(results)
            
            # Check for alerts
            await self._check_alerts(results)
            
            return {
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Diagnostics failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _store_results(self, results: Dict[str, Any]) -> None:
        """Store diagnostic results."""
        try:
            # Store in memory
            for check_type, result in results.items():
                if isinstance(result, dict):
                    self.check_results.append(
                        DiagnosticResult(
                            check_type=check_type,
                            status=result['status'],
                            value=result.get('value'),
                            threshold=result.get('threshold'),
                            metadata=result.get('metadata', {})
                        )
                    )
            
            # Trim history
            while len(self.check_results) > self.config['max_history']:
                self.check_results.pop(0)
            
            # Store in codex
            self.codex.store_memory(
                content={
                    'type': 'diagnostic_results',
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source='system_diagnostics',
                tags=['diagnostics', 'system_health'],
                confidence=1.0
            )
            
        except Exception as e:
            logger.error(f"Failed to store results: {e}")
    
    async def _check_alerts(self, results: Dict[str, Any]) -> None:
        """Check results for alert conditions."""
        try:
            alerts = []
            
            for check_type, result in results.items():
                if isinstance(result, dict):
                    if result['status'] in ('warning', 'critical', 'error'):
                        alerts.append({
                            'type': check_type,
                            'status': result['status'],
                            'message': f"{check_type} check {result['status']}",
                            'details': result
                        })
            
            if alerts:
                await self._send_alerts(alerts)
                
        except Exception as e:
            logger.error(f"Alert check failed: {e}")
    
    async def _send_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Send alerts through configured channels."""
        for channel in self.config['alert_channels']:
            try:
                if channel == 'internal':
                    # Store in codex
                    self.codex.store_memory(
                        content={
                            'type': 'system_alerts',
                            'alerts': alerts,
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        source='system_diagnostics',
                        tags=['alerts', 'system_health'],
                        confidence=1.0
                    )
                
                elif channel == 'log':
                    for alert in alerts:
                        logger.warning(
                            f"System Alert: {alert['type']} - {alert['message']}"
                        )
                
                elif channel == 'metrics':
                    # Update metrics
                    for alert in alerts:
                        self.thread_manager.update_metrics({
                            f"alert_{alert['type']}": 1,
                            'alert_status': alert['status']
                        })
                
            except Exception as e:
                logger.error(f"Failed to send alert to {channel}: {e}")
    
    async def _diagnostic_loop(self) -> None:
        """Main diagnostic loop."""
        while self.running:
            try:
                # Run diagnostics
                await self.run_diagnostics()
                
                # Update last check time
                self.last_check = datetime.utcnow()
                
                # Wait for next interval
                await asyncio.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Diagnostic loop error: {e}")
                await self._handle_error('diagnostic_loop', e)
                await asyncio.sleep(5)  # Error backoff
    
    async def _handle_error(
        self,
        component: str,
        error: Exception
    ) -> None:
        """Handle component errors."""
        try:
            # Update error count
            self.error_count[component] = self.error_count.get(component, 0) + 1
            
            # Check if recovery needed
            if (
                self.error_count[component] >=
                self.config['failure_handling']['max_retries']
            ):
                if not self.recovery_in_progress:
                    await self._initiate_recovery(component)
            
        except Exception as e:
            logger.error(f"Error handling failed: {e}")
    
    async def _initiate_recovery(self, component: str) -> None:
        """Initiate component recovery."""
        try:
            self.recovery_in_progress = True
            logger.warning(f"Initiating recovery for {component}")
            
            # Execute recovery actions
            for action in self.config['failure_handling']['recovery_actions']:
                try:
                    if action == 'restart_component':
                        await self._restart_component(component)
                    elif action == 'clear_cache':
                        await self._clear_cache()
                    elif action == 'reload_config':
                        await self._reload_config()
                except Exception as e:
                    logger.error(f"Recovery action {action} failed: {e}")
            
            # Reset error count
            self.error_count[component] = 0
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
        finally:
            self.recovery_in_progress = False
    
    async def _restart_component(self, component: str) -> None:
        """Restart a system component."""
        try:
            logger.info(f"Restarting component: {component}")
            
            if component == 'diagnostic_loop':
                self.running = False
                if self.diagnostic_thread:
                    self.diagnostic_thread.join(timeout=5.0)
                self.running = True
                self._start_diagnostic_thread()
            
            # Add other component restart logic as needed
            
        except Exception as e:
            logger.error(f"Component restart failed: {e}")
    
    async def _clear_cache(self) -> None:
        """Clear system caches."""
        try:
            logger.info("Clearing system caches")
            
            # Clear diagnostic results
            self.check_results.clear()
            
            # Clear monitor history
            for monitor in self.monitors.values():
                monitor.history.clear()
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
    
    async def _reload_config(self) -> None:
        """Reload system configuration."""
        try:
            logger.info("Reloading configuration")
            
            # Reload plugin configuration
            plugin_dir = Path(__file__).parent
            with open(plugin_dir / 'plugin.json', 'r') as f:
                self.config = json.load(f)['config']
            
            # Reinitialize monitors
            self.monitors = self._initialize_monitors()
            
        except Exception as e:
            logger.error(f"Config reload failed: {e}")
    
    def _start_diagnostic_thread(self) -> None:
        """Start the diagnostic thread."""
        self.diagnostic_thread = threading.Thread(
            target=lambda: asyncio.run(self._diagnostic_loop()),
            daemon=True
        )
        self.diagnostic_thread.start()

# Global diagnostics instance
diagnostics: Optional[SystemDiagnostics] = None

def init_plugin() -> bool:
    """Initialize the plugin."""
    try:
        # Load configuration
        plugin_dir = Path(__file__).parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            config = json.load(f)
        
        # Create and start diagnostics
        global diagnostics
        diagnostics = SystemDiagnostics(config['config'])
        diagnostics.running = True
        diagnostics._start_diagnostic_thread()
        
        return True
        
    except Exception as e:
        logger.error(f"Plugin initialization failed: {e}")
        return False

def cleanup() -> bool:
    """Clean up plugin resources."""
    try:
        if diagnostics:
            diagnostics.running = False
            if diagnostics.diagnostic_thread:
                diagnostics.diagnostic_thread.join(timeout=5.0)
        return True
    except Exception as e:
        logger.error(f"Plugin cleanup failed: {e}")
        return False

def get_metadata() -> Dict[str, Any]:
    """Return plugin metadata."""
    try:
        plugin_dir = Path(__file__).parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return {}

def health_check() -> Dict[str, Any]:
    """Return plugin health status."""
    if not diagnostics:
        return {
            'status': 'error',
            'message': 'Diagnostics not initialized'
        }
    
    try:
        if not diagnostics.last_check:
            return {
                'status': 'warning',
                'message': 'No diagnostics run yet'
            }
        
        age = datetime.utcnow() - diagnostics.last_check
        if age > timedelta(
            seconds=diagnostics.config['check_interval'] * 2
        ):
            return {
                'status': 'warning',
                'message': f'Diagnostics delayed: {age}'
            }
        
        return {
            'status': 'healthy',
            'message': 'System diagnostics running normally',
            'metrics': {
                'last_check': diagnostics.last_check.isoformat(),
                'results_count': len(diagnostics.check_results),
                'monitors': list(diagnostics.monitors.keys())
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Health check failed: {e}'
        }

# Example usage:
if __name__ == "__main__":
    # Initialize plugin
    if init_plugin():
        print("Plugin initialized successfully")
        
        # Wait for some diagnostics
        time.sleep(10)
        
        # Check health
        health = health_check()
        print("\nHealth Status:")
        print(json.dumps(health, indent=2))
        
        # Cleanup
        cleanup()
    else:
        print("Plugin initialization failed")
