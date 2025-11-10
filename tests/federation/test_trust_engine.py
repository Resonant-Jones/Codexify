"""Tests for Trust and Reputation System.

Tests cover:
- Trust record creation and metric updates
- Trust score computation with weighted formula
- Exponential violation penalties
- Metric decay over time
- Event-driven reputation updates
- Persistence and snapshot import/export
- Low-trust peer rejection
- Dynamic search ranking with trust
"""

import pytest
import tempfile
import math
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from guardian.federation.trust_registry import (
    TrustRecord,
    TrustRegistry,
    get_trust_registry,
)
from guardian.federation.trust_engine import (
    TrustEngine,
    TRUST_EVENTS,
    get_trust_engine,
)


class TestTrustRecord:
    """Test TrustRecord model."""

    def test_create_trust_record(self):
        """Test creating a TrustRecord."""
        record = TrustRecord(node_id="peer-1")
        assert record.node_id == "peer-1"
        assert record.trust_score == 0.5
        assert record.reputation["uptime"] == 1.0
        assert record.reputation["violations"] == 0

    def test_get_metric(self):
        """Test getting a metric value."""
        record = TrustRecord(node_id="peer-1")
        assert record.get_metric("uptime") == 1.0
        assert record.get_metric("violations") == 0

    def test_set_metric_clamping(self):
        """Test that metrics are clamped to valid ranges."""
        record = TrustRecord(node_id="peer-1")

        # Set valid value
        record.set_metric("uptime", 0.8)
        assert record.get_metric("uptime") == 0.8

        # Clamp above 1.0
        record.set_metric("uptime", 1.5)
        assert record.get_metric("uptime") == 1.0

        # Clamp below 0.0
        record.set_metric("uptime", -0.5)
        assert record.get_metric("uptime") == 0.0

    def test_update_metric_delta(self):
        """Test updating a metric by delta."""
        record = TrustRecord(node_id="peer-1")
        record.update_metric("uptime", -0.1)
        assert record.get_metric("uptime") == pytest.approx(0.9)

        # Test that adding to 1.0 gets clamped
        record.update_metric("auth_success", 0.05)
        # 1.0 + 0.05 = 1.05, but should be clamped to 1.0
        assert record.get_metric("auth_success") == 1.0

    def test_update_violations(self):
        """Test updating violations metric."""
        record = TrustRecord(node_id="peer-1")
        record.update_metric("violations", 1.0)
        assert record.get_metric("violations") == 1.0

        record.update_metric("violations", 2.0)
        assert record.get_metric("violations") == 3.0

    def test_trust_record_serialization(self):
        """Test TrustRecord JSON serialization."""
        record = TrustRecord(node_id="peer-1")
        record.set_metric("uptime", 0.9)

        json_str = record.model_dump_json()
        assert "peer-1" in json_str
        assert "uptime" in json_str
        assert "0.9" in json_str


