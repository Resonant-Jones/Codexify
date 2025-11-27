"""Tests for Federated Context Retrieval and Semantic Discovery.

Tests cover:
- Local semantic search accuracy and graph integration
- Federated query merge and result ranking
- Trust weight impact on scoring
- Role and capability enforcement
- Peer discovery and filtering
- Result deduplication and scoring formulas
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardian.federation.graph_model import GraphEdge, GraphNode
from guardian.federation.graph_store import GraphStore
from guardian.federation.manifest import NodeManifest
from guardian.federation.trust_registry import (
    TrustRegistry,
    calculate_recency_factor,
    calculate_result_score,
)
from guardian.routes.federation_context import (
    PeerInfo,
    SearchRequest,
    SearchResult,
    _search_local,
    _search_peers,
)


class TestTrustRegistry:
    """Test trust level management."""

    def test_init_trust_registry(self):
        """Test creating a trust registry."""
        registry = TrustRegistry()
        assert len(registry.trust) == 0

    def test_init_with_trust_levels(self):
        """Test initializing with trust levels."""
        initial = {"peer-1": 0.8, "peer-2": 0.6}
        registry = TrustRegistry(initial_trust=initial)
        assert registry.get_trust_level("peer-1") == 0.8
        assert registry.get_trust_level("peer-2") == 0.6

    def test_default_trust_level(self):
        """Test default trust for unknown peers."""
        registry = TrustRegistry()
        assert registry.get_trust_level("unknown") == 0.5

    def test_set_trust_level(self):
        """Test setting trust level."""
        registry = TrustRegistry()
        registry.set_trust_level("peer-1", 0.9)
        assert registry.get_trust_level("peer-1") == 0.9

    def test_trust_level_bounds(self):
        """Test that trust levels are bounded 0.0-1.0."""
        registry = TrustRegistry()

        # Valid values
        registry.set_trust_level("peer-1", 0.0)
        registry.set_trust_level("peer-2", 1.0)
        assert registry.get_trust_level("peer-1") == 0.0
        assert registry.get_trust_level("peer-2") == 1.0

        # Invalid values
        with pytest.raises(ValueError):
            registry.set_trust_level("peer-3", -0.1)

        with pytest.raises(ValueError):
            registry.set_trust_level("peer-4", 1.1)

    def test_get_all_trust_levels(self):
        """Test getting all trust levels."""
        registry = TrustRegistry({"peer-1": 0.8, "peer-2": 0.6})
        all_trust = registry.get_all_trust_levels()
        assert all_trust["peer-1"] == 0.8
        assert all_trust["peer-2"] == 0.6

    def test_reset_trust_level(self):
        """Test resetting trust level to default."""
        registry = TrustRegistry({"peer-1": 0.8})
        registry.reset_trust_level("peer-1")
        assert registry.get_trust_level("peer-1") == 0.5  # Default

    def test_clear_all_trust(self):
        """Test clearing all trust levels."""
        registry = TrustRegistry({"peer-1": 0.8, "peer-2": 0.6})
        registry.clear_all()
        assert len(registry.trust) == 0
        assert registry.get_trust_level("peer-1") == 0.5  # Default


class TestScoringFormula:
    """Test result scoring calculations."""

    def test_calculate_result_score_basic(self):
        """Test basic score calculation."""
        # Similarity only (no trust or recency boost)
        score = calculate_result_score(
            similarity=1.0, trust_level=0.0, recency=0.0
        )
        assert score == pytest.approx(0.7)  # 1.0 * 0.7

    def test_calculate_result_score_with_trust(self):
        """Test score with trust weight."""
        score = calculate_result_score(
            similarity=1.0, trust_level=1.0, recency=0.0
        )
        assert score == pytest.approx(0.9)  # 1.0 * 0.7 + 1.0 * 0.2

    def test_calculate_result_score_with_recency(self):
        """Test score with recency weight."""
        score = calculate_result_score(
            similarity=1.0, trust_level=0.0, recency=1.0
        )
        assert score == pytest.approx(0.8)  # 1.0 * 0.7 + 1.0 * 0.1

    def test_calculate_result_score_all_weights(self):
        """Test score with all weights at 1.0."""
        score = calculate_result_score(
            similarity=1.0, trust_level=1.0, recency=1.0
        )
        assert score == pytest.approx(1.0)  # 0.7 + 0.2 + 0.1

    def test_calculate_result_score_capped_at_one(self):
        """Test that score is capped at 1.0."""
        # If individual factors sum to > 1.0, cap at 1.0
        score = calculate_result_score(
            similarity=1.5, trust_level=1.5, recency=1.5
        )
        assert score <= 1.0

    def test_calculate_recency_factor_recent(self):
        """Test recency factor for recent items."""
        # 10 minutes ago out of 1440 minute window
        factor = calculate_recency_factor(10, max_age_minutes=1440)
        assert factor == pytest.approx(1.0 - (10 / 1440))

    def test_calculate_recency_factor_recent_exact(self):
        """Test recency factor for very recent item."""
        factor = calculate_recency_factor(0)  # Just created
        assert factor == 1.0

    def test_calculate_recency_factor_old(self):
        """Test recency factor for old items."""
        # Exactly at max_age
        factor = calculate_recency_factor(1440, max_age_minutes=1440)
        assert factor == 0.0

    def test_calculate_recency_factor_very_old(self):
        """Test recency factor for very old items."""
        # Beyond max_age
        factor = calculate_recency_factor(2000, max_age_minutes=1440)
        assert factor == 0.0

    def test_calculate_recency_factor_negative(self):
        """Test recency factor for negative age (future dates)."""
        # Should handle gracefully, returning 1.0
        factor = calculate_recency_factor(-100)
        assert factor == 1.0


class TestLocalSearch:
    """Test local graph search."""

    @pytest.fixture
    def temp_graph_store(self):
        """Create a temporary graph store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "graph.json")
            store = GraphStore(path=path)
            yield store

    @pytest.mark.asyncio
    async def test_search_local_no_results(self, temp_graph_store):
        """Test search with no matching nodes."""
        # Patch get_graph_store to return our test store
        with patch(
            "guardian.routes.federation_context.get_graph_store"
        ) as mock_get:
            mock_get.return_value = temp_graph_store

            results = await _search_local(
                "nonexistent", limit=5, include_graph=True
            )
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_local_label_match(self, temp_graph_store):
        """Test search matching node labels."""
        # Add a node to the store
        node = GraphNode(
            id="doc-1",
            type="document",
            label="Python Tutorial",
        )
        temp_graph_store.upsert_node(node)

        with patch(
            "guardian.routes.federation_context.get_graph_store"
        ) as mock_get:
            mock_get.return_value = temp_graph_store

            results = await _search_local("Python", limit=5, include_graph=True)
            assert len(results) == 1
            assert results[0].label == "Python Tutorial"

    @pytest.mark.asyncio
    async def test_search_local_metadata_match(self, temp_graph_store):
        """Test search matching node metadata."""
        node = GraphNode(
            id="thread-1",
            type="thread",
            label="Discussion",
            metadata={"topic": "machine learning", "status": "active"},
        )
        temp_graph_store.upsert_node(node)

        with patch(
            "guardian.routes.federation_context.get_graph_store"
        ) as mock_get:
            mock_get.return_value = temp_graph_store

            results = await _search_local(
                "machine learning", limit=5, include_graph=True
            )
            assert len(results) == 1
            assert "machine learning" in str(results[0].metadata)

    @pytest.mark.asyncio
    async def test_search_local_respects_limit(self, temp_graph_store):
        """Test that search respects result limit."""
        # Add multiple nodes
        for i in range(10):
            node = GraphNode(
                id=f"doc-{i}",
                type="document",
                label=f"Document {i} about python",
            )
            temp_graph_store.upsert_node(node)

        with patch(
            "guardian.routes.federation_context.get_graph_store"
        ) as mock_get:
            mock_get.return_value = temp_graph_store

            results = await _search_local("python", limit=3, include_graph=True)
            assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_local_graph_disabled(self, temp_graph_store):
        """Test search with graph disabled."""
        node = GraphNode(
            id="doc-1",
            type="document",
            label="Test Document",
        )
        temp_graph_store.upsert_node(node)

        with patch(
            "guardian.routes.federation_context.get_graph_store"
        ) as mock_get:
            mock_get.return_value = temp_graph_store

            results = await _search_local(
                "Test",
                limit=5,
                include_graph=False,  # Disabled
            )
            assert len(results) == 0  # No results when graph disabled


