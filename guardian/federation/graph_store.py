"""Persistent graph store for the federated awareness graph.

Manages storage and retrieval of graph nodes and edges, supporting
synchronization across federated nodes with automatic persistence.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

from guardian.federation.graph_model import GraphNode, GraphEdge, GraphSnapshot

logger = logging.getLogger(__name__)

# Global instance
_store: Optional["GraphStore"] = None


def get_graph_store(path: str = "data/awareness_graph.json") -> "GraphStore":
    """Get or create the global graph store instance.

    Args:
        path: Path to the graph storage file

    Returns:
        GraphStore instance
    """
    global _store
    if _store is None:
        _store = GraphStore(path=path)
    return _store


class GraphStore:
    """Persistent store for the federated awareness graph.

    Maintains nodes and edges in a JSON file with automatic persistence.
    Provides querying, synchronization, and snapshot capabilities.
    """

    def __init__(self, path: str = "data/awareness_graph.json"):
        """Initialize the graph store.

        Args:
            path: Path to JSON file for persistence (created if missing)
        """
        self.path = Path(path)
        self.graph = {"nodes": {}, "edges": [], "metadata": {"version": 1, "created_at": None}}
        self._load()

    def _load(self) -> None:
        """Load graph from persistent storage.

        Creates the file if it doesn't exist. Handles legacy formats gracefully.
        """
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)

                # Validate structure
                if "nodes" not in data or "edges" not in data:
                    logger.warning(f"Invalid graph structure in {self.path}, initializing new")
                    self._initialize()
                    return

                # Load nodes
                self.graph["nodes"] = {}
                for node_id, node_data in data.get("nodes", {}).items():
                    try:
                        node = GraphNode(**node_data)
                        self.graph["nodes"][node_id] = node
                    except Exception as e:
                        logger.error(f"Failed to load node {node_id}: {e}")

                # Load edges
                self.graph["edges"] = []
                for edge_data in data.get("edges", []):
                    try:
                        edge = GraphEdge(**edge_data)
                        self.graph["edges"].append(edge)
                    except Exception as e:
                        logger.error(f"Failed to load edge: {e}")

                # Load metadata
                self.graph["metadata"] = data.get("metadata", {"version": 1, "created_at": None})

                logger.info(
                    f"Loaded graph with {len(self.graph['nodes'])} nodes "
                    f"and {len(self.graph['edges'])} edges from {self.path}"
                )
            except Exception as e:
                logger.error(f"Failed to load graph from {self.path}: {e}")
                self._initialize()
        else:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize a new empty graph."""
        self.graph = {
            "nodes": {},
            "edges": [],
            "metadata": {
                "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        self._save()

    def _save(self) -> None:
        """Save graph to persistent storage.

        Converts all objects to dicts for JSON serialization.
        """
        try:
            # Prepare data for JSON serialization
            data = {
                "nodes": {
                    node_id: node.model_dump(mode="json")
                    for node_id, node in self.graph["nodes"].items()
                },
                "edges": [edge.model_dump(mode="json") for edge in self.graph["edges"]],
                "metadata": self.graph["metadata"],
            }

            # Ensure directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically with temp file
            temp_path = self.path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            temp_path.replace(self.path)

        except Exception as e:
            logger.error(f"Failed to save graph to {self.path}: {e}")
            raise

    def upsert_node(self, node: GraphNode) -> None:
        """Create or update a node in the graph.

        Updates the timestamp automatically and persists to storage.

        Args:
            node: GraphNode to upsert
        """
        # Update timestamp
        node.updated_at = datetime.now(timezone.utc)

        # Store by node_id (combining type and id)
        node_id = f"{node.type}:{node.id}"
        self.graph["nodes"][node_id] = node

        logger.debug(f"Upserted node {node_id} of type {node.type}")
        self._save()

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the graph.

        Also removes all edges connected to this node.

        Args:
            node_id: Node ID to remove (format: "type:id")

        Returns:
            True if node was removed, False if not found
        """
        if node_id not in self.graph["nodes"]:
            return False

        # Remove node
        del self.graph["nodes"][node_id]

        # Remove connected edges
        self.graph["edges"] = [
            edge for edge in self.graph["edges"]
            if edge.source != node_id and edge.target != node_id
        ]

        logger.debug(f"Removed node {node_id}")
        self._save()
        return True

    def add_edge(self, edge: GraphEdge) -> None:
        """Add or update an edge in the graph.

        If edge already exists (same source, target, relation), it's updated.
        Updates timestamp automatically and persists to storage.

        Args:
            edge: GraphEdge to add
        """
        # Update timestamp
        edge.updated_at = datetime.now(timezone.utc)

        # Check if edge already exists
        existing = None
        for i, e in enumerate(self.graph["edges"]):
            if (
                e.source == edge.source
                and e.target == edge.target
                and e.relation == edge.relation
            ):
                existing = i
                break

        if existing is not None:
            # Update existing edge
            self.graph["edges"][existing] = edge
            logger.debug(
                f"Updated edge {edge.source} --[{edge.relation}]--> {edge.target}"
            )
        else:
            # Add new edge
            self.graph["edges"].append(edge)
            logger.debug(
                f"Added edge {edge.source} --[{edge.relation}]--> {edge.target}"
            )

        self._save()

    def remove_edge(self, source: str, target: str, relation: str) -> bool:
        """Remove an edge from the graph.

        Args:
            source: Source node ID
            target: Target node ID
            relation: Relationship type

        Returns:
            True if edge was removed, False if not found
        """
        original_count = len(self.graph["edges"])
        self.graph["edges"] = [
            e
            for e in self.graph["edges"]
            if not (e.source == source and e.target == target and e.relation == relation)
        ]

        removed = len(self.graph["edges"]) < original_count
        if removed:
            logger.debug(f"Removed edge {source} --[{relation}]--> {target}")
            self._save()

        return removed

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID.

        Args:
            node_id: Node ID (format: "type:id")

        Returns:
            GraphNode if found, None otherwise
        """
        return self.graph["nodes"].get(node_id)

    def query_neighbors(self, node_id: str, direction: str = "both") -> List[GraphNode]:
        """Query all nodes connected to a given node.

        Args:
            node_id: Central node ID
            direction: "in", "out", or "both"

        Returns:
            List of connected GraphNodes
        """
        neighbors_ids = set()

        for edge in self.graph["edges"]:
            if direction in ("out", "both") and edge.source == node_id:
                neighbors_ids.add(edge.target)
            if direction in ("in", "both") and edge.target == node_id:
                neighbors_ids.add(edge.source)

        return [
            self.graph["nodes"][nid]
            for nid in neighbors_ids
            if nid in self.graph["nodes"]
        ]

    def query_relation(self, relation: str) -> List[GraphEdge]:
        """Query all edges of a specific relation type.

        Args:
            relation: Relationship type to search for

        Returns:
            List of matching GraphEdges
        """
        return [e for e in self.graph["edges"] if e.relation == relation]

    def query_by_type(self, node_type: str) -> List[GraphNode]:
        """Query all nodes of a specific type.

        Args:
            node_type: Node type to search for

        Returns:
            List of matching GraphNodes
        """
        return [
            node
            for node in self.graph["nodes"].values()
            if node.type == node_type
        ]

    def query_by_metadata(self, key: str, value: Any) -> List[GraphNode]:
        """Query nodes by metadata field.

        Args:
            key: Metadata key
            value: Value to match

        Returns:
            List of matching GraphNodes
        """
        return [
            node
            for node in self.graph["nodes"].values()
            if node.metadata.get(key) == value
        ]

    def find_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> List[List[GraphNode]]:
        """Find all paths between two nodes (breadth-first search).

        Args:
            source: Source node ID
            target: Target node ID
            max_depth: Maximum path length

        Returns:
            List of paths, each path is a list of GraphNodes
        """
        if source not in self.graph["nodes"] or target not in self.graph["nodes"]:
            return []

        paths = []
        queue = [([source], 0)]  # (path_ids, depth)

        while queue:
            path_ids, depth = queue.pop(0)
            current = path_ids[-1]

            if current == target:
                # Reconstruct path with actual nodes
                path = [self.graph["nodes"][nid] for nid in path_ids]
                paths.append(path)
                continue

            if depth >= max_depth:
                continue

            # Get neighbors
            for edge in self.graph["edges"]:
                if edge.source == current and edge.target not in path_ids:
                    new_path = path_ids + [edge.target]
                    queue.append((new_path, depth + 1))

        return paths

    def export_snapshot(self) -> GraphSnapshot:
        """Export the entire graph as a snapshot.

        Snapshot can be synced to peer nodes or used for offline sync.

        Returns:
            GraphSnapshot with current nodes and edges
        """
        return GraphSnapshot(
            nodes=self.graph["nodes"].copy(),
            edges=self.graph["edges"].copy(),
            timestamp=datetime.now(timezone.utc),
        )

    def import_snapshot(self, snapshot: GraphSnapshot, merge: bool = True) -> None:
        """Import a graph snapshot.

        Can merge with existing graph or replace entirely.

        Args:
            snapshot: GraphSnapshot to import
            merge: If True, merge with existing; if False, replace entirely
        """
        if not merge:
            self.graph["nodes"] = {}
            self.graph["edges"] = []

        # Import nodes
        for node_id, node in snapshot.nodes.items():
            existing = self.graph["nodes"].get(node_id)
            # Only update if snapshot is newer
            if not existing or node.updated_at > existing.updated_at:
                self.graph["nodes"][node_id] = node

        # Import edges
        for edge in snapshot.edges:
            self.add_edge(edge)

        logger.info(
            f"Imported snapshot with {len(snapshot.nodes)} nodes "
            f"and {len(snapshot.edges)} edges"
        )
        self._save()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph.

        Returns:
            Dictionary with node count, edge count, relation types, etc
        """
        node_types = {}
        for node in self.graph["nodes"].values():
            node_types[node.type] = node_types.get(node.type, 0) + 1

        relation_types = {}
        for edge in self.graph["edges"]:
            relation_types[edge.relation] = relation_types.get(edge.relation, 0) + 1

        return {
            "node_count": len(self.graph["nodes"]),
            "edge_count": len(self.graph["edges"]),
            "node_types": node_types,
            "relation_types": relation_types,
            "metadata": self.graph["metadata"],
        }

    def clear(self) -> None:
        """Clear all data from the graph (use with caution)."""
        self.graph = {
            "nodes": {},
            "edges": [],
            "metadata": {
                "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        self._save()
        logger.warning("Graph cleared")
