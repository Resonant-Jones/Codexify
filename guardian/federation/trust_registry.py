"""Trust registry for managing peer node reliability and trust weights.

Trust levels influence the ranking of search results from peer nodes.
Higher trust peers' results are weighted more heavily in merged result sets.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Default trust levels for peers
DEFAULT_TRUST_LEVELS: Dict[str, float] = {
    # Format: "peer_node_id": trust_level (0.0 to 1.0)
    # These can be overridden by environment or configuration
}


class TrustRegistry:
    """Registry for managing trust levels between federated nodes.

    Trust levels are used to weight the importance of search results
    from different peers during semantic discovery.
    """

    def __init__(self, initial_trust: Optional[Dict[str, float]] = None):
        """Initialize trust registry.

        Args:
            initial_trust: Dictionary mapping peer_id to trust level (0.0-1.0)
        """
        self.trust = initial_trust or DEFAULT_TRUST_LEVELS.copy()
        self.last_updated: Dict[str, datetime] = {}

    def get_trust_level(self, peer_id: str) -> float:
        """Get trust level for a peer.

        Returns default trust (0.5) if peer not explicitly configured.

        Args:
            peer_id: Peer node identifier

        Returns:
            Trust level from 0.0 (untrusted) to 1.0 (fully trusted)
        """
        return self.trust.get(peer_id, 0.5)

    def set_trust_level(self, peer_id: str, trust_level: float) -> None:
        """Set trust level for a peer.

        Args:
            peer_id: Peer node identifier
            trust_level: Trust level from 0.0 to 1.0

        Raises:
            ValueError: If trust_level is outside [0.0, 1.0]
        """
        if not 0.0 <= trust_level <= 1.0:
            raise ValueError(f"Trust level must be between 0.0 and 1.0, got {trust_level}")

        self.trust[peer_id] = trust_level
        self.last_updated[peer_id] = datetime.now(timezone.utc)
        logger.info(f"Updated trust level for {peer_id}: {trust_level}")

    def get_all_trust_levels(self) -> Dict[str, float]:
        """Get all configured trust levels.

        Returns:
            Dictionary of peer_id -> trust_level
        """
        return self.trust.copy()

    def reset_trust_level(self, peer_id: str) -> None:
        """Reset trust level to default.

        Args:
            peer_id: Peer node identifier
        """
        if peer_id in self.trust:
            del self.trust[peer_id]
            logger.info(f"Reset trust level for {peer_id} to default")

    def clear_all(self) -> None:
        """Clear all configured trust levels."""
        self.trust.clear()
        self.last_updated.clear()
        logger.warning("Cleared all trust levels")


# Global trust registry instance
_trust_registry: Optional[TrustRegistry] = None


def get_trust_registry() -> TrustRegistry:
    """Get or create the global trust registry instance.

    Returns:
        TrustRegistry instance
    """
    global _trust_registry
    if _trust_registry is None:
        _trust_registry = TrustRegistry()
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


def calculate_recency_factor(minutes_ago: int, max_age_minutes: int = 1440) -> float:
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
