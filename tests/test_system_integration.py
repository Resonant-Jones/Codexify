"""
System Integration Tests
----------------------
Verifies that all Threadspace components work together correctly.
Tests core functionality, self-awareness, and system coherence.
"""

import json
import logging
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.codex_awareness import CodexAwareness
from guardian.config.system_config import SystemConfig
from guardian.metacognition import MetacognitionEngine
from guardian.plugin_loader import PluginLoader
from guardian.self_check import epistemic_self_check
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestWorkerThread(threading.Thread):
    """Test thread for thread management verification."""
    
    def __init__(self, thread_id: str, manager: ThreadManager):
        super().__init__()
        self.thread_id = thread_id
        self.manager = manager
        self.running = True
        self.daemon = True
    
    def run(self):
        while self.running:
            self.manager.heartbeat(
                self.thread_id,
                {'status': 'running', 'timestamp': datetime.utcnow().isoformat()}
            )
            time.sleep(1)
    
    def stop(self):
        self.running = False

class SystemIntegrationTest(unittest.TestCase):
    """
    Integration tests for the Threadspace system.
    Tests component interaction and system coherence.
    """
    
    @classmethod
    def setUpClass(cls):
        """Initialize system components for testing."""
        cls.config = SystemConfig()
        cls.thread_manager = ThreadManager()
        cls.codex_awareness = CodexAwareness()
        cls.plugin_loader = PluginLoader()
        cls.metacognition = MetacognitionEngine()
    
    def setUp(self):
        """Set up test-specific resources."""
        self.test_threads: List[TestWorkerThread] = []
    
    def tearDown(self):
        """Clean up test resources."""
        for thread in self.test_threads:
            thread.stop()
            thread.join(timeout=5.0)
    
    def test_thread_management(self):
        """Test thread lifecycle management and health monitoring."""
        # Create and register test thread
        worker = TestWorkerThread("test_worker", self.thread_manager)
        self.test_threads.append(worker)
        
        self.thread_manager.register_thread(
            "test_worker",
            worker,
            "test"
        )
        
        # Start thread
        self.thread_manager.start_thread("test_worker")
        time.sleep(2)  # Allow time for thread to run
        
        # Check health
        health = self.thread_manager.health_check()
        self.assertEqual(health['status'], 'nominal')
        self.assertIn("test_worker", health['threads'])
        
        # Stop thread
        success = self.thread_manager.stop_thread("test_worker")
        self.assertTrue(success)
    
    def test_plugin_system(self):
        """Test plugin loading and management."""
        # Load plugins
        self.plugin_loader.load_all_plugins()
        
        # Verify memory_analyzer plugin
        self.assertIn(
            'memory_analyzer',
            self.plugin_loader.plugins
        )
        
        # Check plugin health
        health = self.plugin_loader.check_plugin_health('memory_analyzer')
        self.assertEqual(health['status'], 'healthy')
        
        # Test plugin disable/enable
        self.assertTrue(
            self.plugin_loader.disable_plugin('memory_analyzer')
        )
        self.assertTrue(
            self.plugin_loader.enable_plugin('memory_analyzer')
        )
    
    def test_codex_awareness(self):
        """Test memory storage and retrieval."""
        # Store test memory
        memory_id = self.codex_awareness.store_memory(
            content={
                'type': 'test',
                'data': 'test_data'
            },
            source='test',
            tags=['test'],
            confidence=0.9
        )
        
        # Query memory
        results = self.codex_awareness.query_memory(
            query='test',
            tags=['test']
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, memory_id)
        self.assertEqual(results[0].confidence, 0.9)
    
    def test_epistemic_self_check(self):
        """Test system self-awareness capabilities."""
        # Perform self-check
        check_result = epistemic_self_check(
            intent="test_operation",
            available_functions=["test"],
            context={"test": True}
        )
        
        self.assertIn('confidence_level', check_result)
        self.assertIn('knowledge_gaps', check_result)
        self.assertIn('recommendations', check_result)
    
    def test_metacognition_integration(self):
        """Test metacognition engine integration."""
        # Perform system health check
        health = self.metacognition.system_health_check()
        
        self.assertIn('agent_status', health)
        self.assertIn('memory_status', health)
        self.assertIn('thread_health', health)
        self.assertIn('overall_health', health)
        
        # Test decision reflection
        reflection = self.metacognition.reflect_on_decision(
            intent="test_decision",
            context={"test": True},
            available_functions=["test_function"]
        )
        
        self.assertIn('epistemic_check', reflection)
        self.assertIn('relevant_memories', reflection)
        self.assertIn('confidence_assessment', reflection)
    
    def test_full_system_interaction(self):
        """
        Test complete system interaction flow.
        Verifies that all components work together correctly.
        """
        # 1. Initialize test thread
        worker = TestWorkerThread("integration_test", self.thread_manager)
        self.test_threads.append(worker)
        self.thread_manager.register_thread(
            "integration_test",
            worker,
            "test"
        )
        
        # 2. Start thread and verify health
        self.thread_manager.start_thread("integration_test")
        time.sleep(1)
        
        thread_health = self.thread_manager.health_check()
        self.assertEqual(thread_health['status'], 'nominal')
        
        # 3. Store test memory
        memory_id = self.codex_awareness.store_memory(
            content={
                'type': 'integration_test',
                'timestamp': datetime.utcnow().isoformat()
            },
            source='test',
            tags=['integration', 'test'],
            confidence=0.95
        )
        
        # 4. Perform metacognitive reflection
        reflection = self.metacognition.reflect_on_decision(
            intent="integration_test",
            context={
                "thread_health": thread_health,
                "memory_id": memory_id
            },
            available_functions=["test_integration"]
        )
        
        self.assertGreater(
            reflection['confidence_assessment']['confidence_score'],
            0.5
        )
        
        # 5. Store decision outcome
        outcome_id = self.metacognition.store_decision_outcome(
            intent="integration_test",
            outcome={
                "success": True,
                "thread_health": thread_health,
                "reflection": reflection
            },
            confidence=0.9,
            tags=['integration', 'test', 'outcome']
        )
        
        # 6. Verify stored outcome
        results = self.codex_awareness.query_memory(
            query='integration_test',
            tags=['outcome']
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, outcome_id)
        
        # 7. Clean up
        self.thread_manager.stop_thread("integration_test")

def run_tests():
    """Run the integration tests."""
    unittest.main()

if __name__ == '__main__':
    run_tests()
