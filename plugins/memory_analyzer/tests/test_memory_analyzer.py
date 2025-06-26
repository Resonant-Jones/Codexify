"""
Memory Analyzer Plugin Tests
--------------------------
Test suite for memory analysis functionality.
"""

import asyncio
import json
import logging
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMemoryAnalyzer(unittest.TestCase):
    """Test suite for memory analyzer plugin."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test resources."""
        # Load plugin configuration
        plugin_dir = Path(__file__).parent.parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            cls.config = json.load(f)['config']
    
    def setUp(self):
        """Set up test-specific resources."""
        # Mock dependencies
        self.codex = MagicMock(spec=CodexAwareness)
        self.metacognition = MagicMock(spec=MetacognitionEngine)
        
        # Initialize plugin
        from ..main import MemoryAnalyzer
        self.analyzer = MemoryAnalyzer(self.config)
        self.analyzer.codex = self.codex
        self.analyzer.metacognition = self.metacognition
    
    async def test_initialization(self):
        """Test plugin initialization."""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.config, self.config)
    
    async def test_memory_analysis(self):
        """Test memory analysis functionality."""
        # Mock memory data
        test_memories = [
            {
                'id': 'mem1',
                'content': 'test memory 1',
                'timestamp': '2024-01-01T00:00:00Z',
                'tags': ['test']
            },
            {
                'id': 'mem2',
                'content': 'test memory 2',
                'timestamp': '2024-01-02T00:00:00Z',
                'tags': ['test']
            }
        ]
        
        self.codex.query_memories.return_value = test_memories
        
        # Run analysis
        result = await self.analyzer.analyze_memories()
        
        # Verify analysis
        self.assertIsNotNone(result)
        self.assertIn('patterns', result)
        self.assertIn('statistics', result)
    
    async def test_pattern_detection(self):
        """Test pattern detection in memories."""
        # Mock memory data with patterns
        test_memories = [
            {
                'id': 'mem1',
                'content': 'recurring pattern A',
                'timestamp': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'mem2',
                'content': 'recurring pattern A',
                'timestamp': '2024-01-02T00:00:00Z'
            },
            {
                'id': 'mem3',
                'content': 'unique content',
                'timestamp': '2024-01-03T00:00:00Z'
            }
        ]
        
        self.codex.query_memories.return_value = test_memories
        
        # Run pattern detection
        patterns = await self.analyzer.detect_patterns(test_memories)
        
        # Verify patterns
        self.assertTrue(len(patterns) > 0)
        self.assertIn('recurring pattern A', str(patterns[0]))
    
    async def test_memory_statistics(self):
        """Test memory statistics calculation."""
        # Mock memory data
        test_memories = [
            {
                'id': 'mem1',
                'content': 'test content',
                'timestamp': '2024-01-01T00:00:00Z',
                'confidence': 0.8
            },
            {
                'id': 'mem2',
                'content': 'test content',
                'timestamp': '2024-01-02T00:00:00Z',
                'confidence': 0.9
            }
        ]
        
        # Calculate statistics
        stats = self.analyzer.calculate_statistics(test_memories)
        
        # Verify statistics
        self.assertIn('total_memories', stats)
        self.assertIn('average_confidence', stats)
        self.assertEqual(stats['total_memories'], 2)
        self.assertAlmostEqual(stats['average_confidence'], 0.85)
    
    async def test_error_handling(self):
        """Test error handling during analysis."""
        # Mock error in codex
        self.codex.query_memories.side_effect = Exception("Test error")
        
        # Run analysis
        with self.assertRaises(Exception):
            await self.analyzer.analyze_memories()
        
        # Verify error handling
        self.metacognition.handle_error.assert_called_once()
    
    async def test_memory_filtering(self):
        """Test memory filtering functionality."""
        # Mock memory data
        test_memories = [
            {
                'id': 'mem1',
                'content': 'important memory',
                'tags': ['important']
            },
            {
                'id': 'mem2',
                'content': 'regular memory',
                'tags': ['regular']
            }
        ]
        
        # Filter memories
        filtered = self.analyzer.filter_memories(
            test_memories,
            tags=['important']
        )
        
        # Verify filtering
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 'mem1')
    
    def test_plugin_metadata(self):
        """Test plugin metadata."""
        metadata = self.analyzer.get_metadata()
        
        self.assertIn('name', metadata)
        self.assertIn('version', metadata)
        self.assertIn('description', metadata)
        self.assertIn('capabilities', metadata)
    
    def test_health_check(self):
        """Test plugin health check."""
        health = self.analyzer.health_check()
        
        self.assertIn('status', health)
        self.assertIn('timestamp', health)
        self.assertEqual(health['status'], 'healthy')

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == '__main__':
    run_tests()
