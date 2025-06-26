"""
System Diagnostics Plugin Tests
-----------------------------
Test suite for system diagnostics functionality.
"""

import asyncio
import json
import logging
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.threads.thread_manager import ThreadManager

from ..main import SystemDiagnostics, DiagnosticResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSystemDiagnostics(unittest.TestCase):
    """Test suite for system diagnostics plugin."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test resources."""
        # Load test configuration
        plugin_dir = Path(__file__).parent.parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            cls.config = json.load(f)['config']
    
    def setUp(self):
        """Set up test-specific resources."""
        self.diagnostics = SystemDiagnostics(self.config)
        
        # Mock dependencies
        self.diagnostics.codex = MagicMock(spec=CodexAwareness)
        self.diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
        self.diagnostics.thread_manager = MagicMock(spec=ThreadManager)
    
    def tearDown(self):
        """Clean up test resources."""
        if self.diagnostics.running:
            self.diagnostics.running = False
            if self.diagnostics.diagnostic_thread:
                self.diagnostics.diagnostic_thread.join(timeout=5.0)
    
    async def test_monitor_initialization(self):
        """Test monitor initialization."""
        # Verify all configured monitors are initialized
        for monitor_type in self.config['monitors']:
            if self.config['monitors'][monitor_type]:
                self.assertIn(
                    monitor_type,
                    self.diagnostics.monitors
                )
    
    async def test_memory_monitor(self):
        """Test memory monitoring."""
        # Mock memory info
        memory_info = {
            'usage_percent': 75.0,
            'total': 16384,
            'used': 12288,
            'free': 4096
        }
        self.diagnostics.thread_manager.get_memory_info.return_value = memory_info
        
        # Run memory check
        result = await self.diagnostics.monitors['memory'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'memory')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 75.0)
        self.assertEqual(result.metadata, memory_info)
    
    async def test_thread_monitor(self):
        """Test thread monitoring."""
        # Mock thread info
        thread_info = {
            'active_count': 10,
            'dead_count': 2,
            'total_created': 12
        }
        self.diagnostics.thread_manager.get_thread_info.return_value = thread_info
        
        # Run thread check
        result = await self.diagnostics.monitors['threads'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'threads')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 2)
        self.assertIn('thread_info', result.metadata)
    
    async def test_plugin_monitor(self):
        """Test plugin monitoring."""
        # Mock plugin info
        plugin1 = MagicMock()
        plugin1.name = 'plugin1'
        plugin1.health_check.return_value = {'status': 'healthy'}
        
        plugin2 = MagicMock()
        plugin2.name = 'plugin2'
        plugin2.health_check.return_value = {'status': 'warning'}
        
        self.diagnostics.thread_manager.get_plugins.return_value = [
            plugin1,
            plugin2
        ]
        
        # Run plugin check
        result = await self.diagnostics.monitors['plugins'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'plugins')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 1)  # One unhealthy plugin
        self.assertEqual(len(result.metadata['plugins']), 2)
    
    async def test_agent_monitor(self):
        """Test agent monitoring."""
        # Mock agent info
        agent1 = MagicMock()
        agent1.name = 'agent1'
        agent1.get_status.return_value = {'status': 'healthy'}
        
        agent2 = MagicMock()
        agent2.name = 'agent2'
        agent2.get_status.return_value = {'status': 'healthy'}
        
        self.diagnostics.thread_manager.get_agents.return_value = [
            agent1,
            agent2
        ]
        
        # Run agent check
        result = await self.diagnostics.monitors['agents'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'agents')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 0)  # No unhealthy agents
        self.assertEqual(len(result.metadata['agents']), 2)
    
    async def test_performance_monitor(self):
        """Test performance monitoring."""
        # Mock performance metrics
        metrics = {
            'response_time': 100,
            'throughput': 1000,
            'cpu_usage': 60,
            'memory_usage': 70
        }
        self.diagnostics.thread_manager.get_performance_metrics.return_value = metrics
        
        # Run performance check
        result = await self.diagnostics.monitors['performance'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'performance')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 100)
        self.assertIn('throughput', result.metadata)
    
    async def test_error_monitor(self):
        """Test error monitoring."""
        # Add some test results
        self.diagnostics.check_results = [
            DiagnosticResult('test', 'healthy', None),
            DiagnosticResult('test', 'error', None),
            DiagnosticResult('test', 'healthy', None),
            DiagnosticResult('test', 'error', None)
        ]
        
        # Run error check
        result = await self.diagnostics.monitors['errors'].check()
        
        # Verify result
        self.assertEqual(result.check_type, 'errors')
        self.assertEqual(result.status, 'warning')
        self.assertEqual(result.value, 0.5)  # 50% error rate
    
    async def test_alert_generation(self):
        """Test alert generation and delivery."""
        # Create test results with alerts
        results = {
            'memory': {
                'status': 'warning',
                'value': 90.0,
                'threshold': 80.0
            },
            'threads': {
                'status': 'critical',
                'value': 10,
                'threshold': 5
            }
        }
        
        # Process alerts
        await self.diagnostics._check_alerts(results)
        
        # Verify alert storage
        self.diagnostics.codex.store_memory.assert_called()
        
        # Verify metric updates
        self.diagnostics.thread_manager.update_metrics.assert_called()
    
    async def test_error_handling(self):
        """Test error handling and recovery."""
        # Simulate repeated errors
        component = 'test_component'
        error = Exception('Test error')
        
        for _ in range(self.config['failure_handling']['max_retries'] + 1):
            await self.diagnostics._handle_error(component, error)
        
        # Verify recovery was initiated
        self.assertTrue(
            self.diagnostics.error_count[component] >=
            self.config['failure_handling']['max_retries']
        )
    
    async def test_diagnostic_loop(self):
        """Test main diagnostic loop."""
        # Start diagnostics
        self.diagnostics.running = True
        self.diagnostics._start_diagnostic_thread()
        
        # Wait for some diagnostics to run
        await asyncio.sleep(2)
        
        # Verify diagnostics are running
        self.assertIsNotNone(self.diagnostics.last_check)
        self.assertTrue(len(self.diagnostics.check_results) > 0)
    
    async def test_result_storage(self):
        """Test diagnostic result storage."""
        # Create test results
        results = {
            'test': {
                'status': 'healthy',
                'value': 100,
                'threshold': 200
            }
        }
        
        # Store results
        self.diagnostics._store_results(results)
        
        # Verify memory storage
        self.assertTrue(len(self.diagnostics.check_results) > 0)
        
        # Verify codex storage
        self.diagnostics.codex.store_memory.assert_called_once()
    
    def test_diagnostic_result(self):
        """Test DiagnosticResult class."""
        # Create test result
        result = DiagnosticResult(
            check_type='test',
            status='healthy',
            value=100,
            threshold=200,
            metadata={'test': 'data'}
        )
        
        # Verify result
        self.assertEqual(result.check_type, 'test')
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.value, 100)
        self.assertEqual(result.threshold, 200)
        self.assertEqual(result.metadata['test'], 'data')
        
        # Verify dictionary conversion
        result_dict = result.to_dict()
        self.assertIn('check_type', result_dict)
        self.assertIn('status', result_dict)
        self.assertIn('value', result_dict)
        self.assertIn('threshold', result_dict)
        self.assertIn('metadata', result_dict)
        self.assertIn('timestamp', result_dict)
        self.assertIn('anomaly_score', result_dict)

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == '__main__':
    run_tests()
