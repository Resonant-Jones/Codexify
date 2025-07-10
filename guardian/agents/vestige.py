"""
Vestige Agent
------------
Long-term memory and pattern recognition system.
Preserves and analyzes system memory artifacts, identifying patterns and relationships.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from guardian.codex_awareness import CodexAwareness, MemoryArtifact
from guardian.metacognition import MetacognitionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryPattern:
    """Represents a detected pattern in memory artifacts."""

    def __init__(
        self,
        pattern_type: str,
        confidence: float,
        artifacts: List[str],
        metadata: Dict[str, Any],
    ):
        self.pattern_type = pattern_type
        self.confidence = confidence
        self.artifacts = artifacts
        self.metadata = metadata
        self.timestamp = datetime.utcnow()
        self.verified = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary representation."""
        return {
            "pattern_type": self.pattern_type,
            "confidence": self.confidence,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "verified": self.verified,
        }


class VestigeAgent:
    """
    Core memory preservation and analysis agent.
    Maintains long-term memory coherence and identifies patterns.
    """

    def __init__(self, codex: CodexAwareness, metacognition: MetacognitionEngine):
        self.codex = codex
        self.metacognition = metacognition
        self.patterns: List[MemoryPattern] = []
        self.active_analyses: Set[str] = set()
        self.last_checkpoint: Optional[datetime] = None

    async def process_memory(
        self, memory_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a new memory artifact.

        Args:
            memory_id: ID of the memory to process
            context: Optional processing context

        Returns:
            Dict containing processing results
        """
        try:
            # Get memory artifact directly
            memory = self.codex.artifacts.get(memory_id)
            if not memory:
                logger.warning(f"Memory {memory_id} not found.")
                return {
                    "status": "error",
                    "memory_id": memory_id,
                    "error": f"Memory ID '{memory_id}' not found.",
                }

            # Check for existing patterns
            related_patterns = self._find_related_patterns(memory)

            # Analyze for new patterns
            new_patterns = await self._analyze_patterns(
                memory, related_patterns, context
            )

            # Update memory relationships
            self._update_relationships(memory, new_patterns)

            # Store analysis results
            analysis_id = self.codex.store_memory(
                content={
                    "type": "memory_analysis",
                    "memory_id": memory_id,
                    "patterns": [p.to_dict() for p in new_patterns],
                    "related_patterns": [p.to_dict() for p in related_patterns],
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="vestige",
                tags=["analysis", "patterns"],
                confidence=self._calculate_confidence(new_patterns),
            )

            return {
                "status": "success",
                "memory_id": memory_id,
                "analysis_id": analysis_id,
                "pattern_count": len(new_patterns),
                "confidence": self._calculate_confidence(new_patterns),
            }

        except Exception as e:
            logger.error(f"Memory processing failed: {e}")
            return {"status": "error", "memory_id": memory_id, "error": str(e)}

    async def analyze_patterns(
        self, time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> List[MemoryPattern]:
        """
        Analyze patterns across memory artifacts.

        Args:
            time_window: Optional time range to analyze

        Returns:
            List of detected patterns
        """
        try:
            # Query relevant memories
            query = "type:memory_analysis"
            if time_window:
                start, end = time_window
                query += f" timestamp:[{start.isoformat()} TO {end.isoformat()}]"

            memories = self.codex.query_memory(query=query, min_confidence=0.5)

            patterns: List[MemoryPattern] = []

            # Temporal pattern analysis
            temporal_patterns = self._analyze_temporal_patterns(memories)
            patterns.extend(temporal_patterns)

            # Relationship pattern analysis
            relationship_patterns = self._analyze_relationship_patterns(memories)
            patterns.extend(relationship_patterns)

            # Content pattern analysis for each memory
            for memory in memories:
                if hasattr(memory, "content"):
                    content_patterns = self._analyze_content_patterns(
                        memory.content, None
                    )
                    patterns.extend(content_patterns)

            # Verify patterns
            verified_patterns = await self._verify_patterns(patterns)

            # Store verified patterns
            for pattern in verified_patterns:
                if pattern.verified:
                    self.patterns.append(pattern)

            # If no patterns were found or verified, return a base unclassified pattern
            if not verified_patterns:
                logger.warning("No patterns detected, returning unclassified pattern")
                return [
                    MemoryPattern(
                        pattern_type="unclassified",
                        confidence=0.3,
                        artifacts=(
                            [str(m.id) for m in memories] if memories else ["unknown"]
                        ),
                        metadata={
                            "memory_count": len(memories),
                            "analysis_timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                ]

            return verified_patterns

        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            # Return error pattern instead of empty list
            return [
                MemoryPattern(
                    pattern_type="error",
                    confidence=0.1,
                    artifacts=["error"],
                    metadata={
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            ]

    def _find_related_patterns(self, memory: Any) -> List[MemoryPattern]:
        """Find patterns related to a memory artifact."""
        return [pattern for pattern in self.patterns if memory.id in pattern.artifacts]

    async def _analyze_patterns(
        self,
        memory: Any,
        related_patterns: List[MemoryPattern],
        context: Optional[Dict[str, Any]],
    ) -> List[MemoryPattern]:
        """Analyze memory for new patterns."""
        patterns: List[MemoryPattern] = []

        # Content pattern analysis
        if hasattr(memory, "content"):
            content_patterns = self._analyze_content_patterns(memory.content, context)
            patterns.extend(content_patterns)

        # Temporal pattern analysis
        if hasattr(memory, "timestamp"):
            temporal_patterns = self._analyze_temporal_patterns([memory])
            patterns.extend(temporal_patterns)

        # Relationship pattern analysis
        if related_patterns:
            relationship_patterns = self._analyze_relationship_patterns([memory])
            patterns.extend(relationship_patterns)

        return patterns

    def _analyze_content_patterns(
        self, content: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> List[MemoryPattern]:
        """Analyze patterns in memory content."""
        patterns: List[MemoryPattern] = []

        try:
            # Basic structure pattern
            if isinstance(content, dict):
                patterns.append(
                    MemoryPattern(
                        pattern_type="structure",
                        confidence=0.6,
                        artifacts=[str(content)],
                        metadata={
                            "keys": list(content.keys()),
                            "depth": self._get_dict_depth(content),
                        },
                    )
                )

                # Check for repeated keys
                key_frequency = {}
                for key in content.keys():
                    key_frequency[key] = key_frequency.get(key, 0) + 1

                for key, freq in key_frequency.items():
                    if freq > 1:
                        patterns.append(
                            MemoryPattern(
                                pattern_type="repeated_key",
                                confidence=0.8,
                                artifacts=[str(content)],
                                metadata={"key": key, "frequency": freq},
                            )
                        )

            # Sequence patterns in lists
            for key, value in content.items():
                if isinstance(value, list):
                    sequence_pattern = self._analyze_sequence(value)
                    if sequence_pattern:
                        patterns.append(sequence_pattern)

            # If no patterns found, add a fallback pattern
            if not patterns:
                patterns.append(
                    MemoryPattern(
                        pattern_type="unclassified",
                        confidence=0.3,
                        artifacts=[str(content)],
                        metadata={
                            "content_type": str(type(content)),
                            "size": len(str(content)),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Content pattern analysis failed: {e}")
            # Add error pattern instead of failing
            patterns.append(
                MemoryPattern(
                    pattern_type="error",
                    confidence=0.1,
                    artifacts=[str(content)],
                    metadata={"error": str(e)},
                )
            )

        return patterns

    def _get_dict_depth(self, d: Dict) -> int:
        """Calculate the maximum depth of a nested dictionary."""
        if not isinstance(d, dict) or not d:
            return 0
        return 1 + max(
            self._get_dict_depth(v) if isinstance(v, dict) else 0 for v in d.values()
        )

    def _analyze_sequence(self, seq: List) -> Optional[MemoryPattern]:
        """Analyze a sequence for patterns."""
        if not seq or len(seq) < 2:
            return None

        # Check for repeating elements
        element_counts = {}
        for elem in seq:
            element_counts[str(elem)] = element_counts.get(str(elem), 0) + 1

        if any(count > 1 for count in element_counts.values()):
            return MemoryPattern(
                pattern_type="sequence",
                confidence=0.7,
                artifacts=[str(seq)],
                metadata={
                    "length": len(seq),
                    "unique_elements": len(element_counts),
                    "repetitions": {k: v for k, v in element_counts.items() if v > 1},
                },
            )

        return None

    def _analyze_temporal_patterns(self, memories: List[Any]) -> List[MemoryPattern]:
        """Analyze temporal patterns in memories."""
        patterns: List[MemoryPattern] = []

        if not memories:
            return patterns

        # Sort memories by timestamp
        sorted_memories = sorted(
            memories, key=lambda m: getattr(m, "timestamp", datetime.min)
        )

        # Check for periodic patterns
        intervals = []
        for i in range(1, len(sorted_memories)):
            interval = getattr(sorted_memories[i], "timestamp", datetime.min) - getattr(
                sorted_memories[i - 1], "timestamp", datetime.min
            )
            intervals.append(interval.total_seconds())

        if intervals:
            # Check for regular intervals
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)

            if variance < avg_interval * 0.1:  # Low variance indicates regularity
                patterns.append(
                    MemoryPattern(
                        pattern_type="periodic",
                        confidence=0.9,
                        artifacts=[str(m.id) for m in memories],
                        metadata={"interval": avg_interval, "variance": variance},
                    )
                )

        return patterns

    def _analyze_relationship_patterns(
        self, memories: List[Any]
    ) -> List[MemoryPattern]:
        """Analyze relationship patterns between memories."""
        patterns: List[MemoryPattern] = []

        # Build relationship graph
        relationships = {}
        for memory in memories:
            if hasattr(memory, "related_artifacts"):
                for related_id in memory.related_artifacts:
                    relationships.setdefault(memory.id, set()).add(related_id)

        # Find clusters
        clusters = self._find_memory_clusters(relationships)

        # Create patterns for significant clusters
        for cluster in clusters:
            if len(cluster) > 2:  # Minimum cluster size
                patterns.append(
                    MemoryPattern(
                        pattern_type="relationship_cluster",
                        confidence=0.7,
                        artifacts=list(cluster),
                        metadata={"cluster_size": len(cluster)},
                    )
                )

        return patterns

    def _find_memory_clusters(
        self, relationships: Dict[str, Set[str]]
    ) -> List[Set[str]]:
        """Find clusters of related memories."""
        clusters: List[Set[str]] = []
        visited = set()

        def dfs(memory_id: str, current_cluster: Set[str]):
            """Depth-first search to find connected memories."""
            if memory_id in visited:
                return
            visited.add(memory_id)
            current_cluster.add(memory_id)

            for related_id in relationships.get(memory_id, set()):
                dfs(related_id, current_cluster)

        # Find all clusters
        for memory_id in relationships:
            if memory_id not in visited:
                current_cluster = set()
                dfs(memory_id, current_cluster)
                if current_cluster:
                    clusters.append(current_cluster)

        return clusters

    async def _verify_patterns(
        self, patterns: List[MemoryPattern]
    ) -> List[MemoryPattern]:
        """Verify detected patterns."""
        for pattern in patterns:
            # Perform epistemic check
            check_result = self.metacognition.reflect_on_decision(
                intent=f"verify_pattern_{pattern.pattern_type}",
                context={"pattern": pattern.to_dict(), "artifacts": pattern.artifacts},
                available_functions=["pattern_verification"],
            )

            # Update pattern verification status
            pattern.verified = (
                check_result["confidence_assessment"]["confidence_score"] > 0.7
            )

        return patterns

    def _update_relationships(self, memory: Any, patterns: List[MemoryPattern]) -> None:
        """Update memory relationships based on patterns."""
        related_artifacts = set()

        for pattern in patterns:
            related_artifacts.update(pattern.artifacts)

        if hasattr(memory, "related_artifacts"):
            memory.related_artifacts = list(related_artifacts)

    def _calculate_confidence(self, patterns: List[MemoryPattern]) -> float:
        """Calculate overall confidence in pattern analysis."""
        if not patterns:
            return 0.0

        # Weight verified patterns more heavily
        verified_confidence = sum(p.confidence for p in patterns if p.verified)
        unverified_confidence = sum(
            p.confidence * 0.5 for p in patterns if not p.verified
        )

        total_confidence = verified_confidence + unverified_confidence
        return min(1.0, total_confidence / len(patterns))

    async def checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint of current memory state.

        Returns:
            Dict containing checkpoint information
        """
        try:
            checkpoint_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "pattern_count": len(self.patterns),
                "verified_patterns": len([p for p in self.patterns if p.verified]),
                "active_analyses": list(self.active_analyses),
            }

            # Store checkpoint in memory
            checkpoint_id = self.codex.store_memory(
                content=checkpoint_data,
                source="vestige",
                tags=["checkpoint", "system_state"],
                confidence=1.0,
            )

            self.last_checkpoint = datetime.utcnow()

            return {
                "status": "success",
                "checkpoint_id": checkpoint_id,
                "data": checkpoint_data,
            }

        except Exception as e:
            logger.error(f"Checkpoint creation failed: {e}")
            return {"status": "error", "error": str(e)}


# Example usage:
if __name__ == "__main__":
    # Initialize dependencies
    codex = CodexAwareness()
    metacognition = MetacognitionEngine()

    # Create Vestige agent
    vestige = VestigeAgent(codex, metacognition)

    # Example memory processing
    async def test_processing():
        result = await vestige.process_memory("test_memory", {"context": "test"})
        print(f"Processing result: {result}")

    # Run test
    import asyncio

    asyncio.run(test_processing())
