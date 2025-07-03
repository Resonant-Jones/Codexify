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
        """Initialize shared test resources (class-level)."""
        # Components that need per-test state/isolation are initialized in setUp.
        pass

    def setUp(self):
        """Set up test-specific resources for each test method."""
        # Ensure artifacts.json is clean for CodexAwareness
        artifact_path = Path(__file__).parent.parent / 'guardian' / 'memory' / 'artifacts.json'
        if artifact_path.exists():
            artifact_path.unlink()

        self.codex = CodexAwareness() # Fresh instance
        self.codex.artifacts.clear() # Explicitly clear in-memory artifacts
        self.thread_manager = ThreadManager() # Fresh instance
        # Pass the test's codex instance to MetacognitionEngine
        self.metacognition = MetacognitionEngine(
            thread_manager=self.thread_manager,
            codex_awareness=self.codex
        )
        self.plugin_loader = PluginLoader() # Assuming this can be fresh

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
        # Corrected system_state structure for assess_resonance
        mock_system_state_for_resonance = {
            'resources': {
                'cpu': {'utilization': 0.6},
                'memory': {'utilization': 0.5}
            },
            'errors': {
                'total_operations': 1, # Provide a non-zero total_operations
                'error_count': 0
            },
            'performance': { # Add some performance data
                'response_time': 100, # ms
                'throughput': 10 # ops/sec
            },
            'coherence': { # Add some coherence data
                'component_alignment': 0.9,
                'state_consistency': 0.95
            }
            # 'memory_processing' and 'decision_making' are not standard top-level keys
            # for _analyze_metrics, but assess_resonance takes a generic Dict.
            # For _analyze_metrics to pick up data, it must be under the expected keys.
        }
        resonance_result = await self.echoform.assess_resonance(mock_system_state_for_resonance)
        
        # Verify integration results
        self.assertEqual(vestige_result['status'], 'success')
        self.assertEqual(decision_result['status'], 'success')
        self.assertEqual(resonance_result['status'], 'success')
    
    async def _verify_agent_health(self) -> bool:
        """Verify all agents are operational and respond correctly."""
        try:
            # Test Vestige: Expects an error status for a non-existent memory ID, but should not crash.
            vestige_result = await self.vestige.process_memory(
                'non_existent_memory_for_health_check',
                {'context': 'health_check'}
            )
            if not isinstance(vestige_result, dict) or 'status' not in vestige_result:
                logger.error("Vestige health check failed: Invalid response format.")
                return False
            # For this health check, Vestige returning an error for a missing ID is "healthy" agent behavior.
            # The key is that it processed the request and returned a valid error structure.
            # If it had crashed, the exception block below would catch it.

            # Test Axis: Expects success for a valid basic decision.
            axis_result = await self.axis.make_decision(
                DecisionType.ROUTING,
                {'destination': 'health_check_dest', 'payload': {'data': 'sample'}},
                [{'id': 'route_default', 'value': 'default_action', 'confidence': 0.9}]
            )
            if not isinstance(axis_result, dict) or axis_result.get('status') != 'success':
                logger.error(f"Axis health check failed: Status was {axis_result.get('status')}, error: {axis_result.get('error')}")
                return False
            
            # Test Echoform: Provide structured empty state, expects success.
            mock_empty_system_state = {
                'resources': {'cpu': {'utilization': 0.5}, 'memory': {'utilization': 0.5}},
                'errors': {'total_operations': 0, 'error_count': 0},
                'performance': {'response_time': 0, 'throughput': 0},
                'coherence': {'component_alignment': 1.0, 'state_consistency': 1.0}
            }
            echoform_result = await self.echoform.assess_resonance(mock_empty_system_state)
            if not isinstance(echoform_result, dict) or echoform_result.get('status') != 'success':
                logger.error(f"Echoform health check failed: Status was {echoform_result.get('status')}, error: {echoform_result.get('error')}")
                return False
            
            # If all checks passed as defined above
            return True
            
        except Exception as e:
            logger.error(f"_verify_agent_health encountered an unhandled exception: {e}")
            return False

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == '__main__':
    run_tests()
