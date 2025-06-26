"""
Memory Analyzer Plugin
-------------------
Analyzes system memory patterns and provides insights on memory usage.
Demonstrates proper plugin implementation and best practices.
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryAnalyzer:
    """Core memory analysis functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics: Dict[str, Any] = {}
        self.patterns: List[Dict[str, Any]] = []
        self.last_analysis: Optional[datetime] = None
        self.running = False
        self.lock = threading.Lock()
        self.analysis_thread: Optional[threading.Thread] = None
    
    def start(self) -> bool:
        """Start the analysis thread."""
        try:
            self.running = True
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                daemon=True
            )
            self.analysis_thread.start()
            logger.info("Memory analyzer started")
            return True
        except Exception as e:
            logger.error(f"Failed to start memory analyzer: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the analysis thread."""
        try:
            self.running = False
            if self.analysis_thread:
                self.analysis_thread.join(timeout=5.0)
            logger.info("Memory analyzer stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop memory analyzer: {e}")
            return False
    
    def _analysis_loop(self) -> None:
        """Main analysis loop."""
        while self.running:
            try:
                self._perform_analysis()
                time.sleep(self.config['analysis_interval'])
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                time.sleep(10)  # Error backoff
    
    def _perform_analysis(self) -> None:
        """Perform memory analysis."""
        with self.lock:
            current_time = datetime.utcnow()
            
            # Collect memory metrics
            metrics = self._collect_metrics()
            
            # Analyze patterns
            patterns = self._analyze_patterns(metrics)
            
            # Update state
            self.metrics = metrics
            self.patterns.extend(patterns)
            self.last_analysis = current_time
            
            # Cleanup old data
            self._cleanup_old_data()
            
            # Check thresholds
            self._check_thresholds(metrics)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current memory metrics."""
        # This is a simplified example - in practice, you would
        # collect real memory metrics from the system
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_memory': 1000,
            'used_memory': 500,
            'memory_patterns': [
                {'type': 'cyclic', 'confidence': 0.8},
                {'type': 'growth', 'confidence': 0.6}
            ]
        }
    
    def _analyze_patterns(
        self,
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze memory usage patterns."""
        patterns = []
        
        # Example pattern detection
        usage_ratio = metrics['used_memory'] / metrics['total_memory']
        if usage_ratio > 0.8:
            patterns.append({
                'type': 'high_usage',
                'timestamp': datetime.utcnow().isoformat(),
                'value': usage_ratio,
                'confidence': 0.9
            })
        
        return patterns
    
    def _cleanup_old_data(self) -> None:
        """Remove data older than retention period."""
        retention = timedelta(seconds=self.config['retention_period'])
        current_time = datetime.utcnow()
        
        self.patterns = [
            p for p in self.patterns
            if (current_time - datetime.fromisoformat(p['timestamp'])) <= retention
        ]
    
    def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check if metrics exceed configured thresholds."""
        usage_ratio = metrics['used_memory'] / metrics['total_memory']
        if usage_ratio > self.config['alert_threshold']:
            logger.warning(
                f"Memory usage ({usage_ratio:.2%}) exceeds threshold "
                f"({self.config['alert_threshold']:.2%})"
            )

# Global analyzer instance
analyzer: Optional[MemoryAnalyzer] = None

def init_plugin() -> bool:
    """Initialize the plugin."""
    try:
        # Load configuration
        plugin_dir = Path(__file__).parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            config = json.load(f)
        
        # Create and start analyzer
        global analyzer
        analyzer = MemoryAnalyzer(config['config'])
        return analyzer.start()
        
    except Exception as e:
        logger.error(f"Plugin initialization failed: {e}")
        return False

def cleanup() -> bool:
    """Clean up plugin resources."""
    try:
        if analyzer:
            return analyzer.stop()
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
    if not analyzer:
        return {
            'status': 'error',
            'message': 'Analyzer not initialized'
        }
    
    try:
        with analyzer.lock:
            if not analyzer.last_analysis:
                return {
                    'status': 'warning',
                    'message': 'No analysis performed yet'
                }
            
            age = datetime.utcnow() - analyzer.last_analysis
            if age > timedelta(seconds=analyzer.config['analysis_interval'] * 2):
                return {
                    'status': 'warning',
                    'message': f'Analysis is delayed: {age}'
                }
            
            return {
                'status': 'healthy',
                'message': 'Analyzer is running normally',
                'metrics': {
                    'last_analysis': analyzer.last_analysis.isoformat(),
                    'pattern_count': len(analyzer.patterns),
                    'current_usage': analyzer.metrics.get('used_memory', 0) / 
                                   analyzer.metrics.get('total_memory', 1)
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
        
        # Wait for some analysis
        time.sleep(10)
        
        # Check health
        health = health_check()
        print("\nHealth Status:")
        print(json.dumps(health, indent=2))
        
        # Cleanup
        cleanup()
    else:
        print("Plugin initialization failed")
