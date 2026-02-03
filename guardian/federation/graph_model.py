"""Graph models for federated awareness and relationship tracking.

Represents entities (documents, threads, projects, users, connectors) as
graph nodes and tracks relationships between them for distributed semantic
memory and context sharing across federated nodes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    """A node in the federated awareness graph.

    Represents an entity like a document, thread, project, user, or connector.
    Nodes are identified by type and ID, with metadata for discovery and
    relationship traversal.
    """

    id: str = Field(..., description="Unique identifier for this node")
    type: str = Field(
        ...,
        description="Node type: 'document', 'thread', 'project', 'user', 'connector'",
    )
    label: str = Field(..., description="Human-readable label for this node")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for this node (owner, status, tags, etc)",
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    def __hash__(self) -> int:
        """Hash based on type and id for use in sets/dicts."""
        return hash((self.type, self.id))

    def __eq__(self, other: object) -> bool:
        """Equality based on type and id."""
        if not isinstance(other, GraphNode):
            return False
        return self.type == other.type and self.id == other.id


class GraphEdge(BaseModel):
    """An edge in the federated awareness graph.

    Represents a relationship between two nodes. Edges are directed,
    weighted, and timestamped for tracking relationship evolution.
    """

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation: str = Field(
        ...,
        description="Relationship type: 'references', 'derived_from', 'collaborates_with', 'mirrors'",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=100.0,
        description="Edge weight for importance/strength (0-100)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for this edge",
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    def __hash__(self) -> int:
        """Hash based on source, target, and relation for use in sets."""
        return hash((self.source, self.target, self.relation))

    def __eq__(self, other: object) -> bool:
        """Equality based on source, target, and relation."""
        if not isinstance(other, GraphEdge):
            return False
        return (
            self.source == other.source
            and self.target == other.target
            and self.relation == other.relation
        )


class GraphSnapshot(BaseModel):
    """A snapshot of the entire graph for synchronization and bootstrap.

    Used when syncing with peer nodes or bootstrapping after offline
    periods. Contains all nodes and edges at a point in time.
    """

    nodes: Dict[str, GraphNode] = Field(
        default_factory=dict,
        description="Map of node_id to GraphNode",
    )
    edges: list[GraphEdge] = Field(
        default_factory=list,
        description="List of all edges in the graph",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this snapshot was created",
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