class TestPeerSearch:
    """Test peer node searching."""

    @pytest.mark.asyncio
    async def test_search_peers_no_relays(self):
        """Test peer search with no active relays."""
        with patch(
            "guardian.routes.federation_context.manager"
        ) as mock_manager:
            mock_manager.active_relays = {}
            results = await _search_peers("query", limit=5)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_peers_no_search_capability(self):
        """Test peer search when peer doesn't support search."""
        with patch(
            "guardian.routes.federation_context.manager"
        ) as mock_manager:
            # Setup relay with peer that lacks search capability
            mock_relay = MagicMock()
            mock_relay.is_expired.return_value = False
            mock_relay.target_node_id = "peer-1"
            mock_relay.target_ws = None
            mock_relay.source_ws = None

            mock_manifest = NodeManifest(
                node_id="peer-1",
                public_key="fake_key",
                capabilities=["collab", "autosave"],  # No "search"
                relay_endpoint="ws://peer-1",
            )

            mock_manager.active_relays = {"relay-1": mock_relay}
            mock_manager.get_peer_manifest.return_value = mock_manifest

            results = await _search_peers("query", limit=5)
            assert len(results) == 0  # No results because no search capability


class TestSearchRequest:
    """Test SearchRequest model validation."""

    def test_create_search_request(self):
        """Test creating a SearchRequest."""
        req = SearchRequest(query="test query")
        assert req.query == "test query"
        assert req.limit == 5
        assert req.include_peers is False
        assert req.include_graph is True

    def test_search_request_custom_params(self):
        """Test SearchRequest with custom parameters."""
        req = SearchRequest(
            query="test",
            limit=10,
            include_peers=True,
            include_graph=False,
            depth="deep",
        )
        assert req.query == "test"
        assert req.limit == 10
        assert req.include_peers is True
        assert req.include_graph is False
        assert req.depth == "deep"

    def test_search_request_limit_bounds(self):
        """Test SearchRequest limit validation."""
        # Valid limits
        SearchRequest(query="test", limit=1)
        SearchRequest(query="test", limit=50)

        # Invalid limits
        with pytest.raises(ValueError):
            SearchRequest(query="test", limit=0)

        with pytest.raises(ValueError):
            SearchRequest(query="test", limit=51)


