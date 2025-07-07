"""
Pattern Analyzer Plugin Tests
--------------------------
Test suite for pattern analysis functionality.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestPatternAnalyzer(unittest.TestCase):
    """Test suite for pattern analyzer plugin."""
    
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
        from ..main import PatternAnalyzer
        self.analyzer = PatternAnalyzer(self.config)
        self.analyzer.codex = self.codex
        self.analyzer.metacognition = self.metacognition
    
    async def test_initialization(self):
        """Test plugin initialization."""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.config, self.config)
    
    async def test_pattern_analysis(self):
        """Test pattern analysis functionality."""
        # Mock data
        test_data = [
            {
                'id': 'data1',
                'content': 'recurring pattern X',
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {'type': 'test'}
            },
            {
                'id': 'data2',
                'content': 'recurring pattern X',
                'timestamp': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                'metadata': {'type': 'test'}
            }
        ]
        
        self.codex.query_data.return_value = test_data
        
        # Run analysis
        result = await self.analyzer.analyze_patterns()
        
        # Verify analysis
        self.assertIsNotNone(result)
        self.assertIn('patterns', result)
        self.assertIn('metrics', result)
    
    async def test_temporal_pattern_detection(self):
        """Test temporal pattern detection."""
        # Mock time series data
        time_series = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'value': 1.0
            },
            {
                'timestamp': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                'value': 2.0
            },
            {
                'timestamp': (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                'value': 3.0
            }
        ]
        
        # Detect patterns
        patterns = await self.analyzer.detect_temporal_patterns(time_series)
        
        # Verify patterns
        self.assertTrue(len(patterns) > 0)
        self.assertIn('trend', patterns[0])
    
    async def test_sequence_pattern_detection(self):
        """Test sequence pattern detection."""
        # Mock sequence data
        sequences = [
            ['A', 'B', 'C'],
            ['A', 'B', 'C'],
            ['X', 'Y', 'Z']
        ]
        
        # Detect patterns
        patterns = await self.analyzer.detect_sequence_patterns(sequences)
        
        # Verify patterns
        self.assertTrue(len(patterns) > 0)
        self.assertIn(['A', 'B', 'C'], patterns)
    
    async def test_anomaly_detection(self):
        """Test anomaly detection."""
        # Mock data with anomalies
        test_data = [1.0, 1.1, 1.0, 5.0, 1.2, 1.0]
        
        # Detect anomalies
        anomalies = await self.analyzer.detect_anomalies(test_data)
        
        # Verify anomalies
        self.assertTrue(len(anomalies) > 0)
        self.assertEqual(anomalies[0]['index'], 3)
        self.assertEqual(anomalies[0]['value'], 5.0)
    
    async def test_pattern_classification(self):
        """Test pattern classification."""
        # Test pattern
        pattern = {
            'sequence': ['A', 'B', 'C'],
            'frequency': 10,
            'confidence': 0.9
        }
        
        # Classify pattern
        classification = self.analyzer.classify_pattern(pattern)
        
        # Verify classification
        self.assertIn('type', classification)
        self.assertIn('significance', classification)
    
    async def test_error_handling(self):
        """Test error handling during analysis."""
        # Mock error in analysis
        self.codex.query_data.side_effect = Exception("Test error")
        
        # Run analysis
        with self.assertRaises(Exception):
            await self.analyzer.analyze_patterns()
        
        # Verify error handling
        self.metacognition.handle_error.assert_called_once()
    
    def test_pattern_metrics(self):
        """Test pattern metrics calculation."""
        # Mock patterns
        patterns = [
            {
                'sequence': ['A', 'B'],
                'frequency': 5,
                'confidence': 0.8
            },
            {
                'sequence': ['X', 'Y'],
                'frequency': 3,
                'confidence': 0.6
            }
        ]
        
        # Calculate metrics
        metrics = self.analyzer.calculate_pattern_metrics(patterns)
        
        # Verify metrics
        self.assertIn('total_patterns', metrics)
        self.assertIn('average_confidence', metrics)
        self.assertEqual(metrics['total_patterns'], 2)
        self.assertAlmostEqual(metrics['average_confidence'], 0.7)
    
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