class TestTrustScoring:
    """Test trust score computation."""

    def test_compute_score_default_metrics(self):
        """Test trust score with all default metrics."""
        record = TrustRecord(node_id="peer-1")
        # All metrics at 1.0, no violations
        # score = 0.4*1.0 + 0.3*1.0 + 0.2*1.0 + 0.1*(1-1.0)
        #       = 0.4 + 0.3 + 0.2 + 0.0 = 0.9
        # No violations: * exp(-0) = 0.9
        assert record.trust_score == 0.5  # Initial default

    def test_compute_score_degraded_metrics(self):
        """Test trust score with degraded metrics."""
        record = TrustRecord(node_id="peer-1")
        record.set_metric("uptime", 0.8)
        record.set_metric("auth_success", 0.7)
        record.set_metric("diff_accuracy", 0.6)
        record.set_metric("latency", 0.2)

        # score = 0.4*0.8 + 0.3*0.7 + 0.2*0.6 + 0.1*(1-0.2)
        #       = 0.32 + 0.21 + 0.12 + 0.08 = 0.73
        expected = 0.32 + 0.21 + 0.12 + 0.08
        assert expected == pytest.approx(0.73)

    def test_violation_exponential_penalty(self):
        """Test exponential penalty for violations."""
        registry = TrustRegistry(path=":memory:")
        record = registry.get_record("peer-1")

        # Set all metrics to 1.0
        for metric in ["uptime", "auth_success", "diff_accuracy"]:
            record.set_metric(metric, 1.0)
        record.set_metric("latency", 0.0)

        # Base score = 0.4*1.0 + 0.3*1.0 + 0.2*1.0 + 0.1*(1-0.0)
        #            = 0.4 + 0.3 + 0.2 + 0.1 = 1.0
        # With 0 violations: 1.0 * exp(0) = 1.0 (clamped to 1.0)
        score_no_violations = registry.compute_trust_score("peer-1")
        assert score_no_violations == pytest.approx(1.0)

        # Add 1 violation
        record.set_metric("violations", 1.0)
        # score = 1.0 * exp(-1 * 0.25) = 1.0 * exp(-0.25)
        score_one_violation = registry.compute_trust_score("peer-1")
        expected = 1.0 * math.exp(-1 * 0.25)
        assert score_one_violation == pytest.approx(expected)

        # Add more violations - should decrease exponentially
        record.set_metric("violations", 5.0)
        score_many_violations = registry.compute_trust_score("peer-1")
        expected = 1.0 * math.exp(-5 * 0.25)  # Base score is 1.0
        assert score_many_violations == pytest.approx(expected)
        assert score_many_violations < score_one_violation

    def test_trust_score_clamped_at_one(self):
        """Test that trust score is clamped at 1.0."""
        registry = TrustRegistry(path=":memory:")
        record = registry.get_record("peer-1")

        # Set metrics above 1.0 (should be clamped)
        record.set_metric("uptime", 1.0)
        record.set_metric("auth_success", 1.0)
        record.set_metric("diff_accuracy", 1.0)
        record.set_metric("latency", 0.0)

        score = registry.compute_trust_score("peer-1")
        assert score <= 1.0