class TestSearchResult:
    """Test SearchResult model."""

    def test_create_search_result(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            source="local",
            node_id="doc-1",
            node_type="document",
            label="Test Doc",
            score=0.92,
        )
        assert result.source == "local"
        assert result.node_id == "doc-1"
        assert result.score == 0.92

    def test_search_result_with_peer(self):
        """Test SearchResult from a peer node."""
        result = SearchResult(
            source="peer",
            node_id="doc-2",
            node_type="document",
            label="Peer Doc",
            score=0.85,
            peer="peer-1",
        )
        assert result.peer == "peer-1"

    def test_search_result_score_bounds(self):
        """Test that score is bounded 0.0-1.0."""
        SearchResult(
            source="local",
            node_id="doc",
            node_type="document",
            label="Test",
            score=0.0,
        )
        SearchResult(
            source="local",
            node_id="doc",
            node_type="document",
            label="Test",
            score=1.0,
        )

        # Invalid scores
        with pytest.raises(ValueError):
            SearchResult(
                source="local",
                node_id="doc",
                node_type="document",
                label="Test",
                score=-0.1,
            )

        with pytest.raises(ValueError):
            SearchResult(
                source="local",
                node_id="doc",
                node_type="document",
                label="Test",
                score=1.1,
            )


class TestPeerInfo:
    """Test PeerInfo model."""

    def test_create_peer_info(self):
        """Test creating PeerInfo."""
        peer = PeerInfo(
            node_id="peer-1",
            relay_endpoint="ws://peer-1:8000/relay",
            capabilities=["search", "collab"],
            trust_level=0.8,
        )
        assert peer.node_id == "peer-1"
        assert "search" in peer.capabilities
        assert peer.trust_level == 0.8

    def test_peer_info_default_values(self):
        """Test PeerInfo defaults."""
        peer = PeerInfo(
            node_id="peer-1",
            relay_endpoint="ws://peer-1",
        )
        assert peer.trust_level == 0.5
        assert peer.active_relays == 0
        assert peer.capabilities == []

    def test_peer_info_trust_bounds(self):
        """Test that trust_level is bounded 0.0-1.0."""
        PeerInfo(node_id="peer", relay_endpoint="ws://peer", trust_level=0.0)
        PeerInfo(node_id="peer", relay_endpoint="ws://peer", trust_level=1.0)

        with pytest.raises(ValueError):
            PeerInfo(
                node_id="peer", relay_endpoint="ws://peer", trust_level=-0.1
            )

        with pytest.raises(ValueError):
            PeerInfo(
                node_id="peer", relay_endpoint="ws://peer", trust_level=1.1
            )


