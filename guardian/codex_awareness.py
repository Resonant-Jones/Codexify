"""
Codex Awareness Layer
-------------------
Enables active querying and reflection on Codexify summaries and MemoryOS outputs.
Provides a unified interface for accessing and reasoning about system memory artifacts.

This module serves as the bridge between passive storage and active memory utilization,
allowing the system to reflect on and learn from its accumulated knowledge.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MemoryArtifact:
    """Represents a queryable memory artifact with metadata."""
    
    id: str
    content: Dict[str, Any]
    source: str  # 'codexify' or 'memoryos'
    timestamp: datetime
    tags: List[str]
    confidence: float
    related_artifacts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the artifact to a dictionary representation."""
        return {
            'id': self.id,
            'content': self.content,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'confidence': self.confidence,
            'related_artifacts': self.related_artifacts
        }

class CodexAwareness:
    """
    Main class for managing and querying system memory artifacts.
    Provides reflection capabilities and contextual awareness.
    """
    
    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = memory_path or Path(__file__).parent / 'memory'
        self.memory_path.mkdir(exist_ok=True)
        self.artifacts: Dict[str, MemoryArtifact] = {}
        self._load_artifacts()
    
    def _load_artifacts(self) -> None:
        """Load existing memory artifacts from storage."""
        try:
            artifact_path = self.memory_path / 'artifacts.json'
            if artifact_path.exists():
                with open(artifact_path, 'r') as f:
                    data = json.load(f)
                    for artifact_dict in data:
                        artifact = MemoryArtifact(
                            id=artifact_dict['id'],
                            content=artifact_dict['content'],
                            source=artifact_dict['source'],
                            timestamp=datetime.fromisoformat(
                                artifact_dict['timestamp']
                            ),
                            tags=artifact_dict['tags'],
                            confidence=artifact_dict['confidence'],
                            related_artifacts=artifact_dict['related_artifacts']
                        )
                        self.artifacts[artifact.id] = artifact
        except Exception as e:
            logger.error(f"Failed to load artifacts: {e}")
    
    def save_artifacts(self) -> None:
        """Persist memory artifacts to storage."""
        try:
            artifact_path = self.memory_path / 'artifacts.json'
            with open(artifact_path, 'w') as f:
                json.dump(
                    [a.to_dict() for a in self.artifacts.values()],
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save artifacts: {e}")
    
    def store_memory(
        self,
        content: Dict[str, Any],
        source: str,
        tags: List[str],
        confidence: float = 1.0,
        related_artifacts: Optional[List[str]] = None
    ) -> str:
        """
        Store a new memory artifact.
        
        Args:
            content: The memory content to store
            source: Origin of the memory ('codexify' or 'memoryos')
            tags: Relevant tags for categorization
            confidence: Confidence level in the memory (0-1)
            related_artifacts: IDs of related memory artifacts
        
        Returns:
            str: ID of the stored artifact
        """
        artifact_id = f"{source}_{datetime.utcnow().isoformat()}"
        artifact = MemoryArtifact(
            id=artifact_id,
            content=content,
            source=source,
            timestamp=datetime.utcnow(),
            tags=tags,
            confidence=confidence,
            related_artifacts=related_artifacts or []
        )
        
        self.artifacts[artifact_id] = artifact
        self.save_artifacts()
        return artifact_id
    
    def query_memory(
        self,
        query: str,
        source_filter: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> List[MemoryArtifact]:
        """
        Query memory artifacts based on various criteria.
        
        Args:
            query: Search query string
            source_filter: Filter by source ('codexify' or 'memoryos')
            tags: Filter by tags
            min_confidence: Minimum confidence threshold
            limit: Maximum number of results
        
        Returns:
            List[MemoryArtifact]: Matching memory artifacts
        """
        results = []
        
        for artifact in self.artifacts.values():
            if source_filter and artifact.source != source_filter:
                continue
                
            if tags and not all(tag in artifact.tags for tag in tags):
                continue
                
            if artifact.confidence < min_confidence:
                continue
                
            # Simple text matching for now - could be enhanced with
            # semantic search or embedding similarity
            if self._matches_query(artifact, query):
                results.append(artifact)
                
            if len(results) >= limit:
                break
        
        return results
    
    def _matches_query(self, artifact: MemoryArtifact, query: str) -> bool:
        """Check if an artifact matches the search query."""
        # Convert query and content to lowercase for case-insensitive matching
        query = query.lower()
        
        # Check content
        content_str = json.dumps(artifact.content).lower()
        if query in content_str:
            return True
        
        # Check tags
        if any(query in tag.lower() for tag in artifact.tags):
            return True
        
        return False
    
    def get_related_memories(
        self,
        artifact_id: str,
        max_depth: int = 2,
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> List[MemoryArtifact]:
        """
        Retrieve related memory artifacts up to a specified depth.
        
        Args:
            artifact_id: ID of the source artifact
            max_depth: Maximum depth to traverse related artifacts
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        
        Returns:
            List[MemoryArtifact]: Related artifacts
        """
        if max_depth <= 0:
            return []
            
        if artifact_id not in self.artifacts:
            logger.warning(f"Artifact {artifact_id} not found in memory store")
            return []
        
        related = []
        visited = set()
        
        def traverse_related(current_id: str, depth: int):
            if depth <= 0 or current_id in visited:
                return
            
            visited.add(current_id)
            current_artifact = self.artifacts.get(current_id)
            
            if not current_artifact:
                logger.warning(f"Related artifact {current_id} not found")
                return
            
            # Always include the current artifact's direct relations
            for related_id in current_artifact.related_artifacts:
                if related_id in self.artifacts:
                    related_artifact = self.artifacts[related_id]
                    if related_artifact not in related:
                        related.append(related_artifact)
                        logger.info(f"Found related artifact: {related_id}")
                    traverse_related(related_id, depth - 1)
        
        # Try multiple times with delay
        for attempt in range(max_retries):
            traverse_related(artifact_id, max_depth)
            if related:
                logger.info(f"Found {len(related)} related memories on attempt {attempt + 1}")
                break
                
            if attempt < max_retries - 1:
                logger.warning(f"No related memories found, retrying (attempt {attempt + 1})")
                import time
                time.sleep(retry_delay)
        
        if not related:
            logger.warning(f"No related memories found after {max_retries} attempts")
            # Return an empty list instead of raising an error
            return []
            
        return related
    
    def summarize_context(
        self,
        artifact_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a summary of the context from multiple artifacts.
        
        Args:
            artifact_ids: List of artifact IDs to summarize
        
        Returns:
            Dict containing summary information
        """
        artifacts = [
            self.artifacts[aid] for aid in artifact_ids 
            if aid in self.artifacts
        ]
        
        if not artifacts:
            return {
                'summary': 'No artifacts found',
                'confidence': 0.0,
                'sources': []
            }
        
        # Aggregate information
        sources = set()
        total_confidence = 0.0
        all_tags = set()
        
        for artifact in artifacts:
            sources.add(artifact.source)
            total_confidence += artifact.confidence
            all_tags.update(artifact.tags)
        
        avg_confidence = total_confidence / len(artifacts)
        
        return {
            'summary': f"Context from {len(artifacts)} artifacts",
            'confidence': avg_confidence,
            'sources': list(sources),
            'tags': list(all_tags),
            'timestamp_range': {
                'earliest': min(a.timestamp for a in artifacts).isoformat(),
                'latest': max(a.timestamp for a in artifacts).isoformat()
            }
        }

# Example usage:
if __name__ == "__main__":
    # Initialize the awareness layer
    awareness = CodexAwareness()
    
    # Store a test memory
    test_memory = {
        'type': 'conversation',
        'content': 'Test conversation content',
        'metadata': {'user': 'test_user'}
    }
    
    artifact_id = awareness.store_memory(
        content=test_memory,
        source='codexify',
        tags=['test', 'conversation'],
        confidence=0.9
    )
    
    # Query memories
    results = awareness.query_memory(
        query='conversation',
        tags=['test']
    )
    
    print(f"Found {len(results)} matching memories")