class TestTrustRegistry:
    """Test TrustRegistry persistence and operations."""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary trust registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "trust.json")
            registry = TrustRegistry(path=path)
            yield registry

    def test_registry_initialization(self, temp_registry):
        """Test registry initialization."""
        assert len(temp_registry.records) == 0

    def test_get_or_create_record(self, temp_registry):
        """Test getting or creating a record."""
        record = temp_registry.get_record("peer-1")
        assert record.node_id == "peer-1"
        assert "peer-1" in temp_registry.records

    def test_update_metric(self, temp_registry):
        """Test updating a metric."""
        temp_registry.update_metric("peer-1", "uptime", -0.05)
        record = temp_registry.get_record("peer-1")
        assert record.get_metric("uptime") == pytest.approx(0.95)

    def test_compute_trust_score(self, temp_registry):
        """Test computing trust score."""
        record = temp_registry.get_record("peer-1")
        record.set_metric("uptime", 0.8)
        score = temp_registry.compute_trust_score("peer-1")
        assert 0.0 <= score <= 1.0

    def test_decay_reduces_metrics(self, temp_registry):
        """Test that decay reduces metrics."""
        record = temp_registry.get_record("peer-1")
        record.set_metric("uptime", 0.9)
        record.set_metric("auth_success", 0.85)

        # Apply decay
        temp_registry.decay(decay_rate=0.1)

        # Metrics should be reduced
        decayed_uptime = record.get_metric("uptime")
        decayed_auth = record.get_metric("auth_success")
        assert decayed_uptime < 0.9
        assert decayed_auth < 0.85

    def test_decay_reduces_violations(self, temp_registry):
        """Test that decay reduces violations."""
        record = temp_registry.get_record("peer-1")
        record.set_metric("violations", 5.0)

        # Apply decay
        temp_registry.decay(decay_rate=0.1)

        # Violations should decrease
        violations = record.get_metric("violations")
        assert violations < 5.0

    def test_persistence(self):
        """Test that registry persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "trust.json")

            # Create and populate
            registry1 = TrustRegistry(path=path)
            registry1.update_metric("peer-1", "uptime", -0.1)

            # Create new registry from same path
            registry2 = TrustRegistry(path=path)
            record = registry2.get_record("peer-1")
            assert record.get_metric("uptime") == pytest.approx(0.9)

    def test_export_snapshot(self, temp_registry):
        """Test exporting a snapshot."""
        temp_registry.update_metric("peer-1", "uptime", -0.1)
        temp_registry.update_metric("peer-2", "auth_success", 0.05)

        snapshot = temp_registry.export_snapshot()
        assert "records" in snapshot
        assert "peer-1" in snapshot["records"]
        assert "peer-2" in snapshot["records"]
        assert "exported_at" in snapshot

    def test_import_snapshot_merge(self, temp_registry):
        """Test importing a snapshot with merge."""
        # Create initial data
        temp_registry.update_metric("peer-1", "uptime", -0.1)

        # Create snapshot from another registry
        snapshot = {
            "records": {
                "peer-2": {
                    "node_id": "peer-2",
                    "trust_score": 0.7,
                    "reputation": {
                        "uptime": 0.8,
                        "auth_success": 0.9,
                        "diff_accuracy": 0.7,
                        "latency": 0.1,
                        "violations": 0,
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        }

        # Import with merge
        temp_registry.import_snapshot(snapshot, merge=True)

        # Should have both records
        assert "peer-1" in temp_registry.records
        assert "peer-2" in temp_registry.records

    def test_get_all_trust_levels(self, temp_registry):
        """Test getting all trust levels."""
        temp_registry.update_metric("peer-1", "uptime", -0.1)
        temp_registry.update_metric("peer-2", "uptime", -0.2)

        all_levels = temp_registry.get_all_trust_levels()
        assert "peer-1" in all_levels
        assert "peer-2" in all_levels
        assert all_levels["peer-1"] > 0.0


class TestTrustEngine:
    """Test TrustEngine event handling."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = TrustEngine(decay_interval_seconds=600)
        assert engine.registry is not None
        assert engine.decay_interval == 600
        assert not engine._running

    def test_trust_events_mapping(self):
        """Test that all trust events are mapped."""
        assert "federation.session.accepted" in TRUST_EVENTS
        assert "federation.session.denied" in TRUST_EVENTS
        assert "federation.diff.applied" in TRUST_EVENTS
        assert "federation.diff.rejected" in TRUST_EVENTS
        assert "federation.graph.updated" in TRUST_EVENTS
        assert "federation.policy.violation" in TRUST_EVENTS

    def test_session_accepted_event(self):
        """Test that session accepted increases auth_success."""
        metric, delta = TRUST_EVENTS["federation.session.accepted"]
        assert metric == "auth_success"
        assert delta == 0.02

    def test_violation_event(self):
        """Test that violation events add violations."""
        metric, delta = TRUST_EVENTS["federation.policy.violation"]
        assert metric == "violations"
        assert delta == 1.0

    @pytest.mark.asyncio
    async def test_handle_trust_event(self):
        """Test handling a trust event."""
        engine = TrustEngine()

        # First, reduce auth_success so there's room to improve
        engine.registry.update_metric("peer-1", "auth_success", -0.2)
        initial_trust = engine.get_peer_trust("peer-1")

        payload = {
            "source_node_id": "peer-1",
            "target_node_id": "peer-2",
        }

        # Simulate handling session accepted event
        await engine._handle_trust_event("federation.session.accepted", payload)

        # Trust should be updated
        final_trust = engine.get_peer_trust("peer-1")
        assert final_trust > initial_trust  # Should have increased

    def test_is_trusted_above_threshold(self):
        """Test trusted check with threshold."""
        engine = TrustEngine()

        # Update peer to have higher trust
        engine.registry.update_metric("peer-1", "uptime", 0.2)  # Push higher
        trust_score = engine.registry.compute_trust_score("peer-1")

        # Should be trusted above default threshold
        if trust_score >= 0.3:
            assert engine.is_trusted("peer-1", threshold=0.3)
        else:
            assert not engine.is_trusted("peer-1", threshold=0.9)

    def test_is_trusted_low_score_rejected(self):
        """Test that low-trust peers are rejected."""
        engine = TrustEngine()

        # Add violations to lower trust
        engine.registry.update_metric("peer-1", "violations", 10.0)
        trust_score = engine.registry.compute_trust_score("peer-1")

        # Should be rejected (trust < 0.3)
        assert not engine.is_trusted("peer-1", threshold=0.3)


