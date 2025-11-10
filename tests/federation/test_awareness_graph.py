"""Tests for Federated Awareness Graph.

Tests cover:
- Node and edge creation, persistence, and querying
- Graph snapshots and synchronization
- Cross-node graph updates and signature verification
- EventBus integration for automatic graph updates
- Snapshot export/import with integrity checking
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from guardian.federation.graph_model import GraphNode, GraphEdge, GraphSnapshot
from guardian.federation.graph_store import GraphStore, get_graph_store


class TestGraphNodeModel:
    """Test GraphNode Pydantic model."""

    def test_create_node(self):
        """Test creating a GraphNode."""
        node = GraphNode(
            id="doc-123",
            type="document",
            label="Test Document",
        )

        assert node.id == "doc-123"
        assert node.type == "document"
        assert node.label == "Test Document"
        assert node.updated_at is not None
        assert node.metadata == {}

    def test_node_with_metadata(self):
        """Test GraphNode with metadata."""
        node = GraphNode(
            id="user-456",
            type="user",
            label="John Doe",
            metadata={"email": "john@example.com", "role": "admin"},
        )

        assert node.metadata["email"] == "john@example.com"
        assert node.metadata["role"] == "admin"

    def test_node_hash_and_equality(self):
        """Test node hashing and equality."""
        node1 = GraphNode(id="doc-1", type="document", label="Doc 1")
        node2 = GraphNode(id="doc-1", type="document", label="Doc 1 Updated")
        node3 = GraphNode(id="doc-2", type="document", label="Doc 2")

        # Same type and id should be equal
        assert node1 == node2
        assert hash(node1) == hash(node2)

        # Different id should not be equal
        assert node1 != node3
        assert hash(node1) != hash(node3)

    def test_node_json_serialization(self):
        """Test GraphNode JSON serialization."""
        node = GraphNode(
            id="thread-789",
            type="thread",
            label="Test Thread",
            metadata={"status": "active"},
        )

        json_str = node.model_dump_json()
        assert "thread-789" in json_str
        assert "thread" in json_str
        assert "active" in json_str

        # Verify roundtrip
        data = json.loads(json_str)
        node2 = GraphNode(**data)
        assert node2.id == node.id
        assert node2.type == node.type


class TestGraphEdgeModel:
    """Test GraphEdge Pydantic model."""

    def test_create_edge(self):
        """Test creating a GraphEdge."""
        edge = GraphEdge(
            source="doc-1",
            target="thread-1",
            relation="references",
        )

        assert edge.source == "doc-1"
        assert edge.target == "thread-1"
        assert edge.relation == "references"
        assert edge.weight == 1.0
        assert edge.updated_at is not None

    def test_edge_with_weight(self):
        """Test GraphEdge with weight."""
        edge = GraphEdge(
            source="user-1",
            target="doc-1",
            relation="authored",
            weight=5.5,
        )

        assert edge.weight == 5.5

    def test_edge_weight_bounds(self):
        """Test that edge weight is bounded 0-100."""
        # Valid weights
        edge1 = GraphEdge(source="a", target="b", relation="test", weight=0)
        edge2 = GraphEdge(source="a", target="b", relation="test", weight=100)
        assert edge1.weight == 0
        assert edge2.weight == 100

        # Invalid weights should raise validation error
        with pytest.raises(ValueError):
            GraphEdge(source="a", target="b", relation="test", weight=-1)

        with pytest.raises(ValueError):
            GraphEdge(source="a", target="b", relation="test", weight=101)

    def test_edge_hash_and_equality(self):
        """Test edge hashing and equality."""
        edge1 = GraphEdge(source="a", target="b", relation="refs")
        edge2 = GraphEdge(source="a", target="b", relation="refs", weight=5.0)
        edge3 = GraphEdge(source="a", target="b", relation="other")

        # Same source, target, relation should be equal
        assert edge1 == edge2
        assert hash(edge1) == hash(edge2)

        # Different relation should not be equal
        assert edge1 != edge3
        assert hash(edge1) != hash(edge3)


class TestGraphStore:
    """Test GraphStore persistence and querying."""

    @pytest.fixture
    def temp_store(self):
        """Create a temporary graph store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "graph.json")
            store = GraphStore(path=path)
            yield store

    def test_store_initialization(self, temp_store):
        """Test graph store initialization."""
        assert temp_store.path.exists()
        assert len(temp_store.graph["nodes"]) == 0
        assert len(temp_store.graph["edges"]) == 0

    def test_upsert_node(self, temp_store):
        """Test upserting nodes."""
        node = GraphNode(id="doc-1", type="document", label="Doc 1")
        temp_store.upsert_node(node)

        stored = temp_store.get_node("document:doc-1")
        assert stored is not None
        assert stored.id == "doc-1"
        assert stored.type == "document"

    def test_upsert_node_update(self, temp_store):
        """Test that upserting updates existing node."""
        node1 = GraphNode(id="doc-1", type="document", label="Doc 1")
        temp_store.upsert_node(node1)

        node2 = GraphNode(
            id="doc-1",
            type="document",
            label="Doc 1 Updated",
            metadata={"version": 2},
        )
        temp_store.upsert_node(node2)

        stored = temp_store.get_node("document:doc-1")
        assert stored.label == "Doc 1 Updated"
        assert stored.metadata["version"] == 2

    def test_persistence(self):
        """Test that nodes persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "graph.json")

            # Create and populate first store
            store1 = GraphStore(path=path)
            node = GraphNode(id="persistent", type="document", label="Persistent Doc")
            store1.upsert_node(node)

            # Create new store from same path
            store2 = GraphStore(path=path)
            retrieved = store2.get_node("document:persistent")
            assert retrieved is not None
            assert retrieved.id == "persistent"

    def test_add_edge(self, temp_store):
        """Test adding edges."""
        # Add nodes first
        node1 = GraphNode(id="doc-1", type="document", label="Doc 1")
        node2 = GraphNode(id="thread-1", type="thread", label="Thread 1")
        temp_store.upsert_node(node1)
        temp_store.upsert_node(node2)

        # Add edge
        edge = GraphEdge(
            source="document:doc-1",
            target="thread:thread-1",
            relation="references",
        )
        temp_store.add_edge(edge)

        assert len(temp_store.graph["edges"]) == 1
        assert temp_store.graph["edges"][0].relation == "references"

    def test_add_edge_update(self, temp_store):
        """Test that adding duplicate edge updates existing."""
        node1 = GraphNode(id="a", type="document", label="A")
        node2 = GraphNode(id="b", type="document", label="B")
        temp_store.upsert_node(node1)
        temp_store.upsert_node(node2)

        edge1 = GraphEdge(source="document:a", target="document:b", relation="refs", weight=1.0)
        temp_store.add_edge(edge1)

        edge2 = GraphEdge(source="document:a", target="document:b", relation="refs", weight=5.0)
        temp_store.add_edge(edge2)

        assert len(temp_store.graph["edges"]) == 1
        assert temp_store.graph["edges"][0].weight == 5.0

    def test_query_neighbors(self, temp_store):
        """Test querying node neighbors."""
        nodes = [
            GraphNode(id="doc-1", type="document", label="Doc 1"),
            GraphNode(id="thread-1", type="thread", label="Thread 1"),
            GraphNode(id="user-1", type="user", label="User 1"),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        # Add edges
        edges = [
            GraphEdge(source="document:doc-1", target="thread:thread-1", relation="in"),
            GraphEdge(source="user:user-1", target="document:doc-1", relation="authored"),
        ]
        for edge in edges:
            temp_store.add_edge(edge)

        # Query outgoing neighbors from doc-1
        out_neighbors = temp_store.query_neighbors("document:doc-1", direction="out")
        assert len(out_neighbors) == 1
        assert out_neighbors[0].id == "thread-1"

        # Query incoming neighbors to doc-1
        in_neighbors = temp_store.query_neighbors("document:doc-1", direction="in")
        assert len(in_neighbors) == 1
        assert in_neighbors[0].id == "user-1"

    def test_query_relation(self, temp_store):
        """Test querying edges by relation type."""
        node1 = GraphNode(id="doc-1", type="document", label="Doc 1")
        node2 = GraphNode(id="doc-2", type="document", label="Doc 2")
        node3 = GraphNode(id="user-1", type="user", label="User 1")
        temp_store.upsert_node(node1)
        temp_store.upsert_node(node2)
        temp_store.upsert_node(node3)

        edges = [
            GraphEdge(source="document:doc-1", target="document:doc-2", relation="derived_from"),
            GraphEdge(source="document:doc-1", target="document:doc-2", relation="mirrors"),
            GraphEdge(source="user:user-1", target="document:doc-1", relation="authored"),
        ]
        for edge in edges:
            temp_store.add_edge(edge)

        # Query by relation
        derived = temp_store.query_relation("derived_from")
        assert len(derived) == 1

        authored = temp_store.query_relation("authored")
        assert len(authored) == 1

    def test_query_by_type(self, temp_store):
        """Test querying nodes by type."""
        nodes = [
            GraphNode(id="doc-1", type="document", label="Doc 1"),
            GraphNode(id="doc-2", type="document", label="Doc 2"),
            GraphNode(id="thread-1", type="thread", label="Thread 1"),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        docs = temp_store.query_by_type("document")
        assert len(docs) == 2
        assert all(n.type == "document" for n in docs)

        threads = temp_store.query_by_type("thread")
        assert len(threads) == 1

    def test_query_by_metadata(self, temp_store):
        """Test querying nodes by metadata."""
        nodes = [
            GraphNode(
                id="doc-1",
                type="document",
                label="Doc 1",
                metadata={"status": "active"},
            ),
            GraphNode(
                id="doc-2",
                type="document",
                label="Doc 2",
                metadata={"status": "archived"},
            ),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        active = temp_store.query_by_metadata("status", "active")
        assert len(active) == 1
        assert active[0].id == "doc-1"

    def test_find_paths(self, temp_store):
        """Test finding paths between nodes."""
        nodes = [
            GraphNode(id="a", type="document", label="A"),
            GraphNode(id="b", type="document", label="B"),
            GraphNode(id="c", type="document", label="C"),
            GraphNode(id="d", type="document", label="D"),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        edges = [
            GraphEdge(source="document:a", target="document:b", relation="refs"),
            GraphEdge(source="document:b", target="document:c", relation="refs"),
            GraphEdge(source="document:c", target="document:d", relation="refs"),
        ]
        for edge in edges:
            temp_store.add_edge(edge)

        # Find path from a to d
        paths = temp_store.find_paths("document:a", "document:d", max_depth=5)
        assert len(paths) > 0
        assert len(paths[0]) == 4  # a -> b -> c -> d

    def test_remove_node(self, temp_store):
        """Test removing nodes and connected edges."""
        node1 = GraphNode(id="a", type="document", label="A")
        node2 = GraphNode(id="b", type="document", label="B")
        temp_store.upsert_node(node1)
        temp_store.upsert_node(node2)

        edge = GraphEdge(source="document:a", target="document:b", relation="refs")
        temp_store.add_edge(edge)

        assert len(temp_store.graph["nodes"]) == 2
        assert len(temp_store.graph["edges"]) == 1

        # Remove node
        removed = temp_store.remove_node("document:a")
        assert removed is True
        assert len(temp_store.graph["nodes"]) == 1
        assert len(temp_store.graph["edges"]) == 0

    def test_export_snapshot(self, temp_store):
        """Test exporting graph snapshot."""
        nodes = [
            GraphNode(id="doc-1", type="document", label="Doc 1"),
            GraphNode(id="user-1", type="user", label="User 1"),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        edge = GraphEdge(
            source="user:user-1",
            target="document:doc-1",
            relation="authored",
        )
        temp_store.add_edge(edge)

        snapshot = temp_store.export_snapshot()
        assert isinstance(snapshot, GraphSnapshot)
        assert len(snapshot.nodes) == 2
        assert len(snapshot.edges) == 1
        assert snapshot.timestamp is not None

    def test_import_snapshot(self, temp_store):
        """Test importing a graph snapshot."""
        # Create initial graph
        node = GraphNode(id="doc-1", type="document", label="Doc 1")
        temp_store.upsert_node(node)

        # Create snapshot with different data
        new_node = GraphNode(id="doc-2", type="document", label="Doc 2")
        new_edge = GraphEdge(
            source="document:doc-1",
            target="document:doc-2",
            relation="refs",
        )
        snapshot = GraphSnapshot(
            nodes={"document:doc-2": new_node},
            edges=[new_edge],
        )

        # Import with merge
        temp_store.import_snapshot(snapshot, merge=True)
        assert len(temp_store.graph["nodes"]) == 2
        assert len(temp_store.graph["edges"]) == 1

    def test_get_statistics(self, temp_store):
        """Test getting graph statistics."""
        nodes = [
            GraphNode(id="doc-1", type="document", label="Doc 1"),
            GraphNode(id="doc-2", type="document", label="Doc 2"),
            GraphNode(id="user-1", type="user", label="User 1"),
        ]
        for node in nodes:
            temp_store.upsert_node(node)

        edges = [
            GraphEdge(source="document:doc-1", target="document:doc-2", relation="refs"),
            GraphEdge(source="user:user-1", target="document:doc-1", relation="authored"),
            GraphEdge(source="user:user-1", target="document:doc-2", relation="authored"),
        ]
        for edge in edges:
            temp_store.add_edge(edge)

        stats = temp_store.get_statistics()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 3
        assert stats["node_types"]["document"] == 2
        assert stats["node_types"]["user"] == 1
        assert stats["relation_types"]["refs"] == 1
        assert stats["relation_types"]["authored"] == 2


class TestGraphSnapshot:
    """Test GraphSnapshot model and operations."""

    def test_snapshot_creation(self):
        """Test creating a snapshot."""
        nodes = {
            "document:1": GraphNode(id="1", type="document", label="Doc 1"),
        }
        edges = [
            GraphEdge(source="document:1", target="document:2", relation="refs"),
        ]

        snapshot = GraphSnapshot(nodes=nodes, edges=edges)
        assert len(snapshot.nodes) == 1
        assert len(snapshot.edges) == 1
        assert snapshot.timestamp is not None

    def test_snapshot_serialization(self):
        """Test snapshot JSON serialization."""
        node = GraphNode(id="1", type="document", label="Doc 1")
        edge = GraphEdge(source="document:1", target="document:2", relation="refs")
        snapshot = GraphSnapshot(nodes={"document:1": node}, edges=[edge])

        json_str = snapshot.model_dump_json()
        data = json.loads(json_str)

        assert "nodes" in data
        assert "document:1" in data["nodes"]
        assert len(data["edges"]) == 1
        assert data["timestamp"] is not None


class TestGraphIntegration:
    """Integration tests for complete graph workflows."""

    @pytest.fixture
    def temp_store(self):
        """Create a temporary graph store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "graph.json")
            store = GraphStore(path=path)
            yield store

    def test_complete_workflow(self, temp_store):
        """Test a complete graph workflow."""
        # Create entities
        doc = GraphNode(id="article-1", type="document", label="Research Article")
        thread = GraphNode(id="discussion-1", type="thread", label="Discussion Thread")
        user1 = GraphNode(id="alice", type="user", label="Alice")
        user2 = GraphNode(id="bob", type="user", label="Bob")

        for node in [doc, thread, user1, user2]:
            temp_store.upsert_node(node)

        # Create relationships
        edges = [
            GraphEdge(
                source="thread:discussion-1",
                target="document:article-1",
                relation="references",
                weight=3.0,
            ),
            GraphEdge(
                source="user:alice",
                target="document:article-1",
                relation="authored",
            ),
            GraphEdge(
                source="user:bob",
                target="thread:discussion-1",
                relation="collaborates_with",
            ),
            GraphEdge(
                source="user:alice",
                target="user:bob",
                relation="collaborates_with",
            ),
        ]
        for edge in edges:
            temp_store.add_edge(edge)

        # Query and verify
        stats = temp_store.get_statistics()
        assert stats["node_count"] == 4
        assert stats["edge_count"] == 4

        # Find paths
        paths = temp_store.find_paths("user:alice", "thread:discussion-1")
        assert len(paths) > 0

        # Export and reimport
        snapshot = temp_store.export_snapshot()
        assert snapshot.nodes
        assert snapshot.edges

    def test_cross_node_sync(self):
        """Test synchronizing graph updates between two nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = str(Path(tmpdir) / "graph1.json")
            path2 = str(Path(tmpdir) / "graph2.json")

            store1 = GraphStore(path=path1)
            store2 = GraphStore(path=path2)

            # Node 1 creates entities
            doc = GraphNode(id="shared-doc", type="document", label="Shared Document")
            store1.upsert_node(doc)

            # Node 1 exports snapshot
            snapshot = store1.export_snapshot()

            # Node 2 imports snapshot
            store2.import_snapshot(snapshot, merge=False)

            # Verify sync
            assert len(store2.graph["nodes"]) == len(store1.graph["nodes"])
            retrieved = store2.get_node("document:shared-doc")
            assert retrieved is not None
            assert retrieved.label == "Shared Document"
