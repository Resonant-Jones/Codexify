"""
Pattern Analyzer Plugin
--------------------
Analyzes system behavior patterns and generates codex entries.
Demonstrates integration with memory system and codex generation.
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Pattern:
    """Represents a detected system behavior pattern."""
    
    def __init__(
        self,
        pattern_type: str,
        signature: str,
        confidence: float,
        evidence: List[str],
        metadata: Dict[str, Any]
    ):
        self.pattern_type = pattern_type
        self.signature = signature
        self.confidence = confidence
        self.evidence = evidence
        self.metadata = metadata
        self.timestamp = datetime.utcnow()
        self.verified = False
        self.codex_entry: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary representation."""
        return {
            'pattern_type': self.pattern_type,
            'signature': self.signature,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'verified': self.verified,
            'codex_entry': self.codex_entry
        }

class PatternAnalyzer:
    """Core pattern analysis functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.codex = CodexAwareness()
        self.metacognition = MetacognitionEngine()
        self.patterns: Dict[str, Pattern] = {}
        self.running = False
        self.analysis_thread: Optional[threading.Thread] = None
        self.last_analysis: Optional[datetime] = None
    
    def start(self) -> bool:
        """Start the pattern analyzer."""
        try:
            self.running = True
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                daemon=True
            )
            self.analysis_thread.start()
            logger.info("Pattern analyzer started")
            return True
        except Exception as e:
            logger.error(f"Failed to start pattern analyzer: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the pattern analyzer."""
        try:
            self.running = False
            if self.analysis_thread:
                self.analysis_thread.join(timeout=5.0)
            logger.info("Pattern analyzer stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop pattern analyzer: {e}")
            return False
    
    def _analysis_loop(self) -> None:
        """Main analysis loop."""
        while self.running:
            try:
                self._analyze_patterns()
                time.sleep(self.config['analysis_interval'])
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                time.sleep(10)  # Error backoff
    
    def _analyze_patterns(self) -> None:
        """Perform pattern analysis."""
        try:
            # Query recent memory artifacts
            recent_memories = self.codex.query_memory(
                query="timestamp:[now-1h TO now]",
                min_confidence=self.config['min_confidence']
            )
            
            # Analyze different pattern types
            for pattern_type in self.config['pattern_types']:
                patterns = self._analyze_pattern_type(
                    pattern_type,
                    recent_memories
                )
                
                # Generate codex entries for new patterns
                for pattern in patterns:
                    if pattern.signature not in self.patterns:
                        self._generate_codex_entry(pattern)
                        self.patterns[pattern.signature] = pattern
            
            # Clean up old patterns
            self._cleanup_patterns()
            
            self.last_analysis = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
    
    def _analyze_pattern_type(
        self,
        pattern_type: str,
        memories: List[Any]
    ) -> List[Pattern]:
        """Analyze specific type of patterns."""
        patterns: List[Pattern] = []
        
        if pattern_type == "behavioral":
            patterns.extend(
                self._analyze_behavioral_patterns(memories)
            )
        elif pattern_type == "temporal":
            patterns.extend(
                self._analyze_temporal_patterns(memories)
            )
        elif pattern_type == "structural":
            patterns.extend(
                self._analyze_structural_patterns(memories)
            )
        elif pattern_type == "relational":
            patterns.extend(
                self._analyze_relational_patterns(memories)
            )
        
        return patterns
    
    def _analyze_behavioral_patterns(
        self,
        memories: List[Any]
    ) -> List[Pattern]:
        """Analyze behavioral patterns in system operations."""
        patterns: List[Pattern] = []
        
        # Group memories by operation type
        operations: Dict[str, List[Any]] = {}
        for memory in memories:
            if hasattr(memory, 'content'):
                op_type = memory.content.get('operation_type')
                if op_type:
                    operations.setdefault(op_type, []).append(memory)
        
        # Analyze operation sequences
        for op_type, op_memories in operations.items():
            if len(op_memories) >= 3:  # Minimum sequence length
                # Look for repeated sequences
                sequences = self._find_sequences(op_memories)
                
                for seq in sequences:
                    pattern = Pattern(
                        pattern_type="behavioral",
                        signature=f"behavior_{op_type}_{hash(str(seq))}",
                        confidence=self._calculate_sequence_confidence(seq),
                        evidence=[m.id for m in seq],
                        metadata={
                            'operation_type': op_type,
                            'sequence_length': len(seq),
                            'frequency': self._calculate_sequence_frequency(
                                seq,
                                op_memories
                            )
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_temporal_patterns(
        self,
        memories: List[Any]
    ) -> List[Pattern]:
        """Analyze temporal patterns in system events."""
        patterns: List[Pattern] = []
        
        # Group memories by time intervals
        intervals = self._group_by_intervals(memories, timedelta(minutes=5))
        
        # Analyze interval patterns
        for interval, interval_memories in intervals.items():
            if len(interval_memories) >= 3:
                # Look for periodic events
                periodic = self._find_periodic_events(interval_memories)
                
                for period, events in periodic.items():
                    pattern = Pattern(
                        pattern_type="temporal",
                        signature=f"temporal_{interval}_{period}",
                        confidence=self._calculate_periodic_confidence(events),
                        evidence=[e.id for e in events],
                        metadata={
                            'interval': str(interval),
                            'period': period,
                            'event_count': len(events)
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_structural_patterns(
        self,
        memories: List[Any]
    ) -> List[Pattern]:
        """Analyze structural patterns in system components."""
        patterns: List[Pattern] = []
        
        # Build component dependency graph
        dependencies = self._build_dependency_graph(memories)
        
        # Find structural patterns
        structural_patterns = self._find_structural_patterns(dependencies)
        
        for pattern_type, components in structural_patterns.items():
            pattern = Pattern(
                pattern_type="structural",
                signature=f"structure_{pattern_type}_{hash(str(components))}",
                confidence=self._calculate_structural_confidence(components),
                evidence=[str(c) for c in components],
                metadata={
                    'pattern_type': pattern_type,
                    'component_count': len(components),
                    'dependencies': dependencies
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _analyze_relational_patterns(
        self,
        memories: List[Any]
    ) -> List[Pattern]:
        """Analyze relational patterns between system elements."""
        patterns: List[Pattern] = []
        
        # Build relationship graph
        relationships = self._build_relationship_graph(memories)
        
        # Find clusters and patterns
        clusters = self._find_relationship_clusters(relationships)
        
        for cluster_type, elements in clusters.items():
            pattern = Pattern(
                pattern_type="relational",
                signature=f"relation_{cluster_type}_{hash(str(elements))}",
                confidence=self._calculate_relational_confidence(elements),
                evidence=[str(e) for e in elements],
                metadata={
                    'cluster_type': cluster_type,
                    'element_count': len(elements),
                    'relationship_strength': self._calculate_relationship_strength(
                        elements,
                        relationships
                    )
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _find_sequences(
        self,
        memories: List[Any]
    ) -> List[List[Any]]:
        """Find repeated sequences in memories."""
        sequences: List[List[Any]] = []
        min_length = 3
        
        for i in range(len(memories) - min_length + 1):
            for j in range(i + min_length, len(memories) + 1):
                sequence = memories[i:j]
                # Check if sequence repeats
                if self._is_repeated_sequence(sequence, memories):
                    sequences.append(sequence)
        
        return sequences
    
    def _is_repeated_sequence(
        self,
        sequence: List[Any],
        memories: List[Any]
    ) -> bool:
        """Check if a sequence repeats in memories."""
        seq_str = self._sequence_to_string(sequence)
        mem_str = self._sequence_to_string(memories)
        
        # Count occurrences
        return mem_str.count(seq_str) > 1
    
    def _sequence_to_string(self, sequence: List[Any]) -> str:
        """Convert sequence to string representation."""
        return ','.join(
            str(getattr(m, 'content', {}).get('operation_type', ''))
            for m in sequence
        )
    
    def _calculate_sequence_confidence(
        self,
        sequence: List[Any]
    ) -> float:
        """Calculate confidence in a behavioral sequence."""
        if not sequence:
            return 0.0
        
        # Consider sequence length
        length_factor = min(len(sequence) / 10.0, 1.0)
        
        # Consider memory confidence
        confidence_avg = sum(
            getattr(m, 'confidence', 0.0) for m in sequence
        ) / len(sequence)
        
        return (length_factor + confidence_avg) / 2.0
    
    def _calculate_sequence_frequency(
        self,
        sequence: List[Any],
        memories: List[Any]
    ) -> float:
        """Calculate frequency of a sequence in memories."""
        seq_str = self._sequence_to_string(sequence)
        mem_str = self._sequence_to_string(memories)
        
        count = mem_str.count(seq_str)
        max_possible = len(memories) - len(sequence) + 1
        
        return count / max_possible if max_possible > 0 else 0.0
    
    def _group_by_intervals(
        self,
        memories: List[Any],
        interval: timedelta
    ) -> Dict[str, List[Any]]:
        """Group memories by time intervals."""
        intervals: Dict[str, List[Any]] = {}
        
        for memory in memories:
            if hasattr(memory, 'timestamp'):
                interval_start = memory.timestamp.replace(
                    minute=memory.timestamp.minute // 5 * 5,
                    second=0,
                    microsecond=0
                )
                interval_key = interval_start.isoformat()
                intervals.setdefault(interval_key, []).append(memory)
        
        return intervals
    
    def _find_periodic_events(
        self,
        memories: List[Any]
    ) -> Dict[str, List[Any]]:
        """Find periodic events in memories."""
        periodic: Dict[str, List[Any]] = {}
        
        # Group by event type
        events: Dict[str, List[Any]] = {}
        for memory in memories:
            if hasattr(memory, 'content'):
                event_type = memory.content.get('event_type')
                if event_type:
                    events.setdefault(event_type, []).append(memory)
        
        # Find periodic patterns
        for event_type, event_memories in events.items():
            if self._is_periodic(event_memories):
                period = self._calculate_period(event_memories)
                periodic[f"{event_type}_{period}"] = event_memories
        
        return periodic
    
    def _is_periodic(self, memories: List[Any]) -> bool:
        """Check if events show periodic behavior."""
        if len(memories) < 3:
            return False
        
        # Calculate intervals between events
        intervals = []
        for i in range(1, len(memories)):
            if hasattr(memories[i], 'timestamp') and hasattr(memories[i-1], 'timestamp'):
                interval = (
                    memories[i].timestamp - memories[i-1].timestamp
                ).total_seconds()
                intervals.append(interval)
        
        if not intervals:
            return False
        
        # Check if intervals are consistent
        avg_interval = sum(intervals) / len(intervals)
        variance = sum(
            (i - avg_interval) ** 2 for i in intervals
        ) / len(intervals)
        
        # Low variance indicates periodicity
        return variance < (avg_interval * 0.2)
    
    def _calculate_period(self, memories: List[Any]) -> str:
        """Calculate the period of periodic events."""
        intervals = []
        for i in range(1, len(memories)):
            if hasattr(memories[i], 'timestamp') and hasattr(memories[i-1], 'timestamp'):
                interval = (
                    memories[i].timestamp - memories[i-1].timestamp
                ).total_seconds()
                intervals.append(interval)
        
        if not intervals:
            return "unknown"
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Convert to human-readable period
        if avg_interval < 60:
            return f"{int(avg_interval)}s"
        elif avg_interval < 3600:
            return f"{int(avg_interval/60)}m"
        else:
            return f"{int(avg_interval/3600)}h"
    
    def _generate_codex_entry(self, pattern: Pattern) -> None:
        """Generate codex entry for a pattern."""
        try:
            entry_content = {
                'type': 'pattern_codex',
                'pattern': pattern.to_dict(),
                'analysis': self._generate_pattern_analysis(pattern),
                'implications': self._generate_pattern_implications(pattern),
                'recommendations': self._generate_pattern_recommendations(pattern)
            }
            
            # Store in codex
            pattern.codex_entry = self.codex.store_memory(
                content=entry_content,
                source='pattern_analyzer',
                tags=['pattern', pattern.pattern_type, 'codex'],
                confidence=pattern.confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to generate codex entry: {e}")
    
    def _generate_pattern_analysis(
        self,
        pattern: Pattern
    ) -> Dict[str, Any]:
        """Generate analysis of pattern characteristics."""
        return {
            'characteristics': {
                'frequency': self._analyze_pattern_frequency(pattern),
                'stability': self._analyze_pattern_stability(pattern),
                'impact': self._analyze_pattern_impact(pattern)
            },
            'context': {
                'system_state': self._get_system_state_context(pattern),
                'related_patterns': self._find_related_patterns(pattern)
            }
        }
    
    def _generate_pattern_implications(
        self,
        pattern: Pattern
    ) -> List[Dict[str, Any]]:
        """Generate implications of the pattern."""
        implications = []
        
        # Performance implications
        perf_impact = self._analyze_performance_impact(pattern)
        if perf_impact:
            implications.append({
                'type': 'performance',
                'description': perf_impact['description'],
                'severity': perf_impact['severity']
            })
        
        # Resource implications
        resource_impact = self._analyze_resource_impact(pattern)
        if resource_impact:
            implications.append({
                'type': 'resource',
                'description': resource_impact['description'],
                'severity': resource_impact['severity']
            })
        
        # Stability implications
        stability_impact = self._analyze_stability_impact(pattern)
        if stability_impact:
            implications.append({
                'type': 'stability',
                'description': stability_impact['description'],
                'severity': stability_impact['severity']
            })
        
        return implications
    
    def _generate_pattern_recommendations(
        self,
        pattern: Pattern
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on pattern analysis."""
        recommendations = []
        
        # Performance optimization recommendations
        if pattern.pattern_type == "behavioral":
            recommendations.extend(
                self._generate_behavioral_recommendations(pattern)
            )
        
        # Resource management recommendations
        elif pattern.pattern_type == "structural":
            recommendations.extend(
                self._generate_structural_recommendations(pattern)
            )
        
        # Monitoring recommendations
        recommendations.extend(
            self._generate_monitoring_recommendations(pattern)
        )
        
        return recommendations
    
    def _cleanup_patterns(self) -> None:
        """Clean up old or invalid patterns."""
        current_time = datetime.utcnow()
        
        # Remove patterns older than 24 hours
        self.patterns = {
            sig: pattern
            for sig, pattern in self.patterns.items()
            if (current_time - pattern.timestamp) < timedelta(hours=24)
        }
        
        # Limit total number of patterns
        if len(self.patterns) > self.config['max_patterns']:
            # Sort by confidence and keep top patterns
            sorted_patterns = sorted(
                self.patterns.items(),
                key=lambda x: x[1].confidence,
                reverse=True
            )
            self.patterns = dict(
                sorted_patterns[:self.config['max_patterns']]
            )

# Global analyzer instance
analyzer: Optional[PatternAnalyzer] = None

def init_plugin() -> bool:
    """Initialize the plugin."""
    try:
        # Load configuration
        plugin_dir = Path(__file__).parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            config = json.load(f)
        
        # Create and start analyzer
        global analyzer
        analyzer = PatternAnalyzer(config['config'])
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
        if not analyzer.last_analysis:
            return {
                'status': 'warning',
                'message': 'No analysis performed yet'
            }
        
        age = datetime.utcnow() - analyzer.last_analysis
        if age > timedelta(
            seconds=analyzer.config['analysis_interval'] * 2
        ):
            return {
                'status': 'warning',
                'message': f'Analysis is delayed: {age}'
            }
        
        return {
            'status': 'healthy',
            'message': 'Pattern analyzer is running normally',
            'metrics': {
                'last_analysis': analyzer.last_analysis.isoformat(),
                'pattern_count': len(analyzer.patterns),
                'types_analyzed': analyzer.config['pattern_types']
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