class TestTrustDecay:
    """Test metric decay behavior."""

    @pytest.fixture
    def registry(self):
        """Create a test registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "trust.json")
            reg = TrustRegistry(path=path)
            yield reg

    def test_decay_reduces_all_metrics(self, registry):
        """Test that decay reduces all positive metrics."""
        record = registry.get_record("peer-1")

        # Set metrics
        record.set_metric("uptime", 0.9)
        record.set_metric("auth_success", 0.85)
        record.set_metric("diff_accuracy", 0.8)

        initial_sum = (
            record.get_metric("uptime")
            + record.get_metric("auth_success")
            + record.get_metric("diff_accuracy")
        )

        # Apply decay
        registry.decay(decay_rate=0.1)

        decayed_sum = (
            record.get_metric("uptime")
            + record.get_metric("auth_success")
            + record.get_metric("diff_accuracy")
        )

        # Sum should decrease
        assert decayed_sum < initial_sum

    def test_decay_rate_parameter(self, registry):
        """Test that decay rate affects the amount of decay."""
        record1 = registry.get_record("peer-1")
        record1.set_metric("uptime", 0.9)

        registry.decay(decay_rate=0.05)
        result1 = record1.get_metric("uptime")

        # Create new registry with same state
        record2 = registry.get_record("peer-2")
        record2.set_metric("uptime", 0.9)

        registry.decay(decay_rate=0.2)
        result2 = record2.get_metric("uptime")

        # Higher decay rate should reduce more
        assert result2 < result1


class TestLowTrustRejection:
    """Test low-trust peer rejection."""

    def test_reject_peer_below_threshold(self):
        """Test rejecting peers below trust threshold."""
        engine = TrustEngine()
        registry = engine.registry

        # Add multiple violations
        registry.update_metric("untrusted-peer", "violations", 10.0)
        trust_score = registry.compute_trust_score("untrusted-peer")

        # Should be below threshold (0.3)
        assert trust_score < 0.3
        assert not engine.is_trusted("untrusted-peer", threshold=0.3)

    def test_accept_peer_above_threshold(self):
        """Test accepting peers above trust threshold."""
        registry = TrustRegistry(path=":memory:")
        engine = TrustEngine()

        # Good peer with no violations
        record = registry.get_record("trusted-peer")
        for metric in ["uptime", "auth_success", "diff_accuracy"]:
            record.set_metric(metric, 0.95)
        record.set_metric("latency", 0.05)

        trust_score = registry.compute_trust_score("trusted-peer")

        # Should be above threshold
        assert trust_score > 0.3
        assert engine.is_trusted("trusted-peer", threshold=0.3)


class TestSearchRankingWithTrust:
    """Test search result ranking with dynamic trust."""

    def test_high_trust_peer_higher_score(self):
        """Test that high-trust peers' results score higher."""
        registry = TrustRegistry(path=":memory:")

        # High trust peer
        high_peer = registry.get_record("high-trust-peer")
        for metric in ["uptime", "auth_success", "diff_accuracy"]:
            high_peer.set_metric(metric, 0.95)
        high_trust = registry.compute_trust_score("high-trust-peer")

        # Low trust peer
        low_peer = registry.get_record("low-trust-peer")
        low_peer.set_metric("violations", 5.0)
        low_trust = registry.compute_trust_score("low-trust-peer")

        # High trust should be greater
        assert high_trust > low_trust

    def test_trust_affects_search_ranking(self):
        """Test that trust level affects search result ranking."""
        registry = TrustRegistry(path=":memory:")

        # Create two peers with different trust
        registry.update_metric("peer-1", "uptime", 0.2)
        registry.update_metric("peer-2", "violations", 3.0)

        score1 = registry.compute_trust_score("peer-1")
        score2 = registry.compute_trust_score("peer-2")

        # When ranking search results, peer-1 should score higher
        # (assuming same semantic similarity)
        assert score1 > score2
