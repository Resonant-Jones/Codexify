"""
Agent and Plugin Integration Tests
------------------------------
Tests interaction between agents and plugins, including error cases
and edge conditions.
"""

import asyncio
import json
import logging
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.agents.axis import AxisAgent, DecisionType
from guardian.agents.echoform import EchoformAgent, ResonanceState
from guardian.agents.vestige import VestigeAgent
from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.plugin_loader import PluginLoader
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestAgentsAndPlugins(unittest.TestCase):
    """Test suite for agent and plugin integration."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize shared test resources."""
        cls.codex = CodexAwareness()
        cls.metacognition = MetacognitionEngine()
        cls.thread_manager = ThreadManager()
        cls.plugin_loader = PluginLoader()
    
    def setUp(self):
        """Set up test-specific resources."""
        self.vestige = VestigeAgent(self.codex, self.metacognition)
        self.axis = AxisAgent(self.codex, self.metacognition)
        self.echoform = EchoformAgent(self.codex, self.metacognition)
    
    def tearDown(self):
        """Clean up test resources."""
        pass
    
    async def test_vestige_memory_processing(self):
        """Test Vestige agent's memory processing capabilities."""
        # Store test memory
        memory_content = {
            'type': 'test_memory',
            'data': 'test_data',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        memory_id = self.codex.store_memory(
            content=memory_content,
            source='test',
            tags=['test'],
            confidence=0.9
        )
        
        # Process memory
        result = await self.vestige.process_memory(
            memory_id,
            {'context': 'test'}
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['memory_id'], memory_id)
        self.assertIn('analysis_id', result)
        
        # Verify pattern detection
        patterns = await self.vestige.analyze_patterns()
        self.assertTrue(len(patterns) > 0)
    
    async def test_axis_decision_making(self):
        """Test Axis agent's decision-making capabilities."""
        # Test routing decision
        decision_result = await self.axis.make_decision(
            decision_type=DecisionType.ROUTING,
            context={
                'destination': 'test_destination',
                'payload': {'type': 'test_data'}
            },
            options=[
                {
                    'id': 'route_1',
                    'value': 'direct',
                    'confidence': 0.8
                },
                {
                    'id': 'route_2',
                    'value': 'cached',
                    'confidence': 0.6
                }
            ]
        )
        
        self.assertEqual(decision_result['status'], 'success')
        self.assertIn('decision_id', decision_result)
        self.assertIn('selected_option', decision_result)
        self.assertIn('confidence', decision_result)
        
        # Test decision outcome recording
        outcome_result = await self.axis.record_outcome(
            decision_result['decision_id'],
            {'success': True, 'latency': 100}
        )
        
        self.assertEqual(outcome_result['status'], 'success')
    
    async def test_echoform_resonance(self):
        """Test Echoform agent's resonance assessment."""
        # Test system state assessment
        result = await self.echoform.assess_resonance({
            'resources': {
                'cpu': {'utilization': 0.7},
                'memory': {'utilization': 0.6}
            },
            'performance': {
                'response_time': 100,
                'throughput': 50
            },
            'errors': {
                'total_operations': 1000,
                'error_count': 5
            }
        })
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('resonance_state', result)
        self.assertIn('assessment_id', result)
        self.assertIn('metrics', result)
    
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle management."""
        # Load plugins
        self.plugin_loader.load_all_plugins()
        
        # Verify memory_analyzer plugin
        self.assertIn('memory_analyzer', self.plugin_loader.plugins)
        
        # Check plugin health
        health = self.plugin_loader.check_plugin_health('memory_analyzer')
        self.assertEqual(health['status'], 'healthy')
        
        # Test plugin disable/enable
        self.assertTrue(
            self.plugin_loader.disable_plugin('memory_analyzer')
        )
        
        # Verify disabled state
        health = self.plugin_loader.check_plugin_health('memory_analyzer')
        self.assertNotEqual(health['status'], 'healthy')
        
        # Re-enable plugin
        self.assertTrue(
            self.plugin_loader.enable_plugin('memory_analyzer')
        )
        
        # Verify re-enabled state
        health = self.plugin_loader.check_plugin_health('memory_analyzer')
        self.assertEqual(health['status'], 'healthy')
    
    def test_plugin_error_handling(self):
        """Test plugin error handling and recovery."""
        # Test loading non-existent plugin
        result = self.plugin_loader.load_plugin(
            Path('/nonexistent/plugin')
        )
        self.assertIsNone(result)
        
        # Test loading plugin with missing interface
        # Create temporary invalid plugin
        invalid_plugin_path = Path('plugins/invalid_plugin')
        invalid_plugin_path.mkdir(exist_ok=True)
        
        with open(invalid_plugin_path / 'plugin.json', 'w') as f:
            json.dump({
                'name': 'invalid_plugin',
                'version': '1.0.0',
                'description': 'Invalid plugin for testing',
                'author': 'Test',
                'dependencies': [],
                'capabilities': []
            }, f)
        
        result = self.plugin_loader.load_plugin(invalid_plugin_path)
        self.assertIsNone(result)
        
        # Clean up
        import shutil
        shutil.rmtree(invalid_plugin_path)
    
    async def test_agent_error_recovery(self):
        """Test agent error recovery capabilities."""
        # Test Vestige recovery from invalid memory
        result = await self.vestige.process_memory(
            'invalid_memory_id',
            {'context': 'test'}
        )
        self.assertEqual(result['status'], 'error')
        
        # Test Axis recovery from invalid decision type
        with self.assertRaises(ValueError):
            await self.axis.make_decision(
                decision_type='invalid_type',
                context={},
                options=[]
            )
        
        # Verify agents remain operational
        self.assertTrue(await self._verify_agent_health())
    
    async def test_system_integration(self):
        """Test full system integration scenarios."""
        # 1. Create and process memory
        memory_id = self.codex.store_memory(
            content={'type': 'test', 'data': 'integration_test'},
            source='test',
            tags=['test', 'integration'],
            confidence=0.9
        )
        
        vestige_result = await self.vestige.process_memory(
            memory_id,
            {'context': 'integration_test'}
        )
        
        # 2. Make decision based on memory
        decision_result = await self.axis.make_decision(
            DecisionType.STRATEGY,
            context={
                'objective': 'process_memory',
                'parameters': {'memory_id': memory_id}
            },
            options=[
                {
                    'id': 'strategy_1',
                    'value': 'immediate_processing',
                    'confidence': 0.8
                },
                {
                    'id': 'strategy_2',
                    'value': 'delayed_processing',
                    'confidence': 0.6
                }
            ]
        )
        
        # 3. Assess system resonance
        resonance_result = await self.echoform.assess_resonance({
            'memory_processing': vestige_result,
            'decision_making': decision_result,
            'system_state': {
                'resources': {'cpu': 0.6, 'memory': 0.5},
                'errors': {'count': 0}
            }
        })
        
        # Verify integration results
        self.assertEqual(vestige_result['status'], 'success')
        self.assertEqual(decision_result['status'], 'success')
        self.assertEqual(resonance_result['status'], 'success')
    
    async def _verify_agent_health(self) -> bool:
        """Verify all agents are operational."""
        try:
            # Test Vestige
            vestige_result = await self.vestige.process_memory(
                'test_memory',
                {'context': 'health_check'}
            )
            
            # Test Axis
            axis_result = await self.axis.make_decision(
                DecisionType.ROUTING,
                {'destination': 'test', 'payload': {}},
                [{'id': 'test', 'value': 'test'}]
            )
            
            # Test Echoform
            echoform_result = await self.echoform.assess_resonance({
                'test': True
            })
            
            return all(
                result['status'] != 'error'
                for result in [vestige_result, axis_result, echoform_result]
            )
            
        except Exception:
            return False

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == '__main__':
    run_tests()
