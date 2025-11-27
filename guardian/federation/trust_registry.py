"""Trust registry for managing peer node reliability and reputation metrics.

Implements a sophisticated trust scoring system based on:
- Uptime: Node availability and responsiveness
- Auth success: Successful federation connections
- Diff accuracy: Quality of submitted diffs
- Latency: Response time performance
- Violations: Security and policy violations

Trust levels influence federation decisions, search result ranking, and access privileges.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default trust levels for peers
DEFAULT_TRUST_LEVELS: Dict[str, float] = {
    # Format: "peer_node_id": trust_level (0.0 to 1.0)
    # These can be overridden by environment or configuration
}


class TrustRecord(BaseModel):
    """Record of a peer node's trust metrics and reputation.

    Trust score is calculated from weighted combination of metrics:
    trust_score = 0.4*uptime + 0.3*auth_success + 0.2*diff_accuracy + 0.1*(1-latency)
    trust_score *= exp(-violations * 0.25)
    """

    node_id: str = Field(..., description="Peer node identifier")
    trust_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Computed trust score (0.0-1.0)",
    )
    reputation: Dict[str, float] = Field(
        default_factory=lambda: {
            "uptime": 1.0,
            "auth_success": 1.0,
            "diff_accuracy": 1.0,
            "latency": 1.0,
            "violations": 0,
        },
        description="Reputation metrics",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last time metrics were updated",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was created",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}

    def get_metric(self, metric_name: str) -> float:
        """Get a specific metric value."""
        return self.reputation.get(metric_name, 0.0)

    def set_metric(self, metric_name: str, value: float) -> None:
        """Set a specific metric value, clamping to valid range."""
        if metric_name == "violations":
            self.reputation[metric_name] = max(0, value)
        else:
            self.reputation[metric_name] = max(0.0, min(1.0, value))
        self.last_updated = datetime.now(timezone.utc)

    def update_metric(self, metric_name: str, delta: float) -> None:
        """Update a metric by a delta value."""
        current = self.get_metric(metric_name)
        if metric_name == "violations":
            new_value = current + delta
        else:
            new_value = current + delta
        self.set_metric(metric_name, new_value)


class TrustRegistry:
    """Registry for managing trust records and reputation between federated nodes.

    Maintains sophisticated trust metrics for each peer including uptime,
    auth success, diff accuracy, latency, and violations.
    Computes trust score from weighted metrics with exponential penalty for violations.
    """

    def __init__(
        self,
        path: str | Dict[str, float] = "data/trust_registry.json",
        initial_trust: Optional[Dict[str, float]] = None,
        load_existing: bool = True,
    ):
        """Initialize trust registry.

        Args:
            path: Path to persistent trust registry file
            initial_trust: Optional initial trust map
            load_existing: Load persisted registry from disk when True
        """
        if isinstance(path, dict):
            initial_trust = path
            path = "data/trust_registry.json"

        self.path = Path(path)
        self.records: Dict[str, TrustRecord] = {}
        # Keep simple trust dict for backward compatibility
        self.trust = (initial_trust or DEFAULT_TRUST_LEVELS).copy()
        self.last_updated: Dict[str, datetime] = {}
        if (
            load_existing
            and initial_trust is None
            and self.path != Path(":memory:")
        ):
            self._load()

    def _load(self) -> None:
        """Load trust records from persistent storage."""
        if self.path.exists():
            try:
                with open(self.path) as f:
                    data = json.load(f)

                for node_id, record_data in data.get("records", {}).items():
                    try:
                        record = TrustRecord(**record_data)
                        self.records[node_id] = record
                    except Exception as e:
                        logger.warning(
                            f"Failed to load trust record for {node_id}: {e}"
                        )

                logger.info(
                    f"Loaded trust records for {len(self.records)} peers"
                )
            except Exception as e:
                logger.error(
                    f"Failed to load trust registry from {self.path}: {e}"
                )

    def _save(self) -> None:
        """Save trust records to persistent storage."""
        try:
            data = {
                "records": {
                    node_id: json.loads(record.model_dump_json())
                    for node_id, record in self.records.items()
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.path)

        except Exception as e:
            logger.error(f"Failed to save trust registry: {e}")

    def get_record(self, node_id: str) -> TrustRecord:
        """Get or create a trust record for a peer.

        Args:
            node_id: Peer node identifier

        Returns:
            TrustRecord for the peer
        """
        if node_id not in self.records:
            self.records[node_id] = TrustRecord(node_id=node_id)
        return self.records[node_id]

    def get_trust_level(self, peer_id: str) -> float:
        """Get trust level for a peer.

        Returns computed trust score if record exists,
        else returns default trust (0.5).

        Args:
            peer_id: Peer node identifier

        Returns:
            Trust level from 0.0 (untrusted) to 1.0 (fully trusted)
        """
        if peer_id in self.trust:
            return self.trust.get(peer_id, 0.5)
        if peer_id in self.records:
            return self.compute_trust_score(peer_id)
        return 0.5

    def set_trust_level(self, peer_id: str, trust_level: float) -> None:
        """Set simple trust level for a peer (backward compatible).

        For sophisticated metric-based trust, use update_metric instead.

        Args:
            peer_id: Peer node identifier
            trust_level: Trust level from 0.0 to 1.0

        Raises:
            ValueError: If trust_level is outside [0.0, 1.0]
        """
        if not 0.0 <= trust_level <= 1.0:
            raise ValueError(
                f"Trust level must be between 0.0 and 1.0, got {trust_level}"
            )

        self.trust[peer_id] = trust_level
        self.last_updated[peer_id] = datetime.now(timezone.utc)
        logger.info(f"Updated trust level for {peer_id}: {trust_level}")

    def update_metric(self, node_id: str, metric: str, delta: float) -> None:
        """Update a reputation metric for a peer.

        Args:
            node_id: Peer node identifier
            metric: Metric name (uptime, auth_success, diff_accuracy, latency, violations)
            delta: Change in metric value
        """
        record = self.get_record(node_id)
        record.update_metric(metric, delta)
        self.last_updated[node_id] = datetime.now(timezone.utc)
        logger.debug(f"Updated {metric} for {node_id} by {delta}")
        self._save()

    def compute_trust_score(self, node_id: str) -> float:
        """Compute trust score from reputation metrics.

        Formula:
            base_score = 0.4*uptime + 0.3*auth_success + 0.2*diff_accuracy + 0.1*(1-latency)
            trust_score = base_score * exp(-violations * 0.25)

        Args:
            node_id: Peer node identifier

        Returns:
            Trust score from 0.0 to 1.0
        """
        record = self.get_record(node_id)
        metrics = record.reputation

        # Weighted combination of base metrics
        base_score = (
            0.4 * metrics.get("uptime", 1.0)
            + 0.3 * metrics.get("auth_success", 1.0)
            + 0.2 * metrics.get("diff_accuracy", 1.0)
            + 0.1 * (1.0 - metrics.get("latency", 0.0))
        )

        # Apply exponential penalty for violations
        violations = metrics.get("violations", 0)
        penalty = math.exp(-violations * 0.25)
        trust_score = base_score * penalty

        # Clamp to valid range
        trust_score = max(0.0, min(1.0, trust_score))

        # Update record
        record.trust_score = trust_score
        self.last_updated[node_id] = datetime.now(timezone.utc)

        return trust_score

    def decay(self, decay_rate: float = 0.05) -> None:
        """Apply decay to all metrics over time.

        Reduces drift and encourages peers to maintain reputation.

        Args:
            decay_rate: Rate of decay (0.0-1.0), applied to positive metrics
        """
        now = datetime.now(timezone.utc)
        for node_id, record in self.records.items():
            # Decay positive metrics toward default
            for metric in ["uptime", "auth_success", "diff_accuracy"]:
                current = record.get_metric(metric)
                decayed = current * (1.0 - decay_rate)
                record.set_metric(metric, decayed)

            # Slowly reduce violations
            violations = record.get_metric("violations")
            if violations > 0:
                record.set_metric(
                    "violations", violations * (1.0 - decay_rate * 0.5)
                )

            # Recompute trust score
            self.compute_trust_score(node_id)

        logger.debug(f"Applied decay to {len(self.records)} trust records")
        self._save()

    def get_all_trust_levels(self) -> Dict[str, float]:
        """Get all configured trust levels (includes computed scores).

        Returns:
            Dictionary of peer_id -> trust_level
        """
        result = self.trust.copy()
        # Add computed trust scores
        for node_id in self.records:
            result[node_id] = self.get_trust_level(node_id)
        return result

    def get_all_records(self) -> Dict[str, TrustRecord]:
        """Get all trust records.

        Returns:
            Dictionary of node_id -> TrustRecord
        """
        return self.records.copy()

    def reset_trust_level(self, peer_id: str) -> None:
        """Reset trust level to default.

        Args:
            peer_id: Peer node identifier
        """
        if peer_id in self.trust:
            del self.trust[peer_id]
            logger.info(f"Reset trust level for {peer_id} to default")
        if peer_id in self.records:
            del self.records[peer_id]
            self._save()

    def clear_all(self) -> None:
        """Clear all configured trust levels and records."""
        self.trust.clear()
        self.records.clear()
        self.last_updated.clear()
        logger.warning("Cleared all trust levels")
        self._save()

    def export_snapshot(self) -> Dict[str, Any]:
        """Export trust registry as a snapshot for sharing.

        Returns:
            Dictionary with all records and metadata
        """
        return {
            "records": {
                node_id: json.loads(record.model_dump_json())
                for node_id, record in self.records.items()
            },
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def import_snapshot(
        self, snapshot: Dict[str, Any], merge: bool = True
    ) -> None:
        """Import a trust registry snapshot.

        Args:
            snapshot: Snapshot dictionary from export_snapshot
            merge: If True, merge with existing; if False, replace
        """
        try:
            if not merge:
                self.records.clear()

            for node_id, record_data in snapshot.get("records", {}).items():
                try:
                    record = TrustRecord(**record_data)
                    # Don't overwrite newer records
                    if node_id in self.records:
                        existing = self.records[node_id]
                        if record.last_updated > existing.last_updated:
                            self.records[node_id] = record
                    else:
                        self.records[node_id] = record
                except Exception as e:
                    logger.warning(
                        f"Failed to import record for {node_id}: {e}"
                    )

            logger.info(f"Imported snapshot with {len(self.records)} records")
            self._save()
        except Exception as e:
            logger.error(f"Failed to import snapshot: {e}")


# Global trust registry instance
_trust_registry: Optional[TrustRegistry] = None


def get_trust_registry(path: str = "data/trust_registry.json") -> TrustRegistry:
    """Get or create the global trust registry instance.

    Args:
        path: Path to trust registry file

    Returns:
        TrustRegistry instance
    """
    global _trust_registry
    if _trust_registry is None:
        _trust_registry = TrustRegistry(path=path)
    return _trust_registry


def calculate_result_score(
    similarity: float,
    trust_level: float = 0.5,
    recency: float = 0.5,
) -> float:
    """Calculate ranked score for a search result.

    Combines semantic similarity, peer trust, and result recency.

    Formula:
        score = similarity * 0.7 + trust * 0.2 + recency * 0.1

    Args:
        similarity: Semantic similarity score (0.0 to 1.0)
        trust_level: Peer trust level (0.0 to 1.0), default 0.5
        recency: Recency factor (0.0 to 1.0), default 0.5

    Returns:
        Combined ranked score (0.0 to 1.0)
    """
    # Ensure inputs are in valid range
    sim = max(0.0, min(1.0, similarity))
    trust = max(0.0, min(1.0, trust_level))
    rec = max(0.0, min(1.0, recency))

    # Weighted combination
    score = (sim * 0.7) + (trust * 0.2) + (rec * 0.1)
    return min(1.0, score)  # Cap at 1.0


def calculate_recency_factor(
    minutes_ago: int, max_age_minutes: int = 1440
) -> float:
    """Calculate recency factor for a result based on age.

    Older results get lower scores. Results older than max_age get 0.0.

    Args:
        minutes_ago: How many minutes ago the result was created/updated
        max_age_minutes: Age at which recency factor becomes 0.0 (default 24 hours)

    Returns:
        Recency factor from 0.0 (very old) to 1.0 (very recent)
    """
    if minutes_ago < 0:
        return 1.0

    if minutes_ago >= max_age_minutes:
        return 0.0

    # Linear decline from 1.0 to 0.0 over time
    return 1.0 - (minutes_ago / max_age_minutes)