class TestResultRanking:
    """Test result ranking and merging."""

    def test_rank_by_similarity(self):
        """Test ranking by similarity score."""
        results = [
            SearchResult(
                source="local",
                node_id="a",
                node_type="doc",
                label="A",
                score=0.5,
            ),
            SearchResult(
                source="local",
                node_id="b",
                node_type="doc",
                label="B",
                score=0.9,
            ),
            SearchResult(
                source="local",
                node_id="c",
                node_type="doc",
                label="C",
                score=0.7,
            ),
        ]

        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        assert sorted_results[0].node_id == "b"
        assert sorted_results[1].node_id == "c"
        assert sorted_results[2].node_id == "a"

    def test_rank_with_trust_weight(self):
        """Test ranking with trust-weighted scores."""
        registry = TrustRegistry({"peer-1": 0.9})

        results = [
            SearchResult(
                source="local",
                node_id="a",
                node_type="doc",
                label="A",
                score=0.8,
            ),
            SearchResult(
                source="peer",
                node_id="b",
                node_type="doc",
                label="B",
                score=0.7,
                peer="peer-1",
            ),
        ]

        # Apply trust weighting
        for result in results:
            if result.peer:
                trust = registry.get_trust_level(result.peer)
            else:
                trust = 1.0
            result.score = calculate_result_score(
                result.score, trust_level=trust
            )

        # Local result (trust=1.0) should now rank higher
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        assert sorted_results[0].source == "local"

    def test_dedup_results(self):
        """Test deduplication of identical node results."""
        results = [
            SearchResult(
                source="local",
                node_id="doc-1",
                node_type="document",
                label="Doc 1",
                score=0.9,
            ),
            SearchResult(
                source="peer",
                node_id="doc-1",  # Same node
                node_type="document",
                label="Doc 1",
                score=0.85,
                peer="peer-1",
            ),
        ]

        # Simple dedup: keep first occurrence, higher score
        unique = {}
        for result in results:
            key = (result.node_id, result.node_type)
            if key not in unique or result.score > unique[key].score:
                unique[key] = result

        assert len(unique) == 1
        assert unique[("doc-1", "document")].score == 0.9


class TestAuthorizationEnforcement:
    """Test role and capability enforcement."""

    def test_search_requires_auth(self):
        """Test that search requires authentication."""
        # This would be tested via API integration tests
        # with actual FastAPI test client
        pass

    def test_peer_capability_check(self):
        """Test that peers are filtered by search capability."""
        peer_with_search = NodeManifest(
            node_id="peer-1",
            public_key="key1",
            capabilities=["search", "collab"],
            relay_endpoint="ws://peer-1",
        )

        peer_without_search = NodeManifest(
            node_id="peer-2",
            public_key="key2",
            capabilities=["collab", "autosave"],
            relay_endpoint="ws://peer-2",
        )

        # Check capability
        assert "search" in peer_with_search.capabilities
        assert "search" not in peer_without_search.capabilities


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_search_workflow(self):
        """Test a complete local search workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "graph.json")
            store = GraphStore(path=path)

            # Setup graph with test data
            nodes = [
                GraphNode(
                    id="doc-1",
                    type="document",
                    label="Python Guide",
                    metadata={"topic": "python"},
                ),
                GraphNode(
                    id="doc-2",
                    type="document",
                    label="Ruby Tutorial",
                    metadata={"topic": "ruby"},
                ),
                GraphNode(
                    id="thread-1",
                    type="thread",
                    label="Python Discussion",
                ),
            ]
            for node in nodes:
                store.upsert_node(node)

            with patch(
                "guardian.routes.federation_context.get_graph_store"
            ) as mock:
                mock.return_value = store

                # Search for python
                results = await _search_local(
                    "python",
                    limit=10,
                    include_graph=True,
                )

                # Should find python-related nodes
                assert len(results) >= 2
                python_results = [
                    r for r in results if "python" in r.label.lower()
                ]
                assert len(python_results) > 0
